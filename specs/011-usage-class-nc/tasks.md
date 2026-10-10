---
description: "Tasks of feature 011: usage class and non-commercial releases"
---

# Tasks: Usage class and non-commercial releases

**Input**: Design documents from `specs/011-usage-class-nc/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli.md, quickstart.md

**Tests**: Included. The success criteria (SC-001 to SC-007) are verified by tests, and the quickstart runs them.

**Organization**: Tasks are grouped by user story. US1 and US2 are both P1 and share the derivation built in Phase 2.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1–US4 from spec.md

## Phase 1: Setup

- [X] T001 Extend `compliance/lists/licence-allowlist.yaml` per data-model.md "Licence entry": fields `non_commercial` (bool, default false), `share_alike` (bool, default false), `release_licences` ("required when `share_alike`; every id in `release_licences` is itself an entry"), `trains` (bool, default true), `note`. Set `CC-BY-SA-4.0 {share_alike: true, release_licences: [CC-BY-SA-4.0]}`; add `CC-BY-NC-4.0 {non_commercial: true}`, `CC-BY-NC-SA-4.0 {non_commercial: true, share_alike: true, release_licences: [CC-BY-NC-SA-4.0]}`, `LicenseRef-MSMARCO-terms {non_commercial: true, trains: false}`. Rewrite the header comment: NC entries permit training of non-commercial models only; ND licences are never listed.
- [X] T002 Make `allowlisted()` in `src/mobility_model_zoo/compliance/ingest.py` return only entries with `trains: true` and not `non_commercial` by default, so C-I2 behaves exactly as before until T020 adds the target class.

## Phase 2: Foundational (blocks all stories)

- [X] T003 Create `src/mobility_model_zoo/compliance/usage.py` with `UsageClass` (values `commercial`, `commercial-share-alike`, `non-commercial`, `non-commercial-share-alike`; `parse`, `__str__`, `combine` = "`commercial = a.commercial and b.commercial`, `share_alike = a.share_alike or b.share_alike`", `covers` = "`(not a.commercial or b.commercial) and (a.share_alike or not b.share_alike)`") and `LicenceList` (load from the register's lists, `entry(id)`, `restriction(id)` → UsageClass or None when unresolved).
- [X] T004 In `src/mobility_model_zoo/compliance/usage.py` add `resolve_source_licence(root, source, declared, by_origin)` following research R3: dataset declaration → compliance source/dataset record with the same origin → licence string as list id → `bootstrap.LICENCES` free-text mapping → unresolved.
- [X] T005 In `src/mobility_model_zoo/compliance/usage.py` add `RestrictingInput` (`kind` in `source|dataset|base_model|teacher|third_party|zoo_model_output`, `id`, `licence`, `restriction`) and `Derivation(cls, restricting_inputs, findings)`, and `satisfying_licences(cls, inputs, licences)` per research R5 (intersection of `release_licences` of share-alike inputs, filtered to non-commercial licences for NC classes; empty ⇒ conflict finding C-U3 naming the inputs; without share-alike inputs: commercial accepts any listed non-NC licence, NC accepts `CC-BY-NC-4.0` or `CC-BY-NC-SA-4.0`).
- [X] T006 In `src/mobility_model_zoo/compliance/usage.py` add `derive_release(root, model, record)` that collects the inputs of a release (provenance sources with `permitted_use: training_allowed`; `base_model` with `base_model_license`; teachers; zoo-model teachers; datasets with `produced_by`), resolves them, returns a `Derivation`, and emits C-U1 for unresolved licences and C-T2-style findings for inputs whose entry has `trains: false` or that are `benchmark_only`. Third-party run-time models are added in T030.
- [X] T007 [P] Add `usage_class` (enum of the four values, required) to `src/mobility_model_zoo/release/schemas/model.schema.json` and set it in `zoo/models/{scout-large,sandbox-pipeline-tiny,pace-cnn,picket-forest,picket-mlp}/model.yaml` (`commercial`) and `zoo/models/hum-fan/model.yaml` (`commercial-share-alike`); also in the release test fixtures under `tests/release/fixtures/` and `tests/website/fixtures/registry/`.
- [X] T008 [P] Add the optional `usage` object (`class`, `licence`, `restricting_inputs[]` of `{kind, id, licence, restriction}`) and the optional teacher field `outputs_non_commercial: bool` to `src/mobility_model_zoo/release/schemas/release-record.schema.json`.
- [X] T009 [P] Change `src/mobility_model_zoo/compliance/schemas/datasets.schema.json` per data-model.md: licence `-ND` ⇒ `benchmark_only` (keep), licence `-NC` ⇒ `commercial_use: false` (new), remove "`training_allowed` ⇒ `commercial_use: true`", add optional `produced_by` (string); change `sources.schema.json` so that only `-ND` forces `benchmark_only`; add `non_commercial` to the `output_training_permitted` enum in `providers.schema.json`.
- [X] T010 Add `Register.output_training_terms(teacher)` returning `yes|non_commercial|no|unclear` in `src/mobility_model_zoo/compliance/register.py`; keep `output_training_permitted` true only for `yes`.
- [X] T011 [P] Unit tests in `tests/compliance/test_usage.py`: class parse/combine/covers table, licence list validation (`release_licences` required for share-alike), source resolution order R3 including an unresolved free-text licence, satisfying licences and the CC-BY-SA + CC-BY-NC-SA conflict; update `tests/compliance/test_register_schemas.py` and `tests/datasets/test_declarations.py` to the new NC rules (NC `training_allowed` with `commercial_use: false` valid; NC with `commercial_use: true` invalid; ND `training_allowed` invalid).

**Checkpoint**: derivation available; nothing in the gate uses it yet.

## Phase 3: User Story 1 - Release a non-commercial model, marked everywhere (P1) 🎯 MVP

**Goal**: an NC model with NC training data passes the gate and is marked in card, Hub tag, release record and website.

**Independent Test**: `uv run pytest tests/release/test_usage_class.py -k nc_fixture`.

- [X] T012 [US1] Rewrite gate rule 6 in `src/mobility_model_zoo/release/gate.py`: drop the blanket "non-commercial licence for training" refusal and the `PERMISSIVE` set; call `derive_release`; refuse when the declared `usage_class` does not cover the derived class (C-U2, naming each restricting input with its licence), when `license` is not among the satisfying licences (C-U3), and on derivation findings; keep the dataset declaration checks and the teacher output checks (a `no` teacher fails for every class).
- [X] T013 [US1] Gate rule 2 in `src/mobility_model_zoo/release/gate.py`: require `name == <base>-<variant>-nc` for non-commercial classes and refuse a name ending in `-nc` for commercial classes (C-U4 messages from contracts/cli.md); keep `variant` without the suffix.
- [X] T014 [US1] Gate rule 6: require `usage` in every record whose `published` is empty, refuse when it differs from the derivation, and refuse (C-U5) a class that differs from `model.yaml` or from an earlier release record of the same model that has `usage`, in `src/mobility_model_zoo/release/gate.py`.
- [X] T015 [US1] Card: add the usage line under the version line and repeat it in `## License` in `src/mobility_model_zoo/release/templates/model_card.md.j2`, with a `usage_context()` helper in `src/mobility_model_zoo/release/card.py` ("Non-commercial use only · licence <id> · because <inputs>" or "the owner chose this restriction"; "commercial use permitted · licence <id>"; share-alike: "derivatives must keep <id>"); front matter keeps `license` lowercased.
- [X] T016 [US1] Gate rule 10 in `src/mobility_model_zoo/release/gate.py`: the rendered card's usage line must match the record's `usage`.
- [X] T017 [US1] Website: hero chip `Licence <id> · <class>` in `src/mobility_model_zoo/site/templates/partials/hero.html.j2`, a "Usage" row with the reason in `partials/provenance.html.j2`, a non-commercial notice before the install line in the quickstart partial, the class on each start-page entry; pass the class through `src/mobility_model_zoo/site/context.py`; site check L3 in `src/mobility_model_zoo/site/check.py` requires the usage class text on each model page.
- [X] T018 [US1] NC fixture model `nc-fixture-tiny-nc` (declared `non-commercial`, licence `CC-BY-NC-4.0`, one declared CC-BY-NC-4.0 dataset `training_allowed` with `commercial_use: false`) under `tests/release/fixtures/` and tests in `tests/release/test_usage_class.py`: offline gate passes; card top, front matter licence tag, record `usage` and site page all contain "non-commercial", `CC-BY-NC-4.0` and the dataset id (SC-001); NC-SA input with CC-BY-NC-SA-4.0 passes and with CC-BY-NC-4.0 is refused (US1 scenario 5).
- [X] T019 [US1] Update the golden cards `tests/release/fixtures/golden/*.README.md`, `tests/release/test_edge_rules.py` (`test_rule6_non_commercial_training_source` now expects acceptance for an NC model and refusal for a commercial one) and the site tests in `tests/website/` for the new usage line and chips.

