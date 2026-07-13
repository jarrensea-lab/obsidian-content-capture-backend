from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from script.frame_ocr import read_frame_ocr_text


DEFAULT_SIKU_ROOT = Path("/Users/zhuchenyuan/AI/projects/司库")


@dataclass(frozen=True)
class SikuReportPaths:
    raw_note: Path
    study_report: Path
    project_suggestion: Path


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_transcript(out_dir: Path) -> str:
    path = out_dir / "transcript.txt"
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8").strip()
    marker = "--- 文案 ---"
    if marker in text:
        return text.split(marker, 1)[1].strip()
    return text


def _read_frame_manifest(out_dir: Path) -> dict[str, Any]:
    manifest_path = out_dir / "frames" / "manifest.json"
    if not manifest_path.exists():
        return {}
    return _read_json(manifest_path)


def _safe_filename(value: str, *, fallback: str) -> str:
    text = re.sub(r"[\\/:*?\"<>|#\[\]\n\r\t]+", "-", value).strip(" .-")
    text = re.sub(r"\s+", "", text)
    return (text or fallback)[:48]


def _frontmatter(**items: str) -> str:
    lines = ["---"]
    for key, value in items.items():
        escaped = str(value).replace('"', '\\"')
        lines.append(f'{key}: "{escaped}"')
    lines.append("---")
    return "\n".join(lines)


def _extract_points(text: str, *, limit: int = 8) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return ["原始内容暂未提取到足够文本，需要回看视频或重新转写。"]
    parts = re.split(r"[。！？!?；;]\s*", cleaned)
    points = [p.strip(" ，,") for p in parts if len(p.strip()) >= 8]
    if not points:
        return [cleaned[:180]]
    return points[:limit]


