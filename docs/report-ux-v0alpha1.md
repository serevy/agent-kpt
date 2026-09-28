# Report UX v0alpha1 — teach without turning the report into homework

The default report should help a worker have a more comfortable coding-agent life. It is not a developer scorecard and it is not a lesson plan.

## Surface contract

The first screen answers five questions:

1. How did this week feel overall?
2. What worked?
3. What is worth watching?
4. What is the **one** small thing to try next?
5. Did the model / harness / environment change?

Everything else is drill-down.

The view model therefore caps the surface at:

- 4 KPI cards;
- 3 Keep cards;
- 3 Problem cards;
- 1 Next Try;
- 3 trend notes.

These are display limits, not evidence limits.

## Progressive disclosure

The report keeps raw counts, independent root-lineage counts, evidence provenance, diagnostics, and environment history. HTML places these under a collapsed `<details>` block. Markdown puts them after the main report under a separate details heading.

The worker does not need to learn the term `root_lineage_id` to benefit from it.

Surface copy should translate:

> raw occurrences = 8, unique root lineages = 2

into something like:

> 8回見えていますが、独立した作業で起きたのは2系統です。

The exact evidence remains available below.

## Coaching, not scoring

The report must not contain developer/agent scores, grades, ratings, ranks, or leaderboards.

Good behavior can be reinforced as Keep. A friction point can be described as a Problem. The report may suggest one Try. None of these is a judgment of the person's ability.

The Python reference validator rejects user-facing keys named `score`, `rating`, `grade`, or `rank`.

## One Small Try

A long improvement backlog belongs in the ledger, not on the worker's first screen.

The report surface exposes at most one `next_try`. The ledger may retain many proposed/rejected/deferred interventions, but the report chooses one small experiment for the current period.

## Evidence is never discarded

Conciseness means hiding detail until requested, not deleting it.

A report can show:

- "same failure appeared twice"

while still retaining:

- raw occurrences;
- unique sessions;
- unique root lineages;
- distinct days/weeks;
- evidence IDs and timestamps;
- source provenance;
- ingestion diagnostics.

## Rendering boundary

The Report View Model contains already-decided facts and copy. The renderer is deterministic. It does not reinterpret evidence.

This makes HTML / Markdown presentation replaceable without changing the KPT semantics.
