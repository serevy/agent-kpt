English | [日本語](README.ja.md)

# agent-kpt

**Retrospectives for human-agent workflows.**

`agent-kpt` is an experimental continuous-improvement toolkit for people working with coding agents.

It analyzes real session history, separates deterministic telemetry from semantic interpretation, and produces concise weekly / monthly KPT retrospectives for the whole working system:

- **Human** — prompt granularity, session boundaries, compact / fork / clear timing, model usage habits
- **Agent** — recurring failures, retries, missed instructions, unnecessary exploration
- **Tooling** — cache behavior, latency, scripts, commands, static checks, integrations
- **Workflow** — repeated manual work, handoffs, review loops, automation opportunities

The goal is not to score people or agents. The goal is to make the next week of work better.

## Core idea

```text
Coding-agent sessions
        |
        v
Provider adapter
        |
        v
Deterministic telemetry
        |
        v
Evidence / recurrence analysis
        |
        v
Weekly / monthly KPT
        |
        +--> Keep    reinforce useful patterns
        +--> Problem identify recurring friction
        +--> Try     suggest the next small improvement
        |
        v
Human review
        |
        v
Skill / Script / Config / Workflow changes
        |
        v
Next sessions
```

Useful behavior should eventually become normal behavior and disappear from the report. Model, CLI, or workflow updates can invalidate old lessons, so previously useful interventions should be revalidated instead of accumulating forever.

## Design principles

- **Deterministic first.** Count tokens, cache events, errors, latency, and tool activity with code when possible. Use an LLM for interpretation, not arithmetic.
- **Human-gated.** Reports recommend changes; they do not silently rewrite the operator's environment.
- **Evidence-backed.** Keep detailed supporting evidence even when the main report stays short.
- **Lineage-aware.** Forked / branched sessions must not inflate recurrence or usage metrics.
- **Provider-neutral core.** Claude Code is the first adapter, not the permanent architecture boundary.
- **Human + agent, not agent-only.** Operator habits, tooling, and workflow design are first-class improvement targets.
- **Adaptive, not additive.** Improvements need provenance, review dates, and retirement when the environment changes.
- **Local-first where practical.** Raw work history should stay under the user's control.

## Reports

The intended report shape is:

1. a short summary and KPI cards;
2. trend charts;
3. the highest-value Keep / Problem / Try items;
4. drill-down evidence only when needed.

A retrospective should save attention, not become another wall of text.

## Initial scope

The first public version will focus on:

- Claude Code session ingestion;
- weekly and monthly KPT;
- context / cache / latency / retry telemetry;
- session lineage / fork deduplication;
- recurring-problem and intervention ledgers;
- human-usage coaching around session boundaries and agent interaction;
- concise HTML + Markdown reports.

Later adapters may include Codex, OpenCode, Cursor, Hermes, and others.

## Non-goals

- automatically applying every suggested improvement;
- declaring one universal "best prompting style";
- treating correlation as causal proof;
- ranking individual developers;
- forcing one model/provider;
- replacing existing observability or code-review products.

## Status

Early extraction from a real, personally dogfooded workflow. Interfaces and schemas are not stable yet.

## License

MIT.

## Project decisions

