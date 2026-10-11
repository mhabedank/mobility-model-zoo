---

description: "Tasks for feature 013: quickstart that works from a fresh install"
---

# Tasks: Quickstart that works from a fresh install

**Input**: Design documents from `/specs/013-fresh-install-quickstart/`

**Prerequisites**: plan.md, spec.md, research.md (R1–R10), data-model.md, contracts/ (dependency-layout, picket-forest-api, model-repo-files, gate-and-card), quickstart.md

**Tests**: included; the spec requires them (FR-004 parity, FR-011 replayed failures, SC-003, SC-006).

**Organization**: by user story. US1 is the MVP (picket-forest runs from its card alone); US2 makes it durable (the gate); US3, US4 polish the path; US5 ships it.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependencies)
- **[Story]**: US1–US5 as in spec.md
- Paths are repository-relative; single package under `src/mobility_model_zoo/`.

---

## Phase 1: Setup (dependency layout, R1)

**Purpose**: the small base and the extras every later task installs against.

- [X] T001 In `pyproject.toml` reduce `dependencies` to `huggingface_hub>=1.19` and `numpy>=1.26`; add extra `text = ["torch>=2.4", "transformers>=4.46", "safetensors>=0.4", "sentencepiece>=0.2"]`; add `"mobility-model-zoo[text]"` as first entry of `jtbd`; add `"scikit-learn>=1.5"` and `"joblib>=1.3"` to `edge`; keep every other extra unchanged (contracts/dependency-layout.md)
- [X] T002 Regenerate `uv.lock` with `uv lock` and confirm `uv sync --extra jtbd --extra release --extra edge --extra catalog --no-install-package torch` (the ci.yml line) and `uv sync --extra edge --no-install-package torch` both succeed
- [X] T003 [P] Update `README.md` section "Setup" so the sync line names `--extra text` where the text stack is needed and says what each extra is for (base, text, edge, jtbd, release)

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: schema and card plumbing that US1, US2 and US4 all build on.

- [X] T004 Confirm the Python-requirement change already in the working tree is complete: `python_requirement()` in `src/mobility_model_zoo/release/card.py`, "Requires {{ python_requirement }}." in `src/mobility_model_zoo/release/templates/model_card.md.j2`, `python_requirement` in `src/mobility_model_zoo/site/build.py` and `src/mobility_model_zoo/site/templates/partials/quickstart.html.j2`, golden files under `tests/release/fixtures/golden/`; run `uv run pytest tests/release tests/website -q`
- [X] T005 [P] Add optional string `card.own_data` to `src/mobility_model_zoo/release/schemas/model.schema.json` (and the copy in `specs/005-topic-layout-security-merge/contracts/model.schema.json` if the tests load it) with a description: "snippet that uses the model on the user's own data; shown, not executed by the gate"
- [X] T006 [P] In `src/mobility_model_zoo/release/card.py` add `how_to_run_output: str | None = None` to `CardInput`, pass `how_to_run_output` and `own_data = fill(m["card"].get("own_data", ""), repo, f"v{version}", "").strip()` to the template; in `model_card.md.j2` add, after the python block and only when `mcu and how_to_run_output`, "Output:" with a ```text block, and after the device block when `own_data`, "### Use it on your own vehicle" with a ```python block (contracts/gate-and-card.md)
- [X] T007 Write the test helper `tests/security/can_ids/picket_fixtures.py` with `example_paths()` (the three registry JSONs), `load_release_model()` (downloads `model.joblib` of `mobility-model-zoo/picket-forest@v0.2.0` into the pytest cache via `hf_hub_download`, skips without network) and `header_table(path) -> list[tuple]` (parses `picket_forest_table.h` rows `{0x..., p, w, m, d}`)

**Checkpoint**: schema, card slots and fixtures exist; the extras resolve.

---

## Phase 3: User Story 1 — Run picket-forest from its card alone (Priority: P1) 🎯 MVP

**Goal**: a complete, compiler-free, repository-free Python path from `model.joblib` + `calibration_table.json` + `examples/01-fabrication.json` to printed scores and alarms, bit-exact with the device.

