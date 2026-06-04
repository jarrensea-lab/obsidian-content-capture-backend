---
name: douyin-content-capture
description: >-
  抖音分享链解析、无水印下载、本地 Whisper 转写、图文配文与配图提取。
  维护 obsidian-content-capture-backend 的 script/、web/、流水线或 Obsidian 插件对接时使用。
---

# 抖音内容提取（本地流水线）

从抖音分享链接或整段分享文案，获取无水印视频/配图，在本地提取简体文案并保存到 `output/`。**无需登录 Cookie，无需云端语音 API。**

## 功能概述

- **获取作品信息**: 解析短链、`note`/`video` 页、`iesdouyin.com/share`；读分享页 SSR 公开数据
- **无水印下载**: 视频 CDN 直链；图文下载 `images/` 配图
- **提取文案**: 视频用本地 **faster-whisper** + **zhconv**；图文直接取 `desc` 配文（不做图片 OCR）
- **自动保存**: 每个作品一个文件夹 `output/{作品ID}_{标题}/`

## 环境要求

### 依赖安装

```bash
cd obsidian-content-capture-backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

| 包 | 用途 |
|----|------|
| `requests` | 分享页请求、文件下载 |
| `faster-whisper` | 视频转写（首次需联网下载模型） |
| `zhconv` | 转写结果转简体 |
| `flask` | Web 界面（仅 `web/` 需要） |

### 系统要求

- Python 3.10+
- **FFmpeg**（视频抽音频）
  - macOS: `brew install ffmpeg`
  - Ubuntu: `sudo apt install ffmpeg`
- 首次转写会从网上下载 Whisper 模型；视频在 CPU 上可能较慢

## 使用方法

### 命令行

```bash
# 完整提取（视频或图文）
python main.py "https://v.douyin.com/xxxxx/"
python -m script "https://www.douyin.com/note/作品ID"

# 指定 Whisper 模型（仅视频）
python main.py --model base "https://v.douyin.com/xxxxx/"

# 指定输出目录
python -m script -o ./output "分享链接或整段文案"
```

### Web 界面

```bash
python web/app.py
```

浏览器打开 **http://127.0.0.1:5050**，可「获取信息」或「提取文案」。

### 在 Python 中调用

```python
from script.config import Settings
from script.douyin_resolver import resolve_douyin_share
from script.pipeline import process_douyin_share

# 仅元数据
info = resolve_douyin_share("抖音分享链接")

# 完整流水线
out_dir = process_douyin_share("抖音分享链接", settings=Settings(whisper_model="small"))
```

### HTTP API（插件 / Obsidian 对接）

- `POST /api/video/info` — `{ "url": "..." }` 仅信息
- `POST /api/video/extract` — `{ "url": "...", "model": "small" }` 完整提取
- `GET /api/health` — 健康检查

## 输出目录结构

**视频:**

```
output/{作品ID}_{标题}/
├── video.mp4
├── audio.wav
├── transcript.txt
├── transcript_segments.json
└── meta.json
```

**图文:**

```
output/{作品ID}_{标题}/
├── images/01.jpg …
├── image_urls.txt
├── transcript.txt
└── meta.json
```

`transcript.txt` 含元数据头，正文在 `--- 文案 ---` 之后。

## 工作流程

### 获取作品信息

1. 从输入中提取抖音链接（支持整段分享文案）
2. `www.douyin.com/note|video` 转为 `iesdouyin.com/share/...`
3. 移动端 UA 请求分享页，解析 `_ROUTER_DATA`
4. 返回作品 ID、标题、作者、无水印链接或配图列表

### 提取文案（视频）

1. 下载无水印视频到作品目录
2. FFmpeg 提取 16kHz 音频
3. faster-whisper 转写，zhconv 转简体
4. 写入 `transcript.txt`、`meta.json`

### 提取文案（图文）

1. 将 `desc` 作为文案写入 `transcript.txt`
2. 下载全部配图到 `images/`
3. 不运行 Whisper

## 代码位置（改 bug 时）

| 需求 | 文件 |
|------|------|
| 链接解析 | `script/douyin_resolver.py` |
| 下载与流水线 | `script/pipeline.py` |
| 语音转写 | `script/transcriber.py` |
| Web / API | `web/app.py` |

业务写在 `script/`；`web/` 只做界面与 HTTP。插件化时调 `process_douyin_share()`，详见 README。

## 常见问题

### 无法解析链接

- 确认链接有效（`v.douyin.com` 短链或 `note`/`video` 页）
- `note` 页必须能转到 `iesdouyin.com/share/note/...`

### 提取很慢或报错

- 视频转写耗时长，CPU 用 `small` 模型数分钟正常
- 确保已 `activate .venv`，且已安装 FFmpeg
- `float16 → float32` 警告可忽略

### Web 无反应

- 提取为同步请求，视频未完成前页面不会更新
- 服务默认端口 **5050**（非 5000）

## 注意事项

- 仅供学习与研究，遵守法律法规与平台规则
- 图文题本在图片中的文字不会自动识别
- 更多说明见项目根目录 `README.md`
