---
description: "Tasks for feature 006: compliance harness"
---

# Tasks: Compliance harness

**Input**: Design documents from `specs/006-compliance-harness/`: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md), [legal-research/report.md](legal-research/report.md)

**Tests**: Included. SC-003 requires one failing fixture per check id. Fail-closed checks are only trustworthy if every failure path is tested. No test may contain real personal data. Fixtures use invented names like "Erika Mustermann" and example.org addresses.

**Organization**: Tasks are grouped by user story (US1–US6 from spec.md).
- **(ops)** marks a step that touches GitHub or Hugging Face or needs the owner.
- **GATE** marks a point where work stops until a condition holds.
- **Check ids:** "C-xx" are the ids in [contracts/checks.md](contracts/checks.md); the prefix keeps them apart from decision ids (`D…`) and task ids. Example: C-F1 is the robots.txt check, C-M2 the overdue-review check. Code, waivers and failure messages use the same ids.
- **Code paths:** `src/mobility_model_zoo/compliance/`, `src/mobility_model_zoo/productdev/jtbd/` (shortened to `jtbd/`), `src/mobility_model_zoo/release/`.

**Order note**: US3 (scout-large 0.1.2, P1) is scheduled after US4 (P2), because rule 16 needs the publication scan and the card lint from US4. US5 and US6 follow; they protect future data generation and requests, which do not block the patch.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [X] T001 Record the baseline in `specs/006-compliance-harness/validation.md` under "Baseline": run `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --offline pytest -q` and `uv run zoo validate --all` and write down the counts and runtime.
- [X] T002 Add `reuse` to the dev group in `pyproject.toml`. Add `[project.optional-dependencies] labeling-api = ["anthropic>=0.69"]`. Add `src/mobility_model_zoo/compliance/schemas/*.json` and `templates/*` as package data if hatchling does not include them. Run `uv lock` and check that the base dependencies are unchanged.
- [X] T003 [P] Add `MMZ_SUPPRESSION_KEY=` with a comment ("random secret for HMAC hashes of request identifiers; never commit") to `.env.example`. Add `/data/compliance/` to `.gitignore` (already covered by `data/`; verify with `git check-ignore`).

---

## Phase 2: Foundational

**Purpose**: The compliance package skeleton that every story uses. **No story work starts before this phase is complete.**

- [X] T004 Create `src/mobility_model_zoo/compliance/__init__.py` and `findings.py`:
  - `Finding(check_id, stage, record, field, reason)`.
  - `StageFailed(findings)`, which maps to exit code 2.
  - `run_stages(stages, ctx)`: runs stages in order and stops at the first stage with findings (fail closed, FR-006).
  - `Unknown` handling: the value `"unknown"` is valid only with a sibling `unknown_checked_at` date, and it fails any check that needs the value unless `register.waiver_for(check_id, record)` returns an unexpired waiver.
- [X] T005 Create `src/mobility_model_zoo/compliance/register.py`. It loads:
  - `compliance/*.yaml`;
  - `topics/*/compliance/*.yaml`;
  - `zoo/models/*/releases/*.compliance.yaml`.

  Every file is validated against the schema with the same stem in `compliance/schemas/`. Lookups: `source(id)`, `sources_for(model, version)`, `route(id)`, `routes_for_run(run_dir)`, `decision(id)`, `waiver_for(check, record)`, `controller()`. Every record requires `owner`, `last_reviewed` and `next_review` (ISO dates); a missing field is a finding of check C-M1.
- [X] T006 Create `src/mobility_model_zoo/compliance/cli.py` (Typer app `compliance`) and mount it in `src/mobility_model_zoo/release/cli.py` as `zoo compliance`. Implement `check [--ci] [--stage S] [--model M --version V]`, with the other commands from contracts/cli.md as stubs that exit 1 "not implemented". Exit codes follow the `zoo` convention. Output lines read `stage / record / field / reason`.
- [X] T007 [P] Write `tests/compliance/conftest.py`. It has a fixture `register_tree(tmp_path)` that builds a minimal valid register (controller, one source class, one source, one route, one decision) in a temporary repository layout, and a helper `seed(path, key, value)` for violations. Also write `tests/compliance/test_findings.py`: the runner stops after the first failing stage; `unknown` without a date fails; `unknown` with a valid waiver passes; an expired waiver fails.

**Checkpoint**: `zoo compliance check` runs against an empty stage list.

---

## Phase 3: User Story 1 - One register answers every compliance question (Priority: P1) 🎯 MVP

**Goal**: The register exists with schemas, the decisions of 2026-10-08, the legal watch list, and complete records for everything behind `scout-large` 0.1.x.

**Independent Test**: quickstart scenario 1. `zoo compliance check --stage meta` passes. Seeding an overdue review, an expired waiver or a missing field makes it fail with the record named.

### Tests for User Story 1

- [X] T008 [P] [US1] Write `tests/compliance/test_register_schemas.py`. For each schema there is one valid and one invalid example, covering:
  - source `permitted_use` not in `training_allowed|benchmark_only`;
  - `redistribution` not in `allowed|not_allowed|unclear`;
  - source class `copyright_basis: tdm_60d` (rejected per D5);
  - route `access_path` not in `local|api|openrouter|consumer_cli`;
  - a waiver without `expires_at`, or with `expires_at` more than 6 months after `approved_at`;
  - request `type` not in `objection|erasure|access|takedown|opt_out`;
  - release compliance record `exclusion_basis` other than `art2_12` while `monetisation: none`.