**Independent Test**: `uv run pytest tests/security/can_ids/test_picket_forest_reference.py -q` passes without a compiler (examples reproduce `expected_scores` and `expected_alarms`); in a fresh `[edge]` venv the card snippet runs against the staging repository.

### Tests for User Story 1

- [X] T008 [P] [US1] Create `tests/security/can_ids/test_picket_forest_reference.py` with `test_module_imports_are_user_safe` (AST of `src/mobility_model_zoo/security/can_ids/picket_forest.py`: third-party imports ⊆ {numpy, joblib, sklearn}; never `mobility_model_zoo.edge`, `ctypes`, `subprocess`, `pandas`, `release_export_v2`, `forest`, `calibrated`)
- [X] T009 [P] [US1] In the same file add `test_examples_reproduce_expected_scores_and_alarms`: for each example JSON, `pf.score(pf.load_capture(p), table, model)` where `table = rx.example_table()` serialised through `save_table`/`load_table` and `model = load_release_model()`; assert `scores.view(np.uint32)` as 8-hex strings `== expected_scores` and `np.flatnonzero(alarms).tolist() == expected_alarms` (skip without network)
- [X] T010 [P] [US1] Add `test_table_roundtrip_and_header_equivalence`: `load_table(save_table(t))` equals `t` field by field (`period`, `window`, `max_count`, `dlc`, `bus_rate` as float32, `seconds`); `table_header(t)` rows parsed by `header_table()` equal `t.entries()`
- [X] T011 [P] [US1] Add `test_read_candump_matches_frames_reader`: a small candump log in `tests/security/can_ids/fixtures/benign.log` (10 lines, `(1700000000.000123) can0 123#DEADBEEF`) read by `pf.read_candump` equals `frames.read_candump` column by column (ts µs, id, dlc, data), and `pf.calibrate([cap])` returns a table with those ids
- [X] T012 [P] [US1] Add `test_alarms_matches_c_semantics` with hand-built cases: k=3 flagged within 200 ms fires once, hold-off 1 s suppresses the next, flags outside the window do not fire; expected arrays written by hand from `msml_alarm.c`
- [X] T013 [US1] Extend `tests/security/can_ids/test_release_export_v2.py`: in the parity test assert `par["numpy_feature_mismatches"] == 0` and compare `pf.features(cap, table)` with `cal.features(cap, table)` (`np.array_equal` on `.view(np.uint32)`) and `pf.alarms(...)` with `forest_features.alarms(...)` for every parity capture and the three examples (runs in the firmware job, needs cc)

### Implementation for User Story 1

