# Quickstart: validating the pace-cnn first release

Runnable scenarios that prove feature 021 end to end. Commands and formats are in [contracts/cli.md](contracts/cli.md) and [contracts/records.md](contracts/records.md). Expected results name the spec's success criteria.

## Prerequisites

- Python 3.12 with `uv`; `uv sync --extra edge --extra edge-train --extra edge-hw`.
- `MMZ_DATA` set (default `~/.cache/mobility-model-zoo/datasets`).
- `uv run zoo data download uci-har` succeeds, with the licence check passing.
- For V6: esp32-1 (LilyGO LoRa32) and esp8266-1 connected to the Mac; for the emulator run, Espressif QEMU on the PATH (as in CI `edge-qemu`).
- For V11 and V12: the owner's Hugging Face tokens and approvals ([research.md R18](research.md#r18-owner-steps-and-outward-facing-actions)).

## US1: measured candidate with an honest verdict

**V1. Freeze the benchmark.**

1. Run `uv run condmon activity freeze`, then run it a second time.
2. Run `uv run pytest tests/condition_monitoring/test_activity_benchmark.py`, which patches the benchmark constant's `validation_seed` and freezes again.

Expected:

- the first run writes `topics/condition-monitoring/benchmarks/uci-har-v1/manifest.json`, with 18/3/9 subjects and 2,947 test windows;
- the second run changes nothing;
- the freeze with the changed seed is refused with exit 3 (in the test).
- `grep` finds no subject number in the manifest.

**V2. Pre-registration is enforced.**

1. With `pace-cnn-criteria.yaml` modified but not committed, run `uv run condmon activity train --seed 0`.
2. After the commit, run it again.

Expected: the first run exits 3; after the commit it trains. The run report holds the criteria commit and SHA-256.

**V3. Five runs.**

`for s in 0 1 2 3 4; do uv run condmon activity train --seed $s; done`

Expected:

- five folders `seed-<n>` under `$MMZ_DATA/derived/pace-cnn/`;
- in each report, `tflite_interpreter_mismatches` is 0 over all 2,947 test windows (SC-001).

**V4. Evaluate.**

`uv run condmon activity evaluate --version 0.1.0`

Expected:

- `quality.json` passes the results schema;
- `evaluation.json` holds per-class F1, the confusion matrix, per-subject results without subject numbers and the seed spread;
- `verdict.json` says `experimental` and lists S5 as missed, plus every other missed criterion with its value (SC-008);
- running the command twice gives identical files.

**V5. Reproduce.** `uv run condmon activity reproduce`

Expected: "identical" (same `.npz` SHA-256), or the measured deviation written into `evaluation.json` (FR-013).

## US2: within budget on a real microcontroller

**V6. Bench runs**, in this order:

1. `MMZ_EDGE_MODELS=$MMZ_DATA/derived/pace-cnn/seed-0/pace-cnn.npz uv run edge run -b sim`
2. `… uv run edge --boards hil/qemu-boards.yaml run -b esp32-qemu --require-all`
3. `… uv run edge run -b esp32-1`
4. `… uv run edge run -b esp8266-1`

Expected:

- all HIL tests pass with pace-cnn in the catalogue;
- on esp32-1, every self-test vector and every example equals the host reference (SC-003);
- `test_benchmark` stays under the 100 ms budget on esp32-1, or the card reports the miss (SC-002).

**V7. Footprint and performance file.**

1. Run `uv run edge measure … -b esp32-1 --footprint model --model-version 0.1.0 --out esp32.json` (and the same for `esp32-qemu`, `esp8266-1` and `sim`).
2. Run `uv run edge performance --model pace-cnn --version 0.1.0 --reference esp32.json --extra qemu.json --extra esp8266.json --extra sim.json`.

Expected: `performance.json` passes the results schema; `flash_kb`, `ram_kb` and `latency_us` have `origin: real_board` and `hardware` naming esp32-1; the values are compared with 128 KB, 32 KB and 100 ms (SC-002).

**V8. Device sources stand alone.**

1. Run `uv run condmon activity export --version 0.1.0 --out /tmp/pace-cnn-0.1.0`.
2. Compile `c/*.c` with the host compiler and a small driver.
3. Feed `examples/*.json` through the compiled code.

Expected: outputs equal `expected` bit for bit; the folder matches the allow-list of [release-files.md](contracts/release-files.md); it contains no `*.eval.npz` and no dataset window.

## US3: a newcomer finds and uses the published model

**V9. Gate before staging.** `uv run zoo check pace-cnn 0.1.0 --offline`

Expected:

- open are only the rules that need staging or the Hub (1, 5, 12) and rule 16, which needs the owner's signoff (V10);
- rules 7 (with the confirmation of no Claude inputs), 9 (with the benchmark trace), 13, 15, 17 and 18 pass;
- card lint C-C2 passes.

**V10. Compliance.**

1. Run `uv run zoo compliance render`, then `scan-publish`.
2. The owner signs off.

Expected:

- `scan-publish` passes without a text snapshot for `uci-har`, with the exemption reason recorded;
- the rendered card shows the UCI HAR attribution text and the privacy note;
- after the signoff, `uv run zoo check pace-cnn 0.1.0 --offline` also passes rule 16 (SC-006).

**V11. Release pipeline.** These steps involve the owner.

1. Run `zoo init-model pace-cnn`. The `condition-monitoring` collection is created as private and its slug is in `zoo/topics.yaml`.
2. Run `zoo stage pace-cnn 0.1.0 --from /tmp/pace-cnn-0.1.0`.
3. Run the full `zoo check`; all 18 rules pass.
4. Merge the PR and push the tag `pace-cnn/v0.1.0`. release-verify builds the preview, and the card's topic link points to the collection.
5. The owner starts release-publish.

Expected: the public repo and the Hub tag `v0.1.0` exist, the collection is public and lists pace-cnn, and `zoo/MODELS.md` shows it as published.

**V12. Fresh-environment walkthrough (SC-004).** In a new folder, create a fresh Python 3.12 venv with `uv`, run the card's install line, then paste the card's host example. Time the run with a stopwatch.

Expected: six int8 scores are printed in at most 5 minutes, using only the card's steps.

**V13. Public surfaces (SC-005, SC-007).**

Expected:

- the website model page exists and shows status `experimental` and the missed criteria;
- the roadmap entry `pace-cnn` shows "delivered" with the publication date, on or before 2026-12-31;
- every number on the card appears in `quality.json` or `performance.json`.
