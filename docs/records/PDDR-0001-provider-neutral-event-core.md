---
id: PDDR-0001
title: Provider-neutral normalized event core
decision_date: 2026-09-28
recorded_date: 2026-09-28
decision_status: accepted
delivery_status: validated
scope:
  - project
  - product
owners:
  - serevy
evidence:
  - https://github.com/serevy/agent-kpt/issues/2
  - docs/baseline-v0.md
related:
  - issue-2
supersedes: []
superseded_by: null
---

# PDDR-0001: Provider-neutral normalized event core

## Summary

Propose a provider-neutral normalized Session/Event contract between source-specific adapters and deterministic KPT metrics.

Claude Code remains the first adapter target, but its JSONL shape must not become the core architecture boundary.

## Context and observations

The sanitized baseline records a known lineage problem: three transcript/session files represent only two independent root lineages.

A path-quoting signal appears in a root session and its fork. Raw counting correctly sees two observations, but treating them as two independent recurrences would overstate the evidence.

The project also expects later adapters for other coding-agent harnesses, so source-specific transcript shapes should be isolated from KPT semantics.

No runtime implementation language has been selected yet.

## Options considered

### Option A — Keep Claude Code JSONL as the core model

- Description: let KPT logic read Claude-specific records directly.
- Benefits: shortest route to the first implementation.
- Costs / constraints: couples metrics and reporting to one evolving harness; makes lineage semantics harder to reuse.
- Status: rejected by this proposal

### Option B — Normalize provider records into Session/Event before metrics

- Description: provider adapters emit normalized sessions, events, and diagnostics.
- Benefits: provider-neutral core, explicit lineage, deterministic raw/deduplicated metrics, fail-soft compatibility handling.
- Costs / constraints: requires an adapter boundary and schema evolution policy.
- Status: proposed

### Option C — Convert everything directly into semantic KPT findings

- Description: skip a normalized event layer and let semantic analysis absorb provider differences.
- Benefits: fewer visible data structures.
- Costs / constraints: makes arithmetic, provenance, recurrence, and regression behavior harder to verify.
- Status: rejected by this proposal

## Decision

Accepted contract:

1. provider adapters own source transcript parsing;
2. adapters emit normalized Session/Event records plus diagnostics;
3. Session records carry root and parent lineage identity;
4. Event records distinguish observed, inherited, replayed, and derived history;
5. deterministic metrics expose both raw and lineage-deduplicated views;
6. unknown provider record shapes fail soft when trustworthy partial normalization remains possible;
7. runtime implementation language remains intentionally undecided.

The repository owner accepted this contract on 2026-09-28, with the expectation that it may be revised through a later PDDR if implementation evidence exposes problems.

## Delivery and validation

Validated through the Issue #2 Python reference implementation.

Delivery artifacts now include:

- JSON Schemas for Session, Event, and AdapterResult;
- a synthetic lineage fixture derived from baseline-v0;
- a Claude Code adapter behind the provider boundary;
- deterministic raw vs lineage-deduplicated metrics;
- fail-soft unknown-record handling;
- privacy regression coverage that excludes raw prompt/tool/error content from normalized telemetry;
- cross-platform tests on Ubuntu, Windows, and macOS.

The executable reference implementation reproduces the accepted core golden metrics, including raw path-error observations = 2 and independent root-lineage incidents = 1.

## Consequences

Benefits:

- Claude Code format changes can be contained in one adapter;
- future providers can reuse recurrence/report semantics;
- forked history no longer has to masquerade as independent recurrence;
- inherited transcript history can remain inspectable without inflating new model-call usage.

Accepted constraints if adopted:

- schema versioning becomes part of the public compatibility surface;
- adapters must preserve lineage and provenance as far as the source allows;
- some providers may not expose enough lineage detail for perfect deduplication.

This decision does not select Python, TypeScript, or another runtime.

## Revisit when

Revisit if:

- the first real Claude Code adapter cannot express important source semantics without provider-specific leakage;
- another provider exposes a fundamentally different lineage model;
- normalized event volume creates unacceptable storage/performance cost;
- the project chooses a runtime and discovers a simpler equivalent contract.

## Evidence

- Issue #2: Common Event Schema + lineage-aware session metrics
- `docs/baseline-v0.md`
- `fixtures/baseline-v0/session-metrics.json`
- `fixtures/core-v0alpha1/`

## Related records

None yet.
