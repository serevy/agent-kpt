from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
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
        result[session_id] = {"root_lineage_id": root, "parent_session_id": parent}
    return result


def infer_lineage_map(paths: Iterable[str | Path]) -> dict[str, dict[str, str | None]]:
    """Infer lineage from shared serialized entry UUIDs and parent transcript paths."""
    scans = [_scan_identity(Path(path)) for path in paths]
    by_id = {scan["session_id"]: scan for scan in scans}
    parent: dict[str, str] = {sid: sid for sid in by_id}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        if a not in parent or b not in parent:
            return
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    uuid_owner: dict[str, str] = {}
    for scan in scans:
        sid = scan["session_id"]
        parent_sid = scan.get("parent_session_id")
        if isinstance(parent_sid, str):
            union(sid, parent_sid)
        for uuid in scan["uuids"]:
            other = uuid_owner.get(uuid)
            if other is None:
                uuid_owner[uuid] = sid
            else:
                union(sid, other)

    components: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for scan in scans:
        components[find(scan["session_id"])].append(scan)

    result: dict[str, dict[str, str | None]] = {}
    for members in components.values():
        uuid_candidates: list[tuple[str, str]] = []
        for member in members:
            for uuid, ts in member.get("uuid_times", {}).items():
                uuid_candidates.append((ts, uuid))
        if uuid_candidates:
            _, seed_uuid = min(uuid_candidates)
            digest = hashlib.sha256(seed_uuid.encode("utf-8")).hexdigest()[:12]
            root = f"lineage-{digest}"
        else:
            mains = [m for m in members if not m.get("parent_session_id")]
            candidates = mains or members
            root = min(
                candidates,
                key=lambda m: (
                    m.get("started_at") or "9999-12-31T23:59:59Z",
                    m["session_id"],
                ),
            )["session_id"]
        for member in members:
            result[member["session_id"]] = {
                "root_lineage_id": root,
                "parent_session_id": member.get("parent_session_id"),
            }
    return result


def ingest_paths(
    paths: Iterable[str | Path],
    *,
    lineage_map: Mapping[str, Mapping[str, str | None]] | None = None,
) -> dict[str, Any]:
    """Normalize Claude Code JSONL without persisting raw conversational content."""
    normalized_paths = sorted((Path(p) for p in paths), key=lambda p: p.as_posix())
    inferred = infer_lineage_map(normalized_paths)
    if lineage_map:
        inferred.update({key: dict(value) for key, value in lineage_map.items()})

    loaded: list[tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]] = []
    for raw_path in normalized_paths:
        loaded.append(_read_session(raw_path, inferred))

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
                e["provenance"].get("source_index")
                if e["provenance"].get("source_index") is not None
                else -1,
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
                elif (
                    source_session
                    and source_session["root_lineage_id"] == session["root_lineage_id"]
                ):
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


def inspect_transcript(path: str | Path) -> dict[str, Any]:
    """Return privacy-safe discovery metadata for one transcript."""
    p = Path(path)
    cwd = None
    earliest = None
    latest = None
    try:
        with p.open("r", encoding="utf-8-sig") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict):
                    continue
                if cwd is None and isinstance(record.get("cwd"), str):
                    cwd = record["cwd"]
                ts = _parse_timestamp(record.get("timestamp"))
                if ts:
                    earliest = min(earliest, ts) if earliest else ts
                    latest = max(latest, ts) if latest else ts
    except OSError as exc:
        raise ValueError(f"unable to read {p}: {exc}") from exc
    return {
        "path": p,
        "session_id": p.stem,
        "cwd": cwd,
        "started_at": earliest,
        "ended_at": latest,
        "parent_session_id": _parent_session_id_from_path(p),
    }


def _scan_identity(path: Path) -> dict[str, Any]:
    uuids: set[str] = set()
    uuid_times: dict[str, str] = {}
    started_at = None
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict):
                    continue
                uuid = record.get("uuid")
                ts = _parse_timestamp(record.get("timestamp"))
                if isinstance(uuid, str) and uuid:
                    uuids.add(uuid)
                    if ts and (uuid not in uuid_times or ts < uuid_times[uuid]):
                        uuid_times[uuid] = ts
                if ts:
                    started_at = min(started_at, ts) if started_at else ts
    except OSError as exc:
        raise ValueError(f"unable to read {path}: {exc}") from exc
    return {
        "session_id": path.stem,
        "parent_session_id": _parent_session_id_from_path(path),
        "uuids": uuids,
        "uuid_times": uuid_times,
        "started_at": started_at,
    }


