#!/usr/bin/env python3
"""Consume Feishu video-inbox records and run the Douyin extraction pipeline."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from script.feishu_inbox import default_inbox_files, process_inbox_once
from script.paths import OUTPUT_DIR
from script.video_report import DEFAULT_SIKU_ROOT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="处理飞书短视频收件箱队列。")
    parser.add_argument(
        "--inbox-dir",
        type=Path,
        help="收件箱目录，默认读取 VIDEO_INBOX_DIR 或 output/_inbox。",
    )
    parser.add_argument("--inbox-path", type=Path, help="指定 feishu-events.jsonl 路径。")
    parser.add_argument("--processed-path", type=Path, help="指定 processed-events.jsonl 路径。")
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT_DIR, help="提取结果输出目录。")
    parser.add_argument("--model", default="small", choices=["tiny", "base", "small", "medium", "large-v2", "large-v3"])
    parser.add_argument("--device", default="auto")
    parser.add_argument("--compute-type", default="default")
    parser.add_argument("--skip-transcribe", action="store_true", help="只下载视频/图文，不跑 Whisper。")
    parser.add_argument("--dry-run", action="store_true", help="只记录将处理哪些链接，不下载不转写。")
    parser.add_argument("--no-report", action="store_true", help="不生成司库 Markdown 报告。")
    parser.add_argument("--siku-root", type=Path, default=DEFAULT_SIKU_ROOT, help="司库根目录。")
    parser.add_argument("--gbrain-capture", action="store_true", help="报告生成后同步到 gbrain。")
    parser.add_argument("--gbrain-source", default="default", help="gbrain capture --source。")
    parser.add_argument("--limit", type=int, help="本轮最多创建多少条处理结果。")
    parser.add_argument("--loop", action="store_true", help="常驻轮询。")
    parser.add_argument("--interval", type=float, default=30.0, help="--loop 模式轮询间隔秒数。")
    return parser.parse_args()


def _resolve_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    if args.inbox_path and args.processed_path:
        return args.inbox_path, args.processed_path
    default_inbox_path, default_processed_path = default_inbox_files(args.inbox_dir)
    return args.inbox_path or default_inbox_path, args.processed_path or default_processed_path


def run_once(args: argparse.Namespace) -> int:
    inbox_path, processed_path = _resolve_paths(args)
    summary = process_inbox_once(
        inbox_path,
        processed_path,
        output_dir=args.output,
        model=args.model,
        device=args.device,
        compute_type=args.compute_type,
        skip_transcribe=args.skip_transcribe,
        dry_run=args.dry_run,
        write_reports=not args.no_report,
        siku_root=args.siku_root,
        gbrain_capture=args.gbrain_capture,
        gbrain_source=args.gbrain_source,
        limit=args.limit,
    )
    print(
        "scanned={scanned} created={created} skipped={skipped} failed={failed} inbox={inbox} processed={processed}".format(
            scanned=summary.scanned_records,
            created=summary.created_results,
            skipped=summary.skipped_results,
            failed=summary.failed_results,
            inbox=inbox_path,
            processed=processed_path,
        )
    )
    return 1 if summary.failed_results else 0


def main() -> int:
    args = parse_args()
    if not args.loop:
        return run_once(args)

    while True:
        code = run_once(args)
        if code:
            return code
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
