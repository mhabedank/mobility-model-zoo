# Quickstart and validation: feature 017

How to prove each user story works. Commands follow [contracts/cli.md](contracts/cli.md). Entities follow [data-model.md](data-model.md).

## Prerequisites

- Python 3.12, `uv`, a checkout of this repository.
- **Stories 1 and 2**: nothing else. A populated `$MMZ_DATA` makes the measured columns appear.
- **Stories 3 to 6**: `uv` on the laptop (the server runs there through `uvx`). For Spark runs: SSH access to the DGX Spark (`SPARK_HOST` in `.env`), as for training today. Nothing is installed or started on the Spark besides the training run.

```bash
uv sync --extra release --extra edge            # overview only
uv sync --extra jtbd --extra release --extra edge --extra tracking   # with tracking
```

## 1. Overview without any server (US1, SC-001, SC-002)

```bash
unset MLFLOW_TRACKING_URI
uv run zoo data stats
uv run zoo data stats --topic security --kind benchmark --wide
uv run zoo data stats --use benchmark_only --json | jq length
MMZ_DATA=/nonexistent uv run zoo data stats      # rows say "not downloaded here", exit 0
```

Expected:
- **Rows**: every active entry of `topics/*/compliance/datasets.yaml` (6 security, 2 condition-monitoring), the productdev source collection, `span-train-v1` (only if `data/span-train-v1/frozen.json` exists here), and the benchmarks `pilot-v1`, `pilot-v2`, `cluster-v1`, `can-ids-v1`, `can-ids-v2`, `can-ids-v3`.
- **Counts**: `can-ids-v3` shows 281 captures with roles test 183, train 47, validation 28, out_of_scope 17, excluded 6. `cluster-v1` shows items dev 3395, test 6967, holdout 2133.
- **Speed**: the command returns in under one minute (SC-001).

## 2. History and comparison (US2, SC-003)

```bash
uv run zoo data history can-ids
uv run zoo data diff can-ids-v2 can-ids-v3 --members
uv run zoo data history can-train-and-test
```

Expected:
- **History**: `can-ids` lists v1 to v3 with freeze dates, commits and the `based_on` chain.
- **Diff**: the v2 → v3 diff shows 6 captures moved to `excluded` and the per-role deltas.
- **Register history**: shows the register edits with dates.

**Integrity check**: in a scratch copy, change one value in `topics/security/benchmarks/can-ids-v2/manifest.json`. `zoo data stats` now exits 7 and reports `mismatch` on `can-ids-v3` (`based_on` hash) and `changed-after-freeze` on `can-ids-v2`.

## 3. Server on the laptop (setup for US3 to US6, SC-009)

```bash
scripts/mlflow/mlflow.sh up
scripts/mlflow/mlflow.sh status                  # healthy, 3.17.1, listening on 127.0.0.1:5000 only
echo 'MLFLOW_TRACKING_URI=http://127.0.0.1:5000' >> .env
uv run zoo tracking status                       # exit 0, lists experiments
```

Checks:
- **No network exposure**: `lsof -nP -iTCP:5000 -sTCP:LISTEN` shows only `127.0.0.1:5000`.
- **Host header**: `curl -s -o /dev/null -w '%{http_code}' -H 'Host: evil.example' 'http://127.0.0.1:5000/api/2.0/mlflow/experiments/search?max_results=1'` returns 403. `/health` is exempt from the host check and always answers.
- **Backup and restore**: `mlflow.sh down` writes a backup to `$MMZ_TRACKING_BACKUP`; `mlflow.sh restore <that dir>` brings the same runs back in the UI. Time it: under 30 minutes (SC-009).

## 4. Data versions in MLflow (US3)

```bash
uv run zoo data publish --dry-run
uv run zoo data publish --profile
uv run zoo data publish                          # second run: only "update", no "create"
```

Then open `http://127.0.0.1:5000`, experiment `datasets`:
- **Entries**: one run per row of step 1.
- **Sorting**: possible by `size_mb` and `count.captures`.
- **Changed hash**: add a test row in a scratch branch with a changed manifest and publish. A new run appears and the old one carries `mmz.superseded_by`.

## 5. Training runs (US4, SC-004, SC-006)

**On the Spark, offline** (`MMZ_TRACKING_OFFLINE=1` in the laptop's `.env`, which `train_span.sh` passes into the container):

```bash
topics/productdev/scripts/spark/train_span.sh c1
scripts/spark/tracking-pull.sh                   # after one or two epochs
scripts/spark/tracking-pull.sh                   # again after the run ends
```

- **First sync**: in `productdev/jtbd-span`, the run appears as `RUNNING` with config params, `mmz.git_commit`, `mmz.training_set=span-train-v1`, `mmz.hardware=dgx-spark`, the epochs so far and system metrics with GPU utilisation (open item 3). The pull plus sync take under two minutes (SC-004).
- **Second sync**: `updated N` with only the new epochs; the run is `FINISHED` with the run's own end time. A third sync prints `unchanged`.
- **Files**: `data/models/span-xlmr-c1/` on the Spark contains no tracking file; the log sits in `data/models/span-xlmr-c1.tracking/`.
- **Overhead**: compare epoch time with and without `MMZ_TRACKING_OFFLINE` on the same candidate. The difference must be under 2 % (SC-006).

**On the laptop, live** (a tiny span run or any short training with `MLFLOW_TRACKING_URI` set): metrics appear within a minute. Stop the server mid-run with `mlflow.sh down`: the training finishes, its result files are complete, and `tracking.json` says `complete: false` with one warning in the log.

## 6. Run ↔ data links and import (US5, FR-028, SC-005, SC-005a)

```bash
uv run zoo tracking import --dry-run
uv run zoo tracking import
uv run zoo tracking import                       # second time: all "exists"
```

- **Imported runs**: in `productdev/jtbd-span`, runs tagged `mmz.imported=true` exist for scout-large 0.1.0 to 0.1.3. In `security/can-ids` they exist for picket-forest 0.2.0 and 0.2.1. Their metrics equal `zoo/models/*/results/<v>/quality.json` exactly.
- **Run → data**: a run shows its dataset inputs.
- **Data → runs**: filter the run table with `datasets.name = 'can-ids@can-ids-v3'`. It lists every training and evaluation run on that benchmark.
- **Release link**: add `tracking: {run_id: <id>}` to a sandbox release record. `zoo validate --all` passes, and an invalid id fails rule 1.

## 7. Comparison (US6)

In the browser, select two or more `productdev/jtbd-span` runs and click Compare. Params and metrics line up, and `mmz.benchmark` is shown so that runs on different benchmark versions can be filtered apart.

## 8. Privacy and CI (SC-007, SC-008)

```bash
uv run zoo tracking audit                        # exit 0, no findings
unset MLFLOW_TRACKING_URI MMZ_TRACKING_OFFLINE && uv run pytest   # full suite unchanged
./scripts/check_install_size.sh                  # edge install size unchanged
uv run pytest -m slow tests/integration/test_tracking_server.py   # real server round trip
```
