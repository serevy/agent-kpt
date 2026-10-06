from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Mapping, MutableMapping

SCHEMA_VERSION = "agent-kpt.ledger/v0alpha1"
TARGET_TYPES = {
    "human",
    "agent",
    "skill-instruction",
    "script",
    "workflow",
    "config",
    "tooling",
    "environment",
    "documentation",
    "upstream",
    "observe-only",
}
INTERVENTION_STATUSES = {
    "not-started",
    "applied",
    "verifying",
    "effective",
    "ineffective",
    "revise",
    "retired",
}
DECISION_STATES = {"proposed", "accepted", "rejected", "deferred"}
KEEP_STATES = {"none", "reinforcing", "habituated", "graduated"}
ENVIRONMENT_KEYS = (
    "model",
    "model_family",
    "harness",
    "harness_version",
    "adapter",
    "adapter_version",
    "skill_config_version",
    "runtime",
    "os",
)


def new_ledger() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "problems": []}


def stable_problem_id(fingerprint: str) -> str:
    if not fingerprint:
        raise ValueError("fingerprint must not be empty")
    digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:12]
    return f"problem-{digest}"


def upsert_problem(
    ledger: MutableMapping[str, Any],
    *,
    fingerprint: str,
    title: str,
    target_type: str,
    observed_at: str,
    evidence: Mapping[str, Any],
) -> MutableMapping[str, Any]:
    if target_type not in TARGET_TYPES:
        raise ValueError(f"unsupported target_type: {target_type}")
    observed_at = _normalize_time(observed_at)
    problem_id = stable_problem_id(fingerprint)
    problems = ledger.setdefault("problems", [])
    problem = next((item for item in problems if item.get("id") == problem_id), None)

    if problem is None:
        problem = {
            "id": problem_id,
            "fingerprint": fingerprint,
            "title": title,
            "target_type": target_type,
            "lifecycle": "observed",
            "first_seen": observed_at,
            "last_seen": observed_at,
            "independent_root_lineages": 0,
            "evidence": [],
            "interventions": [],
            "keep": {
                "state": "none",
                "since": None,
                "habituated_at": None,
                "graduated_at": None,
            },
            "revalidation": {"state": "not-required", "reasons": []},
            "retirement_reason": None,
            "retired_at": None,
        }
        problems.append(problem)

    normalized_evidence = _normalize_evidence(problem_id, evidence, observed_at)
    evidence_ids = {item["id"] for item in problem["evidence"]}
    if normalized_evidence["id"] not in evidence_ids:
        problem["evidence"].append(normalized_evidence)

    problem["first_seen"] = min(problem["first_seen"], observed_at)
    problem["last_seen"] = max(problem["last_seen"], observed_at)
    root_lineages = {
        item.get("root_lineage_id")
        for item in problem["evidence"]
        if isinstance(item.get("root_lineage_id"), str) and item.get("root_lineage_id")
    }
    problem["independent_root_lineages"] = len(root_lineages)
    if problem["lifecycle"] == "observed" and len(root_lineages) >= 2:
        problem["lifecycle"] = "recurring"
    return problem


def add_intervention(
    problem: MutableMapping[str, Any],
    *,
    kind: str,
    summary: str,
    proposed_at: str,
    decision: str = "proposed",
) -> MutableMapping[str, Any]:
    if kind not in TARGET_TYPES:
        raise ValueError(f"unsupported intervention kind: {kind}")
    if decision not in DECISION_STATES:
        raise ValueError(f"unsupported decision: {decision}")

    proposed_at = _normalize_time(proposed_at)
    normalized_summary = _normalize_intervention_summary(summary)
    if not normalized_summary:
        raise ValueError("intervention summary must not be empty")

    interventions = problem.setdefault("interventions", [])
    existing = next(
        (
            item
            for item in interventions
            if item.get("kind") == kind
            and _normalize_intervention_summary(str(item.get("summary") or ""))
            == normalized_summary
        ),
        None,
    )
    if existing is not None:
        _record_reproposal(existing, proposed_at)
        return existing

    intervention_id = _stable_id(
        "intervention",
        str(problem["id"]),
        kind,
        normalized_summary,
    )
    intervention = {
        "id": intervention_id,
        "kind": kind,
        "summary": summary.strip(),
        "decision": decision,
        "status": "not-started",
        "proposed_at": proposed_at,
        "first_proposed_at": proposed_at,
        "last_proposed_at": proposed_at,
        "proposal_count": 1,
        "applied_at": None,
        "validated_at": None,
        "retired_at": None,
        "validated_environment": {},
        "retire_reason": None,
    }
    interventions.append(intervention)
    if decision == "accepted" and problem["lifecycle"] in {"observed", "recurring", "revise"}:
        problem["lifecycle"] = "try-proposed"
    return intervention


def _record_reproposal(intervention: MutableMapping[str, Any], proposed_at: str) -> None:
    original = intervention.get("proposed_at")
    original_time = (
        _normalize_time(original)
        if isinstance(original, str) and original
        else proposed_at
    )
    first_raw = intervention.get("first_proposed_at")
    first = (
        _normalize_time(first_raw)
        if isinstance(first_raw, str) and first_raw
        else original_time
    )
    last_raw = intervention.get("last_proposed_at")
    last = (
        _normalize_time(last_raw)
        if isinstance(last_raw, str) and last_raw
        else original_time
    )

    intervention["first_proposed_at"] = min(first, original_time, proposed_at)
    intervention["last_proposed_at"] = max(last, proposed_at)

    count = intervention.get("proposal_count")
    proposal_count = (
        count if isinstance(count, int) and not isinstance(count, bool) and count >= 1 else 1
    )
    if proposed_at > last:
        proposal_count += 1
    intervention["proposal_count"] = proposal_count


