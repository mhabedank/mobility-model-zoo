---

description: "Task list for feature 009: mobility resource index"
---

# Tasks: Mobility resource index (multilingual, multimodal)

**Input**: Design documents from `specs/009-mobility-dataset-index/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Included. The quickstart defines test scenarios, and the project gates every change on
pytest (CI selects tests by area). Network access is never used in tests: HTTP goes through
`httpx.MockTransport` with recorded responses under `tests/fixtures/catalog/http/`.

**Organization**: Tasks are grouped by user story (spec.md US1–US6). Paths are relative to the
public repository unless they start with `catalog:`, which means the private repository
`mhabedank/mobility-model-zoo-catalog` (checked out at `$MMZ_CATALOG`, default
`../mobility-model-zoo-catalog`).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: The user story the task belongs to (US1–US6)

---

## Phase 1: Setup (shared infrastructure)

**Purpose**: Package skeleton, dependencies, CLI mount, CI routing.

- [ ] T001 Add the optional extra `catalog = ["pyyaml>=6.0", "jsonschema>=4.23", "typer>=0.12", "httpx>=0.27", "rapidfuzz>=3.14.6"]` to `pyproject.toml`, run `uv lock`, and add `--extra catalog` to the `uv sync` line of the test job in `.github/workflows/ci.yml`.
- [ ] T002 Create the package skeleton `src/mobility_model_zoo/catalog/` with `__init__.py` (docstring naming feature 009 and R1: entries live in the private repository, never in this one), empty modules `cli.py`, `model.py`, `validate.py`, `rules.py`, `states.py`, `checks.py`, `ingest.py`, `query.py`, `reports.py`, `audit.py`, `fetchlist.py` and `pilot.py`, and the folders `harvest/`, `schemas/`, `vocab/` and `templates/`, each with a one-line docstring.
- [ ] T003 Mount `zoo catalog` in `src/mobility_model_zoo/release/cli.py` with a `_mount_catalog()` function following `_mount_data()`. In `catalog/cli.py`, create the Typer app with the global option `--catalog PATH` (resolution order: option, then `$MMZ_CATALOG`, then `../mobility-model-zoo-catalog`; exit 5 with the message "catalog repository not found: …" if none exists) and an error wrapper that maps `ZooError`/`GateFailed` to their exit codes as `datasets/cli.py` `_run` does.
- [ ] T004 [P] Add a `catalog` area to `scripts/ci/select_tests.py` mapping `src/mobility_model_zoo/catalog/*`, `tests/catalog/*`, `tests/fixtures/catalog/*` and `.claude/skills/catalog-discover/*` to `tests/catalog` (plus `tests/compliance/test_signals.py` for `compliance/signals.py` changes). Keep `tests/unit/test_ci_select.py` green.
- [ ] T005 [P] Add the line `src/mobility_model_zoo/catalog/  shared resource index (feature 009); entries live in the private repository mobility-model-zoo-catalog` to the layout block in `docs/layout.md`, and add a "Resource index" row to its "Where a new topic or task goes" table.

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: Schemas, vocabularies, loading and index versioning. Every story depends on these.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T006 Copy `specs/009-mobility-dataset-index/contracts/entry.schema.json`, `candidate.schema.json` and `fetch-list.schema.json` to `src/mobility_model_zoo/catalog/schemas/`. Add `run.schema.json` for the run header in data-model.md "Entity: Discovery run", with required fields `id`, `date`, `kind` (pattern `^(harvester:[a-z0-9-]+|agent)$`), `scope{languages[],areas[],subdomains[],modalities[]}`, `method`, `agent` (object `{tool, model_id, model_version}` or null), `cost{cash_eur, notes}` and `outcome{proposed, accepted, merged, rejected, by_cell[], rejected_lines[]}`. Add a `schema(stem)` loader in `catalog/model.py` modelled on `compliance/register.py` `schema()`.
- [ ] T007 [P] Create `src/mobility_model_zoo/catalog/vocab/languages.yaml` with `version: 1`, a `changelog[]` of `{date, change, reason}`, `codes:` (every ISO 639-1 code with its English name, plus `zh-Hans`, `zh-Hant`, `zxx` "no linguistic content" and `und` "undetermined"; ISO 639-3 codes are added on demand through the changelog), and `targets:` with the 34 target languages of FR-023: `bg hr cs da nl en et fi fr de el hu ga it lv lt mt pl pt ro sk sl es sv zh ja ko hi ar tr ru id uk vi`.
- [ ] T008 [P] Create `src/mobility_model_zoo/catalog/vocab/areas.yaml` (version and changelog) with every ISO 3166-1 alpha-2 code and its English name, plus the regions `EU` (European Union), `001` (World, meaning "global"), `150` (Europe), `142` (Asia), `002` (Africa), `019` (Americas), `009` (Oceania), `145` (Western Asia) and `419` (Latin America and the Caribbean).
- [ ] T009 [P] Create `src/mobility_model_zoo/catalog/vocab/source-kinds.yaml` (version and changelog; one definition per value) with: parliament, government, research, open_data_portal, company, association, standards_body, media, community, education, individual, international_org.
- [ ] T010 [P] Create `src/mobility_model_zoo/catalog/vocab/resource-types.yaml` (version and changelog). It maps each modality to its DCMI Type (text→Text, audio→Sound, video→MovingImage, image→StillImage, graphic→StillImage, structured_data→Dataset or Service) and lists the allowed genres per modality:
  - text: paper, report, law, transcript, article, book, forum_thread, standard, statistics_publication;
  - audio: podcast, speech_recording, radio_programme;
  - video: hearing, lecture, talk, documentary, news_video, explainer;
  - image: photo, map, satellite_image;
  - graphic: chart, infographic, diagram;
  - structured_data: table, spreadsheet, database, bucket, api, feed, gtfs, gtfs_rt, geodata, time_series, sensor_data, json_xml_dump.
- [ ] T011 [P] Create `src/mobility_model_zoo/catalog/vocab/subdomains.yaml` (version and changelog) with: road, rail, public_transport, cycling, walking, micromobility, shared_mobility, aviation, maritime, freight_logistics, ev_charging, automated_driving, vehicle_technology, vehicle_security, condition_monitoring, urban_planning, rural_mobility, policy_regulation, safety, accessibility.
- [ ] T012 [P] Create `src/mobility_model_zoo/catalog/vocab/frequencies.yaml` (the EU frequency codes `CONT`, `DAILY`, `WEEKLY`, `MONTHLY`, `QUARTERLY`, `ANNUAL`, `IRREG`, `NEVER`, `UNKNOWN`), and `vocab/topics.yaml` listing the topic ids of `zoo/topics.yaml` without `sandbox`.
- [ ] T013 [P] Add `tests/catalog/test_vocab.py`. It checks that every vocabulary file has `version` and a non-empty `changelog`, that `targets` has exactly 34 codes all present in `codes`, that `vocab/topics.yaml` equals the non-sandbox ids of `zoo/topics.yaml` (drift guard), and that every genre belongs to exactly one modality.
- [ ] T014 Implement `catalog/model.py` with `load(path) -> Catalog`:
  - read `entries/**/*.yaml` and `catalog.yaml`;
  - `Catalog.entries: dict[id, dict]`, `Catalog.root`, `Catalog.commit` (`git rev-parse HEAD` in the catalog root, or None outside git), and `Catalog.sha256` (SHA-256 over the entries sorted by id and serialised as canonical JSON with sorted keys, R10);
  - `Catalog.vocab` (all vocabulary files with `vocab_version` = the maximum of their versions);
  - `write_entry(entry)`, which writes `entries/<origin_area lower>/<id>.yaml` with a stable key order (the order of the data-model table) and refuses a target path inside the public repository: raise `UsageRefused` if the catalog root resolves to the zoo repository or below it.
- [ ] T015 [P] Create the fixture catalog `tests/fixtures/catalog/`:
  - `catalog.yaml`;
  - 12 valid synthetic entries, two per modality, across `es`, `pl`, `ja`, `fr`, `zxx` and `und`, with licences CC-BY-4.0, CC-BY-NC-4.0, unknown, mixed, LicenseRef-proprietary and CC0-1.0; one collection with two items; one audio entry with transcripts;
  - a folder `invalid/` with: an entry without `licence`, one with `publisher.kind: blog`, one combining `zxx` and `es`, an item whose parent does not exist, and an entry with a non-unknown licence and `evidence_url: null`;
  - `EXPECTED.md`, listing the expected results of the quickstart queries.

  All URLs use `https://example.org/…` or `.test` domains.