**Checkpoint**: US1 works; an NC model can be released and is marked.

## Phase 4: User Story 2 - The gate refuses a release that hides a restriction (P1)

**Goal**: every kind of restricted input is refused for a commercial model, early where possible.

**Independent Test**: `uv run pytest tests/release/test_usage_class.py -k refused` and `uv run pytest tests/compliance -k train`.

- [X] T020 [US2] `check_training(..., usage_class="commercial")` in `src/mobility_model_zoo/compliance/train.py` per research R11: C-T2 refuses unknown, ND, all-rights-reserved, unresolved and `benchmark_only` inputs for every class and NC inputs only for commercial targets; C-T3 refuses share-alike inputs when the class lacks share-alike; `check_snapshots(..., usage_class="commercial")` in `src/mobility_model_zoo/compliance/ingest.py` accepts NC list entries only for NC targets.
- [X] T021 [US2] `src/mobility_model_zoo/productdev/jtbd/span/datacheck.py` passes the declared class of the model named in the span config (`model:`) from `zoo/models/<name>/model.yaml`, commercial when absent; `src/mobility_model_zoo/productdev/jtbd/corpus/autochunk.py` passes commercial unless told otherwise.
- [X] T022 [US2] `require_training_allowed(ds, usage_class="commercial")` in `src/mobility_model_zoo/datasets/__init__.py` refuses `commercial_use: false` for commercial targets; callers `src/mobility_model_zoo/edge/int8/keras_export.py` and `src/mobility_model_zoo/security/can_ids/forest.py` pass the declared class of the model they build when known; `produced_by` read in `src/mobility_model_zoo/datasets/registry.py`, and `zoo data validate` refuses `commercial_use: true` when `produced_by` names a non-commercial model.
- [X] T023 [US2] Teachers in `derive_release` (`src/mobility_model_zoo/compliance/usage.py`): `outputs_non_commercial: true` or a provider route with `non_commercial` makes the release non-commercial; a teacher whose `model_id` is a zoo model (`mobility-model-zoo/<name>` or `<name>`) takes that model's declared class.
- [X] T024 [US2] Refusal fixtures and tests in `tests/release/test_usage_class.py`: one commercial model per input kind (dataset, base model, teacher, third-party run-time model, zoo-model output), each refused with a message naming the input (SC-002); the same models declared non-commercial pass; ND, unknown, all-rights-reserved and a Reddit-like `benchmark_only` source refused for both classes (SC-003); `-nc` name on a commercial model and missing `-nc` on an NC model refused; class change between versions refused. Update `tests/compliance/test_retention_train.py` and `tests/compliance/test_ingest_presend.py` for the class parameter.

