---
description: "Task list for the zoo website with a landing page for scout-large"
---

# Tasks: Zoo website with a landing page for scout-large

**Input**: Design documents from `/specs/008-zoo-website/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (cli.md, site-tree.md, checks.md, site-yaml.schema.json), quickstart.md

**Tests**: Included. The plan defines `tests/website/` (unit, golden, property, slow browser tests), and the spec's success criteria SC-003 to SC-006 are verified by automated checks.

**Organization**: Tasks are grouped by user story. Paths are relative to the repository root. Check IDs (B1…C1) refer to `contracts/checks.md`. Section numbers refer to `contracts/site-tree.md`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: User story from spec.md (US1–US5)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Dependencies, package skeleton, licences, CLI wiring

- [X] T001 Add `"markdown-it-py>=3.0"` to the `release` extra and a new dependency group `site-check = ["playwright>=1.47"]` under `[dependency-groups]` in `pyproject.toml`; run `uv lock` to update `uv.lock`
- [X] T002 Create the package skeleton `src/mobility_model_zoo/site/__init__.py` (module docstring only) and empty folders `src/mobility_model_zoo/site/{templates/partials,static/css,static/js,static/fonts,static/img/motifs,schemas}/` (with `.gitkeep` where empty), and `tests/website/__init__.py`
- [X] T003 [P] Add `/_site/` and `/.cache/` to `.gitignore`, with the comment `# Website build output and example-output cache (feature 008); regenerated, never committed`
- [X] T004 [P] Copy `specs/008-zoo-website/design/source/fonts/Figtree-variable-latin.woff2` and `JetBrainsMono-variable-latin.woff2` to `src/mobility_model_zoo/site/static/fonts/`; add `src/mobility_model_zoo/site/static/fonts/OFL.txt` with the SIL OFL 1.1 text and both copyright lines ("Copyright 2022 The Figtree Project Authors (https://github.com/erikdkennedy/figtree)", "Copyright 2020 The JetBrains Mono Project Authors (https://github.com/JetBrains/JetBrainsMono)"); add `LICENSES/OFL-1.1.txt` (via `uv run reuse download OFL-1.1`)
- [X] T005 [P] Vendor axe-core: download a pinned `axe.min.js` release (record version and sha256 in a header comment) into `src/mobility_model_zoo/site/checks_vendor/axe.min.js`; add `LICENSES/MPL-2.0.txt` (via `uv run reuse download MPL-2.0`); exclude `checks_vendor/` from anything copied into `_site/`
- [X] T006 Extend `src/mobility_model_zoo/compliance/templates/REUSE.toml.j2` with `[[annotations]]` for `src/mobility_model_zoo/site/static/fonts/**` (SPDX-FileCopyrightText: both font copyright lines; SPDX-License-Identifier `OFL-1.1`) and `src/mobility_model_zoo/site/checks_vendor/**` (Deque Systems copyright; `MPL-2.0`), each with `precedence = "override"`; add both components to `src/mobility_model_zoo/compliance/templates/THIRD_PARTY_NOTICES.md.j2`; run `uv run zoo compliance render` and confirm `uv run reuse --root . lint` passes (depends on T004, T005)
- [X] T007 Create `src/mobility_model_zoo/site/cli.py` with a Typer app `site_app` and the stub commands `build`, `check` and `serve`, with the options of `contracts/cli.md` (`--out _site`, `--offline`, `--refresh-examples`, `--a11y/--no-a11y`, `--only`, `--port 8000`); mount it in `src/mobility_model_zoo/release/cli.py` with `app.add_typer(site_app, name="site")` next to `compliance` and `data`; map `GateFailed` to exit 1 and `UsageError`/`ZooError` to exit 2, the same way as the existing commands

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Data loading, fact resolution, base layout, build loop and check runner that every page needs

**⚠️ CRITICAL**: No user-story work can begin until this phase is complete

- [X] T008 Create the site-wide config `zoo/site.yaml` per data-model.md "SiteConfig": `title: Mobility Model Zoo`, `canonical_url: https://mhabedank.github.io/mobility-model-zoo/`, `tagline` (no digits), the four `principles` copied in meaning from `docs/hf-org/README.md` "How we publish" (Measured, not claimed; Immutable versions; Open method, closed data; Compliance), `legal.imprint: https://miskatonic-analytics.com/imprint.html`, `legal.privacy` and `legal.copyright` as GitHub `blob/main` URLs of `PRIVACY.md` and `COPYRIGHT_POLICY.md`, `repo: https://github.com/mhabedank/mobility-model-zoo`, `hf_org: https://huggingface.co/mobility-model-zoo`
- [X] T009 [P] Create `src/mobility_model_zoo/site/schemas/site.schema.json` by copying `specs/008-zoo-website/contracts/site-yaml.schema.json` (per-model pitch), and `src/mobility_model_zoo/site/schemas/site-config.schema.json` for `zoo/site.yaml` (all SiteConfig fields required, URLs as `format: uri`, `principles` 3–6 items of `{title, text}`)
- [X] T010 Implement `src/mobility_model_zoo/site/context.py`. Contents:
  - `load_site_config(reg)`.
  - `site_models(reg)`, returning `SiteModel` dicts per data-model.md. It skips sandbox models (same rule as `release/index.py`). Status is derived as specified: "`published`: at least one published version not deprecated. `deprecated`: the latest is deprecated. `in_progress`: no published version." `latest` is computed with `parse_version` over `Registry.published_versions(name)`.
  - `site_release(reg, name, ver)` per "SiteRelease". It includes links only when the file exists: `releases/<ver>.training-data-summary.md`, `<ver>.ai-act.md`, `<ver>.compliance.yaml`, as GitHub URLs at tag `<name>/v<ver>`. It also includes the HF tree at `published.repo_commit`, and `deprecated` (`null` or `{reason, successor}`). Release `status` uses the schema enum "`experimental` / `released` / `deprecated`"; a model is `deprecated` when the latest published record has a non-null `deprecated` object.
  - `load_pitch(reg, name)`, which validates against `site.schema.json` and raises `GateFailed("B1 …")` on failure or when a published model has no `site.yaml`.
