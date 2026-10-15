# Tasks: Transparency over training data, benchmarks and training runs (MLflow)

**Input**: Design documents from `/specs/017-mlflow-data-transparency/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/cli.md](contracts/cli.md), [contracts/tracking.md](contracts/tracking.md), [contracts/release/](contracts/release/), [quickstart.md](quickstart.md)

**Tests**: The plan names its test files, so pytest tasks are included. They are written alongside the code, not TDD-first. Spark-only checks are owner tasks marked **(Spark)**. They need the DGX Spark and cannot run in CI.

**Organization**:
- US1 and US2 (P1) need no server and ship first.
- US3 (P2) brings the server and the tracking core. US4, US5 and US6 build on US3.
- T040 is the Principle IV go/no-go between US4's first integration and the rest.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story from spec.md (US1 to US6)

## Path Conventions

Single project:
- **Code**: `src/mobility_model_zoo/`
- **Tests**: `tests/`
- **Spark scripts**: `scripts/spark/mlflow/`
- **Owner docs**: `docs/`
- **Data**: lives in `$MMZ_DATA` (default `~/.cache/mobility-model-zoo/datasets`) and in the gitignored `data/`, never in git.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: extra, configuration keys, CI wiring and package skeletons.

- [X] T001 Add the optional extra `tracking = ["mlflow-skinny>=3.17.1,<4", "numpy>=1.26", "python-dotenv>=1.0", "psutil>=7", "nvidia-ml-py>=12"]` to `pyproject.toml` (after `labeling-api`, with a comment "experiment tracking client, feature 017; server runs on the Spark"), then run `uv lock` and commit `uv.lock`.
- [X] T002 [P] Add `tracking` to `TRAINING_EXTRAS` in `tests/unit/test_dependency_layout.py` and assert that `tracking` does not include `mobility-model-zoo[text]` and that the base dependencies stay `{"huggingface-hub", "numpy"}`.
- [X] T003 [P] Add three keys to `.env.example`:
  - `SPARK_HOST=`
  - `MLFLOW_TRACKING_URI=`, commented "http://127.0.0.1:5000 through `scripts/spark/mlflow/mlflow.sh tunnel`; leave empty to disable tracking"
  - `MLFLOW_TRACKING_URI_CONTAINER=`, commented "address for training containers on the Spark's `mmz-tracking` network, usually http://mlflow:5000"

  Add all three to the "Other local settings in `.env` (not used by CI)" paragraph of `docs/credentials.md`.
- [X] T004 [P] Create the package skeletons `src/mobility_model_zoo/datasets/inventory/__init__.py` and `src/mobility_model_zoo/tracking/__init__.py`, each with an SPDX header and module docstring, and empty test packages `tests/tracking/__init__.py`.
- [X] T005 [P] Add rules to `scripts/ci/select_tests.py` (done: `datasets/inventory` is already covered by the existing `datasets/*` rule of area `all`, which runs every test; new rules map `tracking` and `tests/fixtures/inventory`) mapping `src/mobility_model_zoo/datasets/inventory/**` to the `datasets` area, `src/mobility_model_zoo/tracking/**` and `tests/tracking/**` to a new `tracking` area (`tests/tracking`), and `scripts/spark/mlflow/**` and `docs/tracking.md` to `docs`. Keep `tests/unit/test_ci_select.py` green.
- [X] T006 [P] Add `--extra tracking` to both `uv sync` lines of the `test` job in `.github/workflows/ci.yml`. Leave the `checks`, `edge-sim` and `qemu` jobs unchanged so the install size check is unaffected.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the derived entities and hash helpers that US1, US2, US3 and US5 all read.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T007 Create the dataclasses `InventoryRow`, `HistoryEvent` and `VersionDiff` in `src/mobility_model_zoo/datasets/inventory/rows.py`, exactly as in [data-model.md](data-model.md).
  - **`InventoryRow` field values**:
    - `kind` ∈ {`dataset`, `source-collection`, `training-set`, `benchmark`}
    - `status` ∈ {`active`, `rejected`, `broken_at_source`, `frozen`, `decided`, `building`}
    - `permitted_use` ∈ {`training_allowed`, `benchmark_only`, null}
    - `availability` ∈ {`measured`, `register-only`, `partial`, `error`}
    - `integrity` ∈ {`ok`, `mismatch`, `unchecked`, `changed-after-freeze`}
  - **Validation**: "`(kind, id, version)` is unique"; "`sha256` is null only when `availability` is `register-only` and the hash needs data"; "`counts` values are ≥ 0".
  - **`HistoryEvent.event`** ∈ {`registered`, `field-changed`, `frozen`, `superseded`, `revised`, `excluded`, `retrieved`}.
  - Provide `to_dict()` for JSON output.
- [X] T008 Create `src/mobility_model_zoo/datasets/inventory/hashes.py` following the "Hashes" table of data-model.md:
  - `dataset_hash(source_json)`: sha256 over sorted `name:sha256` lines of `SOURCE.json` `files[]`, using `name:checksum` for zip-member entries.
  - `manifest_hash(manifest)`: `sha256(json.dumps(manifest, sort_keys=True).encode())`, the formula used by `security/can_ids/evaluate.py:234`. Import and share it rather than duplicating it if a helper already exists there.
  - `source_collection_hash(path)`: reuse `productdev/jtbd/freeze.sha256_canonical`.
  - `training_set_hash(frozen)`: returns `frozen["sha256"]`.

  Note that `productdev.jtbd.freeze` lives behind the `jtbd` extra: import it lazily, and fall back to an inline canonical hash if the import fails.
- [X] T009 [P] Add unit tests `tests/datasets/test_inventory_rows.py` for T007 (enum and uniqueness validation, `to_dict`) and T008 (each hash against a hand-computed value; `manifest_hash` equals the `based_on.manifest_sha256` recorded in `topics/security/benchmarks/can-ids-v2/manifest.json` for `can-ids-v1`).

**Checkpoint**: entities and hashes are tested. US1 and US2 can start; US3 can start in parallel on the tracking core.

---

## Phase 3: User Story 1 - See all datasets and benchmarks at a glance (Priority: P1) 🎯 MVP

**Goal**: `zoo data stats` lists every dataset, source collection, training set and benchmark version with size, counts, distributions, licence, permitted use, freeze date, hash, last change and users. It needs no server and no downloaded data.

**Independent Test**: [quickstart.md](quickstart.md) §1. Run it with and without `$MMZ_DATA`. Every active register entry and every manifest under `topics/*/benchmarks/` appears exactly once, and the counts match the manifests (`can-ids-v3`: 281 captures; roles test 183, train 47, validation 28, out_of_scope 17, excluded 6).

### Implementation for User Story 1

- [X] T010 [P] [US1] Implement the third-party dataset collector in `src/mobility_model_zoo/datasets/inventory/third_party.py`.
  - **Records**: read them through `datasets.registry.declarations(root)` and `to_source()`; raw YAML is also needed for `last_reviewed` and `storage`.
  - **When `$MMZ_DATA/<id>/SOURCE.json` exists** (resolve via `datasets.download.dataset_dir`):
    - set `version` to the `retrieved_at` date
    - set `sha256` via `dataset_hash`
    - measure `size_mb` and `files` by walking `$MMZ_DATA/<id>/`
    - set `availability` to `measured`
  - **Otherwise**: `version="register"`, `availability="register-only"`, `sha256=None`, `approx_size_mb` from the register, and the note "not downloaded here".
  - **Status**: rows with status `rejected` or `broken_at_source` are produced too. `collect()` filters them unless `include_rejected` is set, and always counts them.
  - Never open data files other than `SOURCE.json`; only `stat()` them (FR-008).
- [X] T011 [P] [US1] Implement the source collection collector for `topics/productdev/compliance/sources.yaml` in `src/mobility_model_zoo/datasets/inventory/sources.py`.
  - **Rows**: one row `kind=source-collection`, `id=productdev-sources`.
  - **Counts**: `counts.sources`.
  - **Distributions**: `source_class`, `licence` and `permitted_use`.
  - **Snapshots**: `snapshots` count and `size_mb` from the configured snapshot directory when it exists. Take it from `configs/productdev/jtbd/pilot-v1.yaml` `paths`, or the `storage:` value `data/snapshots`.
  - **Hash**: `source_collection_hash`.
- [X] T012 [P] [US1] Implement the benchmark readers in `src/mobility_model_zoo/datasets/inventory/benchmarks.py`, one per manifest shape, chosen by keys:
  - **jtbd pilot** (`chunks` + `holdout_chunks`):
    - counts `chunks`, `holdout_chunks`, `train_chunks`
    - lineage `supersedes`
    - note "no label distribution stored in this manifest"
  - **jtbd cluster** (`counts.items`):
    - counts per split for items, snapshots, pairs and sets; `excluded_items`, `excluded_snapshots`
    - distribution `split`
  - **can-ids** (`captures`):
    - counts `captures`, `frames`, `attack_frames`, `episodes`, `duration_s`
    - distributions `role`, `split`, `set`, `vehicle`, `dataset`, `attack_family`
    - lineage `based_on`
    - `licence` and `permitted_use` from `datasets[]` joined with the registry, using the strictest permitted use.
  - **For every benchmark**: `status` from `state`, or `frozen` when `frozen_at` is set. `id` is the family (`pilot`, `cluster`, `can-ids`); `version` is the folder name.
  - **Discovery**: scan `topics/*/benchmarks/*/manifest.json`.
  - **No benchmarks yet**: a topic without a benchmarks folder adds a footer note instead of rows. Today that is condition-monitoring.
- [X] T013 [P] [US1] Implement the training set collector for `span-train` in `src/mobility_model_zoo/datasets/inventory/training_sets.py`.
  - **Location**: resolve `paths.data` from `configs/productdev/jtbd/span-train-v1.yaml`.
  - **`frozen.json`**: `chunk_count`, `sha256`, `frozen_at`.
  - **`rows/rows.stats.json`**: `rows`, `rows_per_split.train` and `.val` → `rows_train` and `rows_val`, `relevant_rows`, `items_kept`, `items_dropped`, and distributions `language`, `source_type`, `sub_area` from `composition`.
  - **Missing data**: if the files are absent, emit `availability="register-only"` with the note "training set not on this machine".
  - **Lineage**: `built_from` → `productdev-sources`.
- [X] T014 [P] [US1] Implement `used_by` resolution in `src/mobility_model_zoo/datasets/inventory/used_by.py`:
  - **Datasets**: register `used_by`.
  - **Benchmarks**: every `zoo/models/*/releases/*.yaml` whose `evaluation.benchmark` equals the version, as `<model>@<version>`.
  - **span-train**: release records whose `recipe.config` or provenance names `span-train-v1`.
- [X] T015 [US1] Implement `collect(root, data_root=None, kinds=None, topics=None, use=None, include_rejected=False)` in `src/mobility_model_zoo/datasets/inventory/__init__.py`.
  - **Steps**: call T010 to T014; set `last_change` with one `git log -1 --format=%cs -- <path>` per source file, cached. When git is unavailable or the clone is shallow, set null.
  - **Errors**: catch per-row errors into `availability="error"` with a short note, so one bad manifest never stops the overview.
  - **Order**: sort rows by topic, kind, id, version.
- [X] T016 [US1] Implement the table and JSON output in `src/mobility_model_zoo/datasets/inventory/render.py`:
  - **Default columns**: `topic kind id version status use size files main-count frozen last-change integrity`.
  - **`--wide`**: adds licence, redistribution, sha256 (12 characters), lineage and used-by.
  - **Footer**: totals per kind and topic, the total measured size, the hidden rejected count, and notes (for example "condition-monitoring: no benchmarks frozen yet").
  - **JSON**: `--json` prints `[row.to_dict()]`.
- [X] T017 [US1] Add the `stats` command to `src/mobility_model_zoo/datasets/cli.py`, matching the contract:
  - options `--topic`, `--kind`, `--use`, `--include-rejected`, `--verify`, `--json`, `--wide` (multi-value where the contract shows `...`);
  - exit 0, or 7 when any row has integrity `mismatch` or `changed-after-freeze` (integrity arrives in US2; until then rows say `unchecked`).

  Use the existing `_run` error wrapper.
- [X] T018 [P] [US1] Add fixtures under `tests/fixtures/inventory/`: a mini repo tree with a `datasets.yaml` (one active, one rejected dataset), a jtbd pilot manifest, a cluster manifest and two can-ids manifests (v1 and v2 with `based_on`), a `sources.yaml`, a fake `$MMZ_DATA/<id>/SOURCE.json` with two files, and a `span-train` `frozen.json` + `rows.stats.json`. Keep every file small; no real data.
- [X] T019 [P] [US1] Write tests in `tests/datasets/test_inventory_collect.py`:
  - every reader's counts and distributions on the fixtures;
  - register-only vs measured rows (`MMZ_DATA` set to the fixture or to an empty directory);
  - the strictest permitted use for benchmarks;
  - `used_by` from a fixture release record;
  - an error row from a malformed manifest leaves the other rows intact;
  - the same dataset id in two topic registers yields one error row for that id, not two silent rows (spec edge case).
- [X] T020 [US1] Write CLI tests in `tests/datasets/test_inventory_cli.py` with `CliRunner` on the `zoo` app (`["data", "stats", ...]`):
  - table and `--json` output;
  - filters by topic, kind and use;
  - `--include-rejected`;
  - exit 0 without `MMZ_DATA` content;
  - one test against the real repository asserting the `can-ids-v3` role counts from the Independent Test above and the cluster-v1 item counts (dev 3395, test 6967, holdout 2133), and that the command finishes in under 30 s (a generous bound for SC-001; the plan's target is 10 s).

**Checkpoint**: `zoo data stats` answers "what do we have, how big, how many" in under one minute (SC-001, SC-002).

---

## Phase 4: User Story 2 - See when and how data changed (Priority: P1)

**Goal**: `zoo data history` and `zoo data diff` show versions, freeze dates, commits, register edits and differences. Integrity checks flag changed frozen benchmarks.

**Independent Test**: [quickstart.md](quickstart.md) §2.
- `zoo data history can-ids` lists v1 to v3 with dates, commits and the `based_on` chain.
- `zoo data diff can-ids-v2 can-ids-v3` shows 6 captures moved to `excluded`.
- Editing a frozen manifest in a scratch copy makes `zoo data stats` exit 7.

### Implementation for User Story 2

- [X] T021 [P] [US2] Implement git history in `src/mobility_model_zoo/datasets/inventory/history.py`, using the pattern of `site/roadmap.py:_history` (`git log --format='%H %cs' --reverse -- <file>` plus `git show <sha>:<file>`, `functools.cache`).
  - **Register files** (`topics/*/compliance/datasets.yaml`, `sources.yaml`):
    - parse each historic version;
    - emit `registered` when an id first appears;
    - emit `field-changed` with `field`, `old` and `new` for each changed scalar field, register values only.
  - **Benchmark manifests**:
    - emit `frozen` (the commit that added the manifest, via `--diff-filter=A`, plus `frozen_at`);
    - emit `superseded` from `supersedes` or `based_on`;
    - map the manifest's own `history[]`, `events[]` and `revisions[]` to `revised` and `excluded` events with `commit=null`.
  - **Datasets**: emit `retrieved` from `SOURCE.json` `retrieved_at` when present.
  - **Shallow clone or no git**: return `[]` with a flag that renders "history unavailable (shallow clone)".
- [X] T022 [P] [US2] Implement `src/mobility_model_zoo/datasets/inventory/integrity.py`:
  1. Every `based_on.manifest_sha256` must equal `manifest_hash` of the parent's current manifest; otherwise mark the child `mismatch`.
  2. A frozen manifest whose path has commits after the freezing commit, other than those covered by its own `revisions[]`, is marked `changed-after-freeze`.
  3. With `verify=True` and data present, call the existing verifiers and map failures to `mismatch`:
     - `productdev.jtbd.freeze.verify_frozen` and `verify_benchmark_frozen` for pilots;
     - `productdev.jtbd.cluster.bench.verify` for cluster;
     - `security.can_ids.benchmark.verify_captures` for can-ids.

     Import them lazily, because they need the `jtbd` or `edge` extras; if the import fails, leave the row `unchecked` with a note.

  Rows that are not checked stay `unchecked`; rows that pass get `ok`.
- [X] T023 [P] [US2] Implement `diff(a_row, b_row, members=False)` in `src/mobility_model_zoo/datasets/inventory/diff.py`, returning a `VersionDiff`:
  - **Counts and distributions**: per-dimension `{a, b, delta}`.
  - **Members**: added, removed and changed member ids with hashes — capture `id` and `sha256` for can-ids, chunk ids and hashes for pilots, record ids for registers. Never content.
  - **Protocol**: changed keys of `protocol` or `hashes` blocks.
  - **Kind mismatch**: raise a usage error when kinds or families differ.
- [X] T024 [US2] Wire integrity into `collect()` (T015). Add the `history ID` and `diff A B [--members]` commands and `--verify` to `src/mobility_model_zoo/datasets/cli.py`:
  - `history` accepts a dataset id, a family (`can-ids`, `pilot`, `cluster`, `span-train`) or one version (`can-ids-v2`) and prints events oldest first, then the lineage chain;
  - `diff` exits 2 on a kind or family mismatch;
  - `stats` exits 7 on `mismatch` or `changed-after-freeze`.
- [X] T025 [P] [US2] Write `tests/datasets/test_history_diff.py` on a temporary git repository built in the test (`git init`, commit the T018 fixtures, edit `permitted_use` in a second commit, add can-ids v2 in a third). Assert:
  - the `registered` and `field-changed` events with old and new values;
  - the `frozen` and `superseded` events;
  - the diff counts and members;
  - "history unavailable" for a shallow clone (`git clone --depth 1`).
- [X] T026 [P] [US2] Write `tests/datasets/test_integrity.py`:
  - a `based_on` hash mismatch after editing the parent manifest;
  - `changed-after-freeze` after a later commit to a frozen manifest;
  - no false positive for a cluster manifest whose later change is recorded in `revisions[]`;
  - `unchecked` when the verifier import fails;
  - the CLI exit code 7.
- [X] T027 [US2] Run `uv run zoo data stats` and `uv run zoo data history can-ids` on the real repository and fix any finding. Any real integrity finding in the committed benchmarks is reported to the owner, not "fixed" by editing a frozen manifest (constitution IX). Also update the stale table in `topics/security/benchmarks/README.md` to list `can-ids-v2` and `can-ids-v3` with their freeze dates and `based_on`.

**Checkpoint**: US1 and US2 together are the P1 MVP: the full data overview with history, needing no server.

---

## Phase 5: User Story 3 - Browse data versions in MLflow (Priority: P2)

**Goal**: a private MLflow server on the Spark, the tracking core (config, guard, client) and `zoo data publish` mirroring the overview into the `datasets` experiment idempotently.

**Independent Test**: [quickstart.md](quickstart.md) §3, §4, §8.
- `zoo tracking status` exits 0 through the tunnel.
- `zoo data publish` twice yields only `update` the second time.
- `zoo tracking audit` exits 0.
- The server is unreachable from the LAN.

### Implementation for User Story 3

- [X] T028 [P] [US3] Write `scripts/spark/mlflow/mlflow.sh` (bash, `set -euo pipefail`, SPDX header) with the subcommands from contracts/cli.md:
  - **`up`**:
    - create the network `mmz-tracking` if missing;
    - run the server:

      ```bash
      docker run -d --name mlflow --restart unless-stopped --network mmz-tracking \
        -p 127.0.0.1:5000:5000 -v "$HOME/mlflow:/data" ghcr.io/mlflow/mlflow:${MLFLOW_TAG:-v3.17.1} \
        mlflow server --host 0.0.0.0 --port 5000 --backend-store-uri sqlite:////data/mlflow.db \
        --artifacts-destination /data/artifacts --allowed-hosts <localhost, 127.0.0.1 and mlflow, with ports>
      ```

    - verify the `--allowed-hosts` value syntax against `mlflow server --help` of that tag (research R2, open item 1).
  - **`down`, `status`, `logs`**: `status` prints the container state, `curl -fsS http://127.0.0.1:5000/health` and the server version.
  - **`backup`**:
    - online SQLite backup via `docker exec mlflow python -c "import sqlite3; s=sqlite3.connect('/data/mlflow.db'); d=sqlite3.connect('/data/backup.db'); s.backup(d)"`;
    - move it plus a tar of `artifacts/` to `~/mlflow-backups/$(date +%F)/`;
    - keep the newest 14.
  - **`restore DIR`**: stop, replace `mlflow.db` and `artifacts/`, start.
  - **`upgrade TAG`**: backup, stop, run `mlflow db upgrade sqlite:////data/mlflow.db` with the new tag, then start with the new tag.
  - **`pull-backup`** (laptop): rsync the newest backup from `$SPARK_HOST` to `~/mlflow-backups/`.
  - **`tunnel`** (laptop): `ssh -N -L 5000:127.0.0.1:5000 "$SPARK_HOST"`.
  - **Environment**: read `SPARK_HOST` from `.env` the way `train_span.sh` does. Never configure an assistant, gateway or LLM key (research R10).
