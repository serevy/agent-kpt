from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from agent_kpt.adapters.claude_code import ingest_paths, load_lineage_map
from agent_kpt.metrics import compute_metrics, render_metrics_markdown
from agent_kpt.report import render_report_html, render_report_markdown
from agent_kpt.review import apply_review_actions
from agent_kpt.workflow import build_analysis_packet, ledger_status


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

    render = subcommands.add_parser(
        "render-report",
        help="render a concise Report View Model as HTML or Markdown",
    )
    render.add_argument("input", help="report-view JSON")
    render.add_argument("--format", choices=("html", "markdown"), default="html")
    render.add_argument("-o", "--output", default="-", help="output path, or - for stdout")

    workflow = subcommands.add_parser("workflow", help="prepare KPT workflow inputs")
    workflow_sub = workflow.add_subparsers(dest="workflow_command", required=True)
    prepare = workflow_sub.add_parser("prepare", help="build a privacy-safe analysis packet")
    prepare.add_argument("mode", choices=("weekly", "monthly"))
    prepare.add_argument("--project", default=".", help="project working directory")
    prepare.add_argument("--claude-root", help="override ~/.claude/projects")
    prepare.add_argument("--timezone", default="UTC", help="IANA report timezone")
    prepare.add_argument("--no-persist", action="store_true", help="do not save last packet")
    prepare.add_argument("-o", "--output", default="-", help="output JSON path, or - for stdout")

    status = subcommands.add_parser("status", help="show local improvement-ledger status")
    status.add_argument("--project", default=".", help="project working directory")
    status.add_argument("-o", "--output", default="-", help="output JSON path, or - for stdout")

    apply_review = subcommands.add_parser(
        "apply-review",
        help="apply semantic review actions to the local improvement ledger",
    )
    apply_review.add_argument("actions", help="review-actions JSON")
    apply_review.add_argument("packet", help="analysis packet JSON")
    apply_review.add_argument("--project", default=".", help="project working directory")
    apply_review.add_argument("-o", "--output", default="-", help="write updated ledger JSON")

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

        if args.command == "render-report":
            view = _read_json(args.input)
            rendered = (
                render_report_html(view)
                if args.format == "html"
                else render_report_markdown(view)
            )
            _write_text(args.output, rendered)
            return 0

        if args.command == "workflow" and args.workflow_command == "prepare":
            packet = build_analysis_packet(
                args.mode,
                project=args.project,
                root=args.claude_root,
                report_timezone=args.timezone,
                persist=not args.no_persist,
            )
            _write_text(args.output, json.dumps(packet, ensure_ascii=False, indent=2) + "\n")
            return 0

        if args.command == "status":
            result = ledger_status(project=args.project)
            _write_text(args.output, json.dumps(result, ensure_ascii=False, indent=2) + "\n")
            return 0

        if args.command == "apply-review":
            actions = _read_json(args.actions)
            packet = _read_json(args.packet)
            result = apply_review_actions(actions, packet, project=args.project)
            _write_text(args.output, json.dumps(result, ensure_ascii=False, indent=2) + "\n")
            return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
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
