# Implementation Plan: Mobility model zoo with versioned Hugging Face releases

**Branch**: `003-model-zoo-hf-release` | **Date**: 2026-10-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-model-zoo-hf-release/spec.md`

## Summary

The project becomes `mobility-model-zoo`: a collection of mobility models grouped by topic, starting with `productdev` (the JTBD models). This feature builds everything a model release needs except the production model itself, which is feature 004:

1. **Rename and restructure**: GitHub repository, Python distribution and import package (`mobility_model_zoo`), and the Hugging Face organization `mobility-model-zoo`. The proof-of-concept tool `pilot` becomes the JTBD task tool `jtbd` (no alias), its code moves to `mobility_model_zoo.productdev.jtbd`, and its configs move to `configs/productdev/jtbd/`. The constitution is amended to v1.3.0 for a multi-topic zoo. Apache-2.0 license file.
2. **Zoo registry in the repository**: `zoo/topics.yaml`, and per model `model.yaml`, one release record per version, results files and example texts ([data-model.md](data-model.md)).
3. **Release tool `zoo`** ([contracts/cli.md](contracts/cli.md)): staging repo setup with the release token, staging upload from the training machine, a 14-rule release gate, a deterministic card build ([contracts/model-card.md](contracts/model-card.md)), a preview on a private staging branch, publication as one tagged commit, collections, the generated model overview, deprecation, audit and a git history check.
4. **GitHub workflows** ([contracts/workflows.md](contracts/workflows.md)): CI, tag-triggered verify with preview, manually started publish (the owner's approval), weekly audit.
5. **Proof**: a tiny sandbox test model is published end to end to a private repo in the organization, and a draft release record for the span model passes the offline dry run apart from the fields feature 004 delivers.

The try-it field is deferred (free organizations cannot host Gradio Spaces, research R1). The cash budget is €0.

## Technical Context

**Language/Version**: Python 3.12, managed with `uv` (unchanged)

**Primary Dependencies**:
- Base install (inference only, what model users get): `torch`, `transformers`, `huggingface_hub>=1.19`, `safetensors`, `sentencepiece`
- `[release]` extra: `jsonschema`, `pyyaml`, `jinja2`, `typer`, `httpx`
- `[jtbd]` extra: the current pilot dependencies (pydantic, openai, rapidfuzz, scikit-learn, scipy, pandas, matplotlib, trafilatura, pypdf, …)
- `gitleaks` (external binary, only for `zoo history-check`)
- GitHub Actions with `astral-sh/setup-uv`

**Storage**: Files in the repository (`zoo/`, YAML and JSON). Model files only in Hugging Face repos: private `<name>-staging`, public `<name>`. Nothing under `data/` is read by the pipeline.

**Testing**: `pytest`. Unit tests for every gate rule (one failing fixture per rule), schema tests, golden-file test for the card build (byte-identical output), and integration tests against a mocked `HfApi`. One manual end-to-end run with the sandbox model against the real Hub ([quickstart.md](quickstart.md)).

**Target Platform**:
- Pipeline: GitHub-hosted `ubuntu-latest` runners (private repo: 2 vCPU, 7 GB RAM, 14 GB disk).
- `zoo stage`: the DGX Spark or the Mac, wherever training ran.
- Published models: CPU-only machines within each model's stated budget (Principle V).

**Project Type**: single project (library plus two CLIs: `jtbd` for the JTBD task, `zoo` for releases) plus CI workflows

**Performance Goals**: From approval to the published tag in under 30 minutes (SC-007); expected about 10 minutes for a 2.2 GB model.

**Constraints**:
- €0 cash: free HF organization (100 GB private storage), free GitHub Actions minutes.
- One commit per published version (atomicity); tags never overwritten or deleted.
- The publish run releases exactly the reviewed preview (no rebuild); the card build is still deterministic so that previews are reproducible.
- The repository stays private during this feature; it becomes public in feature 004 after `zoo history-check` passes.

**Scale/Scope**: 2 topics (`productdev`, `sandbox`), 2 models in the registry (sandbox test model, span model draft), about 4 published sandbox versions during testing, one public model later (004).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution version: **1.2.0** at plan time. This feature amends it to **1.3.0** (FR-002, research R13). The check below is against 1.2.0 and, where it differs, the planned 1.3.0 text.

| Principle | Touched | Pre-design | Post-design | How the plan complies |
|-----------|---------|------------|-------------|-----------------------|
| I. Problem-First | no | ✅ | ✅ | No change to inputs or prompts. In 1.3.0 it applies to the `productdev` JTBD models. |
| II. Grounded Evidence | no | ✅ | ✅ | Unchanged. Card examples show real model output, not curated output (gate rule 13). |
| III. Measure Before Optimizing | yes | ✅ | ✅ | Cards say "agreement with <reference>", never accuracy (template rule, schema forbids metric names with "accuracy"). Quality metrics must name reference, frozen benchmark and item count (results schema). Every number comes from a results file (gate rule 9). |
| IV. Riskiest Assumption First | no | ✅ | ✅ | No data generation in this feature. 004 handles the gate. |
| V. Small and Local | yes | ✅ | ✅ | Each release record states the RAM budget and `gpu: false`; the card shows speed and memory with the hardware. The usage example runs on a CPU runner (gate rule 12). Hosted HF is distribution only, never a runtime dependency (models load from local files after download). |
| VI. Clean Provenance | yes | ✅ | ✅ | No data is published: upload allow-list (gate rule 11), staging refuses data paths, the card holds a provenance summary only. Teacher terms and `training_allowed` sources are gate rules 6 and 7. `zoo history-check` before the repository goes public. |
| VII. Metadata over Inference | no | ✅ | ✅ | Unaffected. |
| VIII. Fair Comparison | no | ✅ | ✅ | No training or evaluation here. The card shows only results from the shared harness (004). Ludwig: not applicable. |
| IX. Reproducible, Dated Releases | yes | ✅ | ✅ | Semantic versions with dates, release record per version, `recipe.git_commit` check (rule 8), immutable tags with `zoo audit`, deterministic build. The release gate of "Development Workflow & Quality Gates" is implemented as `zoo check`. |
| X. Scope Discipline | no | ✅ | ✅ | No change to model tasks. |
| Technical Spikes | yes | ✅ | ✅ | Spike models and results are never published: `spike_data: false` required (rule 7). The pipeline test uses a non-spike sandbox model in a private repo. |
| Resources & Cost Discipline | yes | ✅ | ✅ | €0 cash. Local and free tiers only; the paid Space options were rejected (R1). |
| Project Scope (amendment) | yes | ⚠ amendment required | ✅ | The scope broadens to a multi-topic zoo. Planned as constitution 1.3.0 (MINOR, no principle removed), done as the first task, before any code. |

No unjustified violations. The scope change is handled through the constitution's amendment process, not as a deviation.

## Project Structure

### Documentation (this feature)

```text
specs/003-model-zoo-hf-release/
├── plan.md              # This file
├── research.md          # Phase 0: R1–R13
├── data-model.md        # Phase 1: topics, models, release records, results, states, gate rules
├── quickstart.md        # Phase 1: end-to-end validation with the sandbox model
├── contracts/
│   ├── cli.md                     # zoo commands, exit codes, gate rules
│   ├── model-card.md              # card sections and metadata
│   ├── workflows.md               # GitHub workflows, tags, secrets
│   ├── topics.schema.json
│   ├── model.schema.json
│   ├── release-record.schema.json
│   └── results.schema.json
├── checklists/requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
LICENSE                                  # Apache-2.0 (new)
pyproject.toml                           # name = "mobility-model-zoo"; extras [jtbd], [release]; scripts jtbd, zoo
.github/workflows/
├── ci.yml
├── release-verify.yml
├── release-publish.yml
└── zoo-audit.yml
zoo/
├── topics.yaml
├── MODELS.md                            # generated
└── models/
    ├── sandbox-pipeline-tiny/           # model.yaml, releases/, results/, examples/
    └── productdev-jtbd-span-xlmr/       # draft for 004: model.yaml, releases/0.1.0.yaml (draft), examples/
