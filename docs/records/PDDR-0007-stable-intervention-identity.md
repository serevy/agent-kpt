---
id: PDDR-0007
title: Stable intervention identity and reproposal reuse
decision_date: 2026-10-06
recorded_date: 2026-10-06
decision_status: accepted
delivery_status: validated
scope:
  - product
  - project
owners:
  - serevy
evidence:
  - https://github.com/serevy/agent-kpt/issues/23
related:
  - PDDR-0003
  - PDDR-0006
supersedes: []
superseded_by: null
---

# PDDR-0007: Stable intervention identity and reproposal reuse

## Summary

Treat repeated semantically identical Next Try proposals for the same Problem as one durable Intervention, not one new Intervention per report period.

Reuse the existing Intervention, preserve human decision/status, and record bounded re-proposal metadata.

## Context and observations

Real repeated weekly dogfood found that Problem identity behaved correctly while Intervention identity did not.

Observed behavior:

- the same Problem fingerprint was reused;
- recurrence/lifecycle updated correctly;
- the same Next Try text submitted one week later created another `proposed` Intervention;
- `intervention_count` therefore increased from 1 to 2 even though the proposal itself had not changed.

The previous implementation included `proposed_at` in the Intervention ID. That made each weekly occurrence a distinct durable object.

If left unchanged, an unchanged recommendation could accumulate one pending Intervention per week and make status/ledger review noisy.

## Options considered

### Option A — Keep one Intervention per report period

- Description: timestamp remains part of durable Intervention identity.
- Benefits: every proposal occurrence is explicit as a separate object.
- Costs / constraints: duplicate pending decisions accumulate; human decision history fragments; status becomes noisy.
- Status: rejected

### Option B — Reuse semantic Intervention and record re-proposal metadata

- Description: within one Problem, identity is based on Intervention kind + normalized summary. Repeated proposals update metadata.
- Benefits: one human decision object; recurrence remains visible; status stays bounded.
- Costs / constraints: summary normalization becomes part of identity semantics.
- Status: accepted

### Option C — Silently ignore repeated proposals

- Description: reuse the Intervention without recording that it was suggested again.
- Benefits: smallest schema.
- Costs / constraints: loses useful evidence that the same recommendation resurfaced.
- Status: rejected

## Decision

1. Problem identity remains anchored by the Problem fingerprint.
2. Within a Problem, Intervention identity is the combination of:
   - Intervention kind; and
   - normalized summary.
3. Summary normalization is conservative: collapse whitespace and apply case-folding. Punctuation and materially different wording remain distinct.
4. New Interventions use a stable ID that does not include proposal time.
5. Existing stored canonical Intervention IDs are not rewritten. Old timestamp-derived IDs are matched semantically and reused.
6. Safe legacy duplicates created by the old timestamp-based identity may be lazily coalesced:
   - pristine `proposed + not-started` duplicates may fold into one canonical Intervention;
   - pristine duplicates may fold into one matching human-decided/progressed Intervention;
   - conflicting human-decided duplicates are preserved rather than silently merged.
7. `proposed_at` remains the earliest known proposal timestamp for compatibility.
8. New or lazily upgraded Interventions may also carry:
   - `first_proposed_at`;
   - `last_proposed_at`;
   - `proposal_count`.
9. Re-applying the exact same proposal timestamp is idempotent and does not increment `proposal_count`.
10. A later proposal timestamp increments `proposal_count` once and advances `last_proposed_at`.
11. Re-proposal never overwrites human decision or delivery/effectiveness status.
12. An accepted, rejected, deferred, applied, effective, or retired Intervention therefore remains the same durable object when resurfaced.
13. A materially different kind or summary creates a new Intervention.

The repository owner approved fixing the repeated-proposal behavior from real dogfood feedback on 2026-10-06.

## Delivery and validation

Validated in PR #24.

Evidence:

- unit regressions cover semantic re-proposal reuse and exact replay idempotency;
- a later weekly proposal increments only proposal metadata;
- accepted/rejected/deferred decisions remain unchanged;
- applied status is preserved across re-proposal;
- legacy canonical Intervention IDs remain unchanged while safe bug-created duplicates are coalesced;
- one human-decided Intervention absorbs only pristine proposed duplicates;
- conflicting human-decided duplicates are not auto-coalesced;
- materially different proposals still create separate Interventions;
- integration regression confirms repeated weekly `apply-review` calls leave `intervention_count == 1`;
- GitHub Actions passes on Ubuntu (Python 3.10 and 3.13), Windows (Python 3.11), and macOS (Python 3.11);
- PDDR validation passes.

## Consequences

Benefits:

- Ledger status remains bounded instead of growing one duplicate proposal per week;
- a human decision stays attached to one durable recommendation;
- repeated recommendation pressure remains observable through `proposal_count` and timestamps;
- old ledgers can adopt the behavior lazily without bulk migration or rewriting the canonical identifier.

Accepted constraints:

- summary normalization is not semantic NLP; materially equivalent but differently worded recommendations may still be distinct;
- punctuation changes remain distinct by design;
- retrying a previously rejected recommendation does not silently reset it to proposed;
- explicitly reviving a rejected/retired recommendation requires a future explicit lifecycle action or a materially changed proposal.

## Revisit when

Revisit if dogfood shows that text normalization is too weak/strong, one semantic Intervention needs multiple concurrent variants, or explicit revival/reconsideration needs a first-class lifecycle action.

## Evidence

- Issue #23
- `src/agent_kpt/ledger.py`
- `schemas/v0alpha1/ledger.schema.json`
- `tests/test_ledger.py`
- `tests/test_workflow.py`

## Related records

- PDDR-0003: Stateful improvement ledger lifecycle
- PDDR-0006: Dogfood hardening for privacy-safe actionable reports
