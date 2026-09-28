from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from agent_kpt import __version__

SCHEMA_VERSION = "agent-kpt.core/v0alpha1"
ADAPTER_NAME = "claude-code-jsonl"
KNOWN_IGNORED_TYPES = {
    "ai-title",
    "attachment",
    "deferred_tools_delta",
    "file-history-snapshot",
    "last-prompt",
    "mcp_instructions_delta",
    "mode",
    "progress",
    "queue-operation",
    "summary",
    "system",
}


def load_lineage_map(path: str | Path) -> dict[str, dict[str, str | None]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("lineage map must be a JSON object keyed by session id")
    result: dict[str, dict[str, str | None]] = {}
    for session_id, value in data.items():
        if not isinstance(session_id, str) or not isinstance(value, dict):
            raise ValueError("lineage map entries must be objects keyed by string session ids")
        root = value.get("root_lineage_id", session_id)
        parent = value.get("parent_session_id")
        if not isinstance(root, str) or not root:
            raise ValueError(f"invalid root_lineage_id for {session_id}")
        if parent is not None and (not isinstance(parent, str) or not parent):
            raise ValueError(f"invalid parent_session_id for {session_id}")
        result[session_id] = {
            "root_lineage_id": root,
            "parent_session_id": parent,
        }
    return result


def ingest_paths(
    paths: Iterable[str | Path],
    *,
    lineage_map: Mapping[str, Mapping[str, str | None]] | None = None,
) -> dict[str, Any]:
    """Normalize one or more Claude Code JSONL session files.

    The on-disk Claude Code transcript format is intentionally treated as an
    unstable adapter boundary. Only known telemetry fields are copied into the
    normalized core. Raw prompt text, assistant text, tool input, and tool
    output are not copied.
    """

    lineage_map = lineage_map or {}
    loaded: list[tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]] = []

    for raw_path in sorted((Path(p) for p in paths), key=lambda p: p.as_posix()):
        loaded.append(_read_session(raw_path, lineage_map))

    sessions = [item[0] for item in loaded]
    diagnostics = [diag for item in loaded for diag in item[2]]

    session_by_id = {session["id"]: session for session in sessions}
    ordered_sessions = sorted(sessions, key=lambda s: _session_order_key(s, session_by_id))

    events_by_session = {item[0]["id"]: item[1] for item in loaded}
    events: list[dict[str, Any]] = []
    seen_source_keys: dict[str, tuple[str, str]] = {}

    for session in ordered_sessions:
        session_events = sorted(
            events_by_session.get(session["id"], []),
            key=lambda e: (
                e["timestamp"],
                e["provenance"].get("source_index") if e["provenance"].get("source_index") is not None else -1,
                e["id"],
            ),
        )
        for event in session_events:
            source_key = event.pop("_source_key", None)
            if source_key and source_key in seen_source_keys:
                source_event_id, source_session_id = seen_source_keys[source_key]
                source_session = session_by_id.get(source_session_id)
                if source_session_id == session["id"]:
                    event["history_role"] = "replayed"
                elif source_session and source_session["root_lineage_id"] == session["root_lineage_id"]:
                    event["history_role"] = "inherited"
                else:
                    event["history_role"] = "replayed"
                event["source_event_id"] = source_event_id
            else:
                event["history_role"] = "observed"
                if source_key:
                    seen_source_keys[source_key] = (event["id"], session["id"])
            events.append(event)

    return {
        "schema_version": SCHEMA_VERSION,
        "sessions": sorted(sessions, key=lambda s: s["id"]),
        "events": events,
        "diagnostics": diagnostics,
    }