src/mobility_model_zoo/
├── __init__.py
├── productdev/
│   └── jtbd/                            # former src/jtbd_pilot (git mv), CLI `jtbd`
├── sandbox/
│   ├── model.py                         # PipelineTestModel (PyTorchModelHubMixin)
│   └── build_test_model.py
└── release/
    ├── cli.py                           # `zoo` (typer)
    ├── registry.py                      # load and validate topics, models, records, results
    ├── schemas/                         # copies of contracts/*.schema.json (single source, tested equal)
    ├── gate.py                          # the 14 rules, one function each
    ├── hub.py                           # all HfApi calls in one place (mockable)
    ├── card.py                          # Jinja2 rendering + Hub validation
    ├── templates/model_card.md.j2
    ├── usage.py                         # fresh-venv usage check
    ├── examples.py                      # run the staged model on the example texts
    ├── publish.py                       # stage, preview, publish, deprecate
    ├── index.py                         # MODELS.md and collections
    ├── audit.py
    └── history.py                       # history-check (paths + gitleaks)
tests/
├── unit/ …                              # existing JTBD tests, imports and CLI name updated
├── integration/ …                       # existing
└── release/
    ├── fixtures/                        # a valid sandbox registry + one broken copy per rule
    ├── test_schemas.py
    ├── test_gate_rules.py
    ├── test_gate_required_fields.py     # SC-005
    ├── test_card_build.py               # golden file, determinism
    ├── test_publish.py                  # mocked HfApi: atomic commit, tag refusal, resume after failure
    └── test_index.py
