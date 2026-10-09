# Implementation Plan: Deduplication and clustering of JTBD items

**Branch**: `009-jtbd-dedup-cluster` | **Date**: 2026-10-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/009-jtbd-dedup-cluster/spec.md`

## Summary

A new task `jtbd-cluster` sits between `scout-large` and the opportunity methods. It reads scout outputs with source metadata, merges items that state the same need into duplicate groups, links more specific groups under more general ones, arranges groups of all kinds into one or two cluster levels, and writes one versioned result (`jtbd-cluster-v1`) that an Opportunity Solution Tree and an outcome-driven needs list can be read from directly.

1. **Stage** (`jtbd cluster run`, Python `ClusterStage`): exact copies by hash (R4); multilingual sentence embeddings of the quote only, cached (R5, R6); average-linkage deduplication within kind on a sparse neighbour graph (R7); specificity by multilingual NLI on candidate pairs (R8); clusters on group centroids across kinds (R9).
2. **Continuity**: stable item ids by hash and group/cluster ids by overlap matching (R13); human corrections recorded by item id and applied on every run (R14); statements and assignments kept in annotations (R15); change report.
3. **Measurement**: benchmark `cluster-v1` from real scout outputs, with stratified pairs and neighbourhood sets, split by snapshot (R10); labeled by the two existing reference models through the existing safeguards (R11); agreement pilot with frozen criteria and one re-pilot (R12); training-free baseline tuned on development data, scored per level (R12); speed and memory on the reference VM (R17).
4. **Views**: `report` renders a Markdown tree and a CSV of needs from the result (R16).

No model is trained and nothing is released in this feature. A trained model follows only if the baseline misses the bar (spec FR-025), as a new feature.

## Technical Context

**Language/Version**: Python 3.12, managed with `uv` (unchanged)

**Primary Dependencies**:
- Base install (unchanged): `torch`, `transformers` (encoders and NLI model)
- New extra `cluster`: `numpy`, `scipy`, `scikit-learn`, `pyyaml`, `jsonschema`, `typer` (R18)
- `jtbd` extra (unchanged): labeling backends, budget, freeze, metrics for building and measuring
- Pretrained models, pinned by revision in the settings: one encoder from `intfloat/multilingual-e5-small`, `intfloat/multilingual-e5-base`, `Alibaba-NLP/gte-multilingual-base`; NLI `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`; sampler `sentence-transformers/LaBSE` (benchmark building only). Licence basis recorded per model before first use.

**Storage**: Files. Bundles, maps, runs and analysis under `data/cluster/` (gitignored, never published); benchmark manifest (hashes only) under `topics/productdev/benchmarks/cluster-v1/`; guideline under `topics/productdev/guideline/cluster-v1/`; configs under `configs/productdev/jtbd/`.

**Testing**: `pytest`. Unit tests for bundle validation, item ids, exact-copy keys and independence units, deduplication with a stub encoder (fixed vectors), kind separation, specificity with a stub NLI, cycle breaking, cluster levels and aggregates, id matching on merge and split, corrections (applied, stale, refused), annotations survival, determinism, schema and semantic checks, pair and B-cubed metrics, criteria decisions, pair batch runner with the mock backend. Integration test on a small fixture bundle end to end with stub models (no download). Manual runs with real models per [quickstart.md](quickstart.md).

**Target Platform**: Development on the MacBook or DGX Spark; speed and memory on the reference VM (8 GB RAM, 4 vCPU, no GPU, Linux); users on any CPU machine with Python 3.12.

**Project Type**: single project (library plus the `jtbd` CLI)

**Performance Goals**: 50,000 items in ≤ 15 minutes with ≤ 4 GB peak RSS on the reference VM, offline after model download (FR-021, SC-005).

**Constraints**:
- Cash ≤ €20 for reference labeling and the reference VM, own budget `cluster-v1` with the existing hard key limit (SC-007).
- No hosted API at runtime; no generated text in the result; quotes never changed (FR-002, FR-014).
- Thresholds tuned on development data only; benchmark frozen before labeling; criteria frozen before the pilot (FR-024).
- Scout, its training objective and frozen extraction artifacts are not touched.

**Scale/Scope**: about 5,000 to 10,000 real items in the pool; 1,600 labeled pairs plus 300 holdout pairs; 16 sets of 40 items; at most three encoder candidates on the benchmark; 50,000-item scale set for speed only.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution version **2.0.0**. Task: `jtbd-cluster` (`productdev`), tool `jtbd cluster`; no release in this feature.

| Principle | Touched | Pre-design | Post-design | How the plan complies |
|-----------|---------|------------|-------------|-----------------------|
| I. Problem-First | yes | ✅ | ✅ | No persona, segment or scheme enters extraction or grouping; assignments are written downstream into annotations (R15). |
| II. Grounded Evidence | yes | ✅ | ✅ | Quotes are carried byte-identical and checked (`check`); representatives are member quotes; no generated statements or labels (R9, R16). Groups of one are valid. |
| III. Measure Before Optimizing | yes | ✅ | ✅ | Own frozen benchmark labeled by two reference families (R10, R11); contested pairs separate and scored neutrally; deterministic checks reported on their own; scores named as agreement with the named references; quality reported with time and memory (R17). |
| IV. Riskiest Assumption First | yes | ✅ | ✅ | Riskiest assumption: references agree on "same need" and "belongs together". Agreement pilot per level with criteria frozen before labeling, one re-pilot on holdout (R12). Baseline bar written down before scoring. |
| V. Small and Local, Budgets per Task | yes | ✅ | ✅ | Budget: 50,000 items ≤ 15 min, ≤ 4 GB, CPU, reference VM; measurement origin recorded; scale set labeled as such (R17). No runtime API. |
| VI. Clean Provenance | yes | ✅ | ✅ | Pool only from redacted, permitted chunks; pilot holdout untouched; no author metadata (R3); pre-send checks and approved routes for reference calls (R11); benchmark text and labels never published, manifest holds hashes only; retention as the JTBD data store. Third-party model licences recorded before use. |
| VII. Metadata over Inference | yes | ✅ | ✅ | Date, source class and origin come from the bundle, never inferred (R2). |
| VIII. Fair Comparison | yes | ✅ | ✅ | Every candidate is tuned on the same development split and scored with the same harness and benchmark version (R12). |
| IX. Reproducible, Dated Releases | partly | ✅ | ✅ | No release. Settings pinned by model revision and hashed into every result; deterministic output with the embedding cache (R6, R13). |
| X. Scope Discipline | yes | ✅ | ✅ | Separate downstream stage; scout unchanged; prioritisation, scoring, statements, personas and ontology out of scope. |
| Tasks and Releases | yes | ✅ | ✅ | One build-and-measure tool for the task (`jtbd cluster`); JTBD modules reused by import, no premature shared module (R1). |
| Resources & Cost Discipline | yes | ✅ | ✅ | Local first; reference labeling batched (about 100 calls per model); €20 budget with the hard key limit; development and reference hardware kept apart. |

No violations; Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/009-jtbd-dedup-cluster/
├── plan.md              # This file
├── research.md          # Phase 0: R1–R18
├── data-model.md        # Phase 1: input, map directory, entities, benchmark, states
├── quickstart.md        # Phase 1: validation scenarios S1–S7
├── contracts/
│   ├── cli.md                       # jtbd cluster commands
│   ├── python-api.md                # ClusterStage, read_bundle
│   ├── cluster-input.schema.json    # jtbd-cluster-input-v1
│   └── cluster-output.schema.json   # jtbd-cluster-v1
├── checklists/requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
configs/productdev/jtbd/
├── cluster-v1.yaml                  # benchmark: pool, split, sampling, sizes, seeds, reference models, budget name
├── cluster-criteria.yaml            # agreement thresholds, revise/rethink rules, baseline bar (frozen)
├── cluster-baseline.yaml            # stage settings: encoder + revision, NLI + revision, k, thresholds, levels
└── budget.yaml                      # + budget block cluster-v1 (€20)
topics/productdev/
├── tasks/jtbd-cluster.md            # task document: scope, reference, benchmark, metrics, tool, budget, riskiest assumption
├── guideline/cluster-v1/            # guideline-cluster-v1.md + examples (DE/EN: same, more specific, different, clusters)
└── benchmarks/cluster-v1/manifest.json
src/mobility_model_zoo/productdev/jtbd/
├── cluster/
│   ├── __init__.py                  # exports ClusterStage, read_bundle
│   ├── bundle.py                    # input validation, item ids, exact-copy keys, independence units
│   ├── embed.py                     # encoder loading, pooling, embedding cache
│   ├── dedup.py                     # neighbour graph, average linkage within kind, must/cannot-link
│   ├── specificity.py               # NLI on candidate pairs, parent choice, cycle breaking
│   ├── hierarchy.py                 # centroids, cluster levels, representatives, aggregates
│   ├── continuity.py                # id matching, state.json, change report
│   ├── corrections.py               # corrections.yaml, apply, stale/refused
│   ├── annotations.py               # annotations.jsonl merge
│   ├── stage.py                     # ClusterStage: orchestration, result assembly
│   ├── checks.py                    # deterministic checks (FR-026) and schema validation
│   ├── report.py                    # tree.md, needs.csv
│   ├── bench.py                     # pool, split by snapshot, stratified pairs, neighbourhood sets
│   ├── label.py                     # batch runner for pair and set labeling on existing backends
│   ├── prompt.py                    # frozen prompts and wire schemas for pairs and sets
│   ├── metrics.py                   # pair P/R/F1, B-cubed, kappa per level, consensus/contested
│   ├── decide.py                    # criteria → go/revise/rethink, baseline bar
│   ├── tune.py                      # grid search on development data only
│   ├── perf.py                      # child-process timing and RSS, scale set
│   ├── cli.py                       # `jtbd cluster …` sub-app
│   ├── jtbd-cluster-input-v1.schema.json
│   └── jtbd-cluster-v1.schema.json
└── cli.py                           # registers the `cluster` sub-app
pyproject.toml                       # + extra `cluster`
tests/
├── unit/cluster/                    # one test module per cluster module above
├── integration/test_cluster_end_to_end.py   # fixture bundle → run → check → correct → rerun → report, stub models
└── fixtures/cluster/                # bundles (DE/EN paraphrases, copies, mixed kinds), stub vectors, mock answers
```