**Checkpoint**: US1 and US2 complete; the relaxation cannot leak restricted inputs into commercial releases.

## Phase 5: User Story 3 - One register of third-party models (P2)

**Goal**: third-party models are pinned and their licences, including named training data, determine restrictions.

**Independent Test**: `uv run pytest tests/compliance/test_third_party.py` and `uv run zoo compliance check --ci`.

- [X] T025 [P] [US3] Schema `src/mobility_model_zoo/compliance/schemas/third-party-models.schema.json` per data-model.md (fields `id` "unique, `org/name`", `revision` "40-hex commit", `remote_code` "null or `{repo, revision}` with 40-hex commit", `weights_licence`, `training_data` "list of `{name, url, licence}`; `licence` resolvable or `unknown`", `training_data_named` "false ⇒ `training_data` empty", `used_by`, `notes`, `owner`, `last_reviewed`, `next_review`) and register loading in `src/mobility_model_zoo/compliance/register.py` (`SHARED["third-party-models.yaml"] = ("third-party-models", "models")`).
- [X] T026 [US3] Read the Common Crawl terms of use and record the result (research R15): add `LicenseRef-CommonCrawl-ToU` to `compliance/lists/licence-allowlist.yaml` with the attributes the terms imply and `trains: false`.
- [X] T027 [US3] Create `compliance/third-party-models.yaml` with `FacebookAI/xlm-roberta-large` (revision from `configs/productdev/jtbd/span-xlmr.yaml`, MIT, CC-100, `used_by: [{kind: base_model, ref: scout-large}, {kind: stage, ref: "configs/productdev/jtbd/span-xlmr.yaml#base_encoder"}]`) and the five models of feature 009 at the revisions pinned there (multilingual-e5-base d1287505…, -small 614241f6…, gte-multilingual-base 9bbca17d… with remote code Alibaba-NLP/new-impl 40ced75c…, LaBSE 836121a0…, mDeBERTa NLI b5113eb3…), their weights licences and the training data their model cards name, with `used_by: []` (feature 009 adds its references); add the licences these training data carry to the licence list (`trains: false`) or record them as `unknown`.
- [X] T028 [US3] Checks C-X1 and C-X2 in the meta stage (`src/mobility_model_zoo/compliance/checks.py`, helper in `usage.py`): `model.yaml` `base_model` must be registered; `used_by` stage references must resolve to a config key with the same model id and revision; a mapping in `configs/**/*.yaml` with `revision` and a `model_id` or `name` of the form `org/name` must be registered (exclude `configs/productdev/jtbd/models.yaml`); an `unknown` training-data licence is C-X2 unless a decision in `compliance/decisions.yaml` lists the record id in `affected_records`.
- [X] T029 [US3] Record an owner decision in `compliance/decisions.yaml` only if T027 leaves `unknown` training-data licences that the owner must accept; otherwise none. (Owner step: if needed, ask before recording.) **Result 2026-10-10**: none needed; unknown training-data licences exist only on models of feature 009 that nothing uses yet, and C-X2 applies once `used_by` is set.
- [X] T030 [US3] In `src/mobility_model_zoo/compliance/usage.py`: third-party restriction = combination of weights licence and every training-data licence (FR-019); `derive_release` uses the register for the base model when it is registered and for run-time models listed in a new optional `model.yaml` field `runtime_models: [ids]`; add `third_party_metadata(root, ids)` returning `[{id, revision, usage_class, reason}]` for stage outputs (FR-020).
- [X] T031 [US3] Tests in `tests/compliance/test_third_party.py`: MIT weights with CC-BY-NC training data ⇒ non-commercial with the reason; unregistered base model, differing revision and unpinned remote code fail C-X1; unknown training-data licence fails C-X2 and passes with a decision; `third_party_metadata` output; the real register passes `zoo compliance check --ci`.

