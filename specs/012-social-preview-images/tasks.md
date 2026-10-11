---

description: "Task list for feature 012: social preview images"
---

# Tasks: Social preview images for every zoo page

**Input**: Design documents from `/specs/012-social-preview-images/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (cli.md, checks.md, share-card.md, site-yaml-share-line.md), quickstart.md

**Tests**: Included. The spec makes the checks part of the feature (User Story 4, FR-011), and the owner relies on automated QA instead of manual review.

**Organization**: Tasks are grouped by user story. Browser-based tests are marked `slow`, as in `tests/website/test_browser.py`. They `importorskip("playwright")` and skip if Chromium is missing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1–US4 from spec.md

---

## Phase 1: Setup

**Purpose**: Module skeleton, schema fields and test defaults.

- [X] T001 Create `src/mobility_model_zoo/site/og.py` with this skeleton:
  - The module docstring points to `specs/012-social-preview-images/`.
  - Constants: `WIDTH = 1200`, `HEIGHT = 630`, `MAX_BYTES = 300_000`, `MAX_LINE = 90`, `MAX_LINES = 3`, `TITLE_SIZES = (76, 60, 48)`, `MARGIN = 48`, `SAFE_X = (285, 915)`.
  - `LATIN_RANGES`: the Unicode ranges listed in research.md R7, as a tuple of `(start, end)` ints.
  - `OG_DIR = "assets/og"`.
- [X] T002 [P] Add the optional `share_line` property to `src/mobility_model_zoo/site/schemas/site.schema.json` and `src/mobility_model_zoo/site/schemas/site-config.schema.json`, exactly as in contracts/site-yaml-share-line.md (`"type": "string"`, `"minLength": 1`, `"maxLength": 90`, with that description).
- [X] T003 [P] In `tests/website/site_fixture.py`, give `SiteEnv.build` the default `images=False`, so the existing fast tests and the `built` fixture in `tests/website/conftest.py` keep running without Chromium. Add a helper `SiteEnv.clone_model(src, dst)` that copies `zoo/models/<src>/` and `.cache/site/<src>/` to `<dst>` in the temporary registry and sets `name` and `repos` in the copied `model.yaml` to the new name. US2 uses it.

---

## Phase 2: Foundational (blocking all stories)

**Purpose**: Share line rules, card dicts, card HTML and the input hash. Every story needs them.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 [P] Write `tests/website/test_share_line.py`. It covers `og.share_line(pitch)` and `og.share_line_errors(owner, text, from_tagline)` against data-model.md:
  - A share line of exactly 90 characters passes.
  - 91 characters fail with `B6 <name>: share line has 91 characters, at most 90`.
  - `{metric:performance.peak_ram_gb}` fails with `… contains a metric placeholder`.
  - "Runs in 8 s" fails with `… contains the number "8"`.
  - "Runs on an M3 Pro" passes, because the digits are part of a name (the F2 pattern).
  - "→" (U+2192) fails with `character U+2192 is not in the site fonts`. "€", "–" and "’" pass.
  - Whitespace is collapsed before the length is counted.
  - Without `share_line`, a tagline that meets the rules is used. A tagline of 96 characters fails, and the message ends with `; add share_line to site.yaml`.
- [X] T005 Implement the share line rules in `src/mobility_model_zoo/site/og.py`:
  - `share_line(text_source: dict) -> tuple[str, bool]` returns the effective line (`share_line` or `tagline`, whitespace collapsed) and whether it came from the tagline.
  - `share_line_errors(owner: str, text: str, from_tagline: bool) -> list[str]` applies the four rules of data-model.md:
    - length ≤ 90;
    - no `facts.PLACEHOLDER` match;
    - no match of the F2 `NUMBER` pattern. Move `NUMBER` from `site/check.py` to `site/facts.py` and import it from there in both `check.py` and `og.py`, so `og` never imports `check` (no import cycle);
    - every character in `LATIN_RANGES`.

  The tests of T004 must pass.
- [X] T006 [P] Write `tests/website/test_og_fonts.py`. It runs `pytest.importorskip("fontTools")` and needs `brotli` for woff2; skip if it is missing. It reads the cmap of `static/fonts/Figtree-variable-latin.woff2` and asserts that every printable code point in `og.LATIN_RANGES` that is not a control or format character is covered (research R7).
- [X] T007 Implement card dicts in `src/mobility_model_zoo/site/og.py`:
  - `cards(reg, site, models, formats) -> list[dict]` builds one card per shareable page, with the fields of data-model.md "Share card": `page`, `kind`, `title`, `line`, `labels`, `motif`, `alt`, `slug`. Pages are `""` (zoo), `models/<name>/` for every published model, and `formats/<id>/` for every public format id.
  - `labels` follows the data-model order: release status of the latest record if it is not `released`; `deprecated` if the site status is deprecated; `non-commercial` if `usage["class"]` starts with `non-commercial`. It reads the same `usage` dict that `context.site_models` passes to the page.
  - `alt`: `"<title>, Mobility Model Zoo: <line>"`, plus ` (<labels joined by ', '>)` if there are labels. Format cards use `"Output format <id>, Mobility Model Zoo: <line>"`.
  - `card_errors(cards)` returns B6 for every card via `share_line_errors`.
- [X] T008 [P] Create the card template `src/mobility_model_zoo/site/templates/og/card.html.j2` and its styles `src/mobility_model_zoo/site/static/css/og.css`, following contracts/share-card.md:
  - 1200 × 630 body, background `--bg` #0A0F2E, accent `--accent` #6FFFC8, Figtree only, 48 px margins.
  - Blocks centred: brand row (mark 88 px for zoo, 56 px otherwise, plus wordmark), eyebrow (topic title or "Output format"), title (`data-og="title"`, 76 px Figtree 700, in a box of `max-width: 630px` centred on the safe square, `white-space: nowrap`), line (`data-og="line"`, 34 px Figtree 500, max-width 960 px), label chips (`data-og="labels"`).
  - The motif, `aria-hidden="true"`, at both side edges outside x ∈ [285, 915].
  - No numbers and no URLs in the template text.

  The template links `tokens.css`, `og.css` and the fonts with relative paths into `_site/assets/`, and loads nothing else.
- [X] T009 Implement in `src/mobility_model_zoo/site/og.py`:
  - `card_html(env, card) -> str`: renders `og/card.html.j2` with `mark()` and `motif()` from `build.py`.
  - `asset_paths(html) -> list[str]`: the `href`/`src`/`url()` targets of the card.
  - `renderer_id() -> str`: `"playwright <version>"`, with the version from `importlib.metadata.version("playwright")`, or, if Playwright is not installed, from the `playwright` entry in `uv.lock`. No Chromium revision: the Playwright version pins it, and a browser-less build must yield the same addresses (research R5).
  - `input_hash(html, assets_root, renderer) -> str`: SHA-256 over the HTML, each asset's bytes in sorted path order, and the renderer id (research R5).
  - `card_file(card, digest) -> str`: `assets/og/<slug>-<digest[:12]>.png`.
- [X] T010 [P] Write `tests/website/test_og_meta.py` (fast, `images=False`):
  - `og.cards` on the fixture registry returns exactly the zoo card, `models/scout-large/` and `formats/jtbd-span-v1/`. The unpublished `picket-forest` and the sandbox model are absent.
  - scout-large labels equal the release status and usage class of the fixture record.
  - The alt text has the documented form.
  - `input_hash` is equal for two calls with the same input and different when the line, an asset byte or the renderer id changes.
  - `renderer_id()` returns the same string whether or not Playwright is importable (monkeypatch `importlib.metadata.version` to raise `PackageNotFoundError` and compare with the `uv.lock` value).

**Checkpoint**: the rules, card data and hash are tested without a browser.

---

## Phase 3: User Story 1 - A shared model link shows the model (Priority: P1) 🎯 MVP

**Goal**: The scout-large page declares its own 1200 × 630 image with the name, mark, share line and labels.

**Independent Test**: `uv run zoo site build --offline`, then open `_site/assets/og/scout-large-*.png`. `grep og:image _site/models/scout-large/index.html` shows that file.

### Tests for User Story 1

- [X] T011 [P] [US1] Extend `tests/website/test_og_meta.py`. After `build(images=False)`, `_site/models/scout-large/index.html` contains the eight tags of contracts/share-card.md, with these values:
  - `og:image` is `<canonical_url>assets/og/scout-large-<12 hex>.png`;
  - width 1200, height 630, `image/png`;
  - `twitter:card` is `summary_large_image`;
  - both alt tags equal the card alt.

  `_site/_build/og.json` lists the card with the same `file`.
- [X] T012 [P] [US1] Create `tests/website/test_og_render.py` (`pytestmark = pytest.mark.slow`, `importorskip("playwright")`, skip on missing Chromium as in `test_browser.py`). `build(images=True)` writes a PNG for scout-large whose IHDR says 1200 × 630, ≤ 300 000 bytes. The manifest `layout` has `title_px` in `(76, 60, 48)`, `line_lines` ≤ 3 and empty `overflow`, and the `mark` and `title` boxes lie inside x ∈ [285, 915].

### Implementation for User Story 1

- [X] T013 [US1] Implement `render(cards, out, say) -> None` in `src/mobility_model_zoo/site/og.py`:
  - one `sync_playwright` Chromium launch, viewport 1200 × 630, device scale factor 1;
  - `page.route("**/*", …)` aborts every request whose URL does not start with `file:`;
  - for each card: open `_site/_build/og/<slug>.html`, await `document.fonts.ready`, then step the title font size through `TITLE_SIZES` until the title's `scrollWidth <= clientWidth` inside its 630 px box;
  - count the line's lines as `round(height / line-height)`;
  - collect the bounding boxes of the mark, title, line and labels, and every element whose `scrollWidth > clientWidth` or `scrollHeight > clientHeight`, into `layout`;
  - raise `GateFailed` with `B7 <page>: title does not fit at 48 px` or `B7 <page>: share line needs <n> lines, at most 3`;
  - otherwise `page.screenshot(path=…, type="png")`.

  If Playwright or Chromium is missing, raise `UsageError` with the message of contracts/cli.md.
- [X] T014 [US1] Wire the cards into `src/mobility_model_zoo/site/build.py`:
  - `build(…, images: bool = True)`.
  - After the context is loaded: compute `og.cards`, add `og.card_errors` to `failures`, write each card HTML to `_site/_build/og/<slug>.html`, compute `file` via `input_hash`, and write `_site/_build/og.json` (`{"renderer": …, "cards": […]}`, data-model.md).
  - Pass `card` into `render()` of each shareable page. The 404 page gets the zoo card.
  - If `images`, call `og.render`, then rewrite the manifest with `layout`.
  - The summary line becomes `site: <n> pages, <i> images in <s> s, <m> models (<k> in progress)`, with the render time of the image step (SC-005).
- [X] T015 [US1] Replace the single `og:image` line in `src/mobility_model_zoo/site/templates/base.html.j2` with the eight tags of contracts/share-card.md, filled from `card` and `site.canonical_url`.
- [X] T016 [US1] Add `share_line: Finds jobs, pains and gains in mobility texts, each with a verbatim quote.` to `zoo/models/scout-large/site.yaml` and to the fixture copy `tests/website/fixtures/registry/zoo/models/scout-large/site.yaml`. Check: ≤ 90 characters, no numbers.
- [X] T017 [US1] Show the release-status labels at the top of the model page (FR-003): in `src/mobility_model_zoo/site/templates/partials/hero.html.j2`, next to the existing status chip, add one chip per card label (`experimental`, `deprecated`, `non-commercial`) using the same `card.labels` list, so page and image use one source. Extend `tests/website/test_model_page.py`: the scout-large hero contains a chip for every label of its card, and none when the record says `released`.
- [X] T018 [US1] Add `--images/--no-images` (default on) to `zoo site build` in `src/mobility_model_zoo/site/cli.py` and pass it to `build`. A `UsageError` from `og.render` exits with code 2, as the other usage errors do.

**Checkpoint**: scout-large has its own preview image. MVP done.

---

## Phase 4: User Story 2 - A new model gets its image without anyone designing it (Priority: P1)

**Goal**: Publishing a model, or changing its share line or status, updates its image on the next build. The release gate rejects text that would break the image build.

**Independent Test**: `pytest tests/website -k new_model -m slow` builds a registry with a cloned second published model and finds its image. `pytest tests/release/test_gate_site_text.py` shows rule 17 reporting B6.

### Tests for User Story 2

- [X] T019 [P] [US2] In `tests/website/test_og_meta.py`, add `test_new_model_gets_card_and_meta` (fast). `env.clone_model("scout-large", "scout-mini")`, build with `images=False`, then:
  - `models/scout-mini/index.html` carries `og:image` with `assets/og/scout-mini-<hash>.png`;
  - the manifest lists it;
  - no file under `src/mobility_model_zoo/site/` changed.
- [X] T020 [P] [US2] In `tests/website/test_og_render.py`, add `test_new_model_image_rendered` (slow): the same clone, built with `images=True`, gets its PNG.
- [X] T021 [P] [US2] In `tests/website/test_og_meta.py`, add `test_address_changes_with_content`:
  - Build twice without changes: every manifest `file` is equal (SC-006).
  - Change the scout-large `share_line`: only the scout-large `file` changes.
  - Set the latest record `deprecated`: the labels gain `deprecated` and the address changes.
- [X] T022 [P] [US2] Extend `tests/release/test_gate_site_text.py`. Rule 17 reports `B6 scout-large: share line …` when `share_line` has 95 characters or contains `{metric:…}`, and when `share_line` is removed while the tagline has 96 characters. Rule 17 passes with the T016 share line.
- [X] T023 [P] [US2] In `tests/website/test_og_render.py`, add `test_title_too_long_fails` (slow): a clone named with 40 characters (wider than the 630 px title box at 48 px) causes `GateFailed` with `B7 models/<name>/: title does not fit at 48 px`; a clone named with 13 characters (`picket-forest` length) passes at 76 px.

### Implementation for User Story 2

- [X] T024 [US2] In `src/mobility_model_zoo/site/context.py`, `pitch_errors(reg, name, version)` appends `og.share_line_errors(name, *og.share_line(pitch))`. This makes gate rule 17 enforce FR-006 with no change in `release/gate.py`.
- [X] T025 [US2] In `src/mobility_model_zoo/site/build.py`, validate the zoo `share_line` (or the zoo tagline) and each format `title` from `zoo/formats/<id>.yaml` with `share_line_errors`. Failures go into the build's `failures` (B6).

**Checkpoint**: new models and changes flow into images automatically, and the gate guards the text.

---

## Phase 5: User Story 3 - Start page and format pages share well too (Priority: P2)

**Goal**: The start and format pages have generated images. The hand-made `og.png` and its script are gone.

**Independent Test**: After a build, `index.html` and `formats/jtbd-span-v1/index.html` declare their own images. Changing `zoo/site.yaml` `share_line` changes the start image address.

### Tests for User Story 3

- [X] T026 [P] [US3] In `tests/website/test_og_meta.py`, add `test_start_format_and_404_cards`:
  - `index.html` points at `assets/og/zoo-<hash>.png`;
  - `formats/jtbd-span-v1/index.html` at `assets/og/format-jtbd-span-v1-<hash>.png`;
  - `404.html` at the zoo image, and 404 is not in the manifest;
  - no page references `assets/img/og.png`;
  - `run_checks(out, only=["S1"])` reports nothing after a build in which `assets/og/` holds three 150 KB files (S1 ignores preview images).

### Implementation for User Story 3

- [X] T027 [US3] Delete `src/mobility_model_zoo/site/static/img/og.png` and `scripts/site_og_image.py`.
  - In `src/mobility_model_zoo/site/check.py` `check_size` (S1), remove `"og.png"` from the name exemption and instead skip every file under `assets/og/`: preview images are loaded by scrapers, not visitors, and O1 limits each to 300 KB. Without this, three images of ~100 KB already exceed the 300 KB site total.
  - In `scripts/ci/select_tests.py`, replace `"scripts/site_og_image.py"` in the `site` entry with nothing; `site/*` already covers `og.py` and the template.
- [X] T028 [US3] Make sure the zoo card and the format cards render correctly with `og/card.html.j2`, adjusting it as needed:
  - zoo: mark 88 px, title "Mobility Model Zoo", line = zoo share line or tagline, no eyebrow and no labels;
  - format: eyebrow "Output format", title = id, line = format `title`.

**Checkpoint**: every shareable page has its own image.

---

## Phase 6: User Story 4 - Images are checked like the rest of the site (Priority: P2)

**Goal**: `zoo site check` runs O1–O5 and blocks the deploy on any finding.

**Independent Test**: `pytest tests/website -k og_checks` injects faults (wrong size, missing tag, stale hash, orphan file, overflow, label mismatch) and each one is reported with its id.

### Tests for User Story 4

- [X] T029 [P] [US4] Write `tests/website/test_og_checks.py` (fast parts with `images=False` plus synthetic PNGs written with `struct`/`zlib`):
  - O1: a missing `twitter:card` tag; a PNG of 1200 × 600; a 300 001-byte file; a missing file (the `--no-images` build); a non-absolute `og:image`.
  - O2: a manifest `layout` with an overflow entry, and a title box at x = 200.
  - O4: the manifest line differs from the registry share line; alt text differs from the manifest alt; a missing `non-commercial` label for an NC model.
  - O5: the file name hash does not match the recomputed hash; an extra `assets/og/orphan.png`.

  Each case asserts the finding id and page.
- [X] T030 [P] [US4] In `tests/website/test_og_render.py`, add `test_full_check_passes` (slow): build with `images=True`, then `run_checks(out, a11y=True)` reports nothing, O3 included. Also add a contrast fault: card HTML with a line colour of #333 on `--bg` yields O3. Add `test_render_time_five_models` (SC-005): clone scout-large four times (five published models), build with `images=True` and assert the image step takes under 60 s; `build` reports the image time in its summary line (`… <i> images in <s> s …`) so CI logs show it too.

### Implementation for User Story 4

- [X] T031 [US4] Implement O1, O2, O4 and O5 in `src/mobility_model_zoo/site/check.py`, reading `_site/_build/og.json` and the pages. They follow contracts/checks.md:
  - O1 is the metadata, file, PNG signature and IHDR via `struct`, 1200 × 630 and ≤ `og.MAX_BYTES`.
  - O2 checks the layout against `MARGIN` and `SAFE_X`.
  - O4 recomputes the cards with `og.cards` and compares `title`, `line`, `labels` and `alt` with the manifest and the meta tags.
  - O5 recomputes `og.input_hash` from `_build/og/<slug>.html` and flags orphan files in `assets/og/`.

  Register the ids so that `--only` accepts them.
- [X] T032 [US4] Implement O3 in `src/mobility_model_zoo/site/a11y.py`: in the existing browser session, open each card HTML from the manifest and run the vendored axe with `runOnly: ["color-contrast"]`. Report `O3 <page> <violation summary>`.

- [X] T033 [US4] Extend P1 and P3 in `src/mobility_model_zoo/site/check.py` to the card pages: add `card_pages(out)` returning `sorted((out / "_build" / "og").glob("*.html"))`, and run the P1 resource scan and the P3 branding/advertising scan over `pages(out) + card_pages(out)`, naming findings by the card path (`P1 _build/og/scout-large.html …`). Test in `tests/website/test_og_checks.py`: a card with `<link href="https://fonts.googleapis.com/…">` yields P1, a card with "Sponsor" yields P3 (contracts/checks.md, FR-007, FR-015).

**Checkpoint**: images are verified before every deploy.

---

## Phase 7: Polish & Cross-Cutting

- [X] T034 [P] Update `docs/website.md`:
  - Replace the `scripts/site_og_image.py` sentence with a section "Preview images". It covers generation at build time, `share_line`, `--no-images`, checks B6/B7 and O1–O5, and how to verify a preview in LinkedIn Post Inspector.
- [X] T035 [P] In `docs/adding-a-model.md`, mention the optional `share_line` (≤ 90 characters, no numbers) in the `site.yaml` step.
- [X] T036 [P] Copy the new check ids into `specs/008-zoo-website/contracts/checks.md`, with a one-line pointer to `specs/012-social-preview-images/contracts/checks.md`, so the 008 catalogue stays complete.
- [X] T037 Run the full local validation:
  - `uv run ruff check . && uv run ruff format --check .`
  - `uv run pytest -q`
  - `uv run pytest tests/website -m slow`
  - `uv run zoo site build --offline && uv run zoo site check --a11y`
  - `uv run zoo validate`, `uv run zoo compliance check --ci`, `reuse lint`

  Fix every finding.
- [X] T038 Run the steps of `specs/012-social-preview-images/quickstart.md` 1–6. Look at the three PNGs and confirm by eye that the name, mark, share line and labels are readable and centred. Write the result to `specs/012-social-preview-images/validation.md`.
- [ ] T039 After the deploy: check the live scout-large URL with at least three platform preview tools (LinkedIn Post Inspector, a Mastodon post preview, Slack), and run the SC-004 question with three people. Record both in `specs/012-social-preview-images/validation.md`. This is manual and runs after the merge.

---

## Dependencies & Execution Order

- **Phase 1 → Phase 2 → stories.** T005 needs T001. T007 needs T005. T009 needs T008. T010 needs T007 and T009.
- **US1 (Phase 3)** needs Phase 2. T013 → T014 → T015. T016 and T018 are independent of each other.
- **US2 (Phase 4)** needs US1 (T014), because the build must carry cards. T024 needs only T005 and can start right after Phase 2.
- **US3 (Phase 5)** needs US1 (T014, T015).
- **US4 (Phase 6)** needs US1 (manifest and meta). O3 needs T013.
- **Polish** comes after all stories. T039 comes after the merge and deploy.

## Parallel Examples

- Phase 1: T002 ∥ T003, after T001.
- Phase 2: T004 ∥ T006 ∥ T008 (tests, font test and template are separate files).
- US1: T011 ∥ T012 (tests), then T016 ∥ T018 next to T013–T015; T017 after T014 (needs `card` in the page context).
- US2: T019 ∥ T020 ∥ T021 ∥ T022 ∥ T023 (tests); T024 ∥ T025.
- US4: T029 ∥ T030; then T031 ∥ T032 (`check.py` vs `a11y.py`); T033 after T031 (same file).
- Polish: T034 ∥ T035 ∥ T036.

## Implementation Strategy

1. **MVP = Phases 1–3.** scout-large gets its own preview image and metadata. Shareable at once.
2. **Add US2.** The gate guards the share line, and a new model is proven to get its image automatically (the cloned-model test).
3. **Add US3.** The start and format images replace the hand-made `og.png`.
4. **Add US4.** O1–O5 block bad images before deploy.
5. **Polish.** Docs, full validation, then merge. Platform checks and the user test (T039) follow on the live site.