**Checkpoint**: Schemas, vocabularies and loading are ready.

---

## Phase 3: User Story 1 - Record a resource with the facts that decide whether it can be used (Priority: P1) 🎯 MVP

**Goal**: The index accepts complete entries and rejects incomplete or invalid ones, naming the field (FR-005, FR-006). The private repository has its CI gate.

**Independent Test**: Quickstart scenario 1. `pytest tests/catalog/test_validate.py` passes; `zoo catalog --catalog tests/fixtures/catalog validate` exits 0, and exits 1 on `tests/fixtures/catalog/invalid`.

### Tests for User Story 1

- [ ] T016 [P] [US1] Write `tests/catalog/test_validate.py`:
  - the 12 fixture entries pass;
  - each invalid fixture fails with the expected check and field in the message (`FAIL <id> K1 languages[0].code: …`);
  - `zxx`/`und` combined with another code fails with "zxx and und cannot be combined with other codes";
  - a genre outside its modality fails;
  - a `topics` value of `sandbox` fails;
  - a `description` longer than 600 characters fails ("≤ 600 chars").
- [ ] T017 [P] [US1] Write `tests/catalog/test_dedupe.py` for R7:
  - same canonical landing URL (with/without `www.`, trailing slash) → exact duplicate;
  - same DOI → exact duplicate;
  - title + publisher similarity ≥ 0.92 → `possible_duplicate` warn only;
  - similarity < 0.92 → no finding.
- [ ] T018 [P] [US1] Write `tests/catalog/test_init.py`:
  - `zoo catalog init` creates `catalog.yaml`, `entries/`, `runs/`, `fetch-lists/`, `reports/`, `pilot/` and `.github/workflows/check.yml` in a temporary directory;
  - it refuses a non-empty directory (exit 3);
  - it refuses a path inside the zoo repository (exit 3).
- [ ] T019 [P] [US1] Write `tests/catalog/test_repo_hygiene.py`: the public repository contains no `entries/` directory with catalog entries outside `tests/fixtures/catalog/` (any `*.yaml` with `schema_version` and `landing_url` outside the fixtures fails).

### Implementation for User Story 1

