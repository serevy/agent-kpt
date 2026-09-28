# Baseline regression check

Until an executable provider-neutral evaluator exists, this fixture uses a small human-readable regression contract.

A future implementation may change internal schemas, commands, rendering technology, or provider adapters, but the following behaviors should remain explainable against the fixture.

## Required behaviors

1. **Separate telemetry from interpretation**
   - Numeric/session telemetry comes from deterministic processing.
   - KPT meaning is interpreted from that evidence.

2. **Weekly and Monthly have different roles**
   - Weekly focuses on near-term operational improvement.
   - Monthly focuses on recurring / structural patterns.

3. **Lineage is visible**
   - The two path-quoting observations in the fixture must not be described as two independent recurring incidents.
   - Raw occurrence count may remain 2.
   - Independent root-lineage incident count is 1.

4. **Human behavior is a first-class target**
   - The expected Weekly fixture contains task-dependent prompt-granularity coaching.
   - It must not become a universal rule such as “always provide exact file paths.”

5. **Keep can graduate**
   - A useful behavior may be reinforced while new.
   - A future ledger must be able to stop surfacing it once it becomes routine.

6. **Evidence remains inspectable**
   - A concise report may summarize the finding, but the underlying synthetic session evidence must remain reachable.

## Initial review procedure

For changes touching session semantics, recurrence, KPT classification, or report generation:

1. inspect `session-metrics.json`;
2. compare behavior with `expected-weekly.md`;
3. compare Monthly information hierarchy with `expected-monthly.html`;
4. record intentional behavior changes in the PR.

When the first executable evaluator is introduced, convert these checks into automated fixtures rather than keeping a second independent specification.