def _sentences(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []
    parts = re.split(r"(?<=[。！？!?；;])\s*|\n+", cleaned)
    return [part.strip(" ，,。") for part in parts if part.strip(" ，,。")]


def _matching_sentences(text: str, keywords: list[str], *, limit: int = 10) -> list[str]:
    matches: list[str] = []
    for sentence in _sentences(text):
        lower = sentence.lower()
        if any(keyword.lower() in lower for keyword in keywords):
            matches.append(sentence)
    return matches[:limit] or ["未从转写中明确提取到，需结合视频画面复核。"]


def _full_content_block(transcript: str) -> str:
    if not transcript.strip():
        return "暂未提取到正文。"
    return transcript.strip()


def _asset_sections(text: str, title: str) -> dict[str, list[str]]:
    corpus = f"{title}\n{text}"
    return {
        "提示词模板": _matching_sentences(
            corpus,
            ["提示词", "prompt", "模板", "主体", "风格", "镜头", "运镜", "角色"],
        ),
        "软件 / 工具用法": _matching_sentences(
            corpus,
            ["软件", "工具", "seedance", "comfyui", "豆绘", "剪映", "使用", "打开", "导入"],
        ),
        "Skill / 工作流": _matching_sentences(
            corpus,
            ["skill", "工作流", "流程", "步骤", "先", "然后", "最后", "拆解", "复用"],
        ),
        "参数 / 语法": _matching_sentences(
            corpus,
            ["参数", "语法", "@", "strength", "ratio", "seed", "fps", "motion", "权重"],
        ),
    }


def _asset_section_markdown(sections: dict[str, list[str]]) -> str:
    chunks: list[str] = []
    for title, items in sections.items():
        chunks.append(f"### {title}")
        chunks.append(_bullet_list(items))
    return "\n\n".join(chunks)


def _frame_evidence_markdown(out_dir: Path) -> str:
    manifest = _read_frame_manifest(out_dir)
    frames = manifest.get("frames") or []
    if not frames:
        return "暂未抽取视频帧。"
    every = manifest.get("every_seconds", "未知")
    lines = [
        f"- 帧目录：`{out_dir / 'frames'}`",
        f"- 抽帧间隔：每 {every} 秒",
        f"- 帧数量：{manifest.get('frame_count', len(frames))}",
        "- 帧索引：",
    ]
    lines.extend(f"  - `{name}`" for name in frames[:120])
    if len(frames) > 120:
        lines.append(f"  - 其余 {len(frames) - 120} 帧见本地目录。")
    return "\n".join(lines)


def _infer_projects(text: str, title: str) -> list[str]:
    haystack = f"{title}\n{text}".lower()
    projects: list[str] = []
    rules = [
        ("OHHF", ["seedance", "comfyui", "运镜", "镜头", "视频生成", "aicg", "图像", "视觉"]),
        ("gbrain", ["知识库", "rag", "记忆", "语义", "检索", "知识图谱", "agent"]),
        ("司库", ["obsidian", "笔记", "知识管理", "流程", "归档", "资料"]),
        ("恭喜发财", ["量化", "股票", "交易", "因子", "回测", "投资", "a股"]),
        ("Horizon", ["自动化", "调度", "日报", "飞书", "webhook", "系统"]),
    ]
    for project, keywords in rules:
        if any(keyword.lower() in haystack for keyword in keywords):
            projects.append(project)
    return projects or ["待人工归类"]


def _bullet_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _project_actions(projects: list[str]) -> list[str]:
    actions = ["将本视频先作为参考资料保留，不自动改动任何项目代码。"]
    if "OHHF" in projects:
        actions.append("评估是否能转成运镜/镜头语言提示词模板或 ComfyUI 工作流检查项。")
    if "恭喜发财" in projects:
        actions.append("提炼为研究假设或风险提示，先进入研究层验证，不直接进入交易信号。")
    if "gbrain" in projects:
        actions.append("评估是否能变成记忆检索、语义路由或证据组织规则。")
    if "司库" in projects:
        actions.append("评估是否能变成知识采集、标签路由或报告模板。")
    if "Horizon" in projects:
        actions.append("评估是否能变成自动化调度、通知或运行观测规则。")
    if projects == ["待人工归类"]:
        actions.append("先人工判断归属项目，再决定是否进入项目 Worklist。")
    return actions


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return path


def generate_siku_reports(
    out_dir: Path,
    *,
    siku_root: Path = DEFAULT_SIKU_ROOT,
    source_link: str = "",
    source_text: str = "",
    now: datetime | None = None,
) -> SikuReportPaths:
    meta = _read_json(out_dir / "meta.json")
    transcript = _read_transcript(out_dir)
    frame_ocr_text = read_frame_ocr_text(out_dir)
    analysis_text = "\n".join(part for part in [transcript, frame_ocr_text, source_text] if part)
    created_at = now or datetime.now().astimezone()
    date = created_at.strftime("%Y-%m-%d")
    aweme_id = str(meta.get("aweme_id") or meta.get("video_id") or out_dir.name)
    title = str(meta.get("title") or "未命名短视频")
    author = str(meta.get("author") or "未知作者")
    content_type = str(meta.get("content_type") or "unknown")
    source_url = source_link or str(meta.get("source_url") or "")
    filename = f"{date}__Douyin__{_safe_filename(title, fallback=aweme_id)}.md"

    points = _extract_points(analysis_text)
    projects = _infer_projects(analysis_text, title)
    assets = _asset_sections(analysis_text, title)
    frame_evidence = _frame_evidence_markdown(out_dir)

    raw_note = siku_root / "01-资料采集" / "Douyin" / filename
    study_report = siku_root / "03-知识加工" / "蒸馏精华" / "短视频学习" / filename
    project_suggestion = siku_root / "03-知识加工" / "智能建议" / "项目优化建议" / filename

    common_fm = {
        "type": "douyin-video-capture",
        "source": "feishu-mage",
        "date": date,
        "aweme_id": aweme_id,
        "title": title,
        "author": author,
        "source_url": source_url,
    }

    raw_content = f"""{_frontmatter(**common_fm)}
# {title}

## 基本信息
- 作者：{author}
- 类型：{content_type}
- 抖音链接：{source_url or "未记录"}
- 本地素材目录：{out_dir}

## 手机分享原文
{source_text or "未记录"}

## 转写 / 配文
{transcript or "暂未提取到正文。"}
"""

    study_content = f"""{_frontmatter(**{**common_fm, "type": "douyin-study-report"})}
# 短视频学习报告：{title}

## 内容概览
{points[0]}

## 核心要点
{_bullet_list(points)}

## 可复用资产清单
{_asset_section_markdown(assets)}

## 帧证据
{frame_evidence}

## 帧 OCR 文本
{frame_ocr_text or "暂未识别到帧中文字。"}

## 需要二次验证
- 原视频中的示例是否完整覆盖关键条件。
- 方法是否依赖特定模型、平台版本或作者经验。
- 是否能通过本地项目样例复现。
- 转写无法表达的软件界面、参数面板、提示词原文，需要结合帧证据或视觉模型复核。

## 关联项目
{_bullet_list(projects)}

## 完整转写 / 配文
{_full_content_block(transcript)}
"""

    suggestion_content = f"""{_frontmatter(**{**common_fm, "type": "project-suggestion-card"})}
# 项目优化建议卡：{title}

## 推荐关联项目
{_bullet_list(projects)}

## 建议动作
{_bullet_list(_project_actions(projects))}

## Worklist 草案
- [ ] 回看原视频和转写文本，确认关键概念没有识别错误。
- [ ] 抽取 3-5 条可复用规则。
- [ ] 选择一个目标项目做小样验证。
- [ ] 验证有效后再沉淀为方法卡或项目任务。

## 证据
- 原始采集：[[{raw_note.stem}]]
- 学习报告：[[{study_report.stem}]]
- 抖音链接：{source_url or "未记录"}
"""

    return SikuReportPaths(
        raw_note=_write(raw_note, raw_content),
        study_report=_write(study_report, study_content),
        project_suggestion=_write(project_suggestion, suggestion_content),
    )
