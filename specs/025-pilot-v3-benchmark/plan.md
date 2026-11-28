# Implementation Plan: Benchmark pilot-v3 for scout guideline v3

**Branch**: `claude/025-pilot-v3-benchmark` | **Date**: 2026-11-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/025-pilot-v3-benchmark/spec.md`

## Summary

This feature builds the benchmark pilot-v3 for scout-large 0.2.0 on the owner-approved guideline v3 package, runs its agreement pilot, and then labels and freezes the full benchmark.

Technically it is a new `jtbd/v3` subpackage next to the frozen v1 code, made of these parts:

- labeler schemas per pass;
- a three-pass extension of the existing runner;
- token-IoU matching;
- agreement statistics, including Krippendorff's alpha with MASI, written in-house;
- the brief's decision rule as a pure function;
- a seeded sampler with the connective-enriched link sample;
- a state-machine benchmark freeze in its own directory;
- a reverse separation check for new benchmark sources.

The pass instructions become part of the approved package (research R2), so implementation starts with an owner gate.

## Technical Context

- **Language/Version**: Python 3.14, the project's `uv` environment
- **Primary Dependencies**: the existing ones only: pydantic, typer, pyyaml, numpy, scipy (Hungarian matching), scikit-learn (Cohen's kappa) and jsonschema. No new dependency (research R6).
- **Storage**: files. Labels and runs go under `data/pilot-v3/`, which is git-ignored and private. The manifest, samples and report go under `topics/productdev/benchmarks-v3/pilot-v3/`. Configs go under `configs/productdev/jtbd/`.
- **Testing**: pytest. Unit tests per statistic and per decision branch (hand-computed fixtures), and a mock end-to-end chain on an extended `mini-corpus` fixture with mock answers per pass.
- **Target Platform**: the developer laptop (macOS) for the code and the remote reference; the DGX Spark over VPN for the local reference (Ollama) and the PII review.
- **Project Type**: CLI and library inside the `mobility_model_zoo` package
- **Performance Goals**: none as gates. The local reference takes about 30 s per call; the pilot is about 600 calls, roughly 5 hours, and resumable.
- **Constraints**:
  - Principle XI: the Claude gate (exit 7) and the package check (exits 3 and 7) on every run.
  - Thresholds frozen before the first label (IV).
  - EUR 25 cash cap.
  - The remote reference only on its signed-off route.
  - German and English separate.
  - No change to frozen v1 artefacts (schema hash, `budget.yaml`, pilot-v1 benchmark directory).
- **Scale/Scope**: at least 500 pool chunks per language. Per language: pilot 100, holdout 100, enriched 100 to 200, full benchmark sized after the pilot. 2 references and up to 3 baselines.

## Constitution Check

*GATE: must pass before Phase 0 research; re-checked after Phase 1 design.*

| Principle | Check | Status |
|---|---|---|
| I. Problem-first, not persona-first | The prompt is the package guideline (domain definition, no persona). The user message is the chunk text, plus fixed items in passes 2 and 3 as data. | pass |
| II. Grounded evidence | Every quote and pointer must be a verbatim part of its chunk. Invalid pointers are emptied and counted, never repaired. | pass |
| III. Measure before optimizing | References are two non-Claude families. Benchmark labelers are `teacher_banned`. Contested entries are kept. | pass |
| IV. Validate the riskiest assumption first | The agreement pilot comes before full labeling. The criteria are a verbatim copy of the approved brief, frozen before the first label, and the freeze refuses drift. | pass |
| V. Small and local, budgets per task | Own budget config with an EUR 25 cap. The local reference is preferred; the remote one is used only on its signed-off route. | pass |
| VI. Clean provenance | New sources are `benchmark_only`, fetched once. A reverse separation check runs against training data. Redaction and a full redact-check run before any send. | pass |
| VII. Metadata over inference | Language is detected by code. Source class is recorded per chunk. No label is inferred from metadata. | pass |
| VIII. Fair comparison | The baselines use the same three passes and prompts as the references (FR-005). | pass |
| IX. Reproducible, dated | Seeds are recorded. Model version per pass. Raw files are never overwritten. The manifest has hashes for every input. | pass |
| X. Scope discipline | Teacher labels, training and cairn are out. At most one revision round. | pass |
| XI. No Claude | The Claude gate runs on every run. The pass instructions are added to the owner-approved package (R2) instead of being hard-coded. Wire schemas carry no description text. pilot-v2 Claude labels are never read. | pass, with the owner gate as task 1 |
| Workflow gates | Gate before the labeling run: no Claude model, package unchanged since approval. Gate before reporting: a frozen benchmark version is named. | pass |

Post-design re-check (after Phase 1): the design adds no write path for Claude text outside the package, no new dependency and no change to frozen v1 hashes. **Pass.**

## Project Structure

### Documentation (this feature)

```text
specs/025-pilot-v3-benchmark/
├── spec.md
├── plan.md               # this file
├── research.md           # R1–R13
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   ├── benchmark-manifest-v3.md
│   ├── labeler-pass1.schema.json
│   ├── labeler-pass2.schema.json
│   └── labeler-pass3.schema.json
├── checklists/requirements.md
└── tasks.md              # /speckit-tasks
```

### Source Code (repository root)

```text
src/mobility_model_zoo/productdev/jtbd/
├── v3/
│   ├── __init__.py
│   ├── schema.py         # pass models, wire schemas without descriptions, merge into the labeler output v3
│   ├── passes.py         # three-pass labeling of one chunk; raw/parsed per pass; pointer location
│   ├── tokens.py         # Unicode word tokens with offsets; token IoU
│   ├── agreement.py      # matching at token IoU ≥ 0.5, kappas, MASI alpha, AC1, link F1, bootstrap per language
│   ├── decision.py       # the brief's decision rule as a pure function; keep-always stop; per language
│   ├── sample.py         # seeded pilot/holdout/enriched/full draw; connective and role-word hits
│   ├── bench.py          # manifest state machine, freeze-criteria, revise, consensus, freeze
│   ├── report.py         # agreement.json → report.md
│   └── cli.py            # `jtbd v3 …`
├── guideline_package.py  # extended: instructions/pass{1,2,3}.md from brief `pass_instructions`
├── labeling/runner.py    # extended: dispatch to v3.passes when the config has a `v3:` block; pass-aware estimate
├── labeling/openrouter.py# extended: configurable schema name
├── corpus/separation.py  # extended: reverse check of benchmark sources against training data
└── config.py             # extended: `v3` top-level key

