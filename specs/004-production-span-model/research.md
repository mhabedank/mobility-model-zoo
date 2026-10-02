# Research: Production span model, first public release

Phase 0 of [plan.md](plan.md). Each entry: decision, rationale, alternatives considered. Spike measurements (feature 002) inform the design choices below; none of them sets a threshold, release bar or decision rule (constitution, Technical Spikes).

## R1 Training corpus as its own dataset, outside the pilot benchmark

- **Decision**: The training chunks form a separate dataset `span-train-v1` with its own config `configs/productdev/jtbd/span-train-v1.yaml` and data directory `data/span-train-v1/` (chunks, runs, analysis). It shares the snapshot store, the source registry and the budget ledger with the pilot. Training chunks never enter the `pilot-v1` config.
- **Rationale**: `jtbd freeze` hashes the train chunks of a config into the frozen manifest (`freeze.py:99`), and `corpus split` overwrites every split (`split.py:47`). Adding about 1,000 training chunks to `pilot-v1` after it is frozen would break `verify_frozen` and block every later pilot command. The spike already used this pattern (`spike-v1.yaml` with `data/spike`).
- **Alternatives**: Add a `train` split to `pilot-v1` before freezing (rejected: the pilot is not finished, and it would tie the benchmark hash to training data that changes per model). One directory per model (rejected for now: the dataset is reusable by later JTBD models; versioned names allow `span-train-v2`).

## R2 Strict separation of training sources from benchmark and holdout sources

- **Decision**: `jtbd corpus autochunk` gets `--exclude-benchmark <config>`. A training snapshot is refused if it is used by any main or holdout chunk of that benchmark, matched three ways: same `snapshot_id`, same normalized origin URL (scheme, `www.`, trailing slash, query tracking parameters removed), or same content hash of the raw snapshot. Superseded snapshots count as the same source. A new command `jtbd span data-check` re-verifies this, plus `permitted_uses == training_allowed` for every training chunk and the absence of spike data, and writes `data/span-train-v1/analysis/provenance.json` (SC-006).
- **Rationale**: Today only `use: train` → `training_allowed` is enforced (`autochunk.py:94`); nothing compares against an existing benchmark. Without the check the benchmark could measure memorised text.
- **Alternatives**: Separate by source type or by publisher (rejected: too coarse, would waste good sources); manual review only (rejected: not repeatable).

## R3 Source acquisition and composition of about 1,000 chunks

- **Decision**: First use every stored `training_allowed` snapshot that is not excluded by R2, including the spike's training snapshots (the snapshots are not spike data; the spike's labels and chunks are, and are not used). Only then fetch new sources once, with `jtbd source fetch/register`, under the pilot's provenance rules. Chunks are cut with `autochunk` (1,400–5,800 characters, sentence boundaries), so roughly 3.5 million characters of source text are needed. Composition targets, checked by `jtbd span data-check` and reported, not enforced as hard gates: both German and English at least 30% each; at least 15% off-topic windows (the spike's relevance head was weak because nearly every chunk was relevant); every pilot sub-area represented; at least three source types.
- **Rationale**: Crawl once; quality over volume. The off-topic share addresses the measured weakness (2 of 35 irrelevant spike chunks) without using spike numbers as a rule.
- **Alternatives**: Reuse the spike's 180 chunks (forbidden: spike data); hand-picked selections like the pilot (rejected: about 1,000 chunks are too many to select by hand).

## R4 Redaction for the training corpus

- **Decision** (recorded in spec FR-005): Every training chunk goes through pattern redaction (`redact-v2`) and an automated identifier scan (e-mail, `@`-handles, phone numbers, URLs with user paths). Manual review covers a stratified 10% sample (at least 100 chunks) plus every chunk from forum and review sources, where usernames occur. The config declares `redaction.review: sampled`; `redact-check` accepts sampled review only for configs that declare it, and the pilot keeps full review.
- **Rationale**: The constitution requires identifiers to be removed before labeling; it does not prescribe full manual review. Reviewing 1,000 long chunks by hand would take days, while most sources (papers, parliamentary records, reports) carry no usernames. The spike used pattern redaction plus a spot check without findings.
- **Alternatives**: Full manual review (rejected: cost without matching benefit); no manual review (rejected: forum text is the high-risk part).

## R5 Teacher labeling of the training corpus

