# Feature Specification: End-to-end spike (sources → teacher data → fine-tuned model)

**Feature Branch**: `002-e2e-spike`
**Created**: 2026-09-27
**Status**: Draft
**Type**: **Technical spike** (constitution v1.2.0, "Technical Spikes"). Results are labeled "spike", never "benchmark".

## Purpose

Run the whole chain once, end to end, before the agreement pilot (001) is complete:

1. Load sources and cut chunks.
2. Generate training data with a local teacher model.
3. Fine-tune a small model.
4. Compare the untrained and the fine-tuned small model on the same evaluation chunks.

The spike finds integration problems early: framework compatibility on the DGX Spark, data format, serving and scoring. It produces the first two points (base, fine-tuned) for later comparison.

## Clarifications

### Session 2026-09-27

- Q: How does the spike relate to the constitution's gate before data generation? → A: The constitution is amended with a "Technical Spikes" section (v1.2.0). The spike is exempt from that gate and from the frozen-benchmark reporting requirement, within stated bounds.
- Q: What is the evaluation reference? → A: Claude through the subscription, as a single reference model. There is no consensus and no contested set; this is a spike limitation.
- Q: Where does the heavy work run? → A: On the DGX Spark over SSH. The teacher runs on Ollama, training in Docker with the GPU, and serving on vLLM.

## User Scenarios & Testing

### User Story 1 - One complete run (Priority: P1)

The project owner runs the chain once and gets:
- a spike report with per-dimension scores for the base model, the fine-tuned model and the teacher, all measured against the Claude reference on the same evaluation chunks
- throughput on the Spark
- a list of what broke

**Independent Test**: The spike report exists. It lists all three models with the same evaluation chunk count, and it is labeled "spike".

**Acceptance Scenarios**:

1. **Given** the stored snapshots, **When** chunks are cut automatically, **Then** training chunks come only from `training_allowed` snapshots and evaluation chunks only from other snapshots, so no source appears in both.
2. **Given** the teacher labels, **When** the training set is exported, **Then** items whose quote is not verbatim are dropped, and chunks with a schema-invalid output are excluded.
3. **Given** the base and the fine-tuned model, **When** both label the evaluation chunks, **Then** they use the same prompt, schema, decoding settings and serving stack.

### Edge Cases

- **The training framework does not run on the Spark (aarch64, GB10):** the finding is recorded, and a fallback framework is used with the deviation documented.
- **The teacher is too slow:** the training set shrinks to what fits in about 3 hours of teacher time, and the size is recorded.
- **The fine-tuned model produces invalid JSON:** this counts against the model in schema validity. Its output is never repaired.

## Requirements

- **FR-S01**: Size bounds are at most 250 training chunks and 40 evaluation chunks, each 300–1500 tokens. Evaluation chunks come from snapshots that are not used for training.
- **FR-S02**: Only `training_allowed` snapshots MAY supply training chunks. `benchmark_only` snapshots MAY supply evaluation chunks.
- **FR-S03**: The teacher is a local open-weight model on the Spark whose license permits training on its outputs: `qwen3.6:35b` (Apache 2.0). Claude and GPT MUST NOT generate training data.
- **FR-S04**: The evaluation reference is Claude (subscription CLI). The teacher and both small models are scored against it with the pilot's scoring harness, with every item counted as consensus.
- **FR-S05**: The small base model is `Qwen/Qwen3-4B-Instruct-2507` (Apache 2.0). Fine-tuning uses LoRA. The training framework is Ludwig (constitution Principle VIII), with a documented fallback if Ludwig does not run.
- **FR-S06**: The base and fine-tuned models are served the same way (vLLM with structured output), so the comparison is fair.
- **FR-S07**: All raw outputs, training data and the adapter stay in `data/` (gitignored) or on the Spark and are never released (Technical Spikes).
- **FR-S08**: Usernames and direct identifiers are removed before labeling (pattern redaction plus a spot check). The sources are papers and parliamentary records.
- **FR-S09**: The cash budget is €0. The run uses only the subscription and local compute.
- **FR-S10**: The spike report lists scores, throughput on the Spark (not the reference hardware), sizes, run times, deviations and findings.

## Success Criteria

- **SC-S01**: One complete run from snapshots to the spike report, with no manual editing of intermediate data.
- **SC-S02**: The report shows base and fine-tuned scores on the same ≥ 30 evaluation chunks, plus the teacher's score for comparison.
- **SC-S03**: The findings list names every step that failed or needed a workaround.

## Constitution Alignment

- **Technical Spikes (v1.2.0)**: declared as a spike with bounds and budget (FR-S01, FR-S09). Results are labeled "spike".
- **I, II**: same prompt (domain, no persona) and verbatim-quote filter on training data (FR-S03, acceptance scenario 2).
- **III**: Claude never generates training data, and the teacher is not an evaluation reference. The frozen-benchmark requirement is waived as a spike exemption.
- **V**: throughput is measured on the Spark and labeled as development hardware, not target hardware.
- **VI**: `permitted_uses` is enforced for training chunks, redaction is applied, and nothing is released.
- **VIII**: Ludwig is the primary framework, and any fallback is documented.
- **Resources & Cost Discipline**: runs local first, then the subscription, at €0.

## Assumptions

- The guideline draft `guideline-v1` is used unchanged. The spike does not wait for its review.
- Automatically cut chunks get the source's sub-area and language. Their relevance intent is not curated.