def _parent_session_id_from_path(path: Path) -> str | None:
    parts = path.parts
    for marker in ("subagents", "workflows"):
        if marker in parts:
            idx = parts.index(marker)
            if idx > 0:
                return parts[idx - 1]
    return None


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
            diagnostics.append(
                _diagnostic(
                    "warning",
                    "invalid-json-line",
                    "Invalid JSON line was skipped.",
                    True,
                    index,
                )
            )
            continue
        if not isinstance(value, dict):
            diagnostics.append(
                _diagnostic(
                    "warning",
                    "unsupported-record-shape",
                    "Non-object record was skipped.",
                    True,
                    index,
                )
            )
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
        diagnostics.append(
            _diagnostic(
                "warning",
                "missing-session-timestamp",
                "Session had no parseable timestamp; epoch sentinel was used.",
                True,
                None,
            )
        )

    versions = [
        record.get("version")
        for _, record in records
        if isinstance(record.get("version"), str) and record.get("version")
    ]
    version = Counter(versions).most_common(1)[0][0] if versions else None

    models: list[str] = []
    for _, record in records:
        if record.get("type") != "assistant":
            continue
        message = record.get("message")
        if (
            isinstance(message, dict)
            and isinstance(message.get("model"), str)
            and message.get("model")
        ):
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
        events.extend(
            _events_from_record(session_id, record, index, diagnostics, path.name)
        )
    events = _collapse_model_calls(events)
    _attach_tool_names(events)
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
        diagnostics.append(
            _diagnostic(
                "warning",
                "unsupported-record-shape",
                "Record without a string type was skipped.",
                True,
                source_index,
            )
        )
        return []

    timestamp = _parse_timestamp(record.get("timestamp"))
    if record_type in KNOWN_IGNORED_TYPES:
        return []
    if timestamp is None:
        diagnostics.append(
            _diagnostic(
                "warning",
                "missing-event-timestamp",
                f"{record_type} record without a parseable timestamp was skipped.",
                True,
                source_index,
            )
        )
        return []

    if record_type == "assistant":
        return _assistant_events(session_id, record, source_index, timestamp, source_name)
    if record_type == "user":
        return _user_events(session_id, record, source_index, timestamp, source_name)
    if record_type == "tool_result":
        return [
            _tool_result_event(
                session_id, record, source_index, timestamp, source_name
            )
        ]
    if record_type == "tool_error":
        return [
            _tool_error_event(
                session_id, record, source_index, timestamp, source_name
            )
        ]

    diagnostics.append(
        _diagnostic(
            "warning",
            "unsupported-record-shape",
            f"Unknown record type '{record_type}' was skipped.",
            True,
            source_index,
        )
    )
    return []


def _assistant_events(
    session_id: str,
    record: dict[str, Any],
    source_index: int,
    timestamp: str,
    source_name: str,
) -> list[dict[str, Any]]:
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
        if isinstance((value := usage.get(key)), (int, float))
        and not isinstance(value, bool)
    }
    call_key = _assistant_call_key(record, message, source_index)

    events: list[dict[str, Any]] = []
    if safe_usage:
        event = _event(
            session_id,
            record,
            source_index,
            timestamp,
            "model.call",
            {"model": model, "usage": safe_usage},
            source_name,
            suffix="model-call",
            source_key=f"model-call:{call_key}",
        )
        event["_call_key"] = call_key
        events.append(event)

    content = message.get("content")
    if isinstance(content, list):
        for block_index, block in enumerate(content):
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            name = block.get("name") if isinstance(block.get("name"), str) else None
            tool_id = block.get("id") if isinstance(block.get("id"), str) else None
            input_data = block.get("input") if isinstance(block.get("input"), dict) else {}
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
            if name == "Skill" and isinstance(input_data.get("skill"), str):
                events.append(
                    _event(
                        session_id,
                        record,
                        source_index,
                        timestamp,
                        "skill.invoke",
                        {"name": input_data["skill"]},
                        source_name,
                        suffix=f"skill-{block_index}",
                    )
                )
            if name in {"Agent", "Task"} and isinstance(
                input_data.get("subagent_type"), str
            ):
                events.append(
                    _event(
                        session_id,
                        record,
                        source_index,
                        timestamp,
                        "subagent.invoke",
                        {"type": input_data["subagent_type"]},
                        source_name,
                        suffix=f"subagent-{block_index}",
                    )
                )
    return events


def _assistant_call_key(
    record: Mapping[str, Any], message: Mapping[str, Any], source_index: int
) -> str:
    for value in (record.get("requestId"), message.get("id"), record.get("uuid")):
        if isinstance(value, str) and value:
            return value
    return f"line-{source_index}"


