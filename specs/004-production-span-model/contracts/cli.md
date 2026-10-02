# CLI contract: `jtbd` additions for the span model

Exit codes follow the existing `jtbd` convention: 0 success, 1 check failed or refused, 2 usage or configuration error. `--config` is a global option and goes before the subcommand (`jtbd --config <file> span train …`); default `configs/productdev/jtbd/pilot-v1.yaml` unless stated.

## Changed commands

### `jtbd corpus autochunk … --exclude-benchmark <config>`

Refuses (exit 1, listing the snapshots and the matching rule) any snapshot mapped to `train` that is used by a main or holdout chunk of the given benchmark config, matched by snapshot ID, normalized origin URL or content hash, including superseded snapshots. Also refuses spike-chunk snapshots (data-model, Chunk). Writes into the data directory of `--config` (here `span-train-v1.yaml`).

### `jtbd corpus redact-check`

With `redaction.review: sampled` in the config: passes when every chunk passed the pattern redaction and the identifier scan, every chunk in the drawn sample and every chunk of an always-review source type has `manual_review_at`. `jtbd corpus review-sample --seed <n>` draws and prints the sample once and records it; redrawing is refused. Configs without `sampled` behave as before.

### `jtbd label --role teacher`

Allowed only with `--split train`. Refused (exit 1) if `analysis/decision.json` of the benchmark config is missing, if the model is not the recommended teacher (or a member of the recommended ensemble), or if the guideline or schema hash differs from the one of the pilot's final decision. Budget guard as for every paid run.

### `jtbd ensemble --split train`

Allowed when all members have complete `teacher` runs on the train split; writes a `teacher` ensemble run.

### `jtbd check --run <span run>`

Validates every `parsed/*.json` against `jtbd-span-v1` and checks `quote == text[start:end]` for every item.

### `jtbd score --run <span run>`

Scores produced dimensions only; non-produced dimensions appear as `"not_produced"` in the score file. Adds `comparison_composite` and the dimension set it uses.

### `jtbd perf --backend span --model-dir <dir> --hardware <label> [--text <file>]`

Runs in a child process with `torch.set_num_threads(vcpus)`. Records `load_time_s`, `latency_9k_chars_s` (median of 5 after one warm-up on `--text`, default `configs/productdev/jtbd/perf/interview-9k-de.txt`), `chunks_per_min` over the main split, `peak_rss_mb`, the hardware info and the SHA-256 of `model.safetensors`. Refuses (exit 1) if the hash differs from the quality run's `settings.model_sha256`.

## New commands: `jtbd span …`

| Command | Purpose | Main options | Refuses (exit 1) when |
|---------|---------|--------------|-----------------------|
| `span data-check` | Verify provenance of the training dataset; write `analysis/provenance.json` with composition | `--config span-train-v1.yaml` | any chunk not `training_allowed`, shared with the benchmark or holdout, from spike data, or not redaction-checked |
| `span build-rows` | Teacher run → `rows/rows.jsonl` with frozen quote repair and validation split by snapshot | `--run <teacher run>` | run is not role `teacher` on split `train`, or not complete |
| `span freeze-data` | Hash chunks and rows into `frozen.json`; write `retention.yaml` | | rows missing; already frozen with different content |
| `span train` | Train one candidate; write model files to `--out` | `--recipe span-xlmr.yaml --out <dir> [--device cuda]` | data not frozen; fewer than `min_usable_chunks` (600) rows; release bar not committed before the current commit, or changed since without a `release_bar_changes` entry; dimensions in the recipe differ from `decision.json` |
| `span tune` | Tune unit and relevance thresholds on validation rows; write them into `span_config.json` | `--model-dir <dir>` | |
| `span label` | Run the model on a benchmark split; write a `student` run with backend `span` | `--model-dir <dir> --split main --candidate-change "<text>"` | split is not `main` (the holdout stays unused); the candidate cap is reached; model already evaluated (same hash) |
| `span results` | Write the zoo results files for a version | `--run <student run> --perf <perf file> --version 0.1.0` | score or perf file missing; perf hash ≠ run hash |
| `span select` | Apply `selection.rule` to every candidate with a score and a perf file; print the ranking; write `selected: true` for the result | `--config span-train-v1.yaml` | a candidate lacks a score or perf file |
| `span release-check` | Evaluate the release bar from the results files; print each condition with pass or fail and every `release_bar_changes` entry | `--version 0.1.0` | any condition fails |

`span train` and `span label` record the git commit and refuse to run on a dirty working tree for files under `src/` and `configs/`.
