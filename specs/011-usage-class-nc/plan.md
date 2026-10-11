# Implementation Plan: Usage class and non-commercial releases

**Branch**: `011-usage-class-nc` | **Date**: 2026-10-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/011-usage-class-nc/spec.md`

## Summary

Every model gets a declared usage class (`commercial`, `commercial-share-alike`, `non-commercial`, `non-commercial-share-alike`) in `model.yaml`; each release gets a derived class computed by one new module, `compliance/usage.py`, from the licences of its inputs. The module resolves licences through an extended licence list, follows provider routes and teacher records, dataset declarations (including data produced by zoo models) and a new register of third-party models. The release gate (rules 2, 6, 10), the train checks (C-T2, C-T3), the ingest check (C-I2), the dataset training guard, the card renderer, the website and a new audit command `zoo compliance usage` use it. NC-licensed data may now train NC models; data that forbids training stays `benchmark_only`. Published release records are not changed.

## Technical Context

**Language/Version**: Python 3.12+ (repository runs 3.13 locally)

**Primary Dependencies**: existing only: typer, pyyaml, jsonschema, jinja2 (release and site), huggingface_hub (Hub drift check, unchanged)

**Storage**: YAML registers in the repository (`compliance/`, `topics/*/compliance/`, `zoo/models/`)

**Testing**: pytest; fixtures under `tests/release/fixtures/`, `tests/compliance/`, `tests/website/fixtures/`

**Target Platform**: developer machine and GitHub CI, offline

**Project Type**: library with CLIs (`zoo`, `jtbd`)

**Performance Goals**: audit of all models under one minute offline (SC-004)

**Constraints**: fail closed; published release records immutable; no network in checks; no cash costs

**Scale/Scope**: six models, about 100 release-record sources, under ten third-party models

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan complies |
|---|---|
| VI. Clean Provenance, Restrictions Carry Over | Implements the usage class, carry-over from datasets, sources, base models, teachers, third-party models and zoo-model outputs; data that forbids training stays `benchmark_only`; third-party models pinned, training data governs (R1–R8, R11, R12). |
| IX. Reproducible, Dated Releases | Usage class and licence in record, card, Hub tag and website; NC licence and `-nc` suffix; published records untouched (R9, R10, R13). |
| Project Scope (naming) | `<name>-<variant>-nc`; change of class refused (R9, R10). |
| Development Workflow & Quality Gates | Gate before a release checks class against licence and covers third-party models (R4, R8). |
| III. Measure Before Optimizing | `benchmark_only` inputs do not count (FR-004). |
| V. Small and Local | No hosted dependency; all checks offline. |
| Resources & Cost | No cash costs. |

Gate result: pass, no deviations. Re-check after design: pass (the design adds one module, one register file and one command; no principle is weakened).

## Project Structure

### Documentation (this feature)

```text
specs/011-usage-class-nc/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/cli.md
├── checklists/requirements.md
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

```text
compliance/
├── lists/licence-allowlist.yaml        # extended: non_commercial, share_alike, release_licences, trains
├── third-party-models.yaml             # new register
└── providers.yaml                      # output_training_permitted may be non_commercial
src/mobility_model_zoo/
├── compliance/
│   ├── usage.py                        # new: UsageClass, licence resolution, derivation, metadata helper
│   ├── register.py                     # loads third-party-models.yaml; output_training_terms()
│   ├── checks.py                       # meta stage: C-X1, C-X2
│   ├── train.py                        # C-T2/C-T3 by target class
│   ├── ingest.py                       # C-I2 by target class
│   ├── cli.py                          # `zoo compliance usage`
│   └── schemas/{third-party-models,datasets,sources,providers}.schema.json
├── datasets/__init__.py, registry.py   # require_training_allowed(usage_class), produced_by
├── release/
│   ├── gate.py                         # rules 2, 6, 10 use usage.py
│   ├── card.py, templates/model_card.md.j2   # usage line, License section
│   └── schemas/{model,release-record}.schema.json
├── site/                               # hero chip, provenance row, start page, check L3
└── productdev/jtbd/span/datacheck.py   # passes the target class
zoo/models/*/model.yaml                 # usage_class added
zoo/models/*/releases/*.yaml            # drafts only: usage block
zoo/site.yaml                           # zoo-wide copy
docs/adding-a-model.md                  # usage class and -nc
tests/
├── compliance/test_usage.py            # new: derivation, licence list, register checks
├── release/test_usage_class.py         # new: gate cases, NC fixture, marking
├── release/fixtures/…                  # NC fixture model, goldens updated
└── website/…                           # usage class on pages
```

**Structure Decision**: Single project. The derivation lives in `compliance` because the registers and the licence list live there; release, datasets, site and the JTBD data check call it.

## Phases (for /speckit-tasks)

1. Foundations: licence list attributes, `UsageClass`, licence resolution, register loading of `third-party-models.yaml`, schemas (model, release record, datasets, sources, providers, third-party models).
2. US1 + US2 (P1): derivation, gate rules 2/6/10, train and ingest checks, dataset guard, card and Hub marking, NC fixture, refusal fixtures.
3. US3 (P2): third-party register records (xlm-roberta-large and the 009 candidates), C-X1/C-X2, stage metadata helper.
4. US4 (P2): `usage_class` in all `model.yaml`, usage block in draft records, audit command, website marking and copy.
5. Polish: docs, quickstart run, full suite.

## Complexity Tracking

No constitution violations.