- [X] T014 [US1] Create `src/mobility_model_zoo/security/can_ids/picket_forest.py` (module docstring: user-facing reference of picket-forest, numpy only) and move from `calibrated.py` verbatim: the constants `MIN_WINDOW_US`, `WINDOW_PERIODS`, `BUCKETS`, `MIN_FRAMES`, `MAX_IDS`, `RULES_MARGIN`, `LOG_CAP = 8.0`, `W_BUS = 256`, `W_BUS_LONG = 2048`, `UNKNOWN_RING = 64`, `MAX_SPAN_US = 2_000_000`, `FEATURE_NAMES`, `ENTRY`, class `Table`, `to_us`, `_window`, `bucket_counts`, `_trim`, `calibrate`, `rules`; move `vote_score` from `forest.py`
- [X] T015 [US1] In `picket_forest.py` implement `q_log2(num: np.ndarray, den: np.ndarray) -> np.ndarray` (float64 `np.log2(num/den)`, non-finite → `LOG_CAP`, `np.floor(r*256+0.5)/256`, clip ±`LOG_CAP`, `astype(np.float32)`) and `features(cap, table) -> float32[n,10]` per the table in research.md R2: per-id groups via `np.unique(..., return_inverse)` and stable argsort; `log_dt_period` from per-id diffs (first frame of an id and `period_us == 0` → `LOG_CAP`); `log_count_ratio`/`count_excess` from `bucket_counts` per id against `max_count`; `dlc_changed_cal`; `hamming`/`bytes_changed` via xor with the id's previous data and a 256-entry popcount table (0 for the first frame); `unknown_count`/`unknown_count_long` from the cumulative count of unknown frames windowed by index (`W_BUS`, `W_BUS_LONG`) and by time (`searchsorted` on `ts - MAX_SPAN_US`, strict as in C: `>=` breaks), clipped to `UNKNOWN_RING`; `log_bus_rate` = 0 for the first 256 frames, else `q_log2(256.0*1e6/(ts - ts[i-256]), float32(bus_rate))`
- [X] T016 [US1] In `picket_forest.py` implement `alarms(ts_us, flagged, k, window_ms, holdoff_ms=1000.0) -> uint8[n]` as a loop over `np.flatnonzero(flagged)` reproducing `msml_alarm_update` (ring of k timestamps, `ts - oldest > window_us` → no alarm, hold-off `ts - last < holdoff_us`), with k clamped to 1..16 and window/hold-off in integer microseconds (`int(window_ms * 1000)`)
- [X] T017 [US1] In `picket_forest.py` implement `load_model(path)` (joblib; validate `format == "picket-forest-v2"` and keys `model`, `threshold`, `rules_margin`, `alarm`, else `ValueError`), `load_table(path)` / `save_table(table, path, note="")` for format `picket-forest-table-v1` (fields and ordering in contracts/model-repo-files.md; `bus_rate` written as `float(np.float32(...))`), `load_capture(path)` (examples JSON → capture dict with `ts` = `ts_us/1e6` float64, `can_id` uint32, `dlc` uint8, `data` uint8 n×8, `y` zeros int8, `id` = file stem) and `read_candump(path, name=None)` (port of `frames.read_candump` with the same regular expression, numpy arrays, no pandas)
- [X] T018 [US1] In `picket_forest.py` implement `score(cap, table, model) -> (float32[n], uint8[n])` (`x = features`; `s = vote_score(model["model"], x)`; `flags = rules(x, model["rules_margin"]) > 0`; `a = alarms(to_us(cap["ts"]), flags, model["alarm"]["k"], model["alarm"]["window_ms"], model["alarm"]["holdoff_ms"])`) and `summary(cap, scores, alarms) -> str` with the fixed format `"{n} frames, {seconds:.2f} s; {k} alarm(s)" + " at frame {i} (t={t:.3f} s)" per alarm + "; highest forest score {max:.3f}"`
- [X] T019 [US1] Turn `src/mobility_model_zoo/security/can_ids/calibrated.py` into a thin owner of the C path: `from mobility_model_zoo.security.can_ids.picket_forest import (Table, calibrate, rules, to_us, bucket_counts, FEATURE_NAMES, ENTRY, RULES_MARGIN, MAX_IDS, ...)` re-exported with `__all__`; keep `_lib`, `_batch`, `features`, `event_flags` unchanged; in `forest.py` replace `vote_score` by `from .picket_forest import vote_score`; in `frames.py` make `read_candump` build its DataFrame from `picket_forest.read_candump`
- [X] T020 [US1] In `src/mobility_model_zoo/security/can_ids/release_export_v2.py`: `parity()` also computes numpy features/alarms per capture and returns `numpy_feature_mismatches` and `numpy_alarm_mismatches` (export refuses the release when any count is non-zero); `export()` writes `examples/<file>` (byte copies of `zoo/models/picket-forest/examples/*.json`) and `calibration_table.json` (`pf.save_table(table, ..., note=...)`) into `out_dir`; add `table_json(table, path, note)` next to `table_header`
- [X] T021 [US1] In `src/mobility_model_zoo/security/cli.py` make `v2 table` also write `<out stem>.json` via `pf.save_table` and print both paths; add `v2 table-json --from-header picket_forest_table.h --out calibration_table.json` for repacking an existing release (parses the header rows, writes the JSON with a note naming the header)
- [X] T022 [US1] In `zoo/models/picket-forest/model.yaml` replace `card.how_to_run` with the snippet of contracts/picket-forest-api.md (three `hf_hub_download` lines, `pf.score`, `print(pf.summary(...))`) and add `card.own_data` with the own-data snippet; update `card.input_output` to mention `calibration_table.json` next to the header
- [X] T023 [US1] Run `uv run pytest tests/security -q` and, with a compiler, `uv run pytest tests/security/can_ids/test_release_export_v2.py -q`; fix any mismatch in `picket_forest.py` (if `log2` differs by one ulp on a platform, switch `q_log2` to `np.frompyfunc(math.log2, 1, 1)` as research.md R2 allows and note it in the module docstring)