def _collapse_model_calls(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    output: list[dict[str, Any]] = []
    for event in events:
        if event.get("type") != "model.call":
            output.append(event)
            continue
        call_key = event.pop("_call_key", None)
        if not isinstance(call_key, str):
            output.append(event)
            continue
        existing = grouped.get(call_key)
        if existing is None:
            grouped[call_key] = event
            output.append(event)
            continue
        existing_usage = existing["payload"].setdefault("usage", {})
        incoming_usage = event.get("payload", {}).get("usage", {})
        if isinstance(incoming_usage, dict):
            for key, value in incoming_usage.items():
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    existing_usage[key] = max(existing_usage.get(key, 0), value)
        if (
            not existing["payload"].get("model")
            and event.get("payload", {}).get("model")
        ):
            existing["payload"]["model"] = event["payload"]["model"]
    return output


def _user_events(
    session_id: str,
    record: dict[str, Any],
    source_index: int,
    timestamp: str,
    source_name: str,
) -> list[dict[str, Any]]:
    message = record.get("message") if isinstance(record.get("message"), dict) else {}
    content = message.get("content")
    events: list[dict[str, Any]] = []

    if not record.get("isMeta") and not record.get("isCompactSummary"):
        text = _extract_user_text(content)
        is_tool_result = (
            isinstance(content, list)
            and bool(content)
            and isinstance(content[0], dict)
            and content[0].get("type") == "tool_result"
        )
        is_interrupt = isinstance(text, str) and text.startswith("[Request interrupted")
        if not is_tool_result and not is_interrupt:
            events.append(
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
            )
            command = _extract_command_name(text)
            if command:
                events.append(
                    _event(
                        session_id,
                        record,
                        source_index,
                        timestamp,
                        "command.invoke",
                        {"name": command},
                        source_name,
                        suffix="command",
                    )
                )

    if isinstance(content, list):
        for block_index, block in enumerate(content):
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            is_error = bool(block.get("is_error"))
            tool_use_id = (
                block.get("tool_use_id")
                if isinstance(block.get("tool_use_id"), str)
                else None
            )
            error_type = (
                block.get("error_type")
                if isinstance(block.get("error_type"), str)
                else None
            )
            payload: dict[str, Any] = {
                "tool_use_id": tool_use_id,
                "is_error": is_error,
            }
            fingerprint = None
            if is_error:
                category, subtype = _classify_error(
                    error_type=error_type,
                    text=_extract_error_text(block.get("content")),
                )
                payload["category"] = category
                payload["subtype"] = subtype
                fingerprint = _classified_error_fingerprint(category, subtype)
            events.append(
                _event(
                    session_id,
                    record,
                    source_index,
                    timestamp,
                    "error" if is_error else "tool.result",
                    payload,
                    source_name,
                    suffix=f"tool-result-{block_index}",
                    fingerprint=fingerprint,
                )
            )
    return events


def _extract_user_text(content: Any) -> str | None:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for block in content:
            if (
                isinstance(block, dict)
                and block.get("type") == "text"
                and isinstance(block.get("text"), str)
            ):
                return block["text"]
    return None


def _extract_command_name(text: str | None) -> str | None:
    if not text:
        return None
    match = re.search(
        r"<command-(?:name|message)>\s*/?([^<]+)</command-(?:name|message)>",
        text,
    )
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def _tool_result_event(
    session_id: str,
    record: dict[str, Any],
    source_index: int,
    timestamp: str,
    source_name: str,
) -> dict[str, Any]:
    is_error = bool(record.get("is_error"))
    tool_use_id = (
        record.get("tool_use_id")
        if isinstance(record.get("tool_use_id"), str)
        else None
    )
    error_type = (
        record.get("error_type")
        if isinstance(record.get("error_type"), str)
        else None
    )
    payload: dict[str, Any] = {
        "tool_use_id": tool_use_id,
        "is_error": is_error,
    }
    fingerprint = None
    if is_error:
        category, subtype = _classify_error(
            error_type=error_type,
            text=_extract_error_text(record.get("content") or record.get("message")),
        )
        payload["category"] = category
        payload["subtype"] = subtype
        fingerprint = _classified_error_fingerprint(category, subtype)
    return _event(
        session_id,
        record,
        source_index,
        timestamp,
        "error" if is_error else "tool.result",
        payload,
        source_name,
        suffix="tool-result",
        fingerprint=fingerprint,
    )


def _tool_error_event(
    session_id: str,
    record: dict[str, Any],
    source_index: int,
    timestamp: str,
    source_name: str,
) -> dict[str, Any]:
    error_type = None
    for key in ("errorType", "error_type", "code"):
        value = record.get(key)
        if isinstance(value, str) and value:
            error_type = value
            break
    tool_name = record.get("tool") if isinstance(record.get("tool"), str) else None
    tool_use_id = (
        record.get("tool_use_id")
        if isinstance(record.get("tool_use_id"), str)
        else None
    )
    category, subtype = _classify_error(
        error_type=error_type,
        text=_extract_error_text(
            record.get("message")
            or record.get("error")
            or record.get("stderr")
            or record.get("content")
        ),
    )
    return _event(
        session_id,
        record,
        source_index,
        timestamp,
        "error",
        {
            "tool": tool_name,
            "tool_use_id": tool_use_id,
            "category": category,
            "subtype": subtype,
        },
        source_name,
        suffix="tool-error",
        fingerprint=_classified_error_fingerprint(category, subtype),
    )


def _attach_tool_names(events: list[dict[str, Any]]) -> None:
    tool_by_use_id: dict[str, str] = {}
    for event in events:
        if event.get("type") != "tool.use":
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        tool_use_id = payload.get("tool_use_id")
        name = payload.get("name")
        if isinstance(tool_use_id, str) and isinstance(name, str) and name:
            tool_by_use_id[tool_use_id] = name

    for event in events:
        if event.get("type") != "error":
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict) or payload.get("tool"):
            continue
        tool_use_id = payload.get("tool_use_id")
        if isinstance(tool_use_id, str) and tool_use_id in tool_by_use_id:
            payload["tool"] = tool_by_use_id[tool_use_id]