- [X] T029 [P] [US3] Write `scripts/spark/mlflow/README.md`:
  - one-time setup on the Spark, and the crontab line for the nightly `mlflow.sh backup`;
  - laptop tunnel and `.env`;
  - upgrade procedure, with "check https://osv.dev/list?ecosystem=PyPI&q=mlflow before upgrading";
  - restore drill.
- [X] T030 [P] [US3] Implement `src/mobility_model_zoo/tracking/config.py`.
  - **URI lookup**: `tracking_uri()` returns `MLFLOW_TRACKING_URI` from `os.environ`. If unset, it reads only `MLFLOW_*` keys with `dotenv.dotenv_values` from `.env` in the cwd, then at the repository root. It never mutates `os.environ` except to copy the found `MLFLOW_*` keys.
  - **`enabled()`**: false when no URI is set or `mlflow` is not importable.
  - **Short retries**: `apply_client_defaults()` sets `MLFLOW_HTTP_REQUEST_MAX_RETRIES=2` and `MLFLOW_HTTP_REQUEST_TIMEOUT=10` only when they are unset (research R5).
  - **Display**: `uri_host()` returns only the host and port for sidecars and status.
  - **Lazy imports**: python-dotenv and mlflow are imported lazily.
- [X] T031 [P] [US3] Implement `src/mobility_model_zoo/tracking/guard.py` per [contracts/tracking.md](contracts/tracking.md):
  - **Keys**: match `^[a-z0-9_./-]{1,120}$`.
  - **Tags**: only the `mmz.*` allow-list from the contract table, plus `mlflow.*` system tags. `mlflow.source.name` is reduced to a repo-relative path or dropped.
  - **Params**: numbers, booleans, or strings of at most 120 characters with no line break and at most three spaces. Home-directory paths are rewritten to repo-relative or `$MMZ_DATA/...`, or refused.
  - **Metrics**: finite numbers only.
  - **Artifacts**: only the allow-listed names and kinds (`profile.json`, `config/<name>.yaml` from `configs/`, `span_config.json` with `data/` paths reduced to file names, `report.json`, `summary.json`, `summary.md`, `quality.json`, `performance.json`), each at most 1 MB. Always refused: `*.safetensors`, `*.bin`, `*.joblib`, `*.tflite`, `*.npz`, `*.keras`, `*.h5`, `*.jsonl`, and anything under `data/` or `$MMZ_DATA` other than the allowed files.
  - **Outcome**: `check_*` functions return the cleaned value or raise `GuardRefused`. The module flag `STRICT` decides whether callers re-raise (tests) or drop with a warning (runtime).
