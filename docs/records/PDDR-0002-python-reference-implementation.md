---
id: PDDR-0002
title: Python reference implementation with language-neutral core
decision_date: 2026-09-28
recorded_date: 2026-09-28
decision_status: accepted
delivery_status: validated
scope:
  - project
  - process
owners:
  - serevy
evidence:
  - https://github.com/serevy/agent-kpt/issues/2
related:
  - PDDR-0001
supersedes: []
superseded_by: null
---

# PDDR-0002: Python reference implementation with language-neutral core

## Summary

Use Python as the first official reference implementation for provider adapters, deterministic metrics, and CLI tooling while keeping the normalized core contract language-neutral.

## Context and observations

The project should run across Windows, macOS, and Linux without making Node.js or an OS-specific runtime part of the core requirement.

The accepted PDDR-0001 contract already separates provider-specific parsing from the normalized Session/Event schema. The implementation language can therefore be chosen independently from the contract.

Python is already present in this repository through PDDR Kit validation and provides cross-platform standard-library support for JSON, paths, dates, CLI parsing, and local file processing.

## Options considered

### Option A — Python reference implementation

- Description: implement the first adapter, metrics engine, and CLI in Python.
- Benefits: cross-platform, low dependency surface, good fit for local JSONL/file analysis, aligns with existing repository tooling.
- Costs / constraints: users still need a supported Python runtime.
- Status: accepted

### Option B — TypeScript / Node.js reference implementation

- Description: make Node.js the first runtime dependency.
- Benefits: strong ecosystem and easy web integration later.
- Costs / constraints: adds a second runtime to a repository that already uses Python; unnecessary for the first local telemetry pipeline.
- Status: considered

### Option C — Bind the public core contract to Python types

- Description: treat Python classes as the canonical API instead of the JSON Schema contract.
- Benefits: less duplication for Python-only consumers.
- Costs / constraints: weakens provider/runtime neutrality and makes future non-Python implementations harder.
- Status: rejected

## Decision

Python is the first official reference implementation.

The JSON Schema and documented semantics remain the canonical language-neutral compatibility boundary. Python-specific types, modules, package layout, and CLI structure are implementation details unless separately promoted to a stable public API.

The reference implementation should prefer the standard library where practical and avoid OS-specific assumptions. Cross-platform CI must include Windows, macOS, and Linux.

## Delivery and validation

Validated in PR #8.

Evidence:

- six unit/regression tests pass;
- the synthetic Claude Code fixture reproduces the existing core golden metrics;
- unknown record types fail soft with recoverable diagnostics;
- raw prompt/assistant/tool/error content is excluded from normalized telemetry;
- inherited duplicate model-call history is distinguished from new calls;
- GitHub Actions passes on Ubuntu (Python 3.10 and 3.13), Windows (Python 3.11), and macOS (Python 3.11).

## Consequences

Benefits:

- one lightweight implementation path across major desktop/server OSes;
- no Node.js requirement for local retrospective generation;
- provider-neutral schemas can later be implemented in TypeScript, Rust, or another runtime without changing the core contract.

Accepted constraints:

- supported Python versions become part of the reference implementation's compatibility surface;
- OS neutrality still needs CI evidence rather than assumption;
- web-specific tooling can use another runtime later if justified.

## Revisit when

Revisit if Python installation becomes the main adoption barrier, performance becomes unacceptable for realistic transcript volumes, or another runtime materially improves packaging/distribution without weakening the language-neutral contract.

## Evidence

- Issue #2
- PDDR-0001
- Python reference implementation PR and CI results

## Related records

- PDDR-0001: Provider-neutral normalized event core
