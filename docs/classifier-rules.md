# Layered classifier rules

agent-kpt classifies error-like provider records locally before raw error text is discarded.

The classifier is layered:

```text
common rules
  -> provider / harness rules
  -> optional user / project rules
  -> unknown
```

The first matching layer wins.

User rules are intentionally the last layer. They fill gaps for local tools and project-specific states; they do not silently override built-in common or provider classifications.

## Normalized result

Classified error Evidence may retain:

- `category`
- `subtype`
- `outcome`
- `tool`
- `rule_id`
- `rule_scope` — `common`, `provider`, or `user`
- `ruleset_version`
- `provider_version`

Raw error text is not persisted by the default workflow.

## Outcome semantics

- `failure` — actionable failure candidate
- `blocked` — precondition, policy, or environment blocked the operation
- `waiting` — the tool/provider reports a state that should normally be waited on
- `warning` — warning/friction, not automatically a failed task
- `transient` — retryable/transient condition such as rate-limit or timeout
- `unknown` — insufficient deterministic classification evidence

A provider `is_error` flag therefore does not automatically mean `outcome = failure`.

## Local rule location

Run:

```sh
agent-kpt paths --project .
```

The returned `classifier_rules_path` defaults under:

```text
~/.agent-kpt/projects/<hashed-project-path>/classifier-rules.json
```

This keeps local tool patterns outside the target repository by default.

Override it with:

```text
AGENT_KPT_CLASSIFIER_RULES=/path/to/rules.json
```

or explicitly:

```sh
agent-kpt workflow prepare weekly --project . --classifier-rules /path/to/rules.json
agent-kpt ingest claude-code session.jsonl --classifier-rules /path/to/rules.json
```

## Rule format

Schema: `schemas/v0alpha1/classifier-rules.schema.json`

Example:

```json
{
  "schema_version": "agent-kpt.classifier-rules/v0alpha1",
  "ruleset_version": "my-project-v1",
  "rules": [
    {
      "id": "user.unity.compiling",
      "tool": "Bash",
      "contains_any": ["Unity is compiling", "Unity is reloading"],
      "category": "tool-state",
      "subtype": "unity-busy",
      "outcome": "waiting"
    },
    {
      "id": "user.pyenv.version-unset",
      "contains_any": ["no global or local python version has been set"],
      "category": "environment",
      "subtype": "python-version-unset",
      "outcome": "blocked"
    }
  ]
}
```

`tool` is optional. If omitted, the literal patterns may match any tool.

v0alpha1 user rules use case-insensitive literal substring matching only. Regex is intentionally not supported yet.

Invalid rule files/rules fail soft with classifier diagnostics. Valid rules in the same file continue to load when an individual rule is invalid.

## Versioning and revalidation

Built-in common and provider rules carry their own `ruleset_version`. Provider events also retain the observed provider/harness version when available.

Rule versions and provider versions are evidence/provenance, not numeric confidence scores. Environment changes should trigger revalidation rather than assuming an old classification rule is still correct.
