# Implementation Plan: Compliance harness

**Branch**: `006-compliance-harness` | **Date**: 2026-10-08 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/006-compliance-harness/spec.md`; legal basis [legal-research/report.md](legal-research/report.md) (not legal advice)

## Summary

The zoo gets a compliance register, fail-closed checks along the data and release path, generated public documents, and a compliance patch of the published model:

1. **Register** (R1, R2):
   - Shared records in `compliance/`: controller, provider routes, decisions, waivers, requests, suppression, legal watch, recipients.
   - Topic records in `topics/<topic>/compliance/`: source classes, sources per origin, datasets.
   - Release compliance records next to the release records.
   - YAML validated by JSON Schemas; no personal data of data subjects.
2. **Checks** (R3–R9, R11, R12): a shared package `mobility_model_zoo.compliance` with 49 numbered checks ([contracts/checks.md](contracts/checks.md)), wired into the existing tools:
   - `jtbd source` (fetch);
   - `corpus autochunk` (ingest);
   - the labeling runner (pre-send and post-receive);
   - `span data-check` (train);
   - `zoo check` rule 16 (release);
   - CI and the weekly audit (meta, licence, repository, notices, drift).
3. **Documents** (R10): rendered from the register and checked for drift, per [contracts/documents.md](contracts/documents.md):
   - `PRIVACY.md`, `COPYRIGHT_POLICY.md`, `SECURITY.md`, `NOTICE`, `THIRD_PARTY_NOTICES.md`;
   - REUSE files and the rights-request template;
   - the Art. 30 record and LIA/DPIA;
   - per release: the AI Act record and the training-data summary;
   - new model-card sections.
4. **Fixes found in the code** (from the code read): robots.txt fails open; no TDM signals; `register` skips signals; `retention_until` is never enforced; the pre-send step trusts a stored flag; the OpenRouter provider is unchecked and teacher routes are unpinned; `training_on_outputs_permitted` is hard-coded to `True`.
5. **scout-large 0.1.2** (R13): retrospective records (sources, routes from the logs, the Claude risk acceptance, Art. 9 counts, redaction recall), a new card, and the same files and metrics. Published through the existing pipeline after owner approval.

## Technical Context

**Language/Version**: Python 3.12 with `uv` (unchanged).

**Primary Dependencies**:
- Existing: `jsonschema`, `pyyaml`, `jinja2`, `typer`, `httpx` (release and jtbd extras).
- New dev dependency: `reuse` (REUSE lint).
- New optional dependency: `anthropic` (SDK) in a new `labeling-api` extra, for the future API backend.
- No Presidio or spaCy (R5).
- `gitleaks` is already used.

**Storage**:
- Register: YAML in git.
- Crawl manifest, corpus shingle index, scan reports' inputs and the deletion log: `data/compliance/` (gitignored).
- Scan reports (counts and hashes only) and release compliance records: in git.

**Testing**:
- `pytest` with one failing fixture per check id and a clean fixture per stage (SC-003).
- `httpx.MockTransport` for robots.txt, TDMRep, ai.txt and terms pages.
- A synthetic redaction test set (300 sentences, DE and EN).
- Fixture cards and registers; release fixtures for rule 16; drift tests.
- No real personal data in tests.

**Target Platform**: macOS and Linux development; GitHub Actions `ubuntu-latest` for CI.

**Project Type**: single project (library plus the CLIs `zoo` and `jtbd`).

**Performance Goals**:
- `zoo compliance check --ci` under 30 s.
- The publication scan for one release under 2 min on the M3 Pro for the about 3.5 M characters of corpus.
- The default `pytest` run stays under 4 min.

**Constraints**:
- Fail closed everywhere.
- No personal data of data subjects in git or in published files.
- Published 0.1.0/0.1.1 records and cards unchanged.
- Patch 0.1.2 with identical files.
- Cash budget €0: no hosted labeling runs in this feature.
- All documents in English.

**Scale/Scope**:
- 87 source origins and about 4 source classes for productdev.
- About 10 provider routes from 23 run folders.
- 49 check ids, about 12 generated documents, 1 patch release.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution **2.0.0**. The task touched is `jtbd` (fetch, ingest, label and train paths); releases go through `zoo`.

| Principle | Touched | Pre-design | Post-design | How the plan complies |
|-----------|---------|------------|-------------|-----------------------|
| I. Problem-First | no | ✅ | ✅ | No model input changes. |
| II. Grounded Evidence | yes | ✅ | ✅ | Verbatim quotes stay spans of the user's input. The overlap scan applies to published files, not to model outputs. |
| III. Measure Before Optimizing | yes | ✅ | ✅ | Redaction recall and Art. 9 counts are measured on named sets with thresholds (D9). Metrics are unchanged in 0.1.2. |
| IV. Riskiest Assumption First | yes | ✅ | ✅ | The riskiest compliance assumption, "the past routes are documentable", is tested first, from the logs (R7), before any document claims it. |
| V. Small and Local, Budgets per Task | yes | ✅ | ✅ | Local-first labeling and the local PII review (R5). Hosted labeling only through allowlisted, pinned routes. Cash budget €0 in this feature. |
| VI. Clean Provenance | yes | ✅ | ✅ | Register per source and dataset with licence, permitted use, redistribution, retention and opt-out verdicts. §44b only (D5). Art. 9 quarantine (D12). Datasets stay out of git. |
| VII. Metadata over Inference | no | ✅ | ✅ | |
| VIII. Fair Comparison | no | ✅ | ✅ | Benchmark and harness unchanged. |
| IX. Reproducible, Dated Releases | yes | ✅ | ✅ | Release compliance records frozen per version. 0.1.2 is a patch with identical files. Datasets are not published. |
| X. Scope Discipline | no | ✅ | ✅ | |
| Project Scope (layout) | yes | ✅ | ✅ | Topic records go in `topics/productdev/compliance/`; shared records go in `compliance/`. |
| Tasks and Releases | yes | ✅ | ✅ | A shared module, because two consumers (`jtbd`, `zoo`) need it from the start. |
| Resources & Cost | yes | ✅ | ✅ | No cash cost. Crawl once kept. Retention enforced (R8). |
| Technical Spikes | no | ✅ | ✅ | `spike/` untouched; spike runs appear in the recipients summary like all runs. |
| Quality Gates | yes | ✅ | ✅ | The gate before a release gains rule 16. Deviations: none. |

Gate result: pass.

## Project Structure

### Documentation (this feature)

```text
specs/006-compliance-harness/
├── plan.md
├── research.md            # R1–R15, owner decisions D5–D13
├── data-model.md          # register records, release compliance record, crawl manifest
├── quickstart.md
├── contracts/
│   ├── cli.md             # zoo compliance and changed commands
│   ├── checks.md          # 49 check ids
│   └── documents.md       # what each generated document contains
├── legal-research/        # report.md and six research notes (2026-10-08)
├── checklists/requirements.md
└── tasks.md               # /speckit-tasks
```

### Source Code (repository root)

```text
src/mobility_model_zoo/compliance/
├── __init__.py
├── register.py            # load, validate, query; unknown/waiver handling
├── schemas/               # *.schema.json for every record type
├── checks.py              # stage functions → findings; fail-closed runner
├── signals.py             # robots.txt (AI agents), TDMRep, X-Robots-Tag/meta, ai.txt, ToS screen
├── scan.py                # PII patterns (DE/EU), Art. 9 lexicon, corpus shingle index and overlap
├── recipients.py          # labeling logs → recipients summary
├── render.py              # documents and card sections
├── templates/             # Jinja templates for every generated document
├── hashing.py             # HMAC identifiers for requests and suppression
└── cli.py                 # `zoo compliance …` (mounted in release/cli.py)