def _read_session(
    path: Path,
    lineage_map: Mapping[str, Mapping[str, str | None]],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    session_id = path.stem
    records: list[tuple[int, dict[str, Any]]] = []
    diagnostics: list[dict[str, Any]] = []

    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        raise ValueError(f"unable to read {path}: {exc}") from exc

    for index, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            diagnostics.append(_diagnostic("warning", "invalid-json-line", "Invalid JSON line was skipped.", True, index))
            continue
        if not isinstance(value, dict):
            diagnostics.append(_diagnostic("warning", "unsupported-record-shape", "Non-object record was skipped.", True, index))
            continue
        records.append((index, value))

    timestamps = [_parse_timestamp(record.get("timestamp")) for _, record in records]
    timestamps = [value for value in timestamps if value is not None]
    if timestamps:
        started_at = min(timestamps)
        ended_at = max(timestamps)
    else:
        started_at = "1970-01-01T00:00:00Z"
        ended_at = None
        diagnostics.append(_diagnostic("warning", "missing-session-timestamp", "Session had no parseable timestamp; epoch sentinel was used.", True, None))

    versions = [record.get("version") for _, record in records if isinstance(record.get("version"), str) and record.get("version")]
    version = Counter(versions).most_common(1)[0][0] if versions else None

    models: list[str] = []
    for _, record in records:
        if record.get("type") != "assistant":
            continue
        message = record.get("message")
        if isinstance(message, dict) and isinstance(message.get("model"), str) and message.get("model"):
            models.append(message["model"])
    model_name = Counter(models).most_common(1)[0][0] if models else None

    lineage = lineage_map.get(session_id, {})
    root_lineage_id = lineage.get("root_lineage_id") or session_id
    parent_session_id = lineage.get("parent_session_id")

    session: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "id": session_id,
        "root_lineage_id": root_lineage_id,
        "parent_session_id": parent_session_id,
        "provider": "anthropic",
        "harness": {"name": "claude-code", "version": version},
        "model": {"name": model_name, "family": "claude"} if model_name else None,
        "started_at": started_at,
        "ended_at": ended_at,
        "environment": {},
        "provenance": {
            "adapter": ADAPTER_NAME,
            "adapter_version": __version__,
            "source": path.name,
            "source_id": session_id,
        },
    }

    events: list[dict[str, Any]] = []
    for index, record in records:
        events.extend(_events_from_record(session_id, record, index, diagnostics, path.name))

    return session, events, diagnostics


def _events_from_record(
    session_id: str,
    record: dict[str, Any],
    source_index: int,
    diagnostics: list[dict[str, Any]],
    source_name: str,
) -> list[dict[str, Any]]:
    record_type = record.get("type")
    if not isinstance(record_type, str):
        diagnostics.append(_diagnostic("warning", "unsupported-record-shape", "Record without a string type was skipped.", True, source_index))
        return []

    timestamp = _parse_timestamp(record.get("timestamp"))
    if record_type in KNOWN_IGNORED_TYPES:
        return []
    if timestamp is None:
        diagnostics.append(_diagnostic("warning", "missing-event-timestamp", f"{record_type} record without a parseable timestamp was skipped.", True, source_index))
        return []

    if record_type == "assistant":
        return _assistant_events(session_id, record, source_index, timestamp, source_name)
    if record_type == "user":
        return _user_events(session_id, record, source_index, timestamp, source_name)
    if record_type == "tool_result":
        return [_tool_result_event(session_id, record, source_index, timestamp, source_name)]
    if record_type == "tool_error":
        return [_tool_error_event(session_id, record, source_index, timestamp, source_name)]

    diagnostics.append(_diagnostic("warning", "unsupported-record-shape", f"Unknown record type '{record_type}' was skipped.", True, source_index))
    return []


def _assistant_events(session_id: str, record: dict[str, Any], source_index: int, timestamp: str, source_name: str) -> list[dict[str, Any]]:
    message = record.get("message") if isinstance(record.get("message"), dict) else {}
    model = message.get("model") if isinstance(message.get("model"), str) else None
    usage = message.get("usage") if isinstance(message.get("usage"), dict) else {}
    safe_usage = {
        key: value
        for key in (
            "input_tokens",
            "output_tokens",
            "cache_creation_input_tokens",
            "cache_read_input_tokens",
        )
        if isinstance((value := usage.get(key)), (int, float)) and not isinstance(value, bool)
    }

    events = [
        _event(
            session_id,
            record,
            source_index,
            timestamp,
            "model.call",
            {"model": model, "usage": safe_usage},
            source_name,
            suffix="model-call",
        )
    ]

    content = message.get("content")
    if isinstance(content, list):
        for block_index, block in enumerate(content):
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            name = block.get("name") if isinstance(block.get("name"), str) else None
            tool_id = block.get("id") if isinstance(block.get("id"), str) else None
            events.append(
                _event(
                    session_id,
                    record,
                    source_index,
                    timestamp,
                    "tool.use",
                    {"name": name, "tool_use_id": tool_id},
                    source_name,
                    suffix=f"tool-use-{block_index}",
                )
            )
    return events


def _user_events(session_id: str, record: dict[str, Any], source_index: int, timestamp: str, source_name: str) -> list[dict[str, Any]]:
    message = record.get("message") if isinstance(record.get("message"), dict) else {}
    content = message.get("content")
    events = [
        _event(
            session_id,
            record,
            source_index,
            timestamp,
            "user.message",
            _content_shape(content),
            source_name,
            suffix="user-message",
        )
    ]

    if isinstance(content, list):
        for block_index, block in enumerate(content):
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            is_error = bool(block.get("is_error"))
            tool_use_id = block.get("tool_use_id") if isinstance(block.get("tool_use_id"), str) else None
            error_type = block.get("error_type") if isinstance(block.get("error_type"), str) else None
            events.append(
                _event(
                    session_id,
                    record,
                    source_index,
                    timestamp,
                    "error" if is_error else "tool.result",
                    {"tool_use_id": tool_use_id, "is_error": is_error},
                    source_name,
                    suffix=f"tool-result-{block_index}",
                    fingerprint=_error_fingerprint(error_type or "tool-result") if is_error else None,
                )
            )
    return events