- [X] T009 [P] [US1] Write `tests/compliance/test_meta.py` with one failing fixture each:
  - C-M1: schema violation;
  - C-M2: `next_review` yesterday; legal-watch `review_by` yesterday without `reviewed_at`;
  - C-M3: an expired waiver;
  - C-M4: an open request past its deadline.

  The clean register passes.

### Implementation for User Story 1

- [X] T010 [US1] Write the JSON Schemas in `src/mobility_model_zoo/compliance/schemas/` exactly as specified in data-model.md: `controller`, `source-classes`, `sources`, `datasets`, `providers`, `recipients`, `decisions`, `waivers`, `requests`, `suppression`, `legal-watch`, `release-compliance`. Copy them to `specs/006-compliance-harness/contracts/schemas/`, and add a test in `tests/compliance/test_register_schemas.py` that the copies are byte-identical. Constraints to encode verbatim:
  - **Source classes:** `copyright_basis` enum `tdm_44b|official_work_5|licence` ("§60d is not allowed"); `art9_handling: allowed_by_decision` requires `decision_id`.
  - **Sources:**
    - `licence` is an SPDX id, `LicenseRef-*` or `unknown`;
    - NC/ND licences require `permitted_use: benchmark_only`;
    - `quote_allowed: true` only with class `official_work_5` or a `CC-BY*` licence;
    - `signals.*` take `allow|deny|absent`;
    - `tos_verdict` takes `allow|deny|owner_confirmed_allow`.
  - **Datasets:** `status` enum `active|broken_at_source|rejected`, and `reason` is required unless `active`.
  - **Providers:** `consumer_cli` routes must have `allowed_for: []`.
  - **Waivers:** fields `id, check, scope, rationale, approved_by, approved_at, expires_at`; `check` matches `^C-[A-Z][0-9]$`; `expires_at` at most 6 months after `approved_at`.
  - **Release compliance:** `state` enum `draft|signed_off|published`.
- [X] T011 [US1] Implement the meta stage (checks C-M1 to C-M4) in `src/mobility_model_zoo/compliance/checks.py` and wire it into `zoo compliance check --stage meta` and `zoo validate --all` (`release/cli.py`). T008 and T009 pass.
- [X] T012 [P] [US1] Create `compliance/controller.yaml`:
  - name: "Martin Habedank (private person)";
  - `privacy_contact`: `privacy@miskatonic-analytics.com`; `general_contact`: `contact@miskatonic-analytics.com`;
  - `imprint_url`: https://miskatonic-analytics.com/imprint.html; `website_privacy_url`: https://miskatonic-analytics.com/privacy.html;
  - `supervisory_authority`: "Berliner Beauftragte für Datenschutz und Informationsfreiheit";
  - `commercial_activity: none`;
  - owner and review dates (next review 2027-04-08).
- [X] T013 [P] [US1] Create `compliance/decisions.yaml` with the owner decisions:
  - **Context decisions 1–4 of spec.md:**
    - `D-routing`: local first, pinned EU/DPF zero-retention providers only;
    - `D-claude-api`: future reference labels via the Anthropic API with a DPA;
    - `D-contact`: private controller, Miskatonic contact, no branding;
    - `D-order`: 006 before 005.
  - **Planning decisions D5–D13** from research.md, each with date 2026-10-08, rationale, scope and `review_by`. D6 is reviewed at 2026-12-17 (BGH I ZR 281/25).
  - **`D-parl-art9`:** political content in parliamentary speeches by office holders, Art. 9(2)(e) (research R6).
  - **`D-claude-risk-0.1.x`:** a dated risk acceptance for the Claude reference labels made via the consumer CLI subscription. Scope: `scout-large` 0.1.x benchmark reference labels; review by 2027-04-08.
- [X] T014 [P] [US1] Create `compliance/legal-watch.yaml` with these items, each with `expected`, `review_by` (expected date plus 14 days, or 2027-01-15 if unknown) and `affects`:
  - BGH I ZR 281/25 (expected 2026-12-17; affects D6, C-F6);
  - ProdHaftG transposition (2026-12-09);
  - AI Act Art. 50(2) grace end (2026-12-02);
  - GEMA v OpenAI appeal;
  - CJEU C-250/25;
  - GDPR omnibus Art. 88bis;
  - final CRA FOSS guidance C(2026) 5252;
  - Latombe v Commission appeal.
- [X] T015 [P] [US1] Create the lists in `compliance/lists/`:
  - `ai-user-agents.yaml`: GPTBot, ChatGPT-User, OAI-SearchBot, CCBot, ClaudeBot, Claude-Web, anthropic-ai, Google-Extended, PerplexityBot, Bytespider, Applebot-Extended, meta-externalagent, Amazonbot, cohere-ai, Diffbot, omgili, Timpibot.
  - `denylist.yaml`: empty, with a comment on what goes in it.
  - `piracy-domains.yaml`: an initial list of well-known shadow-library domains, with a `source` comment.
  - `licence-allowlist.yaml`: CC0-1.0, CC-BY-4.0, CC-BY-SA-4.0 (marked share-alike), CC-BY-3.0, PDDL-1.0, ODC-By-1.0, MIT, Apache-2.0, BSD-3-Clause, `LicenseRef-official-work-UrhG-5`, `LicenseRef-OGL-UK-3.0`, `LicenseRef-Open-Parliament-Licence`, `LicenseRef-US-PD`.
  - `special-categories.yaml`: German and English terms per Art. 9 category.
  - `card-lint.yaml`: required sections per topic kind, and forbidden patterns per research R11.