- [X] T011 Implement metric resolution in `src/mobility_model_zoo/site/facts.py`. Contents:
  - A `Facts` collector that records `(page, key, value, source_file, json_path)` and writes `_build/facts.json`.
  - `metric(reg, name, ver, "quality"|"performance", metric_name)`. It returns the value formatted with `mobility_model_zoo.release.card.num`, plus unit, reference/benchmark (quality) or hardware (performance). It raises `GateFailed("B2 …")` when the metric is missing, when a quality metric lacks `reference` or `benchmark`, or when a performance metric lacks `hardware`.
  - `resolve_placeholders(text, …)`, which replaces `{metric:<kind>.<name>}`, records each fact and returns footnote ids.
- [X] T012 [P] Implement `src/mobility_model_zoo/site/markdown.py`: `md(text) -> Markup` using `markdown_it.MarkdownIt("commonmark", {"html": False})`, used for `intended_use`, `out_of_scope`, `limitations`, `input_output` and `changes`
- [X] T013 [P] Create `src/mobility_model_zoo/site/static/css/tokens.css`:
  - The `.t-light` and `.t-dark` token values from `specs/008-zoo-website/design/source/identity-system.html` (lines 14–15), mapped to `:root` (light) and `@media (prefers-color-scheme: dark) { :root {…} }`, plus `color-scheme: light dark`.
  - The `@font-face` rules for Figtree (`font-weight: 300 900`) and JetBrains Mono (`100 800`) with `font-display: swap`, pointing at `../fonts/*.woff2`.
- [X] T014 [P] Create `src/mobility_model_zoo/site/static/css/site.css` from the component rules in `design/source/identity-system.html` (lines 16–102: type scale, `.wrap`, `.sec`, header/nav, `.btn`, `.chip`, `.tile`, `.metric`, `.code`, `.tbl`, `.callout`, `.hl` job/pain/gain with solid/dashed/dotted underlines, `.viewer`, `.jitem`, `.ft`, `.ch` chart classes, `.lol` latency bars, the mobile breakdown at 640px). Remove the `.mz` scoping, add a visible skip link and a `.copy` button hidden unless `html.js`. Rule from research R9: highlighted spans (`.hl`) always use `--text`, never `--muted`.
- [X] T015 [P] Create `src/mobility_model_zoo/site/static/img/mark.svg` and `favicon.svg` from `specs/008-zoo-website/design/source/mark.svg` (favicon: the same mark with a 512 viewBox, no outline); add `src/mobility_model_zoo/site/static/img/mark-mono.svg` (the monochrome form with `currentColor`, from identity-system.html line 133)
- [X] T016 Create `src/mobility_model_zoo/site/templates/base.html.j2`:
  - `<html lang="en">` with `<meta name="color-scheme" content="light dark">`, viewport, `<title>`, `<link rel="canonical">` from `canonical_url`, and relative links to `assets/css/tokens.css` and `assets/css/site.css`. A `root` variable holds the relative prefix (`""` or `"../../"`).
  - Preload of both fonts, the skip link, `<header>` (mark + wordmark; nav Models, Topics, Principles, Hugging Face, GitHub), and a `<main id="main">` block.
  - `<footer>` with the imprint, privacy notice, copyright policy and licence links and the line "Private, non-commercial project. No cookies, no analytics, no third-party requests."
  - `<script src="…assets/js/site.js" defer>`.
  - No absolute URLs to assets.
- [X] T017 Implement `src/mobility_model_zoo/site/build.py`:
  - `build(reg, out, offline, refresh)`. It empties `out`, copies `static/` to `out/assets/` (excluding `checks_vendor/`) and creates a Jinja2 `Environment` with `PackageLoader("mobility_model_zoo.site")`, `StrictUndefined`, `autoescape=True` and filters `num` and `md`.
  - A page registry that renders each page with its `root` prefix, writes `_build/facts.json`, and prints `site: <n> pages, <m> models (<k> in progress)`.
  - Wire it to `zoo site build` in `cli.py`.