- [X] T032 [US3] Implement `src/mobility_model_zoo/tracking/client.py`: a `TrackedRun` class built on `mlflow.tracking.MlflowClient`.
  - **Calls**: synchronous, one `log_batch` per `log_step`.
  - **Circuit breaker**: on the first `MlflowException`, `requests` connection error or timeout, set `degraded=True`, warn once, and turn every later call into a no-op.
  - **Counting**: count dropped values, from the guard and the breaker.
  - **End of run**: set status `FINISHED`, `FAILED` (exception) or `KILLED` (KeyboardInterrupt).
  - **Sidecar**: write `tracking.json` to `out_dir` with `tracking_uri_host`, `experiment`, `run_id`, `complete`, `dropped`, `warnings`, as in data-model.md "TrackingSidecar".
  - **System metrics**: enable them through `mlflow.enable_system_metrics_logging` when `psutil` is importable and `MMZ_TRACKING_SYSTEM_METRICS` is not `0`.
  - **Inputs**: log a dataset input as `mlflow.entities.Dataset(name=f"{id}@{version}", digest=sha256[:16], source_type="zoo", source=<repo path>, profile=json.dumps({"counts":…, "distribution":…}))` with an `InputTag("mlflow.data.context", context)`.
- [X] T033 [US3] Implement the public API in `src/mobility_model_zoo/tracking/__init__.py`:
  - `EXPERIMENTS` (the eight names from contracts/tracking.md) and `STRICT = False`.
  - `run(experiment, name, task, config_path=None, inputs=(), out_dir=None, system_metrics=False, tags=None)`, a context manager.
    - **No tracking URI**: it yields a no-op object with the same methods (`log_step`, `log_final`, `log_params`, `log_artifact`, `set_tag`) and writes no sidecar.
    - **With a URI**: it sets `mmz.git_commit` (`git rev-parse HEAD`), `mmz.git_clean` (`git status --porcelain` empty), `mmz.hardware` (`MMZ_HARDWARE` env or the hostname mapped through a small table, e.g. `spark*` → `dgx-spark`), `mmz.task` and `mmz.topic`, and flattens `config_path` YAML into params with `.` separators.
  - `data_ref(id, version, context)` resolves the `InventoryRow` through `datasets.inventory.collect` (cached). When it cannot, it sets the tag `mmz.input_unresolved=<id>@<version>` and warns.
