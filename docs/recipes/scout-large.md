# Recipe: scout-large

How the JTBD span extractor is built, measured and staged (feature 004). Every step is a command; every setting lives in a versioned config:

| What | Where |
|------|-------|
| Hyperparameters, seed, windows, threshold grid, selection rule, release bar | [`configs/productdev/jtbd/span-xlmr.yaml`](../../configs/productdev/jtbd/span-xlmr.yaml) |
| Training dataset: separation, redaction policy, validation split, minimum size, retention | [`configs/productdev/jtbd/span-train-v1.yaml`](../../configs/productdev/jtbd/span-train-v1.yaml) |
| Cash budget of the teacher labels and the reference VM | [`configs/productdev/jtbd/budget-span-xlmr.yaml`](../../configs/productdev/jtbd/budget-span-xlmr.yaml) |
| Fixed latency text | [`configs/productdev/jtbd/perf/interview-9k-de.txt`](../../configs/productdev/jtbd/perf/interview-9k-de.txt) |
| Model code | [`src/mobility_model_zoo/productdev/jtbd/span/`](../../src/mobility_model_zoo/productdev/jtbd/span/) |

`--config` is a global option of `jtbd` and goes before the subcommand. `TRAIN` stands for `configs/productdev/jtbd/span-train-v1.yaml`, `BENCH` for the pilot config of the final decision (`configs/productdev/jtbd/pilot-v1.yaml` unless the pilot reran).

## 0. Before anything is trained

The release bar and the selection rule in `span-xlmr.yaml` are committed before the first training run (Principle IV). `jtbd span train` refuses to run if the bar changed since that commit without an entry in `release_bar_changes` (date, change, rationale).

## 1. Training data

Training chunks come only from `training_allowed` snapshots that share no source (snapshot ID, normalized URL, content hash or supersession) with the benchmark's main or holdout chunks, and never from spike data.

```bash
uv run jtbd --config TRAIN corpus autochunk --map data/span-train-v1/autochunk-map.yaml \
    --train 1000 --eval 0 --seed 20261002            # --exclude-benchmark defaults to the config
uv run jtbd --config TRAIN corpus redact
uv run jtbd --config TRAIN corpus pii-review --model teacher-qwen3.8   # local model, every chunk
uv run jtbd --config TRAIN corpus redact-check
uv run jtbd --config TRAIN span data-check       # writes data/span-train-v1/analysis/provenance.json
uv run jtbd --config TRAIN freeze                # freezes guideline, schema and the training chunks
```

`autochunk` starts from an empty chunk directory. To add sources, fetch them once (`jtbd source fetch/register --permitted-uses training_allowed`), add them to the map, delete `data/span-train-v1/chunks/` and cut again before any review.

Redaction: every chunk passes the pattern redaction, then a local model on the development hardware lists personal data about private individuals and each finding is replaced by a placeholder, until the model finds nothing (spec FR-005 as amended 2026-10-06: no manual review). The text never leaves the local network for this step; every pass is stored for audit.

## 2. Teacher labels (after the pilot has decided)

Only the teacher the pilot recommends (`data/analysis/<version>/decision.json`) may label the training split, with the guideline and schema of the pilot's final decision.

```bash
uv run jtbd --config TRAIN budget --estimate --model <teacher> --chunks <n>
uv run jtbd --config TRAIN label --role teacher --backend <backend> --model <teacher> --split train
uv run jtbd --config TRAIN ensemble --split train          # only if the teacher is the ensemble
uv run jtbd --config TRAIN check --run <teacher run>
```

## 3. Rows

```bash
# Set `dimensions` in span-xlmr.yaml to the attribute dimensions that passed the pilot; commit.
uv run jtbd --config TRAIN span build-rows --run <teacher run>
uv run jtbd --config TRAIN span freeze-data
```

`build-rows` repairs near-miss teacher quotes with the frozen rule of `teacher-scoring.yaml`, keeps only the produced dimensions, and puts 10% of the snapshots (not chunks) into the validation split. Fewer than 600 usable rows: stop, the model is not trained.

## 4. Training and thresholds (DGX Spark)