- [X] T018 Implement `src/mobility_model_zoo/site/check.py`, the runner: it collects findings `(check_id, page, detail)`, supports `--only`, prints one line each and raises `GateFailed` if there are any. Wire it to `zoo site check`. Implement `zoo site serve` in `cli.py`: `http.server` serving `out` under the prefix `/mobility-model-zoo/`.
- [X] T019 Create the test fixture registry `tests/website/fixtures/registry/` by copying the minimal structure of `tests/release/fixtures/registry/zoo/`. It contains one published model with two versions (one deprecated), one in-progress model, one sandbox model, a `site.yaml` for the published model and `zoo/site.yaml`. Add `tests/website/fixtures/cache/<model>/<version>.json` with example outputs, so tests run offline. Add `tests/website/conftest.py` with a `site_env` fixture (chdir into a temp copy, `Registry(root)`).
- [X] T020 [P] Unit tests in `tests/website/test_context.py`:
  - status derivation (published / deprecated / in_progress, sandbox excluded),
  - `latest` selection,
  - release links only for existing files,
  - B1 raised for a missing or invalid `site.yaml`.
- [X] T021 [P] Unit tests in `tests/website/test_facts.py`:
  - placeholder resolution, with values equal to `card.num` output;
  - B2 for an unknown metric, a quality metric without `reference`/`benchmark`, and a performance metric without `hardware`;
  - `facts.json` content.

**Checkpoint**: `uv run zoo site build` writes an empty-shell site with header and footer; foundation tests pass

---

## Phase 3: User Story 1 - Understand and try scout-large in minutes (Priority: P1) 🎯 MVP

**Goal**: The scout-large page with hero, "Why this model", quickstart (including expected output) and the quality and speed section, all from release data.

**Independent Test**: A newcomer reading only `/models/scout-large/` names the main advantage, a main limitation and the hardware it needs, and runs the quickstart to get the shown output (quickstart.md scenarios 2–3).

### Tests for User Story 1

- [X] T022 [P] [US1] (Done as structural assertions instead of a golden HTML file, so a new release does not need a golden update.) Golden test in `tests/website/test_model_page.py`: build the fixture site and compare `models/<name>/index.html` with `tests/website/fixtures/golden/model.html` (regenerate with `--update-golden`). Assert the section anchors `#top #why #quickstart #interface #examples #quality #limits #provenance #versions #cite` appear in this order.
- [X] T023 [P] [US1] Property test F2 in `tests/website/test_no_literal_numbers.py`. Fail on any free-standing number matching `(?<![\w.,-])\d+(?:[.,]\d+)*(?![\w-]|[.,]\d)` outside `{metric:…}` placeholders in every `zoo/models/*/site.yaml` and in the text nodes of `src/mobility_model_zoo/site/templates/**/*.j2` (attribute values, `<style>` and SVG geometry excluded). Allow digits inside names (e.g. "M3 Pro", "jtbd-span-v1").
- [X] T024 [P] [US1] Test F4 in `tests/website/test_card_parity.py`: for the fixture model, every number in the `#quality` section and in the resolved differentiators also appears in `release.card.render(CardInput(...))` for the same version.
- [X] T025 [P] [US1] Unit tests in `tests/website/test_examples.py`:
  - parsing card markdown with three `### Example ... `file`` blocks;
  - cache hit/miss keyed by `repo_commit`; a card whose sha256 differs from `published.card_sha256` raises B3;
  - `--offline` failure on a missing cache entry;
  - a truncated (non-JSON) output raises B3 naming the example.

### Implementation for User Story 1

- [X] T026 [US1] Move the parser of `publish._examples_from_hub()` (`src/mobility_model_zoo/release/publish.py`, line ~323) into a shared function `parse_card_examples(markdown: str) -> dict[str, str]` in `src/mobility_model_zoo/release/card.py`. Make `_examples_from_hub` call it, and add an optional `revision` argument (default `"main"`) to its download. Existing tests in `tests/release/` must still pass.
- [X] T027 [US1] Implement `src/mobility_model_zoo/site/examples.py`:
  - `example_outputs(reg, name, version, offline, refresh)`. It downloads `README.md` of `repos.public` at `published.repo_commit` of the release record through `huggingface_hub.hf_hub_download`, checks that the sha256 of the downloaded bytes equals `published.card_sha256` (else `GateFailed("B3 card hash …")`), and caches the result in `.cache/site/<name>/<version>.json` as `{repo_commit, card_sha256, outputs}`.
  - It parses with `parse_card_examples` and `json.loads` each output, raising `GateFailed("B3 <file>: …")` on a parse failure.
  - It returns `Example` dicts (`file`, `text`, `source`, `output`) per data-model.md.
- [X] T028 [US1] Create `zoo/models/scout-large/site.yaml` (validates against `site.schema.json`):
  - `tagline`: jobs, pains and gains from mobility texts, as verbatim quotes, run locally.
  - `audience`: product managers, UX researchers and ML engineers in mobility.
  - 4 `differentiators`, with numbers only as placeholders:
    - Runs locally: `{metric:performance.latency_9k_chars_s}` on 4 CPU cores with `{metric:performance.peak_ram_gb}`.
    - Fast: `{metric:performance.chunks_per_min_dgx_spark_gpu}` on a DGX Spark against the generative models.
    - Evidence you can check: every item is a verbatim quote with offsets; `{metric:quality.quotes_verbatim_rate}` verbatim.
    - Measured: `{metric:quality.comparison_composite}` vs `{metric:quality.comparison_composite_best_baseline}` agreement with frontier reference models.
  - `quickstart_example: 02-depot-charging.txt`.
  - `hardware_note` naming the CPU/GPU options via placeholders.
  - `motif: scout-large.svg`.
  - `charts`: `[{type: quality_vs_speed, metrics: chunks_per_min, labels: topics/productdev/recipes/figures/scout-large-comparison.json}, {type: latency_per_machine, metrics: latency_9k_chars_s, labels: topics/productdev/recipes/figures/scout-large-comparison.json}]`.