- [ ] T020 [US1] Implement K1 in `catalog/validate.py`:
  - JSON Schema validation against `schemas/entry.schema.json`;
  - vocabulary membership for `languages[].code`, `content.transcripts.languages[]`, `origin_area`, `publisher.kind`, `resource_type.genre` (must be allowed for its modality), `topics[]`, `subdomains[]` and `content.frequency`;
  - the rule "`zxx` and `und` cannot be combined with other codes";
  - `licence.id` must be an SPDX id, `LicenseRef-…`, `unknown` or `mixed`.

  Each finding is a `Finding(entry_id, check, severity, field, message)`; reuse `compliance/findings.py` if it fits, otherwise a local dataclass.
- [ ] T021 [US1] Implement K2 in `catalog/validate.py`: a parent exists and has `level: collection`; an item's parent is not itself an item; `relations.translation_of[]` and `duplicate_of` targets exist; ids are unique; the file path matches `entries/<origin_area lower>/<id>.yaml`.
- [ ] T022 [US1] Implement K3 (R7) in `catalog/validate.py` with a `dedupe` helper:
  - key (a): `compliance.signals.canonical()` of `landing_url` and of every `access[].url`;
  - key (b): `identifiers.doi` (lower-cased) and `identifiers.other`;
  - key (c): `rapidfuzz.fuzz.token_sort_ratio` of normalised `title.original + publisher.name` ≥ 92.

  (a) and (b) between two entries are `fail`, unless one has `relations.duplicate_of` set to the other. (c) is `warn` and adds the flag `possible_duplicate`. Make the helper reusable by `ingest.py`.
- [ ] T023 [US1] Implement `zoo catalog validate` in `catalog/cli.py`. It runs K1, K2 and K3 (and K8 once T040 exists) offline over all entries and prints one line per finding. Exit 1 on any `fail`; with no findings it prints `ok: N entries, index <commit[:12]> <sha256[:12]>, vocab v<n>`.
- [ ] T024 [US1] Implement `zoo catalog new --from FILE.yaml` in `catalog/cli.py`. It sets `schema_version: 1`, `provenance.added_by: owner`, `provenance.added_at: today` and `status {value: candidate, since: today}`, runs K1–K3, writes the entry through `model.write_entry`, and refuses (exit 1) on a `fail`, printing the findings.
- [ ] T025 [US1] Create the scaffold templates in `src/mobility_model_zoo/catalog/templates/`:
  - `catalog.yaml` with `catalog_id`, `schema_version: 1`, `owner` and `models: {scout-large: {training_data: span-train-v1, language_shares: {de: 0.28, en: 0.72}, source: topics/productdev/recipes/scout-large.md}}`;
  - `README.md` explaining that the repository is private, holds metadata only, and must never hold content or personal data beyond attribution;
  - `.github/workflows/check.yml`, which on push and pull request installs `mobility-model-zoo[catalog,release]` from `git+https://github.com/mhabedank/mobility-model-zoo` with uv and runs `zoo catalog --catalog . validate`;
  - `.gitignore`.
- [ ] T026 [US1] Implement `zoo catalog init PATH` in `catalog/cli.py`. It copies the templates and creates the empty folders `entries/`, `runs/`, `fetch-lists/`, `reports/` and `pilot/` (each with `.gitkeep`). It refuses (exit 3) a non-empty directory or any path that resolves inside the zoo repository. It never runs git commands.
- [ ] T027 [US1] Owner-assisted step: run `uv run zoo catalog init <tmp>`, copy the result into a clone of `catalog:` (the owner created `https://github.com/mhabedank/mobility-model-zoo-catalog`), commit and push to `main` after the owner confirms, and check that the `check` workflow is green on the empty catalog (quickstart scenario 6).

**Checkpoint**: Entries can be added and validated; the private repository has its CI gate.

---

## Phase 4: User Story 2 - Answer "what do we have?" across languages, countries and modalities (Priority: P1)

**Goal**: Filtered lists and a coverage report with gaps (FR-025, FR-026).

**Independent Test**: Quickstart scenario 3. The query and report results on the fixture catalog match `tests/fixtures/catalog/EXPECTED.md`.

### Tests for User Story 2

- [ ] T028 [P] [US2] Write `tests/catalog/test_query.py`:
  - options combine with AND across options and OR within one;
  - `--lang es pt --modality video --use training_allowed` returns exactly the entries listed in `EXPECTED.md`;
  - `--transcripts yes` and `--include-transcripts` behave as described in contracts/cli.md;
  - `--format ids` prints one id per line;
  - `--format json` validates entries against the entry schema.
- [ ] T029 [P] [US2] Write `tests/catalog/test_report_coverage.py`:
  - counts and summed volume per language × modality, area, kind and permitted use match `EXPECTED.md`;
  - machine-translated and AI-generated language entries are counted separately, never as original;
  - every target language with no `cleared` or `training_allowed` entry appears in `gaps`, and so does every modality without one;
  - the JSON report carries `catalog_commit`, `catalog_sha256` and `vocab_version`.

### Implementation for User Story 2

- [ ] T030 [US2] Implement `catalog/query.py` with `select(catalog, **filters) -> list[entry]`. Filters: lang, area, modality, genre, kind, topic, subdomain, status, use (`usage.permitted_use`, where a missing `usage` counts as `undetermined`), transcripts, origin (the language origin), min_quality and include_transcripts.
- [ ] T031 [US2] Implement `zoo catalog query` in `catalog/cli.py` with the options of contracts/cli.md and `--format table|json|ids`. The table columns are id, languages, area, modality/genre, kind, licence, permitted use, status and quality.
- [ ] T032 [US2] Implement the coverage report in `catalog/reports.py` with `coverage(catalog) -> dict` and `render_markdown(dict) -> str`:
  - sections "By language × modality", "By area", "By kind of source", "By permitted use", "Machine-translated and AI-generated" and "Gaps";
  - estimated volume is summed per unit (items, hours, bytes) and never mixed across units.
