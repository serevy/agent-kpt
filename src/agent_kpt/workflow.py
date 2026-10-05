from __future__ import annotations

import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Mapping

from agent_kpt.adapters.claude_code import ingest_paths, inspect_transcript
from agent_kpt.metrics import compute_metrics
from agent_kpt.storage import (
    canonical_project_path,
    load_last_packet,
    load_ledger,
    project_key,
    save_last_packet,
)

PACKET_SCHEMA_VERSION = "agent-kpt.analysis/v0alpha1"


def default_claude_projects_root() -> Path:
    return Path.home() / ".claude" / "projects"


def discover_claude_code_paths(
    *,
    project: str | Path,
    root: str | Path | None = None,
) -> list[Path]:
    project_path = canonical_project_path(project)
    root_path = Path(root).expanduser() if root is not None else default_claude_projects_root()
    if not root_path.exists():
        return []

    mains: list[Path] = []
    for path in root_path.rglob("*.jsonl"):
        if _is_child_transcript(path):
            continue
        metadata = inspect_transcript(path)
        cwd = metadata.get("cwd")
        if isinstance(cwd, str) and _same_path(cwd, project_path):
            mains.append(path)

    selected: set[Path] = set(mains)
    for main in mains:
        session_dir = main.parent / main.stem
        if session_dir.exists():
            for child in session_dir.rglob("*.jsonl"):
                selected.add(child)
    return sorted(selected, key=lambda p: p.as_posix())


def build_analysis_packet(
    mode: str,
    *,
    project: str | Path,
    root: str | Path | None = None,
    report_timezone: str = "UTC",
    now: datetime | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    if mode not in {"weekly", "monthly"}:
        raise ValueError("mode must be weekly or monthly")
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)
    days = 7 if mode == "weekly" else 30
    start = now - timedelta(days=days)

    project_path = canonical_project_path(project)
    paths = discover_claude_code_paths(project=project_path, root=root)
    result = (
        ingest_paths(paths)
        if paths
        else {
            "schema_version": "agent-kpt.core/v0alpha1",
            "sessions": [],
            "events": [],
            "diagnostics": [
                {
                    "severity": "warning",
                    "code": "no-transcripts",
                    "message": "No Claude Code transcripts matched the current project.",
                    "recoverable": True,
                    "source_index": None,
                }
            ],
        }
    )
    result = _filter_result(result, start)
    metrics = compute_metrics(result, report_timezone=report_timezone)
    previous = load_last_packet(project_path)
    ledger = load_ledger(project_path)

    packet = {
        "schema_version": PACKET_SCHEMA_VERSION,
        "mode": mode,
        "generated_at": _iso(now),
        "period": {
            "start": _iso(start),
            "end": _iso(now),
            "timezone": report_timezone,
        },
        "project": {
            "name": project_path.name,
            "state_key": project_key(project_path),
        },
        "metrics": metrics,
        "signals": _signals(result),
        "environment": _environment_summary(result),
        "environment_changes": _environment_changes(previous, result),
        "ledger": _ledger_summary(ledger),
        "evidence": _evidence(result),
        "diagnostics": _summarize_diagnostics(result.get("diagnostics", [])),
        "report_contract": {
            "max_kpis": 4,
            "max_keep": 3,
            "max_problems": 3,
            "max_trends": 3,
            "max_next_try": 1,
            "scoring": "forbidden",
            "details_required": True,
        },
        "privacy": {
            "raw_prompt_text_persisted": False,
            "raw_assistant_text_persisted": False,
            "raw_tool_input_persisted": False,
            "raw_error_text_persisted": False,
            "derived_error_classification_retained": True,
        },
    }
    if persist:
        save_last_packet(project_path, packet)
    return packet


def ledger_status(*, project: str | Path) -> dict[str, Any]:
    project_path = canonical_project_path(project)
    ledger = load_ledger(project_path)
    previous = load_last_packet(project_path)
    return {
        "schema_version": "agent-kpt.status/v0alpha1",
        "project": project_path.name,
        "ledger": _ledger_summary(ledger),
        "last_report": previous.get("generated_at") if isinstance(previous, dict) else None,
    }


def _filter_result(result: Mapping[str, Any], start: datetime) -> dict[str, Any]:
    start_ts = start.astimezone(timezone.utc)
    events = [
        dict(event)
        for event in result.get("events", [])
        if _event_time(event.get("timestamp")) >= start_ts
    ]
    session_ids = {event.get("session_id") for event in events}
    sessions = [dict(s) for s in result.get("sessions", []) if s.get("id") in session_ids]
    return {
        "schema_version": result.get("schema_version", "agent-kpt.core/v0alpha1"),
        "sessions": sessions,
        "events": events,
        "diagnostics": list(result.get("diagnostics", [])),
    }


