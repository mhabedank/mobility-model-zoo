# Contract: `zoo roadmap`

A sub-app of `zoo`, registered like `zoo site`. Exit code 0 on success, 1 on any finding, with one line per finding on stderr (`<id> <where> <detail>`).

## `zoo roadmap check`

Runs RM1–RM8 ([checks.md](checks.md)) without building the site. Prints the RM6 warning if it applies. Meant for pull requests that touch only the roadmap.

## `zoo roadmap pace QUARTER [--write]`

- `QUARTER`: a closed quarter id, for example `2026-Q4`. A quarter that has not ended yet is refused unless `--draft` is given; a draft report is marked "draft" and is never written.
- Without `--write`: prints the report ([pace-report.md](pace-report.md)) as Markdown to stdout.
- With `--write`: writes `zoo/roadmap/reviews/QUARTER.md`. If the file exists, the generated sections are replaced and the hand-written `## Re-planning` section is kept.
- Reads only the repository: the current roadmap record and the release records. The record keeps each entry's first planned horizon and dates every move and drop, so edits made after the quarter do not change its report.

## `zoo site build` / `zoo site check`

Unchanged interface. Build runs RM1–RM8 and renders `roadmap/index.html`; check adds RM9.

## Environment

- `ZOO_TODAY=YYYY-MM-DD` sets today for RM6, RM7 and `pace` (tests and rehearsals); unset means the UTC date.
