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

## US4 (2026-10-08)

- Schemas (contract copies updated): `runtime` python|mcu, `languages` may be empty, `card.device_usage`, task ids with hyphens (`can-ids`, `sound-anomaly`), `{text}` in `how_to_run` required by gate rule 1 for python only; mcu budget `{ram_kb, flash_kb, target}`; `provenance.sources[].dataset`; `evaluation.reference_kind`; `metrics[].origin`; the "accuracy" ban moved from the results schema to gate rule 10 (model consensus only). All published release records still validate (test over `zoo/models/*/releases/*.yaml`).
- Gate: rule 1 runtime conditions; rule 6 dataset declarations, licence match, share-alike forces the model licence, non-commercial training sources fail, `base_model_license` may be null when `base_model` is null; rule 10 per `reference_kind` (`GROUND_TRUTH` sentence); rule 11 and `forbidden_upload` reject `*.eval.npz`; rules 12/13 for mcu load the staged int8 npz and compare examples bit-exactly on the host reference, example sources must be synthetic or a dataset with `redistribution: allowed`; new rule 15 device evidence (in `OFFLINE_RULES` and the publish rules). Python fixtures and golden cards unchanged (byte-identical).
- Known gap: the mcu branch of rules 12/13 supports int8-engine models (`.npz`). `picket-forest` is a tree model (emlearn C, joblib host reference); its release needs an emlearn host-reference branch, planned with its first release.
- Card: mcu front-matter tags (`tinyml`, `microcontroller`, target), device C usage, JSON examples, budget sentence, "Measured on" column with hardware and origin, dataset provenance table, ground-truth quality sentence. T066: the rendered mcu card of `edge-fixture-tiny` is the golden file `tests/release/fixtures/golden/edge-fixture-tiny-0.1.0.README.md` (the fixture npz is built at test time because model files never go into git).
- `edge measure MODEL.npz -b BOARD --out FILE.json` (results format with `origin` and `hardware`); on `sim` `can_ids_mlp` gives latency 0.3 µs (batched samples below 20 µs), `imu_gnss_cnn1d` 48.5 µs. flash/RAM come from the PlatformIO manifest on real targets (whole image) and from the model's own footprint on the simulator.
- CI: `test` job without TensorFlow (`--extra jtbd --extra release --extra edge --extra labeling-api`); new jobs `edge-sim` (verified locally) and `edge-qemu`; `firmware.yml` (11-target matrix, size summary, picket-forest strict C build and C-vs-Python parity with emlearn, verified locally: 33 passed); `hil.yml` gated by `HIL_RUNNER_ENABLED`. QEMU, the PlatformIO matrix and the self-hosted HIL job run only on GitHub.
- Models registered: `picket-forest`, `picket-mlp` (security, can-ids), `hum-fan` (condition-monitoring, sound-anomaly, CC-BY-SA-4.0), `pace-cnn` (activity, `pipeline_tag: other` with tag `time-series-classification`); draft releases 0.1.0 with dataset sources, `reference_kind: ground_truth` and mcu budgets from the task documents. Pre-zoo research results kept in `topics/*/reports/<model>/` with a "not a benchmark result" README.
- GATE T070 (`zoo check <m> 0.1.0 --offline`, exit 1 = check failed in the zoo convention): every model fails only on "not staged" (rule 1: `files` empty, no staging revision), "results missing" (rules 9, 10, 15, 16) and "no examples" (rule 13, they come from the trained model). Rules 2, 3, 4, 6, 7, 8, 11, 14 pass; no schema error in `model.yaml` or in the record structure.

## US5 (2026-10-08)

- `docs/credentials.md` lists `HF_RELEASE_TOKEN`, `HF_STAGING_TOKEN` and `HIL_RUNNER_ENABLED` with scope, users and rotation; `tests/unit/test_workflow_secrets.py` checks every `secrets.*` and `vars.*` of the workflows against it. `.env.example` mentions `MMZ_DATA` and `HIL_RUNNER_ENABLED`.
- Repository settings of `mhabedank/mobility-model-zoo`: secret `HF_RELEASE_TOKEN` exists (2026-10-01); variable `HIL_RUNNER_ENABLED=false` set on 2026-10-08.

### Old staging repos

The old `hub` workflow created no repositories on Hugging Face. With both tokens (user `ZenCoding`, organization `mobility-model-zoo`), the full model and dataset lists hold only the zoo's own repos:

| Repo | Private | Created | Last modified |
|---|---|---|---|
| mobility-model-zoo/scout-large | no | 2026-10-07 | 2026-10-08 |
| mobility-model-zoo/scout-large-staging | yes | 2026-10-07 | 2026-10-07 |
| mobility-model-zoo/sandbox-pipeline-tiny | yes | 2026-10-01 | 2026-10-01 |
| mobility-model-zoo/sandbox-pipeline-tiny-staging | yes | 2026-10-01 | 2026-10-01 |

Nothing to delete.

### Old repository (before retirement)

`mhabedank/mobility-security-ml`: public, not archived, branches `main`, `claude/clever-goldberg-ygio83`, `claude/cool-volta-rqsgdx`; secrets `HF_RELEASE_TOKEN` and `HF_STAGING_TOKEN` (2026-10-07), no variables. Retirement (README, secrets, archive) waits for the merge of this feature into `main` and the owner's confirmation (T075).

## Quickstart and final checks (2026-10-08)

1. Layout: `topics/` holds `productdev`, `security`, `condition-monitoring`; none of the six old top-level folders exists. `zoo validate --all` ok (compliance register, datasets). `zoo audit`: sandbox-pipeline-tiny 0.2.0 and scout-large 0.1.0, 0.1.1, 0.1.2 OK.
2. History: `git log --follow` reaches the original commits of 2026-10-07 (`metrics.py`: "Add can-ids-tiny …"; `reference.py`: "Add HIL test bench …"); `check_merge_log.py`: merge log complete.
3. No data, no secrets: `zoo history-check` clean; no `test_vectors.h`, `.bin`, `model_zoo.c` or `.joblib` in any commit.
4. Datasets: `zoo data list` and `zoo data verify` as in US3; `MMZ_DATA=$(mktemp -d) zoo data download uci-har` downloaded 45 MiB and wrote `SOURCE.json`; `zoo data download syncan` refused with exit 3 ("rejected: Non-commercial licence"); nothing landed in the repository.
   End-to-end check on the real data: `condmon activity train --config configs/condition-monitoring/activity/pace-cnn.yaml --epochs 2` trained, exported and verified pace-cnn (TFLite interpreter mismatches 0; int8 accuracy 0.805 and macro-F1 0.800 against the UCI HAR test labels after 2 epochs, float 0.806; a smoke run, not a benchmark result), and `edge measure pace-cnn.npz -b sim` measured 169 µs median latency, 7.1 KiB flash and 5.1 KiB RAM on the host simulator, inside the task budget (32 KB RAM, 128 KB flash).
5. Edge: `edge build -t native` and the sim HIL suite pass (30 passed, 4 skipped); `zoo check` of the four models as in US4; `tests/release/test_card_mcu.py` renders the mcu card. QEMU runs in CI (`edge-qemu`).
6. Credentials: `HF_RELEASE_TOKEN` secret and `HIL_RUNNER_ENABLED=false` variable present. Retirement after the merge.

Runtime of the default test suite (`HF_HUB_OFFLINE=1 uv run pytest`, with the edge and edge-train extras): about 150 s on an M3 Pro (goal: under 4 minutes). The CI `test` job runs without TensorFlow; its time is recorded from the PR run.
