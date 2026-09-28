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