- [X] T016 [US1] Implement `zoo compliance recipients --runs DIR…` in `src/mobility_model_zoo/compliance/recipients.py`.
  - **Input:** every `*/manifest.json` and `*/raw/*.json` under the given run folders.
  - **Output:** `compliance/recipients.yaml`, grouped by (`model_id`, backend, `backend_meta.provider` or `unrecorded`), with `roles`, `first_call`, `last_call`, `calls_ok`, `calls_error` and `runs`.
  - **Never** text, chunk ids or raw bodies.

  Test in `tests/compliance/test_recipients.py` with a fixture run folder; the output contains no `chunk_id`.
- [X] T017 [US1] Run `uv run zoo compliance recipients --runs data/runs data/span-train-v1/runs` and commit `compliance/recipients.yaml`. Check by hand that it contains no text, then record the counts under "US1" in `validation.md`.
- [X] T018 [US1] Create `compliance/providers.yaml` with one route per distinct entry in `recipients.yaml`. For each hosting provider seen (OpenAI, DeepInfra, Wafer and the others in the file), look up its current terms and privacy page and record:
  - `terms_url`, `terms_sha256` (of the fetched page), `terms_checked_at`;
  - `region`, `dpf_listed` (search the DPF list at dataprivacyframework.gov);
  - `zero_data_retention`, `training_on_inputs`;
  - `output_training_permitted` with the quoted clause.

  Unknown facts become `unknown` with `unknown_checked_at`.
  - **Claude:** route `claude-consumer-cli` with `access_path: consumer_cli`, `allowed_for: []`, and a note on the Consumer Terms §3 clause.
  - **Local Ollama:** routes `access_path: local`, `allowed_for: [teacher, reference, pii_review]`.
  - **Hosted routes:** `allowed_for` stays empty until the allow rule in data-model.md holds: (EU or `dpf_listed`) and `zero_data_retention` and not `training_on_inputs` and `signoff`.
- [X] T019 [US1] Create `topics/productdev/compliance/source-classes.yaml` with four classes:
  - `parliamentary-records` (`copyright_basis: official_work_5` or licence, `art9_handling: allowed_by_decision`, `decision_id: D-parl-art9`);
  - `cc-papers` (licence);
  - `research-interviews` (licence; `human_subjects`);
  - `forum-review` (`tdm_44b`, benchmark only, `art9_handling: quarantine`).

  Each class gets an LIA object (`purpose`, `necessity`, `balancing`, `safeguards`, `decided_at` 2026-10-08) and a retention rule "reproduce frozen benchmark and current model training set; review 24 months after freeze".
- [X] T020 [US1] Implement `zoo compliance bootstrap-sources --topic T --model M --version V [--benchmark-config C]` in `src/mobility_model_zoo/compliance/bootstrap.py`. It covers each origin in the release record's `provenance.sources` (`used_by: <model>@<version>`) and, with `--benchmark-config`, every snapshot behind the main and holdout chunks of that config (`used_by: benchmark:<name>`). For each origin it:
  - reads the local `data/snapshots/*/source.yaml` files with that `origin_url`, the entry in `data/sources/source-plan.yaml` and, for Zenodo URLs, the Zenodo API record (title, creators, licence, description);
  - writes a source record with `class` (from the source type and publisher), title, creators, publisher, licence (SPDX), licence URL, attribution text (TASL), `modifications: "extracted text, split into chunks, personal identifiers redacted, labeled by language models"`, `permitted_use`, `redistribution: not_allowed` for all (training texts are not redistributed), `quote_allowed`, `retention_until` from the snapshots, `storage: data/snapshots` and `used_by`;
  - writes signals as a retrospective check: fetch today's robots.txt, TDMRep and ai.txt, mark `retrospective: true` and set `checked_at` to today;
  - for Zenodo interview records, searches the description for consent and ethics terms and sets `consent_or_ethics` to the quoted sentence, or to `unknown` with a decision item appended to `validation.md`.

  Nothing is invented: missing values are written as `unknown` with the date. Test in `tests/compliance/test_bootstrap.py` with a fixture snapshot and a mocked Zenodo response.
- [X] T021 [US1] Run `bootstrap-sources --topic productdev --model scout-large --version 0.1.1 --benchmark-config configs/productdev/jtbd/pilot-v1.yaml` and write `topics/productdev/compliance/sources.yaml`.
  - Review every record with `unknown` and resolve what can be found from the source page (creators of papers, Bundestag as publisher).
  - Commit, then run `zoo compliance check --stage meta`.
  - **GATE:** all 87 training origins and every benchmark snapshot source of `pilot-v2` have records, and every remaining `unknown` is either covered by a waiver with expiry or listed for the owner in `validation.md` under "Owner decision items".
- [X] T022 [US1] Check the platform terms of sources obtained through an API (research R16). For the class `forum-review` (Reddit Data API), fetch the current Reddit Developer Terms, Data API Terms and Public Content Policy. Record `platform_terms` on each Reddit source record: `url`, `sha256`, `checked_at`, and `ml_use` and `hosted_processing` (`allowed`, `not_allowed` or `unclear`), each with the quoted clause. Do the same for any other API-fetched source class. Where a use that already happened (benchmark labeling by hosted models) is `not_allowed` or `unclear`, add an owner decision item to `validation.md` with three options:
  - keep the past use, document the assessment and stop new hosted processing;
  - replace the items in a future benchmark version;
  - remove them from the next benchmark version.

  The frozen benchmark is not edited.
