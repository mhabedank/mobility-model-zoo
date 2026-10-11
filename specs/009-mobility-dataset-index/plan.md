# Implementation Plan: Mobility resource index (multilingual, multimodal)

**Branch**: `claude/mobility-dataset-index-b873c3` | **Date**: 2026-10-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/009-mobility-dataset-index/spec.md`

## Summary

A metadata-only index of mobility resources in every language and modality: texts, audio, video,
images, charts and structured data. Its purpose is to make the zoo's next training data
international and multimodal.

**Where things live** (R1):
- Code, JSON schemas, controlled vocabularies and the licence rule table go in the public package
  as a new shared module, `mobility_model_zoo.catalog`, with a `zoo catalog` CLI.
- The entries live in a new private git repository, one YAML file per entry, because the zoo
  repository is public and the index stays internal for now.

**How entries get in** (R6):
- Deterministic harvesters for catalogue APIs that expose licence and language (data.europa.eu,
  Mobility Database, OpenAlex, Zenodo, Hugging Face) supply most entries.
- A Claude Code skill covers what no API lists (parliament archives, podcasts, ministry series).

**How entries are checked**:
- Every entry runs through automated checks: schema, vocabulary, duplicates, reachability, licence
  evidence and opt-out signals. The signal checker of feature 006 is reused and extended by
  Cloudflare `Content-Signal` and IETF AIPREF `Content-Usage` (R4).
- A versioned rule table derives a provisional `permitted_use`. Entries move through a state
  machine to "cleared". Undecidable cases become owner flags, never per-entry reviews.

**What comes out**:
- A fetch list that pre-fills the existing source and dataset registers, so a later download
  needs no new research (R10).
- Coverage and language reports. The language report shows that XLM-R already covers 33 of the 34
  target languages; only Maltese is missing (R9).

A three-language pilot (Spanish, Polish, Japanese) tests the riskiest assumption before discovery
scales to 2,000+ entries.

## Technical Context

| | |
|---|---|
| **Language/Version** | Python 3.12, the same as the zoo package. |
| **Primary Dependencies** | `pyyaml`, `jsonschema`, `typer` and `httpx` (already in the `release` extra); `rapidfuzz` (already used by `jtbd`). A new optional extra `catalog` bundles them. No new third-party dependency. The local re-check model (R8) runs through the existing local inference setup on the DGX Spark, which uses the OpenAI-compatible client already in `jtbd`. |
| **Storage** | YAML files in the private repository `mobility-model-zoo-catalog` (`$MMZ_CATALOG`). Vocabularies, rules and schemas are package data in the public repository. No database. |
| **Testing** | pytest with fixture catalogs under `tests/fixtures/catalog/`. Network checks and harvesters are tested against recorded responses (`httpx.MockTransport`), so CI never touches the network. The existing ruff configuration applies. |
| **Target Platform** | The development laptop (macOS) and the DGX Spark (Linux) for local re-check runs; GitHub Actions for both repositories. |
| **Project Type** | CLI and library inside the existing package; a Claude Code skill for agent discovery. |
| **Performance Goals** | Loading and validating 2,000 entries (10,000 as the ceiling) in under 2 s, a query in under 1 s (SC-006), a full network re-check of 2,000 entries in under 30 min (R12). |
| **Constraints** | No content download (FR-001, FR-024). One request per second per host, at most eight hosts in parallel. Cash budget 0 €. The OpenAlex account has no payment method, so its free daily allowance is a hard spending limit; the harvester stops at 80% of it. Agent discovery uses the flat-rate subscription, with runs spread over time because of its usage limits. The public repository must never receive entries; `zoo catalog init` refuses paths inside it, and a repository hygiene test enforces that no `entries/` directory exists. |
| **Scale/Scope** | At least 2,000 entries in at least 30 non-German, non-English target languages, at least 50 per modality group (SC-002, SC-003). 34 target languages; 5 harvesters in the first set; 1 discovery skill. |

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / section | Touched | Status before design | Status after design |
|---|---|---|---|
| I, II, X (JTBD task rules) | No; no model or extraction change | n/a | n/a |
| III Measure Before Optimizing | No model result is reported. The index has its own checks: deterministic checks (K1–K8) are reported on their own, and the audit reports agreement, not accuracy (SC-005 wording). | Pass | Pass. The audit names its references: the SPDX matcher and a named local model. |
| IV Riskiest assumption first | Yes | Pass. The spec names the assumption, the criteria are fixed, and the pilot runs before scaling. | Pass. `pilot-v1.yaml` is committed before the first run; `pilot evaluate` refuses changed criteria without a recorded rationale. |
| V Small and Local, budgets | No model. The cost budget applies to discovery. | Pass | Pass. Harvesters and checks run locally; the re-check uses a local model; cash is 0 €. |
| VI Clean provenance | Yes, centrally | Pass | Pass. Every entry has a licence, evidence and signals. Rules reuse `licence-allowlist.yaml` (NC → benchmark_only). Opt-outs and platform terms block clearing. No content and no personal data beyond attribution. Entries stay out of the public repository. The binding decision stays with the source record at fetch time. |
| VII Metadata over Inference | Yes | Pass | Pass. Language, area, kind, type, dates and subdomain are recorded at discovery. |
| VIII Fair comparison, tools per task | Tool choice stated | Pass | Pass. Plain Python, YAML and JSON Schema, the same stack as the compliance register; the reason is one validation path for all registers. |
| IX Reproducible, dated | Yes | Pass | Pass. Each index version is a commit plus a SHA-256; reports and fetch lists carry the version together with the vocabulary and rule versions. |
| Project Scope (layout) | Yes | Pass | Pass. A shared module `src/mobility_model_zoo/catalog/` (like `compliance/` and `datasets/`); no topic folder; entries outside the repository. `docs/layout.md` gains one line. |
| Tasks and Releases | No release | n/a | n/a |
| Resources & Cost (cost order, crawl once) | Yes | Pass | Pass. Order: local, then subscription, then no pay-per-use. Crawl once is unaffected, because the index fetches landing and licence pages only and stores their hashes, not their content. |
| Technical Spikes | No | n/a | n/a |
| Workflow gates | Gate before an experiment | Pass. The pilot's success and kill criteria are in the spec, and the cash budget is 0 €. | Pass |

No violations, so Complexity Tracking stays empty.

## Project Structure

### Documentation (this feature)

```text
specs/009-mobility-dataset-index/
├── plan.md              # this file
├── research.md          # Phase 0: R1–R12
├── data-model.md        # Phase 1: entry, status machine, checks, runs, fetch lists, reports, vocabularies
├── quickstart.md        # Phase 1: validation scenarios
├── contracts/
│   ├── cli.md                   # zoo catalog commands, discovery skill, library interface
│   ├── entry.schema.json        # authoritative entry schema
│   ├── candidate.schema.json    # discovery run lines
│   └── fetch-list.schema.json   # hand-off to downloads
├── checklists/requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (public repository)

