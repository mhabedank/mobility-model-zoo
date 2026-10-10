# CI with real boards

## What runs where

| Workflow | Runner | Content |
|---|---|---|
| `ci.yml` | GitHub-hosted | job `checks` on every pull request (ruff, repository-wide tests, `zoo validate`, compliance check); job `test`: the tests of the areas a pull request touches; job `edge-sim`: HIL suite against simulated boards; job `edge-qemu`: HIL suite on the ESP32 firmware in QEMU. `edge-sim` and `edge-qemu` run only when edge code, firmware or `hil/` change. Pushes to `main` run everything. The mapping from paths to tests is in `scripts/ci/select_tests.py` |
| `firmware.yml` | GitHub-hosted | firmware build for all targets with a size overview (on changes of `firmware/`, `hil/`, `src/mobility_model_zoo/edge/`) |
| `hil.yml` | **self-hosted, label `hil`** | `uv run edge run --parallel --slow` on all connected boards, nightly and manually; runs only when the repository variable `HIL_RUNNER_ENABLED` is `true`, otherwise the job is skipped |

These workflows are being added in feature 005.

## Setting up the self-hosted runner on the HIL host

1. Prepare the host: `sudo ./hil/setup-host.sh` (dialout, udev rule `hil/99-mmz-edge.rules`,
   uhubctl) and keep `hil/boards.yaml` up to date with the real boards (`uv run edge discover`,
   then `uv run edge list`).
2. GitHub → *Settings → Actions → Runners → New self-hosted runner*. Follow the instructions and
   give the additional label `hil` during `config.sh`. Install the runner as a service
   (`sudo ./svc.sh install && sudo ./svc.sh start`) and add the service user to the group
   `dialout`.
3. Set the repository variable `HIL_RUNNER_ENABLED` to `true`
   (*Settings → Secrets and variables → Actions → Variables*). Without it, `hil.yml` skips its job.
4. Optionally use the same lock directory for humans and CI, so that an interactive test and a
   CI run never share the same board:
   `lab: {lock_dir: /var/lock/mmz-edge}` in `hil/boards.yaml`.
5. *Actions → hil → Run workflow* starts a run, optionally with a board list and smoke mode.

## Baseline / performance regressions

After a good run, check in `results/hil/summary.json` as `hil/baseline.json`. From then on,
`test_benchmark` fails as soon as a model gets more than 25 % slower on a board
(`--tolerance`). Fixed upper limits per target and model are set in `hil/targets.yaml`:

```yaml
esp8266:
  budgets: {picket-mlp: 5000, pace-cnn: 1000000}   # microseconds
```

Budget keys are firmware model names: the bench reference models (`can_ids_mlp`, `sensor_ae`,
`imu_gnss_cnn1d`) or trained models added through `MMZ_EDGE_MODELS`.

## Artifacts

Every run uploads `results/…`: `summary.md`, `summary.json`, `junit.xml`, `metrics/*.jsonl`
and, per board, the complete serial log (including all host commands). The summary
also appears directly on the workflow page.
