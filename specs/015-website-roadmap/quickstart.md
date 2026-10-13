# Quickstart: validating the roadmap feature

How to prove that feature 015 works, end to end. Contracts: [checks.md](contracts/checks.md), [cli.md](contracts/cli.md), [pages.md](contracts/pages.md), [pace-report.md](contracts/pace-report.md). Record format: [data-model.md](data-model.md).

## Prerequisites

```bash
uv sync --extra release --group site-check
uv run playwright install chromium   # once; needed for preview images and browser checks
```

## 1. The record is valid

```bash
uv run zoo roadmap check
```

Expected: exit 0, no findings. Between 2026-12-18 and 2026-12-31 the RM6 warning names the end of `Q4 2026`.

## 2. Pages render and pass every check

```bash
uv run zoo site build
uv run zoo site check --a11y
uv run zoo site serve      # http://localhost:8000/mobility-model-zoo/roadmap/
```

Expected:

- `_site/roadmap/index.html` exists. It shows three columns (`Q4 2026`, `H1 2027`, `H2 2027`) with 6, 6 and 3 cards in the approved order, and the line "A plan, not a commitment. As of 12 October 2026."
- **Start page**: two published tiles (scout-large, picket-forest). Under "Coming next" there are 11 small cards. The heading reads "2 published · 11 coming next."
- **Navigation**: every page has "Roadmap" in the header.
- **Checks**: zero findings, RM9 and the preview image checks O1–O5 for `roadmap/` included.
- **Screens**: at 1440 × 900 all three columns are side by side; at 390 px the columns are stacked and nothing scrolls sideways (A5).

## 3. Faults fail the build (SC-004)

Each on a scratch copy of the repository, then `uv run zoo roadmap check`:

| Fault | Expected finding |
|---|---|
| delete the `pace-cnn` entry | `RM2 … pace-cnn is registered and unpublished but has no open entry` |
| add a seventh open entry to `2026-Q4` | `RM4 … 2026-Q4 holds 7 open entries, limit 6` |
| `text` with "2x faster" | `RM3 … literal number` |
| change `planned` of `hum-bearing` to `2027-Q1..Q2` and commit | `RM5 hum-bearing: planned was 2026-Q4 when the entry was added` |
| `ZOO_TODAY=2027-01-05` with the record unchanged | `RM6 … open entry in 2026-Q4, which ended 2026-12-31` |
| roll horizons to `2027-Q1`, `2027-Q2..Q3`, `2027-Q4..2028-Q1` without a review | `RM7 … no review for 2026-Q4` |
| `delivered_by: {model: picket-forest, version: 9.9.9}` | `RM8 … picket-forest 9.9.9 is not published` |

## 4. Pace report

On a scratch copy:
1. Publish one entry inside its horizon. In a test, set `published.published_at` in a fixture release record.
2. Move a second entry with a reason and drop a third.
3. Run:

```bash
ZOO_TODAY=2027-01-05 uv run zoo roadmap pace 2026-Q4
```

Expected:
- **Summary**: one entry delivered on time, one moved, one dropped. The delivery rate is shown as "1 of N", where N counts the entries due in Q4.
- **Due and not delivered**: lists the moved entry with its reason.
- **Unplanned releases**: lists any other release published in Q4.

With `--write`, the file `zoo/roadmap/reviews/2026-Q4.md` is created. Fill its "Re-planning" section, roll the horizons, and `zoo roadmap check` passes.

## 5. Automated tests

```bash
uv run pytest tests/website -q -k roadmap
uv run pytest tests/website -q          # the existing site tests, start page test updated
uv run pytest tests/website -q -m slow  # browser checks over all pages, roadmap included
```

## 6. Reader test (SC-001)

Show `/roadmap/` to at least three people who do not know the project. Within 60 seconds each should name:
- the next three planned releases;
- the period of one of them.

Note the result in the PR.
