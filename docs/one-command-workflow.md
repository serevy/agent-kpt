# One-command workflow

The default worker entrypoint is intentionally small:

```text
/agent-kpt
/agent-kpt weekly
/agent-kpt monthly
/agent-kpt status
```

The Skill is orchestration, not the core.

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
