# Baseline v0 — current personal workflow

This document freezes the behavior that already proved useful before `agent-kpt` was extracted as OSS.

It is a **reference baseline**, not the final architecture.

## Existing workflow

```text
Claude Code session JSONL
        |
        v
deterministic session scan
  - tokens
  - cache read/create
  - 5m / 1h cache creation
  - post-tool latency
  - errors
  - subagents
  - slash commands
  - skill invocations
        |
        v
weekly / monthly rollup
        |
        v
semantic KPT interpretation
        |
        +--> Keep
        +--> Problem -> suggestion
        +--> Try / immediate next actions
        |
        v
HTML / Markdown report
        |
        v
human decides what to change
```

## Weekly role

Weekly review is operational.

It focuses on:
- what worked recently;
- recurring friction visible within the last seven days;
- avoidable retries / repeated manual work;
- cache / context / latency observations;
- whether an existing command or Skill could have helped;
- small next actions.

The report may positively reinforce a useful behavior as **Keep**. Once that behavior becomes ordinary and no longer informative, it should stop surfacing.

## Monthly role

Monthly review is structural.

It focuses on:
- problems recurring across independent sessions and weeks;
- trends rather than one-off incidents;
- larger automation / scripting opportunities;
- whether previous interventions appear to be helping;
- context / cache / latency changes over a wider window.

Monthly is not just a longer Weekly report.

## Existing design choices worth preserving

### Deterministic first

Mechanical counting is done by code. An LLM interprets the resulting evidence.

The earlier implementation delegated mechanical session aggregation to a small model. That proved both expensive and inaccurate, so counting was moved into a deterministic scanner.

### Human gate

The report recommends changes but does not apply them.

A suggestion such as “this can probably be scripted” or “ask the agent to configure this once” is intentionally separated from implementation.

### Human behavior is in scope

The retrospective is not only about agent mistakes.

Examples:
- prompt specificity;
- when to investigate broadly vs point at an exact file/method;
- when to compact;
- when to fork / clear / start a new session;
- whether repeated work should become a command / script / Skill;
- whether a strong model was used where a normal model would have been enough.

### Keep is reinforcement, not permanent praise

A useful behavior can surface as Keep while it is being learned.
Once it becomes routine, it should graduate from the report.

### Old improvements can expire

A model, harness, CLI, cache policy, or tool update can make an old workaround unnecessary or harmful.
Improvements therefore need provenance and later revalidation.

## Known baseline limitations

These are intentionally **not hidden** by the OSS extraction.

1. **Fork / lineage overcounting**  
   The old scanner treated session files mostly independently. Forked histories may inflate occurrence and usage counts.

2. **Error sampling cap**  
   The old scanner retained only a bounded number of representative error snippets per session. A different late-session error class could therefore be missed by semantic analysis.

3. **Claude Code-specific transcript assumptions**  
   Paths and JSONL shapes come from one harness and can change.

4. **Report density**  
   The original HTML is useful but verbose. Public UX should separate concise summary from drill-down evidence.

5. **Correlation is not causation**  
   A lower error count after an intervention does not, by itself, prove the intervention caused the improvement.

## What Issue #1 freezes

The synthetic fixtures in `fixtures/baseline-v0/` preserve the intended semantics:

- deterministic telemetry exists separately from interpretation;
- Weekly and Monthly have different jobs;
- Human / Agent / Tool / Workflow are all valid improvement targets;
- Keep / Problem / Try are evidence-backed;
- detailed evidence remains available even when the top report is short.

Later Core work may change implementation details while keeping these behavioral contracts.