```text
src/mobility_model_zoo/catalog/
├── __init__.py          # load(), require_cleared()
├── cli.py               # `zoo catalog …` (mounted in release/cli.py like `zoo data`)
├── model.py             # Entry/Catalog loading, index version (commit + sha256)
├── validate.py          # K1–K3 (schema, vocabulary, integrity, duplicates)
├── rules.py             # K8 + rules.yaml (R5)
├── states.py            # state machine transitions and flags
├── checks.py            # K4–K7 network checks (uses compliance.signals)
├── ingest.py            # run files → entries, dedupe (R7)
├── harvest/             # data_europa.py, mobility_database.py, openalex.py, zenodo.py, huggingface.py
├── query.py             # filters (FR-025)
├── reports.py           # coverage, languages (FR-026, FR-027)
├── audit.py             # sample re-check (R8)
├── fetchlist.py         # fetch lists + proposed records (R10)
├── pilot.py             # pilot evaluate
├── schemas/             # entry, candidate, fetch-list, run (copied from contracts/)
├── vocab/               # languages, areas, source-kinds, resource-types, subdomains, frequencies, base-models
├── rules.yaml
└── templates/           # catalog repo scaffold (catalog.yaml, CI workflow, README)

src/mobility_model_zoo/compliance/signals.py    # + Content-Signal, Content-Usage (R4)
compliance/lists/ai-preferences.yaml            # AIPREF/Content-Signal labels that count as reservation
.claude/skills/catalog-discover/SKILL.md        # agent discovery (contracts/cli.md)
docs/catalog.md                                 # how to run discovery, checks, fetch lists
docs/layout.md, docs/credentials.md             # one line each

tests/catalog/                                  # test_validate, test_rules, test_states, test_ingest,
                                                # test_query, test_reports, test_fetchlist, test_checks,
                                                # test_harvest_*, test_pilot, test_repo_hygiene
tests/fixtures/catalog/                         # fixture catalog (synthetic entries) + recorded HTTP responses
```

### Private repository (created by `zoo catalog init`, owner pushes)

The layout is given in [data-model.md](data-model.md#catalog-repository-layout-private-r1).

**Structure Decision**: Single project. The catalogue is a shared module next to `compliance/` and
`datasets/`, because it serves every topic. Entries are separated from code by repository, not by
folder (R1).

## Delivery order

Each step ends with a measurable result, following the iterative rule.

1. **Schema, vocabularies, validation, fixture catalog** (US1): `validate`, `new`; CI gate.
   Result: scenario 1 passes.
2. **Query and coverage report** (US2). Result: scenario 3 passes.
3. **Rules, state machine, network checks and signal extension** (FR-017, FR-018, FR-020), and the monthly re-check workflow of the catalog repository.
   Result: scenario 2 passes; recorded-response tests for K4–K7 pass.
4. **Ingest, the five harvesters and the discovery skill** (US3), then `init` and the private
   repository (owner pushes).
5. **Pilot** in es, pl and ja. This is a gate: the scale-up waits for `pilot evaluate`.
6. **Fetch list, link and withdraw** (US4, US5). Result: scenario 5 passes.
7. **Language report and audit** (US6, SC-005, SC-008).
8. **Scale-up** to 2,000+ entries over all target languages through scheduled harvester and agent
   runs. Result: SC-002, SC-003 and SC-004 in the coverage report.

## Complexity Tracking

No constitution violations.
