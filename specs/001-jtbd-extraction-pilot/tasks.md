---

description: "Task list for the JTBD Extraction Pilot"
---

# Tasks: JTBD Extraction Pilot

**Input**: Design documents from `specs/001-jtbd-extraction-pilot/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: included. The plan and quickstart require `pytest` with hand-computed fixtures for metrics, matching, quotes, consensus, the decision table and the budget guard, plus an end-to-end run on the mini corpus. Write each test task before the implementation it covers, and confirm the test fails first.

**Organization**:
- Tasks are grouped by user story (US1–US5 from spec.md).
- Some tasks are operational rather than code, for example collecting sources or running a model. They are marked **(ops)** and name the file they produce.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1–US5
- Paths are relative to the repository root (single project, see plan.md)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: project skeleton and tooling.

- [X] T001 Create `pyproject.toml` with `uv`:
  - Python 3.12, package `jtbd_pilot` under `src/jtbd_pilot/`, console script `pilot = jtbd_pilot.cli:app`
  - dependencies: pydantic>=2, typer, openai, httpx, scikit-learn, scipy, numpy, pandas, matplotlib, trafilatura, pypdf, pyyaml, jsonschema
  - dev dependencies: pytest, ruff
- [X] T002 Create the directory layout from plan.md:
  - `configs/domain/`, `guideline/examples/`, `src/jtbd_pilot/{sources,corpus,labeling,report}/` with `__init__.py`, `benchmarks/pilot-v1/`, `reports/pilot-v1/figures/`, `tests/{unit,integration,fixtures/mini-corpus}/`
  - `.gitignore` with `data/` and `.env`. `data/` is **never** committed (Principle VI)
- [X] T003 [P] Configure ruff and pytest in `pyproject.toml` (`[tool.ruff]`, `[tool.pytest.ini_options] testpaths=["tests"]`)
- [X] T004 [P] Create `.env.example` with `OPENROUTER_API_KEY=`, `OLLAMA_HOST=http://spark:11434`, `OLLAMA_HOST_VM=` and `REDDIT_CLIENT_ID=`/`REDDIT_CLIENT_SECRET=`, each with a comment. Add `README.md` with the setup steps from quickstart.md "Prerequisites".

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the schema, configuration, hashing, budget and CLI skeleton that every story uses.

**⚠️ CRITICAL**: no user-story work starts until this phase is complete.

- [X] T005 [P] Write `tests/unit/test_schema.py`. It asserts:
  - the JSON Schema exported from `schema.py` equals `specs/001-jtbd-extraction-pilot/contracts/extraction-output.schema.json` (semantic equality)
  - an empty `items` list validates
  - `additionalProperties: false` rejects extra keys
- [X] T006 Implement `src/jtbd_pilot/schema.py` with the Pydantic v2 models:
  - `ExtractionOutput{relevant: bool, items: list[Item]}`
  - `Item` with these fields:
    - `kind ∈ {job, pain, gain}`
    - `quote` (minLength 1, "Verbatim substring of the chunk text, in the source language")
    - `actor`
    - `actor_type ∈ {individual, worker, organization, public_sector, society}`
    - `statement` (English)
    - `evidence_type ∈ {opinion, anecdote, routine, observation, measurement}` (ordinal 0–4, exposed through a helper `evidence_rank()`)
    - `evidence_scope ∈ {single, multiple, quantified}`
  - Also the models `SourceSnapshot`, `ChunkRecord`, `LabelRunManifest` and `DecisionCriteria`, which mirror the contract schemas in `specs/001-jtbd-extraction-pilot/contracts/`.
  - An `export_json_schema(model)` helper.
- [X] T007 [P] Implement `src/jtbd_pilot/config.py`:
  - loads `configs/pilot-v1.yaml`, `configs/models.yaml`, `configs/budget.yaml`, `configs/decision-criteria.yaml` and `configs/domain/mobility.yaml` into typed objects
  - `--config` override
  - reads `.env`
- [X] T008 [P] Create `configs/domain/mobility.yaml`:
  - the domain definition, quoted verbatim from spec FR-001
  - the five sub-areas as enum keys `public_transport_rural`, `logistics_delivery`, `emobility_charging`, `car_ownership_use`, `sharing_platforms`
  - no persona fields (Principle I)
- [X] T009 [P] Create `configs/pilot-v1.yaml`:
  - composition targets from FR-002 to FR-007: main 140–160 chunks; sub-area 15–25% of relevant chunks; source type 18–32%; irrelevant or near-miss 15–25%; non-EU 10–15%; each language ≥ 35%
  - holdout of about 30 chunks
  - chunk length 300–1500 tokens
  - `min_iou: 0.3`, `bootstrap_resamples: 1000`, `underpowered_min_units: 30`
  - `max_retries: 2`
  - `consistency_rules: [irrelevant_no_items, enum_values, quantified_has_quantity]`
