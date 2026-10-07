from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

COMMON_RULESET_VERSION = "common-v0alpha1"
USER_RULE_SCHEMA_VERSION = "agent-kpt.classifier-rules/v0alpha1"
OUTCOMES = {"failure", "blocked", "waiting", "warning", "transient", "unknown"}
RULE_SCOPES = {"common", "provider", "user"}
_TOKEN_RE = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")


@dataclass(frozen=True)
class Classification:
    category: str
    subtype: str
    outcome: str
    rule_id: str
    rule_scope: str
    ruleset_version: str

    def as_payload(self, *, provider_version: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "category": self.category,
            "subtype": self.subtype,
            "outcome": self.outcome,
            "rule_id": self.rule_id,
            "rule_scope": self.rule_scope,
            "ruleset_version": self.ruleset_version,
        }
        if provider_version:
            payload["provider_version"] = provider_version
        return payload


@dataclass(frozen=True)
class UserRule:
    rule_id: str
    tool: str
    contains_any: tuple[str, ...]
    category: str
    subtype: str
    outcome: str


@dataclass(frozen=True)
class UserRuleSet:
    ruleset_version: str
    rules: tuple[UserRule, ...]


def classify_common(*, error_type: str | None, text: str) -> Classification | None:
    haystack = f"{error_type or ''}\n{text}".lower()
    normalized_error_type = (error_type or "").lower()

    if (
        "rate limit" in haystack
        or "too many requests" in haystack
        or re.search(r"\b(?:http(?: status)?|status(?: code)?)\s*[:=]?\s*429\b", haystack)
    ):
        return _common("rate-limit", "rate-limit", "transient", "common.rate-limit")

    if (
        "timeout" in normalized_error_type
        or "timedout" in normalized_error_type
        or any(
            pattern in haystack
            for pattern in (
                "timed out",
                "timeout error",
                "request timeout",
                "operation timeout",
                "connection timeout",
                "read timeout",
                "connect timeout",
                "deadline exceeded",
                "etimedout",
            )
        )
    ):
        return _common("timeout", "timeout", "transient", "common.timeout")

    rules = (
        (
            "auth",
            "unauthorized",
            "failure",
            "common.auth.unauthorized",
            ("unauthorized", "authentication failed", "invalid token", "invalid api key"),
        ),
        (
            "permission",
            "permission-denied",
            "failure",
            "common.permission.denied",
            ("permission denied", "access denied", "eacces", "operation not permitted"),
        ),
        (
            "path",
            "path-quoting",
            "failure",
            "common.path.quoting",
            ("path-quoting", "path quoting"),
        ),
        (
            "path",
            "file-not-found",
            "failure",
            "common.path.file-not-found",
            (
                "no such file or directory",
                "file not found",
                "path not found",
                "cannot find path",
                "enoent",
            ),
        ),
        (
            "path",
            "not-a-directory",
            "failure",
            "common.path.not-a-directory",
            ("not a directory", "enotdir"),
        ),
        (
            "dependency",
            "module-not-found",
            "failure",
            "common.dependency.module-not-found",
            ("no module named", "module not found", "cannot find module"),
        ),
        (
            "dependency",
            "command-not-found",
            "failure",
            "common.dependency.command-not-found",
            (
                "command not found",
                "is not recognized as an internal or external command",
                "executable not found",
            ),
        ),
        (
            "syntax",
            "syntax-error",
            "failure",
            "common.syntax.error",
            ("syntax error", "invalid syntax", "parse error", "unexpected token"),
        ),
        (
            "network",
            "connection-refused",
            "transient",
            "common.network.connection-refused",
            ("connection refused", "econnrefused"),
        ),
        (
            "network",
            "dns",
            "transient",
            "common.network.dns",
            ("could not resolve host", "name or service not known", "getaddrinfo"),
        ),
        (
            "network",
            "network",
            "transient",
            "common.network.generic",
            ("network is unreachable", "enetunreach", "econnreset", "connection reset"),
        ),
    )
    for category, subtype, outcome, rule_id, patterns in rules:
        if any(pattern in haystack for pattern in patterns):
            return _common(category, subtype, outcome, rule_id)
    return None


def classify_user(
    ruleset: UserRuleSet | None,
    *,
    tool: str | None,
    text: str,
) -> Classification | None:
    if ruleset is None or not tool:
        return None
    normalized_tool = tool.casefold()
    haystack = text.casefold()
    for rule in ruleset.rules:
        if rule.tool.casefold() != normalized_tool:
            continue
        if any(pattern.casefold() in haystack for pattern in rule.contains_any):
            return Classification(
                category=rule.category,
                subtype=rule.subtype,
                outcome=rule.outcome,
                rule_id=rule.rule_id,
                rule_scope="user",
                ruleset_version=ruleset.ruleset_version,
            )
    return None


