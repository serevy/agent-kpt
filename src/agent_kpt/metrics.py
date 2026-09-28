from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

SCHEMA_VERSION = "agent-kpt.core/v0alpha1"


def compute_metrics(adapter_result: Mapping[str, Any], *, report_timezone: str = "UTC") -> dict[str, Any]:
    if report_timezone in {"UTC", "Etc/UTC", "GMT"}:
        zone = timezone.utc
    else:
        try:
            zone = ZoneInfo(report_timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(
                f"unknown timezone: {report_timezone}; install tzdata on platforms without an IANA database"
            ) from exc

    sessions = list(adapter_result.get("sessions", []))
    events = list(adapter_result.get("events", []))
    diagnostics = list(adapter_result.get("diagnostics", []))
    session_by_id = {session["id"]: session for session in sessions}

    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for event in events:
        fingerprint = event.get("fingerprint")
        if isinstance(fingerprint, str) and fingerprint:
            grouped[fingerprint].append(event)

    recurrence: dict[str, Any] = {}
    for fingerprint, fingerprint_events in sorted(grouped.items()):
        session_ids = {event["session_id"] for event in fingerprint_events}
        root_ids = {
            session_by_id[event["session_id"]]["root_lineage_id"]
            for event in fingerprint_events
            if event.get("session_id") in session_by_id
        }
        day_keys: set[str] = set()
        week_keys: set[str] = set()
        for event in fingerprint_events:
            dt = _parse_event_time(event["timestamp"]).astimezone(zone)
            day_keys.add(dt.date().isoformat())
            iso_year, iso_week, _ = dt.isocalendar()
            week_keys.add(f"{iso_year}-W{iso_week:02d}")
        recurrence[fingerprint] = {
            "raw_occurrences": len(fingerprint_events),
            "unique_sessions": len(session_ids),
            "unique_root_lineages": len(root_ids),
            "distinct_days": len(day_keys),
            "distinct_weeks": len(week_keys),
        }

    model_calls = [event for event in events if event.get("type") == "model.call"]
    role_counts = defaultdict(int)
    for event in model_calls:
        role_counts[event.get("history_role", "observed")] += 1

    recoverable = sum(1 for item in diagnostics if bool(item.get("recoverable")))
    fatal = sum(1 for item in diagnostics if not bool(item.get("recoverable")))

    return {
        "schema_version": SCHEMA_VERSION,
        "report_timezone": report_timezone,
        "session_metrics": {
            "raw_sessions": len(sessions),
            "unique_root_lineages": len({session["root_lineage_id"] for session in sessions}),
        },
        "recurrence": recurrence,
        "model_calls": {
            "raw_model_call_events": len(model_calls),
            "actual_new_model_calls": role_counts["observed"],
            "inherited_model_call_events": role_counts["inherited"],
            "replayed_model_call_events": role_counts["replayed"],
        },
        "adapter_diagnostics": {
            "recoverable": recoverable,
            "fatal": fatal,
        },
    }


def render_metrics_markdown(metrics: Mapping[str, Any]) -> str:
    session_metrics = metrics["session_metrics"]
    model_calls = metrics["model_calls"]
    diagnostics = metrics["adapter_diagnostics"]
    lines = [
        "# agent-kpt deterministic metrics",
        "",
        f"> Report timezone: `{metrics.get('report_timezone', 'UTC')}`",
        "",
        "## Sessions",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Raw sessions | {session_metrics['raw_sessions']} |",
        f"| Unique root lineages | {session_metrics['unique_root_lineages']} |",
        "",
        "## Model calls",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Raw model-call events | {model_calls['raw_model_call_events']} |",
        f"| Actual new calls | {model_calls['actual_new_model_calls']} |",
        f"| Inherited history events | {model_calls['inherited_model_call_events']} |",
        f"| Replayed history events | {model_calls['replayed_model_call_events']} |",
        "",
        "## Recurrence",
        "",
    ]

    recurrence = metrics.get("recurrence", {})
    if not recurrence:
        lines.extend(["No fingerprinted recurrence events.", ""])
    else:
        for fingerprint, item in recurrence.items():
            lines.extend(
                [
                    f"### `{fingerprint}`",
                    "",
                    "| Metric | Value |",
                    "| --- | ---: |",
                    f"| Raw occurrences | {item['raw_occurrences']} |",
                    f"| Unique sessions | {item['unique_sessions']} |",
                    f"| Unique root lineages | {item['unique_root_lineages']} |",
                    f"| Distinct days | {item['distinct_days']} |",
                    f"| Distinct weeks | {item['distinct_weeks']} |",
                    "",
                ]
            )

    lines.extend(
        [
            "## Adapter diagnostics",
            "",
            f"- Recoverable: **{diagnostics['recoverable']}**",
            f"- Fatal: **{diagnostics['fatal']}**",
            "",
        ]
    )
    return "\n".join(lines)


def _parse_event_time(value: str) -> datetime:
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    return datetime.fromisoformat(candidate)
