---
name: agent-kpt
description: Run a concise weekly/monthly KPT retrospective for the current coding-agent project, or show the improvement-ledger status. Use when the user asks for "/agent-kpt", a weekly/monthly coding-agent retrospective, recurring workflow problems, or what to try next.
argument-hint: [weekly|monthly|status] [--details]
allowed-tools: [Bash, Read, Write, Edit, Skill]
---

# agent-kpt

Generate a short, evidence-backed retrospective for the current project.

The user invoked this skill with:

`$ARGUMENTS`

## Modes

- no arguments -> `weekly`
- `weekly` -> trailing 7 days
- `monthly` -> trailing 30 days
- `status` -> show the current local Problem / Intervention ledger
- `--details` -> include a little more drill-down in chat, while keeping the generated report structure unchanged

Do not invent additional modes.

## Resolve the CLI

Prefer the installed `agent-kpt` executable.

If it is not on PATH and this skill is running as a Claude Code plugin, use:

```sh
python "${CLAUDE_PLUGIN_ROOT}/scripts/agent-kpt.py" ...
```

If `python` is unavailable, try `python3`. Python 3.10+ is required.

Do not modify the user's project to install dependencies automatically.

## Status

For `status`, run:

```sh
agent-kpt status --project .
```

Explain active/recurring problems, interventions waiting for a decision or verification, Keep state, and anything needing revalidation.

Do not create a report or modify the ledger in status mode.

## Weekly / monthly preparation

Run:

```sh
agent-kpt workflow prepare <weekly|monthly> --project . -o .agent-kpt-packet.json
```

Read `.agent-kpt-packet.json`.

If diagnostics say no transcripts matched the current project, stop with a concise explanation. Do not fabricate a KPT.

The packet does not persist raw prompt text, assistant text, or raw tool input/output.

## Compose the Report View Model

Create `.agent-kpt-report.json` using `agent-kpt.report/v0alpha1`.

Keep the surface small:

- at most 4 KPIs;
- at most 3 Keep items;
- at most 3 Problem items;
- zero or one Next Try;
- at most 3 trends;
- no score / grade / rank / rating;
- details retain raw-vs-deduplicated recurrence and evidence.

Translate internal facts into plain meaning. A worker should not need to understand `root_lineage_id`.

Keep must reinforce evidence-backed behavior. Problems must distinguish raw repetition from independent recurrence. Choose one small experiment for Next Try.

Surface environment changes when they could invalidate old advice.

## Create ledger actions

Create `.agent-kpt-review.json`:

```json
{
  "schema_version": "agent-kpt.review/v0alpha1",
  "problems": []
}
```

For a Problem that should persist across reports, use:

```json
{
  "fingerprint": "stable-semantic-fingerprint",
  "title": "short problem title",
  "target_type": "human|agent|skill-instruction|script|workflow|config|tooling|environment|documentation|upstream|observe-only",
  "evidence_ids": ["existing-id-from-packet"],
  "next_try": {
    "kind": "workflow",
    "summary": "small proposed intervention"
  }
}
```

Every evidence ID must come from the packet. Keep fingerprints stable and specific. Do not create a ledger problem from weak speculation.

Ledger interventions remain `proposed`; never mark them accepted on the user's behalf.

After the report renders successfully, apply actions:

```sh
agent-kpt apply-review .agent-kpt-review.json .agent-kpt-packet.json --project . -o .agent-kpt-ledger-result.json
```

## Optional Japanese polish

If the report is Japanese and `natural-japanese` is available, it may polish only headline/summary/card/trend text.

It must not change KPI values, raw/deduplicated counts, lifecycle state, evidence IDs, timestamps, provenance, or which single Next Try was selected.

Skip this step if unavailable.

## Render

```sh
agent-kpt render-report .agent-kpt-report.json --format html -o agent-kpt-report.html
agent-kpt render-report .agent-kpt-report.json --format markdown -o agent-kpt-report.md
```

If rendering fails, fix the Report View Model. Do not bypass validation.

## Clean up and respond

Delete only:

- `.agent-kpt-packet.json`
- `.agent-kpt-report.json`
- `.agent-kpt-review.json`
- `.agent-kpt-ledger-result.json`

Keep:

- `agent-kpt-report.html`
- `agent-kpt-report.md`

Tell the user the one-sentence takeaway, the single Next Try, and the saved report paths. With `--details`, also mention the most important raw-vs-independent recurrence distinction and any environment-change/revalidation marker.

Do not dump the whole evidence section into chat.
