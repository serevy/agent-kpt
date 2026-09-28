# Core v0alpha1 fixture

This directory translates the sanitized baseline into the provider-neutral contract proposed by Issue #2.

- `adapter-result.json` — three normalized sessions, lineage-aware events, and one recoverable adapter diagnostic
- `expected-metrics.json` — deterministic raw vs deduplicated counts
- `expected-report.md` — human-readable rendering of the contract

The fixture deliberately preserves the baseline's forked path-quoting case:

- raw observations: 2
- concrete sessions: 2
- independent root lineages: 1

No real transcript, employer, project, or user data is included.
