# Core schema v0alpha1

These JSON Schemas define the language-neutral boundaries used by agent-kpt.

- `session.schema.json` — concrete session identity and lineage
- `event.schema.json` — normalized event, history role, optional recurrence fingerprint
- `adapter-result.schema.json` — normalized sessions/events plus fail-soft diagnostics
- `ledger.schema.json` — stateful Problem / Evidence / Intervention lifecycle
- `report-view.schema.json` — concise summary-first report surface plus drill-down evidence
- `analysis-packet.schema.json` — privacy-safe deterministic packet handed to semantic composition
- `review-actions.schema.json` — evidence-bound Problem / proposed-Intervention actions written back to the ledger
- `classifier-rules.schema.json` — optional versioned local literal-match rules, used after common/provider rules

The schemas use raw GitHub URLs as canonical `$id` values so relative `$ref` resolution remains machine-readable outside the GitHub UI.

`v0alpha1` is intentionally unstable. Runtime implementation language is not selected by these schemas.

## Locale and presentation

New analysis packets include `report_contract.locale` and `locale_source` (`explicit`, `environment`, `conversation`, or `default`). Resolution is `--locale > AGENT_KPT_LOCALE > --conversation-locale > en-US`; see [workflow policy](../../docs/one-command-workflow.md). Report composition copies the resolved locale into the report view's `locale` and writes prose in that language. Locale does not change schema keys, enum values, fingerprints, evidence IDs, or lifecycle state.

The renderer supports Japanese and English labels, with English labels for other locales. It preserves composed prose rather than translating it.

## Classification provenance

Error-like event payloads, analysis Evidence, and report detail Evidence carry normalized `category`, `subtype`, `outcome`, `tool`, `rule_id`, `rule_scope`, `ruleset_version`, and `provider_version` when available. Outcomes distinguish `failure`, `blocked`, `waiting`, `warning`, `transient`, and `unknown`; the provider error flag alone is not proof of failure. Raw error text is excluded from the default persisted pipeline.

Local classifier rules use first-match `common -> provider -> user -> unknown` precedence and case-insensitive literal substring matching. See [rule format and configuration](../../docs/classifier-rules.md).

Review actions reference packet Evidence IDs and create/update Problems and proposed Interventions. Ledger evidence preserves source and environment provenance; full classifier detail remains in the packet/report. Re-proposal history uses `first_proposed_at`, `last_proposed_at`, and `proposal_count` while preserving original `proposed_at` and human decisions. See [ledger lifecycle](../../docs/improvement-ledger-v0alpha1.md).
