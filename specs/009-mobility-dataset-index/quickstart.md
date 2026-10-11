# Quickstart and validation: Mobility resource index

**Feature**: [spec.md](spec.md) | **Contracts**: [contracts/cli.md](contracts/cli.md)

These scenarios prove the feature end to end. Scenarios 1 to 5 run offline or against local
fixtures in CI. Scenarios 6 to 8 need the network and the private catalog repository.

## Prerequisites

```bash
uv sync --extra catalog --extra release
```

```bash
export MMZ_CATALOG=../mobility-model-zoo-catalog
```

Free API keys for the pilot harvesters go in `.env`, as described in `docs/credentials.md`:
`MOBILITYDATABASE_REFRESH_TOKEN` and `OPENALEX_API_KEY`.

## 1. Mandatory facts are enforced (US1, FR-005, SC-001)

Run `uv run pytest tests/catalog/test_catalog_validate.py`. It uses the fixture catalog
`tests/fixtures/catalog/`, which holds 12 entries across all six modalities plus the invalid ones
below.

Expected:
- The complete entries pass.
- The entry with no `licence` fails K1 and names the field.
- The entry with `publisher.kind: blog` fails K1 and lists the allowed kinds.
- The chart entry with `languages: [{code: zxx}]` passes.
- `zxx` combined with `es` fails.

## 2. State machine and clearing rules (FR-016, FR-018, R5)

Run `uv run pytest tests/catalog/test_catalog_rules.py tests/catalog/test_catalog_states.py`.

Expected:
- `CC-BY-4.0` with no signals and a free API route ends as `cleared` (rule U3).
- `CC-BY-NC-4.0` ends as `benchmark_only` (rule U4) and `cleared`.
- `unknown` stays `verified` with `undetermined` (rule U2).
- A `deny` signal gives `not_usable` (rule U1).
- An unclassified proprietary licence gives the flag `owner_decision_needed` (rule U6).
- A withdrawn entry never appears in a fetch list.

## 3. Query and coverage report (US2, FR-025, FR-026)

```bash
uv run zoo catalog --catalog tests/fixtures/catalog query --lang es pt --modality video --use training_allowed
```

```bash
uv run zoo catalog --catalog tests/fixtures/catalog report coverage --out /tmp/cov
```

Expected:
- The query lists exactly the fixture entries tagged for it in `tests/fixtures/catalog/EXPECTED.md`.
- The coverage report lists every target language. Languages without a training-usable entry
  appear under "gaps".

## 4. Ingest and duplicates (US3, FR-019, FR-022)

Run `uv run pytest tests/catalog/test_catalog_ingest.py`.

Expected:
- A run file with 10 candidates becomes 7 new entries, 2 merged access routes (same DOI, same
  canonical address) and 1 rejected line (missing `evidence`).
- The run header holds the per-cell counts, including a cell with zero candidates.

## 5. Fetch list hand-off (US4, FR-028, SC-007 preparation)

Run `uv run pytest tests/catalog/test_catalog_fetchlist.py`.

Expected:
- Only cleared entries become items.
- The `proposed_record` of a text entry validates against `sources.schema.json` once the
  fetch-time fields are added.
- The `proposed_record` of a structured-data entry validates against `datasets.schema.json` in
  the same way.
- The refused entries carry a reason.

## 6. Create the private catalog repository (R1, owner action)

```bash
uv run zoo catalog init ../mobility-model-zoo-catalog
```

The owner creates the private GitHub repository `mobility-model-zoo-catalog` and pushes. Expected:
the repository's CI runs `zoo catalog validate` green on an empty catalog.

## 7. Pilot: Spanish, Polish, Japanese (Riskiest Assumption)

1. Commit `pilot/pilot-v1.yaml` with the languages `es`, `pl` and `ja`, the modalities `text`,
   `video` and `structured_data`, and the criteria from the spec: at least 30% determined licence
   and at least 10 `training_allowed` per language. Do this before any pilot run.
2. Run the harvesters:

   ```bash
   uv run zoo catalog harvest data-europa --lang es pl
   ```

   ```bash
   uv run zoo catalog harvest mobility-database --area ES PL JP
   ```

   ```bash
   uv run zoo catalog harvest openalex --lang es pl ja
   ```

3. Run agent discovery through the skill `catalog-discover` for each of the three languages,
   covering video and text.
4. Check the entries and evaluate the pilot:

   ```bash
   uv run zoo catalog check
   ```

   ```bash
   uv run zoo catalog pilot evaluate pilot/pilot-v1.yaml
   ```

Expected: pass or fail per language. If two of the three languages fail, the discovery strategy is
revised before any further languages are run.

## 8. Independent re-check (SC-005, SC-008)

```bash
uv run zoo catalog audit --sample 30 --seed 9
```

Expected: at least 90% agreement, no cleared entry classified as `not_usable`, and fewer than 2%
duplicates in the audit of 50 entries.
