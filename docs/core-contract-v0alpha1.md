# Core contract v0alpha1

Issue #2 separates provider-specific transcript parsing from KPT semantics.

This document is intentionally language-neutral. It defines the normalized contract first; choosing the runtime implementation language is a separate decision.

## Boundary

```text
provider transcript / session store
            |
            v
provider adapter
  - understands source-specific shapes
  - preserves provenance
  - emits diagnostics for unknown shapes
            |
            v
normalized Session + Event
            |
            v
deterministic metrics
  - raw occurrence counts
  - unique sessions
  - unique root lineages
  - distinct days / weeks
  - new vs inherited/replayed model calls
            |
            v
semantic KPT interpretation
```

The core must not parse Claude Code JSONL directly. Claude Code is the first adapter, not the core data model.

## Session lineage

A normalized session has:

- `id`: one concrete session/transcript identity;
- `root_lineage_id`: identity shared by the original session and its descendants;
- `parent_session_id`: direct parent when the source exposes one.

A raw session count is therefore not an independent-attempt count.

For recurrence metrics, the minimum useful views are:

- raw occurrences;
- unique sessions;
- unique root lineages;
- distinct days;
- distinct weeks.

A finding that appears twice in a session and its fork can be `raw=2` while still being `unique_root_lineages=1`.

## Event history role

Every normalized event carries `history_role`:

- `observed` — newly observed in this concrete session;
- `inherited` — history inherited from an ancestor/fork;
- `replayed` — the harness replayed an earlier record;
- `derived` — deterministic processing produced the event from other evidence.

This prevents transcript length from being mistaken for new model/tool activity.

For model-call usage metrics:

```text
actual_new_model_calls
  = count(type == "model.call" && history_role == "observed")
```

Inherited or replayed `model.call` events remain inspectable but are excluded from "new call" usage.

## Fingerprints

`Event.fingerprint` is an optional stable grouping key for events that can be compared mechanically.

Examples:

- `error:path-quoting`
- `tool:timeout`

The core does not require every event to have a fingerprint. A semantic layer may later create richer findings, but deterministic recurrence must never pretend that unrelated events are identical merely because they share a broad type.

## Fail-soft adapter contract

Provider adapters return:

- normalized `sessions`;
- normalized `events`;
- `diagnostics`.

An unknown source record shape should normally produce a recoverable diagnostic such as `unsupported-record-shape` and ingestion should continue.

A whole input should fail only when the adapter cannot establish enough identity/provenance to produce trustworthy normalized data. Unknown optional fields are not a reason to abort.

Diagnostics are not silently converted into normal KPT events, so adapter compatibility noise cannot inflate user-facing recurrence metrics.

## Time buckets

Event timestamps use RFC 3339 date-times.

Distinct day/week metrics are computed in the report timezone. When a caller does not supply a timezone, UTC is the deterministic fallback. The timezone policy belongs to report configuration rather than a provider adapter.

## Baseline delta

The sanitized baseline intentionally contains three session files but only two independent root lineages.

The path-quoting signal appears twice in raw history and across two concrete sessions, but both belong to `root-a`.

The v0alpha1 contract therefore explains the old behavior without erasing it:

| View | Value |
| --- | ---: |
| Raw sessions | 3 |
| Unique root lineages | 2 |
| Raw path-quoting observations | 2 |
| Sessions containing path-quoting | 2 |
| Independent root lineages containing path-quoting | 1 |

This is the first explicit correction to the baseline's known fork/lineage overcounting limitation.

## Schemas and fixtures

- `schemas/v0alpha1/session.schema.json`
- `schemas/v0alpha1/event.schema.json`
- `schemas/v0alpha1/adapter-result.schema.json`
- `fixtures/core-v0alpha1/adapter-result.json`
- `fixtures/core-v0alpha1/expected-metrics.json`
- `fixtures/core-v0alpha1/expected-report.md`

These files define a contract, not a permanent stable API. The `v0alpha1` name is deliberate.
