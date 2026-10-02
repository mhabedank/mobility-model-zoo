# Quickstart: validating feature 004

Commands and exit codes: [contracts/cli.md](contracts/cli.md). Entities: [data-model.md](data-model.md). Scenarios 1–3 run now, before the pilot finishes; scenarios 4–9 need the pilot's `decision.json`.

## Prerequisites

- `uv sync --extra jtbd --extra release`
- For scenarios 4+: frozen `pilot-v1` (or the final pilot version) with `data/analysis/decision.json`; DGX Spark reachable; new OpenRouter key with a USD 20 limit if the recommended teacher is hosted.

## 1. Inference package on the base install

```bash
uv run pytest tests/unit/span tests/integration/test_span_end_to_end.py
```

Expected: all pass. The end-to-end test uses the tiny random fixture model: `extract` returns schema-valid `jtbd-span-v1`, failed dimensions are absent, `quote == text[start:end]`, and a fresh environment with only the base dependencies imports `mobility_model_zoo.productdev.jtbd.span`.

## 2. Harness accepts a span run

```bash
uv run jtbd span label --model-dir tests/fixtures/span/tiny --split main --config tests/fixtures/span/bench.yaml --candidate-change "fixture"
uv run jtbd check --run <run_id> --config tests/fixtures/span/bench.yaml
uv run jtbd score --run <run_id> --config tests/fixtures/span/bench.yaml
```

Expected: exit 0; the score file lists non-produced dimensions as `not_produced` and contains `comparison_composite` with its dimension set. A fourth `span label` on a fixture with cap 3 exits 1.

## 3. Training corpus guards

```bash
uv run jtbd corpus autochunk --config configs/productdev/jtbd/span-train-v1.yaml --map <map.yaml> --exclude-benchmark configs/productdev/jtbd/pilot-v1.yaml
uv run jtbd corpus redact --config configs/productdev/jtbd/span-train-v1.yaml
uv run jtbd corpus review-sample --config configs/productdev/jtbd/span-train-v1.yaml --seed 20261002
uv run jtbd corpus redact-check --config configs/productdev/jtbd/span-train-v1.yaml
uv run jtbd span data-check --config configs/productdev/jtbd/span-train-v1.yaml
```

Expected: a map entry that reuses a benchmark snapshot (or its origin URL) is refused with exit 1; after review of the sample, `redact-check` and `data-check` exit 0, and `provenance.json` shows about 1,000 chunks, zero shared or spike sources and the composition against its targets.

## 4. Teacher guard and labeling (after the pilot)

```bash
uv run jtbd label --role teacher --model <not recommended> --split train --config configs/productdev/jtbd/span-train-v1.yaml   # exit 1
uv run jtbd budget --estimate --model <recommended> --chunks 1000
uv run jtbd label --role teacher --model <recommended> --split train --config configs/productdev/jtbd/span-train-v1.yaml
uv run jtbd span build-rows --run <teacher run> --config configs/productdev/jtbd/span-train-v1.yaml
uv run jtbd span freeze-data --config configs/productdev/jtbd/span-train-v1.yaml
```

Expected: the non-recommended model is refused; `rows.stats.json` reports repaired and dropped items and the validation rows (about 10% of snapshots).

## 5. Train, tune, evaluate (Spark)

```bash
scripts/spark/train_span.sh c1          # runs `jtbd span train` in the container
uv run jtbd span tune --model-dir <dir>
uv run jtbd span label --model-dir <dir> --split main --candidate-change "c1: recipe defaults"
uv run jtbd check --run <run_id> && uv run jtbd score --run <run_id>
```

Expected: `span train` refuses if the release bar was committed after the current commit; `candidates.json` lists `c1`; quotes 100% verbatim, schema 100% valid.

## 6. Speed on the reference VM

```bash
uv run jtbd perf --backend span --model-dir <dir> --hardware "ref-vm 8GB 4vCPU"   # for each candidate in candidates.json
uv run jtbd span select
```

Expected: `latency_9k_chars_s ≤ 10`, `peak_rss_mb ≤ 4096`, model hash equals the quality run's, for every candidate; the Pareto figure and points are written; `jtbd span select` marks one candidate or none. Then delete the VM and record its cost with `jtbd budget --add`.

## 7. Results and release bar

```bash
uv run jtbd span results --run <run_id> --perf <perf file> --version 0.1.0
uv run jtbd span release-check --version 0.1.0
```

Expected: exit 0 only if the comparison composite beats every zero-shot baseline, all checks pass and the budget is met. Otherwise stop here: the model is reported, not published.

## 8. Release (feature 003 pipeline)

```bash
uv run zoo init-model productdev-jtbd-span-xlmr
uv run zoo stage productdev-jtbd-span-xlmr 0.1.0 --from <dir>   # on the Spark
uv run zoo check productdev-jtbd-span-xlmr 0.1.0                 # online, all 14 rules pass
uv run zoo history-check                                          # exit 0, then make the repository public
git tag productdev-jtbd-span-xlmr/v0.1.0 && git push origin productdev-jtbd-span-xlmr/v0.1.0
```

Expected: verify workflow builds the preview; after the owner's approval the model is public under `0.1.0` (SC-001); no manual upload.

## 9. After publication

- On a clean CPU machine: install with the card's install line, run the card's usage example on example 1, compare with the card's output (SC-005).
- Reader test with `specs/003-model-zoo-hf-release/reader-test.md`: at least 6 of 7 correct (SC-004).
- `jtbd budget` for budget `span-xlmr-0.1.0`: total ≤ €20 (SC-007).