**Checkpoint**: `picket_forest` reproduces every example bit-exactly without a compiler; the card snippet is complete.

---

## Phase 4: User Story 2 — The gate refuses a card that cannot be followed (Priority: P1)

**Goal**: the fresh environment is built from the card's install line, every model's snippet runs there, its output lands on the card, and each failure of 2026-10-11 is rejected by a test.

**Independent Test**: `uv run pytest tests/release -q -k "usage_runner or rule_12 or card_mcu or card_emlearn"` passes; a `FakeRunner(returncode=1)` fails rule 12 for an mcu model; the integration test shows a real `[edge]` venv rejecting `import torch`.

### Tests for User Story 2

- [X] T024 [P] [US2] Create `tests/release/test_usage_runner.py` with `test_install_spec_keeps_extras` (`install_spec(root, 'pip install "mobility-model-zoo[edge] @ git+...@x/v1"') == f"{root}[edge]"`, two extras, no brackets → `str(root)`) and `test_fresh_env_rejects_import_outside_extra` marked `network` and `slow`: a real `VenvRunner(root, None, install_line_with_edge)` running `import torch` returns rc ≠ 0, running `from mobility_model_zoo.security.can_ids import picket_forest` returns 0
- [X] T025 [P] [US2] In `tests/release/test_edge_rules.py` add `test_rule_12_runs_how_to_run_for_mcu` (gate with `FakeRunner`: after the device example check, `runner.calls` has exactly one entry equal to `cards.fill(how_to_run, staging.repo, staging.revision, "")`, `gate.how_to_run_output` is the fake output, and the rendered card contains "Output:" followed by it) and `test_rule_12_fails_when_mcu_snippet_fails` (`FakeRunner(returncode=1)` → rule 12 failure text contains "how_to_run failed")
- [X] T026 [P] [US2] In `tests/release/test_edge_rules.py` add `test_tree_file_rule_requires_examples_and_table`: a staged tree model without `examples/01-...json` fails naming the file; with a differing sha256 fails; with `calibration_table.json` whose entries differ from the staged header fails; the edge-fixture-forest fixture extended with both passes
- [X] T027 [P] [US2] Add `tests/release/test_card_own_data.py`: a model.yaml with `card.own_data` renders "### Use it on your own vehicle" with `{repo_id}`/`{revision}` filled; without the field the heading is absent

### Implementation for User Story 2