- [X] T023 [P] [US1] Create `topics/productdev/compliance/datasets.yaml` with `datasets: []` and a comment that third-party datasets of this topic are listed here, and that feature 005 adds the security and condition-monitoring files with this schema.

**Checkpoint**: The register is complete for everything published, and the meta stage passes.

---

## Phase 4: User Story 2 - Public compliance documents are generated (Priority: P1)

**Goal**: Every public compliance text is rendered from the register and drift-checked.

**Independent Test**: quickstart scenario 2. `zoo compliance render --check` and `reuse lint` pass, a hand edit is detected, and `PRIVACY.md` names every route in `recipients.yaml`.

### Tests for User Story 2

- [X] T024 [P] [US2] Write `tests/compliance/test_render.py`. On the fixture register, rendering produces every file in contracts/documents.md, and each file contains its required elements (one assertion per element listed in the contract). Rendering twice gives byte-identical output.
- [X] T025 [P] [US2] Write `tests/compliance/test_notices.py`. Seeded violations:
  - C-N1: a route in `recipients.yaml` missing from `PRIVACY.md`;
  - C-N2: a retention in `PRIVACY.md` differs from the register;
  - C-N3: a hand-edited `NOTICE`.

  Each fails; the clean render passes.

### Implementation for User Story 2

- [X] T026 [US2] Create the Jinja templates in `src/mobility_model_zoo/compliance/templates/`: `PRIVACY.md.j2`, `COPYRIGHT_POLICY.md.j2`, `SECURITY.md.j2`, `NOTICE.j2`, `THIRD_PARTY_NOTICES.md.j2`, `REUSE.toml.j2`, `rights-request.yml.j2`, `record-of-processing.md.j2`, `lia-dpia.md.j2`, `ai-act.md.j2`, `training-data-summary.md.j2`. Content per contracts/documents.md, in English.
  - `PRIVACY.md` has the Art. 21 objection right as its own section.
  - Contacts come only from `controller.yaml`.
  - No text mentions Miskatonic other than the e-mail addresses and the imprint and privacy links.
- [X] T027 [US2] Implement `src/mobility_model_zoo/compliance/render.py` and `zoo compliance render [--check]`. It writes these files and nothing else; in `--check` mode it compares and reports C-N3 per file.
  - `PRIVACY.md`, `COPYRIGHT_POLICY.md`, `SECURITY.md`, `NOTICE`, `THIRD_PARTY_NOTICES.md`, `REUSE.toml`;
  - `LICENSES/` (Apache-2.0, MIT, CC-BY-4.0, CC-BY-SA-4.0 texts from SPDX);
  - `.github/ISSUE_TEMPLATE/rights-request.yml`;
  - `docs/compliance/record-of-processing.md`, `docs/compliance/lia-dpia.md`;
  - per release with a compliance record: `zoo/models/<m>/releases/<v>.ai-act.md` and `<v>.training-data-summary.md`.
- [X] T028 [US2] Implement the notices checks C-N1 and C-N2 in `checks.py`. Add the documentation-only stage set to `zoo compliance check --ci`: meta, notices and drift. T024 and T025 pass.
- [X] T029 [US2] Add the new card sections to the model card. Edit `src/mobility_model_zoo/release/card.py` (`SECTIONS`) and `templates/model_card.md.j2`:
  - "Training data and attribution": a TASL table from the source records plus modification notes and the NOTICE text, including the XLM-R MIT notice when `base_model` is `FacebookAI/xlm-roberta-large`.
  - "Teacher and labeling models": route, hosting provider and terms checked date.
  - "Out-of-scope use".
  - "Dual-use considerations": only for topics marked `security` in `card-lint.yaml`.
  - "Privacy and personal data": a summary, with links to `PRIVACY.md`, `COPYRIGHT_POLICY.md` and the AI Act record at the release tag.

  The sections render only when a release compliance record exists, and rule 10 requires them only then. Releases without a compliance record keep the current 15 required sections. Published 0.1.0/0.1.1 cards keep rendering byte-identically: add a golden test in `tests/release/test_card_build.py`.
- [X] T030 [US2] Run `uv run zoo compliance render`, run `uv run reuse lint`, fix the REUSE globs until it passes, and commit the generated files. **GATE:** `render --check`, `reuse lint` and `check --ci` pass.

**Checkpoint**: Public documents exist and cannot drift.

---

## Phase 5: User Story 4 - Published material cannot leak or overclaim (Priority: P2)

**Goal**: The release gate gains rule 16 with the model, publication, card, licence, repository and sign-off stages.

**Independent Test**: quickstart scenario 3 (publication and card part). The seeded violations C-U1–C-U4, C-C1–C-C2, C-L1–C-L3, C-G1–C-G4, C-D1–C-D2 and C-S1 each fail, and a clean release fixture passes.

### Tests for User Story 4

