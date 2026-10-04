# Project guidance

## GitHub Actions

When creating or changing CI:

- Choose triggers, paths, jobs, and matrix entries for the checks the change needs. Preserve required check names and failure detection when changing job routing or combining checks.
- Set explicit job timeouts based on observed runtimes; PDDR validation uses 5 minutes. Cancel obsolete read-only checks only within the same workflow and PR. Use a unique ref/run-ID group for non-PR runs so main and manual runs remain independent.
- Grant only the permissions each job needs. Keep untrusted PR validation separate from jobs that can write to the repository.
- Add dependencies, caches, and artifacts only when they provide a measured benefit. Choose cache keys and artifact retention deliberately; the standard-library PDDR validator needs no additional dependency or cache.
- Record the expected effect, workflow/job counts, validation results, and observed job durations in the PR. Distinguish runtime observations from billed usage.

PDDR workflows are an opt-in integration, outside the Kit's managed-file upgrade set. Adopt workflow updates explicitly using the [PDDR Kit adoption guide](https://github.com/serevy/pddr-kit/blob/main/docs/adoption.md#github-actions). This repository adopts the bounded CI defaults tracked in [PDDR Kit #47](https://github.com/serevy/pddr-kit/issues/47).