- [X] T028 [US2] In `src/mobility_model_zoo/release/usage.py` add `install_spec(root: Path, install_line: str) -> str` (regex `mobility-model-zoo\[([^\]]+)\]` → `f"{root}[{extras}]"`, else `str(root)`), give `VenvRunner.__init__` the parameter `install_line: str`, install `install_spec(self.root, self.install_line)`; on a non-zero `uv pip install` raise `UsageError("fresh environment: install failed: " + last 5 stderr lines)`
- [X] T029 [US2] Pass the install line: `src/mobility_model_zoo/release/cli.py` `_runner()` takes the model name and builds `VenvRunner(Path.cwd(), token, reg.model(name)["card"]["install"])`; `src/mobility_model_zoo/release/publish.py` `build()` the same; update every caller (`check_cmd`, `build_cmd`, `publish`)
- [X] T030 [US2] In `src/mobility_model_zoo/release/gate.py` `rule_12`: for `self.mcu`, after `_device_example`, when `self.runner is not None` run the filled `how_to_run` (`cards.fill(..., "")`), on rc ≠ 0 append `f"how_to_run failed (exit {rc}): {last 5 lines}"`, else set `self.how_to_run_output = out.strip()[:MAX_OUTPUT_CHARS]`; add the attribute with default `None` to `Gate`
- [X] T031 [US2] In `gate.py` extend the tree-file rule (the one using `_staged_tree_scorer`, engine `emlearn`): for each registry example `zoo/models/<name>/examples/*.json` require `examples/<file>` in `record["files"]` with equal sha256 (`sha256_file` of the registry file); require `calibration_table.json` in the staged files, download it and the staged `picket_forest_table.h`, compare `pf.load_table(json).entries()` with `header_table(header)` row by row; failure messages name the file
- [X] T032 [US2] Carry the output to the card: in `src/mobility_model_zoo/release/publish.py` `build()` pass `how_to_run_output=gate.how_to_run_output` into `CardInput` and write it into `build.json`; in `publish()` and `deprecate()` re-render with the stored value so the published card and the deprecation commit keep the block
- [X] T033 [US2] Update `specs/005-topic-layout-security-merge/contracts/release-format.md` rule 12 and the tree-file rule with the new wording (contracts/gate-and-card.md) and list `examples/*.json` and `calibration_table.json` as published files of tree models
- [X] T034 [US2] Extend the release test fixtures so the gate passes: `tests/release/fixtures/registry/zoo/models/edge-fixture-forest/` gets staged `examples/*.json` (copies of its registry examples) and a `calibration_table.json` consistent with its header in the fake hub (`tests/release/release_env.py`); regenerate the three golden cards with `ZOO_UPDATE_GOLDEN=1 uv run pytest tests/release/test_card_build.py tests/release/test_card_mcu.py tests/release/test_card_emlearn.py` and check the diff shows only the "Output:" and own-data blocks
- [X] T035 [US2] In `src/mobility_model_zoo/site/build.py` and `src/mobility_model_zoo/site/templates/partials/quickstart.html.j2`: for mcu models read `how_to_run_output` from the published card (same function the F4 parity check uses) and show it in "Get this output"; show `own_data` as a further step "Use your own vehicle" when set; adapt `tests/website/test_model_page.py` and the website fixture registry (`tests/website/fixtures/registry/zoo/models/picket-forest/model.yaml` gets `own_data`)

**Checkpoint**: rule 12 runs every snippet in the card's own environment; the five failures are rejected by tests.

---

## Phase 5: User Story 3 — Small installs, one extra per model kind (Priority: P2)

**Goal**: every card's install line names exactly its extra; an edge install downloads no deep-learning framework.

**Independent Test**: `uv venv` + `uv pip install ".[edge]"` → `import torch` fails and site-packages < 200 MB; `".[text]"` → scout-large's snippet imports work (quickstart.md step 3).

- [X] T036 [P] [US3] Set `card.install` to `mobility-model-zoo[text] @ git+...@<tag>` in `zoo/models/scout-large/model.yaml` and `zoo/models/sandbox-pipeline-tiny/model.yaml`; confirm `[edge]` in `zoo/models/picket-forest/model.yaml`, `zoo/models/picket-mlp/model.yaml`, `zoo/models/hum-fan/model.yaml`, `zoo/models/pace-cnn/model.yaml`
- [X] T037 [P] [US3] Mirror the install lines in the test registries: `tests/website/fixtures/registry/zoo/models/{scout-large,sandbox-pipeline-tiny}/model.yaml` and `tests/release/fixtures/registry/zoo/models/sandbox-pipeline-tiny/model.yaml` get `[text]`; regenerate the sandbox golden card
- [X] T038 [US3] Add `tests/unit/test_dependency_layout.py`: parse `pyproject.toml` (`tomllib`) and assert the base has no torch/transformers/pandas/scikit-learn, `text` holds the four text packages, `edge` holds scikit-learn and joblib, `jtbd` references `mobility-model-zoo[text]`; and for every `zoo/models/*/model.yaml` the install line's extra is `text` for runtime `python` and `edge` for runtime `mcu`
- [X] T039 [US3] Add `scripts/check_install_size.sh` (used by quickstart.md step 3 and callable in CI): fresh uv venv, `uv pip install ".[edge]"`, print site-packages size in MB, exit 1 above 200 MB or if `python -c "import torch"` succeeds; wire it as a step of the `edge` job in `.github/workflows/ci.yml`
- [X] T040 [US3] Check every workflow still syncs what it needs after T001: `.github/workflows/ci.yml` jtbd jobs (torch via `[jtbd]`→`[text]`), `firmware.yml:104-106` (`--with scikit-learn` now redundant, keep harmless), `datasets.yml`, `hil.yml`, `site.yml`, `release-verify.yml` / `release-publish.yml` (`uv sync --extra release` plus `--extra edge` if `zoo check` now imports `picket_forest` for the table check); run `uv run python scripts/ci/select_tests.py --all` to confirm nothing breaks

