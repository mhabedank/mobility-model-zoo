# Tasks: Model pages in progressive depth

**Input**: Design documents from `/specs/013-model-page-layout/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Included. The checks (D1–D6, gate rules 17 and 18, card order) are deliverables of this feature (FR-021, FR-022), and every gate rule and site check in this repository is covered by tests.

**Organization**: by user story of the spec. Layer numbers refer to [contracts/page-layers.md](contracts/page-layers.md); check IDs to [contracts/checks.md](contracts/checks.md).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1–US6 from spec.md

---

## Phase 1: Setup

**Purpose**: start from the state that contains feature 012 and record the baseline.

- [X] T001 Rebase branch `013-model-page-layout` onto `main` after feature 012 (`012-social-preview-images`) is merged; if 012 is not merged yet, stop and report (research R11). Resolve conflicts in `src/mobility_model_zoo/site/check.py`, `src/mobility_model_zoo/site/templates/partials/hero.html.j2`, `src/mobility_model_zoo/site/schemas/site.schema.json`, `zoo/models/*/site.yaml` by keeping 012's `share_line` and checks B6, B7, O1–O5
- [X] T002 [P] Record the baseline measurement (section start in screens and word count per section at 1440 × 900, for scout-large and picket-forest, as in the spec's "Context: the pages today" table) by building the current site with `uv run zoo site build` and measuring with Playwright; write it to `specs/013-model-page-layout/validation.md` under "Baseline"
- [X] T003 [P] Write a link inventory of each current model page (every `href` target on `_site/models/scout-large/index.html` and `_site/models/picket-forest/index.html`) to `specs/013-model-page-layout/validation.md` under "Link inventory before" (input for SC-006)

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: data fields, budget table, release status and the six-layer page skeleton that every story fills.

**⚠️ CRITICAL**: no user-story work before this phase is complete.

- [X] T004 Create `src/mobility_model_zoo/site/budgets.py` with one constants table and the counting rule (research R5): `OVERVIEW_WORDS = 150`, `NOT_FOR_WORDS = 40`, `NOT_FOR_ITEMS = (2, 3)`, `NOT_FOR_ITEM_WORDS = 15`, `DIFFERENTIATORS = (3, 4)`, `DIFFERENTIATOR_TITLE_WORDS = 5`, `DIFFERENTIATOR_TEXT_WORDS = 20`, `AUDIENCE_WORDS = 25`, `HEADLINE_FIGURES_MAX = 4`, `QUALITY_LEAD_SENTENCES = 1`, `LIMITS_SHORT_ITEMS = 5`, `LIMITS_SHORT_ITEM_WORDS = 25`, `LIMITS_SHORT_WORDS = 120`, `WORDS_BEFORE_QUALITY = 200`, `UNMET_CRITERION_WORDS = 12`, `UNMET_NOTE_WORDS = 15`; plus `words(text) -> int` (whitespace tokens) and `visible_words(element) -> int` that skips elements with `data-budget="skip"` and the content of closed `<details>` except `<summary>`
- [X] T005 [P] Unit tests for `budgets.words` and `budgets.visible_words` (placeholders count as one word; `data-budget="skip"` and closed `<details>` excluded; `<summary>` counted) in `tests/website/test_budgets.py`
- [X] T006 Add optional fields to the `card` object of `src/mobility_model_zoo/release/schemas/model.schema.json` (data-model.md): `not_for` (array of strings, `minItems` 2, `maxItems` 3, each `minLength` 1); `limits_short` (array of strings, `minItems` 1, `maxItems` 5); `unmet_criteria` (array of objects with `criterion` (string, required), `target` (object: `op` enum `<=`, `>=`, `<`, `>`, `=`; `value` number; `unit` string; `source` string path; all required), `measured` (string, pattern `^\{metric:(quality|performance)\.[a-z0-9_]+\}$`), `note` (string), `additionalProperties: false`, `anyOf` requiring `measured` or `note`). Keep all three fields out of `required` so `model.yaml` at old tags stays valid
- [X] T007 [P] Tighten `src/mobility_model_zoo/site/schemas/site.schema.json`: `differentiators.maxItems` 5 → 4; `metric_cards.maxItems` 6 → 4; update the descriptions to name the word limits enforced by gate rule 17 and check D2
- [X] T008 [P] Schema tests: a `model.yaml` with valid `not_for`, `limits_short`, `unmet_criteria` validates; an `unmet_criteria` item with neither `measured` nor `note` fails; a `model.yaml` without the new fields still validates; `site.yaml` with 5 differentiators or 5 metric cards fails; in `tests/release/test_schemas.py`
- [X] T009 Add `release_status` (the `status` of the latest published record: `experimental` | `released`; when the record says `deprecated`, the `status` of the same record read at its tag `<name>/v<version>` with `file_at_tag`) and `short` (the `card.not_for`, `card.limits_short`, `card.unmet_criteria` of `model.yaml`, empty lists when absent) to each model in `site_models()` in `src/mobility_model_zoo/site/context.py`; keep `status` (lifecycle) unchanged
- [X] T010 Add a status sentence to `BANNERS` in `src/mobility_model_zoo/release/card.py` (`"experimental"`: "Experimental: not ready for production use."; `"released"`: "Released: meets the success criteria and budgets of its task.") and a helper `status_sentence(status) -> str` used by both card and site (research R4)
- [X] T011 Add a resolver for unmet criteria in `src/mobility_model_zoo/site/facts.py`: `unmet_rows(reg, name, version, items, f, notes, page)` returns per item `criterion`, `measured` (value + unit via `facts.metric`, registered as a fact with the results file as source), `target` (`op`, `value`, `unit`, registered as a fact with source `zoo/models/<name>/model.yaml`), `note`, and the note number; placeholders in `not_for` and `limits_short` resolve with the existing placeholder function and are registered as facts
- [X] T012 Restructure `src/mobility_model_zoo/site/templates/model.html.j2` into the six layer sections in contract order, each `<section id="…" data-layer="…">`: `top`/`overview` (hero), `quality`, `limits`, `quickstart`, `reference` (wrapping `interface` and `examples` as `<div id="interface">` and `<div id="examples">`), `details` (wrapping `metrics`, `notes`, `provenance`, `versions`, `cite`); move the existing partials into this order without changing their content yet; add `<span id="why"></span>` inside layer 1 as an alias anchor; keep the deprecation banner above `<main>`
- [X] T013 Pass `release_status`, `short`, `status_sentence` and the unmet rows from T009–T011 into the page context in `model_page()` in `src/mobility_model_zoo/site/build.py`
- [X] T014 Update the frozen test registry: add `not_for`, `limits_short` and `unmet_criteria` (with one `measured` metric that exists in its results and one `note` item) to `tests/website/fixtures/registry/zoo/models/scout-large/model.yaml` and `tests/website/fixtures/registry/zoo/models/picket-forest/model.yaml`; shorten their fixture `site.yaml` to the budgets of T004; document the change in `tests/website/fixtures/registry/README.md`

**Checkpoint**: the site builds with the six layer sections in order; content is still today's.

---

## Phase 3: User Story 1 – Decide in the first screen (Priority: P1) 🎯 MVP

**Goal**: layer 1 answers what it is, what it does, why use it and on what terms, within budget, with the release status from the record.

**Independent Test**: open both model pages at 1440 × 900 and 390 px; without scrolling (desktop) find task, tagline, reasons, release status (with sentence for experimental), usage class, licence and the "not for" points; D4 and the layer-1 part of D2/D3 pass.

### Tests for User Story 1

- [X] T015 [P] [US1] Tests for check D4 in `tests/website/test_layers_overview.py`: status chip text equals the latest record status; for `experimental` the status sentence and a link to `#limits` exist inside `[data-layer=overview]`; for a non-commercial usage class the text "Non-commercial" is inside layer 1; a page with the lifecycle chip only ("published") fails; a `site.yaml` tagline containing "experimental" fails
- [X] T016 [P] [US1] Tests for the layer-1 part of D2 and D3 in `tests/website/test_layers_overview.py`: running text ≤ 150 words, `not_for` list ≤ 40 words and 2–3 items, 3–4 differentiators with text ≤ 20 words; no `pre`, `code` block, `table` or `.metric` element in layer 1

### Implementation for User Story 1

- [X] T017 [US1] Rewrite `src/mobility_model_zoo/site/templates/partials/hero.html.j2` as layer 1: eyebrow (topic, task); `h1`; tagline; audience; chips with `data-budget="skip"` for release status (from `release_status`, styled per status; for a record whose status is `deprecated`, the status at its release tag), usage class (reading "Non-commercial" for NC classes), licence, languages or target, output format; for `experimental` the status sentence linking `#limits`; jump links (`#quickstart`, `#limits`, `#details`, model card on Hugging Face) with `data-budget="skip"`
- [X] T018 [US1] Merge the differentiators from `src/mobility_model_zoo/site/templates/partials/why.html.j2` into layer 1 as a compact list (title + one-line text, no `h2` built from `summary`); add the `not_for` list under the heading "Not for" with a link "All limits" to `#limits`; delete `why.html.j2` and its include
- [X] T019 [US1] Add a layer navigation (ordered list of the six layers with anchors, `aria-label="On this page"`, `data-budget="skip"`) at the end of layer 1 in `src/mobility_model_zoo/site/templates/partials/hero.html.j2`
- [X] T020 [US1] Implement check D4 and the layer-1 parts of D2 and D3 as `check_overview(out)` in `src/mobility_model_zoo/site/check.py` using `budgets.py`; register it in `run_checks`; each finding names page, layer, measured value and limit
- [X] T021 [P] [US1] Styles for the status chip variants, the "Not for" list and the layer navigation in `src/mobility_model_zoo/site/static/css/site.css`, using only tokens from `tokens.css`; contrast checked in light and dark mode
- [X] T022 [US1] Write `card.not_for` for the published models in `zoo/models/scout-large/model.yaml` and `zoo/models/picket-forest/model.yaml` (2–3 items, each ≤ 15 words, together ≤ 40 words, no free-standing numbers, derived from their `out_of_scope` and `limitations` text)
- [X] T023 [US1] Shorten `zoo/models/scout-large/site.yaml` and `zoo/models/picket-forest/site.yaml` to the budgets: 3–4 differentiators, title ≤ 5 words, text ≤ 20 words, audience ≤ 25 words; remove the hand-written "Experimental" from the picket-forest tagline and differentiator (now generated, research R4); keep every placeholder resolvable (B2)

**Checkpoint**: layer 1 is complete and checked; US1 testable on its own.

---

## Phase 4: User Story 2 – Quality and speed as pictures first (Priority: P1)

**Goal**: layer 2 directly after the overview: ≤ 4 headline figures (with a comparison bar where a comparison exists) and the charts, no full tables, a link to `#metrics`.

**Independent Test**: on scout-large the first chart starts within 2 screens at 1440 × 900; on picket-forest the headline figures are visible as figures; layer 2 contains no metric table; D3 (layer 2) passes.

### Tests for User Story 2

- [X] T024 [P] [US2] Tests for the layer-2 part of D3 in `tests/website/test_layers_quality.py`: 1–4 `.metric` figures; no `table` outside a chart's `<details>`; at most one sentence of prose before the first figure; a link to `#metrics` exists
- [X] T025 [P] [US2] Tests for the comparison bar in `tests/website/test_charts.py`: a metric card with `compare` renders an inline SVG with `role="img"` and a text alternative naming both values; the bar lengths are proportional on one scale; a card without `compare` renders no bar; no new fact appears in `_build/facts.json`

### Implementation for User Story 2

- [X] T026 [US2] Add `comparison_bar(value, compare, unit, label, compare_label) -> Markup` in `src/mobility_model_zoo/site/charts.py`: server-rendered inline SVG, two bars on one scale, numbers as text next to the bars, `role="img"` with `aria-label`, colours from tokens; call it from `_card()` in `src/mobility_model_zoo/site/build.py` when the card has a comparison
- [X] T027 [US2] Rewrite `src/mobility_model_zoo/site/templates/partials/quality.html.j2` as layer 2 in this order: heading; at most one lead sentence; benchmark and deterministic-check line; headline figures with bars; charts with their value tables in `<details>`; link "All metrics of version x" to `#metrics`. Move the "All metrics" tables in the same step into a new partial `src/mobility_model_zoo/site/templates/partials/metrics.html.j2` (`id="metrics"`, tables open) included in the `details` layer, so no deployable state lacks them (analysis I1)
- [X] T028 [US2] Implement the layer-2 part of D3 as `check_quality_layer(out)` in `src/mobility_model_zoo/site/check.py`; register it in `run_checks`
- [X] T029 [P] [US2] Styles for the bar pair and the compact check line in `src/mobility_model_zoo/site/static/css/site.css`
- [X] T030 [US2] Reduce `metric_cards` to at most 4 in `zoo/models/scout-large/site.yaml` (keep the comparison composite and the DGX Spark throughput with their comparisons) and check `zoo/models/picket-forest/site.yaml` (already 4)

**Checkpoint**: US1 + US2 give the reader "what is it, may I use it, how good and fast" in the first two screens (MVP).

---

## Phase 5: User Story 3 – Know the limits before trying it (Priority: P2)

**Goal**: layer 3 before the quickstart: short form (status sentence, unmet criteria with measured value and target, `limits_short`), evidence links, full texts collapsed.

**Independent Test**: on both pages `#limits` comes before `#quickstart`; the short form has ≤ 5 items and ≤ 120 words and names every unmet criterion with its value; the full limitations text is in the HTML without JavaScript; D1 and rule 18 pass on the real registry and fail on a broken fixture.

### Tests for User Story 3

- [ ] T031 [P] [US3] Tests for check D1 in `tests/website/test_layers_limits.py`: a published `experimental` model without `unmet_criteria` fails; a `released` model with `unmet_criteria` fails; a missing `not_for` or `limits_short` fails; an unresolvable `measured` placeholder or a missing `target.source` file fails
- [ ] T032 [P] [US3] Tests for the limits short form in `tests/website/test_layers_limits.py`: `[data-short=limits]` is the first child content of layer 3; ≤ 5 items and ≤ 120 words; each unmet criterion renders "criterion: measured value (target op value unit)" or "criterion: note"; intended use, out of scope and limitations are inside closed `<details>`; every measured and target number is in `_build/facts.json` (F1)
- [ ] T033 [P] [US3] Tests for gate rule 18 in `tests/release/test_rule18.py` (pattern of `tests/release/test_rule16.py`): `not_for` and `limits_short` required for a new release; `unmet_criteria` non-empty for `experimental`, empty for `released`; each item has `measured` or `note`; each `measured` resolves in the candidate's results; each `target.source` exists at the candidate commit; sandbox models skip

### Implementation for User Story 3

- [ ] T034 [US3] Rewrite `src/mobility_model_zoo/site/templates/partials/limits.html.j2` as layer 3: `<div data-short="limits">` with the status sentence, the unmet rows (T011) and `limits_short`; then evidence links (recipe document `record.recipe.doc` at the tag, results directory `zoo/models/<name>/results/<version>/` at the tag, release notes anchor in `#versions`, compliance record when present); then intended use, out of scope and limitations each in a closed `<details>` with a `<summary>`
- [ ] T035 [US3] Implement check D1 as `check_short_forms(reg)` and the layer-3 parts of D2 and D3 as `check_limits_layer(out)` in `src/mobility_model_zoo/site/check.py`; register both in `run_checks`
- [ ] T036 [US3] Implement gate rule 18 as `rule_18` in `src/mobility_model_zoo/release/gate.py` (docstring: "Status and limits (feature 013)…"), append 18 to `ORDER`, update the module docstring "rules 1-17" to "rules 1-18"; reuse the D1 logic from a shared function in `src/mobility_model_zoo/site/context.py` so gate and site agree
- [ ] T037 [US3] Extend check F2 in `src/mobility_model_zoo/site/check.py` (`_prose`, `check_literal_numbers`) to `card.not_for`, `card.limits_short`, `card.unmet_criteria[].criterion` and `card.unmet_criteria[].note` of every published model's `model.yaml`
- [ ] T038 [US3] Write `card.limits_short` and `card.unmet_criteria` for `zoo/models/picket-forest/model.yaml` from its card limitations, its release record `changes` and the success criteria in `topics/security/tasks/can-ids.md` (criteria: false alarms per hour on unknown vehicles with `measured` `{metric:quality.fa_per_hour_default_unknown_vehicle_unknown_attack_worst}` and the target from the task document; flooding by identifiers missing from calibration as `note`; device evidence emulator-only as `note`); verify each metric name exists in `zoo/models/picket-forest/results/0.2.0/*.json`
- [ ] T039 [US3] Write `card.limits_short` and `card.unmet_criteria` for `zoo/models/scout-large/model.yaml` from its published 0.1.2 card limitations and the success criteria in `specs/004-production-span-model/spec.md`; every `measured` must resolve in `zoo/models/scout-large/results/0.1.2/*.json`. If the published card does not name a missed criterion with its value, do not invent one: record the gap in `specs/013-model-page-layout/validation.md` under "Open compliance gaps" and report it
- [ ] T040 [P] [US3] Styles for the short form (status sentence, criteria list) in `src/mobility_model_zoo/site/static/css/site.css`

**Checkpoint**: limits come before any code, with the unmet criteria and their values.

---

## Phase 6: User Story 4 – Try it in a few minutes (Priority: P2)

**Goal**: the quickstart as layer 4, unchanged content, reachable from the first screen; no code above `#limits`.

**Independent Test**: from the top, the "Quickstart" jump link lands on `#quickstart`; the quickstart shows install, run and expected output; no `pre` or `code` block occurs before `#limits`.

- [ ] T041 [P] [US4] Tests in `tests/website/test_layers_quickstart.py`: `#quickstart` is layer 4 and contains the install and run code and the expected output; the NC notice is present for an NC fixture model; no `pre` element and no `code` element outside inline text appears in a section before `#limits` (FR-023)
- [ ] T042 [US4] Trim `src/mobility_model_zoo/site/templates/partials/quickstart.html.j2` to layer 4 content only (hardware note, NC notice, install, run, expected output); keep ids `qs-install`, `qs-run`, `qs-out` and the copy buttons
- [ ] T043 [US4] Add the "no code before limits" rule to `check_overview` / `check_quality_layer` in `src/mobility_model_zoo/site/check.py` (finding "code before #limits")

**Checkpoint**: layers 1–4 follow the owner's order.

---

## Phase 7: User Story 5 – Reference and required documents at the end (Priority: P3)

**Goal**: layer 5 (interface short form + examples) and layer 6 (all metrics, notes, provenance and documents, versions, citation); no link lost; old anchors work.

**Independent Test**: the link inventory after the change contains every target of the inventory from T003; every old anchor resolves; A2 (changed) and D5 pass.

### Tests for User Story 5

- [ ] T044 [P] [US5] Tests for D5 and the layer-5 part of D3 in `tests/website/test_layers_reference.py`: the six `data-layer` sections exist once each in contract order; the anchors `#top`, `#why`, `#quickstart`, `#interface`, `#examples`, `#ex1`, `#quality`, `#limits`, `#metrics`, `#provenance`, `#versions`, `#cite`, `#notes`, `#fn-1` resolve; layer 5 has no field table and links `/formats/<id>/` and the JSON schema; a fixture model without examples renders no empty "Worked examples" heading; the deprecation banner of a deprecated fixture release is above `<main>` (analysis G2, G3)
- [ ] T045 [P] [US5] Update the A2 test in `tests/website/test_browser.py` (slow): without JavaScript a model page contains the quickstart code, every example's JSON, the limitations text inside layer 3 and a link to its format page; the format page contains its field table

### Implementation for User Story 5

- [ ] T046 [US5] In `src/mobility_model_zoo/site/templates/partials/metrics.html.j2` (created by T027 with the full tables) move the notes block from `model.html.j2` into it below the tables (`id="notes"`, items `fn-<N>`)
- [ ] T047 [US5] Rewrite `src/mobility_model_zoo/site/templates/partials/interface.html.j2` to the short form: `card.input_output`, the input and guarantee lists of the format, a prominent link to `/formats/<id>/` and to the JSON schema; remove the field table include, the edge-case table and the versioning text from the model page (they stay on `format.html.j2`)
- [ ] T048 [US5] Assemble layer 6 in `src/mobility_model_zoo/site/templates/model.html.j2`: `metrics.html.j2`, `provenance.html.j2`, `versions.html.j2`, `cite.html.j2` inside `<section id="details" data-layer="details">` with a short heading "Details and documents"
- [ ] T049 [US5] Change check A2 in `src/mobility_model_zoo/site/a11y.py`: drop `"#interface table.tbl": "field table"` for model pages; require a link to the model's format page; add the field-table requirement for each `formats/<id>/` page; update the module docstring
- [ ] T050 [US5] Implement D5 and the layer-5 part of D3 as `check_layer_order(out)` in `src/mobility_model_zoo/site/check.py`; register it in `run_checks`; L3 keeps its limitations link target `#limits`
- [ ] T051 [US5] Rebuild the site, write the link inventory after the change to `specs/013-model-page-layout/validation.md` under "Link inventory after" and confirm no target from T003 is missing (SC-006); any missing target is a failing result to fix, not to accept

**Checkpoint**: all six layers in place; nothing required lost.

---

## Phase 8: User Story 6 – Same structure for every model and every new release (Priority: P3)

**Goal**: budgets enforced on input (gate rule 17) and on the page (D2), placement measured in the browser (D6), the model card in layer order from the next release, all models carrying the short forms.

**Independent Test**: `zoo check` fails on a release candidate whose site text breaks a budget; `zoo site check --a11y` reports positions within SC-001–SC-003; the card golden file shows the new section order and no changed number.

### Tests for User Story 6

- [ ] T052 [P] [US6] Tests for the extended gate rule 17 in `tests/release/test_gate_site_text.py`: a differentiator text over 20 words, an audience over 25 words, 5 differentiators, a `not_for` over 40 words or a `limits_short` over 5 items fails with model, field and count
- [ ] T053 [P] [US6] Tests for the complete D2 in `tests/website/test_budgets.py`: running text before `#quality` ≤ 200 words on both fixture pages; a fixture with a long tagline plus audience over budget fails
- [ ] T054 [P] [US6] Browser test for D6 in `tests/website/test_browser.py` (slow): at 1440 × 900 the first `.metric` or `figure.chart` top ≤ 1800 px and `#limits` top ≤ 3600 px; status, usage class and licence chips inside the first 900 px; at 390 × 844 the chips inside the first 1688 px and no horizontal scroll
- [ ] T055 [P] [US6] Card tests in `tests/release/test_card_build.py`: `test_every_section_present_and_in_order` expects the new `cards.SECTIONS`; a new test renders a card from a `model.yaml` without `not_for`, `limits_short`, `unmet_criteria` (old tag) without error and without the short-form blocks; a new test asserts the "Not for:" list under Summary and the short form at the top of "Limitations and risks" when the fields exist

### Implementation for User Story 6

- [ ] T056 [US6] Extend `pitch_errors()` in `src/mobility_model_zoo/site/context.py` (gate rule 17) with the word and item limits from `budgets.py` for `differentiators`, `audience`, `card.not_for` and `card.limits_short`, and reject the words "experimental", "released" and "production ready" in `tagline`, `audience` and differentiators (analysis G1)
- [ ] T057 [US6] Implement the complete D2 (`WORDS_BEFORE_QUALITY` and all per-layer budgets, one function over all model pages) in `src/mobility_model_zoo/site/check.py`, reusing the layer checks of T020, T028, T035
- [ ] T058 [US6] Implement D6 in `src/mobility_model_zoo/site/a11y.py`: measure at 1440 × 900 and 390 × 844 the positions listed in contracts/checks.md D6; report each measured value; findings fail the run
- [ ] T059 [US6] Change `SECTIONS` in `src/mobility_model_zoo/release/card.py` to the order of [contracts/card-order.md](contracts/card-order.md) (Summary, Quality, Speed and memory, Limitations and risks, Intended use, Out-of-scope use, How to run it, Input and output, Examples, Training data provenance, Training recipe, Version history, License, Citation, About the zoo); keep `COMPLIANCE_SECTIONS` replacing "Training data provenance" at its position
- [ ] T060 [US6] Reorder `src/mobility_model_zoo/release/templates/model_card.md.j2` to `SECTIONS`; add "Not for:" with the `not_for` items at the end of Summary and, at the top of "Limitations and risks", the status sentence, the unmet criteria (criterion: measured value, target) and `limits_short`, each block only when the field exists; numbers via `card.num()`
- [ ] T061 [US6] Regenerate the golden card with `ZOO_UPDATE_GOLDEN=1 uv run pytest tests/release/test_card_build.py -k golden`; review the diff: only moved sections and the new short-form blocks, no changed number; note the review result in `specs/013-model-page-layout/validation.md`
- [ ] T062 [P] [US6] Add `card.not_for`, `card.limits_short` and `card.unmet_criteria` to the unpublished models `zoo/models/hum-fan/model.yaml`, `zoo/models/pace-cnn/model.yaml` and `zoo/models/picket-mlp/model.yaml` from their card texts and task success criteria (the task document named in each model's release `recipe.doc`, for example `topics/condition-monitoring/tasks/activity.md` or `topics/security/tasks/can-ids.md`), so their next release passes rule 18; every `measured` must resolve in their latest results
- [ ] T063 [US6] Run `uv run pytest tests/release/test_card_emlearn.py tests/release/test_card_mcu.py tests/release/test_deprecate_from_tag.py` and fix fallout from the new section order (device cards, deprecation re-render from an old tag)

**Checkpoint**: every model page and every new card follows the layers; regressions fail CI.

---

## Phase 9: Polish & cross-cutting concerns

- [ ] T064 [P] Update `docs/website.md`: the six layers and their sources, the budget table, checks D1–D6, the changed A2, gate rule 18
- [ ] T065 [P] Update `docs/adding-a-model.md`: the new `card` fields `not_for`, `limits_short`, `unmet_criteria` with one example, the `site.yaml` word limits, gate rule 18
- [ ] T066 [P] Add `src/mobility_model_zoo/site/budgets.py`, `tests/website/test_budgets.py`, `tests/website/test_layers_*.py` and `tests/release/test_rule18.py` to the path filters in `scripts/ci/select_tests.py` so site and release test jobs run when they change
- [ ] T067 Run the full validation of [quickstart.md](quickstart.md) steps 1–5: `uv run pytest tests/website tests/release`, `uv run zoo site build`, `uv run zoo site check --a11y`; record D6 positions for both models next to the baseline in `specs/013-model-page-layout/validation.md` (SC-001–SC-004, SC-007)
- [ ] T068 Run `uv run zoo compliance check` (REUSE, C1) and add licence headers to every new file
- [ ] T070 Report the scout-large card gap (analysis U1): its published 0.1.2 card neither states "not production ready" nor names unmet success criteria with values (constitution 2.2.0, IX, amended after that release). Write the finding and the proposed fix (a card-only patch release 0.1.3 rendered with the new card template and the `unmet_criteria` of T039, for the owner to approve) to `specs/013-model-page-layout/validation.md` under "Open compliance gaps"; do not publish anything
- [ ] T069 Prepare the reader test (SC-005): five-question script and result table in `specs/013-model-page-layout/validation.md` under "Reader test"; to be run after deployment, combinable with feature 008's open SC-001 test

---

## Dependencies & execution order

### Phase dependencies

- **Setup (Phase 1)**: T001 first (needs 012 merged); T002, T003 after T001, in parallel.
- **Foundational (Phase 2)**: after Setup; blocks all stories. T004 → T005; T006 → T008; T009, T010, T011 → T013; T012 before any partial rewrite; T014 after T006 and T007.
- **US1 (Phase 3)** and **US2 (Phase 4)**: after Phase 2; independent of each other (different partials). Together they are the MVP.
- **US3 (Phase 5)**: after Phase 2; T036 (rule 18) shares a function with T035 (D1).
- **US4 (Phase 6)**: after Phase 2; T043 extends checks of T020 and T028, so after US1 and US2.
- **US5 (Phase 7)**: after Phase 2; T046 extends the partial that T027 creates, so after US2.
- **US6 (Phase 8)**: after US1–US5 (D2 and D6 measure the finished page; T056 reuses budgets of US1/US3 content).
- **Polish (Phase 9)**: after all stories.

### Within each story

Tests first and failing, then templates and context, then checks, then content, then the story checkpoint.

### Parallel opportunities

- Phase 1: T002 ∥ T003.
- Phase 2: T005 ∥ T007 ∥ T008 once T004 and T006 exist.
- US1: T015 ∥ T016 ∥ T021.
- US2: T024 ∥ T025 ∥ T029.
- US3: T031 ∥ T032 ∥ T033 ∥ T040.
- US1, US2 and US3 can be worked on in parallel after Phase 2 (different partials and check functions); `check.py` edits must be merged carefully.
- US6: T052 ∥ T053 ∥ T054 ∥ T055 ∥ T062.
- Polish: T064 ∥ T065 ∥ T066.

### Parallel example: User Story 1

```text
T015 tests for D4 in tests/website/test_layers_overview.py
T016 tests for layer-1 budgets in tests/website/test_layers_overview.py   (same file: write after T015 or in one go)
T021 styles in src/mobility_model_zoo/site/static/css/site.css
```

### Parallel example: User Story 3

```text
T031 D1 tests in tests/website/test_layers_limits.py
T033 rule 18 tests in tests/release/test_rule18.py
T040 short-form styles in src/mobility_model_zoo/site/static/css/site.css
```

## Implementation strategy

### MVP first (US1 + US2)

1. Phases 1 and 2.
2. US1: the first screen with status, terms, reasons and "not for".
3. US2: quality and speed with figures and charts directly below.
4. Stop and validate: SC-001 and SC-002 on both pages; the experimental status of scout-large is now visible (Constitution IX gap closed). This alone is deployable: layers 3–6 still exist in the skeleton order.

### Incremental delivery

1. MVP (US1 + US2) → deploy.
2. US3 (limits short form, rule 18) → deploy: experimental releases name their unmet criteria.
3. US4 (quickstart placement) and US5 (reference and details, A2 change) → deploy.
4. US6 (budget enforcement, placement check, card order) → merge before the next model release so it ships with the new card.

## Notes

- [P] = different files, no dependency on unfinished tasks; tests in the same file are written together.
- Published cards, release records and model files are not changed by any task (Constitution IX).
- Content tasks (T022, T023, T030, T038, T039, T062) take text only from the models' existing cards, records, results and task documents; a missing fact is reported (T039), never invented.
- Commit after each task or logical group; the owner approves releases only.
