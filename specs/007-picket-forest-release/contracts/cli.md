# Contract: commands

Exit codes follow the `zoo` convention (`release/errors.py`): 0 ok, 1 check failed, 2 usage, 3 refused, 5 missing input, 6 external service.

## `security can-ids freeze [--benchmark can-ids-v1] [--data DIR]`

This command freezes the benchmark.

1. It reads the declared datasets from `$MMZ_DATA`, using the common frame format, and refuses datasets that are not downloaded (exit 5).
2. It hashes every capture and assigns roles from the protocol in [research R1–R2, R6](../research.md).
3. It writes `topics/security/benchmarks/can-ids-v1/manifest.json`.

Outcomes:

| Situation | Exit | Result |
|---|---|---|
| A duplicate group with different labels has no resolution | 1 | Names the captures; writes nothing |
| `manifest.json` already exists and its content would change | 3 | Refused (frozen; make a new version) |
| `manifest.json` already exists with identical content | 0 | No-op |

## `security can-ids evaluate DETECTOR --benchmark can-ids-v1 [--sets …] [--out DIR] [--report]`

- `DETECTOR` is `picket-forest`, one of the controls `ctrl-id-lookup|ctrl-timing-only|ctrl-forest-with-id|ctrl-shuffled`, one of the baselines `bl-mean-interval|bl-binning|bl-can-logic|bl-isolation-forest|bl-orig-<model>`, or `all`.
- It verifies every capture hash against the manifest before running (exit 1 on a mismatch, naming the capture).
- It trains per set on `train_01` and chooses thresholds and alarm points on validation captures only.
- It writes runs to `$MMZ_DATA/derived/can-ids-v1/runs/`.
- With `--report` it also writes `topics/security/reports/picket-forest/can-ids-v1/{report.md,metrics.json}` and `zoo/models/picket-forest/results/<version>/quality.json`.
- `--sets` limits the run, for a fast check. A report built from a partial run is marked partial and cannot feed the quality results.

## `security can-ids forest export|convert|testvectors` (changed)

- `export` trains the release model on `train_01` of all four sets and writes the staged files listed in [data-model.md](../data-model.md).
- `examples --out zoo/models/picket-forest/examples` (new) writes the synthetic examples ([research R8](../research.md)) with expected scores and alarms from the host scorer.

## `security can-ids measure [--target host|esp32-qemu|esp8266 -b BOARD] [--out FILE]`

- `host` times the host scorer over the synthetic examples.
- `esp32-qemu` builds the PlatformIO replay benchmark for ESP32, runs it in QEMU and reads the `PICKET_FOREST_RESULT` line and the image size report.
- `esp8266 -b BOARD` builds the same benchmark for the ESP8266 env, flashes the board from the inventory (for example the D1 mini) and reads the result line over serial.

It writes or merges performance metrics in the results format, with `origin` `host`, `emulator` or `real_board`.

## Gate changes (`zoo check`, `zoo build`)

| Rule | `runtime: mcu`, `engine: emlearn` |
|---|---|
| 12 | Builds the host scorer from the staged headers and the C sources at the recipe commit. Replays the first example. Compares scores (bit patterns) and alarm indices. |
| 13 | At least 3 examples; each `source` is synthetic or a dataset with `redistribution: allowed`. Online, replays every example as in rule 12. |
| 11 | Additionally rejects staged `*.npz` evaluation sets and any file of more than 5 MB except `model.joblib` |
| 15 | Unchanged: `latency_us`, `flash_kb`, `ram_kb` with origin and hardware; `experimental` may rely on host and emulator evidence |

The `engine: int8` path is unchanged.