configs/productdev/jtbd/
├── pilot-v3.yaml
├── criteria-pilot-v3.yaml
└── budget-pilot-v3.yaml

topics/productdev/guideline/scout-v3/brief.yaml   # + pass_instructions (Claude draft, owner approval)
topics/productdev/benchmarks-v3/pilot-v3/         # manifest.json, samples.json, report.md

tests/
├── unit/v3/              # tokens, agreement (hand-computed), decision (each branch), sample, schema, bench states
├── fixtures/mini-corpus-v3/   # chunks + mock answers per pass for two references and a baseline
└── integration/test_pilot_v3_chain.py
```

**Structure Decision**: The task-specific code goes into its own `v3/` subpackage, following `cluster/`. The shared runner, gate, package check, budget, pre-send and corpus pipeline are extended, not copied. Frozen v1 modules stay untouched apart from the dispatch and the schema-name option.

## Complexity Tracking

| Addition | Why needed | Simpler alternative rejected because |
|---|---|---|
| In-house MASI alpha and AC1 | The brief defines MASI alpha with both-empty counted as agreement for two coders. | `nltk` is a heavy dependency, and its empty-set behaviour differs. |
| Separate benchmark directory and data root | Keeps pilot-v1's `current` pointer and analysis directory stable. | A shared directory moves pilot-v1's active version. |
| Pass instructions inside the package | Principle XI (3.2.0): text a teacher reads must be owner-approved. | Hard-coded instructions in code would be unapproved Claude text. |

## Owner gates during implementation

1. **Pass instructions:** approve the content of `pass_instructions` in the brief, then `jtbd guide approve` on the reassembled package.
2. **Role words:** approve the role-word approximation for the `actor_pair` sample condition when the criteria are frozen (R10).
3. **Merges:** merge PR #64, then #63 and #65, before the first real labeling run.
4. **Revision:** if the decision says revise, approve the revised brief and package once.
