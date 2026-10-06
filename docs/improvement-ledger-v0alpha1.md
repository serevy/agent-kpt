# Improvement ledger v0alpha1

The ledger turns KPT from a sequence of reports into a stateful improvement loop.

## Three durable objects

- **Problem** — a recurring signal with a stable ID derived from its fingerprint.
- **Evidence** — inspectable provenance for observations across sessions/root lineages and environments.
- **Intervention** — a proposed or applied change with separate human decision and delivery/effectiveness state.

## Why two states for an intervention?

Human approval and implementation outcome are different facts.

Example:

```text
decision = accepted
status   = not-started
```

Later:

```text
decision = accepted
status   = effective
```

An intervention may also be rejected, deferred, ineffective, revised, or retired without rewriting its history.

## Intervention identity and re-proposal

Within one Problem, an intervention is treated as the same proposal when its intervention kind and normalized summary are the same.

Repeated weekly proposals reuse the existing intervention instead of creating a new pending row. New/updated interventions may record:

- `first_proposed_at`
- `last_proposed_at`
- `proposal_count`

The legacy `proposed_at` field remains the original proposal timestamp.

Re-applying the exact same report period is idempotent. A later report period increments `proposal_count` once and advances `last_proposed_at`.

Re-proposal never resets human authority or delivery state: an already accepted, rejected, deferred, applied, effective, or retired intervention remains in that state. A materially different kind/summary creates a distinct intervention.

Existing ledgers keep the canonical stored Intervention ID; identity matching is semantic so old timestamp-derived IDs do not need rewriting.

If an old ledger already contains duplicate semantic Interventions created by the timestamp-based bug, agent-kpt may lazily coalesce only safe duplicates:

- `proposed + not-started` duplicates are folded into one canonical Intervention and converted into proposal history;
- when one matching Intervention already carries a human decision or progressed status, pristine proposed duplicates fold into that canonical object;
- conflicting human-decided duplicates are preserved for manual resolution rather than silently merged.

## Recurrence

A problem becomes `recurring` after evidence exists in at least two independent `root_lineage_id` values. Repeated observations inside one fork lineage remain visible evidence but do not independently trigger recurrence.

## Keep graduation

An effective intervention can enter Keep reinforcement:

```text
reinforcing -> habituated -> graduated
```

Graduation means the useful behavior no longer needs routine attention in the top KPT report. The historical evidence remains in the ledger.

## Environment revalidation

An effective intervention stores the environment in which it was validated. The reference implementation compares these fields when present:

- model / model family
- harness / harness version
- adapter / adapter version
- skill/config version
- runtime
- OS

A material change marks the intervention/problem as `needs-revalidation`; it does not automatically claim the old intervention is wrong.

## Retirement

Interventions have an explicit `retired` status and reason. Problems can also be retired with a reason and timestamp. Retirement preserves history rather than deleting the old rule/workaround.

## Contract boundary

- Schema: `schemas/v0alpha1/ledger.schema.json`
- Python reference helpers: `src/agent_kpt/ledger.py`

The schema/lifecycle is still v0alpha1 and is under review in PDDR-0003.