- [ ] T033 [US2] Implement `zoo catalog report coverage [--out DIR]` in `catalog/cli.py`. It writes `<out or catalog:reports>/<date>-coverage.md` and `.json` and prints the gap list.

**Checkpoint**: US1 and US2 together are the MVP: a validated, queryable index with gap reporting.

---

## Phase 5: User Story 3 - Grow the index internationally through assisted discovery (Priority: P2)

**Goal**: Harvesters and the agent skill propose candidates. Automated checks (K4–K8), rules and the state machine move them to verified or cleared without per-entry owner review (FR-017, FR-018, FR-022–FR-024). The pilot gate runs.

**Independent Test**: Quickstart scenarios 2 and 4. Then one real harvester run for one pilot language, ending with a run header that has per-cell counts and only entries that pass the checks.

### Tests for User Story 3

- [ ] T034 [P] [US3] Extend `tests/compliance/test_signals.py`:
  - a robots.txt with `Content-Signal: ai-train=no` blocks with check C-F1 and sets `content_signal: deny`;
  - an HTTP header `Content-Usage` with a label listed in `compliance/lists/ai-preferences.yaml` as a reservation blocks with check C-F2 and sets `content_usage: deny`;
  - with neither present, both are `absent`;
  - the existing cases stay unchanged.
- [ ] T035 [P] [US3] Write `tests/catalog/test_rules.py`. One case per rule U1–U6 of research R5, first match wins:
  - U1: withdrawn, a `deny` signal, or `platform_terms.ml_use: not_allowed` → `not_usable` / `not_allowed`;
  - U2: licence `unknown` or `mixed` → `undetermined` / `unclear`;
  - U3: a licence on `compliance/lists/licence-allowlist.yaml` → `training_allowed` / `allowed`, with `share_alike: true` for CC-BY-SA-4.0;
  - U4: an NC or ND licence → `benchmark_only` / `not_allowed`;
  - U5: `LicenseRef-proprietary` with a kind mapped to a source class → that class's decision;
  - U6: anything else → `undetermined` plus the flag `owner_decision_needed`.

  Every outcome has `rule`, `rules_version`, `rationale` and `decided_at`.
- [ ] T036 [P] [US3] Write `tests/catalog/test_states.py` for the transitions of data-model.md:
  - candidate→verified only with no `fail`;
  - verified→cleared only when every condition of the data-model clearing rule holds: `permitted_use` in {training_allowed, benchmark_only}, signals `allow` or `absent`, platform terms not `not_allowed`, and one route with method in {direct_download, bulk_dump, api, feed, page_by_page}, `cost: free` and `auth` in {none, api_key};
  - cleared→verified with `previous` kept when a re-check changes the licence;
  - retired only after three 404/410 answers at least 7 days apart;
  - rejected, retired and withdrawn require a `reason`;
  - withdrawn requires a `request_id`.
- [ ] T037 [P] [US3] Write `tests/catalog/test_checks.py` with `httpx.MockTransport` and recorded responses in `tests/fixtures/catalog/http/`:
  - K4: 200 → pass; 404 → fail with `unreachable`;
  - K5: a missing evidence page → fail; a licence of `unknown` → skipped;
  - K6: a robots.txt deny for ClaudeBot → `deny`;
  - K7: a HEAD on `download_url` returning 405 falls back to a range GET of bytes 0–0;
  - per-host throttling (at most one request per second per host, measured with an injected clock);
  - robots.txt is cached per host for one day.
- [ ] T038 [P] [US3] Write `tests/catalog/test_ingest.py`. A run file with 10 candidates gives:
  - 7 new entries with status `candidate`;
  - 2 merges as extra `access[]` routes (same DOI; same canonical URL);
  - 1 rejected line (missing `provenance.evidence`), listed in `outcome.rejected_lines` with its reason.

  In addition: the run header holds `by_cell` counts including a zero cell; the command exits 1 when more than 20% of lines fail; candidates that contain `status`, `usage`, `signals`, `checks` or `fetched` are rejected.
- [ ] T039 [P] [US3] Write `tests/catalog/test_harvest.py`, one recorded-response test per harvester (data-europa, mobility-database, openalex, zenodo, huggingface). Each checks that:
  - a run header and JSONL are written, and every line validates against `candidate.schema.json`;
  - a missing licence becomes `licence.id: unknown`, and a missing language becomes `und`;
  - a missing key exits 5 naming `MOBILITYDATABASE_REFRESH_TOKEN` or `OPENALEX_API_KEY`;
  - the OpenAlex harvester stops before its daily budget (an injected budget counter).

### Implementation for User Story 3

- [ ] T040 [US3] Create `src/mobility_model_zoo/catalog/rules.yaml` (`version: 1`, changelog, rules U1–U6 as in research R5, and `source_class_map:` from publisher kind to topic source class, initially `parliament: parliamentary-records` for topic productdev). Implement K8 in `catalog/rules.py`: `apply(entry, allowlist, today) -> usage`, reading `compliance/lists/licence-allowlist.yaml` (with its `share_alike` flags) and treating licence ids containing `-NC` or `-ND` as U4.
- [ ] T041 [US3] Implement `catalog/states.py`: `transition(entry, check_results, usage, today) -> entry` with the state machine and flags of data-model.md. It is the only place that changes `status`.
- [ ] T042 [US3] Extend `src/mobility_model_zoo/compliance/signals.py`:
  - add `content_signal` and `content_usage` to `Verdict`;
  - parse `Content-Signal:` lines in robots.txt (`ai-train=no` → deny, check C-F1);
  - read the `Content-Usage` header and robots.txt rule, matched against labels in the new list `compliance/lists/ai-preferences.yaml` (version, changelog, `reservation_labels`, source: IETF drafts aipref-vocab-08 and aipref-attach-05, check C-F2).

  Add both fields as optional (`allow`, `deny`, `absent`) to the `signals` object of `src/mobility_model_zoo/compliance/schemas/sources.schema.json` and `datasets.schema.json`, so existing records stay valid.