**Checkpoint**: third-party models are covered; feature 009 can reference the register.

## Phase 6: User Story 4 - Existing models get a usage class and the zoo stops overpromising (P2)

**Goal**: one audit shows every model's class; the website states classes per model.

**Independent Test**: `uv run zoo compliance usage` lists six models with class or finding in under a minute and changes no file.

- [X] T032 [US4] Command `zoo compliance usage [--model NAME] [--json]` in `src/mobility_model_zoo/compliance/cli.py` per contracts/cli.md (text and JSON output, exit codes 0/1/2), using `derive_release` on each model's latest release record; read-only.
- [X] T033 [US4] Add the `usage` block to the draft release records (status `draft`, `published` empty) of hum-fan, pace-cnn, picket-forest and picket-mlp under `zoo/models/*/releases/`, with the values the derivation gives; leave published records unchanged.
- [X] T034 [US4] Rewrite the zoo-wide copy in `zoo/site.yaml`: the lead and the principle "Open for everyone, including commercial use" promise open licences and per-model usage classes instead of commercial use for every model (constitution 2.1.0); keep the other texts.
- [X] T035 [US4] Tests in `tests/compliance/test_usage_audit.py`: the audit on the repository lists all six models, runs offline in under 60 s, leaves `git status` clean (compare file hashes), and reports an unresolved free-text licence as C-U1; a site test asserts the start page shows each model's class and `zoo/site.yaml` contains no "including commercial use".
- [X] T036 [US4] Run the audit on the repository and record the result (classes and any findings, with the owner decisions they need) in `specs/011-usage-class-nc/audit-2026-10-10.md`; fix findings that are data gaps (missing register entries, unresolvable licences) and list real restrictions for the owner.

## Phase 7: Polish & Cross-Cutting

- [ ] T037 [P] Document the usage class, the `-nc` suffix, the licence list attributes and the third-party register in `docs/adding-a-model.md` and in the README section on releases (`README.md`).
- [ ] T038 [P] Update the compliance check catalogue of feature 006 (`specs/006-compliance-harness/contracts/checks.md`) with C-U1–C-U5, C-X1, C-X2 and the changed C-T2, C-T3, C-I2.
- [ ] T039 Run the quickstart (`specs/011-usage-class-nc/quickstart.md`), the full suite (`uv run pytest`) and `uv run ruff check .`; list every pre-existing test whose expectation changed and why (SC-007) in the PR description.
- [ ] T040 Write the handover for feature 009 in `specs/011-usage-class-nc/handover-009.md`: reference the register from `configs/productdev/jtbd/cluster-*.yaml` (`used_by`), write `third_party_metadata` into the stage output, and the owner decisions on the NLI model and the e5 encoders that the register derives as non-commercial.

## Dependencies & Execution Order

- Phase 1 → Phase 2 → US1 → US2; US3 after Phase 2 (T030 extends `derive_release`, so after T006 and T023); US4 after US1 (marking) and US3 (register used by the audit); Polish last.
- Within US1: T012 → T013 → T014; T015 → T016; T017 independent of T012–T016; T018 after T012–T017; T019 last.

## Parallel Example

- Phase 2: T007, T008, T009, T011 in parallel after T003–T006 are drafted.
- US3: T025 in parallel with T026; T027 after both.
- Polish: T037 and T038 in parallel.

## Implementation Strategy

MVP is Phase 1, Phase 2 and US1 together with US2 (both P1): the gate must accept NC models and refuse hidden restrictions in the same change, otherwise the relaxation leaks. US3 and US4 follow; the branch is merged after all phases, because the owner needs the constitution and its enforcement on another branch.