def _signals(result: Mapping[str, Any]) -> dict[str, Any]:
    events = [e for e in result.get("events", []) if e.get("history_role") == "observed"]
    event_counts = Counter(str(e.get("type")) for e in events)
    tools = Counter(
        str(e.get("payload", {}).get("name"))
        for e in events
        if e.get("type") == "tool.use" and e.get("payload", {}).get("name")
    )
    skills = Counter(
        str(e.get("payload", {}).get("name"))
        for e in events
        if e.get("type") == "skill.invoke" and e.get("payload", {}).get("name")
    )
    commands = Counter(
        str(e.get("payload", {}).get("name"))
        for e in events
        if e.get("type") == "command.invoke" and e.get("payload", {}).get("name")
    )
    subagents = Counter(
        str(e.get("payload", {}).get("type"))
        for e in events
        if e.get("type") == "subagent.invoke" and e.get("payload", {}).get("type")
    )

    message_lengths = [
        int(e.get("payload", {}).get("text_chars", 0))
        for e in events
        if e.get("type") == "user.message"
        and isinstance(e.get("payload", {}).get("text_chars"), int)
    ]

    usage_totals = Counter()
    for event in events:
        if event.get("type") != "model.call":
            continue
        usage = event.get("payload", {}).get("usage", {})
        if isinstance(usage, Mapping):
            for key in (
                "input_tokens",
                "output_tokens",
                "cache_creation_input_tokens",
                "cache_read_input_tokens",
            ):
                value = usage.get(key, 0)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    usage_totals[key] += value

    input_total = (
        usage_totals["input_tokens"]
        + usage_totals["cache_creation_input_tokens"]
        + usage_totals["cache_read_input_tokens"]
    )
    cache_pct = (
        round(100 * usage_totals["cache_read_input_tokens"] / input_total, 1)
        if input_total
        else 0.0
    )

    return {
        "event_counts": dict(sorted(event_counts.items())),
        "tool_usage": dict(tools.most_common()),
        "skill_invocations": dict(skills.most_common()),
        "slash_commands": dict(commands.most_common()),
        "subagent_types": dict(subagents.most_common()),
        "errors": _error_signals(result),
        "user_messages": {
            "count": len(message_lengths),
            "avg_chars": round(mean(message_lengths), 1) if message_lengths else 0.0,
            "max_chars": max(message_lengths) if message_lengths else 0,
        },
        "tokens": {
            **dict(usage_totals),
            "input_total": input_total,
            "cache_read_percent": cache_pct,
        },
    }


def _error_signals(result: Mapping[str, Any]) -> dict[str, Any]:
    session_by_id = {s.get("id"): s for s in result.get("sessions", [])}
    groups: dict[tuple[str, str, str], dict[str, Any]] = {}
    total_raw = 0

    for event in result.get("events", []):
        if event.get("type") != "error":
            continue
        total_raw += 1
        payload = event.get("payload") if isinstance(event.get("payload"), Mapping) else {}
        category = str(payload.get("category") or "unknown")
        subtype = str(payload.get("subtype") or "unknown")
        tool = str(payload.get("tool") or "unknown")
        key = (category, subtype, tool)
        item = groups.setdefault(
            key,
            {
                "category": category,
                "subtype": subtype,
                "tool": tool,
                "raw_occurrences": 0,
                "_sessions": set(),
                "_lineages": set(),
            },
        )
        item["raw_occurrences"] += 1
        session_id = event.get("session_id")
        if isinstance(session_id, str):
            item["_sessions"].add(session_id)
            session = session_by_id.get(session_id, {})
            root = session.get("root_lineage_id")
            if isinstance(root, str):
                item["_lineages"].add(root)

    output = []
    for item in groups.values():
        output.append(
            {
                "category": item["category"],
                "subtype": item["subtype"],
                "tool": item["tool"],
                "raw_occurrences": item["raw_occurrences"],
                "unique_sessions": len(item["_sessions"]),
                "unique_root_lineages": len(item["_lineages"]),
            }
        )
    output.sort(
        key=lambda item: (
            -item["raw_occurrences"],
            item["category"],
            item["subtype"],
            item["tool"],
        )
    )
    return {"total_raw_occurrences": total_raw, "groups": output}