- [ ] T043 [US3] Implement the network checks K4–K7 in `catalog/checks.py` on top of `compliance.signals.check_url(…, fetch_content=True)` for the landing page:
  - K5: a GET of `licence.evidence_url`, storing only its SHA-256, never the content;
  - K7: a HEAD, or a range GET of bytes 0–0, on `download_url`; a GET on the API base for `method: api`;
  - a per-host throttle of one request per second, at most eight hosts in parallel (thread pool), and a robots.txt cache of one day per host;
  - every result is written as `{check, result, at, detail, previous?}`.
- [ ] T044 [US3] Implement `zoo catalog check [--id …] [--status …] [--stale DAYS] [--offline]` in `catalog/cli.py`:
  - default selection: all `candidate` entries plus `cleared` entries with `provenance.last_verified` more than 180 days ago;
  - run K1–K8, apply `states.transition`, set `provenance.last_verified` and write the entries;
  - exit 6 only when no host was reachable at all.
- [ ] T045 [US3] Implement `zoo catalog flags`, `zoo catalog decide ID --use … --reason …` (writes `usage.rule: U0`, `rationale: owner decision: <reason>`, and removes `owner_decision_needed`), and `zoo catalog reject|retire ID --reason …` in `catalog/cli.py`.
- [ ] T046 [US3] Implement `catalog/ingest.py` and `zoo catalog ingest RUN.jsonl --run RUN.yaml`:
  - validate each line against `candidate.schema.json`;
  - assign an id when absent (slug `<area>-<publisher>-<title>` truncated to 80 characters, made unique with a numeric suffix);
  - dedupe with the T022 helper (an exact key merges as an extra `access[]` route plus evidence; a fuzzy match adds the `possible_duplicate` flag);
  - set provenance and status, run the offline checks and write entries;
  - fill `outcome` and `by_cell` (language × modality, including zero cells from `scope`) into the run header;
  - exit 1 when more than 20% of lines fail.
- [ ] T047 [US3] Implement the harvester base in `catalog/harvest/base.py`:
  - the `Harvester` protocol (`name`, `env_keys`, `iterate(scope) -> Iterator[candidate]`);
  - a shared httpx client with the project user agent from `compliance/signals.py`;
  - per-host throttling, a `--limit N`, and a budget counter hook;
  - a run writer for `runs/<date>-<slug>.yaml` and `.jsonl`;
  - a missing environment key → exit 5 naming it (the keys come from the `.env` loaded with python-dotenv as in `productdev/jtbd/config.py`).
- [ ] T048 [P] [US3] Implement `catalog/harvest/data_europa.py`: query the data.europa.eu search API by language (`es`, `pl`, …) and transport-related themes and keywords. Map `dct:license`, `dct:language`, `dct:publisher` and distribution `accessURL`/`downloadURL`/`format`/`byteSize` to candidate fields; a missing licence becomes `unknown`.
- [ ] T049 [P] [US3] Implement `catalog/harvest/mobility_database.py`:
  - exchange `MOBILITYDATABASE_REFRESH_TOKEN` for an access token (POST `https://api.mobilitydatabase.org/v1/tokens`);
  - list `gtfs_feeds` and `gtfs_rt_feeds` per `--area` country code;
  - map each feed to modality `structured_data`, genre `gtfs` or `gtfs_rt`, language `zxx`, the publisher, and the feed licence URL (licence id `unknown` unless the URL maps to SPDX);
  - set `access[].provider_hint: mobilitydatabase`;
  - group feeds by provider as collections.
- [ ] T050 [P] [US3] Implement `catalog/harvest/openalex.py`:
  - search works filtered by `language`, open-access status and transport-related concepts or topics, using `OPENALEX_API_KEY`;
  - map `best_oa_location.license` to SPDX, the DOI to `identifiers.doi`, and the `primary_location` source as a collection;
  - add a budget counter that stops at 80% of the documented free daily allowance, read from the response headers or the configured value.
- [ ] T051 [P] [US3] Implement `catalog/harvest/zenodo.py`: search records by keywords, `language` (ISO 639-3, mapped to BCP 47) and resource type; map `metadata.license.id` and files (size, type) to candidates with `provider_hint: zenodo`.
- [ ] T052 [P] [US3] Implement `catalog/harvest/huggingface.py`: list datasets from `https://huggingface.co/api/datasets` with `language:` and mobility search terms; map the card's `license` and `language` tags and set `provider_hint: huggingface`. Gated datasets get an access route with `auth: account`, so they are never cleared.
- [ ] T053 [US3] Implement `zoo catalog harvest NAME --lang … --area … --subdomain … --limit N --run-id ID` in `catalog/cli.py`, dispatching to the harvesters and then calling ingest.
- [ ] T054 [US3] Write `.claude/skills/catalog-discover/SKILL.md` following contracts/cli.md "Discovery skill":
  - input: a scope and the catalog path;
  - read the vocabularies and existing entries of that scope, including rejected, retired and withdrawn;
  - search the web, favouring kinds of source with open licences;
  - write candidate JSONL per `candidate.schema.json` with an evidence URL for every licence statement and explicit unknowns;
  - write the run header with the tool, model id and scope;
  - run `zoo catalog ingest`;
  - never download content, and stop on a CAPTCHA or login.

  Write the skill in English, as `tests/unit/test_docs_english.py` requires.