```bash
scripts/spark/train_span.sh c1      # jtbd span train + jtbd span tune in the NVIDIA container
rsync -a "$SPARK_HOST":mobility-model-zoo/data/models/span-xlmr-c1 data/models/
```

The best epoch is chosen on the validation rows; thresholds are tuned on the validation rows only. `span_config.json` in the model directory records the hyperparameters, best epoch, validation scores, thresholds, the dataset hash and the recipe commit.

## 5. Evaluation on the benchmark

```bash
uv run jtbd --config BENCH span label --model-dir data/models/span-xlmr-c1 \
    --candidate-change "c1: recipe defaults"
uv run jtbd --config BENCH check --run <student run>
uv run jtbd --config BENCH score --run <student run>
```

At most three candidates are evaluated on the benchmark, each with its reason written down before the evaluation; all of them are reported. The holdout stays unused.

## 6. Speed and memory on the reference VM

On the reference machine (8 GB RAM, 4 vCPU, no GPU), for every evaluated candidate. For 0.1.0 this was a temporary Railway service with these limits (`deploy/railway-perf/`, staged by `scripts/railway/stage.sh`, results read back by `scripts/railway/collect.py`); the model files came from a branch of the private staging repository:

```bash
uv run jtbd --config BENCH perf --backend span --model-dir data/models/span-xlmr-<c> \
    --hardware "<provider type>, 8 GB RAM, 4 vCPU, no GPU"
```

Delete the machine afterwards and record its cost: `uv run jtbd --config TRAIN budget --add "reference VM" --eur <n>`.

## 7. Selection, results and release bar

```bash
uv run jtbd --config BENCH span select
uv run jtbd --config BENCH span results --run <selected run> --perf <perf file> --version 0.1.0
uv run jtbd --config BENCH span release-check --version 0.1.0
```

## 8. Staging

```bash
uv run zoo stage scout-large 0.1.0 --from data/models/span-xlmr-<selected>
```

Then the release follows `specs/003-model-zoo-hf-release/quickstart.md`.

## Retraining on a new base model

Change `base_encoder` (name and revision) in `span-xlmr.yaml`, commit it, and repeat steps 3 to 8 with a new candidate ID. The training data stays frozen; a new dataset version (`span-train-v2`) needs its own config and freeze. A retrained model is a new minor version.

## Numbers of version 0.1.0

Version 0.1.0 was trained at commit `4a7091a`, where this document was still named `docs/recipes/productdev-jtbd-span-xlmr.md` (the model was renamed `scout-large` on 2026-10-07, before its first publication); the release record points to that path at that commit.


- **Benchmark**: `pilot-v2` (guideline v2), 150 main chunks; reference: consensus of Claude (`claude-opus-5-5`) and `openai/gpt-5.4-mini`.
- **Training data** (`span-train-v1`): 1,100 chunks from 87 `training_allowed` snapshots (UK and Scottish parliamentary evidence, Irish and US hearings, Bundestag plenary protocols of the 20th Bundestag, CC BY citizen interviews and papers); 28% German, 72% English; 1,084 transcript and 16 paper chunks; 20% marked off-topic. Personal-data review changed 202 chunks (895 replacements).
- **Teacher**: `teacher-or-mimo-v2.6-pro` (the pilot's recommendation), all 1,100 chunks labeled, none excluded, EUR 3.55.
- **Rows**: 995 training and 105 validation rows (9 validation snapshots); 11,740 teacher items, 852 repaired by the frozen quote-repair rule (7.3%), 16 dropped.
- **Candidates evaluated on the benchmark**: one (`c1`, recipe defaults); no second candidate was needed.
- **Training**: XLM-RoBERTa-large, 8 epochs on the DGX Spark (about 5 minutes per epoch); best validation epoch 7 (validation score 0.743).
- **Thresholds** (tuned on the validation rows): unit 0.5, relevance 0.700.
- **Results**: comparison composite 0.723 (best zero-shot baseline 0.667); quotes, schema and consistency 100%; on the reference machine 8.1 s for the 9,240-character text, 2.5 GB peak memory, 21.6 chunks per minute.