- [X] T029 [US1] Add release-gate rule 17 "site text" in `src/mobility_model_zoo/release/gate.py`, following the pattern of `rule_16`: for non-sandbox models, `zoo/models/<name>/site.yaml` must exist and validate against `src/mobility_model_zoo/site/schemas/site.schema.json`; every `{metric:…}` placeholder must resolve in the candidate's `results/<ver>/*.json` with `reference`+`benchmark` or `hardware` (reuse `site.facts.metric`); `quickstart_example` must exist in `examples/`; every `charts[].labels` path must exist. Add 17 to the rule set that `zoo publish` runs (`only`, currently 1–11 and 14) and to the docstring/contract list. Tests in `tests/release/test_gate_site_text.py`: missing file, bad placeholder, missing example each fail; the scout-large fixture passes
- [X] T030 [P] [US1] Create the motif `src/mobility_model_zoo/site/static/img/motifs/scout-large.svg` from the sub-mark in `design/source/identity-system.html` (line 202, `viewBox 0 0 96 96`, strokes with `var(--border-strong)`, `var(--mark)`, `var(--text)`). Add the hero graphic `motifs/scout-large-hero.svg` from line 206, with job/pain/gain spans. Give both `role="img"` with an `aria-label` when used inline.
- [X] T031 [P] [US1] Implement `src/mobility_model_zoo/site/charts.py`, producing inline SVG/HTML (research R6, design section 06). Charts are rendered only as declared in `site.yaml` `charts` (`type`, `metrics` prefix, `labels` path); without the declaration the section shows metric cards only. Label files are read at the release tag with `git show <name>/v<ver>:<path>` (as `card.model_at_tag` does); only labels are taken from them, all numbers come from the results JSON:
  - `quality_vs_speed(reg, name, ver)`. It uses a log x-axis of texts per minute (0.1 to 10,000) and a y-axis of the comparison composite. scout-large is one filled point per machine (`chunks_per_min*` metrics). The best zero-shot small model is a dashed line (`comparison_composite_best_baseline`). The comparison models are points or a band from `comparison_composite_<id>` and `comparison_chunks_per_min_<id>`, with display labels from the declared label file's `others[].label` (fallback: the id).
  - `latency_per_machine(...)`: HTML bars `.lol` for `latency_9k_chars_s` (4 vCPU reference), `_mac_m3pro_cpu`, `_mac_m3pro_gpu` and `_dgx_spark_gpu`, labelled from the declared label file's `scout[].label`.
  - Each chart returns an `aria-label` plus a `<table>` of all values for a `<details>` element, and records every number in `Facts`.
- [X] T032 [US1] Create `src/mobility_model_zoo/site/templates/model.html.j2` (extends base) with partials:
  - `partials/hero.html.j2`: §1 title, tagline, audience, language and licence chips, CTA to `#quickstart`, motif.
  - `partials/why.html.j2`: §2 differentiators, with each resolved number linked to a footnote giving reference/benchmark or hardware.
  - `partials/quickstart.html.j2`: §3 the `card.install` line with `<tag>` replaced by `<name>/v<latest>`, `card.how_to_run` with `{repo_id}`, `{revision}` and `{text}` filled exactly as `release/card.py` does, the quickstart example's input text and its output JSON from T027, and the hardware note. Code blocks get `.code` with a copy button.
  - `partials/quality.html.j2`: §6 first a visible line with the frozen benchmark version (`benchmark` of the quality metrics), the deterministic checks `quotes_verbatim_rate`, `schema_valid_rate`, `consistency_rate` and the count `contested_items` (Principle III, gate before reporting a result); then metric cards (composite vs best baseline, latency per machine, peak memory, DGX throughput), the charts declared in `site.yaml` (T031), and a `<details>` table with every metric of `quality.json` and `performance.json` (name, value, unit, description, reference/benchmark or hardware).
  - Placeholder `{% block %}`s for §4, §5 and §7–§10, filled by US2 and US4.
- [X] T033 [US1] Register the model page in `build.py` for every model with `status != in_progress`, at `models/<name>/index.html` with `root="../../"`, and record all facts. Run `uv run zoo site build` against the real registry and confirm the scout-large page shows 0.72 next to "agreement with frontier reference models" and benchmark `pilot-v2`, and the pinned install line `scout-large/v0.1.2`.
- [X] T034 [US1] Implement the static part of check F1 in `check.py`: for each entry of `_build/facts.json`, reload the source JSON/YAML path and compare it with `card.num(value)`. Implement F2 over `site.yaml` files and templates (same regex as T023), and F3: no "accuracy" (case-insensitive) in the rendered text of pages of model-labeled tasks. The task is model-labeled when `quality.json` metrics carry a `reference` naming reference models.

