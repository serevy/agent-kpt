---
id: PDDR-0009
title: Provider-independent report locale policy
decision_date: 2026-10-07
recorded_date: 2026-10-07
decision_status: accepted
delivery_status: implemented
scope:
  - product
  - project
owners:
  - serevy
evidence:
  - tests/test_locale.py
related:
  - PDDR-0004
  - PDDR-0005
supersedes: []
superseded_by: null
---

# PDDR-0009: Provider-independent report locale policy

## Summary

Select KPT report language independently of the provider, coding tool, and README.
Explicit configuration wins, followed by the current user conversation language,
then English. Keep English README.md canonical and synchronize README.ja.md manually.

## Context and observations

The Report View Model already requires locale and the renderer supplies Japanese
and English UI labels. The preparation CLI previously did not select a language,
leaving prose language to implicit agent behavior. Switching tools could therefore
change the report language unintentionally.

## Options considered

### Option A — Infer language from the provider or historical transcripts

- Benefits: no explicit input required.
- Costs / constraints: couples presentation to tool choice or stale conversations;
  adds unnecessary raw-text inspection.
- Status: rejected.

### Option B — Resolve explicit settings and current conversation context

- Benefits: deterministic precedence, portable across providers, no raw conversation
  persistence or new dependency.
- Costs / constraints: the invoking agent supplies the current conversation language;
  unattended CLI calls cannot infer it.
- Status: accepted.

## Decision

The maintainer requested this policy and its implementation on 2026-10-07.

1. `workflow prepare --locale` takes precedence over `AGENT_KPT_LOCALE`, then
   `--conversation-locale`, then `en-US`. Environment configuration is the only
   persistent preference mechanism in this version; no config file is introduced.
2. The invoking skill supplies a conversation tag only when the current user's
   language is clear. Ambiguous or unavailable language is omitted.
3. Normalize tag case and underscore separators; bare `ja` and `en` become `ja-JP`
   and `en-US`. Tags are structurally checked, not checked against the IANA registry.
   An empty environment setting is unset; malformed selected settings fail visibly.
4. Store `locale` and `locale_source` in the analysis packet's `report_contract`.
   Sources are `explicit`, `environment`, `conversation`, and `default`.
5. The agent copies this locale into the Report View Model and writes generated
   prose in that language. Preserve identifiers, enum values, metrics, and provenance.
6. Japanese and English renderer labels remain supported. Other language tags use
   English UI labels while retaining their requested prose language. Rendering an
   existing view never translates its text or reads environment preferences.
7. OS language, tool UI, provider identity, README language, and historical logs
   do not select report language. The older deterministic `report` metrics command
   remains an English diagnostic output, separate from the KPT report workflow.
8. English README remains canonical; Japanese is maintained alongside it without
   adding a translation pipeline for two languages.

## Delivery and validation

Implemented in the resolver, preparation API/CLI, skill, and schema documentation.
Local Windows Python 3.11 validation passes all 49 unit tests, including precedence,
normalization, invalid values, CLI packet persistence, host-language independence,
and renderer UI-label fallback without prose translation. Hosted CI is tracked in
the implementing pull request. Tests do not claim to validate natural-language
translation quality produced by an agent.

## Consequences

Reports can retain one preferred language across coding tools. Only language tags
and selection provenance are stored; no additional raw conversation text is needed.
The CLI does not perform language detection or machine translation. Adding a locale
does not add renderer label translations automatically.

## Revisit when

Introduce a configuration file only when broader settings require one. Revisit
renderer label coverage when users need more languages, and README translation
automation when language count or synchronization effort warrants it.

## Evidence

- `tests/test_locale.py`
- `src/agent_kpt/locale.py`
- `skills/agent-kpt/SKILL.md`
- Implementing PR and hosted checks linked from the PR description.

## Related records

- PDDR-0004: Progressive-disclosure coaching report
- PDDR-0005: Skill-first one-command workflow
