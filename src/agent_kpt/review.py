from __future__ import annotations

from typing import Any, Mapping, MutableMapping

from agent_kpt.ledger import add_intervention, upsert_problem
from agent_kpt.storage import load_ledger, save_ledger

REVIEW_SCHEMA_VERSION = "agent-kpt.review/v0alpha1"


def apply_review_actions(
    actions: Mapping[str, Any],
    packet: Mapping[str, Any],
    *,
    project: str,
) -> dict[str, Any]:
    if actions.get("schema_version") != REVIEW_SCHEMA_VERSION:
        raise ValueError(f"unsupported review schema: {actions.get('schema_version')!r}")

    evidence_map = {
        item.get("id"): item
        for item in packet.get("evidence", [])
        if isinstance(item, Mapping) and isinstance(item.get("id"), str)
    }
    ledger = load_ledger(project)
    period_end = packet.get("period", {}).get("end")
    if not isinstance(period_end, str):
        raise ValueError("packet.period.end is required")

    problems = actions.get("problems", [])
    if not isinstance(problems, list):
        raise ValueError("review problems must be a list")

    for item in problems:
        if not isinstance(item, Mapping):
            raise ValueError("review problem items must be objects")
        fingerprint = _text(item, "fingerprint")
        title = _text(item, "title")
        target_type = _text(item, "target_type")
        evidence_ids = item.get("evidence_ids", [])
        if not isinstance(evidence_ids, list) or not evidence_ids:
            raise ValueError("review problem evidence_ids must be a non-empty list")

        problem: MutableMapping[str, Any] | None = None
        for evidence_id in evidence_ids:
            evidence = evidence_map.get(evidence_id)
            if evidence is None:
                raise ValueError(f"unknown evidence id: {evidence_id}")
            observed_at = evidence.get("observed_at")
            if not isinstance(observed_at, str):
                raise ValueError(f"evidence {evidence_id} has no observed_at")
            problem = upsert_problem(
                ledger,
                fingerprint=fingerprint,
                title=title,
                target_type=target_type,
                observed_at=observed_at,
                evidence={
                    "id": evidence_id,
                    "kind": evidence.get("kind", "event"),
                    "root_lineage_id": evidence.get("root_lineage_id"),
                    "source": {
                        "source": str(evidence.get("source") or ""),
                        "event_id": str(evidence.get("source_event_id") or evidence_id),
                    },
                    "environment": {
                        key: value
                        for key, value in (evidence.get("environment") or {}).items()
                        if value is not None
                    },
                },
            )

        next_try = item.get("next_try")
        if problem is not None and isinstance(next_try, Mapping):
            add_intervention(
                problem,
                kind=_text(next_try, "kind"),
                summary=_text(next_try, "summary"),
                proposed_at=period_end,
                decision="proposed",
            )

    save_ledger(project, ledger)
    return ledger


def _text(mapping: Mapping[str, Any], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()