**Checkpoint**: install lines and extras agree; the size guard runs in CI.

---

## Phase 6: User Story 4 — Try it in five minutes (Priority: P2)

**Goal**: one quickstart document, rendered on the website and linked from the README, with the Python requirement and the observed pitfalls.

**Independent Test**: `uv run zoo site build --out build/site` produces `build/site/quickstart/index.html` containing both install lines of the latest published versions and the three pitfalls; `tests/website` passes; the README section matches the registry.

- [X] T041 [P] [US4] Write `docs/quickstart.md` ("Try it in five minutes"): prerequisites (Python 3.12, uv, link to uv install), one environment (`uv python install 3.12`, `uv venv --python 3.12`, `source .venv/bin/activate`; one line for `python3.12 -m venv` + `pip`), install (`{install:picket-forest}` and `{install:scout-large}` placeholders), run (save the card snippet as `demo.py`, `python demo.py`), expected output (one line per model), pitfalls with symptoms from research.md R9, next steps (model pages, own vehicle)
- [X] T042 [US4] In `src/mobility_model_zoo/site/build.py` render `docs/quickstart.md` to `/quickstart/` through `site/markdown.py` with a new template `src/mobility_model_zoo/site/templates/quickstart.html.j2` (base layout, title, rendered body); replace `{install:<model>}` with `install_line(model, latest published version)` and fail the build with a clear message when a model has no published version; register the page in the link checker's page list
- [X] T043 [P] [US4] Link the page: `src/mobility_model_zoo/site/templates/start.html.j2` hero gets "Try it in five minutes" → `/quickstart/`; `partials/quickstart.html.j2` install step gets "New here? Start with the quickstart." → `/quickstart/`
- [X] T044 [P] [US4] Add a "Try it in five minutes" section near the top of `README.md` (after the intro): the three commands for picket-forest with the latest install line verbatim, the expected summary line, and a link to `docs/quickstart.md`
- [X] T045 [US4] Add `tests/website/test_quickstart_page.py`: the page renders, contains both install lines from the fixture registry, the string "Requires Python 3.12 or newer" or the doc's own requirement sentence, and the three pitfall headings; and `tests/unit/test_readme_install_lines.py`: every `pip install "mobility-model-zoo[` line in `README.md` equals `install_line()` of that model's latest published version
- [X] T046 [US4] Update `docs/website.md` (pages table: `/quickstart/` from `docs/quickstart.md`) and `docs/adding-a-model.md` (install line must name the extra of the runtime; `how_to_run` must run as pasted in a fresh venv built from that line; optional `card.own_data`)

**Checkpoint**: a newcomer has one page to start from, on the site and in the repository.

---

## Phase 7: User Story 5 — Patched releases of both models (Priority: P3)

**Goal**: picket-forest 0.2.1 and scout-large 0.1.3 published with cards that passed the new gate; 0.2.0 deprecated. Owner approves the cards in `release-publish`.

**Independent Test**: following the published 0.2.1 and 0.1.3 cards from a fresh environment prints the expected results (quickstart.md step 7); the 0.2.0 card shows the deprecation banner.

