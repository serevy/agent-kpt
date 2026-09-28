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
