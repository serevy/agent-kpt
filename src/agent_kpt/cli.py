from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from agent_kpt.adapters.claude_code import ingest_paths, load_lineage_map
from agent_kpt.metrics import compute_metrics, render_metrics_markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-kpt")
    subcommands = parser.add_subparsers(dest="command", required=True)

    ingest = subcommands.add_parser("ingest", help="normalize provider session data")
    ingest_sub = ingest.add_subparsers(dest="provider", required=True)
    claude = ingest_sub.add_parser("claude-code", help="normalize Claude Code JSONL sessions")
    claude.add_argument("paths", nargs="+", help="session .jsonl files")
    claude.add_argument("--lineage-map", help="optional JSON lineage map")
    claude.add_argument("-o", "--output", default="-", help="output JSON path, or - for stdout")

    metrics = subcommands.add_parser("metrics", help="compute deterministic metrics")
    metrics.add_argument("input", help="normalized adapter-result JSON")
    metrics.add_argument("--timezone", default="UTC", help="IANA report timezone")
    metrics.add_argument("-o", "--output", default="-", help="output JSON path, or - for stdout")

    report = subcommands.add_parser("report", help="render deterministic Markdown metrics")
    report.add_argument("input", help="normalized adapter-result JSON")
    report.add_argument("--timezone", default="UTC", help="IANA report timezone")
    report.add_argument("-o", "--output", default="-", help="output Markdown path, or - for stdout")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "ingest" and args.provider == "claude-code":
            lineage = load_lineage_map(args.lineage_map) if args.lineage_map else None
            result = ingest_paths(args.paths, lineage_map=lineage)
            _write_text(args.output, json.dumps(result, ensure_ascii=False, indent=2) + "\n")
            return 0
        if args.command == "metrics":
            normalized = _read_json(args.input)
            result = compute_metrics(normalized, report_timezone=args.timezone)
            _write_text(args.output, json.dumps(result, ensure_ascii=False, indent=2) + "\n")
            return 0
        if args.command == "report":
            normalized = _read_json(args.input)
            result = compute_metrics(normalized, report_timezone=args.timezone)
            _write_text(args.output, render_metrics_markdown(result))
            return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"agent-kpt: {exc}", file=sys.stderr)
        return 2
    parser.error("unsupported command")
    return 2


def _read_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_text(path: str, content: str) -> None:
    if path == "-":
        sys.stdout.write(content)
        return
    Path(path).write_text(content, encoding="utf-8")
