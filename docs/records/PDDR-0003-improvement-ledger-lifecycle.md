---
id: PDDR-0003
title: Stateful improvement ledger lifecycle
decision_date: 2026-09-28
recorded_date: 2026-09-28
decision_status: accepted
delivery_status: validated
scope:
  - project
  - product
owners:
  - serevy
evidence:
  - https://github.com/serevy/agent-kpt/issues/3
related:
  - PDDR-0001
  - PDDR-0002
supersedes: []
superseded_by: null
---

# PDDR-0003: Stateful improvement ledger lifecycle

## Summary

Propose a machine-readable Problem / Evidence / Intervention ledger so KPT can track recurrence, human decisions, intervention outcomes, Keep graduation, environment-triggered revalidation, and retirement without accumulating permanent rules forever.

## Context and observations

The current baseline can describe these states in prose, but it cannot reliably answer across weeks/months:

- whether a problem recurred across independent root lineages;
- whether a previous Try was approved, applied, effective, ineffective, or revised;
- whether a Keep has become habitual and should graduate from the report;
- whether a model/harness/adapter/config update invalidates old evidence;
- whether an obsolete workaround was explicitly retired.

PDDR-0001 already makes lineage and environment provenance available to the core. The ledger can build on that evidence without changing provider adapters.

## Options considered

### Option A — Keep state only in generated report prose

- Description: infer history from previous Markdown/HTML reports.
- Benefits: no additional data model.
- Costs / constraints: fragile IDs, difficult effect tracking, ambiguous human decision state, poor retirement/revalidation semantics.
- Status: rejected by this proposal

### Option B — Stateful Problem / Evidence / Intervention ledger

- Description: keep stable problem IDs, inspectable evidence, and intervention history as structured data.
- Benefits: deterministic recurrence, explicit human decisions, effect verification, Keep graduation, environment revalidation, retirement history.
- Costs / constraints: introduces a new versioned schema and lifecycle transitions.
- Status: proposed

## Decision

Accepted v0alpha1 contract:

1. problem IDs are stable functions of the recurring fingerprint;
2. recurrence becomes independent only across distinct root lineages;
3. evidence keeps provenance and relevant environment metadata;
4. intervention `decision` (human authority) is independent from intervention `status` (delivery/effectiveness);
5. effective interventions may move through Keep reinforcement -> habituated -> graduated;
6. validation environment is retained and material changes mark `needs-revalidation` rather than automatically declaring an old intervention invalid;
7. interventions and problems have explicit retirement paths that preserve historical evidence.

The repository owner reviewed and accepted this lifecycle and authority contract on 2026-09-29. Future dogfooding may revise it through a later PDDR without rewriting this record.

## Delivery and validation

Validated in PR #9.

Evidence:

- `schemas/v0alpha1/ledger.schema.json` defines the machine-readable ledger contract;
- `src/agent_kpt/ledger.py` implements the Python reference lifecycle helpers;
- synthetic lifecycle tests cover lineage-aware recurrence, human decision state, intervention delivery/effectiveness state, Keep graduation, environment-triggered revalidation, and retirement;
- the full test suite passes with 10 tests;
- GitHub Actions passes on Ubuntu (Python 3.10 and 3.13), Windows (Python 3.11), and macOS (Python 3.11);
- PDDR validation passes.

## Consequences

Benefits:

- KPT can become a continuous improvement loop rather than disconnected reports;
- old interventions can disappear from attention without losing provenance;
- model/harness changes can trigger review rather than silently carrying stale advice forward;
- human approval is not confused with implementation success.

Accepted constraints if adopted:

- lifecycle/schema evolution becomes a compatibility concern;
- stable fingerprints become important because they anchor problem identity;
- automatic state transitions should stay conservative when evidence is incomplete.

## Revisit when

Revisit if real dogfooding shows that one fingerprint maps to multiple semantically different problems, one problem needs multiple simultaneous Keep states, or environment comparison produces excessive false-positive revalidation.

## Evidence

- Issue #3
- `docs/improvement-ledger-v0alpha1.md`
- `schemas/v0alpha1/ledger.schema.json`
- `tests/test_ledger.py`

## Related records

- PDDR-0001: Provider-neutral normalized event core
- PDDR-0002: Python reference implementation with language-neutral core
