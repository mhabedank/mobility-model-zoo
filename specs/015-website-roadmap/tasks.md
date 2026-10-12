# Tasks: Roadmap and upcoming models on the zoo website

**Input**: Design documents from `/specs/015-website-roadmap/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Included. The checks RM1–RM9 and the pace report are deliverables of this feature (FR-018, FR-024, SC-004, SC-007), and every site check in this repository is covered by tests.

**Organization**: by user story of the spec (US1–US5). Check IDs refer to [contracts/checks.md](contracts/checks.md), decisions to [research.md](research.md) (R1–R12).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1–US5 from spec.md

---

## Phase 1: Setup

**Purpose**: the record, its schema and the test fixture.

- [X] T001 Create `zoo/roadmap/roadmap.yaml` with the initial record from the table "Initial record" at the end of this file: `as_of: 2026-10-12`, `since: 2026-Q4`, `horizons: [2026-Q4, 2027-Q1..Q2, 2027-Q3..Q4]`, 15 entries in the listed order, each with `planned` equal to `horizon`, no `moves`, `dropped` or `delivered_by`. Add the file to `REUSE.toml` coverage if `reuse lint` requires it
- [X] T002 [P] Copy `specs/015-website-roadmap/contracts/roadmap.schema.json` to `src/mobility_model_zoo/site/schemas/roadmap.schema.json` (identical content); make sure the package data includes it (check `pyproject.toml` package-data patterns for `schemas/*.json`)
- [X] T003 [P] Create the test fixture `tests/website/fixtures/registry/zoo/roadmap/roadmap.yaml`:
  - **Header**: `as_of: 2026-10-12`, `since: 2026-Q4`, the same three horizons as T001.
  - **Entries**, in this order:
    - `picket-forest`: kind `first-release`, `model: picket-forest`, topic `security`, stage `in-progress`, horizon `2026-Q4` (picket-forest is unpublished in the fixture);
    - `scout-large-reader-test`: kind `update`, `model: scout-large`, topic `productdev`, horizon `2026-Q4`;
    - `hum-bearing`: kind `new-model`, `working_name: true`, topic `condition-monitoring`, horizon `2027-Q1..Q2`, `precondition: "Data licence to be confirmed"`;
    - `picket-signal`: kind `new-model`, `working_name: true`, topic `security`, horizon `2027-Q3..Q4`.
  - **Texts**: each at most 20 words, without numbers.
- [X] T004 Add an autouse fixture to `tests/website/conftest.py` that sets the environment variable `ZOO_TODAY=2026-10-12` (via `monkeypatch.setenv`), so every website test runs with a fixed today (research R5); tests that need another date override it

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: reading the record, horizon arithmetic, delivery and the derived entry state, which every story uses.

**⚠️ CRITICAL**: no user-story work before this phase is complete.

- [X] T005 Create `src/mobility_model_zoo/site/roadmap.py` with horizon ids (data-model.md "Horizon id", research R2):
  - `Horizon` dataclass with `id`, `quarters` (list of `(year, q)`), `start` (date), `end` (date), `label` (str) and `months` (str, e.g. "October – December").
  - `parse_horizon(id) -> Horizon` accepts `YYYY-Qn`, `YYYY-Qa..Qb` with `b = a + 1`, and `YYYY-Q4..ZZZZ-Q1` with `ZZZZ = YYYY + 1`; it raises `ValueError` otherwise.
  - Labels: `Qn YYYY`; `H1 YYYY` for `Q1..Q2`; `H2 YYYY` for `Q3..Q4`; `Qa–Qb YYYY` (en dash) for other same-year pairs; `Q4 YYYY – Q1 ZZZZ` across a year.
  - `quarter_of(date) -> str` returns e.g. `2026-Q4`.
  - `quarters_between(a, b) -> list[str]` (inclusive).
  - `today() -> date`: the UTC date, or `ZOO_TODAY` (ISO date) when set.
- [X] T006 [P] Unit tests for T005 in `tests/website/test_roadmap_horizons.py`:
  - every grammar case and its label;
  - start and end dates, including `2027-Q4..2028-Q1` (end 2028-03-31);
  - rejected ids: `2027-Q2..Q4`, `2027-Q3..2028-Q1`, `2027-Q5`;
  - `quarter_of`, `quarters_between`;
  - `today()` with and without `ZOO_TODAY`.
- [X] T007 Add loading and RM1 to `src/mobility_model_zoo/site/roadmap.py`:
  - `load(reg) -> dict` reads `reg.zoo / "roadmap" / "roadmap.yaml"` (finding `RM1 zoo/roadmap/roadmap.yaml is missing` if absent).
  - It validates against `roadmap.schema.json` with the same `jsonschema.Draft202012Validator` and format checker as `context._schema_errors`.
  - It reports duplicate entry ids as `RM1 entries: duplicate id <id>`.
  - Findings are raised as `GateFailed` with lines `RM<n> <where> <detail>`.
- [X] T008 Add delivery and state derivation to `src/mobility_model_zoo/site/roadmap.py` (data-model.md "Derived per entry", research R3):
  - `delivering_release(reg, entry) -> (model, version) | None`:
    - `update` entries use `delivered_by`, if that version's record has `published.published_at`;
    - `first-release` and `new-model` entries with `model` use the lowest published version (`reg.published_versions`, `parse_version`).
  - `delivery_date(reg, entry) -> date | None` is the UTC date of `published.published_at`.
  - `state(reg, entry) -> "open" | "delivered" | "dropped"`.
  - `timing(entry, date) -> ("early" | "on time" | "late", slip_days | None, slip_quarters | None)` is computed against `parse_horizon(entry["planned"])`.
  - `usage_label(reg, entry)` maps the model's `usage_class`: `commercial-share-alike` → "share-alike", `non-commercial` → "non-commercial", otherwise `None`.
  - `motif_name(reg, entry)`: the `motif` of `zoo/models/<model>/site.yaml` if present, else `<model>.svg` if `src/mobility_model_zoo/site/static/img/motifs/<model>.svg` exists, else `None`.
- [X] T009 [P] Unit tests for T007 and T008 in `tests/website/test_roadmap_record.py`:
  - **RM1**: the fixture loads; a missing file gives `RM1`; an unknown key gives `RM1`; a duplicate id gives `RM1`.
  - **Delivery**: a `first-release` entry is delivered once its model has a published record, with the date from `published_at`; an `update` entry without `delivered_by` stays open.
  - **Timing**: early, on time and late, with slip days and quarters.
  - **State**: `dropped` wins.
  - **Usage label**: derived from the model's `usage_class`.
- [X] T010 Add `page_context(reg, record) -> dict` to `src/mobility_model_zoo/site/roadmap.py` (data-model.md "Page context"):
  - `as_of` (date and the display form "12 October 2026");
  - `horizons` (each with `id`, `label`, `months`, `start`, `end`, `is_first`, and its open entries in record order);
  - per entry: `id`, `name`, `working_name`, `model`, `topic_title` (from `reg.topic`), `kind`, `stage`, `text`, `precondition`, `usage_label`, `motif`, and `model_url` (`models/<model>/` for `update` entries only, FR-011);
  - `upcoming`: open `new-model` and `first-release` entries ordered by horizon, then record order, each with `horizon_label`;
  - `now_fraction`: the position of today inside the first horizon, between 0 and 1, for the timeline marker.

**Checkpoint**: the record loads, validates structurally and yields the page context.

---

## Phase 3: User Story 1 - See at a glance what the zoo releases next (Priority: P1) 🎯 MVP

**Goal**: the roadmap page `/roadmap/` with three horizons, compact cards, quieter updates, the plan line, and navigation from every page.

**Independent Test**: build the fixture site; `_site/roadmap/index.html` shows the three horizon labels in order, each entry once in record order with an element `id="<entry id>"`, the line "A plan, not a commitment. As of 12 October 2026.", the update entry with a link to `models/scout-large/` and the words "Update of scout-large", the working-name entry with "(working name)" and "Waits for: Data licence to be confirmed"; every page's header links `roadmap/`.

### Tests for User Story 1

- [X] T011 [P] [US1] RM3 and RM4 tests in `tests/website/test_roadmap_record.py`, each with a deliberate fault edited into the fixture via `site_env.edit_yaml`:
  - **RM3**: `text` of 21 words; `text` "Runs 2x faster" (literal number); `precondition` of 9 words; a `{metric:quality.x}` placeholder; the word "released" in `text`.
  - **RM4**: two horizons; a first horizon spanning two quarters; a gap between horizons; a moved entry whose last `to` differs from `horizon`; `horizon` differing from `planned` without moves; an open entry in a horizon not in the list; seven open entries in one horizon; an entry both `dropped` and delivered.
- [X] T012 [P] [US1] Page tests in `tests/website/test_roadmap_page.py` on `built`:
  - content and order as in the Independent Test;
  - update cards carry the class `entry-update`, new-model and first-release cards `entry-new`;
  - the stage chip text is "Planned" or "In progress";
  - "Nothing planned yet." appears for a horizon emptied in the fixture;
  - the page has one `h1` and `lang="en"`;
  - the page contains no `<script>` other than the deferred `assets/js/site.js`.

### Implementation for User Story 1

- [X] T013 [US1] Implement RM3 in `src/mobility_model_zoo/site/roadmap.py`, using `budgets.words`, `facts.NUMBER`/`facts.literal_numbers`, `budgets.PLACEHOLDER` and `budgets.STATUS_WORDS`:
  - "`text` ≤ 20 words, `precondition` ≤ 8 words, move and drop reasons ≤ 20 words";
  - no free-standing number, no `{metric:…}` placeholder, no release-status word in `text` or `precondition`;
  - findings as `RM3 <entry id>.<field> <detail>`.
- [X] T014 [US1] Implement RM4 in `src/mobility_model_zoo/site/roadmap.py`:
  - exactly three horizons: the first spans one quarter, the second and third two quarters each, consecutive without gaps;
  - `horizon == planned` without moves, else `horizon ==` the `to` of the last move;
  - move dates ascend;
  - an open entry's `horizon` is one of the three;
  - "at most 6 open entries per horizon" (constant `MAX_OPEN_PER_HORIZON = 6`);
  - not both dropped and delivered.
- [X] T015 [US1] Add `validate(reg, record, today) -> list[str]` to `src/mobility_model_zoo/site/roadmap.py` that runs RM1, RM3 and RM4 now and later RM2, RM5–RM8 (each a separate function), and call it at the start of `build()` in `src/mobility_model_zoo/site/build.py`, adding its findings to `failures`
- [X] T016 [US1] Create `src/mobility_model_zoo/site/templates/roadmap.html.j2` (extends `base.html.j2`) per [contracts/pages.md](contracts/pages.md) "/roadmap/":
  - **Head**: eyebrow "Roadmap", `h1` "What comes next", and the plan line with `as_of`.
  - **Timeline band**: an `aria-hidden="true"` `div.timeline` with three segments and a "now" marker positioned by `now_fraction` via an inline `style="--now:…"` custom property.
  - **Horizons**: three `section.horizon` with `h2` label, muted months and `ol.entries`.
  - **Entry card**: `li.entry.entry-new|entry-update` with `id`:
    - `h3` with the motif via `motif(name, 28)` and the name, linked to `../{{ model_url }}` for updates;
    - "(working name)" when it applies, and the topic eyebrow;
    - the text;
    - chips: kind words, a stage chip (`chip planned` | `chip progress`) and a usage chip;
    - "Waits for: …".
  - **Empty horizon**: "Nothing planned yet."
  - **Legend**: the line from the contract.
  - **No literal numbers** in template text (F2).
- [X] T017 [US1] Render the roadmap page in `build()` of `src/mobility_model_zoo/site/build.py`: `render("roadmap/index.html", "roadmap.html.j2", "../", "roadmap/", r=roadmap.page_context(reg, record))`, after the model pages and before the start page
- [X] T018 [P] [US1] Add "Roadmap" to the header navigation in `src/mobility_model_zoo/site/templates/base.html.j2` between "Models" and "Topics", `href="{{ root }}roadmap/"` (FR-012)
- [X] T019 [P] [US1] Add the roadmap styles to `src/mobility_model_zoo/site/static/css/site.css`, using only existing tokens (`--surface`, `--border`, `--border-strong`, `--mark`, `--muted`, `--text`, `--accent`) and no new colours:
  - `.timeline`: a line of three segments, the first a third of the width, and a `::after` "now" dot at `left: calc(var(--now) * 33.33%)`.
  - `.horizons`: a grid of one column, `repeat(3, 1fr)` from 960 px.
  - `.entry-new`: `card` look with a 4 px `--mark` left border.
  - `.entry-update`: transparent background, `1.5px dashed var(--border-strong)`, no accent.
  - Chips: `.chip.planned i` hollow; `.chip.progress i` half-filled with `linear-gradient(90deg, var(--mark) 50%, transparent 50%)`.
  - Focus and hover follow `.tile`.
  - At 390 px nothing overflows sideways (A5).

**Checkpoint**: US1 complete; the roadmap page builds and passes T011–T012.

---

## Phase 4: User Story 2 - Upcoming models as small cards on the start page (Priority: P1)

**Goal**: published tiles first, then "Coming next" small cards for every open new model and first release, the separate counts, and a link to the roadmap; one list of upcoming models (FR-019).

**Independent Test**: build the fixture site:
- **Start page**: the scout-large tile is there, but no tile for picket-forest (unpublished).
- **"Coming next"**: three small cards (picket-forest, hum-bearing, picket-signal) in horizon order. Each links `roadmap/#<id>`, shows name, topic and horizon label, and has no version and no digits apart from the horizon label.
- **Heading**: "1 published · 3 coming next."
- **Link**: "See the roadmap" links to `roadmap/`.

### Tests for User Story 2

- [X] T020 [P] [US2] Rewrite `tests/website/test_start_page.py::test_topics_and_tiles` for the new start page (no tile for picket-forest; picket-forest appears as a card) and add tests:
  - card order, links and content as in the Independent Test;
  - the heading counts;
  - an entry delivered by publishing its model (edit the fixture record of picket-forest to have `published`) leaves the cards and its tile appears;
  - `update` entries never appear as cards.
- [X] T021 [P] [US2] RM2 tests in `tests/website/test_roadmap_record.py`, each with a deliberate fault:
  - delete the `picket-forest` entry (a registered, unpublished model without an entry);
  - `model: no-such-model`;
  - `topic: sandbox`;
  - a topic that differs from the model's topic;
  - an open `update` entry for picket-forest (not published);
  - a `new-model` entry with `model` set and `working_name: true`.

### Implementation for User Story 2

- [X] T022 [US2] Implement RM2 in `src/mobility_model_zoo/site/roadmap.py` per [contracts/checks.md](contracts/checks.md) using `context.is_sandbox`, `context.status` and `reg.model_names()`. Every registered, non-sandbox model without a published version must have an open `first-release` or `new-model` entry naming it. Wire it into `validate()`
- [X] T023 [US2] Create `src/mobility_model_zoo/site/templates/partials/upcoming.html.j2` per [contracts/pages.md](contracts/pages.md) "/ start page":
  - `h3` "Coming next";
  - `div.mini-grid` of `a.mini` cards, each linking `roadmap/#<id>`, with the topic eyebrow, the name (plus "(working name)") and the horizon chip;
  - a link "See the roadmap →" to `roadmap/`;
  - no text sentence on the cards (FR-015).
- [X] T024 [US2] Change `src/mobility_model_zoo/site/templates/start.html.j2`:
  - the models heading becomes "{{ linked | length }} published · {{ upcoming | length }} coming next.";
  - the tile loop covers only models with status `published` or `deprecated`;
  - include `partials/upcoming.html.j2` after the tiles;
  - the hero button "Browse the models" is unchanged.
- [X] T025 [US2] Pass `upcoming=r["upcoming"]` from `build()` to the start page render in `src/mobility_model_zoo/site/build.py`, and change the build summary line to count "coming next" from the roadmap instead of `in_progress`
- [X] T026 [P] [US2] Add `.mini-grid` (`grid-template-columns: repeat(auto-fill, minmax(180px, 1fr))`, gap 12px) and `.mini` (compact card: padding 12px 14px, `--surface`, `1px solid var(--border)`, radius 10px, three short lines, focus ring like `.tile`) to `src/mobility_model_zoo/site/static/css/site.css`
- [X] T027 [P] [US2] Update `specs/008-zoo-website/contracts/site-tree.md` "/ start page" item 4 and the header navigation list to point at feature 015 ([contracts/pages.md](contracts/pages.md)): unpublished models appear as "Coming next" cards from the roadmap, not as tiles

**Checkpoint**: US1 and US2 together deliver the visible feature; the site builds on the real repository with the initial record.

---

## Phase 5: User Story 3 - The owner keeps the roadmap current with one edit (Priority: P2)

**Goal**: the history, staleness, delivery and rendered-parity checks (RM5, RM6, RM8, RM9), and `zoo roadmap check` for pull requests.

**Independent Test**: each fault in [quickstart.md](quickstart.md) section 3 except the RM7 row produces its finding and a non-zero exit of `zoo roadmap check`. Moving an entry with a recorded move changes only that entry's column on the page.

### Tests for User Story 3

- [X] T028 [P] [US3] RM5 test in `tests/website/test_roadmap_history.py`:
  - set up a git repository in the fixture copy: `git init`, commit the fixture;
  - change `planned` of `hum-bearing` and commit: `RM5 hum-bearing: planned was 2027-Q1..Q2 when the entry was added`;
  - a correct move (append to `moves`, change `horizon` only) passes;
  - without a git repository, RM5 passes.
- [X] T029 [P] [US3] RM6 and RM8 tests in `tests/website/test_roadmap_record.py`:
  - `ZOO_TODAY=2027-01-05` with an open entry in `2026-Q4` gives RM6;
  - `as_of` 101 days before today gives RM6, and 100 days does not;
  - `as_of` in the future gives RM6;
  - `ZOO_TODAY=2026-12-20` gives the warning and no finding;
  - `delivered_by: {model: scout-large, version: 9.9.9}` gives RM8.
- [X] T030 [P] [US3] RM9 tests in `tests/website/test_checks.py`:
  - on a built fixture site RM9 passes;
  - after removing an entry's `li` from `_site/roadmap/index.html`, reordering two entries, or removing a start-page card, RM9 reports it;
  - a heading count that differs from the cards shown is reported.
- [X] T031 [P] [US3] CLI test in `tests/website/test_roadmap_cli.py`: `zoo roadmap check` (typer `CliRunner`, cwd at the fixture copy, the same registry resolution as `zoo site`) exits 0 on the fixture and 1 with the RM2 fault, printing the finding line

### Implementation for User Story 3

- [X] T032 [US3] Implement RM5 in `src/mobility_model_zoo/site/roadmap.py`:
  - list the commits of `zoo/roadmap/roadmap.yaml` oldest first (`git -C <root> log --format=%H --reverse -- zoo/roadmap/roadmap.yaml`);
  - read each with `git show <sha>:zoo/roadmap/roadmap.yaml` and find each entry id's first appearance;
  - compare `planned`;
  - skip silently when the root is not a git repository or the file has no history;
  - cache the parsed history per root for one run.
- [X] T033 [US3] Implement RM6 in `src/mobility_model_zoo/site/roadmap.py`:
  - `as_of` must not be after today and must be at most 100 days before it (constant `MAX_AS_OF_AGE_DAYS = 100`);
  - no open entry may sit in a horizon whose `end` is before today;
  - a `warnings(record, today)` function returns the 14-day warning (constant `WARN_DAYS_BEFORE_END = 14`), which `build()` and `zoo roadmap check` print without failing.
- [X] T034 [US3] Implement RM8 in `src/mobility_model_zoo/site/roadmap.py`: `delivered_by` must name a version whose release record exists and has `published.published_at`
- [X] T035 [US3] Implement RM9 `check_roadmap_pages(reg, out)` in `src/mobility_model_zoo/site/check.py` per [contracts/checks.md](contracts/checks.md):
  - parse `_site/roadmap/index.html` and `_site/index.html` with the existing `Page` parser, or a small `HTMLParser` that collects `li.entry` ids per `section.horizon` and `a.mini` hrefs;
  - compare with `roadmap.page_context`;
  - check the heading counts;
  - register it in `run_checks` as `("RM9", …)`.
- [X] T036 [US3] Create `src/mobility_model_zoo/site/roadmap_cli.py` with a Typer app with the command `check`: run `roadmap.load` and `validate`, print findings and warnings to stderr, exit 1 on findings ([contracts/cli.md](contracts/cli.md)). Register it in `src/mobility_model_zoo/release/cli.py` with a `_mount_roadmap()` next to `_mount_site()` (`app.add_typer(roadmap_app, name="roadmap")`)
- [X] T037 [US3] Add `- run: uv run zoo roadmap check` after `uv run zoo validate --all` in the `checks` job of `.github/workflows/ci.yml`

**Checkpoint**: the roadmap cannot silently drift from the registry, the calendar or its own history.

---

## Phase 6: User Story 4 - Know whether we are faster or slower than planned (Priority: P2)

**Goal**: `zoo roadmap pace <quarter> [--write]`, the review files, and the review gate RM7 (constitution 2.3.0).

**Independent Test**: [quickstart.md](quickstart.md) section 4. On a constructed history, the report:
- lists one on-time delivery, one moved entry and one dropped entry with their reasons;
- shows the delivery rate as "1 of N";
- lists the unplanned releases.

With `--write`, the file `zoo/roadmap/reviews/2026-Q4.md` is created. Rolling the horizons without that file gives RM7; after the file is written and its "Re-planning" section is filled, the check passes.

### Tests for User Story 4

- [X] T038 [P] [US4] Pace tests in `tests/website/test_roadmap_pace.py` on a fixture copy:
  - give picket-forest a published record with `published_at: 2026-11-20T10:00:00Z` (on time for `2026-Q4`);
  - move `scout-large-reader-test` to `2027-Q1..Q2` with a reason;
  - drop `picket-signal` with a reason;
  - add a scout-large patch record published in Q4 (unplanned).
  
  With `ZOO_TODAY=2027-01-05`, assert every section and number of [contracts/pace-report.md](contracts/pace-report.md):
  - **Summary**: releases, delivered (early, on time, late), "1 of 2" (due = entries first planned for `2026-Q4`), moved, dropped, unplanned.
  - **Delivered**: the timing.
  - **Due and not delivered**: the moved entry with its reason.
  - **Empty tables**: printed as "None.".
  - **Trend**: has one row.
  - **Quarter not closed**: refused without `--draft`.
- [X] T039 [P] [US4] `--write` tests in `tests/website/test_roadmap_pace.py`: the file is created with the "## Re-planning" heading; a second `--write` keeps hand-written text under "## Re-planning" and replaces the generated sections
- [X] T040 [P] [US4] RM7 tests in `tests/website/test_roadmap_record.py`:
  - horizons `2027-Q1`, `2027-Q2..Q3`, `2027-Q4..2028-Q1` with `ZOO_TODAY=2027-01-05` and no review gives `RM7 … no review for 2026-Q4`;
  - a review whose "Re-planning" section is empty gives RM7;
  - a filled review passes.

### Implementation for User Story 4

- [X] T041 [US4] Create `src/mobility_model_zoo/site/pace.py` with `report(reg, record, quarter, today, draft=False) -> dict` per research R6 and [contracts/pace-report.md](contracts/pace-report.md):
  - **Delivered in the quarter**: with timing against `planned` and slip.
  - **Due and not delivered**: first planned horizon ending in or before the quarter, not delivered by the quarter's end, with current horizon and move reasons.
  - **Moved and dropped**: those whose dates fall in the quarter.
  - **Unplanned**: non-sandbox published releases in the quarter that deliver no entry; a later version of an entry's model is marked "patch".
  - **Counts**: releases, delivered, due, delivery rate "<a> of <b>".
  - **Trend**: one row per quarter from `since` up to this one, recomputed.
  - **Rules**: a quarter that has not ended raises an error unless `draft`; the "Due" rule (a two-quarter horizon is due in its second quarter) as stated in the contract.
- [X] T042 [US4] Add `render_markdown(report) -> str` and `write(reg, quarter, text)` to `src/mobility_model_zoo/site/pace.py`:
  - the Markdown follows the template of [contracts/pace-report.md](contracts/pace-report.md), with empty tables printed as "None.";
  - `write` creates `zoo/roadmap/reviews/<quarter>.md`, or replaces everything above "## Re-planning" in an existing file and keeps that section.
- [X] T043 [US4] Add the command `pace QUARTER [--write] [--draft]` to `src/mobility_model_zoo/site/roadmap_cli.py` ([contracts/cli.md](contracts/cli.md)): print the Markdown to stdout, or write and print the path
- [X] T044 [US4] Implement RM7 in `src/mobility_model_zoo/site/roadmap.py`: for every quarter from `since` up to the quarter before the first horizon's start, `zoo/roadmap/reviews/<quarter>.md` exists and its "## Re-planning" section contains at least one sentence (non-empty text other than the template placeholder line). Wire it into `validate()`

**Checkpoint**: plan against actual is measurable; the horizons cannot roll forward without a review.

---

## Phase 7: User Story 5 - Share the roadmap (Priority: P3)

**Goal**: a preview image for `/roadmap/` through the feature 012 pipeline.

**Independent Test**: `uv run zoo site build` (with images) writes a preview image for `roadmap/`; `zoo site check` reports no O1–O5 or B6 finding; `og:image` of `roadmap/index.html` points to it.

- [X] T045 [P] [US5] Tests in `tests/website/test_og_meta.py` and `tests/website/test_share_line.py`:
  - the cards list contains `roadmap/` with eyebrow "Roadmap", title "What comes next" and the default line when `zoo/site.yaml` has no `roadmap.share_line`;
  - a share line with a digit fails B6;
  - `og:image` of the roadmap page names its card file.
- [X] T046 [US5] Add the optional block `roadmap: {share_line}` to `src/mobility_model_zoo/site/schemas/site-config.schema.json` (`share_line`: string, `minLength` 1, `maxLength` 90, same description rules as the top-level `share_line`)
- [X] T047 [US5] Add the roadmap card to `og.cards()` in `src/mobility_model_zoo/site/og.py`: `_card("roadmap/", "page", "roadmap", "What comes next", line, eyebrow="Roadmap", owner="roadmap", from_tagline=False)`, where `line` is `site.get("roadmap", {}).get("share_line")` or "What the zoo plans to release next."; keep `site_cards()` in step so O4 sees it
- [X] T048 [P] [US5] Add `roadmap: {share_line: "What the zoo plans to release next, and what it has delivered."}` to `zoo/site.yaml` (no numbers, at most 90 characters)

**Checkpoint**: all stories done.

---

## Phase 8: Polish & cross-cutting concerns

- [ ] T049 [P] Document the roadmap in `docs/website.md`:
  - a row for `/roadmap/` in the pages table;
  - a section "Roadmap and pace review": the record, the fields, how to move or drop an entry, delivery from release records, the quarterly routine (`zoo roadmap pace <quarter> --write`, fill "Re-planning", roll the horizons, `zoo roadmap check`), and RM1–RM9 in the checks list.
- [ ] T050 [P] Add one line to `README.md` (website section or topics) linking the roadmap page `https://mhabedank.github.io/mobility-model-zoo/roadmap/`
- [ ] T051 Run the whole suite and the site checks locally:
  - `uv run ruff check`, `uv run ruff format --check`;
  - `uv run pytest -q $(python3 scripts/ci/select_tests.py --guards)`;
  - `uv run pytest tests/website -q`;
  - `uv run zoo validate --all`, `uv run zoo compliance check --ci`, `uv run zoo roadmap check`;
  - `uv run zoo site build`, `uv run zoo site check --a11y`, which needs Chromium (`PLAYWRIGHT_BROWSERS_PATH` is preset in cloud sessions);
  - `uv run pytest tests/website -q -m slow`.
  
  Fix every finding.
- [ ] T052 Walk through [quickstart.md](quickstart.md) sections 1–4 and record the results in `specs/015-website-roadmap/validation.md`:
  - the commands and their output;
  - the screen measurements for SC-002 and SC-003: at 1440 × 900 three columns and the page height in screens; on the start page the height of "Coming next" against the models section; at 390 px no horizontal scroll;
  - a screenshot description of the roadmap page in light and dark mode.
- [ ] T053 Re-check the Constitution Check of [plan.md](plan.md) against the implementation (no hand-written number on the site, first planned horizon guarded, delivery only from published records, review gate) and note the result in `specs/015-website-roadmap/validation.md`; leave SC-001 (reader test) and SC-008 (first review at the end of Q4 2026) as open items for the owner

---

## Dependencies & execution order

- **Setup (T001–T004)** → **Foundational (T005–T010)** → user stories.
- **US1 (T011–T019)** and **US2 (T020–T027)** depend only on Foundational. US2's template uses the roadmap context but not the roadmap page, so both can run in parallel; T015 (validate wiring) must land before T022 adds RM2 to it.
- **US3 (T028–T037)** depends on US1 (RM9 checks the rendered page) and US2 (RM9 checks the start-page cards).
- **US4 (T038–T044)** depends on Foundational and on T015 (`validate`) for RM7; it does not depend on US1–US3 pages.
- **US5 (T045–T048)** depends on US1 (the page exists).
- **Polish (T049–T053)** after all stories.

Inside a story: tests first (they fail), then the implementation that makes them pass.

## Parallel examples

- **After Foundational**: T011 + T012 (US1 tests), T020 + T021 (US2 tests), T038 + T039 + T040 (US4 tests) in different test files.
- **US1**: T018 (navigation) and T019 (CSS) in parallel with T016 (template).
- **US2**: T026 (CSS) and T027 (008 contract) in parallel with T023/T024.
- **US3**: T028–T031 (four test files) in parallel; then T032–T034 in `roadmap.py` one after another, T035 in `check.py` and T036 in `roadmap_cli.py` in parallel.

## Implementation strategy

1. **MVP = US1 + US2**: the record, the roadmap page and the start-page cards (T001–T027). This is what the owner asked to see; deployable on its own because RM1–RM4 and RM2 already keep the record honest.
2. **US3**: drift and staleness protection plus `zoo roadmap check` in CI.
3. **US4**: the pace report and review gate, in place before the first review at the end of Q4 2026 (SC-008).
4. **US5 and polish**.

## Initial record (for T001)

Order inside each horizon is the priority order approved on 2026-10-12. Every entry has `planned` equal to `horizon`.

| id | name | working_name | model | topic | kind | stage | horizon | text | precondition |
|---|---|---|---|---|---|---|---|---|---|
| picket-forest-board | picket-forest | false | picket-forest | security | update | planned | 2026-Q4 | Speed and memory measured on a real microcontroller board instead of an emulator. | – |
| scout-large-reader-test | scout-large | false | scout-large | productdev | update | planned | 2026-Q4 | Reader test and a clean-machine run, the last open criteria for production readiness. | – |
| pace-cnn | pace-cnn | false | pace-cnn | condition-monitoring | first-release | in-progress | 2026-Q4 | Activity recognition from motion sensors on a microcontroller. | – |
| hum-fan | hum-fan | false | hum-fan | condition-monitoring | first-release | in-progress | 2026-Q4 | Detects unusual fan sounds on a microcontroller, trained only on normal recordings. | – |
| hum-bearing | hum-bearing | true | – | condition-monitoring | new-model | planned | 2026-Q4 | Finds bearing faults from vibration, for rail and machine maintenance. | – |
| picket-mlp | picket-mlp | false | picket-mlp | security | first-release | planned | 2026-Q4 | A small neural network that detects attacks on the vehicle CAN bus. | – |
| mode-cnn | mode-cnn | true | – | condition-monitoring | new-model | planned | 2027-Q1..Q2 | Recognises the mode of transport from smartphone motion sensors, tested on people it never saw. | Data licence to be confirmed |
| cell-soh | cell-soh | true | – | condition-monitoring | new-model | planned | 2027-Q1..Q2 | Estimates the health of battery cells on a microcontroller. | – |
| gnss-guard | gnss-guard | true | – | security | new-model | planned | 2027-Q1..Q2 | Detects jamming and spoofing of satellite navigation, trained on real attack recordings. | Data licence to be confirmed |
| scout-large-languages | scout-large | false | scout-large | productdev | update | planned | 2027-Q1..Q2 | Reads mobility texts in more languages, starting with Spanish, Polish and Japanese. | Resource index first version |
| jtbd-cluster | jtbd-cluster | true | – | productdev | new-model | planned | 2027-Q1..Q2 | Groups duplicate needs found by scout-large and counts how often they occur. | – |
| picket-forest-control | picket-forest | false | picket-forest | security | update | planned | 2027-Q1..Q2 | New features that pass the shuffled-label control of the evaluation. | – |
| rough-road | rough-road | true | – | condition-monitoring | new-model | planned | 2027-Q3..Q4 | Estimates road roughness from signals an electric car already records. | Privacy review of location data |
| v2x-guard | v2x-guard | true | – | security | new-model | planned | 2027-Q3..Q4 | Flags misbehaving vehicles in vehicle-to-vehicle messages. | Data access to be confirmed |
| picket-signal | picket-signal | true | – | security | new-model | planned | 2027-Q3..Q4 | Detects forged CAN messages by their content, not only their timing. | – |

Notes for T001:
- **scout-large-reader-test**: the text avoids "released"; RM3 rejects release-status words.
- **Model fields**: rows with "–" in `model` have no `model` field; rows with "–" in `precondition` have no `precondition`.
- **Usage chip**: `hum-fan` shows "share-alike" through its `usage_class`, derived and not written into the entry.
