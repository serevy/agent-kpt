---
id: PDDR-0005
title: Skill-first one-command workflow
decision_date: 2026-09-29
recorded_date: 2026-09-29
decision_status: accepted
delivery_status: in-progress
scope:
  - project
  - process
  - product
owners:
  - serevy
evidence:
  - https://github.com/serevy/agent-kpt/issues/12
  - https://github.com/anthropics/claude-plugins-official/blob/main/plugins/example-plugin/skills/example-command/SKILL.md
  - https://github.com/anthropics/claude-plugins-official/blob/main/plugins/session-report/skills/session-report/SKILL.md
related:
  - PDDR-0001
  - PDDR-0002
  - PDDR-0003
  - PDDR-0004
supersedes: []
superseded_by: null
---

# PDDR-0005: Skill-first one-command workflow

## Summary

Use a user-invoked Agent Skill as the first daily entrypoint while keeping the Python core and report contracts provider-neutral.

The default experience is `/agent-kpt` for weekly review, with `monthly` and `status` as explicit modes.

## Context and observations

The core, ledger, and report renderer existed before a comfortable day-to-day entrypoint.

Current Claude Code plugin examples support user-invoked `skills/<name>/SKILL.md` entries as slash-command-style workflows, while legacy `commands/*.md` remains compatible.

The project also needs the same Python core to remain usable from Codex, OpenCode, direct CLI use, and future adapters.

Real Claude Code transcript parsing has additional concerns beyond the synthetic baseline:

- one API response can appear as several assistant JSONL records;
- resumed/forked history can replay entry UUIDs;
- subagent transcripts live below the parent session;
- Skill/slash invocation metadata can be extracted without persisting full prompt text.

## Options considered

### Option A — Claude-only command implementation

- Description: put all behavior in a Claude Code slash-command prompt.
- Benefits: short path to a demo.
- Costs / constraints: duplicates metrics/ledger logic and makes other harnesses second-class.
- Status: rejected

### Option B — Skill wrapper over the Python reference core

- Description: Skill orchestrates deterministic CLI preparation, semantic composition, optional copy polish, rendering, and ledger actions.
- Benefits: simple UX with provider-neutral core; easy to add other harness entrypoints later.
- Costs / constraints: requires both orchestration instructions and CLI contracts.
- Status: accepted

### Option C — Automatically persist raw conversation content for better semantic analysis

- Description: build richer report packets containing prompt/assistant/tool content.
- Benefits: more context for semantic interpretation.
- Costs / constraints: expands privacy exposure and artifact sensitivity.
- Status: rejected for the default path

## Decision

1. `skills/agent-kpt/SKILL.md` is the first interactive entrypoint.
2. Default invocation is weekly; explicit modes are weekly / monthly / status.
3. The Skill invokes Python for deterministic discovery, normalization, metrics, local state, validation, and rendering.
4. Semantic composition remains outside deterministic arithmetic.
5. The default analysis packet does not persist raw prompt text, assistant text, or tool input/output.
6. Current-project transcript discovery uses transcript `cwd` metadata and includes child subagent transcripts.
7. Automatic lineage uses shared serialized UUIDs and parent transcript structure; message-level `parentUuid` is not promoted to session ancestry.
8. Split assistant records for one request are collapsed before model-call accounting.
9. Semantic ledger actions may only reference evidence IDs already present in the packet.
10. New interventions remain `proposed`; the Skill never accepts an intervention on the user's behalf.
11. A repo-local launcher keeps plugin testing portable without making a package install mandatory.

The repository owner approved continuing with this entrypoint on 2026-09-29.

## Delivery and validation

In progress in Issue #12.

Planned evidence:

- realistic split-response / resumed-history adapter regression;
- current-project transcript discovery fixture;
- privacy-safe packet regression;
- local ledger apply/status regression;
- Skill/plugin manifest;
- Windows / macOS / Linux CI.

## Consequences

Benefits:

- daily use becomes one command;
- deterministic facts stay testable outside the agent;
- Claude Code integration does not become the core architecture;
- the default packet is safer to persist than raw transcripts;
- other harnesses can implement their own entrypoint around the same contracts.

Accepted constraints:

- semantic coaching quality is limited by privacy-safe metadata unless a future explicit opt-in content-analysis mode is added;
- Skill orchestration must keep temporary files clean;
- plugin distribution/publishing is separate from local plugin functionality.

## Revisit when

Revisit if privacy-safe metadata is too weak for useful coaching, a standard cross-agent Skill packaging format becomes dominant, or local state needs a different storage boundary.

## Evidence

- Issue #12
- `skills/agent-kpt/SKILL.md`
- `src/agent_kpt/workflow.py`
- `src/agent_kpt/review.py`
- `tests/test_adapter_realistic.py`
- `tests/test_workflow.py`

## Related records

- PDDR-0001: Provider-neutral normalized event core
- PDDR-0002: Python reference implementation with language-neutral core
- PDDR-0003: Stateful improvement ledger lifecycle
- PDDR-0004: Progressive disclosure coaching report
