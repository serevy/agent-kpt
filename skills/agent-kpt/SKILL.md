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

## Resolve working paths

Before weekly/monthly work, run:

```sh
agent-kpt paths --project .
```

Read the returned JSON and use exactly:

- `work_dir` for intermediate JSON files;
- `report_dir` for final HTML/Markdown reports.

The `paths` command creates the state/work/report directories before returning them. If another caller bypasses `paths`, it must create the chosen work/report directories before writing.

Do not write agent-kpt temp/report files into the target repository.

The default report directory is under `~/.agent-kpt/projects/<hash>/reports/`.
`AGENT_KPT_REPORT_DIR` may override the report directory.

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
agent-kpt workflow prepare <weekly|monthly> --project . -o <work_dir>/packet.json
```

Read `<work_dir>/packet.json`.

If diagnostics say no transcripts matched the current project, stop with a concise explanation. Do not fabricate a KPT.

The packet does not persist raw prompt text, assistant text, raw tool input/output, or raw error text.

Error text may be inspected transiently by the local adapter only to derive privacy-safe fields such as `category`, `subtype`, `tool`, and a stable fingerprint.

## Compose the Report View Model

Create `<work_dir>/report.json` using `agent-kpt.report/v0alpha1`.

Keep the surface small:

- at most 4 KPIs;
- at most 3 Keep items;
- at most 3 Problem items;
- zero or one Next Try;
- at most 3 trends;
- no score / grade / rank / rating;
- details retain raw-vs-deduplicated recurrence and evidence;
- error Evidence copies `kind`, `session_id`, `category`, `subtype`, and `tool` from the analysis packet when available;
- include all packet error Evidence in `details.evidence`; the deterministic renderer groups it and selects representatives.

Translate internal facts into plain meaning. A worker should not need to understand `root_lineage_id`.

Keep must reinforce evidence-backed behavior. Problems must distinguish raw repetition from independent recurrence. Choose one small experiment for Next Try.

Surface environment changes when they could invalidate old advice.

For error-heavy reports, do not repeat dozens of identical “tool error” rows as the useful part of the drill-down. Prefer:

1. classification summary (path / permission / timeout / syntax / dependency / network / auth / rate-limit / unknown);
2. representative Evidence across distinct root lineages;
3. the full Evidence list only at the deepest drill-down.

Use the derived classification to make the Problem / Next Try actionable. Do not invent a more specific cause than the packet supports.

If `unknown/unknown` is the dominant error group, treat root cause as insufficient evidence:

- use `OBSERVE` / `WATCH` style wording rather than claiming a concrete cause;
- do not create a durable Ledger Problem from unknown-only evidence;
- explicitly mention limited classifier coverage;
- prefer one observation/classification-oriented Next Try over a speculative fix.

A smaller classified subgroup may still become a Problem when its own evidence is strong and lineage-aware.

## Create ledger actions

Create `<work_dir>/review.json`:

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
agent-kpt apply-review <work_dir>/review.json <work_dir>/packet.json --project . -o <work_dir>/ledger-result.json
```

## Optional Japanese polish

If the report is Japanese and `natural-japanese` is available, it may polish only headline/summary/card/trend text.

It must not change KPI values, raw/deduplicated counts, lifecycle state, evidence IDs, timestamps, provenance, or which single Next Try was selected.

Skip this step if unavailable.

## Render

```sh
agent-kpt render-report <work_dir>/report.json --format html -o <report_dir>/agent-kpt-report.html
agent-kpt render-report <work_dir>/report.json --format markdown -o <report_dir>/agent-kpt-report.md
```

If rendering fails, fix the Report View Model. Do not bypass validation.

## Clean up and respond

Delete only the intermediate files created in `<work_dir>` for this run:

- `packet.json`
- `report.json`
- `review.json`
- `ledger-result.json`

Keep the final reports in `<report_dir>`:

- `agent-kpt-report.html`
- `agent-kpt-report.md`

Tell the user the one-sentence takeaway, the single Next Try, and the absolute saved report paths. With `--details`, also mention the most important raw-vs-independent recurrence distinction, top error classifications, and any environment-change/revalidation marker.

Do not dump the whole evidence section into chat.