- [X] T010 [P] Create `configs/decision-criteria.yaml` by copying `specs/001-jtbd-extraction-pilot/contracts/decision-criteria.example.yaml`: relevance ≥ 0.8, evidence type ≥ 0.6, kind, actor type and scope ≥ 0.6, item F1 ≥ 0.7, rethink below 0.4, `max_reruns: 1`, quality ratio 0.85, throughput ratio 10.
- [X] T011 [P] Create `configs/budget.yaml` with `budget_eur: 20`, `key_cap_eur: 12`, a price table per model (EUR per million input, cached input and output tokens, filled in during T046) and `openrouter_fee: 0.055`.
- [X] T012 [P] Create `configs/models.yaml` with the entries (`model_id`, `family`, `backend`, `host`, `role`, `quantization`, `benchmark_labeler: bool`):
  - Claude reference: `backend: claude_cli`, `family: anthropic-claude`
  - GPT mini reference: `backend: openrouter`, `provider.order: [openai]`, `family: openai-gpt`
  - teacher A: Qwen, `backend: ollama`, `host: spark`
  - teacher B: GLM, `backend: ollama`, `host: spark`
  - baselines `qwen3.5:4b`, `gemma4:e4b` and `ministral-3:3b`
  - *(2026-09-29: teacher entries replaced by the spike's `teacher-qwen3.8`, `teacher-or-mimo-v2.6-pro`, `teacher-or-deepseek-v4.1-flash` and `teacher-or-glm-5.3-flash`; see T071.)*
- [X] T013 [P] Write `tests/unit/test_freeze.py`:
  - canonical hashing is stable across CRLF/LF line endings and YAML key order
  - a changed criteria file produces a mismatch
- [X] T014 Implement `src/jtbd_pilot/freeze.py`:
  - `sha256_canonical(path)` (UTF-8, LF, sorted keys for YAML and JSON)
  - `write_manifest()` and `verify_frozen()` against `benchmarks/pilot-v1/manifest.json`, raising `FrozenHashMismatch`
  - manifest fields: `version`, guideline, schema, criteria and budget hashes, main `chunk_ids` with text hashes, `frozen_at`, `state` (`criteria_frozen` or `frozen`), `rationale` for a new version
- [X] T015 [P] Write `tests/unit/test_budget.py`:
  - the guard refuses when `cumulative + estimated > budget` (€20)
  - the guard refuses when an OpenRouter run would exceed the key cap (€12)
  - `claude_cli` and `ollama` estimates are €0
  - the ledger is append-only
- [X] T016 Implement `src/jtbd_pilot/budget.py`:
  - append-only ledger `data/budget/ledger.jsonl` with fields `ts, item, estimated_eur, actual_eur, cumulative_eur, cap_eur`
  - `estimate_run(model, n_chunks, avg_in, avg_cached_in, avg_out)` using `configs/budget.yaml`, including the fee
  - `guard()`, which raises `BudgetRefused`
- [X] T017 Implement the CLI skeleton `src/jtbd_pilot/cli.py`:
  - typer app with subcommand groups `source`, `corpus`, plus `freeze`, `label`, `budget`, `check`, `match`, `consensus`, `categorize`, `agreement`, `score`, `perf`, `decide` and `report`
  - global `--config` and `--dry-run`
  - exit codes from `specs/001-jtbd-extraction-pilot/contracts/cli.md`: 0 ok, 1 validation, 2 usage, 3 frozen-hash mismatch, 4 budget refusal, 5 crawl-once refusal, 6 backend failure
  - human logs go to stderr, the JSON summary to stdout
- [X] T018 [P] Implement `pilot budget [--estimate --run <spec>]` in `src/jtbd_pilot/cli.py`, backed by `budget.py`
- [X] T019 [P] Create the mini-corpus fixture in `tests/fixtures/mini-corpus/`:
  - 5 chunk records: 2 German and 3 English, one `irrelevant`, and one with a parent-context range
  - 2 snapshot records
  - `pilot.yaml` pointing at the fixture paths, with `test_fixture: true` so the mock chain can freeze a `test_only` benchmark
  - mock responses for two reference "models" in `mock_a/` and `mock_b/`, including:
    - one agreed item
    - one kind disagreement on the same span
    - one item that only one model has
    - one fabricated quote
    - one evidence-type disagreement of distance 2
  - `expected.json` with hand-computed kappa, F1, consensus and contested values

**Checkpoint**: schema, config, freeze, budget and CLI skeleton work, and `uv run pytest tests/unit` passes.

---

## Phase 3: User Story 1 - Assemble a compliant, balanced pilot corpus (Priority: P1) 🎯 MVP

**Goal**: about 150 main chunks and about 30 holdout chunks from lawful sources, each stored once as a full snapshot, with complete metadata, redacted, and meeting the composition targets.

**Independent Test**: `pilot corpus validate --split main`, `pilot corpus validate --split holdout` and `pilot corpus redact-check` exit 0. The composition table meets FR-002 to FR-007. Every chunk references a snapshot (SC-001, SC-010). No model is called.

### Tests for User Story 1

- [X] T020 [P] [US1] Write `tests/unit/test_sources.py`:
  - fetching an already snapshotted canonical URL raises `CrawlOnceRefused` (exit 5)
  - `--update --reason` creates a new snapshot with `supersedes` set
  - `source_type: reddit` forces `permitted_uses: benchmark_only`, and `training_allowed` is rejected
  - `snapshot_id` matches `^snap-[0-9a-f]{12}$`
  - a `retention_until` value is required
- [X] T021 [P] [US1] Write `tests/unit/test_corpus.py`:
  - redaction removes `u/name`, `@name`, emails, phone numbers and profile URLs
  - `redact-check` fails on residual patterns and on a missing `manual_review_at`
  - the stratified split is reproducible for a fixed seed
  - validate reports each composition target as pass or fail on a synthetic corpus
  - token length outside 300–1500 is flagged

### Implementation for User Story 1

- [X] T022 [P] [US1] Implement `src/jtbd_pilot/sources/registry.py`:
  - snapshot index `data/snapshots/index.jsonl`
  - `canonicalize_url()`, which drops tracking parameters and fragments and normalizes the scheme and host
  - `exists(url)`
  - `register(snapshot)`, which enforces the rule "**Unique**: a second fetch of the same canonical URL is refused unless `supersedes` is set" and the rule "`update_reason` required when `supersedes` is set"
- [X] T023 [P] [US1] Implement `src/jtbd_pilot/sources/fetch.py`:
  - generic HTTP fetch that checks robots.txt before fetching
  - stores `raw.<ext>` unmodified, extracts `text.txt` with trafilatura (HTML) or pypdf (PDF), and writes `source.yaml` (the SourceSnapshot fields)
  - never re-fetches a URL that already has a snapshot
- [X] T024 [P] [US1] Implement `src/jtbd_pilot/sources/reddit.py`:
  - fetches a thread (post plus comment tree) through the **official Reddit Data API** with OAuth credentials from `.env`
  - rate limit of 100 queries per minute
  - writes the whole thread as one snapshot with `permitted_uses: benchmark_only` and `legal_basis: "§ 60d UrhG, Reddit Data API (Reddit for Researchers)"`
  - accepts thread IDs, for example ones found with Arctic Shift search, but **never** downloads text from Arctic Shift
- [X] T025 [US1] Implement `pilot source fetch|register|list` in `src/jtbd_pilot/cli.py`, as specified in `contracts/cli.md` "Sources", using T022 to T024. `register` imports a file obtained manually, such as a PDF study.
- [X] T026 [P] [US1] Implement `src/jtbd_pilot/corpus/build.py`:
  - `pilot corpus build --from data/chunks/selection.yaml` cuts chunks from snapshot text using the listed `ranges`, with multiple ranges for parent context (FR-009)
  - fills the ChunkRecord metadata from the selection and the snapshot: `sub_area`, `region` ∈ {DACH, EU_other, non_EU} plus `country`, `language` ∈ {de, en}, `date`, `license`, `relevance_intent` ∈ {relevant, irrelevant, near_miss}
  - counts tokens with a fixed tokenizer approximation, recorded in the chunk
  - never fetches
- [X] T027 [P] [US1] Implement `src/jtbd_pilot/corpus/redact.py`:
  - versioned patterns (`patterns_version`)
  - `redact(text)`
  - `redact_check(chunks)`, which requires `redaction.check_passed` and `manual_review_at`
  - CLI `pilot corpus redact` and `pilot corpus redact-check`
- [X] T028 [P] [US1] Implement `src/jtbd_pilot/corpus/split.py`:
  - `pilot corpus split --holdout 30 --seed <n>`
  - stratified by sub-area × source type × language
  - marks the holdout chunks as locked, so they cannot be labeled until the pilot state is `revise`
- [X] T029 [P] [US1] Implement `src/jtbd_pilot/corpus/validate.py`:
  - `pilot corpus validate [--split]` checks each FR-002 to FR-007 target and metadata completeness per split
  - prints a composition table (sub-area, source type, language, region, relevance intent) and writes `data/analysis/composition-<split>.json`
  - exit 1 on a miss, or when a substitution is recorded (for example Reddit replaced by Stack Exchange) without an explanation
- [X] T030 [US1] **(ops)** ~~Dropped on 2026-09-29 (project decision, spec.md Clarifications): no Reddit; forum_review substitutes via `configs/pilot-v1.yaml`.~~ Apply for Reddit data access through "Reddit for Researchers" and register an OAuth app. Record the status and date in `data/sources/reddit-access.md`. If access is not granted before T034 starts, use the fallback from research.md R2 (Stack Exchange, CC BY-SA) and record the substitution.
- [ ] T031 [US1] **(ops)** Build the source plan `data/sources/source-plan.yaml`. It covers:
  - for each sub-area × source type cell: candidate sources and URLs, license or legal basis, `permitted_uses`, and the date the terms and robots.txt were checked (research.md R3)
  - papers and studies chosen so that observation and measurement evidence is likely to appear in at least 30 consensus items (FR-008)
  - non-European sources for 10–15%
  - near-miss and irrelevant sources, for example cars as hobby objects or motorsport
  - Bundestag protocols (DIP API) and the Scientists for Future podcast for transcripts
- [ ] T032 [US1] **(ops)** Fetch every source in the plan exactly once with `pilot source fetch`, `pilot source register` or the Reddit fetcher, into `data/snapshots/`, with a `retention_until` for each.
- [ ] T033 [US1] **(ops)** Write `data/chunks/selection.yaml` (about 180 chunks, with ranges, metadata and relevance intent), then run `pilot corpus build`.
- [ ] T034 [US1] **(ops)** Run `pilot corpus redact`, manually review every chunk (setting `manual_review_at`), then run `pilot corpus redact-check` until it exits 0. If personal data is found **after** labeling has started: remove or re-redact the chunk, freeze a new version with `pilot freeze --new-version <v> --rationale "re-redaction <chunk_id>"`, relabel that chunk with every run that has already processed it (the old raw responses stay unmodified and are marked superseded), then recompute from `pilot check` onwards (spec Edge Cases).
- [ ] T035 [US1] **(ops)** Run `pilot corpus split --holdout 30 --seed 20260925`, then `pilot corpus validate --split main` and `--split holdout`. Fix the selection until both exit 0. Keep `data/analysis/composition-main.json` and `composition-holdout.json` for the report.

**Checkpoint**: a validated, redacted, snapshot-backed corpus. US1 is complete.

---

## Phase 4: User Story 2 - Establish the frontier reference and measure agreement (Priority: P1)

**Goal**: a frozen guideline and frozen criteria; Claude and GPT labels for every main chunk; deterministic checks; the consensus and contested set; agreement per dimension with CI and breakdowns.

**Independent Test**: on the mini corpus with the mock backend, `pilot freeze → label ×2 → check → match → consensus → freeze --benchmark → agreement` (with `test_fixture: true`) reproduces `tests/fixtures/mini-corpus/expected.json`. On the real corpus, both reference manifests exist with model version and date, and agreement is reported for all six dimensions with n and CI (SC-002, SC-003).

### Tests for User Story 2

- [X] T036 [P] [US2] Write `tests/unit/test_quotes.py`:
  - exact match
  - a match after normalizing whitespace, line breaks and typographic quotes („“ ”“ ‚‘ ’) counts as found
  - a paraphrase fails
  - a translated German quote fails
  - the returned span is correct
  - with several occurrences, the first unused one is taken
- [X] T037 [P] [US2] Write `tests/unit/test_checks.py`:
  - `schema_valid` fails for malformed JSON and for a missing field
  - `irrelevant_no_items` fails when `relevant=false` and items are present
  - `quantified_has_quantity` fails when `evidence_scope=quantified` and the quote has no digit or number word (de and en)
  - `enum_values` catches values outside the enums
- [X] T038 [P] [US2] Write `tests/unit/test_matching.py`:
  - IoU on character spans
  - one-to-one Hungarian assignment
  - a same-kind candidate wins a tie over a higher-IoU different-kind candidate only when the IoUs are equal within 1e-9 (a tie-break, never a precondition)
  - pairs below `min_iou` 0.3 stay unmatched
  - items that fail the quote check are excluded
- [X] T039 [P] [US2] Write `tests/unit/test_consensus.py`, following FR-021 and FR-022:
  - a matched item that agrees on all dimensions becomes a ConsensusEntry
  - a kind disagreement is contested only on `kind` and stays in the consensus for the other dimensions
  - an unmatched item is contested on `item_existence`
  - relevance disagreement is contested at `level: relevance`
- [X] T040 [P] [US2] Write `tests/unit/test_metrics.py` against `tests/fixtures/mini-corpus/expected.json`:
  - Cohen's kappa
  - quadratic-weighted kappa (and linear) for evidence type
  - item F1
  - bootstrap CI resampled by chunk, deterministic with a seed
  - `underpowered` set when n < 30
- [X] T041 [P] [US2] Write `tests/unit/test_label_runner.py`:
  - refuses without a frozen hash (exit 3)
  - refuses when the budget guard fails (exit 4)
  - refuses a `teacher_candidate` whose model is a `benchmark_labeler`, and a teacher family that equals a reference family (exit 1)
  - refuses `--split holdout` unless the pilot state is `revise`
  - stops with exit 6 when the reported model version changes mid-run
  - resumes by skipping chunks that already have a raw response
  - never overwrites a raw response
- [X] T042 [P] [US2] Write `tests/integration/test_mini_corpus_reference.py`, which runs the CLI chain with the `mock` backend on `tests/fixtures/mini-corpus/` and compares the results to `expected.json`.

### Implementation for User Story 2

- [X] T043 [US2] **(ops/doc)** Write the labeling guideline `guideline/guideline-v1.md`. It covers:
  - the domain definition (included from `configs/domain/mobility.yaml`)
  - the relevance rule, including near-miss examples
  - job, pain and gain definitions, including pain versus negated gain
  - the five actor types
  - the five ordinal evidence types with boundary rules (anecdote versus routine, observation versus measurement)
  - the three evidence scopes
  - the verbatim-quote rule: the quote stays in the source language, and the statement is written in English
  - the rule "when uncertain, take the lower grade"
  - "an empty result is valid"
  - the minimum IoU note
- [X] T044 [P] [US2] **(ops/doc)** Write worked examples in `guideline/examples/`: at least 6 (German and English), among them one correct empty result, one near-miss, one measurement-level item and one item with multiple actors.
- [X] T045 [US2] Implement `src/jtbd_pilot/labeling/prompt.py`: `build_prompt(guideline, examples, schema)` returns the system prompt, and the user message is the chunk `text` only. It has no persona and no metadata (Principles I and VII). Hash the rendered prompt into the run manifest.
- [ ] T046 [P] [US2] **(ops)** Choose the GPT mini-tier slug and price from the OpenRouter model list and record them in `configs/models.yaml` and `configs/budget.yaml` (research.md R1 and R8). ~~Set the hard spending limit on the OpenRouter key to €12~~ The key limit is USD 20 (≈ €18.40, no reset) since 2026-09-29 and recorded in `configs/budget.yaml`; only the GPT slug and price remain open.
- [X] T047 [P] [US2] Implement `src/jtbd_pilot/labeling/claude_cli.py`:
  - runs `claude -p --output-format json --json-schema <schema> --system-prompt-file <prompt> --tools "" --model <id> --setting-sources "" --strict-mcp-config --disable-slash-commands --no-session-persistence` in an empty temp directory (no `--bare`: it ignores the subscription login), with the chunk sent on stdin
  - parses `structured_output` (falling back to `result`)
  - records the model ID from the JSON output (the `modelUsage` or usage block). If the output contains no model ID, it passes a **full, dated** model ID to `--model` and records that as `model_version`, adding a note to `deviations` (FR-018, Principle IX)
  - records `session_id` and `total_cost_usd` as information only (the cash cost is €0)
  - sets `temperature: not_settable` and adds the deviation to the manifest `deviations`
  - paces calls at 1–2 seconds
  - retries at most 2 times on a schema failure
- [X] T048 [P] [US2] Implement `src/jtbd_pilot/labeling/openrouter.py`:
  - `openai` client with `base_url` pointing to OpenRouter
  - `response_format` json_schema strict, `temperature: 0`, reasoning effort low
  - `provider: {order: [openai], allow_fallbacks: false, require_parameters: true, data_collection: "deny"}`
  - records the generation ID, the response model and the token usage (including cached tokens)
  - writes the actual cost to the ledger
- [X] T049 [P] [US2] Implement `src/jtbd_pilot/labeling/mock.py`, a backend that replays fixture responses for tests and dry runs.
- [X] T050 [US2] Implement `src/jtbd_pilot/labeling/runner.py` and the `pilot label` command:
  - preconditions: `verify_frozen()`, budget `guard()`, the role and family rules from data-model.md LabelRun, and the holdout lock
  - writes `data/runs/<run_id>/manifest.json` (label-run-manifest contract), `raw/<chunk_id>.json` (never overwritten) and `parsed/<chunk_id>.json`
  - records failed chunks in `excluded_chunks` with a reason after the retries are used up
  - **model-version guard**: compares the model version reported by the backend on every call with the first call of the run. On a change, it stops with exit 6 and marks the run as `invalid_version_change`, so it must be repeated (spec Edge Cases)
  - resumable
- [X] T051 [P] [US2] Implement `src/jtbd_pilot/quotes.py`: `locate(quote, text) -> span | None`, with only the normalization defined in the spec Edge Cases (whitespace, line breaks, typographic quote characters).
- [X] T052 [P] [US2] Implement `src/jtbd_pilot/checks.py` and `pilot check --run`:
  - checks `quote_verbatim`, `schema_valid`, `consistency.irrelevant_no_items`, `consistency.enum_values` and `consistency.quantified_has_quantity`
  - writes `data/analysis/checks/<run_id>.jsonl` and pass rates per model and per check (FR-026)
- [X] T053 [US2] Implement `src/jtbd_pilot/matching.py` and `pilot match --runs <a> <b>`: IoU on the located spans, a kind bonus used only as a tie-break, `min_iou` from config, and `scipy.optimize.linear_sum_assignment`. It writes ItemMatch records to `data/analysis/matches/<a>__<b>.jsonl`, including unmatched items.
- [X] T054 [US2] Implement `src/jtbd_pilot/consensus.py` and `pilot consensus --reference <a> <b>`. It writes `data/analysis/consensus.jsonl` and `contested.jsonl` with contested `dimensions` per entry, and keeps contested entries rather than dropping them (FR-021, FR-022, Principle III).
- [X] T055 [US2] Implement `src/jtbd_pilot/metrics.py` and `pilot agreement --reference <a> <b>`:
  - per dimension: relevance kappa, item F1, kind, actor-type and scope kappa, and evidence-type quadratic kappa (linear also reported)
  - n, bootstrap CI and the underpowered flag for each
  - breakdowns by language, source type and EU versus non-EU (FR-024)
  - **counts per evidence level** in the consensus. When observation or measurement together have fewer than 30 items, those levels are marked `underpowered` and the report says so (FR-008)
  - writes `data/analysis/agreement.json`
- [X] T056 [US2] Implement `pilot freeze` (criteria stage) in `src/jtbd_pilot/cli.py`, using `freeze.py`:
  - hashes the guideline and examples, the schema, `decision-criteria.yaml`, `budget.yaml` and the main chunk IDs and texts
  - sets the state to `criteria_frozen`
  - refuses to change the hashes without `--new-version` and `--rationale`
  - `pilot freeze --benchmark` (benchmark stage): adds the consensus and contested hashes plus the reference run IDs to the manifest and sets `state: frozen` (FR-034). `pilot freeze --benchmark` accepts mock runs **only** when the config sets `test_fixture: true`. The resulting benchmark is marked `test_only` and can never serve as a real benchmark version. In any other config, mock runs are refused.
- [ ] T057 [US2] **(ops)** Run `pilot freeze`. Commit `benchmarks/pilot-v1/manifest.json` **before** any labeling (SC-008, Principle IV).
- [ ] T058 [US2] **(ops)** Run a smoke test on 5 chunks: `pilot label --role reference --backend claude_cli --limit 5` and `--backend openrouter --limit 5`, then `pilot budget`. Check that the manifests contain the model version and the deviations, and that the spend is only cents. **Explicitly check** that the Claude manifest contains a real model version (see T047). If it does not, fix this before T059.
- [ ] T059 [US2] **(ops)** Label the full main split with both reference models, using `pilot label --role reference ...` (Claude through the subscription, spread over sessions if the usage limit is hit). At most 2% of chunks may be excluded per model (SC-002). Then run `pilot check` for both runs, followed by `pilot match` and `pilot consensus`, then **`pilot freeze --benchmark`**, and only then `pilot agreement`. This satisfies the constitution gate "before reporting a result" even at the MVP stop. If a redaction issue shows up during this step, follow the re-redaction procedure in T034 before `pilot freeze --benchmark`.

**Checkpoint**: agreement per dimension exists for the frozen pilot-v1 criteria. The riskiest assumption is measured, and US2 is complete.

---

## Phase 5: User Story 3 - Understand disagreements and propose guideline revisions (Priority: P2)

**Goal**: every contested entry has one primary disagreement category, and each guideline revision proposal references categories and examples.

**Independent Test**: `pilot categorize --check` reports 0 uncategorized contested entries (SC-004). `data/analysis/revisions.md` lists each revision with its guideline section, category and expected effect.

- [X] T060 [P] [US3] Write `tests/unit/test_categorize.py`:
  - a contested entry without a category makes `--check` exit 1
  - an unknown category key is rejected
  - the counts per category and the examples are aggregated correctly
- [X] T061 [US3] Implement `src/jtbd_pilot/categorize.py` and `pilot categorize`:
  - file-based workflow: exports `data/analysis/contested-review.csv` with the chunk excerpt, both reference values and the affected dimensions; imports the filled-in `category` and `note`
  - the category list lives in `data/analysis/categories.yaml` and is seeded with `evidence_boundary_anecdote_routine`, `evidence_boundary_observation_measurement`, `pain_vs_negated_gain`, `item_split_merge`, `actor_type_boundary`, `relevance_near_miss`, `quote_span_choice` and `reference_b_clearly_wrong` (research.md R1 mitigation)
  - `--check` mode
- [X] T062 [US3] Implement a free-text sample in `src/jtbd_pilot/categorize.py` (FR-025): export a stratified sample of 30 matched pairs, showing `actor` and `statement` for both references, to `data/analysis/freetext-sample.csv` for review.
- [ ] T063 [US3] **(ops)** Categorize every contested entry and review the free-text sample, recording the results in `data/analysis/contested-review.csv` and `freetext-sample.csv`.
- [ ] T064 [US3] **(ops/doc)** Write `data/analysis/revisions.md`: one proposed guideline revision per frequent category, each with the guideline section, the category or categories addressed, example chunk IDs and the expected effect on agreement.

**Checkpoint**: disagreements are explained and revisions are ready for a possible Revise outcome.

---

## Phase 6: User Story 4 - Measure zero-shot small-model baselines and teacher candidates (Priority: P2)

**Goal**: five teacher candidates (local qwen3.8:27b; mimo-v2.6-pro, deepseek-v4.1-flash and glm-5.3-flash through OpenRouter; their offline ensemble, FR-019a/b) and 2–3 small models (≤ 4B), each scored against the frozen consensus (teachers also after quote repair, FR-026a), with performance measured for the small models on the 8 GB reference VM.

**Independent Test**:
- `pilot score` produces a ModelScore for each run, with every dimension, the neutral contested counts and the check pass rates; teacher runs also carry the `repaired` view and `repair_stats`.
- `pilot ensemble` builds the derived ensemble run from the four frozen members, and `pilot score` scores it like any teacher run.
- `pilot perf` produces PerfMeasurement records whose digests match the Spark quality runs (SC-005, SC-005a).

### Tests for User Story 4

- [X] T065 [P] [US4] Write `tests/unit/test_scoring.py`:
  - an evaluated item that matches a reference item contested on existence counts as neither hit nor false positive, and increments `neutral_contested_hits`
  - the same applies per attribute dimension
  - an empty output on a chunk that is empty in the consensus counts as correct
  - a schema failure counts against the model and is not repaired
  - `composite` is the unweighted mean of the dimension scores
- [X] T066 [P] [US4] Write `tests/unit/test_perf.py`:
  - p50 and p95 computed from latency lists
  - peak RSS taken from sampled `/proc/<pid>/status` VmRSS values (with a fixture)
  - refusal when the model digest differs from the quality-run digest
- [ ] T086 [P] [US4] Write `tests/unit/test_ensemble.py` (FR-019b, research.md R10), using hand-built `ChunkOutput`s for three members on one chunk:
  - an item found by 2 of 3 members is kept, an item found by 1 is dropped (`min_votes: 2`)
  - at most one item per member and group: two overlapping items of the same member go to different groups
  - relevance majority, and a 1:1 relevance tie counts as relevant
  - an attribute tie is broken by the `tie_break` order of that dimension, and quote, actor and statement come from the first member in `quote_priority`
  - a near-miss quote is repaired to the source passage (whitespace collapsed) before grouping; an unrepairable one is dropped
  - the ensemble run manifest has `backend: ensemble`, `role: teacher_candidate`, `derived_from` = the member run IDs, `cost_eur` = sum of the members, and no `raw/` directory
  - `pilot ensemble` exits 1 when a member run is missing or not `complete`, and exits 3 when the frozen criteria hash does not match
- [ ] T087 [P] [US4] Extend `tests/unit/test_scoring.py` (FR-026a):
  - a teacher run with one near-miss quote gets a higher repaired item F1 than its raw item F1, and `repair_stats` = {invalid_quotes: 1, repaired: 1, dropped: 0}
  - `check_pass_rates.quote_verbatim` is identical with and without repair
  - a `baseline` run has no `repaired` block
  - `cost_per_chunk_eur` = run `cost_eur` / processed chunks (0 for Ollama)
- [ ] T088 [P] [US4] Extend `tests/unit/test_quote_repair.py`: `repair()` honours the `min_score`, `min_length_ratio` and `max_length_ratio` parameters (a passage at length ratio 0.79 is refused with defaults 0.8–1.25, accepted with 0.75), and the defaults are unchanged.

### Implementation for User Story 4

- [X] T067 [P] [US4] Implement `src/jtbd_pilot/labeling/ollama.py`:
  - `POST /api/chat` with `format: <json schema>`, `options.temperature: 0` and a fixed `num_ctx`
  - takes the host from `OLLAMA_HOST` or `OLLAMA_HOST_VM`
  - records the model digest (`/api/show`) and quantization in the manifest
  - cost €0
- [X] T068 [US4] Add a precondition to `pilot score` in `src/jtbd_pilot/cli.py`: it refuses unless the manifest `state` is `frozen` (set in T059 through `pilot freeze --benchmark`, FR-034), and it records the benchmark version in each ModelScore.
- [X] T069 [US4] Implement `src/jtbd_pilot/scoring.py` and `pilot score --run <id>`:
  - matches the run against the consensus with the same `matching.py`
  - per-dimension scores with n and CI, using **the same metric per dimension as agreement** (kappa for relevance, kind, actor type and scope; quadratic-weighted kappa for evidence type; F1 for item existence), computed between the model and the consensus on consensus units
  - neutral scoring of contested entries (FR-028)
  - `composite`
  - also computes the frontier-versus-frontier composite **restricted to consensus units** and **on all units**, for the two FR-031 ratios
  - check pass rates from `checks.py`
  - writes `data/analysis/scores/<run_id>.json`
- [X] T070 [US4] Implement `src/jtbd_pilot/perf.py` and `pilot perf`:
  - `--model --host vm --warmup 3`: a sequential run over the main split, recording chunks/min, output tok/s, p50 and p95 latency, and peak RSS of the Ollama runner process from `/proc`, sampled every 100 ms, together with the hardware description (VM type, vCPU, RAM, CPU model); refuses on a digest mismatch
  - `--frontier --run <gpt-run> --sample 20`: GPT at concurrency 1, which gives the reference throughput for FR-031
  - writes `data/analysis/perf/<run_id>.json`
- [ ] T089 [US4] Extend `src/jtbd_pilot/schema.py`:
  - `DecisionCriteria` gets three required blocks mirroring `contracts/decision-criteria.schema.json`: `TeacherFitness {min_quality_ratio, min_schema_valid (0–1), tie_margin (≥ 0), score_view: Literal["repaired"]}`, `QuoteRepair {min_score (0–100), min_length_ratio > 0, max_length_ratio > 0}`, `TeacherEnsemble {model_id, members (unique, ≥ 1), min_votes ≥ 1, tie_break {kind, actor_type, evidence_type, evidence_scope}: member lists, quote_priority}`; a validator requires every `tie_break` list and `quote_priority` to be a permutation of `members`
  - `LabelRunManifest.backend` accepts `ensemble`; new optional `derived_from: list[str]` (≥ 2), required when `backend == "ensemble"`, and then `role` must be `teacher_candidate`
  - copy the new blocks from `contracts/decision-criteria.example.yaml` into `configs/decision-criteria.yaml` (same `version: criteria-v1`, updated `rationale`; allowed because the criteria are not frozen yet, T057), and add matching blocks for mock teachers to `tests/fixtures/mini-corpus/decision-criteria.yaml`; fix `tests/unit/test_decision.py`'s inline criteria
  - add a test to `tests/unit/test_schema.py` that `configs/decision-criteria.yaml` and the example validate against the contract
- [ ] T090 [P] [US4] Parametrize `repair()` in `src/jtbd_pilot/quotes.py` with `min_score`, `min_length_ratio` and `max_length_ratio` (defaults 90, 0.8, 1.25, unchanged behaviour) so T091 and T092 pass the frozen `criteria.quote_repair` values.
- [ ] T091 [US4] Create `src/jtbd_pilot/ensemble.py` and `pilot ensemble [--split main]` in `src/jtbd_pilot/cli.py`:
  - move `with_repair`, `vote` and `combine` from `spike/ensemble.py`; replace its hard-coded `MODELS`, `DIM_PRIORITY` and `QUOTE_PRIORITY` with `criteria.teacher_ensemble` (member model IDs → their complete run on the split), `min_iou` from the pilot config, repair parameters from `criteria.quote_repair`
  - preconditions: `verify_frozen()` (exit 3); every member has exactly one `complete` run on the split with the frozen hashes (exit 1, naming the member)
  - writes `data/runs/run-teacher_candidate-<teacher_ensemble.model_id>-<split>-<guideline hash[:8]>/manifest.json` (`backend: ensemble`, `role: teacher_candidate`, `family: ensemble`, `model_version` = the members' versions joined, `derived_from`, `cost_eur` = sum of the members, `license_basis` = the members' bases joined, `settings` with `min_votes` and `min_iou`, `status: complete`) and `parsed/<chunk_id>.json`; no `raw/`
  - `pilot check` must accept a run without `raw/` (schema validity is taken from `parsed/`)
  - `spike/ensemble.py` imports `combine` and `with_repair` from the package and keeps its own fixed strategy list; its output in `data/spike/ensemble.json` must stay the same (cheap4 ≥ 2 votes: 0.817)
  - add `teacher-ensemble` (role `teacher_candidate`, backend `ensemble`, family `ensemble`) to `configs/models.yaml` so role checks and the report can resolve it
- [ ] T092 [US4] Extend `score_run` in `src/jtbd_pilot/scoring.py` (FR-026a): for `role == "teacher_candidate"`, rebuild each output's valid items with `ensemble.with_repair` and the frozen `criteria.quote_repair`, run `score_units` again and add `repaired` = {`dimensions`, `composite`, `quality_ratio_a`, `quality_ratio_b`, `repair_stats`}; keep `check_pass_rates` raw; add `cost_per_chunk_eur` for every run. Baselines get no `repaired` block.
- [ ] T071 [US4] **(ops)** Confirm the license basis of the four teacher candidates in `configs/models.yaml` against the model cards (qwen3.8:27b Apache-2.0; MiMo-V2.6-Pro-RL, DeepSeek-V4.1-Flash, GLM-5.3-Flash MIT) and that their families (`qwen`, `xiaomi`, `deepseek`, `glm`) differ from both reference families. Record the check date in each `license_basis`.
- [ ] T072 [US4] **(ops)** Smoke-test the four teachers on 5 main chunks (quickstart.md section 5): `pilot label --role teacher_candidate --backend ollama --model teacher-qwen3.8 --host spark --limit 5`, and `--backend openrouter` for `teacher-or-mimo-v2.6-pro` (`--workers 2`, 429 limits), `teacher-or-deepseek-v4.1-flash` and `teacher-or-glm-5.3-flash` (`--workers 4`). Check the manifests for `data_collection: deny`, quantizations, reasoning setting and the "no fixed provider order" deviation, then `pilot budget`.
- [ ] T073 [US4] **(ops)** After T059 (benchmark frozen): label the main split with the four teachers (same commands without `--limit`; `--retry-failed` after network or rate-limit failures) and with the three baselines (`qwen3.5:4b`, `gemma4:e4b`, `ministral-3:3b`) on the Spark. Then `pilot ensemble`, and `pilot check` and `pilot score` for every run including the ensemble. At most 2% excluded chunks per teacher (SC-002 applied to teachers).
- [ ] T074 [US4] **(ops)** Provision the reference VM (Hetzner CX32 class: 8 GB RAM, 4 vCPU, no GPU). Install Ollama, pull the baselines with the **same digests**, and run `pilot perf` for each baseline, plus `pilot perf --frontier` for GPT. Record the VM cost in the ledger with `pilot budget`, then **delete the VM**. If `gemma4:e4b` does not fit, switch to `gemma4:e2b` and document the switch.

**Checkpoint**: baseline and teacher-candidate quality, and baseline performance, are measured against the frozen pilot-v1.

---

## Phase 7: User Story 5 - Deliver the pilot report and decision (Priority: P2)

**Goal**: a mechanically derived go / revise / rethink decision and a single report containing every item listed in FR-032.

**Independent Test**: `pilot decide` on the mini corpus follows the expected path through the decision table. The generated `reports/pilot-v1/report.md` contains every FR-032 section and uses agreement wording only (FR-033). A reader can reproduce the decision from the numbers in the report (SC-006, SC-007).

### Tests for User Story 5

- [X] T075 [P] [US5] Write `tests/unit/test_decision.py`, with table-driven cases for FR-030 and FR-031:
  - all thresholds met gives go
  - evidence type in [0.4, 0.6) gives revise
  - evidence type < 0.4 gives rethink, which takes precedence over revise
  - relevance < 0.8 gives revise
  - item F1 < 0.7 gives revise
  - after one rerun, a dimension that still fails on the holdout gives rethink
  - a second rerun is refused (`max_reruns: 1`)
  - fine-tuning is optional only when quality ratio ≥ 0.85 against the frontier-vs-frontier composite on consensus units (ratio a) **and** throughput ratio ≥ 10 against the frontier reference chunks/min
  - ratio b (all units) is computed and reported but does not change the classification
- [ ] T093 [P] [US5] Extend `tests/unit/test_decision.py` with table-driven cases for FR-031a `teacher_fitness()`:
  - repaired ratio a 0.90 and schema_valid 0.98 is fit; 0.899 or 0.979 is not fit, with the failing reason listed
  - the raw ratio is ignored (a candidate with raw 0.85 and repaired 0.92 is fit)
  - two fit candidates 0.015 apart: the one with the lower `cost_per_chunk_eur` is recommended; 0.03 apart: the higher composite is recommended
  - no fit candidate: `recommended` is null
  - baselines are never classified
- [X] T076 [P] [US5] Write `tests/integration/test_mini_corpus_report.py`: the full mock chain through `pilot report`. The report must contain these sections: corpus composition, agreement with CI and breakdowns, check results, contested summary, disagreement categories, revisions, baseline and teacher scores, the Pareto figure, the decision path, and the versions. It must contain no "accuracy" wording.

### Implementation for User Story 5

- [X] T077 [US5] Implement `src/jtbd_pilot/decision.py` and `pilot decide`:
  - reads the frozen `decision-criteria.yaml`, `agreement.json`, the scores and the perf results
  - writes `data/analysis/decision.json` (PilotDecision) with a per-dimension decision, the `path` of the rows that fired, the fine-tuning classification with ratios a and b (FR-031), `rerun`, and `deviations`, including the GPT mini-tier throughput reference
  - implements the pilot state machine `collecting → criteria_frozen → labeled → evaluated → decided`, with at most one `revise → rerun_holdout → decided`, stored in the manifest
- [X] T078 [US5] Implement the holdout rerun path in `src/jtbd_pilot/labeling/runner.py` and `src/jtbd_pilot/cli.py`:
  - state `revise` unlocks the holdout
  - requires a new guideline version (`guideline-v2`) and a new benchmark version (`pilot-v2`) through `pilot freeze --new-version pilot-v2 --rationale`
  - the decision uses agreement on the holdout, and agreement on the main split is reported next to it and marked optimistic
  - an optional GPT-5.5 control run on the holdout (about €2.50, research.md R1) only when it is decided before the rerun and the budget guard passes
- [X] T079 [P] [US5] **Load the `dataviz` skill first.** Then implement `src/jtbd_pilot/report/pareto.py`: a quality-vs-throughput chart with each small model as a point (composite quality against chunks/min on the reference VM), a reference line at 85% of the frontier-vs-frontier composite, and a label with the benchmark version. It writes `reports/pilot-v1/figures/pareto.png`.
- [ ] T094 [US5] Add `teacher_fitness(criteria, scores)` to `src/jtbd_pilot/decision.py` and store its result as `teacher_fitness` in `data/analysis/decision.json` (data-model.md PilotDecision): rule text, one row per teacher candidate (`model_id`, repaired `quality_ratio_a`, `schema_valid` rate, `cost_per_chunk_eur`, `fit`, `reasons`) and `recommended`.
- [ ] T095 [US5] Update section 9 of `src/jtbd_pilot/report/render.py`: remove `TEACHER_FITNESS` and `_teacher_fit`; show for each teacher raw and repaired composite, repaired ratio a, schema_valid, quote_verbatim, repair stats, cost per chunk and fit / not fit from `decision.json`, then the recommended teacher and the FR-031a rule; state that the ensemble is derived from its members. Extend the mini-corpus fixture with two mock teacher models (families different from `mock-a`/`mock-b`, license basis set) and their responses under `tests/fixtures/mini-corpus/mock/`, one with a near-miss quote, and extend `tests/integration/test_mini_corpus_report.py` to run `label` for both teachers, `ensemble`, `score` and check the teacher table and the recommendation.
- [X] T080 [US5] Implement `src/jtbd_pilot/report/render.py`, the `report/template.md` and `pilot report`. The report contains all FR-032 content:
  - composition (from `data/analysis/composition-*.json`)
  - agreement per dimension with CI and breakdowns
  - deterministic checks
  - contested summary
  - disagreement categories
  - revisions (from `data/analysis/revisions.md`)
  - baseline and teacher scores, including a fitness statement for each teacher *(replaced by the FR-031a classification in T095)*
  - the Pareto figure
  - the decision path
  - the benchmark and guideline versions
  - these deviations: the GPT mini tier (FR-017) and its effect on the 10x throughput hurdle (FR-031), Claude temperature not settable, and any source substitution
  - both FR-031 quality ratios (a and b)
  - the budget used, taken from the ledger (SC-009)

  It uses agreement wording only and never "accuracy" (FR-033).
- [ ] T081 [US5] **(ops)** Run `pilot decide` and `pilot report` on pilot-v1. If the decision is `revise`, run T078: apply `data/analysis/revisions.md` to create `guideline/guideline-v2.md`, freeze pilot-v2, relabel the main and holdout splits with both references, then decide and report again. Finalize `reports/pilot-v1/report.md` (and `reports/pilot-v2/report.md` if there was a rerun).

**Checkpoint**: the pilot report with a go / revise / rethink decision is delivered.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T082 [P] Document the data retention and deletion procedure in `README.md` (section "Data handling"):
  - `data/` is never committed
  - each snapshot's `retention_until`
  - the deletion or restriction of Reddit snapshots at the end of the research (§ 60d)
  - no dataset is published (Principle VI)
- [X] T083 [P] Add `pilot doctor` in `src/jtbd_pilot/cli.py`. It checks that `claude` is on PATH and logged in, that the OpenRouter key and cap are configured, that both Ollama hosts are reachable, and that the manifest state matches the files on disk.
- [ ] T084 Run every step of `specs/001-jtbd-extraction-pilot/quickstart.md`, sections 1 to 6, including every guardrail row in section 3. Record the results in `data/analysis/quickstart-validation.md`.
- [ ] T085 Run a final traceability check: each FR and SC in spec.md maps to at least one task, artifact or report section, and `pilot budget` shows a total of €20 or less (SC-009).

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: depends on Setup and blocks every story.
- **US1 (Phase 3)**: depends on Foundational. The ops tasks T031–T035 take calendar time (T030, the Reddit access request, was dropped).
- **US2 (Phase 4)**: the code (T036–T056) can be built in parallel with US1 on the mini corpus. Labeling the real corpus (T057–T059) needs US1 to be complete.
- **US3 (Phase 5)**: needs the contested set from T059.
- **US4 (Phase 6)**: the code (T065–T070) can be built in parallel with US2 and US3. Scoring the real runs (T073) needs the consensus from T059 and `pilot freeze --benchmark`. Performance (T074) needs T073 for the digests.
- **US5 (Phase 7)**: the code (T075–T080) can be built in parallel. T081 needs US2, US3 and US4 to be complete.
- **Polish (Phase 8)**: after the stories are complete.

### Key task dependencies

- T006 → T005 turning green, and T006 comes before every model or IO task.
- T014 → T056 → T057 → T058 and T059 (nothing may be labeled before the freeze).
- T016 → T048 and T050 (budget guard).
- T051 → T052 and T053 → T054 → T055 → T059.
- T053 → T069 (scoring reuses matching).
- T086–T088 → T089 → T090 → T091 → T092 → T073 (ensemble and repaired scoring before the teacher runs are scored).
- T093 → T094 → T095 → T081 (teacher fitness before the report).
- T059 → T061 → T063 → T064 → T080.
- T056 (`freeze --benchmark`) → T059 → T068 → T073 → T074 → T077 → T081.

### Parallel opportunities

- Phase 2: T007–T013, T015 and T019 touch different files.
- US1: T020 and T021 (tests), then T022–T024 and T026–T029 (separate modules).
- US2: T036–T042 (tests), then T047, T048, T049, T051 and T052 (separate backends and modules). T044 in parallel with T045.
- US4: T065–T067 and T086–T088 in parallel; T090 in parallel with T089. The ops runs in T073 can run one after another on the Spark while US3 categorization (T063) runs at the same time.
- US5: T075, T076, T079 and T093 in parallel.

## Parallel Example: User Story 2

```bash
# Tests first, in parallel:
Task: "Quote locator tests in tests/unit/test_quotes.py"
Task: "Deterministic check tests in tests/unit/test_checks.py"
Task: "Matching tests in tests/unit/test_matching.py"
Task: "Consensus tests in tests/unit/test_consensus.py"
Task: "Metrics tests in tests/unit/test_metrics.py"

# Then independent modules, in parallel:
Task: "Claude CLI backend in src/jtbd_pilot/labeling/claude_cli.py"
Task: "OpenRouter backend in src/jtbd_pilot/labeling/openrouter.py"
Task: "Quote locator in src/jtbd_pilot/quotes.py"
Task: "Deterministic checks in src/jtbd_pilot/checks.py"
```

## Parallel Example: User Story 4

```bash
Task: "Scoring tests in tests/unit/test_scoring.py"
Task: "Perf tests in tests/unit/test_perf.py"
Task: "Ollama backend in src/jtbd_pilot/labeling/ollama.py"
```

---

## Implementation Strategy

### MVP first (US1 + US2: the riskiest assumption)

1. Phase 1 and Phase 2.
2. (T030, the Reddit access request, was dropped on 2026-09-29.)
3. Build the US2 code against the mini corpus while US1 ops (T031–T035) collect the corpus.
4. Freeze (T057), then label with both references (T059).
5. **Stop and review the agreement.** This already answers the pilot's core question.

### Incremental delivery

1. MVP: agreement per dimension on pilot-v1.
2. US3: disagreement categories and revisions.
3. US4: teacher candidates (four single models and their ensemble) and baselines, with performance on the VM.
4. US5: decision and report, plus at most one holdout rerun.

### Budget checkpoints

- After T058 (smoke test): the ledger should show only cents.
- After T059: GPT spend of a few euros.
- After T072: the teacher smoke tests cost cents. After T073: the three OpenRouter teachers add about €2.
- After T074: add the VM at about €1.
- Before T078 (rerun): run `pilot budget --estimate` for the rerun and the optional GPT-5.5 control.
- The total must stay at or below €20, and OpenRouter at or below the key cap (€18.40).

---

## Notes

- [P] tasks touch different files and have no dependency on an unfinished task.
- **(ops)** tasks are manual or long-running steps. Each produces the named file and is checked by the phase's Independent Test.
- Never edit files in `data/runs/*/raw/`. Never re-fetch a snapshotted source without `--update --reason`.
- Commit after each task or logical group. `data/` is never committed.
