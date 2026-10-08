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
