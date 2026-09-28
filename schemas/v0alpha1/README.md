# Core schema v0alpha1

These JSON Schemas define the language-neutral boundary between provider adapters and the agent-kpt core.

- `session.schema.json` — concrete session identity and lineage
- `event.schema.json` — normalized event, history role, optional recurrence fingerprint
- `adapter-result.schema.json` — normalized sessions/events plus fail-soft diagnostics

The schemas use raw GitHub URLs as canonical `$id` values so relative `$ref` resolution remains machine-readable outside the GitHub UI.

`v0alpha1` is intentionally unstable. Runtime implementation language is not selected by these schemas.