**Checkpoint**: The scout-large page answers "what, why, how fast, how to run" with sourced numbers; US1 tests pass

---

## Phase 4: User Story 2 - Integrate the model's output (Priority: P1)

**Goal**: The interface documentation of `jtbd-span-v1` (on the model page and as its own format page) and worked examples in the output viewer.

**Independent Test**: A parser written only from `/formats/jtbd-span-v1/` accepts all three example outputs shown on the page, and every quote equals `text[start:end]` (quickstart.md scenario 4, SC-003).

### Tests for User Story 2

- [X] T035 [P] [US2] Unit tests in `tests/website/test_schema_doc.py`:
  - flattening `src/mobility_model_zoo/productdev/jtbd/span/jtbd-span-v1.schema.json` yields the paths `output_format_version`, `relevant`, `relevance_probability`, `dimensions`, `items[]`, `items[].kind`, `items[].quote`, `items[].start`, `items[].end`, `items[].score`, `items[].actor_type`, `items[].evidence_type`, `items[].evidence_scope`, with enums (e.g. `actor_type`: `individual, worker, organization, public_sector, society`);
  - B5 is raised for a schema path without a meaning and for a meaning without a schema path.
- [X] T036 [P] [US2] Unit tests in `tests/website/test_spans.py`:
  - B3 is raised when `text[start:end] != quote` or when spans overlap;
  - an output with `relevant: false` and empty `items` renders as "no items (valid result)";
  - B4 is raised for an example whose `SOURCES.yaml` source is not `synthetic`.

### Implementation for User Story 2

- [X] T037 [US2] Create `zoo/formats/jtbd-span-v1.yaml` with one entry per schema path from T035: `meaning`, `empty_case` and `notes`. The content comes from `zoo/models/scout-large/model.yaml` `card.input_output`, the docstrings in `src/mobility_model_zoo/productdev/jtbd/span/`, and the dimension definitions in `topics/productdev/guideline/guideline-v2.md`. Write `empty_case` for `items` as "An empty list is a valid result, also when `relevant` is true". Add top-level `input` notes: German or English, any length, read in overlapping 512-token windows; other languages untested.
- [X] T038 [US2] Implement `src/mobility_model_zoo/site/schema_doc.py`:
  - `output_format(reg, format_id)`, which locates the schema by `output_format_version`, using a mapping `{"jtbd-span-v1": "src/mobility_model_zoo/productdev/jtbd/span/jtbd-span-v1.schema.json"}` declared in `zoo/formats/jtbd-span-v1.yaml` as `schema:`.
  - It flattens the schema into rows (`path`, `type`, `enum`, `required`, `nullable`), merges the meanings, and computes `produced_by` from all release records whose `output_format_version` matches.
  - It raises B5 on any mismatch.
- [X] T039 [US2] Implement the span checks in `src/mobility_model_zoo/site/examples.py`:
  - `is_span_format(schema)`: true when the schema has `items[].quote`, `items[].start` and `items[].end`; span checks and the viewer apply only then.
  - `spans(example)`, which validates each output against the format schema with `jsonschema`, checks `text[start:end] == quote` and no overlaps (B3), and returns ordered segments `{text, marked, kind, item_index}`;
  - the source check against `examples/SOURCES.yaml` (B4).
- [X] T040 [P] [US2] Create `src/mobility_model_zoo/site/templates/partials/interface.html.j2` (§4):
  - the input notes;
  - the field table (`.tbl`: Field, Type, Allowed values, Meaning, Empty case);
  - a dimensions table (`actor_type`, `evidence_type`, `evidence_scope` with their enums);
  - "How the format is versioned": `output_format_version`, the list of releases per format, a link to `../../formats/<id>/`;
  - edge cases: empty text, irrelevant text, long text, other language.
- [X] T041 [P] [US2] Create `src/mobility_model_zoo/site/templates/partials/viewer.html.j2` (§5). Per example:
  - a kinds legend;
  - `.vtext` with `<mark class="hl job|pain|gain" id="ex<n>-q<i>" data-item="<i>">` around each quote, with a `title` of kind and offsets;
  - an ordered list of `.jitem` `<pre>` blocks with the item JSON (`id="ex<n>-i<i>"`) and links in both directions via `href="#…"`, which work without JS;
  - `<details><summary>Full output</summary><pre>` with the complete JSON.
  - For non-span formats (`is_span_format` false, e.g. MCU outputs `{"output": [...]}`): input and output as two `.code` blocks, no highlighting.
- [X] T042 [US2] Create `src/mobility_model_zoo/site/templates/format.html.j2` and register `formats/<id>/index.html` in `build.py` for every format named by any release record. Format pages are never removed, so old formats stay reachable. Fill the §4/§5 blocks of `model.html.j2` with T040/T041 for all examples of the latest release.
- [X] T043 [US2] Implement `src/mobility_model_zoo/site/static/js/site.js` (deferred, ~3 KB, no dependencies):
  - add `html.js`;
  - copy buttons using `navigator.clipboard`, with an "Copied" state and `aria-live`;
  - in the viewer, clicking a `.hl` or `.jitem` toggles `.sel` and `aria-pressed` on both linked elements and scrolls the partner into view.

  Store nothing in cookies or localStorage.