src/mobility_model_zoo/productdev/jtbd/
├── sources/snapshot.py    # fail-closed signals, new user agent, crawl manifest
├── cli.py                 # register --signals; doctor retention
├── corpus/autochunk.py    # ingest checks, Art. 9 quarantine
├── labeling/runner.py     # pre-send and post-receive checks
├── labeling/openrouter.py # pinned providers; answering provider verified
├── labeling/anthropic_api.py  # new backend (not run in this feature)
├── span/datacheck.py      # train checks
└── span/results.py        # training_on_outputs_permitted from the route record

src/mobility_model_zoo/release/
├── gate.py                # rule 16; rule 6 from routes; rule 10 card lint
├── card.py, templates/model_card.md.j2   # new sections from the register
└── cli.py                 # mounts `compliance`

compliance/                # controller, providers, decisions, waivers, requests, suppression, legal-watch, recipients, lists/
topics/productdev/compliance/   # source-classes.yaml, sources.yaml, datasets.yaml
zoo/models/scout-large/releases/0.1.2.yaml, 0.1.2.compliance.yaml, 0.1.2.ai-act.md, 0.1.2.training-data-summary.md
PRIVACY.md  COPYRIGHT_POLICY.md  SECURITY.md  NOTICE  THIRD_PARTY_NOTICES.md  REUSE.toml  LICENSES/
.github/ISSUE_TEMPLATE/rights-request.yml
docs/compliance/record-of-processing.md, lia-dpia.md
tests/compliance/          # per-check fixtures, redaction-set (synthetic), render/drift, signals, scans
```

**Structure Decision**: One shared compliance package used by `jtbd` and `zoo`. Shared register at the top level, topic register under `topics/<topic>/compliance/` (constitution 2.0.0 layout), release evidence next to the release records.

## Implementation phases

| Phase | Content | Done when |
|---|---|---|
| 1 Register | schemas, loader, controller, decisions D1–D13 and `D-parl-art9`/`D2-claude-0.1.x`, legal watch, lists | `check --stage meta` passes; seeded meta violations fail |
| 2 Evidence for scout-large | `recipients` from the logs; route records per provider; `bootstrap-sources`; source classes and LIA; Art. 9 scan; redaction recall | every record of the 0.1.x release complete or `unknown` with date |
| 3 Documents | templates, render, drift, REUSE, card sections, AI Act and training summary | `render --check` and `reuse lint` pass |
| 4 Release checks | rule 16 (meta, model, publication, card, licence, repository, notices, sign-off); rule 6 from routes; publication scan | release fixtures with seeded violations fail; clean passes |
| 5 Data path | signals at fetch, register `--signals`, ingest, pre-send and post-receive, retention, train; Anthropic API backend | each seeded violation fails at its stage |
| 6 Requests and CI | requests, suppression, `zoo-audit` meta, `ci.yml` compliance step | CI green |
| 7 scout-large 0.1.2 | release record, compliance record, scan, sign-off, tag, preview, owner approval, publish | published; audit ok |

## Complexity Tracking

No constitution violation. Choices made instead of the larger alternatives:
- in-house signal checks instead of external services;
- regex plus the local model review instead of Presidio;
- a separate compliance file per release instead of extending frozen records.

All are recorded in research.md.
