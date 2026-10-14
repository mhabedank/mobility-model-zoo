# Tasks: Emotional mobility imagery and prominent model motifs

**Input**: Design documents from `/specs/016-emotional-imagery-motifs/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md), [selection.md](selection.md), [series-siebdruck.yaml](series-siebdruck.yaml)

**Tests**: pytest tasks are included where the plan names a test file; they are written alongside the code, not TDD-first. Browser checks run through `zoo site check --a11y`.

**Organization**: Tasks are grouped by user story. Stories 1 and 2 are both P1 and independent of each other; 3 to 5 build on them.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1 to US5)
- Include exact file paths in descriptions

## Path Conventions

Single project: package in `src/mobility_model_zoo/`, content in `zoo/`, tests in `tests/`, generator in `scripts/imagery/`. The chosen source PNGs are on the DGX Spark under `~/zoo-imagery/out6/` (paths in [selection.md](selection.md)); copy them with `scp` from `dienstollama@10.123.47.52` before the import tasks.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: dependencies, generator script, series file, licence texts, schema

- [X] T001 Add the optional extra `images = ["pillow>=10", "opencv-python-headless>=4.10", "rapidocr-onnxruntime>=1.3"]` to `pyproject.toml` (next to `release`), and the dependency group note in `docs/website.md` "Prerequisites"
- [X] T002 [P] Create `scripts/imagery/gen.py` from the scratchpad generator (series file in, PNGs and `manifest.json` out; models `klein` and `qwen`; `--seeds`, `--steps`, `--only`, `--out`; resumable; manifest entry per image with model, revision, pipeline, prompt, negative_prompt, seed, steps, guidance, width, height, seconds, generated date, hardware class, generator commit and container image digest) per [contracts/cli.md](contracts/cli.md) "Generator"
- [X] T003 [P] Create `scripts/imagery/Dockerfile` (FROM `nvcr.io/nvidia/pytorch:25.09-py3`, `pip uninstall -y torchao`, install `diffusers>=0.41 transformers accelerate sentencepiece protobuf pyyaml huggingface_hub`) and `scripts/imagery/README.md` with the three commands: build `zoo-flux`, cache the models, render a series; note `HF_HUB_DISABLE_XET=1` for downloads and that no token stays on the machine
- [X] T004 [P] Create `zoo/site/images/series/siebdruck.yaml` from `specs/016-emotional-imagery-motifs/series-siebdruck.yaml` (fields `name`, `style`, `negative`, `models.draft`, `models.final`, `subjects` per placement, as in [data-model.md](data-model.md) "Series")
- [X] T005 [P] Add `LICENSES/CC0-1.0.txt` (the CC0 1.0 Universal legal code) and copy `specs/016-emotional-imagery-motifs/contracts/image-record.schema.json` to `src/mobility_model_zoo/site/schemas/image-record.schema.json`
- [X] T006 [P] Add the area `images` to `scripts/ci/select_tests.py`: paths `zoo/site/images/*`, `scripts/imagery/*`, `tests/website/test_images_*`, `tests/imagery/*` → tests `tests/website`, `tests/imagery`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the one motif resolver, the image record loader, the plate component, the import pipeline and the check scaffolding every story uses

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T007 Create `src/mobility_model_zoo/site/motifs.py`: `resolve(reg, name) -> str | None` (1. `zoo/models/<name>/site.yaml` key `motif`, 2. `static/img/motifs/<name>.svg`; roadmap entries by entry id then name), `shown_names(reg, plan)` (published, in-progress and roadmap names the site shows), `coverage(reg, plan)` returning M1 findings, and `lint(path)` returning M2 findings (viewBox `0 0 96 96`; one group with `skewX(-8)`; `stroke-linecap="round"`; stroke widths only 4.5, 5, 8, 12 or 16; colours only `var(--text)`, `var(--border-strong)`, `var(--mark)`; exactly one element in `var(--mark)`; no `<text>`, `<image>`, gradients; ≤ 1536 bytes)
- [X] T008 Replace the three motif lookups with the resolver: `roadmap.motif_name` delegates to `motifs.resolve` in `src/mobility_model_zoo/site/roadmap.py`; `og.cards` uses `motifs.resolve(reg, sm["name"])` instead of `sm["pitch"].get("motif")` in `src/mobility_model_zoo/site/og.py`; `start.html.j2` and `partials/hero.html.j2` receive the resolved name from `build.py` (new context keys `motif` per model) and no longer compute `-hero.svg`
- [X] T009 Create `src/mobility_model_zoo/site/images.py`: `load_records(reg)` (every `zoo/site/images/<id>/image.yaml`, validated against `schemas/image-record.schema.json`; `id` equals directory name; every `checks` value `pass`; `source.sha256` and each `derivatives[w].sha256` match the files; derivative bytes ≤ 60_000 / 140_000 / 300_000 for 480 / 960 / 1600; no two records share a placement; placements name an existing topic or a shown model) → I1 findings; `load_series(reg, name)`; `check_series(records, series)` → I2 findings (prompt = subject + " " + style, negative = series negative, model in series models, `model_licence` in {Apache-2.0, MIT}); `by_placement(records)`; `resolve(records, placement, topic)` with the fallback table of [data-model.md](data-model.md) "Placement resolution" and a `warnings` list; `set_digest(records)` → `{"images": [{"id", "sha256"}]}` for `assets/images/set.json`
- [X] T010 [P] Create `src/mobility_model_zoo/site/images_process.py` (lazy imports of the `images` extra; `MissingExtra` error with the install line): `crop(img, aspect, focal)`, `encode(img, width, quality)` → WebP with XMP `Iptc4xmpExt:DigitalSourceType = http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia` plus model id and series name, re-encode down to quality 60 to meet the byte cap; `faces(png_path)` with YuNet (`cv2.FaceDetectorYN`, model `face_detection_yunet_2023mar.onnx` fetched once into `~/.cache/mobility-model-zoo/yunet/` and pinned by sha256; score ≥ 0.5 and box height ≥ 16 px rejects; also run on two 2× upscaled halves); `text(png_path)` with RapidOCR (any token confidence ≥ 0.7 with ≥ 2 alphanumerics rejects); `tool_versions()`
- [X] T011 Create `src/mobility_model_zoo/site/images_cli.py` with the Typer group `zoo site images` and register it in `src/mobility_model_zoo/site/cli.py`: `add <png> --manifest --id --placement* --focal --scene --alt --dry-run` (verify manifest entry and licence (I2), run faces/text (I4), crop and encode three derivatives, write `zoo/site/images/<id>/image.yaml` + PNG + WebPs only on success; exit codes 0/1/2), `check [--deep] [--regenerate]`, `list`, `remove <id>` per [contracts/cli.md](contracts/cli.md)
- [X] T012 [P] Add the plate component to `src/mobility_model_zoo/site/static/css/site.css`: `.plate { --bg:#111846; --surface:#111846; --text:#EEF1FF; --border-strong:#6F7DC4; --mark:#6FFFC8; background: var(--surface); border-radius: 14px; display:inline-grid; place-items:center }` with size modifiers `.plate-72` (motif 64), `.plate-48` (motif 40), `.plate-hero` (clamp 160–260 px), and update `motif()` in `src/mobility_model_zoo/site/build.py` to accept `plate: int | str | None` and wrap the SVG in `<span class="plate plate-…">`
- [X] T013 Extend `src/mobility_model_zoo/site/build.py`: load records and series (fail the build with I1/I2 findings), copy `zoo/site/images/<id>/*.webp` to `_site/assets/images/`, write `assets/images/set.json`, pass `images` (resolved per placement) and `credits` context to templates, print one warning per placement without an image, fail with M1 findings (`motifs.coverage`), and keep `--no-images` semantics for preview cards only
- [X] T014 Split S1 in `src/mobility_model_zoo/site/check.py`: `check_size` keeps HTML ≤ 150 KB per page and deferred scripts; the site total ≤ 300 KB now excludes `assets/images/` as well as fonts and `assets/og/`; register the new static checks `M1`, `M2` (motifs), `I1`, `I2`, `I3`, `C1`, `X1` (images) in `run_checks` with the ids of [contracts/checks.md](contracts/checks.md)
- [X] T015 [P] Add the browser checks to `src/mobility_model_zoo/site/a11y.py`: `S3` CLS ≤ 0.1 per page (PerformanceObserver `layout-shift`), `S4` transferred bytes per page at 390 px / DPR 2 without `.woff2` (≤ 600_000 on pages with `<img data-image>`, else ≤ 300_000, finding names the heaviest file), `M3` motif pairwise ink Jaccard distance ≥ 0.5 at 96 px on the plate, `M4` motif rendered heights (tiles ≥ 64, roadmap and mini cards ≥ 40, hero visible at 390 px), `M5` stroke contrast ≥ 3:1 against the plate in both schemes
- [X] T016 [P] Tests for the foundation: `tests/website/test_motifs_resolve.py` (site.yaml key, file fallback, roadmap id before name), `tests/website/test_motifs_lint.py` (one valid motif, one per broken rule), `tests/website/test_images_record.py` (schema, hash mismatch, byte cap, duplicate placement, unknown placement), `tests/website/test_images_series.py` (prompt/negative/model/licence mismatches), `tests/imagery/test_gen_manifest.py` (manifest shape from a fixture; render skipped without GPU)

**Checkpoint**: `uv run zoo site build --no-images` passes with no images and fails with M1 for a model without a motif; `uv run zoo site images list` prints an empty table

---

## Phase 3: User Story 2 - Every model has a prominent motif (Priority: P1) 🎯 MVP

**Goal**: every model the site shows has a distinct motif on a dark plate, large on tiles, visible in the hero at phone width

**Independent Test**: `uv run zoo site build --no-images && uv run zoo site check --only M1,M2`; then `--a11y` for M3 to M5; remove one motif and see the build fail naming the model

- [X] T017 [P] [US2] Draw eight motifs in the grammar (96 grid, `skewX(-8)`, stroke 8 round, one mint element, no text, ≤ 1.5 KB) in `src/mobility_model_zoo/site/static/img/motifs/`: `hum-bearing.svg` (bearing ring with a listening arc), `mode-cnn.svg` (three stacked mode bars), `cell-soh.svg` (battery cell with a level), `gnss-guard.svg` (satellite arc with a bracket), `jtbd-cluster.svg` (three dots joined), `rough-road.svg` (road profile), `v2x-guard.svg` (two radio arcs and a shield bracket), `picket-signal.svg` (picket fence with a signal spike); each passes `motifs.lint`
- [X] T018 [P] [US2] Add `cairn-base.svg` (stacked stones) if `motifs.shown_names` lists it, else record in `specs/016-emotional-imagery-motifs/validation.md` that it is not shown
- [X] T019 [US2] Start tiles on plates: in `src/mobility_model_zoo/site/templates/start.html.j2` replace `motif(motif_name, 40)` with `motif(sm.motif, 64, plate=72)` and adjust `.tile-name` / `.tile-top` in `site.css` so the plate leads the tile at every width
- [X] T020 [P] [US2] Roadmap and "Coming next" on plates: `motif(e.motif, 40, plate=48)` in `src/mobility_model_zoo/site/templates/roadmap.html.j2` and add the plate before `.mini-name` in `src/mobility_model_zoo/site/templates/partials/upcoming.html.j2` (context key `motif` from `roadmap.page_context`)
- [X] T021 [US2] Hero at phone width: in `src/mobility_model_zoo/site/templates/partials/hero.html.j2` render `motif(p.motif, 0, plate="hero")` and in `site.css` replace `.hero-art { display:none }` below 860 px with a stacked layout (plate centred above the headline, `clamp(160px, 40vw, 260px)`)
- [X] T022 [P] [US2] Tests: `tests/website/test_motifs_coverage.py` (every shown name resolves; build fails naming a missing one), extend `tests/website/test_start_page.py` and `tests/website/test_roadmap_page.py` for plate markup and sizes, `tests/website/test_browser.py` (slow) for M3 to M5

**Checkpoint**: every tile, roadmap entry and mini card shows a plate with a distinct motif; `zoo site check --a11y` passes M1 to M5

---

## Phase 4: User Story 1 - The start page makes mobility felt (Priority: P1)

**Goal**: the start page shows the hero image and one image per topic, text on solid surfaces, no layout shift, within budget

**Independent Test**: import the four images, `uv run zoo site build && uv run zoo site check --a11y`; open the start page at desktop and 390 px in light and dark; S1 to S4, I1 to I3 and X1 pass

- [X] T023 [US1] Copy the four chosen source PNGs from the Spark (`scp dienstollama@10.123.47.52:~/zoo-imagery/out6/qwen/start-hero-2-1021.png`, `topic-security-2-1020.png`, `topic-security-1-1011.png` and `out6/qwen-fix/topic-condition-monitoring-2-1021.png` plus both `manifest.json`) into a scratch directory, then import them with `uv run zoo site images add … --manifest … --placement start-hero|topic:productdev|topic:security|topic:condition-monitoring --focal … --scene … --alt …` using the recipes in `specs/016-emotional-imagery-motifs/selection.md`; commit `zoo/site/images/<id>/` (record, PNG, three WebPs); ids `hero-train-dawn`, `topic-productdev-workshop`, `topic-security-dashboard`, `topic-condmon-wheelset`
- [X] T024 [US1] Start hero with image: in `src/mobility_model_zoo/site/templates/start.html.j2` wrap the purpose line and calls to action in `.hero-copy` on the page surface and add `<figure class="hero-stage"><img data-image src="assets/images/<id>-960.webp" srcset="… 480w, … 960w, … 1600w" sizes="(min-width: 860px) 50vw, 100vw" width height alt fetchpriority="high" decoding="async"></figure>` from `images["start-hero"]`; layout in `site.css`: two columns from 860 px (copy left, image right), image band above the copy below 860 px; `object-fit: cover; object-position` from the focal point; fallback to the current text-only hero with no `<figure>`
- [X] T025 [US1] Topic cards with images: render `images["topic:<id>"]` as a 3:2 `<img data-image loading="lazy" decoding="async" srcset sizes width height alt>` above title, description and the topic's model plates in `start.html.j2`; card styles in `site.css`; no image when the placement is empty
- [X] T026 [P] [US1] Static checks in `src/mobility_model_zoo/site/check.py`: `I3` (every `img[data-image]` has a record, `width`, `height`, `alt` equal to the record's, `srcset`, `loading="lazy"` unless `fetchpriority="high"`; `img[data-image]` only on `index.html`, `models/*/index.html` and `credits/index.html` (FR-007); no orphan files in `assets/images/`; every WebP carries the IPTC marker, read with Pillow), `X1` (no text node inside an element positioned over an `img[data-image]`; the only allowed overlap is `.plate`)
- [X] T027 [P] [US1] Reduced motion and data saver: no transitions or transforms on `.hero-stage img` and topic images under `@media (prefers-reduced-motion: reduce)`; add `<meta name="color-scheme">` untouched; document in `docs/website.md` that images never animate
- [X] T028 [P] [US1] Tests: `tests/website/test_images_placement.py` (hero and topic markup, srcset widths, alt equals record, fallback without figure), extend `tests/website/test_start_page.py` (text not inside the figure), `tests/website/test_browser.py` (slow) for S2 on the start page, S3 and S4

**Checkpoint**: start page shows four images; `zoo site check --a11y` passes with the images in place

---

## Phase 5: User Story 3 - Model pages put the motif in front of an image stage (Priority: P2)

**Goal**: published model pages show the plate in front of the model's image (or the topic's), also at phone width

**Independent Test**: import the two model images, build, open `/models/scout-large/` and `/models/picket-forest/` at desktop and 390 px in both schemes; remove one record and see the topic fallback with a warning

- [X] T029 [US3] Import the two model images (`out6/qwen/model-scout-large-1-1011.png` → `model:scout-large`, id `model-scout-large-window`; `out6/qwen-fix/model-picket-forest-1-1011.png` → `model:picket-forest`, id `model-picket-forest-bench`) with `zoo site images add` per `selection.md`; commit the directories
- [X] T030 [US3] Image stage in `src/mobility_model_zoo/site/templates/partials/hero.html.j2`: `<figure class="stage">` with the 3:2 `<img data-image loading="lazy" …>` from `images["model:<name>"]` (fallback `topic:<topic>`) and the `.plate-hero` overlapping the lower-left corner; without any image, the plate alone; styles in `site.css` (desktop: stage right of the copy; below 860 px: stage above the headline, plate overlapping the image's bottom edge); text never inside the figure
- [X] T031 [US3] Fallback and warnings in `src/mobility_model_zoo/site/images.py` and `src/mobility_model_zoo/site/build.py`: `images.resolve` returns the topic image for a model without one and the build prints `warning: no image for model:<name>, using topic:<topic>`; a model without topic image prints `warning: no image for model:<name>, motif only`
- [X] T032 [P] [US3] Tests: `tests/website/test_images_fallback.py` (model → topic → none, warnings text), extend `tests/website/test_model_page.py` (stage markup, plate present at any width, no text in figure), `tests/website/test_browser.py` (slow) for M4 hero visibility at 390 px and S4 on model pages

**Checkpoint**: both model pages show plate and stage; fallback works without a broken image

---

## Phase 6: User Story 4 - Every image is honest about its origin and reproducible (Priority: P2)

**Goal**: credits page, four-place disclosure, compliance blocks, deep checks in CI, regeneration check, deployment approval

**Independent Test**: `/credits/` lists all six images as AI-generated with model, licence, date, hardware; footer says "Images are AI-generated"; `zoo site images check --deep` passes; `zoo compliance render && reuse lint` pass; `check --regenerate` on the Spark matches hashes

- [X] T033 [US4] Credits page: `src/mobility_model_zoo/site/templates/credits.html.j2` (one entry per record: scene, "AI-generated with <model> (<licence>) on the project's own hardware, <date>", placements as page links, licence `CC0 1.0` with deed link) rendered to `credits/index.html` in `build.py`; page title "Image credits"
- [X] T034 [US4] Disclosure in `src/mobility_model_zoo/site/templates/base.html.j2`: on pages with images a `<details class="credits">` block above the footer listing that page's images with links to their credits entries, and a footer link "Images are AI-generated · Image credits" (`credits/`); the `alt` suffix "(AI-generated image)" is enforced by the schema and I3
- [X] T035 [P] [US4] Static check `C1` in `src/mobility_model_zoo/site/check.py` (credits page exists, lists every record with all five fields, every page with `img[data-image]` links to it with the words "AI-generated")
- [X] T036 [P] [US4] Compliance templates in `src/mobility_model_zoo/compliance/templates/`: `REUSE.toml.j2` gains one `[[annotations]]` per image directory (`path = "zoo/site/images/<id>/**"`, `SPDX-FileCopyrightText = "NONE"`, `SPDX-License-Identifier = "CC0-1.0"`, comment with model and revision); `THIRD_PARTY_NOTICES.md.j2` gains the section "Website imagery" naming each generating model once with licence and model card URL; `record-of-processing.md.j2` gains the note "The website carries synthetic imagery, disclosed on /credits/, in footers, alt texts and file metadata; no personal data"; `zoo compliance render` reads the records through `images.load_records`
- [X] T037 [P] [US4] Add `.svg` to `TEXT_SUFFIXES` in `src/mobility_model_zoo/compliance/release_checks.py` so C-G2 scans motifs
- [X] T038 [US4] Deep and regenerate checks in `images_cli.py`: `check --deep` re-runs `faces` and `text` on every `source.file` (I4); `check --regenerate` renders each record with `scripts/imagery/gen.py` semantics (same model, revision, prompt, negative, seed, steps, guidance, size) and compares a 64-bit pHash with the source (≤ 4 bits differ; bit-identity reported) (I5; prints the install hint when the `images` extra or the GPU is missing)
- [X] T039 [US4] CI: in `.github/workflows/site.yml` add job `site-images` (runs on `pull_request` and `push` when `zoo/site/images/**` or `scripts/imagery/**` changed: `uv sync --extra release --extra images`, `uv run zoo site images check --deep`), and in the `deploy` job compute the digest of `_site/assets/images/set.json`, fetch the live site's `assets/images/set.json` from the Pages URL, and when they differ run the deploy step with `environment: site-images` and write the added/changed/removed images (scene, series, model, placements) to `$GITHUB_STEP_SUMMARY`; unchanged sets deploy as today
- [X] T040 [US4] Create the GitHub environment `site-images` with the owner as required reviewer: document the one-time setup in `docs/website.md` "Image approval" (repository Settings → Environments; the agent cannot create it) and add a check in `site.yml` that fails with a clear message if the environment is missing (environment `site-images` documented in docs/website.md; creating it on GitHub is the owner's one-time step)
- [X] T041 [P] [US4] Tests: `tests/website/test_credits.py` (entries, disclosure wording, footer link, per-page block), `tests/website/test_images_checks.py` (slow, needs extra: synthetic fixtures with a drawn face and with rendered text are rejected; a clean fixture passes), `tests/website/test_legal.py` extended for the REUSE and notices blocks, `tests/release/` extended if `zoo compliance render` has tests there

**Checkpoint**: credits and disclosure in place, `reuse lint` green, CI job green, deployment waits for approval only when images changed

---

## Phase 7: User Story 5 - Preview cards carry the motif as the main figure (Priority: P3)

**Goal**: preview cards show the motif centred and fully opaque; optional image backdrop only when O2/O3 pass

**Independent Test**: `uv run zoo site build && uv run zoo site check --only O1,O2,O3,O4,O5`; every model card shows its motif centred; picket-forest has one

- [X] T042 [US5] Centre the motif in `src/mobility_model_zoo/site/templates/og/card.html.j2` and `src/mobility_model_zoo/site/static/css/og.css`: one `.og-motif` on a `.plate` inside the centre safe area (x 285–915), opacity 1, size 200 px; remove the two corner copies
- [X] T043 [US5] Optional backdrop in `src/mobility_model_zoo/site/og.py`: when `images["model:<name>"]` (else topic) exists, render the card with the 1600 px WebP as a dimmed backdrop (`opacity .35`) and keep it only if `check_og_layout` (O2) and the contrast check (O3) pass for that card; otherwise render without the backdrop; record the decision in `_build/og.json`
- [X] T044 [P] [US5] Tests: `tests/website/test_og_motif.py` (motif via resolver, centred, picket-forest card has it), extend `tests/website/test_og_checks.py` for the backdrop guard

**Checkpoint**: cards pass O1 to O5 with centred motifs

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T045 [P] Update `docs/website.md`: imagery section (house style SIEBDRUCK, series file, generator on the Spark, import command, checks I1 to I5, credits and disclosure, approval environment), motif rules (grammar, plate, sizes, M1 to M5), revised weight budgets (S1, S3, S4)
- [X] T046 [P] Update `specs/008-zoo-website/contracts/checks.md`: note the S1 split and the new S3/S4, and mark the "no stock photos" rule as superseded by feature 016 for generated illustrated images
- [X] T047 [P] Record the visual identity additions (FR-030) in `specs/008-zoo-website/design/README.md` or, if absent, create `docs/identity.md`: palette use in images, accent-on-vehicle rule, plate component, motif-on-stage composition, series recipe (recorded in docs/website.md "Imagery and motifs" and "Identity")
- [X] T048 [P] Add the `images` area and the `site-images` job to `specs/016-emotional-imagery-motifs/validation.md` together with the measured S2/S3/S4 values of the first full build and the list of shown names covered by M1
- [X] T049 Run the full [quickstart.md](quickstart.md) (steps 1 to 7) on a clean checkout, fix anything that fails, and record the results in `specs/016-emotional-imagery-motifs/validation.md` (steps 1 to 4, 6 and 7 run; step 5 `--regenerate` needs the GPU container, see validation.md)
- [X] T050 Prepare the user test for SC-001 and SC-003 (five people, five-second impression, motif matching) as a short script in `specs/016-emotional-imagery-motifs/validation.md`; execution waits for the owner (can share the session with the 008 SC-001 test) (script in validation.md; execution waits for the owner)
- [X] T051 Update `.claude/worktrees` memory note and the feature status: feature 016 implemented, images live after approval; list open items (user test, cairn-base motif if not shown)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies; T002 to T006 in parallel
- **Foundational (Phase 2)**: depends on Setup; T007 → T008; T009 → T011, T013; T010 independent; T012, T015, T016 in parallel; blocks every story
- **US2 (Phase 3)**: depends on Phase 2 (T007, T008, T012); independent of US1
- **US1 (Phase 4)**: depends on Phase 2 (T009 to T014); independent of US2 (the topic cards show plates, but render without them)
- **US3 (Phase 5)**: depends on US1 (image markup, import) and US2 (plate)
- **US4 (Phase 6)**: depends on US1 (records exist); T036/T037 can start after Phase 2
- **US5 (Phase 7)**: depends on US2 (resolver, plate) and, for the backdrop, US1
- **Polish (Phase 8)**: after all stories; T045 to T048 in parallel

### User Story Dependencies

- US2 (P1): foundation only → MVP
- US1 (P1): foundation only
- US3 (P2): US1 + US2
- US4 (P2): US1
- US5 (P3): US2 (+ US1 for the backdrop)

### Within Each Story

- Content (motifs, imports) before templates; templates before checks; checks before tests
- Tests marked [P] can be written while the previous task is in review

### Parallel Opportunities

- Phase 1: T002, T003, T004, T005, T006
- Phase 2: T010, T012, T015, T016 beside the T007 → T008 and T009 → T011 → T013 chains
- US2: T017, T018, T020, T022 while T019 and T021 are done in order
- US1: T026, T027, T028 after T023 to T025
- US4: T035, T036, T037, T041 beside T033 → T034 and T038 → T039 → T040
- Across stories: US1 and US2 can be worked on in parallel by two agents after Phase 2

---

## Parallel Example: User Story 2

```bash
# After Phase 2, in parallel:
Task T017: draw eight motifs in src/mobility_model_zoo/site/static/img/motifs/
Task T020: plates on roadmap.html.j2 and partials/upcoming.html.j2
Task T022: tests/website/test_motifs_coverage.py
# Then in order:
Task T019: start tiles on plates
Task T021: hero motif at phone width
```

## Parallel Example: User Story 1

```bash
# After T023 (import) and T024/T025 (templates), in parallel:
Task T026: checks I3 and X1 in check.py
Task T027: reduced-motion rules in site.css
Task T028: tests/website/test_images_placement.py
```

---

## Implementation Strategy

### MVP First (User Story 2)

1. Phase 1 and Phase 2
2. Phase 3 (US2): eight motifs, plates, hero at phone width
3. **STOP and validate**: build, `zoo site check --a11y`, look at the start page in both schemes (this is where the owner sees the dark plate in light mode, research R9)
4. Preview build for the owner

### Incremental Delivery

1. US2 → visible change, no images yet
2. US1 → start page with four images → preview for the owner
3. US3 → model pages → preview
4. US4 → credits, compliance, CI, approval environment → first deployment that asks for approval
5. US5 → preview cards
6. Polish → docs, validation, user test script

### Notes

- The source PNGs live on the Spark; copy them before T023 and T029 and never commit anything but the record directories.
- `zoo site build` and `check` must never import the `images` extra; only `zoo site images add|check --deep|--regenerate` do.
- The owner's only manual step is the `site-images` environment approval (FR-017); do not add review steps elsewhere.
- Commit after each phase checkpoint; keep `zoo site check --a11y` green at every commit.
