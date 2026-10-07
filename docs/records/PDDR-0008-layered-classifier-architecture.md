---
id: PDDR-0008
title: Layered privacy-safe classifier architecture
decision_date: 2026-10-07
recorded_date: 2026-10-07
decision_status: proposed
delivery_status: in-progress
scope:
  - product
  - project
  - process
owners:
  - serevy
evidence:
  - https://github.com/serevy/agent-kpt/issues/20
  - https://github.com/serevy/agent-kpt/issues/14
related:
  - PDDR-0001
  - PDDR-0006
  - PDDR-0007
supersedes: []
superseded_by: null
---

# PDDR-0008: Layered privacy-safe classifier architecture

## Summary

Separate error-like record classification into common, provider-specific, and optional user/project layers while retaining normalized outcome and rule provenance.

Do not treat a provider `is_error` flag as proof of an actionable failure.

## Context and observations

Second real dogfood found that the first deterministic taxonomy remained `unknown/unknown` for most current-week error-like records.

A local historical experiment showed that additional rules could substantially reduce unknown-rate, but also exposed a measurement trap: a generic process/exit-code bucket absorbed many records without identifying a cause.

High-volume Unity CLI reload/compile/start records were also provider/tool-reported waiting state rather than real failures.

Therefore the durable problem is not merely "add more strings." The architecture must:

- keep provider-neutral rules out of provider adapters;
- keep provider-specific semantics in the provider adapter layer;
- allow local project/tool knowledge without upstream releases;
- distinguish failure from blocked/waiting/warning/transient states;
- retain which rule produced a classification;
- keep raw error text non-persistent by default;
- validate candidate rules against false positives and held-out evidence.

## Options considered

### Option A — One global rule table

Benefits:
- simplest implementation.

Costs:
- provider/tool-specific semantics leak into the provider-neutral core;
- local tool patterns require upstream releases;
- version/revalidation provenance is weak.

Status: rejected.

### Option B — Let user rules override built-ins

Benefits:
- maximum local flexibility.

Costs:
- a local file can silently redefine provider-neutral/provider-specific deterministic meaning;
- harder to interpret reports across projects.

Status: rejected for v0alpha1.

### Option C — First-match layered classifier

Order:

```text
common -> provider -> user -> unknown
```

Benefits:
- common deterministic meaning wins;
- provider-specific semantics fill provider gaps;
- local user/project rules fill remaining gaps only;
- provenance is explicit.

Costs:
- users cannot override built-in classifications without a future explicit override mechanism;
- rule precedence becomes a compatibility contract.

Status: proposed for validation.

## Decision

1. Classification is deterministic-first and local.
2. Raw error text may be inspected transiently but is not persisted by the default pipeline.
3. Precedence is `common -> provider -> user -> unknown`; first match wins.
4. Common rules contain provider-neutral deterministic patterns.
5. Provider adapter modules contain provider/harness-specific semantics.
6. Optional user/project rules fill unmatched local tool/project states and do not override built-in matches.
7. v0alpha1 user rules use case-insensitive literal substring matching; regex is not supported.
8. `tool` is optional for a user rule.
9. Normalized classification retains:
   - category;
   - subtype;
   - outcome;
   - rule ID;
   - rule scope;
   - ruleset version;
   - tool when known;
   - observed provider/harness version when known.
10. Normalized outcomes are `failure`, `blocked`, `waiting`, `warning`, `transient`, and `unknown`.
11. Provider `is_error` does not imply normalized `failure`.
12. Invalid user rules fail soft with diagnostics.
13. Numeric confidence is not introduced until it has validated semantics.
14. Unknown remains a valid classification result.
15. Report drill-down exposes rule provenance without raw text.
16. Classifier promotion must consider precision/near-miss negatives/held-out evidence, not unknown-rate alone.

## Delivery and validation

Implementation is in progress in Issue #20.

Validation must include:

- common/provider/user layer separation;
- precedence regression;
- optional local rule file;
- fail-soft invalid rule behavior;
- privacy regression proving raw text does not persist;
- outcome and rule provenance through analysis packet/report;
- versioned synthetic near-miss fixture;
- Windows/macOS/Linux hosted tests;
- CodeRabbit review;
- evaluation protocol linked to Issue #16.

Coverage numbers from one user's/project's historical data remain research evidence and are not treated as proof of general classifier quality.

## Consequences

Benefits:

- provider-neutral core remains reusable;
- provider-specific semantics can evolve independently;
- users can describe local tools such as Unity/pyenv without forking agent-kpt;
- waiting/transient states stop looking like identical failures;
- reports can explain why a classification was made;
- environment/ruleset changes can be revalidated.

Accepted constraints if adopted:

- first-match precedence is intentionally conservative;
- user rules cannot override a built-in match in v0alpha1;
- literal matching is less expressive than regex/semantic matching;
- local rule quality remains the user's responsibility;
- `unknown` will remain non-zero by design.

## Revisit when

Revisit if:
- a legitimate need for explicit overrides emerges;
- literal user rules are insufficient;
- provider version churn causes excessive stale rules;
- held-out evaluation supports broader common rules;
- a calibrated confidence model can be defined.

## Evidence

- Issue #20
- Issue #14 second real dogfood
- `fixtures/classifier-v0alpha1/eval.json`
- `tests/test_classification.py`

## Related records

- PDDR-0001: Provider-neutral normalized event core
- PDDR-0006: Dogfood hardening for privacy-safe actionable reports
- PDDR-0007: Stable intervention identity and reproposal reuse
