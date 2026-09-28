---
id: PDDR-0004
title: Progressive disclosure coaching report
decision_date: 2026-09-29
recorded_date: 2026-09-29
decision_status: accepted
delivery_status: in-progress
scope:
  - product
  - project
owners:
  - serevy
evidence:
  - https://github.com/serevy/agent-kpt/issues/4
related:
  - PDDR-0001
  - PDDR-0003
supersedes: []
superseded_by: null
---

# PDDR-0004: Progressive disclosure coaching report

## Summary

Adopt a summary-first, evidence-backed report that coaches workers without scoring them.

The default surface stays small enough to scan in a few minutes, while detailed metrics, lineage, provenance, and diagnostics remain available through drill-down.

## Context and observations

The pre-OSS KPT report preserved useful detail but exposed too much of it at once. The project now has deterministic metrics and a stateful improvement ledger, so user-facing reports no longer need to make workers read the internal model directly.

The intended outcome is not to teach terminology for its own sake. Workers should gradually get better at collaborating with coding agents while mostly seeing plain-language observations and one manageable experiment at a time.

Japanese copy also benefits from a separate readability pass, but that pass must not alter metrics or evidence.

## Options considered

### Option A — Show most evidence inline

- Description: keep the detailed metrics/report shape close to the baseline.
- Benefits: everything is visible immediately.
- Costs / constraints: high cognitive load; internal concepts become required reading.
- Status: rejected

### Option B — Summary-first with progressive drill-down

- Description: keep a compact surface and move raw/deduplicated/evidence details behind drill-down.
- Benefits: low attention cost without evidence loss; better fit for weekly habit formation.
- Costs / constraints: requires a separate Report View Model and renderer contract.
- Status: accepted

### Option C — Add worker/agent quality scores

- Description: compress the report into one or more numeric ratings.
- Benefits: visually simple.
- Costs / constraints: hides nuance, encourages optimization for the score, conflicts with coaching goals.
- Status: rejected

## Decision

The accepted v0alpha1 report contract is:

1. Summary-first and evidence-backed.
2. User-facing surface caps: 4 KPIs, 3 Keep, 3 Problem, 3 trend notes, and **one Next Try**.
3. No developer/agent scores, grades, ranks, or leaderboards.
4. Internal terms are translated into plain-language meaning on the surface.
5. Raw/deduplicated metrics, lineage, provenance, and diagnostics remain available in drill-down.
6. HTML uses collapsed progressive disclosure; Markdown preserves an accessible details section.
7. Environment changes can appear on the surface because they may invalidate old advice.
8. Japanese copy polishing is optional and may edit wording only; facts and evidence are frozen before the polish step.
9. `natural-japanese` is a useful optional reference/integration but not a core/runtime dependency.

The repository owner approved this direction on 2026-09-29.

## Delivery and validation

In progress in Issue #4.

Planned artifacts:

- Report View Model JSON Schema;
- deterministic HTML and Markdown renderers;
- Japanese concise-report fixture;
- tests enforcing surface caps, one Next Try, scoring rejection, evidence references, drill-down, and environment markers;
- documented Japanese copy-polish boundary.

## Consequences

Benefits:

- workers can understand the report without learning internal telemetry terminology;
- the report can teach habits gradually instead of behaving like a lecture;
- evidence remains available to advanced users and maintainers;
- copy quality can evolve independently from deterministic facts.

Accepted constraints:

- a separate semantic/report-composition step must choose what reaches the surface;
- the renderer cannot rescue a badly composed Report View Model;
- concise limits may hide lower-priority findings from the first screen, so those findings must remain in the ledger/evidence layer.

## Revisit when

Revisit if users regularly need more than one Next Try, the surface limits hide urgent information, drill-down is still too technical, or copy-polish integration risks changing factual content.

## Evidence

- Issue #4
- `docs/report-ux-v0alpha1.md`
- `docs/japanese-copy-policy.md`
- `fixtures/report-v0alpha1/report-ja.json`

## Related records

- PDDR-0001: Provider-neutral normalized event core
- PDDR-0003: Stateful improvement ledger lifecycle