- [X] T034 [US3] Implement `src/mobility_model_zoo/tracking/publish.py` (`publish(rows, dry_run=False, profile=False)`):
  - **Lookup**: for each row, search the `datasets` experiment with `tags.mmz.id = '<id>' and tags.mmz.version = '<version>'`.
  - **Not found**: create a run with name `<id>@<version>`, the tags `mmz.kind`, `mmz.topic`, `mmz.id`, `mmz.version`, `mmz.sha256`, `mmz.frozen_at`, `mmz.permitted_use` and `mmz.licence`, the metrics `size_mb`, `files`, `count.<dimension>` and `dist.<dimension>.<value>` (values sanitised to the key pattern), and the dataset input with context `inventory`.
  - **Same `mmz.sha256`**: update the metrics of the existing run.
  - **Different hash**: create a new run and tag the old run `mmz.superseded_by=<new run id>`.
  - **Register-only rows** (`version="register"`, no hash): update the `register` run in place. When a row with a real version of the same id is created, tag the `register` run `mmz.superseded_by`.
  - **Dry run**: with a URI, look up read-only; without one, print every row as `create` and say no server was asked (exit 0).
  - **`profile=True`**: attach `profile.json` (counts and distributions only).
  - **Return**: one action (`create`, `update` or `supersede`) per row.
  - **Errors**: no circuit breaker here. Publishing is the command's purpose, so connection errors raise and map to exit 8.
