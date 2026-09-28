# Weekly KPT — synthetic fixture

> This is a behavioral fixture, not a benchmark result.

## Summary

| Area | Observation | Next step |
| --- | --- | --- |
| Keep | Cache reuse stayed high in the two independent root sessions. | Keep the current session continuity pattern. |
| Problem | A path-quoting failure appeared in one root lineage and its fork. | Do not report this as two independent recurrences. |
| Try | The known-location refactor needed little exploration. | For similarly bounded tasks, continue giving the exact target when known. |

## Keep

- The bounded refactor completed without tool errors and without unnecessary broad search.
- The investigation session used an expert consultation only at a decision point instead of moving the whole task to a stronger model.

## Problem → suggestion

### Path quoting

Raw transcript view shows two occurrences, but both belong to `root-a`.

**Interpretation:** one root incident with a forked repetition, not two independent recurring failures.

**Suggestion:** preserve both raw and lineage-deduplicated counts.

## Human / operator coaching

The fixture intentionally contains two different prompt situations:

- known-location refactor → a precise target can reduce unnecessary exploration;
- cause-unknown investigation → broad exploration can be appropriate.

Do not turn either into a universal prompting rule.

## Evidence

See `session-metrics.json`.