```

**Structure Decision**: One package `mobility_model_zoo` with topic subpackages and a shared `release` subpackage. Guideline (also written into constitution 1.3.0): how a model is built and measured belongs to its **task** (one tool per task, shared by every model of that task, for example `jtbd` for the span model and the 4B model); how a model is released is the same for every model (`zoo`). Code shared between tasks is extracted into a common module only when a second task needs it, not in advance. Topics add subpackages and `zoo/models/` entries; the release tool stays model-agnostic and needs no change for a new topic (US3). All Hub calls go through `release/hub.py` so tests can mock the Hub completely.

## Implementation order

0. Branches: commit the open work on `001-jtbd-extraction-pilot`, fast-forward `main` to it (no divergence: `main` is 9 commits behind), branch `003-model-zoo-hf-release` from `main`, and merge it back by pull request before the first real release run, because `workflow_dispatch` workflows must be on the default branch `main`.
1. Constitution 1.3.0; `LICENSE`; README rewrite as the zoo overview.
2. Rename: `git mv src/jtbd_pilot src/mobility_model_zoo/productdev/jtbd`, rewrite imports, CLI `pilot` → `jtbd`, `git mv configs/*` → `configs/productdev/jtbd/` (with the default config path updated), `pyproject.toml` (name, extras, scripts), README, the open 001 tasks rewritten to the new commands, a path-and-command note at the top of the 001/002 documents, `gh repo rename`. The benchmark keeps its identifier `pilot-v1` (it is a version name, not a tool name). Freeze hashes are content-based, so moving the configs does not change them; a test compares `compute_hashes()` before and after the move. All existing tests pass before anything else changes.
3. Registry, schemas and `zoo validate` with fixtures; `zoo/topics.yaml`; sandbox model files.
4. Gate rules, card template and build (golden test), usage and examples checks.
5. Hub layer, `stage`, `preview`, `publish`, `index`, `audit`, `deprecate`; mocked tests.
6. Workflows; HF organization and tokens (manual, owner); end-to-end sandbox run per quickstart scenarios 2–6.
7. Span model draft record and offline dry run (scenario 7); hand the list of missing fields to the 004 spec.
8. `zoo history-check` implemented and run once; findings recorded for 004.

## Risks

| Risk | Mitigation |
|------|-----------|
| Hub validation rules change and add warnings | Rule 10b runs on every verify; failures are visible before publishing, never after |
| Tags on the Hub can be deleted by a token holder | Pipeline never deletes; `zoo audit` weekly detects drift; release record stores commit and card hashes |
| The rename breaks the JTBD tool (001 still has open ops tasks) | Rename is one commit with the full test suite green; the open 001 tasks are rewritten to `jtbd ...`; a test checks that no `pilot ` command remains in README and open tasks |
| A write token can probably change repo visibility (unverified) | Fine-grained token limited to the organization; `zoo` never changes visibility; audit checks sandbox repos stay private |
| GitHub Actions minutes for private repos | Verify and publish about 10 minutes each; well under the free allowance at a few releases per month |

## Complexity Tracking

No constitution violations to justify. The constitution amendment (scope) is a planned task, not a deviation.
