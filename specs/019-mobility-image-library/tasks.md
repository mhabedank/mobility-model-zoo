# Tasks: Mobility image library in the house style

**Input**: Design documents from `/specs/019-mobility-image-library/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [subjects.md](subjects.md), [quickstart.md](quickstart.md)

**Tests**: pytest tasks are included where the plan names a test file; they are written alongside the code, not TDD-first. Browser checks run through `zoo site check --a11y`. Calibration and the rendering rounds are recorded steps, not unit tests.

**Organization**: Tasks are grouped by user story. US2 (triage, sheet, picks) is the tooling US1 (the library itself) is built with, so US2 comes first although both are P1. US3 and US4 build on the records and are independent of each other.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1 to US4)
- Include exact file paths in descriptions

## Path Conventions

Single project: package in `src/mobility_model_zoo/`, content in `zoo/`, tests in `tests/`, generator in `scripts/imagery/`. The DGX Spark is `dienstollama@10.123.47.52` over the VPN; rendering happens in the `zoo-flux` container with the work directory `~/zoo-imagery/` (016 README). Round directories: `~/zoo-imagery/rounds/<n>/` on both machines. The 016 renders for calibration are under `~/zoo-imagery/out6/` on the Spark; the rejected night-and-rain and photoreal renders under the earlier `~/zoo-imagery/out*/` directories (identify them by the series name in each `manifest.json`).

---

## Phase 1: Setup (schema, series, constants)

**Purpose**: the data changes every story depends on

- [X] T001 Copy `specs/019-mobility-image-library/contracts/image-record.schema.json` over `src/mobility_model_zoo/site/schemas/image-record.schema.json` (adds `theme` enum of the ten themes, `subject` slug `^[a-z0-9]+(-[a-z0-9]+)*$` max 40, optional `round` ≥ 1, `placements` without `minItems`, `source.file` optional while `width`, `height`, `sha256` stay required, `checks.style`, `checks.duplicate` const `pass`, required `checks.measures` with `phash` as 16 hex characters and optional `other_share`, `accent_share`, `accent_largest_share`, `accent_top_share`, `accent_centroid`; the `allOf` keeps only "start-hero requires 16:9")
- [X] T002 Add to `src/mobility_model_zoo/site/images.py` the constants `THEMES` (ordered: rail, public-road, private-road, active, water, air, infrastructure, workshop, iot, ai), `THEME_MINIMUMS` ({rail: 10, public-road: 6, private-road: 8, active: 6, water: 5, air: 4, infrastructure: 14, workshop: 8, iot: 10, ai: 10}), `THEME_CAP = 0.20`, `LIBRARY_MIN = 100`, `LIBRARY_MAX_BYTES = 40_000_000`, `SOURCES_CACHE = ".cache/site/sources"`
- [X] T003 Migrate `zoo/site/images/series/siebdruck.yaml` per [data-model.md](data-model.md) "Series": replace `subjects` by `themes` (map theme id → list of `{id, prompt, aspect?, scene, alt, reserve?}`) with every subject of [subjects.md](subjects.md) including the six 016 prompts under their ids (`rail/regional-dawn` 16:9, `rail/tram-interior`, `rail/wheelset-hall`, `rail/train-window-notebook`, `private-road/workshop-bay`, `workshop/circuit-bench`); write `scene` (20 to 120 characters) and `alt` (one sentence, 40 to 160 characters after the suffix "(AI-generated image)") for every subject; add `negative_history: [<the current negative text verbatim>]` and extend `negative` with `brain, glowing network, hologram, floating icons, circuit pattern`; add `duplicate_max_bits: 10` and a `palette` block with placeholder anchors (filled by T025) and thresholds `tolerance_de: 18`, `other_max: 0.12`, `accent_min: 0.015`, `accent_max: 0.30`, `largest_min: 0.50`, `top_max: 0.15`
- [X] T004 [P] Extend the fixture helper `make_record` in `tests/website/test_images_record.py` with `theme="rail"`, `subject="regional-dawn"`, `checks.style`/`checks.duplicate` `pass` and `checks.measures.phash`, and an option `source_file=False` that omits `source.file`; update `tests/website/site_fixture.py`'s frozen series file (if it copies one) to the `themes` layout so the existing 016 tests keep passing

---

## Phase 2: Foundational (records, I2, I6, I7, I8, generator)

**Purpose**: validation and measurement every story needs; nothing here is visible on the site

- [X] T005 Change `load_records` in `src/mobility_model_zoo/site/images.py`: verify `source.file` only when present (I1 "source … is missing / does not match" findings only then); accept empty `placements`; keep the aspect check for `start-hero` only
- [X] T006 Change `load_series` and `series_findings` (I2) in `src/mobility_model_zoo/site/images.py`: flatten `themes[*][*].prompt` as the subject list (keep reading a legacy `subjects` map so old fixtures do not break), accept `negative_prompt` equal to the series' `negative` or any entry of `negative_history`, and add I8 findings "I8 <id>: theme/subject <t>/<s> is not in series <name>" and "I8 <id>: subject <t>/<s> is also used by <other id>"
- [X] T007 [P] Add `library_findings(records)` to `src/mobility_model_zoo/site/images.py`: L1 (sum of `derivatives[*].bytes` over all records ≤ `LIBRARY_MAX_BYTES`, finding names the three heaviest ids), I7 over records (pairwise Hamming distance of `checks.measures.phash` ≤ the series' `duplicate_max_bits` → "I7 <a>: near-duplicate of <b> (<n> bits)"), and `coverage(records)` returning per theme `{count, minimum, share}` plus `coverage_findings(records)` for L2 (under minimum, over cap, total under `LIBRARY_MIN`)
- [X] T008 [P] Add `style(png_or_webp: Path, palette: dict) -> dict` to `src/mobility_model_zoo/site/images_process.py` (I6, research R4): resize to 240 px long side, convert to CIELAB with OpenCV, assign each pixel to the nearest anchor of `palette.anchors` (navy, mint, cream, accent) within `tolerance_de` else `other`; compute `other_share`, `accent_share`, `accent_largest_share` (largest 8-connected accent component via `cv2.connectedComponentsWithStats`), `accent_top_share` (accent pixels in the top fifth; waived when the largest component's bounding box reaches into the top fifth), `accent_centroid` (of the largest component, clamped to 0.2–0.8); return `{pass, reasons: [...], measures: {...}}` with one reason per failed rule naming the rule and the measured value; add `phash_hex(path)` (16 hex chars) and `duplicate_of(phash, others: dict[str,int], max_bits) -> (id, bits) | None`
- [X] T009 [P] Add `measure_anchors(paths) -> dict` to `src/mobility_model_zoo/site/images_process.py`: k-means (k=4, OpenCV) over the Lab pixels of the given images, map the four cluster centres to navy, mint, cream, accent by L and hue, print the anchors as YAML for the series file (used once in T025)
- [X] T010 [P] Change `scripts/imagery/gen.py` per [contracts/cli.md](contracts/cli.md) "Generator": render from `series["themes"]`; file name `<theme>--<subject>--<seed>.png`; seed `= seed_base + (97 * zlib.crc32(f"{theme}/{subject}".encode())) % 1_000_000 + s`; options `--seed-base` (default 0), `--only theme[/subject],...`, `--reserve`; read `next.txt` in `--out` as the subject list when `--only` is absent; aspect from the subject (`SIZES`); manifest entry gains `theme`, `subject`, `seed_base`, `aspect`; keep resumability
- [X] T011 [P] Extend `tests/imagery/test_gen_manifest.py`: a two-theme series renders the expected file names, seeds differ between subjects and are stable across runs, `--only rail/high-speed-viaduct` and `next.txt` select subjects, manifest entries carry `theme`, `subject`, `seed_base`, `aspect` (render stubbed as in the existing test)
- [X] T012 [P] Add `tests/website/test_images_style.py` (slow, needs the extra): synthetic flat scenes via Pillow with the palette's anchor colours: an in-palette scene with one orange rectangle passes and reports a centroid inside the rectangle; an orange sky band fails `top`; two scattered orange patches of equal size fail `largest`; a grey-green scene fails `other`; a scene without accent fails `accent_min`; `phash_hex` is 16 hex chars and `duplicate_of` finds a twin at 0 bits and none at 20
- [X] T013 Extend `tests/website/test_images_record.py` and `tests/website/test_images_series.py`: a record without `source.file` loads; a record with a missing `theme` or `subject` is I1; an unknown `theme/subject` is I8; two records on one subject are I8; a negative prompt from `negative_history` passes I2; `library_findings` reports L1 above 40 MB (fake `bytes`), I7 for two records with equal `phash`, and `coverage_findings` names a theme under its minimum and a total under 100
- [X] T014 Run `uv run pytest tests/website tests/imagery -q` and `uv run ruff check src tests scripts`; fix until green (the six 016 records still fail I1 here because they lack `theme`, `subject`, `checks.style`, `checks.duplicate`, `checks.measures`; that is T026)

**Checkpoint**: records, series and measurements validate; the generator renders from themes

---

## Phase 3: User Story 2 — The owner picks every image from a clean contact sheet (Priority: P1)

**Goal**: `triage` rejects failing candidates with reasons and writes a numbered sheet of the rest; `pick` imports the owner's numbers as pool records and writes `next.txt`.

**Independent Test**: run `triage` on a synthetic round (fixtures from T012 plus a manifest), open `sheet.html`, pick by number, run `pick`, check records and `next.txt` (quickstart steps 3 and 4 on synthetic data).

- [X] T015 [P] [US2] Create `src/mobility_model_zoo/site/images_triage.py`: `triage_round(reg, round_dir, round_no) -> dict` that reads `manifest.json`, and per candidate in manifest order runs I4 faces, I4 text, I6 style (series palette), I7 duplicate (against `checks.measures.phash` of every library record and every earlier `shown` candidate of the round) and I1 bytes (encode the three derivatives with `images_process.derivatives` into `<round_dir>/thumbs/<file stem>-<w>.webp`), stopping at the first failure; outcome `shown` with a 1-based `number` within the subject or `rejected` with `reasons: [{check, detail}]`; records `measures`, `phash`, `focal_default`; writes `triage.json` per [data-model.md](data-model.md) "Rendering round" with `round`, `container` (manifest generator image digest), `generator`, `tools`, `ran`; returns the summary (candidates, shown, rejected per check, subjects without a shown candidate)
- [X] T016 [P] [US2] Create `src/mobility_model_zoo/site/templates/local/sheet.html.j2` (static, no scripts, inline CSS, dark background): "needs another round" list first (subject, rejection reasons by seed), then themes in `THEMES` order, subjects in series order, each shown candidate as `thumbs/<stem>-480.webp` linking to the PNG, with `#<number>`, seed and a `title` holding the I6 measures; rejected candidates of a subject in one collapsed `<details>` line "rejected: seed (check detail)…"
- [X] T017 [US2] Add `write_sheet(round_dir, triage, series)` to `src/mobility_model_zoo/site/images_triage.py` rendering T016 to `<round_dir>/sheet.html`, and the command `triage <round-dir> [--round N]` to `src/mobility_model_zoo/site/images_cli.py` per [contracts/cli.md](contracts/cli.md) (exit 2 without manifest or extra; prints the summary)
- [X] T018 [US2] Add `pick_round(reg, round_dir, picks, dry_run)` to `src/mobility_model_zoo/site/images_triage.py` and the command `pick <round-dir> [--picks picks.yaml] [--dry-run]` to `images_cli.py`: validate every numbered pick is a `shown` candidate (exit 2 otherwise); for each pick build the record as `add` does (re-run I4, I6, I7 and the schema; `theme`, `subject`, `round`, `placements: []`, `scene` and `alt` from the series subject with the suffix, `focal_point` from the pick's `focal` else `focal_default`, derivatives from `thumbs/` when their sha256 equals a re-encode else re-encoded, `source` without `file`, `checks.style`/`duplicate` `pass`, `checks.measures` incl. `phash`); id `<theme>-<subject>` truncated to 40 with a numeric suffix on collision, or the pick's `id`; refuse the whole import on any failure (nothing written); write `next.txt` with `none` picks and subjects without a shown candidate; refactor the record-building part of `add_cmd` into a shared helper `build_record(...)` used by both
- [X] T019 [US2] Change `add_cmd` in `src/mobility_model_zoo/site/images_cli.py`: options `--theme` and `--subject` (required), `--no-source` (omit the PNG and `source.file`), `--placement` optional (default none); run I6 and I7 and write `checks.style`, `checks.duplicate`, `checks.measures`
- [X] T020 [P] [US2] Add `tests/website/test_images_triage.py` (slow): a synthetic round of three subjects with four seeds each (T012 fixtures with variations; one with text "ROUTE 400", one orange-sky, two identical) → outcomes as expected, numbers 1..n per subject among shown, the twin names its earlier number, `triage.json` fields, `sheet.html` contains the numbers and the "needs another round" subject, and the summary counts
- [X] T021 [P] [US2] Add `tests/website/test_images_pick.py` (slow): `picks.yaml` with one number per subject, one `none` and one `focal` override → records exist with three derivatives and no PNG, `placements == []`, scene and alt from the series, focal from the override; `next.txt` lists the `none` subject; a pick naming a rejected number exits 2 and writes nothing; a dry run writes nothing
- [X] T022 [US2] Run `uv run pytest tests/website -q -m slow -k "triage or pick or style"` and the fast suite; fix until green

**Checkpoint**: a round can be triaged, shown, picked and imported on synthetic data

---

## Phase 4: User Story 1 — A broad, consistent library exists (Priority: P1)

**Goal**: at least 100 records across the ten themes, every one passing the checks, the six 016 records migrated.

**Independent Test**: `uv run zoo site images check --deep --require-coverage` passes (quickstart step 6); `zoo site images list` shows ≥ 100 records with themes.

- [X] T023 [US1] On the Spark: `scp` the migrated `zoo/site/images/series/siebdruck.yaml` and `scripts/imagery/gen.py` to `~/zoo-imagery/`; confirm the `zoo-flux` image digest and the model cache are present (016 README); record the digest in `specs/019-mobility-image-library/rounds/README.md`
- [X] T024 [US1] Build the calibration round on the developer machine: `rsync` `~/zoo-imagery/out6/` (016 renders, 60 PNGs with manifest) and the rejected night-and-rain and photoreal renders from the Spark into `~/zoo-imagery/calib/`; write one `manifest.json` that wraps them with `theme: calib`, `subject: <series>-<n>` (a small script in `scripts/imagery/wrap_manifest.py`, committed)
- [X] T025 [US1] Calibrate I6 and I7 (research R4, R5, quickstart step 1): run `measure_anchors` (T009) over the six PNGs under `zoo/site/images/*/` and write the anchors into `palette.anchors` of `zoo/site/images/series/siebdruck.yaml`; run `uv run zoo site images triage ~/zoo-imagery/calib --round 0`; adjust `palette` thresholds and `duplicate_max_bits` until the six owner-approved images are `shown`, every render of the owner-rejected series is `rejected` by I6, and I7 rejects at most one in twenty between seeds of one subject (the share of the agent's 016 shortlist that stays `shown` is recorded as information only, not as a target); apply the kill criteria if no setting works; record the final thresholds, the counts and any kill outcome in `specs/019-mobility-image-library/validation.md` and commit `triage.json` to `specs/019-mobility-image-library/rounds/0/`
- [X] T026 [US1] Migrate the six 016 records `zoo/site/images/{hero-train-dawn,topic-productdev-interior,topic-security-workshop,topic-condmon-wheelset,model-scout-large-window,model-picket-forest-bench}/image.yaml`: add `theme` and `subject` (rail/regional-dawn, rail/tram-interior, private-road/workshop-bay, rail/wheelset-hall, rail/train-window-notebook, workshop/circuit-bench), run I6 and I7 on their sources and add `checks.style: pass`, `checks.duplicate: pass`, `checks.measures` (incl. `phash`); delete the six source PNGs from the tree and drop `source.file` (FR-015; the sources stay in git history and on the Spark); then `uv run zoo site images check` passes (I1, I2, I7, I8, L1)
- [X] T027 [US1] Draft pass on the Spark (quickstart step 2): `python /work/gen.py --series /work/siebdruck.yaml --model draft --seeds 2 --out /work/rounds/draft`; copy the drafts down; review every subject for misread prompts (toy vehicles, wrong objects, clichés); rewrite the affected prompts in `siebdruck.yaml` and `subjects.md`; re-draft only those with `--only`; note the rewrites in `validation.md`
- [X] T028 [US1] Final pass round 1 on the Spark: `python /work/gen.py --series /work/siebdruck.yaml --model final --seeds 4 --out /work/rounds/1` as a detached chain script (016 pattern: script file, `nohup`, log in `~/zoo-imagery/rounds/1/render.log`); about 22 hours; check progress with `grep -c png render.log`
- [X] T029 [US1] `rsync` `~/zoo-imagery/rounds/1/` to the developer machine; `uv run zoo site images triage ~/zoo-imagery/rounds/1 --round 1`; report the summary to the owner and hand over `sheet.html`
- [X] T030 [US1] Collect the owner's picks (numbers per `theme/subject`, `none`, optional focal) into `~/zoo-imagery/rounds/1/picks.yaml`; `uv run zoo site images pick ~/zoo-imagery/rounds/1 --dry-run` then without; copy `manifest.json`, `triage.json`, `picks.yaml`, `next.txt` to `specs/019-mobility-image-library/rounds/1/`
- [X] T031 [US1] (round 2 done; round 3 declined by the owner on 2026-10-16, pool closes at 91 records, see validation.md §4) Round 2 (and 3 if needed): `scp next.txt` to `~/zoo-imagery/rounds/<n>/`, render with `--seed-base 1000` (then 2000), including `--reserve` when a theme is under its minimum; triage, sheet, picks, import as in T029–T030; repeat until `uv run zoo site images check --require-coverage` passes (≥ 100 records, every theme at its minimum, none over 20%)
- [X] T032 [US1] Run `uv run zoo site images check --deep` over the whole pool and `du -sh zoo/site/images`; record counts per theme, total bytes and the check output in `specs/019-mobility-image-library/validation.md` (SC-001, SC-002, SC-005)

**Checkpoint**: the pool exists, validated, with its audit trail under `rounds/`

---

## Phase 5: User Story 3 — Library images are placed from the pool (Priority: P2)

**Goal**: unplaced records never enter the build; placed ones work as in 016; the owner has a pool overview.

**Independent Test**: quickstart steps 6 and 7: `_site/assets/images/` holds only placed derivatives; a placement change puts a pool image on a model page.

- [X] T033 [US3] Change `src/mobility_model_zoo/site/build.py`: `placed = [r for r in records if r["placements"]]`; `asset_files`, `set_digest`, `credits`, `page_images` and `thumbs` use `placed` only; `load_records` + `series_findings` + `library_findings` (T007) run over all records as build failures; no warning for unplaced records
- [X] T034 [P] [US3] Change `check_image_markup` (I3) in `src/mobility_model_zoo/site/check.py`: every file in `assets/images/` belongs to a record **with a placement**; a derivative of an unplaced record in the build is a finding "I3 <file>: image of unplaced record <id> is in the build"; register `library_findings` (I7, I8, L1) in `run_checks`
- [X] T035 [P] [US3] Change `credits` in `src/mobility_model_zoo/site/images.py` so entries are built only for records with placements (C1 unchanged otherwise), and `check_credits` in `check.py` compares against placed records
- [X] T036 [P] [US3] Create `src/mobility_model_zoo/site/templates/local/pool.html.j2` (static, no scripts): themes in `THEMES` order with "n of minimum m, cap c" and a mark when under or over; each record as its 480 px derivative via a relative `file` link into `zoo/site/images/<id>/`, with id, subject, aspect, placements, round
- [X] T037 [US3] Add `write_overview(reg, out)` to `src/mobility_model_zoo/site/images_triage.py` and the command `overview [--out PATH]` (default `.cache/site/pool.html`) to `images_cli.py`; extend `list_cmd` with theme and subject columns and `--theme`
- [X] T038 [P] [US3] Extend `tests/website/test_images_placement.py`: a build with one placed and one unplaced record copies three files for the placed one only, `set.json` lists the placed id only, credits list the placed one only, no warning mentions the unplaced id; moving the placement to the other record swaps files, credit and digest
- [X] T039 [P] [US3] Add `tests/website/test_images_overview.py`: two themes with records → grouping, counts against minimum and cap, relative links resolve to existing files; `list --theme rail` filters
- [X] T040 [US3] Run `uv run zoo site build && uv run zoo site check --a11y` on the full pool: `ls _site/assets/images | wc -l` equals 3 × placed + 1; every check passes; `uv run pytest tests/website -q` green

**Checkpoint**: the site is unchanged except for placements; the pool is browsable locally

---

## Phase 6: User Story 4 — The library stays reproducible and light (Priority: P2)

**Goal**: deep and regeneration checks work without sources; weight and provenance are enforced and documented.

**Independent Test**: quickstart steps 6 and 8: `check --deep` runs over all records; `--regenerate` on three records gives pHash ≤ 4; L1 holds.

- [X] T041 [P] [US4] Change `check_cmd` in `src/mobility_model_zoo/site/images_cli.py`: `--deep` uses `source.file` next to the record if present, else `.cache/site/sources/<id>.png` if present, else the 1600 px derivative, and says which in the I4 line; `--regenerate` compares against the same choice; add `--require-coverage` (L2 via `coverage_findings`) and print the coverage report always
- [X] T042 [P] [US4] Extend `tests/website/test_images_checks.py`: `faces` and `text` accept a WebP; a record without `source.file` is deep-checked on its 1600 px derivative (patch the detectors, assert the path used)
- [X] T043 [US4] (done with a recipe dump and `regen.py` in the container, not `--regenerate`: the package is not installed there; three records bit-identical) On the Spark, in the container: `uv run zoo site images check --regenerate` restricted to three records chosen at random (add `--only <id>,...` to `check_cmd` for this) → pHash distance ≤ 4 each; record ids, revisions, distances and whether bit-identical in `specs/019-mobility-image-library/validation.md` (SC-006)
- [ ] T044 [P] [US4] (pool growth measured: +11.2 MB on a 13.9 MiB pack; the clone timing waits for the push, see validation.md §5) Measure SC-005: `git count-objects -vH` before and after the pool commits and a timed fresh `git clone` of the branch versus `main`; record both in `validation.md` (≤ 25% slower, ≤ 40 MB)
- [X] T045 [P] [US4] `.github/workflows/site.yml`: timeout kept at 20 minutes (the deep check on 1600 px derivatives takes about 1 s per record); the approval summary now lists placed records only (pool records are not part of the site)
- [X] T046 [US4] Run `uv run zoo compliance render` and `uv run reuse lint`: one `CC0-1.0` annotation per record directory (placed or not), the "Website imagery" notices section unchanged in shape, the record of processing note unchanged; commit the rendered files

**Checkpoint**: provenance, reproducibility and weight are checked and recorded

---

## Phase 7: Polish & Cross-Cutting

- [X] T047 [P] Update `docs/website.md` "Imagery and motifs": add a subsection "Image library (feature 019)" with the themes and minimums, the round workflow (draft pass, final pass, `rsync`, `triage`, sheet, picks, `pick`, `next.txt`), the pool rule (unplaced records are not built, not credited, do not trigger approval), `overview`, how to place an image, and that library records carry no source PNG
- [X] T048 [P] Update `scripts/imagery/README.md` with the rounds workflow and the new generator options (`--seed-base`, `--only theme/subject`, `--reserve`, `next.txt`), and the triage/pick commands on the developer machine
- [X] T049 [P] Add a note to `specs/016-emotional-imagery-motifs/contracts/checks.md` that feature 019 changes I1 to I5 and C1 (link to [contracts/checks.md](contracts/checks.md)) and to `specs/016-emotional-imagery-motifs/data-model.md` that `source.file` is optional since 019
- [X] T050 [P] Add `specs/019-mobility-image-library/rounds/README.md` describing the audit trail files and the container digest, and a `validation.md` section template for SC-003 (blind test with five people: ten images from at least five themes; "one series?" and "what is it about?")
- [X] T051 Full run: `uv run ruff check src tests scripts && uv run ruff format --check src tests scripts`, `uv run pytest tests/website tests/imagery -q` (fast) and `-m slow` (needs the extra and Chromium), `uv run zoo site build && uv run zoo site check --a11y`, `uv run zoo site images check --deep --require-coverage`; fix until green
- [X] T052 Update the memory file `~/.claude/projects/-Users-m-habedank-Projects-private-mobility-llm/memory/project-image-library-019-status.md` with the final counts, the rounds, the calibration outcome and the owner steps left (blind test, first deployment approval after the migration of the six records)

---

## Dependencies & Execution Order

- **Phase 1 → Phase 2 → Phase 3 (US2) → Phase 4 (US1)**: strictly sequential; US1 needs US2's tooling and the calibration (T025) before any final render (research R11).
- **Phase 5 (US3) and Phase 6 (US4)**: both need Phase 4's records for their full tests, but their code tasks (T033–T037, T041–T042) can be written in parallel with Phase 4's long render (T028) on synthetic data.
- **Phase 7**: after everything.

Within Phase 4 the order is fixed: T023 → T024 → T025 (calibration, kill criteria) → T026 (migration) → T027 (drafts) → T028 (final render, ~22 h unattended) → T029 → T030 → T031 (further rounds) → T032.

## Parallel Execution Examples

- Phase 2: T007, T008, T009, T010, T011, T012 touch different files and can run together after T005/T006.
- Phase 3: T015 and T016 together; T020 and T021 together after T018.
- During T028 (the 22-hour render): T033–T039 (US3) and T041–T042, T045 (US4) on synthetic fixtures.
- Phase 7: T047–T050 together.

## Implementation Strategy

1. **MVP = Phases 1–4**: the pool exists and validates; nothing on the site changes yet (unplaced records are ignored by the build only after T033, so until then `build` must not be run against the full pool in CI: keep the pool import on the branch until T033 lands, or do T033 before T030).
2. **Order to avoid the CI trap** (analysis finding O1): T033–T035 (placed-only build) are executed right after Phase 2, before Phase 3, so no build ever ships unplaced records. They keep their US3 ids for traceability.
3. **Increment 2 = US3 rest + US4**: overview, deep fallbacks, measurements.
4. **Increment 3 = Polish**: docs, notes, full run, memory.
