# Validation: Topic layout and security merge

## Baseline (2026-10-08, branch at main 966effe plus 005 docs)

- Default test suite: 474 passed, 1 skipped, 1 deselected in 108 s (run on the merged feature 006 state).
- `uv run zoo validate --all`: ok, compliance register ok.

## Tools

- git-filter-repo a40bce548d2c, gitleaks 8.30.1, Apple clang 21.0.0, GNU Make 3.81, gh logged in.

## US1 (2026-10-08)

- Productdev material moved to `topics/productdev/` in one rename-only commit (66 files); references in configs, code, scripts, tests, README and `model.yaml` updated. Frozen benchmark `pilot-v2` still verifies (`verify_frozen` ok; hashes are content-based).
- Default test suite: 482 passed, 1 skipped, 1 deselected in 120 s. `zoo validate --all` ok including topic folders; `zoo compliance check --ci` ok; `zoo audit`: scout-large 0.1.0, 0.1.1, 0.1.2 OK.
- Card links (`scripts/import/check_card_links.py`): all links of the published 0.1.0 and 0.1.1 cards resolve. The 0.1.2 card has one broken link that the move did not cause: the Senedd licence URL written by the feature 006 bootstrap (`senedd.wales/help/copyright/`, 404). Register and THIRD_PARTY_NOTICES now point to https://research.senedd.wales/commission/access-to-information/copyright/; the published card is immutable and gets the fix with the next card patch.

## US2 (2026-10-08)

- Import: both branches merged with history (`Import mobility-security-ml goldberg …`, `… volta …`); merge log `topics/security/research/merge-log.md` covers 177 paths (`check_merge_log.py` exit 0). `zoo history-check`: no data files, model files or secrets in any commit (the int8 fixtures live in `tests/fixtures/edge-int8/`, not a `data/` folder).
- Integration: shared edge paths (`edge/paths.py`, `MMZ_DATA`, `MMZ_BOARDS`, `MMZ_EDGE_MODELS`); firmware model sources are build output (`edge build`, `make`, PlatformIO pre-script `gen_modelzoo.py`); reference models and their eval sets are built on first use under `build/edge/models/` and are deterministic (arrays and manifest identical across builds; npz bytes differ only in zip timestamps). `hilbench` renamed to `edge` (CLI, lock dir, udev rule, formats).
- Split of `train_real.py`: `security/can_ids/mlp.py` (picket-mlp), `condition_monitoring/sound_anomaly/train.py` (hum-fan), `condition_monitoring/activity/train.py` (pace-cnn), shared `edge/int8/keras_export.py`; common frame format `security/can_ids/frames.py`; picket-mlp reports frame metrics through `security/can_ids/metrics.py`. picket-forest ported (`--data`/`--out` in `$MMZ_DATA`, C sources `picket_forest.{c,h}`, `PICKET_FOREST_` macros); C-vs-Python parity test on a synthetic forest passes with emlearn.
- Task CLIs `security` and `condmon` registered; `evaluate` and `freeze` exit 5 until the benchmarks are frozen.
- `edge-train` extra: `tensorflow-cpu` has no macOS arm64 wheel, so non-Linux hosts get `tensorflow` (environment marker).
- The bench pytest plugin is inert unless boards are selected (`--hil-*`) or `-m hil` is requested.
- Lint: imported code formatted and lint-clean (`ruff check` passes on the whole repository).
- Default test suite: 602 passed, 2 skipped, 23 deselected in 137 s (with the `edge` and `edge-train` extras; without TensorFlow the Keras export tests skip).
- GATE T040: `uv run edge build -t native` ok; `uv run pytest -m hil --hil-board sim` on the generated reference models: 30 passed, 4 skipped (skips: real-board-only tests). One latent test bug fixed: the echo test sent more bytes than the firmware input buffer holds; it was hidden by the larger model set of the old repository.

## US3 (2026-10-08)

- Declarations live in the compliance register of feature 006, `topics/<topic>/compliance/datasets.yaml`, validated by `compliance/schemas/datasets.schema.json` (contract copies in this feature's `contracts/` and in 006). The 006 schema already had the provider fields; added: `commercial_use`, `use_case`, `license_checked`, the rules of T047 (training needs commercial use and no NC/ND, manual check needs a date, rejected and broken need a reason, id pattern), and signals/personal data required only for usable (not rejected) entries. The spelling of the register is kept (`licence`, `attribution_text`, `origin_url`).
- 15 declarations: security 9 (can-train-and-test, road, can-mirgu broken at source, veremi-extension, gps-spoofing-aissou; syncan, hcrl-car-hacking, tue-can-v2, gem-can rejected), condition-monitoring 6 (mimii, uci-har; dcase2020-task2-dev, dcase2021-toyadmos2, gnss-interference-mendeley, driver-behavior rejected). Every entry has `redistribution: unclear` or `not_allowed`; nothing is published.
- Licences checked on 2026-10-08: Zenodo API for road (cc-by-4.0), mimii (cc-by-sa-4.0), veremi-extension (cc-by-4.0); DataCite for can-train-and-test (DOI 10.11583/DTU.24805533, cc-by-4.0) and gps-spoofing-aissou (DOI 10.17632/z7dj3yyzt8.3, cc-by-4.0). The UCI API states no licence; `zoo data verify` reports those entries as `unstated`, never as ok. Crawl signals (robots.txt, TDMRep, X-Robots-Tag, ai.txt) of every origin URL checked live: no deny.
- New source classes `can-bus-datasets`, `machine-sound-datasets`, `imu-activity-datasets` with LIA; PRIVACY.md, record of processing and LIA/DPIA re-rendered. New `art9_handling: not_applicable` for sensor data that is never sent to a language model.
- `zoo data list|info|verify|download|path|tree|validate`; `zoo validate --all` runs `zoo data validate`; `edge data` removed. Bitbucket provider (can-train-and-test files land in `extracted/`; `can_train_and_test.py` only parses and caches Parquet in `$MMZ_DATA/derived/`). Download refuses rejected, broken (without `--force`) and targets inside the repository (exit 3). Training guard `require_training_allowed` in `keras_export.train` (picket-mlp, hum-fan, pace-cnn) and `forest evaluate|export`.
- Exit codes: the contract now follows the zoo convention in `release/errors.py`; `zoo data verify` exits 1 on a licence mismatch.
- `zoo compliance check --ci` was run for the first time over the imported material: three scanner false positives (`@50 Hz` as a handle, hex payload `00112233…` as a phone number, `pricing` in a cited URL) were fixed in the scanner patterns with tests; real identifiers are still found.
- Workflow `.github/workflows/datasets.yml` (weekly, on dispatch and on declaration changes; no downloads, no secrets).