**Checkpoint**: Model page §4–§5 and `/formats/jtbd-span-v1/` are complete; a developer can build a parser from the page alone

---

## Phase 5: User Story 3 - Discover the zoo and its other models (Priority: P2)

**Goal**: The start page with purpose, topics, model tiles (published / in progress) and principles, plus the 404 page and links from the HF org card and README.

**Independent Test**: From `/` alone, a visitor names the topics, reaches scout-large in one click and finds the principles and legal links; the four unpublished models show "in progress" without links (quickstart.md scenario 1).

### Tests for User Story 3

- [X] T044 [P] [US3] Tests in `tests/website/test_start_page.py`:
  - the fixture start page lists every topic of `topics.yaml`;
  - a published tile links to `models/<name>/`;
  - an in-progress tile has no `<a>`, no version and no numbers;
  - sandbox models are absent;
  - a deprecated latest shows the "deprecated" chip;
  - adding a model folder with a published release and a `site.yaml` creates its page with no code change (mirroring `tests/release/test_index.py::test_new_topic_needs_no_code_change`).

### Implementation for User Story 3

- [X] T045 [US3] Create `src/mobility_model_zoo/site/templates/start.html.j2` per `contracts/site-tree.md` "/ start page":
  - the hero (tagline from `zoo/site.yaml`, buttons "Browse the models" → `#models` and "Read the principles" → `#principles`);
  - three value points without numbers;
  - topics with title, description and HF collection link;
  - model tiles: `.tile` with name, topic, task, latest version and chip `published`/`in progress`/`deprecated`, plus the motif if `site.yaml` names one. Only published or deprecated tiles are links.
  - principles.

  Use the layout of `design/source/start-page.html`.
- [X] T046 [P] [US3] Create `src/mobility_model_zoo/site/templates/404.html.j2` (header, a short message, links to `./` and `./#models`). Register `index.html` and `404.html` in `build.py`. GitHub Pages serves `404.html` from the site root, so use absolute-from-root asset paths only there, derived from `canonical_url`'s path `/mobility-model-zoo/`.
- [X] T047 [P] [US3] Add a "Website" line linking `https://mhabedank.github.io/mobility-model-zoo/` to `docs/hf-org/README.md` (under the intro paragraph) and to `README.md` (next to the existing links to `zoo/MODELS.md` and the HF org, around lines 5–6). Add the site link to the template that renders `zoo/MODELS.md` in `src/mobility_model_zoo/release/index.py` and regenerate with `uv run zoo index`.

**Checkpoint**: The site has a home; all three page types build from the registry

---

## Phase 6: User Story 4 - Check whether the model may be used (Priority: P2)

**Goal**: Use-and-limits, licence-and-provenance, versions and citation sections; the privacy notice covers the website; legal links are enforced.

**Independent Test**: A reviewer finds licence, intended use, out-of-scope uses, limitations, training-data summary, AI Act note, privacy notice, copyright policy, imprint and citation from the model page in at most two clicks each (SC-009).

### Tests for User Story 4

- [X] T048 [P] [US4] Tests in `tests/website/test_legal.py`:
  - every built page has the imprint, privacy notice and copyright policy links in `<footer>` (L3);
  - the model page contains every limitation bullet of `model.yaml` `card.limitations` verbatim after markdown rendering;
  - the provenance links point at existing release files;
  - a deprecated version row is marked;
  - P3: no "miskatonic" outside the imprint URL, and no "sponsor", "donate", "pricing" or "consulting" links.

### Implementation for User Story 4

