# One-command workflow

The default worker entrypoint is intentionally small:

```text
/agent-kpt
/agent-kpt weekly
/agent-kpt monthly
/agent-kpt status
```

The Skill is orchestration, not the core.

No argument means `weekly`. Weekly and monthly preparation use rolling 7-day and 30-day windows respectively.

```text
Agent Skill
   ↓
Python workflow prepare
   ↓
privacy-safe analysis packet
   ↓
semantic composition
   ↓
Report View Model
   ↓
optional Japanese copy polish
   ↓
deterministic HTML / Markdown render
   ↓
proposed ledger actions
```

## Report locale policy

Resolve report language independently of the provider, coding tool, and documentation language:

| Priority | Input | `locale_source` |
| --- | --- | --- |
| 1 | `workflow prepare --locale` | `explicit` |
| 2 | `AGENT_KPT_LOCALE` environment configuration | `environment` |
| 3 | `--conversation-locale` supplied by the invoking agent | `conversation` |
| 4 | `en-US` | `default` |

There is no separate locale configuration file. The conversation hint describes the current user conversation; Python does not infer language from archived transcripts, the host tool, or the provider.

An empty environment preference is unset. Selected tags normalize case and underscores;
bare `ja` / `en` become `ja-JP` / `en-US`. Malformed selected tags fail visibly instead
of silently changing language. Validation is structural, not an IANA registry lookup.

```sh
agent-kpt workflow prepare weekly --project . --conversation-locale ja-JP -o packet.json
agent-kpt workflow prepare monthly --project . --locale en-US -o packet.json
```

The analysis packet carries `report_contract.locale` and `report_contract.locale_source`. Semantic composition must use that locale for report prose and the Report View Model's `locale`. Japanese copy polish is optional and applies only to Japanese copy. The renderer translates fixed labels for Japanese/English; other locales use English labels and retain the composed prose. Timezone selection remains independent (`--timezone`).

The English README remains canonical, with the Japanese README manually synchronized; this does not establish an English-only report default when a conversation hint is available.

## Review writeback

After composition, the Skill can record evidence-bound Problems and proposed Interventions:

```sh
agent-kpt apply-review review-actions.json packet.json --project .
```

Evidence IDs must exist in the supplied packet. Writeback records proposals, not human acceptance or implementation. Repeated proposals reuse existing intervention identity without resetting human decisions. See [ledger lifecycle](improvement-ledger-v0alpha1.md).

## Why Skill format

Current Claude Code plugin examples support user-invoked `skills/<name>/SKILL.md` workflows. The legacy `commands/*.md` layout remains compatible, but this repository uses the Skill layout for new work.

## Local plugin testing

The repository contains `.claude-plugin/plugin.json` and a portable launcher.

Claude Code's official plugin development examples use a local plugin-directory mode for testing. Use the equivalent plugin-dir command for the Claude Code binary installed in your environment and point it at this repository.

The Skill first tries an installed `agent-kpt` CLI and otherwise can call:

```sh
python "${CLAUDE_PLUGIN_ROOT}/scripts/agent-kpt.py"
```

No project files are modified to install Python dependencies.

## Persistent state and reports

Ledger, the last analysis packet, workflow temp files, and default reports live outside the target repository:

```text
~/.agent-kpt/projects/<hashed-project-path>/
  ledger.json
  last-packet.json
  classifier-rules.json  # optional
  work/
  reports/
```

Set `AGENT_KPT_HOME` to override the base state directory.

Set `AGENT_KPT_REPORT_DIR` to override the final report directory.

The project path is hashed before it becomes a state-directory name, so normal weekly/monthly runs do not add untracked agent-kpt files to the target Git repository.

## Privacy

The default analysis packet stores:

- deterministic metrics;
- safe Skill / slash-command / subagent labels;
- error fingerprints;
- message length counts;
- evidence IDs and source filenames;
- environment metadata.

It does not persist raw prompt text, assistant text, raw tool input/output, or raw error text.

For errors, the adapter may inspect raw text transiently on the user's machine and retain only deterministic derived classification such as category/subtype/tool/fingerprint. Repeated adapter diagnostics are aggregated before semantic composition, and individual user-message records stay out of detailed Evidence.

A future richer semantic mode must be an explicit opt-in rather than silently widening this boundary.

## Classification and report interpretation

Classification uses first-match precedence `common -> provider -> user -> unknown`. Configure optional local rules with `--classifier-rules`, then `AGENT_KPT_CLASSIFIER_RULES`, or the default `classifier_rules_path` returned by `agent-kpt paths --project .`. Local rules fill unmatched cases; they do not override built-in matches. Invalid rules fail soft with diagnostics.

Error-like records retain normalized outcome (`failure`, `blocked`, `waiting`, `warning`, `transient`, `unknown`) and rule provenance. A provider `is_error` flag must not be described as a confirmed actionable failure. Report details preserve category/subtype, outcome, tool, rule ID/scope, ruleset version, and observed provider version when available, without raw error text. See [classifier rules](classifier-rules.md) and [evaluation](classifier-evaluation.md).
