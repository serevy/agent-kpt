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