- [X] T031 [P] [US4] Write `tests/compliance/test_publication.py`:
  - **C-U2:** a fixture card containing a 31-word span copied from a fixture corpus fails; a 29-word span passes; a 40-word attributed quote from a `quote_allowed` source passes.
  - **C-U3:** a card with `erika.mustermann@example.org` fails.
  - **C-U4:** an example without an entry in `examples/SOURCES.yaml` fails, and so does an entry `source: road` while `road.redistribution: unclear`; `source: synthetic` passes.
  - **C-U1:** a report whose file hash differs from the current file fails.
- [X] T032 [P] [US4] Write `tests/compliance/test_card_lint.py`:
  - C-C1: a missing "Out-of-scope use" fails;
  - C-C2: "suitable as a safety function", "production-ready", "certified" and "this model is anonymous" each fail;
  - an Annex III phrase such as "for screening job applicants" fails;
  - the current `scout-large` card text plus the new sections passes.
- [X] T033 [P] [US4] Write `tests/compliance/test_repo_hygiene.py`:
  - C-G1: a missing `SECURITY.md` fails;
  - C-G2: `.github/FUNDING.yml`, "hire me", "consulting services" or "Miskatonic Analytics" in a README fails, while the e-mail address passes;
  - C-G5: a committed file with `erika.mustermann@example.org` fails, while a creator credit from a register record and the controller contact pass;
  - C-G4: an mcu release without an SBOM fails;
  - C-L2: a NOTICE drift fails;
  - C-L3: a Hub licence mismatch (FakeHub) and a gated BY-SA repo each fail.
- [X] T034 [P] [US4] Write `tests/release/test_rule16.py` on the release fixtures:
  - a draft without a compliance record fails C-S1;
  - a record with `memorisation` missing fails C-D1;
  - `training_compute_flop: 2e23` without a GPAI review fails C-D2;
  - the complete fixture passes rule 16.

  Also write `tests/release/test_rule6_routes.py`: a teacher route with `output_training_permitted: unclear` and no decision fails.

### Implementation for User Story 4

- [X] T035 [US4] Implement the corpus index and overlap scan in `src/mobility_model_zoo/compliance/scan.py`.
  - **`build_index(config, out)`:** hashed word 8-gram shingles (lowercased, Unicode-normalised) over `text.txt` of every snapshot used by the config's chunks, written to `data/compliance/corpus-index/<fingerprint>/`.
  - **`overlap(text, index)`:** the longest run of consecutive corpus words, found by chaining matching shingles.
  - **`pii(text)`:** the redact patterns plus IBAN, German phone, postcode with street, licence plate, tax ID and e-mail obfuscations.
- [X] T036 [US4] Implement `zoo compliance scan-publish --model M --version V`.
  - **Files scanned:** the rendered card, `examples/*`, `zoo/models/<m>/results/<v>/*.json`, release notes, and the `.ai-act.md` and `.training-data-summary.md` files.
  - **Report:** `zoo/models/<m>/releases/<v>.publication-scan.json` with `index_fingerprint` and, per file, `path`, `sha256`, `overlap_max_words` and `pii_hits`. Counts only, no matched text.
  - **Exemptions:** attributed quotes from `quote_allowed` sources are recorded as `allowed_quote_words`.
  - **Checks:** C-U1–C-U4.
- [X] T037 [US4] Implement the card lint (C-C1, C-C2) from `compliance/lists/card-lint.yaml` in `checks.py`, and call it from gate rule 10 (`release/gate.py`) for drafts that have a compliance record.
- [X] T038 [US4] Implement the repository and licence checks in `checks.py`:
  - C-G1: required files;
  - C-G2: monetisation and branding patterns (allowlist the two e-mail addresses and the two URLs from `controller.yaml`);
  - C-G3: run `zoo history-check`'s gitleaks call in working-tree mode;
  - C-G4: SBOM for `runtime: mcu` releases;
  - C-G5: `scan.pii` over every file listed by `git ls-files` with a text extension. The allowlist covers the contact lines from `controller.yaml`, the `creators` of source and dataset records whose licence requires attribution, and `tests/fixtures/compliance/`;
  - C-L1: `reuse lint` subprocess;
  - C-L2: drift of NOTICE, third-party notices and card attribution;
  - C-L3: Hub `cardData.license`, `base_model` and gating through the existing `hub.py`.

  Add C-G1, C-G2, C-G5 and C-L1 to `--ci`.
- [X] T039 [US4] Add gate rule 16 "compliance" to `src/mobility_model_zoo/release/gate.py`: rule table (`gate.py:40-55`), run order and `OFFLINE_RULES` in `release/cli.py`. It loads `zoo/models/<m>/releases/<v>.compliance.yaml` and runs the meta, model (C-D1, C-D2), publication (C-U1 from the committed report), card, licence, repository, notices and sign-off (C-S1) stages. Sandbox models are exempt from C-U and C-D but not from C-G or C-L.
- [X] T040 [US4] Fix rule 6 and the record template:
  - In `src/mobility_model_zoo/productdev/jtbd/span/results.py:394`, read `training_on_outputs_permitted` from the route record: `yes` becomes true, `no` false, and `unclear` false unless a decision covers it.
  - In `release/gate.py` rule 6, require `output_training_permitted: yes` or a covering decision for every teacher route.

  Do not edit published records. T034 passes.
- [X] T041 [US4] Implement `zoo compliance signoff --model M --version V`: it sets `state: signed_off`, `signed_off_by` (from `git config user.name`) and `signed_off_at`, and refuses unless all other stages pass.

**Checkpoint**: Nothing can be published without a clean scan, card lint, licence files and sign-off.

