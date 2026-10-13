# Validation: Roadmap and upcoming models on the zoo website

Run on 2026-10-12 on branch `claude/015-website-roadmap` (cloud session, Linux, Chromium 1194 via Playwright). Guide: [quickstart.md](quickstart.md).

## 1. Record

`uv run zoo roadmap check` → `roadmap: ok (15 open entries)`, exit 0.

Rehearsals with `ZOO_TODAY`:

| Today | Result |
|---|---|
| 2026-12-20 | warning "Q4 2026 ends 2026-12-31 (11 days); after that the site build fails until the roadmap is reviewed", exit 0 |
| 2027-01-05 | `RM6 … open entry in 2026-Q4, which ended 2026-12-31` for each of the six Q4 entries, exit 1 |

## 2. Pages and checks

- **Build**: `uv run zoo site build` → `site: 8 pages, 6 images in 2.0 s, 2 models, 11 coming next`.
- **Checks**: `uv run zoo site check --a11y` passes every check:
  - facts: F1–F4;
  - links: L1, L2 (external links), L3;
  - privacy: P1, P3;
  - weight and language: S1, E1;
  - depth: D1–D5;
  - preview images: O1–O5;
  - accessibility: A (A1–A5, axe-core in light and dark mode);
  - RM9.

Screen measurements (Playwright, Chromium):

| Criterion | Measured | Target |
|---|---|---|
| SC-002 roadmap page at 1440 × 900 | three columns side by side; page height 1.99 screens (footer included) | ≤ 2 screens |
| SC-002 roadmap page at 390 px | `scrollWidth` 390, columns stacked, no sideways scroll | no horizontal scroll |
| SC-003 start page at 1440 × 900 | "Coming next" 306 px of a 804 px models section (38 %), below the published tiles | < 50 % |
| SC-006 | A1–A5, S1 and S2 pass on `roadmap/index.html` like on every page | zero violations |
| SC-007 | `zoo roadmap pace 2026-Q4 --draft` in 1.8 s | < 1 min |

What the pages look like:

- **Roadmap page, light mode**:
  - **Header**: eyebrow "Roadmap", the title "What comes next", and the line "A plan, not a commitment. As of 12 October 2026."
  - **Timeline band**: across the top, with the "now" dot early in Q4.
  - **Three columns**: Q4 2026 (6 entries), H1 2027 (6) and H2 2027 (3).
  - **Card styles**: updates (picket-forest, scout-large) have a dashed outline and a linked name. New models and first releases are framed with the mint accent bar.
  - **Chips**: "Planned" has a hollow dot and "In progress" a half-filled one. hum-fan shows "share-alike".
  - **Working names**: marked "(working name)". Open preconditions are shown in italics.
- **Dark mode**: the same layout on the dark tokens; the chips and the accent bar remain distinguishable.
- **Start page**:
  - **Tiles**: two published model tiles.
  - **"Coming next"**: 11 cards, six per row. Each has the topic eyebrow, the name, "working name" where it applies, and a horizon chip.
  - **Heading**: "2 published · 11 coming next."
  - **Link**: "See the roadmap →".

## 3. Faults (SC-004)

Each fault in quickstart section 3 is covered by an automated test with a deliberate fault (`tests/website/test_roadmap_record.py`, `test_roadmap_history.py`, `test_checks.py`, `test_roadmap_cli.py`):

- **RM2**: a registered model without an entry; an unknown model; the sandbox topic; a topic mismatch; an update of an unpublished model; a working name on a registered model.
- **RM3**: 21 words; a literal number; a 9-word precondition; a placeholder; a release-status word.
- **RM4**: a gap between horizons; a first horizon of two quarters; an inconsistent move; a move that was not recorded; an open entry outside the horizons; more than six open entries; dropped and delivered at once.
- **RM5**: a re-dated `planned` in a commit, and uncommitted.
- **RM6**: an ended horizon; 101 days old; a date in the future.
- **RM7**: a missing review; an empty "Re-planning" section.
- **RM8**: an unpublished `delivered_by`.
- **RM9**: a missing entry; a missing card; a wrong count.

## 4. Pace report

`tests/website/test_roadmap_pace.py` builds the quarter of quickstart section 4:
- picket-forest published 2026-11-20 is delivered on time;
- the reader test moved to H1 2027 with its reason;
- picket-signal dropped;
- scout-large 0.1.2 and 0.1.3 unplanned.

The report shows "1 of 2 entries due this quarter". A late delivery in Q1 2027 is reported with "41 d, 1 q". `--write` keeps the hand-written re-planning section.

Today's real draft (`zoo roadmap pace 2026-Q4 --draft`):
- 4 releases in Q4 so far, all unplanned, because they predate the roadmap;
- 0 of 6 due entries delivered.

## 5. Automated tests

| Run | Result |
|---|---|
| `uv run pytest tests/website -q` | 230 passed, 1 skipped |
| `uv run pytest tests/website -q -m slow` | all pass after updating the preview image counts in `test_og_render.py` (one more image: the roadmap page) |
| `uv run ruff check` | clean |
| `uv run pytest -q $(python3 scripts/ci/select_tests.py --guards)` | 21 passed, 2 skipped |
| `zoo validate --all` | ok |
| `zoo compliance check --ci` | ok |

## Constitution re-check (T053)

| Point | Result |
|---|---|
| No hand-written number on the site | RM3 rejects digits in entry texts; F2 passes for the new templates; the only numbers shown are the horizon labels and dates generated from the record |
| First planned horizon guarded | RM5 compares `planned` with the first commit that contained the entry |
| Delivery only from published records | `delivering_release` reads `published` release records only; RM8 rejects an unpublished `delivered_by` |
| Review gate before roll-over | RM7, tested |
| Usage class not guessed | the label is derived from `usage_class` of a registered model; working names show none |
| Releases never blocked by the roadmap | `zoo check` and the release pipeline do not import the roadmap |

Result: **PASS**.

## Open for the owner

- **SC-001 reader test**: show `/roadmap/` to at least three people who do not know the project and note whether each names the next three planned releases and the period of one of them within 60 seconds.
- **SC-008 first pace review**: after 2026-12-31:
  1. run `uv run zoo roadmap pace 2026-Q4 --write` and fill in "Re-planning";
  2. roll the horizons to `2027-Q1`, `2027-Q2..Q3`, `2027-Q4..2028-Q1` with recorded moves;
  3. set `as_of`.

  Until then the site build fails from 2027-01-01 (RM6), with a warning from 2026-12-17.