- [ ] T055 [US3] Implement `catalog/pilot.py` and `zoo catalog pilot evaluate FILE`. Read `catalog:pilot/pilot-v1.yaml` (`languages`, `modalities`, `runs[]`, `criteria {min_determined_licence_share: 0.30, min_training_allowed: 10, min_languages_passing: 2}`, `criteria_changes[]`). Compute, per language over the accepted entries of the named runs:
  - the share with a licence other than `unknown`;
  - the count with `training_allowed`.

  Print pass or fail per language and overall. Exit 3 if `git log` of the pilot file shows a change after the first run date without a matching `criteria_changes` entry (constitution IV).
- [ ] T056 [P] [US3] Write `tests/catalog/test_pilot.py` covering pass, fail, overall fail (2 of 3 languages fail), and the refusal on changed criteria without a rationale.
- [ ] T057 [US3] Pilot preparation (catalog repository): commit `catalog:pilot/pilot-v1.yaml` with languages `es pl ja`, modalities `text video structured_data`, and the criteria of T055, before any pilot run.
- [ ] T058 [US3] Pilot run (catalog repository). Run in this order:
  1. `zoo catalog harvest data-europa --lang es pl`;
  2. `zoo catalog harvest mobility-database --area ES PL JP`;
  3. `zoo catalog harvest openalex --lang es pl ja`;
  4. `zoo catalog harvest zenodo --lang es pl ja`;
  5. the `catalog-discover` skill for es, pl and ja with the modalities video and text;
  6. `zoo catalog check`;
  7. `zoo catalog pilot evaluate pilot/pilot-v1.yaml`.

  Commit the runs, the entries and the evaluation output (`catalog:reports/<date>-pilot.md`).
- [ ] T059 [US3] Pilot gate: if the overall result is fail (two of three languages miss the criteria), stop and write `catalog:reports/<date>-pilot-review.md` covering what failed and the revised discovery strategy. Phase 9, T079 onwards (the scale-up), MUST NOT start until a pilot run passes.

**Checkpoint**: Discovery works end to end; the riskiest assumption is tested.

---

## Phase 6: User Story 4 - Hand a selection to a later download step (Priority: P2)

**Goal**: Fetch lists that pre-fill the existing registers, plus linking after download (FR-028, FR-029).

**Independent Test**: Quickstart scenario 5. Each `proposed_record` validates against `sources.schema.json` or `datasets.schema.json` once the fetch-time fields are added.

### Tests for User Story 4

- [ ] T060 [P] [US4] Write `tests/catalog/test_fetchlist.py`:
  - only `cleared` entries become items; every other entry is in `refused` with its status and reason;
  - a withdrawn entry is never an item;
  - the file validates against `fetch-list.schema.json`;
  - a text entry's `proposed_record`, after adding `storage`, `retention_until`, `crawl_manifest_sha256` and `pii_scan` stubs, validates against `src/mobility_model_zoo/compliance/schemas/sources.schema.json`;
  - a structured-data entry's record validates against `datasets.schema.json`;
  - an empty item list exits 3.
- [ ] T061 [P] [US4] Write `tests/catalog/test_link.py`:
  - `zoo catalog link` sets `fetched` and the status `fetched` when the record exists in a fixture topic register;
  - it exits 3 when the record is missing;
  - `require_cleared` raises `UsageRefused` for an uncleared entry or one verified more than 180 days ago.

### Implementation for User Story 4

- [ ] T062 [US4] Implement `catalog/fetchlist.py`. `build(catalog, selection, name) -> dict` picks the first usable access route. The target register is `datasets` for modality `structured_data` and `sources` otherwise; the target topic is the first of `topics[]`. `proposed_record(entry)` maps entry fields to the register fields:
  - `id`, `origin_url`, `title`, `publisher`;
  - `creators`: the publisher name;
  - `licence`, `licence_url`, `attribution_text`;
  - `modifications`: "Not yet fetched; proposed from catalog entry <id>.";
  - `permitted_use`, `redistribution`;
  - `redistribution_basis`: the usage rationale;
  - `quote_allowed: false`;
  - `signals` (only the fields that exist in the target schema);
  - `personal_data`: `{present: expectation != none, categories, special_categories: []}`;
  - `platform_terms`;
  - for datasets, also `provider` (from `provider_hint`), `locator`, `approx_size_mb`, `commercial_use` and `license_check: manual`.

  Write the result to `catalog:fetch-lists/<date>-<name>.yaml` with `catalog_commit`, `catalog_sha256`, `vocab_version` and `rules_version`.
- [ ] T063 [US4] Implement `zoo catalog fetchlist NAME [query options]` in `catalog/cli.py`, reusing `query.select`; exit 3 when no item remains.
- [ ] T064 [US4] Implement `zoo catalog link ID REGISTER:TOPIC:RECORD` in `catalog/cli.py`. Look up the record in `topics/<topic>/compliance/<register>.yaml` of the zoo repository (`--zoo-root`, default the current directory); exit 3 if it is missing; set `fetched {register, topic, record_id, linked_at}` and the status `fetched`.
- [ ] T065 [US4] Implement the library interface in `catalog/__init__.py`: `load`, `fetchlist.read(path)` (validated against the schema) and `require_cleared(entry_id, catalog)`. The last raises `release.errors.UsageRefused` unless the status is `cleared` and `last_verified` is within 180 days.

