# Implementation Plan: Production span model, first public release

**Branch**: `004-production-span-model` | **Date**: 2026-10-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-production-span-model/spec.md`

## Summary

The fast span model from the spike is rebuilt as a regular JTBD model and published as `mobility-model-zoo/productdev-jtbd-span-xlmr` `0.1.0` (experimental):

1. **Training corpus** `span-train-v1` (about 1,000 chunks) as its own dataset next to the pilot benchmark, cut only from `training_allowed` snapshots that share no source with the benchmark or holdout, redacted with sampled manual review (research R1–R4, R17).
2. **Teacher labels** from the teacher the pilot recommends, enforced by a new run role `teacher` (R5); training rows with the frozen quote repair (R7).
3. **Model** in the package `mobility_model_zoo.productdev.jtbd.span`: the spike's unit classifier on XLM-RoBERTa-large, with heads only for the attribute dimensions that passed the pilot, trained in plain PyTorch on the DGX Spark, validated and thresholded on held-out training snapshots (R6, R8–R11, R18).
4. **Measurement** in the shared `jtbd` harness: a `span` backend and `student` role, a comparison composite over the dimensions the model produces, and `perf` for PyTorch models on the reference VM (R12, R13).
5. **Release** through the feature 003 pipeline: results files, release bar check, completed release record, repository made public, tag, approval, publication; reader test and clean-machine test (R14, R15).

Data generation is blocked until the pilot (feature 001) has frozen its benchmark and recommended a teacher (FR-001). Everything that does not need pilot results (code, configs, tests on fixtures, corpus building) can start now.

## Technical Context

**Language/Version**: Python 3.12, managed with `uv` (unchanged)

**Primary Dependencies**:
- Base install (inference, what model users get, unchanged): `torch`, `transformers`, `huggingface_hub>=1.19`, `safetensors`, `sentencepiece`
- `[jtbd]` extra (training, rows, evaluation, CLI): existing pilot dependencies; no new ones expected
- Training container on the DGX Spark: `nvcr.io/nvidia/pytorch:25.09-py3` with the package installed (R9)
- Release: the existing `zoo` tool and GitHub workflows from feature 003, unchanged unless a format gap is found

**Storage**: Files. Training dataset under `data/span-train-v1/` (gitignored, never published); model files on the Spark and in the private HF staging repo; results and release record in `zoo/models/productdev-jtbd-span-xlmr/`; configs in `configs/productdev/jtbd/`.

**Testing**: `pytest`. Unit tests for unit splitting, windowing and merging, offset alignment, output schema, loading from a directory, dimension handling (failed dimensions absent), source-separation guard, sampled redaction policy, `teacher` role guard, `span` run loading and scoring with missing dimensions, comparison composite, release-bar check. A tiny random-weight model (small encoder config, no download) as a fixture for end-to-end tests of `extract`, `span label`, `check`, `score` and `perf` on CPU. The base-install import test. Manual runs on the Spark and the reference VM per [quickstart.md](quickstart.md).

**Target Platform**:
- Training: DGX Spark (aarch64, GB10, 128 GB unified memory).
- Evaluation (quality): DGX Spark or Mac with the identical float32 files.
- Speed and memory: the reference VM (8 GB RAM, 4 vCPU, no GPU, Linux).
- Users: any CPU machine with at least 8 GB RAM and Python 3.12.

**Project Type**: single project (library plus the CLIs `jtbd` and `zoo`)

**Performance Goals**: 9,000-character text in ≤ 10 s on the reference VM excluding loading, peak memory ≤ 4 GB (SC-003, FR-009); a training run ≤ about 1 hour on the Spark (spike: 263 s per epoch on 180 chunks for the large encoder, not a rule).

**Constraints**:
- Cash ≤ €20 (teacher labeling, reference VM), hard key limit (R16).
- No spike data, labels or models (FR-004); no benchmark-based selection beyond the capped, fully reported candidate evaluations (R8).
- Frozen pilot artifacts (benchmark, guideline, output schema, teacher-scoring rules) are read, never changed.
- The inference path imports only base dependencies (R18).

**Scale/Scope**: about 1,000 training chunks (at least 600 usable, FR-005) (about 3.5 million characters), about 100 validation chunks, 140–160 benchmark chunks, one published model version of about 2.3 GB, at most three benchmark-evaluated candidates.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution version **1.3.0**. Task: JTBD extraction (`productdev`), tool `jtbd`; release through `zoo`.

| Principle | Touched | Pre-design | Post-design | How the plan complies |
|-----------|---------|------------|-------------|-----------------------|
| I. Problem-First | yes | ✅ | ✅ | `extract(text)` takes only text; no persona or role input. Actor type is an output, only if its dimension passed (R11). |
| II. Grounded Evidence | yes | ✅ | ✅ | Every item is a character span of the input; `check` still verifies `quote == text[start:end]`. An empty item list is valid and not penalised in training (relevant-but-empty chunks kept only when the teacher said so, R7). |
| III. Measure Before Optimizing | yes | ✅ | ✅ | Same frozen benchmark, consensus, matching and scoring harness as every JTBD model (R12); contested items reported separately; deterministic checks reported on their own; quality-vs-throughput chart with the model as a point; numbers called agreement with the named references (card rule 10). Benchmark labelers never label training data (`teacher` role guard, R5). |
| IV. Riskiest Assumption First | yes | ✅ | ✅ | No data generation before the pilot's decision (FR-001, enforced by the `teacher` role needing `decision.json`). Only passed dimensions are trained (R6). Release bar committed before training (R14). |
| V. Small and Local | yes | ✅ | ✅ | Budget ≤ 4 GB RAM, CPU only, on the reference VM; measured with the staged files (R13). No runtime network use after download. |
| VI. Clean Provenance | yes | ✅ | ✅ | `training_allowed` only, no shared source with the benchmark (R2), redaction of every chunk before labeling with sampled manual review (R4, spec FR-005), teacher license from the pilot's recorded basis, retention stated (R17), dataset never published (`zoo stage` refuses data paths). |
| VII. Metadata over Inference | yes | ✅ | ✅ | The model predicts no language, source type, region or date. |
| VIII. Fair Comparison | yes | ⚠ deviation | ✅ justified | Same benchmark and harness (R12); comparison composite over identical dimensions for every model. Ludwig is not used for this model; justified under Complexity Tracking (R9). |
| IX. Reproducible, Dated Releases | yes | ✅ | ✅ | Versioned configs, recorded hyperparameters and seed, recipe document at a recorded commit (gate rule 8), training data hashed (R17), immutable `0.1.0`, release only through the pipeline after approval. |
| X. Scope Discipline | yes | ✅ | ✅ | No deduplication, clustering or prioritisation in model or training objective. |
| Technical Spikes | yes | ✅ | ✅ | Spike chunks, labels and models are not used (`data-check`, `spike_data: false`); the spike's code is re-implemented in the package and `src/` never imports `spike/`. Spike numbers set no rule (research preamble). |
| Resources & Cost Discipline | yes | ✅ | ✅ | Local first (Spark training, local teacher if recommended), then OpenRouter only for a recommended hosted teacher; €20 budget with a hard key limit (R16); development and reference hardware kept apart (R13); crawl once (R3). |
| Tasks and Releases | yes | ✅ | ✅ | Build and measure through `jtbd` (shared with every JTBD model); release through the common `zoo` gate and pipeline. |

## Project Structure

### Documentation (this feature)

```text
specs/004-production-span-model/
├── plan.md              # This file
├── research.md          # Phase 0: R1–R18
├── data-model.md        # Phase 1: datasets, runs, model files, results, states
├── quickstart.md        # Phase 1: validation scenarios
├── contracts/
│   ├── cli.md                     # new and changed jtbd commands
│   ├── python-api.md              # SpanExtractor
│   ├── model-files.md             # published file layout and span_config.json
│   └── span-output.schema.json    # jtbd-span-v1
├── checklists/requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
configs/productdev/jtbd/
├── span-train-v1.yaml                   # training dataset config (data dir, exclude-benchmark, redaction: sampled, composition targets)
├── span-xlmr.yaml                       # model recipe: base encoder, hyperparameters, seed, release bar, candidate cap
├── budget.yaml                          # + budget block span-xlmr-0.1.0
└── perf/interview-9k-de.txt             # fixed fictional 9,000-character perf text
docs/recipes/productdev-jtbd-span-xlmr.md   # recipe.doc: data → rows → train → tune → evaluate → perf → stage
src/mobility_model_zoo/productdev/jtbd/
├── span/
│   ├── __init__.py                      # exports SpanExtractor (base deps only)
│   ├── units.py                         # sentence/clause units, windows (base deps only)
│   ├── model.py                         # SpanTagger: encoder + heads (base deps only)
│   ├── extractor.py                     # SpanExtractor.from_pretrained / extract / save (base deps only)
│   ├── rows.py                          # teacher run → aligned training rows (jtbd extra)
│   ├── train.py                         # training loop, validation by snapshot (jtbd extra)
│   ├── tune.py                          # thresholds on validation rows
│   ├── evaluate.py                      # writes span runs on a benchmark split
│   ├── results.py                       # zoo results files, comparison composite, release check
│   └── cli.py                           # `jtbd span …` sub-app
├── corpus/autochunk.py                  # + --exclude-benchmark guard
├── corpus/redact.py                     # + sampled review policy
├── labeling/runner.py                   # + role teacher (recommended-teacher guard)
├── schema.py                            # + Role.teacher, Role.student, Backend.span
├── runs.py                              # + load span runs as LocatedItems
├── checks.py                            # + jtbd-span-v1 schema check
├── scoring.py                           # + produced-dimension handling, comparison composite
├── perf.py                              # + --backend span (child process, RSS, load time)
└── cli.py                               # registers `span` sub-app
scripts/spark/train_span.sh              # runs `jtbd span train` in the NVIDIA container on the Spark
zoo/models/productdev-jtbd-span-xlmr/
├── model.yaml                           # card texts updated (dimensions, measured speed)
├── releases/0.1.0.yaml                  # completed
└── results/0.1.0/{quality,performance}.json
tests/
├── unit/span/                           # units, windows, alignment, output schema, dimensions, results, release bar
├── unit/test_exclude_benchmark.py
├── unit/test_redaction_sampled.py
├── unit/test_teacher_role.py
├── integration/test_span_end_to_end.py  # tiny random model: extract → label → check → score → perf
└── fixtures/span/                       # tiny encoder config, tokenizer, rows, decision.json
```

**Structure Decision**: The span model is a subpackage of the JTBD task package, as the task-per-tool rule requires. Its inference half (`units`, `model`, `extractor`) depends only on the base install so the published usage example works; the build half uses the `[jtbd]` extra. Harness changes extend existing modules rather than adding a parallel scorer, so every JTBD model is measured the same way. `spike/` is left untouched as history.

## Implementation order

0. Commit the spec and plan on this branch. Record the release bar and candidate cap in `configs/productdev/jtbd/span-xlmr.yaml` and commit it before any training (Principle IV).
1. Inference package (`units`, `model`, `extractor`), output schema, tiny fixture model, base-install import test.
2. Harness: roles and backend in `schema.py`, `span` run loading, checks, produced-dimension scoring, comparison composite, `perf --backend span`. Tests on the fixture model.
3. Training corpus tooling: `span-train-v1.yaml`, `--exclude-benchmark`, sampled redaction, `span data-check`, `retention.yaml`, `freeze-data`.
4. Build the corpus from stored snapshots, fetch new sources once, redact, review the sample (can run before the pilot finishes; labeling cannot).
5. **Wait for the pilot**: `decision.json` with passed dimensions and recommended teacher.
6. Teacher labeling (`--role teacher`), rows, `freeze-data`.
7. Training on the Spark, threshold tuning, candidate evaluation on the benchmark (cap 3), scoring.
8. Reference VM: `perf --backend span` for every evaluated candidate, with the files' hashes; quality-vs-throughput chart with every candidate; select; delete the VM.
9. Results files, `span release-check`. If the bar is missed: stop, report as an unpublished model.
10. Release (R15): staging, record, card texts, `zoo check`, merge to `main`, history check, repository public, tag, approval, publish.
11. Reader test, clean-machine usage test, README update (spike section points to the published model), traceability table.

## Risks

| Risk | Mitigation |
|------|-----------|
| The pilot ends in Rethink on relevance or kind, or recommends no teacher | The feature stops before labeling (spec edge cases); steps 1–4 remain useful for a later attempt |
| Too few `training_allowed` sources not used by the benchmark | Fetch new sources once (R3); if still short, train on the actual size and record it |
| Speed budget missed on the 4-vCPU VM | Fallback order: int8 dynamic quantization, then XLM-RoBERTa-base, each as a new capped candidate (R13) |
| The model does not beat the best baseline on the comparison composite | Not published (FR-015); reported as an unpublished, measured model; findings feed the next spec |
| Teacher labels of a hosted ensemble exceed the budget | `jtbd budget --estimate` before each run and a hard key limit; fall back to the best fit single teacher only if it is within the pilot's 0.02 tie margin, otherwise stop |
| Format gap in the feature 003 release tooling | Fix as a patch to the `zoo` tool with tests, not a workaround in the record |
| Spark memory exhaustion during training (seen in the spike with LLMs) | Encoder model is small; keep `expandable_segments` and the host watchdog from the spike |

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Principle VIII: Ludwig is not the training framework for this model | The model classifies regex sentence and clause units pooled across overlapping 512-token windows, with heads that depend on the pilot outcome; the published inference code must reproduce the training-time units and windows exactly (R9) | Ludwig token classification plus post-processing to units trains a different objective than the decision the model makes and needs a second inference path; the comparison stays fair because evaluation uses the shared harness, not the training framework |