This repository uses [PDDR Kit](https://github.com/serevy/pddr-kit) to preserve durable Project / Product / Process decisions and their evidence.

- Records: [`docs/records/`](docs/records/)
- Template: [`.pddr/template.md`](.pddr/template.md)
- Validate: `python .pddr/pddr.py validate --allow-empty`

PDDR is not a task log. Create or update a record only when a durable decision is made; installation alone does not require a decision record.

## Baseline

The pre-OSS workflow is preserved as a sanitized behavioral reference before generalization begins.

- [Baseline design](docs/baseline-v0.md)
- [Synthetic fixtures](fixtures/baseline-v0/)
- [Regression contract](fixtures/baseline-v0/regression-check.md)


## Python reference implementation

The normalized core contract stays language-neutral. Python is the first reference implementation for local ingestion and deterministic metrics.

Requirements: Python 3.10+.

```bash
python -m pip install -e .

agent-kpt ingest claude-code ~/.claude/projects/<project>/*.jsonl \
  --lineage-map lineage.json \
  -o normalized.json

agent-kpt metrics normalized.json -o metrics.json
agent-kpt report normalized.json -o report.md
```

The Claude Code adapter treats the on-disk JSONL format as unstable: known telemetry is normalized, unknown record shapes are reported as recoverable diagnostics, and raw prompt / assistant / tool content is not copied into normalized telemetry.

Session lineage is explicit. Message-level `parentUuid` is not assumed to mean parent *session*; callers may provide a lineage map when reliable lineage information is available.

The reference implementation is tested on Windows, macOS, and Linux. UTC reporting requires no external timezone data; other IANA timezones may require the `tzdata` package on platforms that do not provide an IANA timezone database.


## Concise coaching reports

The worker-facing report is intentionally smaller than the evidence behind it. It is designed for a quick scan, not as a scorecard.

Surface limits:

- up to 4 KPI cards;
- up to 3 Keep items;
- up to 3 Problem items;
- **one Next Try**;
- up to 3 trend notes;
- environment-change markers when relevant.

Detailed raw / deduplicated metrics and evidence remain available below the surface.

Render a Report View Model as HTML:

```bash
agent-kpt render-report fixtures/report-v0alpha1/report-ja.json \
  --format html \
  -o report.html
```

Or use the accessible Markdown fallback:

```bash
agent-kpt render-report fixtures/report-v0alpha1/report-ja.json \
  --format markdown \
  -o report.md
```

Japanese wording may optionally be polished by an external writing skill such as [natural-japanese](https://github.com/coji/natural-japanese). Copy polish happens **after facts are fixed** and must not change KPI values, lineage counts, lifecycle states, evidence IDs, timestamps, or provenance. See [Japanese copy polish boundary](docs/japanese-copy-policy.md).


## One-command workflow

The day-to-day entrypoint is an Agent Skill:

```text
/agent-kpt
/agent-kpt weekly
/agent-kpt monthly
/agent-kpt status
```

No argument means `weekly`.

The Skill keeps the interactive layer thin. Python discovers Claude Code transcripts for the current project, normalizes them, builds a privacy-safe analysis packet, and keeps the local improvement ledger. The invoking agent composes the concise report from that packet, then the deterministic renderer produces HTML and Markdown.

The default packet does **not** persist raw prompt text, assistant text, or raw tool input/output.

### Try the Skill from this repository

The Skill lives at [`skills/agent-kpt/SKILL.md`](skills/agent-kpt/SKILL.md). Install/copy that skill with your Agent Skill workflow to expose `/agent-kpt`.

For Claude Code plugin development, this repository also includes [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json) and a portable launcher. Claude Code's plugin development flow can load the cloned repository as a local plugin directory for testing; plugin-installed names may be namespaced by the host.

The Skill uses an installed `agent-kpt` CLI when available. When loaded from this repository as a Claude Code plugin, it can fall back to:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/agent-kpt.py" status --project .
```

Python 3.10+ is required. The Skill does not install dependencies into the user's project automatically.

Persistent state, workflow intermediates, and reports are stored outside the target repository by default:

```text
~/.agent-kpt/projects/<hashed-project-path>/
  ledger.json
  last-packet.json
  work/
  reports/
```

Set `AGENT_KPT_HOME` to override the base state directory.

Set `AGENT_KPT_REPORT_DIR` to override the final report directory.

Raw prompt text, assistant text, tool input/output, and raw error text are not persisted by the default analysis packet. Error text may be inspected transiently on the user's machine to retain only deterministic derived classification such as category/subtype/tool/fingerprint.

Repeated adapter diagnostics are aggregated before semantic composition, and detailed `user.message` entries are kept out of the Evidence packet while aggregate message statistics remain available.

See [One-command workflow](docs/one-command-workflow.md) for the architecture and privacy boundary.
