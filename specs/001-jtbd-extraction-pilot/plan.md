# Implementation Plan: JTBD Extraction Pilot

**Branch**: `001-jtbd-extraction-pilot` | **Date**: 2026-09-25, updated 2026-09-29 after the spike | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-jtbd-extraction-pilot/spec.md`

## Summary

The pilot tests whether two frontier models, Claude and GPT, label the JTBD extraction task consistently on about 150 German and English Mobility chunks, plus about 30 holdout chunks that are used only for a rerun. It also measures how far five teacher candidates and 2–3 untrained small models (≤ 4B) get against the frontier consensus. The teacher candidates are four single models (local qwen3.8:27b; mimo-v2.6-pro, deepseek-v4.1-flash and glm-5.3-flash through OpenRouter) and their offline ensemble (FR-019a, FR-019b). Each is classified as fit or not fit to generate training data (FR-031a), scored after quote repair (FR-026a).

The technical approach is a single Python package with a CLI (`pilot`) that runs the pilot as a chain of reproducible steps:

1. Fetch each source once and snapshot it.
2. Build and redact chunks.
3. Freeze the guideline and decision criteria.
4. Label with three backends:
   - Claude through the headless CLI on the subscription
   - a GPT mini-tier model through OpenRouter (budget deviation, see Complexity Tracking)
   - local models through Ollama on the DGX Spark
   - the teacher-candidate ensemble, derived offline from the stored teacher outputs (`pilot ensemble`, no model calls)
5. Run the deterministic checks.
6. Match items, build the consensus and the contested set.
7. Compute agreement, baseline scores and teacher scores (raw, and repaired for teachers).
8. Measure performance on a low-resource reference VM.
9. Derive the go / revise / rethink decision and the teacher-fitness classification mechanically and generate the report.

The cash budget is at most €20. The expected spend is about €10.

## Technical Context

**Language/Version**: Python 3.12, managed with `uv`

**Primary Dependencies**:
- Pydantic v2: the schema is its single source of truth, and JSON Schema is exported from it
- `typer`: CLI
- `openai` SDK: OpenRouter's OpenAI-compatible endpoint (GPT reference and three teacher candidates: `data_collection: deny`, `require_parameters`, an allowed-quantizations filter and a per-model reasoning setting; parallel workers per run)
- `rapidfuzz`: quote repair for the teacher scoring view (FR-026a)
- `httpx`: Ollama and fetching
- `scikit-learn`: kappa
- `scipy`: Hungarian matching
- `numpy` and `pandas`
- `matplotlib`: the Pareto chart
- `trafilatura` / `pypdf`: text extraction from snapshots
- `pyyaml`
- The `claude` CLI, headless, as an external binary

**Storage**:
- Files only.
- `data/` is gitignored and holds snapshots, chunks, raw responses and analysis as JSONL, YAML and raw files.
- `benchmarks/pilot-v1/manifest.json` is versioned and contains hashes only.

**Testing**: `pytest`, with hand-computed fixtures and mocked backends (mini corpus of 5 chunks)

**Target Platform**:
- Development and quality runs: macOS (orchestration) and the DGX Spark (Ollama).
- Performance runs: a Linux cloud VM with 8 GB RAM, 4 vCPU and no GPU.

**Project Type**: single project (CLI plus library)

**Performance Goals**:
- The pilot itself has no throughput target.
- It measures chunks/min, output tok/s, p50/p95 latency and peak RSS for each small model on the reference VM.

**Constraints**:
- Cash budget ≤ €20, with a hard cap on the OpenRouter key: USD 20 (≈ €18.40, no reset) since 2026-09-29, raised from €12 for headroom.
- Each source is fetched only once.
- Every model's raw output is stored unmodified.
- Criteria are hash-frozen before labeling.
- The pilot has no runtime dependency on hosted APIs beyond labeling.

**Scale/Scope**:
- About 180 chunks.
- About 180 calls for each of Claude and GPT.
- About 180 calls for each of the 3 OpenRouter teacher candidates, and about 180 for the local teacher and each of the 2–3 small models on Ollama.
- The ensemble is computed offline from the four teacher runs (no calls).
- One optional rerun on 30 holdout chunks.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution version: **1.2.0** (re-checked 2026-09-29; the 1.2.0 technical-spike exemptions do not apply to this feature)

| Principle | Touched | Pre-design | Post-design | How the plan complies |
|-----------|---------|------------|-------------|-----------------------|
| I. Problem-First | yes | ✅ | ✅ | The prompt is the guideline plus the domain definition from `configs/domain/mobility.yaml`. There is no persona input. Actor fields are output only ([extraction-output schema](contracts/extraction-output.schema.json)). |
| II. Grounded Evidence | yes | ✅ | ✅ | The quote locator maps each quote to a span, and items that fail it are invalid. Empty item lists are valid and scored as correct. The guideline requires "lower grade when uncertain". |
| III. Measure Before Optimizing | yes | ✅ | ⚠ deviation documented | Claude and GPT form the reference. Contested entries are stored and reported separately. Checks are reported independently. The Pareto chart is in the report. The report template says "agreement with frontier models". Both labelers are recorded as `benchmark_labeler` and blocked from the teacher role in `configs/models.yaml`. |
| IV. Riskiest Assumption First | yes | ✅ | ✅ | `pilot freeze` hashes the guideline, schema, decision criteria and teacher-scoring configuration, and `pilot label` refuses to run without a matching frozen hash. |
| V. Small and Local | yes | ✅ | ✅ | Performance is measured on the reference VM (8 GB, no GPU). The Spark is used only for quality runs with identical model digests. Hosted APIs are used only for labeling. |
| VI. Clean Provenance | yes | ✅ | ✅ | Each snapshot records license, legal basis, `permitted_uses` and retention. Reddit comes through the official API and is `benchmark_only`. Redaction plus `redact-check`. `data/` is gitignored and nothing is published. The license basis is recorded for every teacher candidate (qwen3.8: Apache-2.0; mimo, deepseek, glm-5.3-flash: MIT); the ensemble lists its members' license bases. |
| VII. Metadata over Inference | yes | ✅ | ✅ | Metadata lives only in the chunk records and is never in the output schema. |
| VIII. Fair Comparison | yes | ✅ | ✅ | One scoring harness and one frozen benchmark version for every model. Ludwig does not apply because there is no training. |
| IX. Reproducible Releases | yes | ✅ | ✅ | Raw responses are stored with model ID, version or digest, date and settings. Manifest hashes. `pilot-v1` is frozen before baseline scoring. |
| X. Scope Discipline | yes | ✅ | ✅ | Extraction only. There are no deduplication, clustering or prioritization modules. |
| Resources & Cost Discipline | yes | ✅ | ✅ | Cost order: local Spark (qwen3.8 teacher, baseline quality), then subscription (Claude), then pay-per-use (GPT, the three teacher candidates that do not run locally at usable quality or size, and the VM; research.md R1, R10). `budget.py` ledger and pre-call guard, with the key cap (USD 20 ≈ €18.40) below the €20 budget. `pilot source fetch` refuses to fetch a URL that already has a snapshot. |

There is one documented deviation (Principle III, GPT mini tier as the second reference model). It is justified in Complexity Tracking below.

## Project Structure

### Documentation (this feature)

```text
specs/001-jtbd-extraction-pilot/
├── spec.md
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/           # Phase 1
│   ├── extraction-output.schema.json
│   ├── source-snapshot.schema.json
│   ├── chunk-record.schema.json
│   ├── label-run-manifest.schema.json
│   ├── decision-criteria.schema.json
│   ├── decision-criteria.example.yaml
│   ├── teacher-scoring.schema.json
│   ├── teacher-scoring.example.yaml
│   └── cli.md
├── checklists/requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
configs/
├── domain/mobility.yaml        # domain definition and sub-areas (Principle I, domain isolated in config)
├── models.yaml                 # backends, model IDs, hosts, digests, roles
├── decision-criteria.yaml      # FR-030/FR-031/FR-031a thresholds (frozen)
├── teacher-scoring.yaml        # FR-019b ensemble and FR-026a quote-repair rules (frozen with the criteria)
├── budget.yaml                 # cash budget, key cap, prices
└── pilot-v1.yaml               # run settings, composition targets, IoU threshold
guideline/
├── guideline-v1.md             # labeling guideline (prompt body)
└── examples/                   # worked examples, including an empty result
src/jtbd_pilot/
├── schema.py                   # Pydantic models, JSON Schema export
├── cli.py                      # typer entry point `pilot`
├── sources/                    # fetch, snapshot, registry (crawl once)
├── corpus/                     # chunking, redaction, composition, split
├── labeling/
│   ├── prompt.py               # guideline + schema → prompt
│   ├── claude_cli.py           # headless `claude -p` backend
│   ├── openrouter.py           # GPT via OpenRouter
│   ├── ollama.py               # Spark/VM local models
│   ├── mock.py                 # fixture replay (tests, dry runs; test_fixture only)
│   └── runner.py               # label runner: freeze/budget/role guards, resume, version guard
├── budget.py                   # ledger and pre-call guard
├── freeze.py                   # hashing and manifest
├── quotes.py                   # verbatim quote locator; repair() for the teacher scoring view (FR-026a)
├── ensemble.py                 # teacher ensemble (FR-019b): span grouping, votes, frozen tie-break
├── checks.py                   # deterministic checks
├── matching.py                 # span IoU + kind tie-break, Hungarian
├── consensus.py                # consensus and contested entries
├── metrics.py                  # kappa, weighted kappa, F1, bootstrap CIs
├── scoring.py                  # model vs consensus, neutral contested scoring; repaired view for teachers
├── categorize.py               # disagreement categories, free-text sample
├── perf.py                     # throughput, latency, peak RSS
├── decision.py                 # FR-030/FR-031 decision table, FR-031a teacher fitness
└── report/                     # report template and Pareto chart
benchmarks/pilot-v1/manifest.json
data/                           # gitignored: snapshots/, sources/, chunks/, runs/, analysis/, budget/
reports/pilot-v1/               # report.md, figures/
tests/
├── unit/                       # metrics, matching, quotes, consensus, decision, budget, freeze
├── integration/                # mini-corpus end to end with mocked backends
└── fixtures/mini-corpus/
```

**Structure Decision**: a single project, because the pilot is a CLI plus a library with no service or UI. Domain-specific content lives only in `configs/domain/` and `guideline/`, so that later domains need no code changes. The metrics, matching, checks and decision code is written to be reused unchanged by later benchmark versions (Principle VIII).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Principle III asks for a reference from "frontier models". The second reference model is the **mini tier** of the current GPT generation, not the flagship. | Cash budget of €20 (Resources & Cost Discipline). The flagship costs about $31 per pass and GPT-5.5 about $17, so either breaks the budget once a rerun is included. The user chose the smaller model on 2026-09-25. | A higher budget or GPT-5.5 with a holdout-only rerun were both rejected by the user. Mitigations: the report states the deviation, a disagreement category "reference B clearly wrong" is tracked, and an optional GPT-5.5 control run on the 30 holdout chunks (about €2.50) can be decided before any rerun. |

A second documented deviation from the spec defaults is that Claude's sampling temperature cannot be set on the subscription CLI path. It is recorded in the run manifest and in the report, and it does not violate any principle. See [research.md](research.md) R9.

The three OpenRouter teacher candidates are not a violation: the cost order allows pay-per-use for models that are not available locally. The spike (specs/002-e2e-spike, reports/spike-v2) measured them above the best local teacher, and their full runs cost about €2 in total. See [research.md](research.md) R1 and R10.
