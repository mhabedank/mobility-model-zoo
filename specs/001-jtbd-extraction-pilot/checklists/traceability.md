# Traceability check (T085)

**Date**: 2026-10-01. **Scope**: every FR and SC in [spec.md](../spec.md) against [tasks.md](../tasks.md), code and report sections.

**Result**: all 51 requirements and success criteria map to at least one task. "cited" means the task text names the ID; "by content" means it does not, but the listed tasks and artifacts implement it. "(open)" marks tasks that are still open, mostly ops work.

**Not yet closable**: SC-009 (total spend ≤ €20) can only be confirmed after the last paid run. Current `pilot budget`: €2.36 of €20 spent (all OpenRouter, from the spike; key cap €18.40). T085 stays open until then.

| ID | Tasks | Artifacts | Mapping |
|---|---|---|---|
| FR-001 | T008 |  | cited |
| FR-002 | T009, T029 |  | cited |
| FR-002a | T035 (open) | `corpus/split.py`, `corpus/validate.py` | by content |
| FR-003 | T009, T029, T035 (open) | `corpus/validate.py`, report section 3 | by content |
| FR-004 | T009, T029, T035 (open) | `corpus/validate.py`, report section 3 | by content |
| FR-005 | T009, T029, T035 (open) | `corpus/validate.py`, report section 3 | by content |
| FR-006 | T009, T029, T035 (open) | `corpus/validate.py`, report section 3 | by content |
| FR-007 | T009, T029 |  | cited |
| FR-008 | T031 (open), T055 |  | cited |
| FR-009 | T026 |  | cited |
| FR-010 | T006, T026, T029, T033 (open) | `contracts/chunk-record.schema.json` | by content |
| FR-011 | T020, T024, T031 (open) | `contracts/source-snapshot.schema.json` (`legal_basis`, `permitted_uses`) | by content |
| FR-012 | T021, T027, T034 (open) | `corpus/redact.py`, `pilot corpus redact-check` | by content |
| FR-013 | T020, T032 (open), T082 | `retention_until` in every snapshot | by content |
| FR-013a | T019, T020, T022, T023, T024, T032 (open) | `sources/registry.py`, `contracts/source-snapshot.schema.json` | by content |
| FR-014 | T043 | `guideline/guideline-v1.md` | by content |
| FR-015 | T096 |  | cited |
| FR-016 | T005, T006 | `contracts/extraction-output.schema.json`, `schema.py` | by content |
| FR-017 | T080 |  | cited |
| FR-018 | T047 |  | cited |
| FR-019 | T012, T041 | `benchmark_labeler` in `configs/models.yaml`, `labeling/runner.py` role checks | by content |
| FR-019a | T012, T071 (open), T072 (open), T073 (open) | `configs/models.yaml`, `labeling/runner.py` role checks | by content |
| FR-019b | T086, T089, T096 |  | cited |
| FR-020 | T038, T053 | `matching.py` | by content |
| FR-021 | T039, T054 |  | cited |
| FR-022 | T039, T054 |  | cited |
| FR-023 | T055, T059 (open) | `metrics.py`, report section 4 | by content |
| FR-024 | T055 |  | cited |
| FR-025 | T062 |  | cited |
| FR-026 | T052 |  | cited |
| FR-026a | T087, T092, T096 |  | cited |
| FR-027 | T060, T061, T062, T063 (open), T064 (open) | `categorize.py`, report sections 7 and 8 | by content |
| FR-028 | T069 |  | cited |
| FR-029 | T066, T070, T074 (open) | `perf.py`, report section 10 | by content |
| FR-030 | T075 |  | cited |
| FR-031 | T069, T070, T075, T077, T080 |  | cited |
| FR-031a | T093, T095, T080 |  | cited |
| FR-032 | T080 |  | cited |
| FR-033 | T080 |  | cited |
| FR-034 | T056, T068 |  | cited |
| SC-001 | T029, T035 (open) | `pilot corpus validate`, `pilot corpus redact-check` | by content |
| SC-002 | T059 (open), T073 (open) |  | cited |
| SC-003 | T040, T055, T080 | report section 4 | by content |
| SC-004 | T062, T063 (open), T064 (open) | `pilot categorize --check`, report sections 7 and 8 | by content |
| SC-005 | T070, T073 (open), T074 (open) | report sections 9 and 10 | by content |
| SC-005a | T073 (open), T091, T092, T094, T095 | `pilot ensemble`, `pilot score`, report section 9 | by content |
| SC-006 | T075, T076, T080 | `decision.json` path, report section 1 | by content |
| SC-007 | T041, T047, T050 | run manifests and `raw/` responses | by content |
| SC-008 | T057 (open) |  | cited |
| SC-009 | T080, T085 (open) |  | cited |
| SC-010 | T020, T032 (open) | `CrawlOnceRefused` (exit 5) in `sources/` | by content |