---

## Phase 6: User Story 3 - scout-large 0.1.2 closes the gaps (Priority: P1)

**Goal**: A patch release with the same files and metrics, complete records and a compliant card, published after owner approval.

**Independent Test**: quickstart scenario 4. `zoo check scout-large 0.1.2` passes all rules including 16; files and metric values are identical to 0.1.1.

- [X] T042 [US3] Implement `zoo compliance art9-scan --config C` with the lexicon from `compliance/lists/special-categories.yaml`. It writes counts per category and source class into the release compliance record (`scans.art9_counts`) and never writes text or chunk ids into git. Run it on `configs/productdev/jtbd/span-train-v1.yaml` (training chunks) and `pilot-v1.yaml` (benchmark).
  - If hits exist outside `parliamentary-records`, add an owner decision item to `validation.md`: keep with rationale for 0.1.x, or plan 0.2 without them.
  - Test in `tests/compliance/test_art9.py` on synthetic text.
- [X] T043 [US3] Create the synthetic redaction test set `tests/fixtures/compliance/redaction-set/items.jsonl`: 300 German and English sentences with invented identifiers (e-mail, phone, handles, profile URLs, IBAN, postcode with street, licence plate), each annotated with spans. Implement `zoo compliance redaction-recall`, which runs `redact.py` patterns plus `scan.pii` on the set and prints recall per type. Run it, record the result in `validation.md`, and add a test that recall is ≥ 0.95 (D9). If it falls short, extend the patterns before continuing.
- [X] T044 [US3] Create `zoo/models/scout-large/releases/0.1.2.yaml`:
  - copy of 0.1.1 with `version: 0.1.2`, `change_type: patch`, `date` today;
  - `changes: "Compliance documentation: full attribution (TASL), teacher and labeling routes, privacy notice and copyright policy links, NOTICE text. Weights, files and metrics unchanged."`;
  - the same `files` and `staging`;
  - `recipe.git_commit` set to the current commit;
  - `published: null`.

  Copy `results/0.1.1/` to `results/0.1.2/` with `version` changed only. Rule 3 checks the identical sha256 and metrics. Create `zoo/models/scout-large/examples/SOURCES.yaml`, one entry per example file, with `source: synthetic` and a note that the texts are fictional and written for the card. Check each example text against the corpus index (T046) before recording it.
- [X] T045 [US3] Create `zoo/models/scout-large/releases/0.1.2.compliance.yaml`:
  - **AI system:** `ai_system.is_system: true`, rationale "weights plus inference code published".
  - **GPAI:** `gpai.is_gpai: false`, `generative: false`, `params: 560e6`, `training_compute_flop` estimated as 6 × params × fine-tuning tokens (from the training log; `method` stated), `base_model_compute_flop` as published for XLM-R or `unknown` with date, rationale.
  - **Exclusion and purpose:** `exclusion_basis: art2_12`, `monetisation: none`, `intended_purpose` and `out_of_scope` from the model card, `annex_iii_match: none`, `annex_i: {legislation: none, safety_component: false}`, `art50_trigger: none`, `legal_references` with dates.
  - **Export:** `export: {self_classification: "not listed (EU 2021/821)", rationale}`.
  - **Licence manifest:** Apache-2.0 weights, MIT base, notices.
  - **Provenance:** `sources`, the route ids from `recipients.yaml` and `recipients_sha256`.
  - **Scans:** `redaction_recall` from T043; `art9_counts` from T042; `memorisation: {status: not_applicable, rationale: "token-classification encoder without generative head; outputs are spans of the input text"}`.
  - **State:** `state: draft`.
- [X] T046 [US3] Render the card and documents for 0.1.2 with `zoo compliance render`. Build the corpus index, then run `zoo compliance scan-publish --model scout-large --version 0.1.2`. Fix any C-U finding in templates or examples (the examples are fictional; verify they pass). Commit the scan report.
- [X] T047 [US3] Run `uv run zoo check scout-large 0.1.2` and `uv run zoo compliance check --model scout-large --version 0.1.2`. **GATE:** every rule passes except C-S1. Then present the rendered card and the owner decision items from `validation.md` to the owner (AskUserQuestion). After approval, run `zoo compliance signoff` and re-run `zoo check`.
- [ ] T048 [US3] (ops) Publish 0.1.2 through the existing pipeline:
  1. push the tag `scout-large/v0.1.2`;
  2. `release-verify` builds the preview;
  3. the owner approves the preview;
  4. the owner dispatches `release-publish`.

  Afterwards, run `uv run zoo audit` and record the result in `validation.md`.

**Checkpoint**: The published model meets the harness.

---

## Phase 7: User Story 5 - The data path stops non-compliant data (Priority: P2)

**Goal**: Fetch, ingest, pre-send, post-receive, retention and train stages are enforced in `jtbd`.

**Independent Test**: quickstart scenario 3 (data path part). Every seeded violation in C-F1–C-F8, C-I1–C-I7, C-P1–C-P6, C-R1 and C-T1–C-T5 fails at its stage.

### Tests for User Story 5

