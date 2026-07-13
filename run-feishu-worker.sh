#!/usr/bin/env bash
# Process Feishu video-inbox records. Pass --dry-run to verify without downloading.
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi

export VIDEO_INBOX_DIR="${VIDEO_INBOX_DIR:-/Users/zhuchenyuan/AI/projects/司库/01-资料采集/Inbox/video-inbox}"

exec .venv/bin/python -m script.feishu_inbox_worker "$@"