**Checkpoint**: A later download feature can consume fetch lists without new research.

---

## Phase 7: User Story 5 - Keep the index current and honour objections (Priority: P3)

**Goal**: Periodic re-checks and withdrawal through the existing objection channel (FR-020, FR-021).

**Independent Test**: Changing the licence evidence of a fixture entry and running `check` revokes `cleared`. `withdraw` with a request id sets `withdrawn` and adds suppression hashes.

### Tests for User Story 5

- [ ] T066 [P] [US5] Write `tests/catalog/test_recheck.py`:
  - a cleared entry whose evidence page hash changed → `verified` with flag `licence_changed`, and `previous` holds the old hash and licence;
  - a landing page 404 → flag `unreachable`, and the entry stays out of fetch lists;
  - three 404s at least 7 days apart → `retired` with a reason.
- [ ] T067 [P] [US5] Write `tests/catalog/test_withdraw.py`:
  - `withdraw` with an unknown request id exits 3;
  - with a known request in a temporary `compliance/requests.yaml`, the status becomes `withdrawn` with `request_id` and `reason`;
  - `compliance/suppression.yaml` gains one keyed hash per canonical landing and access URL (same hashing as `zoo compliance request add`);
  - `compliance.signals.check_url` then blocks the URL with C-F5.

### Implementation for User Story 5

- [ ] T068 [US5] Store the previous values (licence id, evidence hash, signals) in `checks[].previous` in `catalog/checks.py` and `catalog/states.py`. Implement the `retired` rule (three 404 or 410 answers at least 7 days apart, counted from the K4 history in `checks[].previous`).
- [ ] T069 [US5] Implement `zoo catalog withdraw ID --request REQ [--zoo-root PATH]` in `catalog/cli.py`:
  - look up `REQ` in `compliance/requests.yaml` (types objection, takedown or opt_out; exit 3 otherwise);
  - set the status `withdrawn` with `request_id` and `reason`;
  - add `keyed_hash(canonical(url))` for the landing page and every access URL to `compliance/suppression.yaml` using the helpers behind `zoo compliance request add` (`compliance/hashing.py`, needs `MMZ_SUPPRESSION_KEY`; exit 5 without it).
- [ ] T070 [US5] Add the catalog maintenance routine to `docs/catalog.md`: monthly `zoo catalog check` (re-checks cleared entries older than 180 days, SC-009), `zoo catalog flags` for the owner queue, and objections through `zoo compliance request add` followed by `zoo catalog withdraw`.

**Checkpoint**: The index stays current and objections are enforced twice, at the index and at fetch time.

---

## Phase 8: User Story 6 - See where the models' languages and the index diverge (Priority: P3)

**Goal**: A language report showing base-model coverage and training shares (FR-027, R9).

**Independent Test**: On the fixture catalog, the report lists `mt` as "not supported by the current base model" for scout-large, and `es` with a training share of 0.

### Tests for User Story 6

- [ ] T071 [P] [US6] Write `tests/catalog/test_report_languages.py`:
  - every language in the index appears with entries, cleared entries and volume;
  - for scout-large, read from `zoo/models/scout-large/model.yaml` (`base_model: FacebookAI/xlm-roberta-large`), `mt` is `no`, `es` is `yes` and an unknown base model gives `unknown`;
  - the training shares come from `catalog.yaml` (`de 0.28`, `en 0.72`, and 0 for the rest);
  - the JSON report carries the index version.

### Implementation for User Story 6

- [ ] T072 [P] [US6] Create `src/mobility_model_zoo/catalog/vocab/base-models.yaml` (version and changelog). It maps `FacebookAI/xlm-roberta-large` (and `xlm-roberta-base`) to the 100 CC-100 language codes of `https://github.com/facebookresearch/fairseq/tree/main/examples/xlmr`, recording that Maltese is absent and Irish is present. Add the source URL and the check date 2026-10-10.
- [ ] T073 [US6] Implement `languages(catalog, zoo_root) -> dict` in `catalog/reports.py`, plus its markdown rendering, and `zoo catalog report languages [--out DIR] [--zoo-root PATH]` in `catalog/cli.py`.

**Checkpoint**: The encoder decision is backed by data.

---

## Phase 9: Polish, audit and scale-up (cross-cutting)

**Purpose**: The independent re-check (SC-005, SC-008), documentation, and the scale-up to the first-version targets (SC-002–SC-004).

- [ ] T074 [P] Write `tests/catalog/test_audit.py`. With a seeded sample and mocked evidence pages and a mocked local model client, the audit must:
  - report agreement of the stored `permitted_use` with the SPDX matcher and with the model;
  - exit 1 when agreement is below 90% or when any cleared entry is classified `not_usable`;
  - report duplicates in a 50-entry sample;
  - record the seed, the sample ids and the model id.
- [ ] T075 Implement `catalog/audit.py` and `zoo catalog audit --sample N [--seed S] [--model ID]`:
  - a deterministic SPDX matcher over licence names, URLs and badges in the evidence page text, held in memory only;
  - a classification by a local model on the DGX Spark through the OpenAI-compatible endpoint configured in `.env` (`OLLAMA_HOST`); the default model is a non-Claude family, with its name recorded;
  - output to `catalog:reports/<date>-audit.{md,json}`.
