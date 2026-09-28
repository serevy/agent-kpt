# Claude Code adapter fixture v0alpha1

Synthetic-only fixture for the Python reference adapter.

It intentionally contains:

- one root session and one fork in the same lineage;
- one independent session;
- one assistant record copied into the fork to exercise inherited-history detection;
- two path-quoting errors in one root lineage;
- one unknown future record type to exercise fail-soft diagnostics;
- `SECRET` strings in raw prompt/assistant/tool/error data to verify that normalized telemetry does not copy raw content.

`lineage.json` is an explicit hint file. The adapter does **not** treat message-level `parentUuid` as session lineage.