def _tool_result_event(session_id: str, record: dict[str, Any], source_index: int, timestamp: str, source_name: str) -> dict[str, Any]:
    is_error = bool(record.get("is_error"))
    tool_use_id = record.get("tool_use_id") if isinstance(record.get("tool_use_id"), str) else None
    error_type = record.get("error_type") if isinstance(record.get("error_type"), str) else None
    return _event(
        session_id,
        record,
        source_index,
        timestamp,
        "error" if is_error else "tool.result",
        {"tool_use_id": tool_use_id, "is_error": is_error},
        source_name,
        suffix="tool-result",
        fingerprint=_error_fingerprint(error_type or "tool-result") if is_error else None,
    )


def _tool_error_event(session_id: str, record: dict[str, Any], source_index: int, timestamp: str, source_name: str) -> dict[str, Any]:
    error_type = None
    for key in ("errorType", "error_type", "code"):
        value = record.get(key)
        if isinstance(value, str) and value:
            error_type = value
            break
    tool_name = record.get("tool") if isinstance(record.get("tool"), str) else None
    tool_use_id = record.get("tool_use_id") if isinstance(record.get("tool_use_id"), str) else None
    return _event(
        session_id,
        record,
        source_index,
        timestamp,
        "error",
        {"tool": tool_name, "tool_use_id": tool_use_id},
        source_name,
        suffix="tool-error",
        fingerprint=_error_fingerprint(error_type or "tool"),
    )


def _event(
    session_id: str,
    record: dict[str, Any],
    source_index: int,
    timestamp: str,
    event_type: str,
    payload: dict[str, Any],
    source_name: str,
    *,
    suffix: str,
    fingerprint: str | None = None,
) -> dict[str, Any]:
    record_uuid = record.get("uuid") if isinstance(record.get("uuid"), str) and record.get("uuid") else None
    record_identity = record_uuid or f"line-{source_index}"
    source_key = f"{record_uuid}:{suffix}" if record_uuid else None
    return {
        "schema_version": SCHEMA_VERSION,
        "id": f"{session_id}:{record_identity}:{suffix}",
        "session_id": session_id,
        "timestamp": timestamp,
        "type": event_type,
        "history_role": "observed",
        "fingerprint": fingerprint,
        "source_event_id": None,
        "payload": payload,
        "provenance": {
            "adapter": ADAPTER_NAME,
            "adapter_version": __version__,
            "source": source_name,
            "source_index": source_index,
        },
        "_source_key": source_key,
    }


def _content_shape(content: Any) -> dict[str, Any]:
    if isinstance(content, str):
        return {"content_kind": "string", "block_count": 1, "text_chars": len(content)}
    if isinstance(content, list):
        block_types: Counter[str] = Counter()
        text_chars = 0
        for block in content:
            if not isinstance(block, dict):
                block_types["unknown"] += 1
                continue
            block_type = block.get("type") if isinstance(block.get("type"), str) else "unknown"
            block_types[block_type] += 1
            text = block.get("text")
            if isinstance(text, str):
                text_chars += len(text)
        return {
            "content_kind": "blocks",
            "block_count": len(content),
            "block_types": dict(sorted(block_types.items())),
            "text_chars": text_chars,
        }
    return {"content_kind": "unknown", "block_count": 0, "text_chars": 0}


def _diagnostic(severity: str, code: str, message: str, recoverable: bool, source_index: int | None) -> dict[str, Any]:
    return {
        "severity": severity,
        "code": code,
        "message": message,
        "recoverable": recoverable,
        "source_index": source_index,
    }


def _error_fingerprint(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-") or "unknown"
    return f"error:{slug}"


def _parse_timestamp(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    parsed = parsed.astimezone(timezone.utc)
    return parsed.isoformat().replace("+00:00", "Z")


def _session_order_key(session: Mapping[str, Any], session_by_id: Mapping[str, Mapping[str, Any]]) -> tuple[Any, ...]:
    depth = 0
    current = session
    seen: set[str] = set()
    while current.get("parent_session_id"):
        parent_id = current["parent_session_id"]
        if not isinstance(parent_id, str) or parent_id in seen:
            break
        seen.add(parent_id)
        depth += 1
        parent = session_by_id.get(parent_id)
        if parent is None:
            break
        current = parent
    return (session["root_lineage_id"], depth, session["started_at"], session["id"])