- **Decision**: A new run role `teacher`. `jtbd label --role teacher` is allowed only on split `train`, and only for the model recommended in the pilot's `decision.json` (`teacher_fitness.recommended`), with the guideline and schema versions of the pilot's final decision. If the recommendation is the ensemble, the four members label the training split as `teacher` runs and `jtbd ensemble --split train` combines them with the frozen teacher-scoring configuration. `jtbd budget --estimate` guards each paid run. Teacher labels are kept raw; quote repair (frozen rule from `teacher-scoring.yaml`) happens when training rows are built (R7), and the repair rate is recorded.
- **Rationale**: Makes FR-003 checkable by the tool instead of by discipline. Reuses the labeling runner, retries and manifests.
- **Alternatives**: Reuse role `teacher_candidate` on split `train` (rejected: nothing would stop a non-recommended candidate); label with all four members and pick later (rejected: picking after seeing results).

## R6 Model architecture

- **Decision**: The spike's unit classifier, rebuilt in the package: XLM-RoBERTa-large encoder (MIT); text split into sentences and clauses by the spike's regex; 512-token windows with 128-token overlap, built by hand; token states averaged across windows; heads for unit kind (`O/job/pain/gain`), BIO tokens (auxiliary loss only), relevance and one head per attribute dimension. A chunk is relevant when its best unit score reaches the relevance threshold. Heads exist only for attribute dimensions that passed the pilot; failed dimensions are neither trained nor output. The `--context` variant is not carried over.
- **Rationale**: The spec fixes the architecture (Assumptions). The context variant brought no gain in the spike, and fewer options mean fewer selection steps.
- **Alternatives**: XLM-RoBERTa-base (kept as fallback if the speed budget fails, see R12); a generative small model (out of scope, a later zoo model).

## R7 Training rows

- **Decision**: `jtbd span build-rows` reads the teacher run (or the train-split ensemble run), applies the frozen quote repair, aligns every item to units by character offsets (a unit takes the item that overlaps it most, if the overlap covers at least 50% of the unit or of the item, as in the spike) and writes `data/span-train-v1/rows/rows.jsonl` with `{chunk_id, snapshot_id, text, relevant, items[{span, kind, <passed attributes>}], split}`. Chunks without a valid teacher output are excluded and counted; relevant-but-empty chunks after repair are kept as relevant with no items only if the teacher marked them relevant with no items, otherwise excluded.
- **Rationale**: Same alignment as the spike, which worked; offsets avoid fuzzy matching at training time.
- **Alternatives**: Train on the SFT export format (rejected: built for chat models).

## R8 Training procedure, validation and selection

- **Decision**:
  - Split: 10% of training **snapshots** (not chunks) form the validation set, chosen with a fixed seed, so validation never shares a source with training.
  - Hyperparameters, recorded in `configs/productdev/jtbd/span-xlmr.yaml` and copied into the model's `span_config.json`: AdamW, lr 1.5e-5, weight decay 0.01, 10% linear warm-up, gradient clipping 1.0, batch 4, at most 8 epochs, seed `20261002`. Best epoch by validation score (item F1 plus mean attribute agreement, halved).
  - Thresholds: unit threshold from {0.2, 0.3, 0.4, 0.5, 0.6} and relevance threshold tuned on the validation set only (FR-010).
  - Benchmark evaluations are counted: each evaluated candidate is recorded in `data/span-train-v1/analysis/candidates.json`; at most three candidates may be evaluated on the benchmark, and all evaluated candidates are reported, not only the best (no selection on the benchmark).
- **Rationale**: Validation by snapshot prevents near-duplicate leakage; 10% of about 1,000 chunks gives about 100 validation chunks, against 20 in the spike. Recording the hyperparameters fixes a spike gap. Capping benchmark evaluations keeps the benchmark a measurement, not a tuning signal.
- **Alternatives**: Hyperparameter search (rejected: training runs take about an hour each, and a search on the validation set adds little at this scale); selecting thresholds on the benchmark (forbidden).

## R9 Training framework (deviation from Ludwig)

- **Decision**: Plain PyTorch with `transformers`, on the DGX Spark in the NVIDIA PyTorch container used by the spike (`nvcr.io/nvidia/pytorch:25.09-py3`), with `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`. Training code lives in the package; a thin shell wrapper runs it on the Spark.
- **Rationale**: Ludwig's encoder path offers sequence and token classification on fixed inputs; it cannot express unit-level classification over regex units pooled across overlapping windows, the per-dimension heads that depend on the pilot outcome, or the windowed inference the published model must reproduce exactly. Recorded under Complexity Tracking.
- **Alternatives**: Ludwig token classification with post-processing to units (rejected: the training objective would differ from the unit decision the model makes, and inference would need a second code path).

## R10 Model files and loading