- [X] T047 [US5] Assemble the 0.2.1 staging directory: `huggingface_hub.snapshot_download("mobility-model-zoo/picket-forest", revision="v0.2.0", local_dir="build/repack-0.2.1", allow_patterns=[...all 0.2.0 files...])` without `README.md`, copy `zoo/models/picket-forest/examples/*.json` to `build/repack-0.2.1/examples/`, run `uv run zoo-security can-ids v2 table-json --from-header build/repack-0.2.1/picket_forest_table.h --out build/repack-0.2.1/calibration_table.json`; verify every pre-existing file's sha256 equals the 0.2.0 record
- [ ] T048 [US5] `uv run zoo stage picket-forest 0.2.1 --from build/repack-0.2.1`; edit `zoo/models/picket-forest/releases/0.2.1.yaml`: `change_type: patch`, `changes:` "Card and packaging only: the Python reference runs without the repository or a compiler, the model repository ships the example captures and the calibration table as JSON, the install line names the edge extra. Weights, thresholds and device code identical to 0.2.0.", `recipe.git_commit` = this feature's commit, copy `evaluation`, `performance`, `provenance` from 0.2.0; copy `results/0.2.0/` to `results/0.2.1/`, and the `0.2.0.compliance.yaml`, `.ai-act.md`, `.training-data-summary.md`, `.publication-scan.json` companions to `0.2.1.*` (adjusting the version inside) — **owner step (tokens, compliance sign-off, approval): [release-runbook.md](release-runbook.md); `zoo new-patch` creates the record, results and compliance drafts**
- [ ] T049 [US5] Create `zoo/models/scout-large/releases/0.1.3.yaml` as a copy of `0.1.2.yaml` with `version: 0.1.3`, today's `date`, `change_type: patch`, `changes:` "Card and packaging only: the install line names the text extra and states the Python requirement. Weights identical to 0.1.2.", `recipe.git_commit` = this feature's commit, `published: null`, `deprecated: null`; same `files` and `staging`; copy `results/0.1.2/` to `results/0.1.3/` and the compliance companions to `0.1.3.*` — **owner step (tokens, compliance sign-off, approval): [release-runbook.md](release-runbook.md); `zoo new-patch` creates the record, results and compliance drafts**
- [ ] T050 [US5] Run the gate locally for both: `uv run zoo check picket-forest 0.2.1` and `uv run zoo check scout-large 0.1.3` (with `HF_RELEASE_TOKEN`); confirm rule 12 ran the snippets and the "Output:" block of picket-forest shows the summary of example 01 (one alarm at frame 1155); fix the registry until both pass — **owner step (tokens, compliance sign-off, approval): [release-runbook.md](release-runbook.md); `zoo new-patch` creates the record, results and compliance drafts**
- [ ] T051 [US5] Commit, open the PR for branch `013-fresh-install-quickstart`, merge after CI; tag `picket-forest/v0.2.1` and `scout-large/v0.1.3` on `main`; `release-verify` builds the previews; the owner reviews the cards and starts `release-publish` for each (owner step, not automated) — **owner step (tokens, compliance sign-off, approval): [release-runbook.md](release-runbook.md); `zoo new-patch` creates the record, results and compliance drafts**
- [ ] T052 [US5] After both publishes: `uv run zoo deprecate picket-forest 0.2.0 --reason "the card's snippet could not be run from a fresh install; use 0.2.1" --successor 0.2.1`; confirm the 0.2.0 card carries the banner and its files and tag are unchanged — **owner step (tokens, compliance sign-off, approval): [release-runbook.md](release-runbook.md); `zoo new-patch` creates the record, results and compliance drafts**
- [ ] T053 [US5] Run quickstart.md step 7 on a machine (or a clean folder on the owner's Mac with a fresh uv venv) and record both timings, the printed outputs and any friction in `specs/013-fresh-install-quickstart/validation.md` (SC-001, SC-007) — **owner step (tokens, compliance sign-off, approval): [release-runbook.md](release-runbook.md); `zoo new-patch` creates the record, results and compliance drafts**

**Checkpoint**: both cards work from a fresh install; the broken card is marked.

---

## Phase 8: Polish & cross-cutting

- [ ] T054 [P] `uv run ruff check src tests && uv run ruff format --check src tests`; `uv run pytest -q` (full suite) and the firmware job's parity command with a compiler
- [X] T055 [P] Remove the now-unused `pd` import path from the user-facing chain: confirm `release_export_v2.reference` no longer needs pandas for `reference()` (keep `_frames` for `parity`); confirm `calibrated.py`'s module docstring says it holds the C oracle and points to `picket_forest.py`
- [X] T056 [P] Update `tests/release/fixtures/golden/*.README.md` one final time if any template text changed in Phases 4–6, and check the HF org card Space text (`docs/hf-org/`) still matches the install lines
- [ ] T057 Update `specs/013-fresh-install-quickstart/spec.md` status to Implemented with the publication dates, and record in the compliance audit trail (`zoo/models/*/releases/0.2.1.compliance.yaml`, `0.1.3.compliance.yaml`) that no data input changed

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: starts immediately; T002 after T001; T003 parallel.
- **Foundational (Phase 2)**: after Phase 1; T005, T006, T007 parallel; blocks every story.
- **US1 (Phase 3)**: after Phase 2. Tests T008–T012 parallel and before T014–T018; T013 after T015/T016; T019 after T014; T020 after T017–T018; T021 after T017; T022 after T018; T023 last.
- **US2 (Phase 4)**: after Phase 2; T031 and T034 need `picket_forest.load_table` (T017) and `header_table` (T007). Tests T024–T027 parallel; T028 → T029 → T030; T031 after T028; T032 after T030; T035 after T032.
- **US3 (Phase 5)**: after Phase 1; independent of US1/US2 except T037's golden regeneration, which should follow T034.
- **US4 (Phase 6)**: after Phase 2 (T004); T042 after T041; T045 after T042–T044.
- **US5 (Phase 7)**: after US1–US4 are merged; strictly sequential T047 → T048 → T049 → T050 → T051 → T052 → T053.
- **Polish (Phase 8)**: after US5.

### Parallel Opportunities

- Phase 2: T005 ‖ T006 ‖ T007.
- US1 tests: T008 ‖ T009 ‖ T010 ‖ T011 ‖ T012 (same new file for T008–T012: write them as one task batch or in sequence by one agent; they are marked [P] because they have no code dependencies).
- US2 tests: T024 ‖ T025 ‖ T026 ‖ T027.
- US3: T036 ‖ T037; US4: T041 ‖ T043 ‖ T044.
- US2 and US3 can proceed while US1's numpy port (T015) is being written.

### Parallel Example: User Story 1

```bash
# Tests first (one agent per file is simplest):
Task: "T008–T012 test_picket_forest_reference.py"
Task: "T013 extend test_release_export_v2.py parity"
# Then the module:
Task: "T014 move pure parts into picket_forest.py" → "T015 features" → "T016 alarms" → "T017 loaders" → "T018 score/summary"
# Then in parallel:
Task: "T019 re-exports"  ‖  Task: "T020 export + parity"  ‖  Task: "T021 CLI table-json"  ‖  Task: "T022 model.yaml snippets"
```

---

## Implementation Strategy

### MVP first (US1)

1. Phase 1 + 2 (dependency layout, card slots, fixtures).
2. Phase 3: the numpy reference and the complete snippet. Validate with quickstart.md steps 1–3.
3. Demo: in a fresh `[edge]` venv, run the new snippet against the staging repository of 0.2.1 (needs T047–T048 staged early for a realistic test; a local directory with the same files works for the loaders).

### Incremental delivery

1. US1 → the path works. 2. US2 → the gate keeps it working. 3. US3 + US4 → small installs and a page to start from. 4. US5 → published; 0.2.0 deprecated. 5. Polish.

### Notes

- Never edit the C sources under `firmware/`; the numpy port follows them.
- Published versions are immutable: never re-upload to `v0.2.0` or `v0.1.2`.
- Commit after each task group; the owner approves only the release-publish step.