- [X] T049 [P] [US5] Write `tests/compliance/test_signals.py` with `httpx.MockTransport`:
  - **C-F1:** robots.txt disallows `GPTBot` only, which blocks; a robots.txt network error blocks with "retry later"; robots.txt 404 means allowed; robots.txt 403 blocks.
  - **C-F2:** `/.well-known/tdmrep.json` with `tdm-reservation: 1`, and the same as a header, block.
  - **C-F3:** `X-Robots-Tag: noai`, and the `<meta name="robots" content="noai">` variant, block.
  - **C-F4:** ai.txt disallowing text blocks.
  - **C-F5:** a denylisted domain blocks.
  - **C-F6:** a terms page containing "text and data mining is prohibited" and no owner verdict blocks.
  - **C-F7:** a 402 response, or a login form, blocks.
  - **C-F8:** `register` without `--signals` is refused.
  - A clean site passes, and the crawl manifest line contains every verdict.
- [X] T050 [P] [US5] Write `tests/compliance/test_ingest_presend.py`:
  - **C-I1:** a chunk from a source without a record fails.
  - **C-I2:** a CC-BY-NC source with `training_allowed` fails.
  - **C-I4:** a human-subject source with `consent_or_ethics: unknown` and no decision fails.
  - **C-I6:** a forum chunk with a health statement is quarantined.
  - **C-I7:** a Reddit-class source without `platform_terms`, or with `ml_use: unclear` and no decision, fails.
  - **C-P1:** a chunk with an outdated `patterns_version` fails.
  - **C-P2:** an unredacted `erika.mustermann@example.org` fails before any backend call. Use a fake backend that fails if called.
  - **C-P4:** a `consumer_cli` route for a new run fails.
  - **C-P5:** a `provider_order: null` OpenRouter model fails at run start.
  - **C-P6:** a response whose `provider` differs from the route is discarded and the run fails.
- [X] T051 [P] [US5] Write `tests/compliance/test_retention_train.py`:
  - **C-R1:** a snapshot with `retention_until` yesterday is reported.
  - **`delete`:** removes the raw file, logs hash and URL, and sets `deleted_at`.
  - **C-T1:** a suppressed URL in the training data fails.
  - **C-T2:** an ND licence fails.
  - **C-T3:** a share-alike input with an Apache model licence fails.
  - **C-T4:** a teacher route with `unclear` output rights fails.
  - **C-T5:** a recall below 0.95 fails.

### Implementation for User Story 5

- [X] T052 [US5] Implement `src/mobility_model_zoo/compliance/signals.py` per research R4: robots.txt (RFC 9309; project agent, `*`, AI agents list; fail closed), TDMRep (well-known file, header, meta), `X-Robots-Tag` and meta robots, ai.txt, deny and piracy lists, the terms keyword screen, and access-barrier detection. It returns a `SignalVerdict` with every field of the crawl manifest entry (data-model.md).
- [X] T053 [US5] Wire the signals into `jtbd/sources/snapshot.py`:
  - **`fetch_url`:** replace `robots_allowed` (fails open today at lines 313–318) with `signals.check`. Write each attempt to `data/compliance/crawl-manifest.jsonl`. Refuse with exit 3 naming the check.
  - **User agent:** `USER_AGENT` (line 25) becomes `mobility-model-zoo-crawler/1.0 (+https://github.com/mhabedank/mobility-model-zoo/blob/main/COPYRIGHT_POLICY.md)`. Keep the robots.txt group matching for the old token `jtbd-pilot` as well.
  - **`register_file` (line 353):** require a `--signals` YAML with `url`, `verdicts` and `checked_at`. Add the option in `jtbd/cli.py` (`source register`).
  - **`jtbd/sources/reddit.py`:** run the same checks for the API host's robots.txt and terms.

  T049 passes, and the existing `tests/unit/test_sources.py` and `test_forum_posts.py` stay green after their fixtures are adjusted for the new user agent.
- [X] T054 [US5] Implement the ingest checks C-I1–C-I7 in `checks.py` and call them from `jtbd/corpus/autochunk.py` before chunks are written. Quarantined chunk ids go to `data/compliance/quarantine.jsonl` (outside git), and chunks of classes with `art9_handling: quarantine` are excluded when flagged.
- [X] T055 [US5] Implement the pre-send and post-receive checks in `jtbd/labeling/runner.py`:
  - **Before each batch (C-P1–C-P5):** re-run `scan.pii` on the exact text to be sent, compare `redaction.patterns_version` with the current `PATTERNS_VERSION`, check quarantine, and check the route via `register.route_for(model_cfg)`.
  - **In `jtbd/labeling/openrouter.py`:** refuse `provider_order: null` at backend construction, and pass `provider.order` equal to the route's hosting provider.
  - **After each response (C-P6):** compare `backend_meta.provider` with the route. On a mismatch, delete nothing already written, mark the attempt as `error: provider_mismatch`, and stop the run.

  Local routes (Ollama, openai_compat to localhost) skip C-P4/C-P5 but not C-P1–C-P3.
- [X] T056 [US5] Update `configs/productdev/jtbd/models.yaml`. Every OpenRouter teacher entry with `provider_order: null` (lines 165–247) gets `route:` pointing to a route record and `provider_order:` set to the route's hosting provider. Routes without `allowed_for` are left in place but refused at run start.

  Add a `route:` key to every model entry, and extend `jtbd/config.py` so that `route` loads. Unknown keys must still fail.