- **Decision**: One flat directory, as `zoo stage` expects: `model.safetensors` (encoder and heads in one file), `config.json` (encoder config), tokenizer files (`tokenizer.json`, `tokenizer_config.json`, `sentencepiece.bpe.model` if written, `special_tokens_map.json`), and `span_config.json` ([contracts/model-files.md](contracts/model-files.md)). Weights stay in float32. `SpanExtractor.from_pretrained(repo_or_dir, revision=None, device="cpu")` uses `huggingface_hub.snapshot_download` for repository IDs and builds the encoder from `config.json` without downloading the base model. No `torch.load` of pickles.
- **Rationale**: The spike wrote `encoder/` plus a pickled `heads.pt`; a pickle in a public model is a security smell, and Hub tooling expects safetensors. Float32 keeps quality and speed runs on identical files (constitution, Resources & Cost Discipline) and fits the 4 GB budget (spike peak 2.3 GB).
- **Alternatives**: `PyTorchModelHubMixin` (rejected: it does not save tokenizer files and stores init kwargs, not the label sets); int8 dynamic quantization (deferred: only if R12 shows the speed budget fails, then measured again for quality with the same files).

## R11 Output format `jtbd-span-v1`

- **Decision**: `extract(text)` returns `{"output_format_version": "jtbd-span-v1", "relevant": bool, "relevance_probability": float, "dimensions": [...], "items": [{"kind", "quote", "start", "end", "score", <one key per produced attribute>}]}`. `dimensions` lists the attribute dimensions this model version produces. Schema: [contracts/span-output.schema.json](contracts/span-output.schema.json). No timing field in the output (it would make example outputs non-deterministic).
- **Rationale**: The release record already names `output_format_version: jtbd-span-v1`. Listing the produced dimensions makes FR-006 visible in every output. Removing the spike's `seconds` field keeps the gate's example outputs reproducible.
- **Alternatives**: Emit failed dimensions as `null` (rejected: FR-006 says absent, not empty).

## R12 Evaluation in the shared harness

- **Decision**:
  - New run backend `span` and role `student`. `jtbd span label --model-dir <dir> --config pilot-v1.yaml` runs the model on the benchmark's main split and writes a regular run directory (`manifest.json`, `parsed/<chunk>.json` in `jtbd-span-v1`), with `settings.dimensions` listing the produced dimensions.
  - `runs.py` loads `span` runs into `LocatedItem` objects with offsets as spans and `actor`/`statement` set to `None`; the LLM output schema (frozen, hashed) is not changed.
  - `jtbd check` validates `span` runs against `jtbd-span-v1` and still runs the verbatim check (quote equals `text[start:end]`).
  - `score_run` scores only produced dimensions; non-produced dimensions are reported as "not produced", never as 0 or as skipped-and-hidden.
  - **Comparison composite**: the composite over exactly the span model's dimensions (relevance, item matching, kind and the produced attributes) is computed for the span model, every pilot baseline, the teacher and the frontier-versus-frontier reference, from their existing score files. The release bar (FR-015) uses this composite. The full composite of the baselines is reported next to it.
- **Rationale**: The spike evaluated the span model outside the harness, with no run files or confidence intervals. Principle VIII needs the same harness. Comparing composites over different dimension sets would flatter the model that drops its hardest dimensions.
- **Alternatives**: Placeholder strings for actor and statement (rejected: they would pass schema checks dishonestly); relaxing the frozen LLM schema (rejected: changes the frozen schema hash).

## R13 Performance measurement on the reference hardware

- **Decision**: `jtbd perf --backend span --model-dir <dir>` runs the model in a child process with `torch.set_num_threads(<vcpus>)` and measures: load time; latency for the fixed 9,000-character text `configs/productdev/jtbd/perf/interview-9k-de.txt` (fictional, no personal data; median of 5 runs after one warm-up); throughput over all main chunks; peak memory as the maximum RSS of the child process (sampled from `/proc`, plus `ru_maxrss` as a cross-check). The reference VM is the pilot's (8 GB RAM, 4 vCPU, no GPU, Hetzner CX32 class), provisioned once, used for both the pilot's baselines if still open and this model, then deleted; its cost goes to the ledger. The files measured are checked by SHA-256 against the files staged for release. Every candidate evaluated on the benchmark is also measured on the reference VM, and all candidates are placed on the task's quality-vs-throughput chart before one is selected (Principle III).
- **Rationale**: `perf_local` only knows Ollama. Spike measurements on an M3 Pro CPU (1.9 s, 2.3 GB) suggest a comfortable margin; the 10-second bar of SC-003 leaves room for a slower 4-vCPU VM.
- **Fallback**: If latency exceeds 10 s or peak memory 4 GB, first try int8 dynamic quantization of the linear layers, then XLM-RoBERTa-base; either is a new candidate (R8 cap applies) with quality measured on the same files.
- **Alternatives**: ONNX Runtime export (deferred: adds a runtime dependency and a second inference path; only if the fallback needs it).