- [X] T035 [US3] Add the `publish [--topic] [--kind] [--dry-run] [--profile]` command to `src/mobility_model_zoo/datasets/cli.py`. Create `src/mobility_model_zoo/tracking/cli.py` with `status` (URI host, server version from `/version`, experiments with run counts, client installed; exit 0 or 8) and `audit`. Mount the `tracking` group in `src/mobility_model_zoo/release/cli.py` next to `_mount_data`, as `_mount_tracking()`, importing lazily so `zoo --help` works without the extra.
- [X] T036 [US3] Implement `src/mobility_model_zoo/tracking/audit.py` (`zoo tracking audit [--experiment] [--json]`):
  - **Scan**: iterate all runs of the given or all experiments; re-apply the guard rules to every param, tag and metric key. Download each text artifact (`.json`, `.yaml`, `.md`) into a temp dir and run, over params, tags and artifact text, the detectors that `compliance.release_checks.scan_publication` uses:
    - `compliance.scan.pii(text, allow)`, with `allow = compliance.release_checks.contact_allowlist(<register>.controller())`;
    - when the snapshot corpus is on this machine, `compliance.scan.overlap_spans(text, <CorpusIndex>, VERBATIM_MAX_WORDS)` to catch verbatim source text. Otherwise print "verbatim check skipped (no corpus here)".
  - **Principle XI**: flag any param or tag value containing `claude` (case-insensitive) under a key that names a labeler, teacher, judge or model.
  - **Output**: one line per finding (experiment, run id, key; value truncated to 20 characters).
  - **Exit codes**: 0 clean, 7 findings, 8 server.
