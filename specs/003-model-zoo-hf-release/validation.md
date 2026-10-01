# Validation: feature 003

## Traceability (T065)

Every FR and SC maps to at least one task, artifact or automated test.

| Requirement | Tasks | Artifact or test |
|-------------|-------|------------------|
| FR-001 rename | T003–T012 | `pyproject.toml` (`mobility-model-zoo`, scripts `jtbd`, `zoo`); `tests/unit/test_no_pilot_commands.py`; `tests/unit/test_rename_hashes.py` |
| FR-002 constitution | T001 | `.specify/memory/constitution.md` 1.3.0 |
| FR-003 topics | T019, T048 | `zoo/topics.yaml`; `tests/release/test_index.py::test_new_topic_needs_no_code_change` |
| FR-003a names | T027 (rule 2) | `tests/release/test_gate_rules.py` (rule 2); `tests/release/test_schemas.py` |
| FR-003b license | T002, T027 (rule 6) | `LICENSE`; rule 6 tests |
| FR-003c public + history | T061, T062 | `zoo history-check`, `tests/release/test_history.py`; [handover-004.md](handover-004.md) |
| FR-004 overview | T049 | `zoo/MODELS.md`; `tests/release/test_index.py` |
| FR-005 / 005a versions, status | T027, T054 | rule 3; `tests/release/test_versions.py::test_change_type_rules` |
| FR-006 release record | T015, T016 | `release-record.schema.json`; `tests/release/test_gate_required_fields.py` |
| FR-006a staging | T029, T030, T057 | `zoo init-model`, `zoo stage`; `tests/release/test_publish.py`; audit test |
| FR-007 immutability | T034, T057 | rule 4; `test_second_publish_is_refused_and_changes_nothing`; `test_audit_detects_moved_tags_and_public_staging` |
| FR-008 retrieval by version, latest default | T034 | `test_second_version_keeps_the_first_and_shows_history` |
| FR-009 pipeline | T027–T037 | `.github/workflows/release-verify.yml`, `release-publish.yml`; `tests/release/test_publish.py` |
| FR-010 card sections and metadata | T031, T042, T044 | `templates/model_card.md.j2`; `tests/release/test_card_build.py`; rule 10 |
| FR-011 upload allow-list | T027 (rule 11), T030 | rule 11 tests; `test_stage_refuses_forbidden_files` |
| FR-012 credentials | T013, T063 | `contracts/workflows.md`; `tests/release/test_no_secrets_in_logs.py` |
| FR-013 dry run | T033, T036 | `zoo preview` (staging branch `rc-v<version>`); `zoo check --offline` |
| FR-014 agreement wording | T040, T044 | rule 10 (`accuracy` forbidden, agreement sentence required); results schema |
| FR-015 no spike release, status shown | T027 (rule 7), T031 | rule 7 tests; status banner in the card |
| FR-016 traceable numbers | T043 | rule 9 (`traceability`); `test_rule_9_card_number_not_in_results` |
| FR-017 first public model | (004) | draft `zoo/models/productdev-jtbd-span-xlmr/` (0.1.0, experimental) |
| FR-018 example texts with outputs | T046 | rule 13; three examples per model; outputs from the staged model |
| FR-019 record format for 004 | T059 | [handover-004.md](handover-004.md) |
| FR-020 dry run of the span draft | T060 | [handover-004.md](handover-004.md): only fields 004 delivers are missing |
| FR-021 sandbox test model | T025, T026, T039 | `src/mobility_model_zoo/sandbox/`; `zoo/models/sandbox-pipeline-tiny/`; real run pending (below) |
| SC-001 | T039, T060 | real run pending; dry run done |
| SC-002 | T044, T047 | rule 10b with the Hub's validator; real run pending |
| SC-003 | (004) | [reader-test.md](reader-test.md) |
| SC-004 | T045 | rule 12; `VenvRunner` verified locally on 2026-10-01 (fresh environment, CPU, sandbox model: exit 0) |
| SC-005 | T022 | `tests/release/test_gate_required_fields.py`: 54 required fields, each blocked, nothing uploaded |
| SC-006 | T023 | `test_second_publish_is_refused_and_changes_nothing` |
| SC-007 | T039 | real run pending |
| SC-008 | T043 | rule 9 |

## Automated checks (T064)

On 2026-10-01: `uv run ruff check` passes, `uv run pytest` passes (252 tests), `uv run zoo validate --all` passes (both release records are unstaged drafts).

## Real runs against the Hugging Face Hub

Pending. They need the owner's steps T012 (repository rename), T013 (organization and tokens) and T038 (merge into `main`).

| Task | Scenario | Result |
|------|----------|--------|
| T039 | quickstart 2–5: stage, tag, preview, publish, refusals; SC-001, SC-007 | pending |
| T047 | quickstart 3 again with the full card; SC-002 | pending |
| T058 | quickstart 6: second version and history | pending |