**Structure Decision**: The stage is a subpackage of the JTBD task package next to `span/`, with its own sub-app, configs, benchmark and task document (R1). Runtime modules (`bundle` to `report`) need only the base install and the `cluster` extra so users can run the stage after scout; the measurement modules (`bench` to `perf`) use the `jtbd` extra and reuse its backends, budget, freeze and pre-send checks by import.

## Implementation order

0. Commit spec and plan. Write the task document, the guideline with examples and `cluster-criteria.yaml`, and commit them before any labeling (constitution IV).
1. Input and output contracts in code: schemas, bundle reader, item ids, exact copies, independence units, deterministic checks (User Story 1 foundations).
2. Stage with stub models: deduplication, specificity, hierarchy, result assembly, report; then real encoders and the embedding cache (User Stories 1 and 3).
3. Continuity: ids, corrections, annotations, change report, determinism (User Stories 4 and 5).
4. Benchmark: pool, split, sampling, freeze; pair and set labeling with the mock backend, then the two references; agreement and decision (User Story 2).
5. Tuning on development data, scoring of up to three encoder candidates, perf on the reference VM; results written up in `topics/productdev/reports/cluster-v1/`.

Steps 1–3 need no labels and no cash; step 4 is the only one that spends from the €20 budget.

## Complexity Tracking

No constitution violations to justify.
