---
id: PDDR-0006
title: Dogfood hardening for privacy-safe actionable reports
decision_date: 2026-10-06
recorded_date: 2026-10-06
decision_status: accepted
delivery_status: in-progress
scope:
  - product
  - project
  - process
owners:
  - serevy
evidence:
  - https://github.com/serevy/agent-kpt/issues/14
  - https://github.com/serevy/agent-kpt/issues/18
related:
  - PDDR-0003
  - PDDR-0004
  - PDDR-0005
supersedes: []
superseded_by: null
---

# PDDR-0006: Dogfood hardening for privacy-safe actionable reports

## Summary

Keep raw conversational/error content out of persisted analysis artifacts by default, while retaining deterministic derived error classifications that make KPT drill-down actionable.

Also move report/intermediate artifacts out of the target repository by default.

## Context and observations

Real weekly dogfood on Windows produced a useful top-level recurrence signal:

- 24 raw tool errors;
- 5 sessions;
- 4 independent root lineages.

However, the drill-down only repeated that an error occurred and that raw error text was not persisted. It could not answer what should be fixed.

The same run also produced:

- about 15,877 recoverable diagnostics;
- about 3.7 MB analysis packet, mostly user-message metadata;
- untracked report/intermediate files in the target repository;
- weak early guidance when the selected Python runtime was below 3.10.

The existing decisions that worked well remain unchanged:

- raw occurrence and independent root-lineage recurrence are distinct;
- weak semantic speculation must not become a durable Ledger Problem;
- human review remains required for intervention acceptance.

## Options considered

### Option A — persist raw errors

Benefits:
- maximum semantic detail.

Costs:
- widens the persisted sensitivity boundary;
- may retain paths, secrets, code fragments, API output, or business data.

Status: rejected as the default path.

### Option B — discard raw errors without replacement

Benefits:
- smallest persisted surface.

Costs:
- observed dogfood showed the detailed report becomes diagnostically useless.

Status: rejected.

### Option C — transient local inspection -> derived classification -> discard raw text

Persist:
- category;
- subtype;
- tool name where known;
- stable fingerprint;
- recurrence/evidence provenance.

Do not persist the original error body by default.

Status: accepted.

## Decision

1. Raw prompt, assistant, tool-input/output, and raw error text remain non-persistent by default.
2. The local adapter may inspect raw error text transiently to derive deterministic error classification.
3. Initial categories include path, permission, timeout, syntax, dependency, network, auth, rate-limit, and unknown.
4. Classification must not claim more specificity than deterministic evidence supports.
5. Detailed reports use three disclosure levels:
   - classification summary;
   - representative evidence across root lineages;
   - full evidence at the deepest drill-down.
6. Repeated adapter diagnostics are aggregated by code/severity/recoverability/message with counts.
7. Individual `user.message` entries are not included in the semantic Evidence packet; message statistics remain available as aggregates.
8. Final reports default to `~/.agent-kpt/projects/<hash>/reports/`.
9. Intermediate workflow files default to project-scoped agent-kpt state/work storage, not the target repository.
10. `AGENT_KPT_REPORT_DIR` may override final report output.
11. The repo-local launcher rejects Python < 3.10 before importing the application.

The repository owner approved this direction from real dogfood feedback on 2026-10-06.

## Delivery and validation

In progress in Issue #18.

Expected validation:

- no target-repository pollution during the normal Skill workflow;
- classified error evidence contains no synthetic secret text;
- repeated diagnostics collapse to counted summaries;
- user-message Evidence is absent while aggregate stats remain;
- HTML/Markdown show classification summary before representative/full Evidence;
- Python runtime guard is actionable;
- existing lineage and evidence-bound Ledger regressions remain green across Windows/macOS/Linux.

## Consequences

Benefits:

- drill-down supports an actual next debugging action;
- packet/context cost is reduced;
- target repositories stay clean;
- the privacy boundary stays narrow without making Evidence useless.

Accepted constraints:

- unknown classification remains a valid result;
- deterministic taxonomy will not understand every semantic failure;
- richer raw-content analysis, if added later, must be explicit opt-in.

## Revisit when

Revisit if deterministic classification leaves too many important failures as unknown, if users need project-local reports by default, or if a future explicit local-only semantic error-analysis mode can preserve the same safety boundary.

## Evidence

- Issue #14 real weekly dogfood feedback
- Issue #18 v0.1 hardening tracker
- PR #19 implementation and hosted validation

## Related records

- PDDR-0003: Stateful improvement ledger lifecycle
- PDDR-0004: Progressive disclosure coaching report
- PDDR-0005: Skill-first one-command workflow