def _summarize_diagnostics(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []

    grouped: dict[tuple[str, str, bool], dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, Mapping):
            continue
        code = str(item.get("code") or "unknown")
        severity = str(item.get("severity") or "warning")
        recoverable = bool(item.get("recoverable"))
        key = (code, severity, recoverable)
        group = grouped.setdefault(
            key,
            {
                "code": code,
                "severity": severity,
                "recoverable": recoverable,
                "count": 0,
                "message": str(item.get("message") or code),
            },
        )
        group["count"] += 1

    return sorted(
        grouped.values(),
        key=lambda item: (-item["count"], item["code"], item["severity"]),
    )

def _environment_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    models: set[str] = set()
    harness_versions: set[str] = set()
    for session in result.get("sessions", []):
        model = session.get("model")
        if isinstance(model, Mapping) and isinstance(model.get("name"), str):
            models.add(model["name"])
        harness = session.get("harness")
        if isinstance(harness, Mapping) and isinstance(harness.get("version"), str):
            harness_versions.add(harness["version"])
    return {
        "models": sorted(models),
        "harness_versions": sorted(harness_versions),
    }


def _environment_changes(
    previous: Mapping[str, Any] | None, result: Mapping[str, Any]
) -> list[dict[str, Any]]:
    if not previous:
        return []
    previous_env = previous.get("environment", {})
    current_env = _environment_summary(result)
    changes: list[dict[str, Any]] = []
    for key in ("models", "harness_versions"):
        before = previous_env.get(key) if isinstance(previous_env, Mapping) else None
        after = current_env.get(key)
        if before != after:
            changes.append({"field": key, "previous": before or [], "current": after or []})
    return changes


def _ledger_summary(ledger: Mapping[str, Any]) -> dict[str, Any]:
    problems = list(ledger.get("problems", []))
    lifecycle = Counter(str(p.get("lifecycle", "unknown")) for p in problems)
    revalidation = sum(
        1
        for p in problems
        if isinstance(p.get("revalidation"), Mapping)
        and p["revalidation"].get("state") == "needs-revalidation"
    )
    interventions = sum(len(p.get("interventions", [])) for p in problems)
    return {
        "problem_count": len(problems),
        "by_lifecycle": dict(sorted(lifecycle.items())),
        "intervention_count": interventions,
        "needs_revalidation": revalidation,
    }


def _evidence(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    session_by_id = {s.get("id"): s for s in result.get("sessions", [])}
    out: list[dict[str, Any]] = []
    for event in result.get("events", []):
        event_type = event.get("type")
        history_role = event.get("history_role")
        if event_type == "error":
            if history_role not in {"observed", "inherited", "replayed"}:
                continue
        elif history_role not in {"observed", "inherited"}:
            continue
        if not (
            event.get("fingerprint")
            or event_type in {"skill.invoke", "command.invoke", "subagent.invoke"}
        ):
            continue

        session = session_by_id.get(event.get("session_id"), {})
        payload = event.get("payload") if isinstance(event.get("payload"), Mapping) else {}
        evidence = {
            "id": event.get("id"),
            "kind": event_type,
            "session_id": event.get("session_id"),
            "fingerprint": event.get("fingerprint"),
            "observed_at": event.get("timestamp"),
            "root_lineage_id": session.get("root_lineage_id"),
            "source": event.get("provenance", {}).get("source"),
            "source_event_id": event.get("id"),
            "history_role": event.get("history_role"),
            "environment": {
                "model": session.get("model", {}).get("name")
                if isinstance(session.get("model"), Mapping)
                else None,
                "model_family": session.get("model", {}).get("family")
                if isinstance(session.get("model"), Mapping)
                else None,
                "harness": session.get("harness", {}).get("name")
                if isinstance(session.get("harness"), Mapping)
                else None,
                "harness_version": session.get("harness", {}).get("version")
                if isinstance(session.get("harness"), Mapping)
                else None,
            },
        }
        if event_type == "error":
            evidence["category"] = str(payload.get("category") or "unknown")
            evidence["subtype"] = str(payload.get("subtype") or "unknown")
            evidence["tool"] = str(payload.get("tool") or "unknown")
        out.append(evidence)
    return out


def _same_path(value: str, target: Path) -> bool:
    try:
        left = os.path.normcase(os.path.realpath(os.path.expanduser(value)))
        right = os.path.normcase(os.path.realpath(str(target)))
        return left == right
    except OSError:
        return False


def _is_child_transcript(path: Path) -> bool:
    return "subagents" in path.parts or "workflows" in path.parts


def _event_time(value: Any) -> datetime:
    if not isinstance(value, str):
        return datetime.min.replace(tzinfo=timezone.utc)
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
