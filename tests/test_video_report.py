from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from script.video_report import generate_siku_reports


class VideoReportTest(unittest.TestCase):
    def test_generate_siku_reports_writes_raw_distilled_and_suggestion_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out_dir = root / "output" / "123_运镜大全"
            out_dir.mkdir(parents=True)
            (out_dir / "meta.json").write_text(
                json.dumps(
                    {
                        "aweme_id": "123",
                        "title": "4类186组运镜大全图解",
                        "author": "阿拉赛博蕾",
                        "content_type": "video",
                        "source_url": "https://v.douyin.com/test/",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (out_dir / "transcript.txt").write_text(
                "标题: 4类186组运镜大全图解\n\n--- 文案 ---\n\n"
                "这个视频整理了 Seedance 视频生成里的运镜分类、镜头节奏和提示词复用方法。"
                "提示词模板是：主体 + 动作 + 镜头运动 + 风格。"
                "在 Seedance 软件里使用 @语法 引用角色图，参数建议 motion strength 0.6。",
                encoding="utf-8",
            )
            frames_dir = out_dir / "frames"
            frames_dir.mkdir()
            (frames_dir / "frame_0001.jpg").write_bytes(b"jpg")
            (frames_dir / "manifest.json").write_text(
                json.dumps(
                    {
                        "frame_count": 1,
                        "every_seconds": 2,
                        "frames": ["frame_0001.jpg"],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (frames_dir / "frame_ocr.txt").write_text(
                "## frame_0001.jpg\n"
                "Seedance 提示词模板\n"
                "主体 + 动作 + 镜头运动 + 风格\n"
                "motion strength 0.6\n",
                encoding="utf-8",
            )

            reports = generate_siku_reports(
                out_dir,
                siku_root=root / "司库",
                source_link="https://v.douyin.com/test/",
                source_text="手机分享文案",
            )

            self.assertTrue(reports.raw_note.exists())
            self.assertTrue(reports.study_report.exists())
            self.assertTrue(reports.project_suggestion.exists())
            study_text = reports.study_report.read_text(encoding="utf-8")
            self.assertIn("Seedance", study_text)
            self.assertIn("## 完整转写 / 配文", study_text)
            self.assertIn("## 可复用资产清单", study_text)
            self.assertIn("### 提示词模板", study_text)
            self.assertIn("主体 + 动作 + 镜头运动 + 风格", study_text)
            self.assertIn("### 软件 / 工具用法", study_text)
            self.assertIn("Seedance", study_text)
            self.assertIn("### Skill / 工作流", study_text)
            self.assertIn("### 参数 / 语法", study_text)
            self.assertIn("@语法", study_text)
            self.assertIn("## 帧证据", study_text)
            self.assertIn("frame_0001.jpg", study_text)
            self.assertIn("## 帧 OCR 文本", study_text)
            self.assertIn("motion strength 0.6", study_text)
            self.assertIn(
                "这个视频整理了 Seedance 视频生成里的运镜分类、镜头节奏和提示词复用方法。",
                study_text,
            )
            self.assertIn("OHHF", reports.project_suggestion.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
