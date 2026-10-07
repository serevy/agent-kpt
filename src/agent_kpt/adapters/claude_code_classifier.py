from __future__ import annotations

from agent_kpt.classification import Classification

CLAUDE_CODE_RULESET_VERSION = "claude-code-v0alpha1"


def classify_claude_code(
    *,
    error_type: str | None,
    text: str,
) -> Classification | None:
    haystack = f"{error_type or ''}\n{text}".casefold()

    rules = (
        (
            "precondition",
            "file-not-read",
            "blocked",
            "claude-code.file-not-read",
            (
                "file has not been read yet",
                "file has not been read",
                "must read the file before",
            ),
        ),
        (
            "precondition",
            "file-changed-after-read",
            "blocked",
            "claude-code.file-changed-after-read",
            (
                "file has been modified since read",
                "file has changed since you read",
                "file changed since you read",
            ),
        ),
        (
            "precondition",
            "replacement-not-found",
            "blocked",
            "claude-code.replacement-not-found",
            (
                "old_string not found",
                "old string not found",
                "string to replace not found",
                "replacement target not found",
            ),
        ),
        (
            "policy",
            "safety-block",
            "blocked",
            "claude-code.safety-block",
            (
                "blocked by safety check",
                "operation blocked by safety",
                "safety check blocked",
            ),
        ),
    )

    for category, subtype, outcome, rule_id, patterns in rules:
        if any(pattern in haystack for pattern in patterns):
            return Classification(
                category=category,
                subtype=subtype,
                outcome=outcome,
                rule_id=rule_id,
                rule_scope="provider",
                ruleset_version=CLAUDE_CODE_RULESET_VERSION,
            )
    return None