def _normalize_intervention_summary(summary: str) -> str:
    return " ".join(summary.split()).casefold()


def set_intervention_decision(
    problem: MutableMapping[str, Any], intervention_id: str, decision: str
) -> MutableMapping[str, Any]:
    if decision not in DECISION_STATES:
        raise ValueError(f"unsupported decision: {decision}")
    intervention = _find_intervention(problem, intervention_id)
    intervention["decision"] = decision
    if decision == "accepted" and problem["lifecycle"] in {"observed", "recurring", "revise"}:
        problem["lifecycle"] = "try-proposed"
    return intervention


def set_intervention_status(
    problem: MutableMapping[str, Any],
    intervention_id: str,
    status: str,
    *,
    at: str | None = None,
    environment: Mapping[str, Any] | None = None,
    retire_reason: str | None = None,
) -> MutableMapping[str, Any]:
    if status not in INTERVENTION_STATUSES:
        raise ValueError(f"unsupported intervention status: {status}")
    intervention = _find_intervention(problem, intervention_id)
    at = _normalize_time(at) if at else None
    intervention["status"] = status

    if status == "applied":
        intervention["applied_at"] = at
        problem["lifecycle"] = "intervention-applied"
    elif status == "verifying":
        problem["lifecycle"] = "verifying"
    elif status == "effective":
        intervention["validated_at"] = at
        intervention["validated_environment"] = normalize_environment(environment or {})
        problem["lifecycle"] = "keep"
        if problem["keep"]["state"] == "none":
            problem["keep"]["state"] = "reinforcing"
            problem["keep"]["since"] = at
        problem["revalidation"] = {"state": "current", "reasons": []}
    elif status == "ineffective":
        problem["lifecycle"] = "ineffective"
    elif status == "revise":
        problem["lifecycle"] = "revise"
    elif status == "retired":
        intervention["retired_at"] = at
        intervention["retire_reason"] = retire_reason
    return intervention


def set_keep_state(problem: MutableMapping[str, Any], state: str, *, at: str) -> None:
    if state not in KEEP_STATES:
        raise ValueError(f"unsupported keep state: {state}")
    at = _normalize_time(at)
    keep = problem["keep"]
    keep["state"] = state
    if state == "reinforcing":
        keep["since"] = keep.get("since") or at
        problem["lifecycle"] = "keep"
    elif state == "habituated":
        keep["habituated_at"] = at
        problem["lifecycle"] = "habituated"
    elif state == "graduated":
        keep["graduated_at"] = at
        problem["lifecycle"] = "graduated"
    elif state == "none":
        keep["since"] = None
        keep["habituated_at"] = None
        keep["graduated_at"] = None


def assess_revalidation(
    problem: MutableMapping[str, Any], current_environment: Mapping[str, Any]
) -> Mapping[str, Any]:
    effective = [
        item
        for item in problem.get("interventions", [])
        if item.get("status") == "effective" and item.get("validated_environment")
    ]
    if not effective:
        problem["revalidation"] = {"state": "not-required", "reasons": []}
        return problem["revalidation"]

    intervention = max(effective, key=lambda item: item.get("validated_at") or item.get("proposed_at") or "")
    before = normalize_environment(intervention.get("validated_environment") or {})
    current = normalize_environment(current_environment)
    reasons: list[dict[str, Any]] = []
    for key, previous in before.items():
        now = current.get(key)
        if now != previous:
            reasons.append({"field": key, "validated": previous, "current": now})

    state = "needs-revalidation" if reasons else "current"
    problem["revalidation"] = {"state": state, "reasons": reasons}
    return problem["revalidation"]


def retire_problem(problem: MutableMapping[str, Any], *, reason: str, at: str) -> None:
    problem["lifecycle"] = "retired"
    problem["retirement_reason"] = reason
    problem["retired_at"] = _normalize_time(at)


def normalize_environment(environment: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: environment[key]
        for key in ENVIRONMENT_KEYS
        if key in environment and isinstance(environment[key], (str, int, float, bool))
    }


def _normalize_evidence(problem_id: str, evidence: Mapping[str, Any], observed_at: str) -> dict[str, Any]:
    kind = evidence.get("kind", "event")
    source = evidence.get("source") if isinstance(evidence.get("source"), dict) else {}
    root_lineage_id = evidence.get("root_lineage_id")
    source_id = source.get("source_id") or source.get("event_id") or "unknown"
    evidence_id = evidence.get("id")
    if not isinstance(evidence_id, str) or not evidence_id:
        evidence_id = _stable_id(
            "evidence",
            problem_id,
            str(kind),
            str(source_id),
            str(root_lineage_id or ""),
            observed_at,
        )
    return {
        "id": evidence_id,
        "kind": str(kind),
        "observed_at": observed_at,
        "root_lineage_id": root_lineage_id if isinstance(root_lineage_id, str) else None,
        "source": {
            key: value
            for key, value in source.items()
            if key in {"adapter", "source", "source_id", "event_id", "report_id", "test_id"}
            and isinstance(value, str)
        },
        "environment": normalize_environment(
            evidence.get("environment") if isinstance(evidence.get("environment"), dict) else {}
        ),
    }


def _find_intervention(problem: Mapping[str, Any], intervention_id: str) -> MutableMapping[str, Any]:
    for item in problem.get("interventions", []):
        if item.get("id") == intervention_id:
            return item
    raise KeyError(f"unknown intervention: {intervention_id}")


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def _normalize_time(value: str) -> str:
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValueError(f"invalid RFC3339 timestamp: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