- [X] T037 [P] [US3] Write tests with a fake transport (done with MLflow's in-process file store instead of a fake, `tests/tracking/tracking_helpers.py`: the real client API without a server; the breaker test patches the client to fail) (patch `MlflowClient` with an in-memory fake class in `tests/tracking/fakes.py`):
  - `tests/tracking/test_config_noop.py`: no URI → no mlflow import (`sys.modules` check), no sidecar; `.env` lookup reads only `MLFLOW_*`.
  - `tests/tracking/test_guard.py`: every allow and deny rule in contracts/tracking.md, including prose params, home paths, weight files, a 1.1 MB artifact and unknown tags.
  - `tests/tracking/test_client_breaker.py`: the fake raises on the third call → the run completes, the sidecar has `complete: false` and `dropped > 0`; `KeyboardInterrupt` → `KILLED`.
  - `tests/tracking/test_publish.py`: create, update, supersede and dry-run.
  - `tests/tracking/test_audit.py`: a seeded e-mail address in a tag and a `claude` teacher param are both found; a clean store exits 0.
  - `tests/tracking/test_import_boundary.py` (FR-025): import every module under `mobility_model_zoo.release` and `mobility_model_zoo.compliance`, then assert that neither `mobility_model_zoo.tracking.client` nor `mlflow` is in `sys.modules`. No gate may read the store.
- [X] T038 [US3] Write the slow integration test `tests/integration/test_tracking_server.py` (`@pytest.mark.slow`).
  - **Server**: start `uvx --from mlflow==3.17.1 mlflow server --host 127.0.0.1 --port <free> --backend-store-uri sqlite:///<tmp>/m.db --artifacts-destination <tmp>/a` and wait for `/health`.
  - **Steps**: `zoo data publish` on the T018 fixtures twice (creates, then updates); one `tracking.run` with three steps and a dataset input; search `datasets.name = '<id>@<version>'` finds the run; `zoo tracking audit` exits 0.
  - **Open item 2**: assert that a 16-character digest round-trips (research R9).
- [ ] T039 [US3] **(Spark)** Owner task, following quickstart §3:
  - run `mlflow.sh up` and confirm the network and host checks: LAN `curl` fails; `Host: evil.example` gets 403; the `mlflow` host from a container on `mmz-tracking` is accepted (open item 1);
  - install the crontab backup;
  - run `mlflow.sh backup` and `mlflow.sh restore` once and record the time in `scripts/spark/mlflow/README.md` (SC-009);
  - run `zoo data publish --profile` from the laptop.

**Checkpoint**: the server runs, data versions are browsable in MLflow, and the store audit is clean.

---

## Phase 6: User Story 4 - Follow a training run live (Priority: P2)

**Goal**: training runs on the Spark appear live with config, metrics per epoch, system metrics and final status. A lost server never harms a run.

**Independent Test**: [quickstart.md](quickstart.md) §5. A span candidate trains on the Spark with metrics visible in the browser. Stopping the server mid-run still finishes training with a complete `span_config.json` and `tracking.json` `complete: false`. The overhead is under 2 %.

### Implementation for User Story 4

- [ ] T040 [US4] Integrate tracking into `span/train.py:train_candidate` (`src/mobility_model_zoo/productdev/jtbd/span/train.py`).
  - **Run**: wrap the training in `tracking.run(experiment="productdev/jtbd-span", name=<candidate name>, task="jtbd-span", config_path=<recipe path>, inputs=[data_ref("span-train", <dataset name from span_config meta>, "training")], out_dir=out, system_metrics=True)`.
  - **Per epoch**: call `log_step(epoch, entry)` with the `history` entry minus `epoch`.
  - **At the end**: call `log_final({"best_epoch": …, "score": …})`, then `log_artifact(out / "span_config.json")`. Set tags `mmz.candidate` and `mmz.training_set`.
  - **Run id**: store it in `span_config.json` under `tracking.run_id`, so that `tune` can continue the run.
  - **Without a URI**: the output files must be byte-identical to today. Assert this in a test.

  **Principle IV go/no-go**: this task is followed by T041 before any other integration.
- [ ] T041 [US4] **(Spark)** Owner task, following quickstart §5:
  - adapt `topics/productdev/scripts/spark/train_span.sh`: when `MLFLOW_TRACKING_URI_CONTAINER` is set in the sourced `.env`, add `--network mmz-tracking -e MLFLOW_TRACKING_URI="$MLFLOW_TRACKING_URI_CONTAINER"` to `docker run` (mind the quoting inside the `ssh` string) and install `"/work[jtbd,tracking]"`. The script must not contain the address itself (FR-010). Also fix the stale `scripts/spark/...` path in its header comment;
  - train one candidate; stop the server mid-run with `mlflow.sh down`; confirm the run finishes and `tracking.json` says `complete: false`;
  - measure epoch time with and without tracking, which must be under 2 % (SC-006);
  - confirm GPU utilisation shows in system metrics on GB10 (open item 3).

  Record the results in `specs/017-mlflow-data-transparency/research.md` under "Open items". **If the run is harmed or the overhead exceeds 2 %, stop here and report to the owner** (plan: kill criterion).
- [ ] T042 [US4] Integrate tracking into `span/tune.py:tune_thresholds` (`src/mobility_model_zoo/productdev/jtbd/span/tune.py`):
  - reopen the run from `span_config.json` `tracking.run_id` when present, else start a new run with `mmz.kind=tune`;
  - log thresholds as params and the tuning metrics from `threshold_tuning.validation`.
- [ ] T043 [P] [US4] Implement the Keras callback `TrackingCallback(run)` in `src/mobility_model_zoo/tracking/keras.py`. `on_epoch_end(epoch, logs)` calls `run.log_step(epoch, logs)`. Import Keras lazily.
- [ ] T044 [US4] Integrate tracking into `edge/int8/keras_export.py`:
  - **Run**: in `train_main`/`train()`, open `tracking.run(experiment=<task experiment>, name=<model>-<version>, task=<task>, config_path=<config>, inputs=[data_ref(<dataset id>, <retrieved_at>, "training")], out_dir=<out>)`.
  - **Experiments**: `condition-monitoring/sound-anomaly` and `condition-monitoring/activity` for condmon, `security/can-ids` for `zoo-security can-ids mlp train`.
  - **Training**: add `TrackingCallback` to `fit_kwargs["callbacks"]` without replacing existing callbacks.
  - **After `export()`**: log the scalar fields of `<name>.report.json` as final metrics, and the report as an artifact.
- [ ] T045 [P] [US4] Write tests:
  - `tests/tracking/test_span_integration.py`: the tiny span model from `tests/span_helpers.py` with the fake transport; one step per epoch; the dataset input; `span_config.json` gets `tracking.run_id`; without a URI the outputs are byte-identical to a run on the unchanged code path.
  - `tests/tracking/test_keras_callback.py`: a fake run receives `on_epoch_end`. Skip it when TensorFlow is not installed.

**Checkpoint**: training is visible live and is robust to server loss.

---

## Phase 7: User Story 5 - Every run and model is linked to its data (Priority: P2)

**Goal**: evaluation and measurement runs of every task log their benchmark version. Past results are imported. Release records may name their run.

**Independent Test**: [quickstart.md](quickstart.md) §6.
- `zoo tracking import` twice → the second time is all `exists`.
- The imported metrics equal `zoo/models/*/results/<v>/quality.json`.
- Filtering `datasets.name = 'can-ids@can-ids-v3'` lists every can-ids training and evaluation run.
- A sandbox release record with `tracking.run_id` validates; an invalid id fails rule 1.

### Implementation for User Story 5

- [ ] T046 [P] [US5] Integrate the evaluation runs of jtbd in `src/mobility_model_zoo/productdev/jtbd/scoring.py` (`score_run`), `src/mobility_model_zoo/productdev/jtbd/perf.py` (`perf_span`) and `src/mobility_model_zoo/productdev/jtbd/span/results.py` (`write_results`):
  - experiment `productdev/jtbd-span`, `mmz.kind=evaluate` or `measure`;
  - tag `mmz.benchmark=<settings benchmark version>` and input `data_ref(<family>, <version>, "evaluation")`;
  - scores and perf numbers as final metrics.
- [ ] T047 [P] [US5] Integrate the cluster runs in `src/mobility_model_zoo/productdev/jtbd/cluster/tune.py` (`tune`) and `src/mobility_model_zoo/productdev/jtbd/cluster/score.py` (`score`):
  - experiment `productdev/jtbd-cluster`;
  - the grid as params, the scores as metrics;
  - input `data_ref("cluster", <benchmark_version>, "evaluation")`.
- [ ] T048 [P] [US5] Integrate the can-ids evaluation and measurement runs in `src/mobility_model_zoo/security/can_ids/evaluate.py` (`run`), `forest.py` (`cmd_evaluate`, behind `zoo-security can-ids forest evaluate`), `evaluate_v2.py` (the evaluation functions called by `release_export_v2`) and `measure.py` (`merge`):
  - experiment `security/can-ids`;
  - per-detector metrics prefixed `<detector>.`;
  - tags `mmz.benchmark` and `manifest_sha256` as `mmz.sha256` of the input;
  - input `data_ref("can-ids", <benchmark>, "evaluation")`;
  - per-board performance metrics for `measure`, with `mmz.kind=measure`.
- [ ] T061 [P] [US5] Integrate picket-forest *training* (FR-017, FR-019) in `src/mobility_model_zoo/security/can_ids/forest.py` (`cmd_export`, "train the final model and export C") and `src/mobility_model_zoo/security/can_ids/release_export_v2.py` (`export`, behind `zoo-security can-ids v2 export`):
  - experiment `security/can-ids`, `mmz.kind=train`, `mmz.model=picket-forest`;
  - forest settings from the command options and config as params;
  - training input `data_ref("can-ids", <benchmark>, "training")` plus the tag `mmz.training_set=<benchmark>:train+calibration`;
  - the export's scalar results as final metrics;
  - the export's `config.json` (`benchmark`, `manifest_sha256`, `code_commit`) as artifact `export-config.json`.

  Never the forest, C sources or test vectors (FR-023). Add a case to `tests/tracking/test_eval_integrations.py` that runs `cmd_export` on the existing small edge fixture with the fake transport and checks the training input and that no model file was logged.
- [ ] T049 [P] [US5] Integrate the HIL bench in `src/mobility_model_zoo/edge/bench/results.py` (`write_summary`):
  - experiment `edge/hil-bench`, `mmz.kind=measure` (no benchmark version; FR-019 measurement rule);
  - `perf.<board>.<model>.us_avg` and similar metrics, accuracy metrics, `mmz.hardware=<board>`, `mmz.model` and `mmz.model_version` when known;
  - when accuracy tests read an evaluation file (e.g. `<name>.eval.npz`), log its sha256 as a dataset input with context `evaluation`;
  - artifacts `summary.json` and `summary.md`;
  - logging only when a URI is set; the pytest plugin path in `bench/pytest_plugin.py` needs no change if `write_summary` is the single exit.
- [ ] T050 [US5] Implement `src/mobility_model_zoo/tracking/importer.py` and the `zoo tracking import [--model] [--dry-run]` command in `src/mobility_model_zoo/tracking/cli.py` (research R13).
  - **Sources**:
    - `zoo/models/*/results/<version>/{quality,performance}.json`; skip `sandbox-pipeline-tiny`;
    - the matching `releases/<version>.yaml`: `date`, `evaluation.benchmark`, `recipe.git_commit`, `usage`;
    - `topics/productdev/benchmarks/cluster-v1/decision.json`;
    - `topics/condition-monitoring/reports/{hum-fan,pace-cnn}/research-report.json` (scalar fields only).
  - **Each run**:
    - experiment by the model's task;
    - tags `mmz.imported=true`, `mmz.import_key=<model>@<version>` (or `cluster-v1/decision`), `mmz.model`, `mmz.model_version`, `mmz.benchmark`, `mmz.git_commit`;
    - `start_time` and `end_time` from the record date; metrics with that timestamp;
    - the benchmark dataset input; `quality.json` and `performance.json` as artifacts.
  - **No reconstruction**: missing values stay missing.
  - **Idempotent**: search `tags.mmz.import_key` first and print `exists`.
- [ ] T051 [US5] Copy `specs/017-mlflow-data-transparency/contracts/release/release-record.schema.json` over `src/mobility_model_zoo/release/schemas/release-record.schema.json` (byte-identical; it adds the optional `tracking` object with `run_id` pattern `^[0-9a-f]{32}$` and `experiment` pattern `^[a-z0-9_./-]{1,120}$`). Point `CONTRACTS` in `tests/release/test_schemas.py` at `specs/017-mlflow-data-transparency/contracts/release`, with the comment "latest owner of the format". Make `zoo release-verify` (and `zoo check` output) print `tracking.run_id` when present: find the evidence printout in `src/mobility_model_zoo/release/cli.py` or `gate.py`. The card and website must not show it.
- [ ] T052 [P] [US5] Write tests:
  - `tests/tracking/test_importer.py`: fixture results and release records → expected runs, tags and timestamps; a second import is all `exists`; `sandbox-pipeline-tiny` is skipped; metric values equal the JSON exactly (SC-005a).
  - `tests/release/test_schemas.py`: a record with a valid `tracking` passes; `run_id` of 31 hex characters fails rule 1; a record without `tracking` passes.
  - `tests/tracking/test_eval_integrations.py`: can-ids `run`, jtbd `score_run` and HIL `write_summary` log the benchmark input and tags with the fake transport.
- [ ] T053 [US5] **(Spark)** Owner task, following quickstart §6: run `zoo tracking import` (twice) and check a few imported runs against `quality.json`. Filter runs by `datasets.name` in the UI and confirm that data → runs and run → data both work.

**Checkpoint**: every result is traceable to its data in both directions, back to the first published model.

---

## Phase 8: User Story 6 - Compare candidates side by side (Priority: P3)

**Goal**: runs of one task compare cleanly, and runs on different benchmark versions are never silently mixed.

**Independent Test**: [quickstart.md](quickstart.md) §7. Compare three span runs in the UI: params and metrics line up, and `mmz.benchmark` is visible and filterable.

### Implementation for User Story 6

- [ ] T054 [US6] Add a consistency test `tests/tracking/test_tag_consistency.py`. For every integration (span train and tune, jtbd score and perf, cluster, can-ids evaluate and measure, Keras, HIL), run it with the fake transport and assert:
  - the same experiment name per task;
  - `mmz.task` and `mmz.topic` set;
  - `mmz.benchmark` set on every run with `mmz.kind=evaluate`; runs with `mmz.kind=measure` carry `mmz.hardware` instead;
  - `mmz.training_set` set on every training run;
  - metric names stable across two runs of the same command.
- [ ] T055 [US6] Write the comparison guide section in `docs/tracking.md` ("Compare candidates"): the saved filter `tags.mmz.benchmark = 'pilot-v2'`, which columns to pin, and why runs on different benchmark versions must not be compared (constitution VIII).

**Checkpoint**: all user stories are functional.

---

## Phase 9: Polish & Cross-Cutting Concerns

- [ ] T056 [P] Add the owner decision `D-tracking-store` to `compliance/decisions.yaml`, following the existing entry format:
  - **Location**: the owner's DGX Spark, DE.
  - **Content**: metrics, hashes and metadata; no personal data, no dataset content.
  - **Access**: owner only, via SSH.
  - **Retention**: kept with the project; backups 14 days.
  - **Principle XI**: no assistant or LLM on the server.

  Add one paragraph on the tracking store to the "Technical and organisational measures" text of `src/mobility_model_zoo/compliance/templates/record-of-processing.md.j2`. Run `uv run zoo compliance render` and commit the re-rendered `docs/compliance/record-of-processing.md`, so that `zoo compliance check --ci` passes.
- [ ] T057 [P] Write `docs/tracking.md` (owner guide, plain English):
  - what lives where (repository = truth, MLflow = lab notebook);
  - tunnel and `.env`;
  - the commands from contracts/cli.md with one example each;
  - the privacy rules (what may enter the store);
  - backup, restore and upgrade (link `scripts/spark/mlflow/README.md`);
  - security notes (loopback only, close the tunnel, check OSV before upgrading);
  - the "Compare candidates" section from T055.

  Link it from `README.md` with a short "Data and runs overview" section under "How the zoo is organized".
- [ ] T058 [P] Add `zoo data stats|history|diff|publish` and `zoo tracking …` to the command lists in `README.md` ("Quick commands per topic") and to `docs/layout.md` where packages are listed (`datasets/inventory`, `tracking`).
- [ ] T059 Run the full local checks:
  - `uv run ruff check . && uv run ruff format --check .`
  - `uv run pytest` (no `MLFLOW_TRACKING_URI`)
  - `uv run pytest -m slow tests/integration/test_tracking_server.py`
  - `./scripts/check_install_size.sh`
  - `uv run zoo validate --all`
  - `uv run zoo compliance check --ci`
  - `uv run reuse lint`

  Fix every finding (SC-008).
- [ ] T060 **(Spark)** Final owner pass:
  - run `zoo tracking audit` against the real store; it must exit 0 (SC-007);
  - walk through [quickstart.md](quickstart.md) §1 to §8 and tick off SC-001 to SC-010;
  - note any deviation in `specs/017-mlflow-data-transparency/research.md`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none.
- **Foundational (Phase 2)**: depends on T004 and blocks all stories.
- **US1 (Phase 3)**: depends on Phase 2.
- **US2 (Phase 4)**: depends on T015 (collect) and T017 (stats command) from US1.
- **US3 (Phase 5)**:
  - T028 to T033 (server and tracking core) depend only on Phase 1 and can run in parallel with US1 and US2;
  - T034 to T036 (publish, CLI, audit) need T015 from US1.
- **US4 (Phase 6)**: depends on T030 to T033. T041 (Spark go/no-go) blocks T042 to T044 and all of US5's integrations.
- **US5 (Phase 7)**: depends on T041 passing; T050 and T051 need only T033 and T030.
- **US6 (Phase 8)**: depends on US4 and US5 integrations.
- **Polish (Phase 9)**: T056 to T058 any time after US3; T059 and T060 last.

### User Story Dependencies

- **US1**: independent; this is the MVP.
- **US2**: extends US1's rows with history and integrity.
- **US3**: independent of US2. It needs US1's `collect()` only for publishing.
- **US4**: needs US3's tracking core and server.
- **US5**: needs US3's core and US4's go/no-go.
- **US6**: needs US4 and US5.

### Within Each Story

- Collectors and readers before `collect()`; `collect()` before render and CLI.
- `config` and `guard` before `client`; `client` before the API; the API before integrations.
- Tests alongside each module. The story's checkpoint is reached only when its tests pass.

### Parallel Opportunities

- **Phase 1**: T002, T003, T004, T005, T006 after T001.
- **US1**: T010, T011, T012, T013, T014, T018 in parallel; then T015 → T016 → T017; T019 and T020 last.
- **US2**: T021, T022, T023 in parallel; T025 and T026 in parallel after them.
- **US3**: T028, T029, T030, T031 in parallel, also in parallel with US1 and US2.
- **US5**: T046, T047, T048, T049, T061 in parallel after the go/no-go.

## Parallel Example: User Story 1

```text
Task: "T010 [US1] third-party dataset collector in src/mobility_model_zoo/datasets/inventory/third_party.py"
Task: "T011 [US1] source collection collector in src/mobility_model_zoo/datasets/inventory/sources.py"
Task: "T012 [US1] benchmark readers in src/mobility_model_zoo/datasets/inventory/benchmarks.py"
Task: "T013 [US1] training set collector in src/mobility_model_zoo/datasets/inventory/training_sets.py"
Task: "T014 [US1] used_by resolution in src/mobility_model_zoo/datasets/inventory/used_by.py"
Task: "T018 [US1] fixtures under tests/fixtures/inventory/"
```

## Parallel Example: User Story 3 (alongside US1)

```text
Task: "T028 [US3] scripts/spark/mlflow/mlflow.sh"
Task: "T030 [US3] src/mobility_model_zoo/tracking/config.py"
Task: "T031 [US3] src/mobility_model_zoo/tracking/guard.py"
```

## Implementation Strategy

### MVP First (US1 + US2, no server)

1. Phase 1 and Phase 2.
2. US1: `zoo data stats`. **Stop and validate** with quickstart §1. This already answers the owner's main question.
3. US2: history, diff and integrity. Validate with quickstart §2.
4. Merge-ready on its own. Nothing needs the Spark.

### Incremental Delivery

1. **MVP**: the overview (US1 + US2).
2. **US3**: the server and the `datasets` experiment. The owner sees the data in the browser.
3. **US4**: span training live → **go/no-go T041** → Keras tasks.
4. **US5**: evaluations, import, release link.
5. **US6**: consistency and the guide.

Each step leaves `main` working, and CI stays green with tracking off.

### Notes

- Never edit a frozen manifest to make an integrity check pass (constitution IX). Report it instead.
- No test or command may put dataset content into output or the store (FR-008, FR-024).
- Without `MLFLOW_TRACKING_URI` every existing command must behave byte-identically (SC-008).
- Commit after each task or logical group, with messages prefixed `017:`.
