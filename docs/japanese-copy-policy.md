# Japanese copy polish boundary

Japanese report copy may be polished by an external writing skill after the Report View Model has decided the facts.

A useful reference is [coji/natural-japanese](https://github.com/coji/natural-japanese), an MIT-licensed Agent Skill for readable Japanese work documents.

## Where a Japanese writing skill helps

It is a good fit for:

- the headline;
- the short summary;
- Keep / Problem / Try body text;
- trend commentary;
- plain-language explanations such as "what this number means."

It should make the wording easier to scan and more natural.

## What it must not change

A copy-polish step must not change:

- KPI values;
- raw occurrence counts;
- deduplicated / root-lineage counts;
- lifecycle or revalidation states;
- evidence IDs;
- timestamps;
- provenance;
- which Try was selected.

Those facts are frozen before copy polish.

## Dependency policy

`natural-japanese` is optional and is not a runtime dependency of agent-kpt.

The base report must remain useful with only the Python reference implementation. A Claude Code / Codex / other agent environment may invoke a Japanese writing skill when available, then write the polished text back into the same text fields before final rendering.

This keeps the core OS/provider-neutral and avoids making SudachiPy / uv / a particular agent skill mandatory for deterministic telemetry and reporting.

## Recommended order

```text
metrics + ledger + semantic interpretation
                |
                v
        Report View Model
       (facts are frozen)
                |
                +--> optional ja-JP copy polish
                |      e.g. natural-japanese
                |
                v
        HTML / Markdown renderer
```

The key rule is simple: **polish the sentence, not the evidence.**