- [X] T049 [P] [US4] Create `src/mobility_model_zoo/site/templates/partials/limits.html.j2` (§7): `card.intended_use` and `card.out_of_scope` as markdown, and all of `card.limitations` in a `.callout` with `role="note"`, shown in full and not collapsed.
- [X] T050 [P] [US4] Create `src/mobility_model_zoo/site/templates/partials/provenance.html.j2` (§8):
  - licence and base model with licence (`base_model`, `base_model_license`);
  - links from `site_release` to the training-data summary, source attribution (the summary's attribution section), the AI Act note and the compliance record of the latest release;
  - links to the HF repo, the recipe (`topics/<topic>/recipes/<name>.md` on GitHub) and the code repository (FR-014).
- [X] T051 [P] [US4] Create `src/mobility_model_zoo/site/templates/partials/versions.html.j2` (§9) and `partials/cite.html.j2` (§10):
  - the versions table, newest first: version, date, status chip, `output_format_version`, `changes` (markdown) and the HF revision link. Deprecated rows are marked.
  - a model-level deprecation banner naming the successor when the record has one.
  - the citation block from `card.citation` with a copy button.
- [X] T052 [US4] Fill the §7–§10 blocks in `model.html.j2` with T049–T051.
- [X] T053 [P] [US4] Add a section "## Website" before "## Recipients" in `src/mobility_model_zoo/compliance/templates/PRIVACY.md.j2`, per research R11:
  - the site address;
  - the host GitHub, Inc. (US), which processes visitors' IP addresses in server logs to deliver and secure the site;
  - the legal basis Art. 6(1)(f) GDPR;
  - no cookies, no analytics and no third-party content on the site;
  - a link to the GitHub General Privacy Statement and GitHub's stated transfer basis;
  - that the controller receives no visitor data.

  Add the matching processing activity "Project website" to `src/mobility_model_zoo/compliance/templates/record-of-processing.md.j2`. Run `uv run zoo compliance render` and commit the regenerated `PRIVACY.md` and `docs/compliance/record-of-processing.md`.
- [X] T054 [US4] Implement checks L3 (legal links in every footer; licence, `#limits` and AI Act links on every model page) and P3 (branding/advertising words, as in T048) in `src/mobility_model_zoo/site/check.py`.

**Checkpoint**: All compliance facts are on or one click from the model page; the privacy notice covers the site

---

## Phase 7: User Story 5 - Recognize the zoo's identity (Priority: P3)

**Goal**: The identity applied consistently: monochrome mark, motifs for later models, Open Graph image, dark mode polish.

**Independent Test**: Side by side with the HF org page, people identify the site as the same project; the mark and colours are identical (`#1B3BD8`, `#6FFFC8`).

- [X] T055 [P] [US5] Add motif sketches for the in-progress models (picket-forest, picket-mlp, hum-fan, pace-cnn) from `design/source/identity-system.html` (lines 218–221) as `src/mobility_model_zoo/site/static/img/motifs/<name>.svg`, used on their tiles only (no model page until published).
- [X] T056 [P] [US5] Create `src/mobility_model_zoo/site/static/img/og.png` (1200×630: mark, wordmark and tagline on `--bg` light) by rendering an SVG with Playwright. The script lives in `scripts/site_og_image.py`. Reference it with `og:image`, `og:title` and `og:description` in `base.html.j2`, using the absolute URL from `canonical_url`, since Open Graph needs absolute URLs.
- [X] T057 [US5] Visual pass against `design/source/*.html` at 1280 px and 390 px in light and dark: spacing, type scale, chips, tiles, metric cards, viewer. Fix deviations in `site.css` only, without changing tokens, so the identity stays swappable (FR-024).

**Checkpoint**: The site matches the delivered identity in both themes and at both widths

---

## Phase 8: Polish & Cross-Cutting Concerns (checks, CI, deployment, docs)

**Purpose**: The checks that block publication, the deployment workflow, documentation and the final validation

- [X] T058 [P] Implement L1 (every internal `href`/`src` and `#anchor` resolves inside `_site/`) and L2 (external links to huggingface.co, github.com and the legal URLs answer 2xx/3xx via `httpx` HEAD with 2 retries; skipped with `--offline`) in `src/mobility_model_zoo/site/check.py`.
- [X] T059 [P] Implement P1 in `check.py`: parse every HTML page (stdlib `html.parser`) and CSS file; any `src`, `srcset`, `poster`, `<link href>`, `<script src>`, CSS `url()` or `@import` that is not relative or `data:` is a finding. `<a href>` is allowed. Implement S1: HTML ≤ 150 KB per page, total size without fonts ≤ 300 KB, and every `<script>` has `defer`.
- [X] T060 Implement the browser checks in `src/mobility_model_zoo/site/a11y.py`, invoked by `zoo site check --a11y`:
  - Start `serve` on a free port and launch Playwright Chromium.
  - For every page and for `color_scheme` in (`light`, `dark`), inject `checks_vendor/axe.min.js` and run `axe.run({runOnly: {type: 'tag', values: ['wcag2a','wcag2aa','wcag21a','wcag21aa']}})`. Each violation is an A1 finding.
  - Record every request; any host other than localhost is a P2 finding. Read `context.cookies()` and `document.cookie`; any value is a P2 finding.
  - In a context with `java_script_enabled=False`, assert the model pages contain `#quickstart pre`, the field table, every example's full JSON and `#limits` (A2).
  - Check that every `img`/`svg[role=img]` has an accessible name and every chart has a data table (A3).
  - Keyboard (A4): press Tab repeatedly; the first focus is the skip link; every `a`, `button` and viewer control is reached in document order; each focused element has a computed `outline-width` ≥ 2px.
  - Load time (S2): with CDP `Network.emulateNetworkConditions` (1.6 Mbps down, 150 ms latency) and `Emulation.setCPUThrottlingRate` 4, read Largest Contentful Paint via `PerformanceObserver`; > 2,000 ms on any page is a finding.
- [X] T061 [P] Slow tests in `tests/website/test_browser.py` (`@pytest.mark.slow`, skipped if Playwright is missing). They run T060 against the fixture site and assert zero findings, and assert failures for injected faults: a Google Fonts `<link>` gives P1/P2; `--muted` text on `.hl.job` in dark mode gives A1; a removed `alt` gives A3; `outline: none` on `:focus-visible` gives A4.
- [X] T062 Create `.github/workflows/site.yml` per `contracts/cli.md`:
  - Triggers: `push` to `main` on the paths `zoo/**`, `src/mobility_model_zoo/site/**`, `PRIVACY.md`, `COPYRIGHT_POLICY.md` and `.github/workflows/site.yml`; `pull_request` on the same paths; `workflow_run` of `release-publish` with `types: [completed]` and `if: github.event.workflow_run.conclusion == 'success'`; `workflow_dispatch`.
  - Job `build`: checkout, setup uv, `uv sync --extra release --group site-check`, `uv run playwright install --with-deps chromium`, `uv run zoo site build`, `uv run zoo site check --a11y`, `rm -rf _site/_build`, `actions/upload-pages-artifact@v3` with `path: _site`.
  - Job `deploy`: only on `refs/heads/main` and not on pull requests; `needs: build`; `permissions: pages: write, id-token: write`; `environment: github-pages`; `actions/deploy-pages@v4`.
  - `concurrency: group: pages, cancel-in-progress: false`.
- [X] T063 [P] Write `docs/website.md`: what the site is, the sources of each section (link data-model.md), how to add a model page (write `zoo/models/<name>/site.yaml`; numbers only as placeholders), `zoo site build|check|serve`, the checks table (link contracts/checks.md), deployment, and the one-time owner step "Settings → Pages → Source: GitHub Actions". Link it from `docs/adding-a-model.md` (new step: write `site.yaml` before the first publish).
- [X] T064 Run `uv run ruff check src tests && uv run ruff format --check src tests`, `uv run pytest tests/website tests/release`, `uv run pytest tests/website -m slow`, `uv run zoo validate --all` and `uv run zoo compliance check --ci`, and fix every finding.
- [X] T065 Run the full validation in `specs/008-zoo-website/quickstart.md`:
  - sections 1–2, with scenario 3 run in a fresh venv against the real HF model;
  - section 3, every negative test fails with the listed check ID.

  Record the results (pass/fail per scenario, date, commit) in `specs/008-zoo-website/validation.md`.
- [ ] T066 Run the SC-001 test after the first deploy: three people from the target group (product, UX research or ML in mobility) who have not seen the project each get the model page URL and at most 3 minutes, then name the main advantage, one main limitation and the needed hardware. Record answers, time and pass/fail per person (no names, no other personal data) in `specs/008-zoo-website/validation.md`; a failure leads to text changes in `zoo/models/scout-large/site.yaml` or the templates.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies. T006 needs T004 and T005; T007 needs T002.
- **Foundational (Phase 2)**: needs Setup and blocks all stories. T010 and T011 need T008 and T009; T016 needs T013–T015; T017 needs T010–T012 and T016; T018 needs T017; T019–T021 need T017.
- **US1 (Phase 3)**: needs Foundational. This is the MVP.
- **US2 (Phase 4)**: needs Foundational and T027 (example outputs) from US1. It is otherwise independent of US1's sections.
- **US3 (Phase 5)**: needs Foundational only. It can run in parallel with US1 and US2. Tile links only resolve once a model page exists (US1).
- **US4 (Phase 6)**: needs Foundational and the `model.html.j2` blocks from T032. T053 (privacy notice) is independent and can start right after Setup.
- **US5 (Phase 7)**: needs US1 and US3 templates in place.
- **Polish (Phase 8)**: T058, T059 and T063 can start after Foundational. T060–T062 need all pages. T064 and T065 come last; T066 (user test) runs after the first deploy.

### Within each story

Tests come first and fail first. Then data and context (`site.yaml`, `zoo/formats/*.yaml`), then modules (`examples.py`, `charts.py`, `schema_doc.py`), then templates, then build registration, then checks.

### Parallel Opportunities

- Setup: T003, T004 and T005 together.
- Foundational: T009, T012, T013, T014 and T015 together; then T020 and T021 together.
- US1: T022–T025 together; T030 and T031 together while T026–T029 run.
- US2: T035 and T036 together; T040 and T041 together.
- US3 can run alongside US1 or US2. T046 and T047 run in parallel with T045.
- US4: T048–T051 and T053 together.
- US5: T055 and T056 together.
- Polish: T058, T059 and T063 together.

## Parallel Example: User Story 1

```text
# Tests first, together:
T022 golden model page        tests/website/test_model_page.py
T023 no literal numbers (F2)  tests/website/test_no_literal_numbers.py
T024 card parity (F4)         tests/website/test_card_parity.py
T025 example outputs          tests/website/test_examples.py

# Then, in parallel with T026–T029:
T030 motif SVGs               src/mobility_model_zoo/site/static/img/motifs/
T031 charts                   src/mobility_model_zoo/site/charts.py
```

## Implementation Strategy

### MVP first (US1)

1. Phase 1 Setup, then Phase 2 Foundational.
2. Phase 3 (US1): the scout-large page with hero, why, quickstart and quality.
3. Stop and validate with quickstart.md scenarios 2–3. The page can be previewed locally with `zoo site serve`.

### Incremental delivery

1. Add US2 (interface and examples). The two P1 stories together are the first deployable model page.
2. Add US3 (start page) and US4 (limits, provenance, privacy notice). These are required before the first public deploy, because FR-016 needs the legal links and the privacy notice.
3. Polish T058–T062 (checks and workflow). The first deploy happens once T062 merges to `main` and the owner has switched Pages to "GitHub Actions".
4. US5 last; the site already uses the identity's tokens from Phase 2.

### Note on the first public deploy

The deploy job must not run before US4 (T053 privacy notice, T054 legal checks) and Polish T058–T061 are done. Merge T062 last.
