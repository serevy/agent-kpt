# Core metrics fixture — v0alpha1

> Synthetic contract fixture. This is not a benchmark.

## Lineage

| Metric | Value |
| --- | ---: |
| Raw sessions | 3 |
| Unique root lineages | 2 |

## Recurrence: `error:path-quoting`

| Metric | Value |
| --- | ---: |
| Raw occurrences | 2 |
| Unique sessions | 2 |
| Unique root lineages | 1 |
| Distinct days | 1 |
| Distinct weeks | 1 |

**Interpretation:** the signal appears twice in raw history, but it is one independent lineage-level incident.

## Model-call accounting

| Metric | Value |
| --- | ---: |
| Raw `model.call` events | 3 |
| Actual new calls | 2 |
| Inherited history events | 1 |
| Replayed history events | 0 |

Inherited/replayed transcript history is inspectable evidence, not new usage.

## Adapter compatibility

The fixture includes one recoverable `unsupported-record-shape` diagnostic.

Expected behavior: keep the normalized data that can be trusted, surface the diagnostic, and do not turn the unknown provider record into a normal KPT recurrence event.
