"""Provider-independent report language selection (no transcript inspection)."""

from __future__ import annotations

import os
import re


def normalize_locale(value: str) -> str:
    """Accept a language tag, normalizing case and common underscore spelling.

    This is a structural check, not validation against the IANA registry.
    Bare ja/en select the report defaults ja-JP/en-US.
    """
    if not isinstance(value, str):
        raise ValueError("report locale must be a language tag such as ja-JP or en-US")
    tag = value.strip().replace("_", "-")
    if not re.fullmatch(r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*", tag):
        raise ValueError("report locale must be a language tag such as ja-JP or en-US")
    parts = tag.split("-")
    language = parts[0].lower()
    if len(parts) == 1:
        return {"ja": "ja-JP", "en": "en-US"}.get(language, language)
    normalized = [language]
    extension = False
    for part in parts[1:]:
        if len(part) == 1:
            extension = True
        if not extension and len(part) == 4 and part.isalpha():
            normalized.append(part.title())
        elif not extension and len(part) == 2 and part.isalpha():
            normalized.append(part.upper())
        else:
            normalized.append(part.lower())
    return "-".join(normalized)


def resolve_report_locale(
    explicit: str | None = None,
    conversation: str | None = None,
) -> tuple[str, str]:
    """Resolve explicit > environment configuration > conversation > English.

    Empty environment configuration is unset. Invalid selected input fails
    visibly rather than silently generating a report in an unintended language.
    """
    configured = os.environ.get("AGENT_KPT_LOCALE", "").strip()
    for value, source in (
        (explicit, "explicit"),
        (configured or None, "environment"),
        (conversation, "conversation"),
    ):
        if value is not None:
            return normalize_locale(value), source
    return "en-US", "default"