- [X] T057 [US5] Add the backend `anthropic_api` in `jtbd/labeling/anthropic_api.py` (Anthropic SDK, structured JSON output with the same schema as `claude_cli`, model version from the response, `backend_meta` with the request id), registered in `labeling/base.py`. Its route in `providers.yaml` is `claude-api` with `access_path: api`. It gets `allowed_for: []` until the owner signs a DPA and the commercial terms check is recorded. Test it with a fake client in `tests/unit/test_anthropic_api_backend.py`. No paid call in this feature.
- [X] T058 [US5] Implement retention (C-R1):
  - `zoo compliance retention [--fail]`, which reads snapshot `retention_until` and register retention;
  - `zoo compliance delete --snapshot ID --reason TEXT`, which removes `raw.*` and `text.txt`, appends to `data/compliance/deletions.jsonl` and sets `deleted_at` in the source record;
  - a retention report line in `jtbd doctor` (`jtbd/doctor.py`).
- [X] T059 [US5] Implement the train checks C-T1–C-T5 in `checks.py` and call them from `jtbd/span/datacheck.py`, writing the result into `provenance.json`. T050 and T051 pass.

**Checkpoint**: Future data generation cannot bypass the register.

---

## Phase 8: User Story 6 - Requests and legal dates (Priority: P3)

**Goal**: The request channel, log, suppression and legal watch are operational.

**Independent Test**: quickstart scenario 5.

- [X] T060 [P] [US6] Write `tests/compliance/test_requests.py`:
  - `request add` stores only an HMAC identifier;
  - it fails without `MMZ_SUPPRESSION_KEY`;
  - the deadline is set to 1 month for objection, erasure and access, and 14 days for takedown;
  - a suppressed URL blocks a later fetch (C-F5), and a suppressed identifier blocks training (C-T1);
  - `watch review` clears C-M2.
- [X] T061 [US6] Implement `src/mobility_model_zoo/compliance/hashing.py`: HMAC-SHA-256 over NFKC-lowercased identifiers and canonical URLs with `MMZ_SUPPRESSION_KEY`. Implement `zoo compliance request add/close` and `zoo compliance watch review` per contracts/cli.md, writing `compliance/requests.yaml` and `compliance/suppression.yaml`.
- [X] T062 [US6] Add the meta stage to `.github/workflows/zoo-audit.yml` (weekly), with a step `uv run zoo compliance check --stage meta`. No secrets are needed for this step.
- [X] T063 [US6] Document the request handling for the owner in `docs/compliance/requests.md` (English): how to receive, hash, search the stores (snapshots, chunks, runs, published files), answer within the deadline, and suppress. Link it from `PRIVACY.md` through its template.

**Checkpoint**: Requests have a channel, a log and an effect.

---

## Phase 9: Polish & Cross-Cutting

- [X] T064 Add `uv run zoo compliance check --ci` and `uv run reuse lint` as steps in `.github/workflows/ci.yml`, after the tests.
- [X] T065 [P] Update `README.md` with a short "Compliance" section linking `PRIVACY.md`, `COPYRIGHT_POLICY.md`, `SECURITY.md`, `NOTICE` and `docs/compliance/`. Update `docs/adding-a-model.md` with the register records, compliance record, scan and sign-off. Update `docs/hf-org/README.md` with the policy links (Hugging Face org card; push via the existing process). Keep the README section within the drift rules: README is not generated, so link only.
- [ ] T066 [P] Update feature 005 docs on branch `005-topic-layout-security-merge` after this feature is merged:
  - dataset declarations move to `topics/<topic>/compliance/datasets.yaml` with the register schema;
  - the 005 task numbers T048–T055 refer to it;
  - the edge release record gets a compliance record;
  - 005 builds the firmware SBOM generator (CycloneDX) that C-G4 checks.

  Record this as a note in `specs/005-topic-layout-security-merge/plan.md`.
- [X] T067 Run the full quickstart (scenarios 1–5) and the full test suite. Write results and runtimes to `validation.md`. Run `uv run zoo history-check`. Open the PR "006: compliance harness and scout-large 0.1.2" with `gh pr create`; the body lists the owner decisions and gates. **GATE:** CI green.

---

## Dependencies & Execution Order

- **Overall order:** Setup (T001–T003) → Foundational (T004–T007) → US1 (T008–T023) → US2 (T024–T030) → US4 (T031–T041) → US3 (T042–T048) → US5 (T049–T059) → US6 (T060–T063) → Polish (T064–T067).
- **US2** needs the US1 register: the documents render from it.
- **US4** needs US2 (card sections, NOTICE) and US1.
- **US3** needs US1, US2 and US4. T048 needs the owner's approval of the preview.
- **US5** needs US1 (routes, sources, lists) and the T035 PII scan. It is independent of US3.
- **US6** needs US1 and the US5 fetch and train wiring (for suppression).

### Parallel opportunities

- **Phase 2:** T007 in parallel with T005 and T006.
- **US1:** T008 and T009 together; T012–T015 together; T023 any time after T010.
- **US2:** T024 and T025 together.
- **US4:** T031–T034 together; T037 and T038 after T035.
- **US5:** T049–T051 together; T056 and T057 in parallel with T054.
- **Polish:** T065 and T066 together.

## Implementation Strategy

1. **MVP = US1 + US2:** a complete register plus generated `PRIVACY.md`, `NOTICE` and the policies. This already closes the public gaps (privacy notice, contact, attribution) in the repository, before the patch.
2. **US4 + US3:** gate rule 16 and the 0.1.2 patch, the first release under the harness.
3. **US5 + US6:** protection of future data generation and the request workflow.
4. Feature 005 resumes after the merge, with its dataset declarations in the register.
