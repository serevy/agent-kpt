# Core schema v0alpha1

These JSON Schemas define the language-neutral boundaries used by agent-kpt.

- `session.schema.json` — concrete session identity and lineage
- `event.schema.json` — normalized event, history role, optional recurrence fingerprint
- `adapter-result.schema.json` — normalized sessions/events plus fail-soft diagnostics
- `ledger.schema.json` — stateful Problem / Evidence / Intervention lifecycle
- `report-view.schema.json` — concise summary-first report surface plus drill-down evidence
- `analysis-packet.schema.json` — privacy-safe deterministic packet handed to semantic composition
- `review-actions.schema.json` — evidence-bound Problem / proposed-Intervention actions written back to the ledger

The schemas use raw GitHub URLs as canonical `$id` values so relative `$ref` resolution remains machine-readable outside the GitHub UI.

`v0alpha1` is intentionally unstable. Runtime implementation language is not selected by these schemas.