def _extract_error_text(value: Any) -> str:
    parts: list[str] = []

    def collect(item: Any) -> None:
        if isinstance(item, str):
            parts.append(item)
            return
        if isinstance(item, list):
            for child in item:
                collect(child)
            return
        if isinstance(item, dict):
            for key in ("text", "message", "error", "stderr", "content"):
                if key in item:
                    collect(item[key])

    collect(value)
    return "\n".join(parts)


def _classify_error(*, error_type: str | None, text: str) -> tuple[str, str]:
    haystack = f"{error_type or ''}\n{text}".lower()

    rules = [
        ("rate-limit", "rate-limit", ("rate limit", "too many requests", "429")),
        ("auth", "unauthorized", ("unauthorized", "authentication", "invalid token", "api key")),
        ("permission", "permission-denied", ("permission denied", "access denied", "eacces", "operation not permitted")),
        ("timeout", "timeout", ("timed out", "timeout", "deadline exceeded", "etimedout")),
        ("path", "path-quoting", ("path-quoting", "path quoting")),
        ("path", "file-not-found", ("no such file or directory", "file not found", "path not found", "cannot find path", "enoent")),
        ("path", "not-a-directory", ("not a directory", "enotdir")),
        ("dependency", "module-not-found", ("no module named", "module not found", "cannot find module")),
        ("dependency", "command-not-found", ("command not found", "is not recognized as an internal or external command", "executable not found")),
        ("syntax", "syntax-error", ("syntax error", "invalid syntax", "parse error", "unexpected token")),
        ("network", "connection-refused", ("connection refused", "econnrefused")),
        ("network", "dns", ("could not resolve host", "name or service not known", "getaddrinfo")),
        ("network", "network", ("network is unreachable", "enetunreach", "econnreset", "connection reset")),
    ]
    for category, subtype, patterns in rules:
        if any(pattern in haystack for pattern in patterns):
            return category, subtype
    return "unknown", "unknown"


def _classified_error_fingerprint(category: str, subtype: str) -> str:
    return f"error:{category}:{subtype}"


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
    source_key: str | None = None,
) -> dict[str, Any]:
    record_uuid = (
        record.get("uuid")
        if isinstance(record.get("uuid"), str) and record.get("uuid")
        else None
    )
    record_identity = record_uuid or f"line-{source_index}"
    if source_key is None:
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
        return {
            "content_kind": "string",
            "block_count": 1,
            "text_chars": len(content),
        }
    if isinstance(content, list):
        block_types: Counter[str] = Counter()
        text_chars = 0
        for block in content:
            if not isinstance(block, dict):
                block_types["unknown"] += 1
                continue
            block_type = (
                block.get("type") if isinstance(block.get("type"), str) else "unknown"
            )
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


def _diagnostic(
    severity: str,
    code: str,
    message: str,
    recoverable: bool,
    source_index: int | None,
) -> dict[str, Any]:
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
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _session_order_key(
    session: Mapping[str, Any],
    session_by_id: Mapping[str, Mapping[str, Any]],
) -> tuple[Any, ...]:
    depth = 0
    current = session
    seen: set[str] = set()
    while current.get("parent_session_id"):
        parent_id = current["parent_session_id"]
        if not isinstance(parent_id, str) or parent_id in seen:
            break
        seen.add(parent_id)
        depth += 1
        parent_session = session_by_id.get(parent_id)
        if parent_session is None:
            break
        current = parent_session
    return (
        session["root_lineage_id"],
        depth,
        session.get("ended_at") or session["started_at"],
        session["started_at"],
        session["id"],
    )