## R14 Results files and the release bar

- **Decision**: `jtbd span results --version 0.1.0` writes `zoo/models/productdev-jtbd-span-xlmr/results/0.1.0/quality.json` and `performance.json` from the score, check and perf files, with `source_run` set. Deterministic-check bar: 100% verbatim quotes, 100% schema-valid outputs and 100% consistency (the span model's quotes are spans of the input by construction, so anything less is a bug). Quality metrics: agreement per produced dimension and the comparison composite (with `reference`, `benchmark`, `n_items`), verbatim and schema pass rates, contested-item count, and comparison metrics: comparison composite of the best zero-shot baseline, of the teacher, of the frontier-versus-frontier reference and 85% of that reference value. `jtbd span release-check` evaluates FR-015 from these files and exits non-zero if the bar is missed. The bar itself is written into `configs/productdev/jtbd/span-xlmr.yaml` and committed before training starts.
- **Rationale**: Rule 9 of the gate requires every number on the card to be a metric in a results file, so comparison numbers must be metrics too. The card template renders the metric table generically; no template change is needed. Committing the bar first satisfies Principle IV (criteria before the experiment).
- **Alternatives**: Put comparisons only in the free-text limitations (rejected: untraceable numbers fail rule 9).

## R15 Release steps

- **Decision**: In this order: `zoo init-model productdev-jtbd-span-xlmr` (staging repo); add the repo to `HF_STAGING_TOKEN`; `zoo stage` from the Spark; complete `releases/0.1.0.yaml` (recipe commit, config `configs/productdev/jtbd/span-xlmr.yaml`, doc `docs/recipes/productdev-jtbd-span-xlmr.md`, `ram_gb: 4`, sources grouped by origin and license with counts, teacher with license basis); update `model.yaml` card texts (limitations name any omitted dimension and the reason; summary speed matches measured numbers); `zoo check` offline and online; merge the branch to `main`; rerun `zoo history-check`; make the GitHub repository public; tag; approve the preview; publish. Then the reader test (SC-004) and the clean-machine usage test (SC-005).
- **Rationale**: Follows the feature 003 hand-over. The repository must be public before approval because the card's install line points to it (FR-019); the workflows must be on `main` (feature 003, implementation order step 0).
- **Alternatives**: Publish first, open the repository later (rejected: the usage example would fail for visitors).

## R16 Budget and keys

- **Decision**: A separate budget block `span-xlmr-0.1.0` in `configs/productdev/jtbd/budget.yaml` with €20 total, and a new OpenRouter key for this feature with a hard limit of USD 20 (about €18.40). Ledger entries carry the budget name. Expected spend: €0 if the recommended teacher is local; about €10 per 1,000 chunks if it is the four-model ensemble (from spike prices, used only as an estimate); under €1 for the reference VM.
- **Rationale**: Keeps the pilot's €20 and this feature's €20 apart (spec Assumptions). A separate key gives a hard limit per budget.
- **Alternatives**: Raise the pilot key's limit (rejected: mixes budgets, the limit does not reset).

## R17 Retention

- **Decision**: `data/span-train-v1/` (chunks, teacher runs, rows) carries a `retention.yaml`: kept while a model version trained on it is current, reviewed for deletion no later than 24 months after the training data is frozen (`jtbd span freeze-data`, which hashes chunks and rows). Snapshots keep their own `retention_until`.
- **Rationale**: Constitution VI requires a stated retention for each dataset; mirrors the pilot.
- **Alternatives**: none considered.

## R18 Module layout and dependency boundary

- **Decision**: `mobility_model_zoo.productdev.jtbd.span` is a package. `span/__init__.py`, `span/model.py`, `span/units.py`, `span/extractor.py` use only the base dependencies (torch, transformers, huggingface_hub, safetensors, sentencepiece). Training, rows, tuning, evaluation and CLI code live in `span/train.py`, `span/rows.py`, `span/tune.py`, `span/evaluate.py`, `span/cli.py` and may use the `[jtbd]` extra; they are never imported by `__init__.py`. A unit test imports the inference path in an environment without the extra (the gate's usage check also covers it). `spike/` stays as a historical record; nothing in `src/` imports it.
- **Rationale**: Hand-over requirement: the base install must be enough to run the model.
- **Alternatives**: Separate distribution for inference (rejected: one package is simpler and already set up).
