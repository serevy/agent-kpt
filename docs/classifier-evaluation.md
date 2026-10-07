# Classifier evaluation protocol

Classifier improvement must not be measured by unknown-rate alone.

A broad catch-all can make `unknown` disappear while providing little actionable information.

## Required measurements

Evaluate candidate rules with at least:

- unknown rate;
- cause-bearing coverage;
- per-rule/category counts;
- manual precision sample;
- benign/waiting vs real-failure precision;
- near-miss false-positive rate;
- held-out user/project/time data when available.

Catch-all buckets such as generic `process` / exit-code-only classification do not count as cause-bearing coverage.

## Repository regression fixture

`fixtures/classifier-v0alpha1/eval.json` contains synthetic positive and near-miss cases.

It exists to prevent known regressions such as:

- `4290` in a path becoming HTTP 429;
- the word `timeout` in a path becoming a timeout classification;
- generic `Process exited with code 1` being promoted to a cause-bearing class;
- provider precondition rules being overwritten by local user rules.

The synthetic fixture is **not** evidence of cross-user/project generalization.

## Held-out evaluation

For a meaningful candidate evaluation:

1. freeze the candidate ruleset/version;
2. choose records that were not used to author those rules;
3. keep raw text local and ephemeral;
4. manually label a bounded sample for outcome/category correctness;
5. compare baseline vs candidate;
6. include near-miss negatives;
7. reject a candidate if precision/false positives regress materially;
8. do not promote solely because unknown rate decreases;
9. prefer cross-project/user data before broadening a provider-neutral rule;
10. human review remains required even after validation passes.

This follows the validation-gated direction tracked in Issue #16.

## Current v0alpha1 boundary

The repository fixture validates deterministic plumbing and known edge cases.

Real-world promotion of new broad rules remains evidence-driven dogfood/research work. Provider-specific and user/project rules can evolve without pretending that one person's historical logs establish universal accuracy.