- [ ] T076 [P] Write `docs/catalog.md`, the guide covering: purpose and the R1 storage rule (entries never in the public repository), setup (`MMZ_CATALOG`, keys), adding entries, harvesters, the discovery skill, checks and flags, fetch lists, reports, the audit, and maintenance (from T070). Link it from `README.md`'s documentation list if one exists, and from `docs/layout.md`.
- [ ] T077 [P] Add `docs/catalog.md` and `.claude/skills/catalog-discover/SKILL.md` to the paths checked by `tests/unit/test_docs_english.py` if that test uses an explicit list. Run `uv run ruff check` and `uv run pytest tests/catalog tests/compliance/test_signals.py tests/unit/test_ci_select.py` green.
- [ ] T078 Run the quickstart scenarios 1–5 from `specs/009-mobility-dataset-index/quickstart.md` against the fixture catalog. Record the outcome in `specs/009-mobility-dataset-index/validation.md`.
- [ ] T079 Scale-up batch 1 (only after T059 passes), catalog repository: run the harvesters data-europa, zenodo, openalex and huggingface for the remaining EU languages (`bg hr cs da nl et fi fr el hu ga it lv lt mt pt ro sk sl sv`), and mobility-database for their countries. Then run `zoo catalog check` and commit the runs and entries.
- [ ] T080 Scale-up batch 2, catalog repository: run the harvesters for `zh ja ko hi ar tr ru id uk vi` (openalex, zenodo, huggingface; mobility-database for CN, KR, IN, SA, AE, EG, TR, ID, UA and VN). Then `zoo catalog check`, and commit.
- [ ] T081 Scale-up batch 3, catalog repository: run the `catalog-discover` skill over the gaps reported by `zoo catalog report coverage`, prioritising audio, video, image and graphic, which harvesters cover poorly. Spread the runs over several days because of the subscription usage limits; each run is one scope cell.
- [ ] T082 Final measurement, catalog repository: `zoo catalog report coverage`, `zoo catalog report languages` and `zoo catalog audit --sample 30 --seed 9`. Commit the reports. Record in `specs/009-mobility-dataset-index/validation.md` whether SC-001 to SC-005, SC-008 and SC-009 are met, with numbers. SC-007 is measured by the later download feature, and SC-006 by the owner.

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)** has no dependencies. T001 comes first, because T003 imports typer through the extra.
- **Foundational (Phase 2)** depends on Setup and blocks all stories.
- **US1 (Phase 3)** depends on Phase 2. T027 (pushing the private repository) needs the owner's confirmation.
- **US2 (Phase 4)** depends on Phase 2 and can run in parallel with US1 once T014 and T015 exist. Its `use` filter reads `usage`, which the fixtures carry, so it does not wait for US3.
- **US3 (Phase 5)** depends on US1 (validate, dedupe, write_entry). T040 also completes K8 in `validate` (T023).
- **US4 (Phase 6)** depends on US3 (states, so that `cleared` exists) and on US2 (`query.select`).
- **US5 (Phase 7)** depends on US3 (checks, states).
- **US6 (Phase 8)** depends on Phase 2 and US2 (`reports.py`); it is independent of US3–US5.
- **Polish (Phase 9)**: T074–T078 depend on US1–US6. The scale-up tasks T079–T082 depend on the pilot gate T059.

### Within each story

- Tests are written first and must fail before the implementation.
- Rules and state machine (T040, T041) come before checks (T043) and the check command (T044).
- The harvester base (T047) comes before the harvesters (T048–T052), and they come before `harvest` (T053) and the pilot (T058).

### Parallel opportunities

- Phase 2: T007–T012 (the vocabulary files) and T015 (fixtures) in parallel.
- US1: the tests T016–T019 in parallel.
- US3: the tests T034–T039 in parallel; the harvesters T048–T052 in parallel after T047.
- US2 and US6 can run alongside US3.

## Parallel Example: User Story 3

```bash
# Tests together:
Task: "Extend tests/compliance/test_signals.py for Content-Signal and Content-Usage"
Task: "Write tests/catalog/test_rules.py (U1–U6)"
Task: "Write tests/catalog/test_states.py"
Task: "Write tests/catalog/test_checks.py with recorded responses"
Task: "Write tests/catalog/test_ingest.py"
Task: "Write tests/catalog/test_harvest.py"

# Harvesters together after T047:
Task: "catalog/harvest/data_europa.py"
Task: "catalog/harvest/mobility_database.py"
Task: "catalog/harvest/openalex.py"
Task: "catalog/harvest/zenodo.py"
Task: "catalog/harvest/huggingface.py"
```

## Implementation Strategy

### MVP first (US1 + US2)

1. Phases 1 and 2.
2. US1: validate, new, init, and the private repository with its CI gate.
3. US2: query and the coverage report.
4. **Stop and validate**: quickstart scenarios 1 and 3. Entries can already be added by hand and the gaps are visible.

### Incremental delivery

1. US3 brings discovery and the pilot gate. This is the decisive increment for "going international".
2. US4 brings fetch lists, which are what the download feature waits for.
3. US5 keeps the index current and lawful.
4. US6 adds the language report.
5. Scale-up to 2,000+ entries over batches 1–3.

### Notes

- Never commit catalog entries to the public repository (T019 enforces this).
- Every harvester and agent run is one discovery run with its own header; failed lines stay in the header and never become entries.
- Commit after each task or logical group. Catalog-repository commits are separate from public-repository commits.