def unknown_classification() -> Classification:
    return Classification(
        category="unknown",
        subtype="unknown",
        outcome="unknown",
        rule_id="classifier.unknown",
        rule_scope="common",
        ruleset_version=COMMON_RULESET_VERSION,
    )


def load_user_rules(
    path: str | Path | None,
) -> tuple[UserRuleSet | None, list[dict[str, Any]]]:
    if path is None:
        return None, []

    rule_path = Path(path).expanduser()
    if not rule_path.exists():
        return None, [
            _diagnostic(
                "classifier-rules-missing",
                "Configured classifier rule file does not exist; user rules were skipped.",
            )
        ]

    try:
        data = json.loads(rule_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, [
            _diagnostic(
                "classifier-rules-invalid",
                "Classifier rule file could not be read as JSON; user rules were skipped.",
            )
        ]

    if not isinstance(data, Mapping):
        return None, [
            _diagnostic(
                "classifier-rules-invalid",
                "Classifier rule file must contain one JSON object; user rules were skipped.",
            )
        ]
    if data.get("schema_version") != USER_RULE_SCHEMA_VERSION:
        return None, [
            _diagnostic(
                "classifier-rules-invalid",
                f"Classifier rule file must use schema_version {USER_RULE_SCHEMA_VERSION}.",
            )
        ]

    ruleset_version = data.get("ruleset_version")
    if not isinstance(ruleset_version, str) or not ruleset_version.strip():
        return None, [
            _diagnostic(
                "classifier-rules-invalid",
                "Classifier rule file requires a non-empty ruleset_version.",
            )
        ]

    raw_rules = data.get("rules")
    if not isinstance(raw_rules, list):
        return None, [
            _diagnostic(
                "classifier-rules-invalid",
                "Classifier rule file requires a rules array.",
            )
        ]

    diagnostics: list[dict[str, Any]] = []
    rules: list[UserRule] = []
    seen_ids: set[str] = set()
    for index, raw in enumerate(raw_rules):
        try:
            rule = _parse_user_rule(raw, seen_ids)
        except ValueError as exc:
            diagnostics.append(
                _diagnostic(
                    "classifier-rule-invalid",
                    f"User classifier rule {index} was skipped: {exc}",
                )
            )
            continue
        seen_ids.add(rule.rule_id)
        rules.append(rule)

    return UserRuleSet(ruleset_version=ruleset_version.strip(), rules=tuple(rules)), diagnostics


def _parse_user_rule(raw: Any, seen_ids: set[str]) -> UserRule:
    if not isinstance(raw, Mapping):
        raise ValueError("rule must be an object")

    rule_id = _required_token(raw, "id")
    if rule_id in seen_ids:
        raise ValueError(f"duplicate rule id {rule_id!r}")

    tool = raw.get("tool")
    if not isinstance(tool, str) or not tool.strip():
        raise ValueError("tool must be a non-empty string")

    contains_any = raw.get("contains_any")
    if (
        not isinstance(contains_any, list)
        or not contains_any
        or any(not isinstance(item, str) or not item.strip() for item in contains_any)
    ):
        raise ValueError("contains_any must be a non-empty list of strings")
    if len(contains_any) > 32:
        raise ValueError("contains_any supports at most 32 patterns")

    category = _required_token(raw, "category")
    subtype = _required_token(raw, "subtype")
    outcome = raw.get("outcome")
    if outcome not in OUTCOMES:
        raise ValueError(f"outcome must be one of {sorted(OUTCOMES)}")

    return UserRule(
        rule_id=rule_id,
        tool=tool.strip(),
        contains_any=tuple(item.strip() for item in contains_any),
        category=category,
        subtype=subtype,
        outcome=str(outcome),
    )


def _required_token(raw: Mapping[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not _TOKEN_RE.fullmatch(value):
        raise ValueError(f"{key} must match {_TOKEN_RE.pattern}")
    return value


def _common(category: str, subtype: str, outcome: str, rule_id: str) -> Classification:
    return Classification(
        category=category,
        subtype=subtype,
        outcome=outcome,
        rule_id=rule_id,
        rule_scope="common",
        ruleset_version=COMMON_RULESET_VERSION,
    )


def _diagnostic(code: str, message: str) -> dict[str, Any]:
    return {
        "severity": "warning",
        "code": code,
        "message": message,
        "recoverable": True,
        "source_index": None,
    }
