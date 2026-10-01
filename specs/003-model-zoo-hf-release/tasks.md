---
description: "Tasks for feature 003: mobility model zoo with versioned Hugging Face releases"
---

# Tasks: Mobility model zoo with versioned Hugging Face releases

**Input**: Design documents from `specs/003-model-zoo-hf-release/`: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Included. The plan lists the test files, and SC-005 requires an automated test that blocks every missing required field.

**Organization**: Tasks are grouped by user story. Paths follow the plan's structure: `src/mobility_model_zoo/`, `tests/`, `zoo/`, `.github/workflows/`. **(ops)** marks a manual step for the owner (accounts, tokens, real Hub runs).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1–US4 from spec.md

---

## Phase 1: Setup

**Purpose**: Governance and license before any code changes.

- [ ] T001 Amend `.specify/memory/constitution.md` to 1.3.0 (research R13): preamble and "Project Scope" describe the multi-topic zoo `mobility-model-zoo`; Principles I, II, VII and X apply to the `productdev` JTBD models; III, IV, V, VI, VIII, IX, Resources, Technical Spikes and Gates apply zoo-wide, with JTBD-specific wording made task-neutral; Principle IX adds "published versions are immutable", "publication only through the release pipeline with owner approval" and "datasets are never published"; a new section states the task/release split (one build-and-measure tool per task, shared by all its models; one common release record and gate for every model; shared code is extracted only when a second task needs it). Update the Sync Impact Report, version 1.3.0, Last Amended 2026-10-01.
- [ ] T002 [P] Add the Apache-2.0 license text as `LICENSE` at the repository root (FR-003b).

---

## Phase 2: Foundational (rename and release scaffolding)

**Purpose**: The rename touches every import and command, and the registry and Hub layer are used by every story. **No story work starts before this phase is complete.**

### Branches

- [ ] T003 **(ops)** Set up branches (plan step 0): on `001-jtbd-extraction-pilot`, commit the open work (`README.md`, `spike/*.py`, `spike/*.sh`, `specs/003-model-zoo-hf-release/`) after checking that no file under `data/` or `.env` is staged; push; fast-forward `main` with `git push origin 001-jtbd-extraction-pilot:main` (`main` is 9 commits behind and has not diverged); create `003-model-zoo-hf-release` from `main` and push it. All 003 work happens on that branch. The open 001 ops tasks continue on `main` after the 003 merge (T038).

### Rename (one commit, full test suite green)

- [ ] T004 Write `tests/unit/test_rename_hashes.py`: compute `compute_hashes()` from `freeze.py` against the current `configs/pilot-v1.yaml` and store the expected values as a fixture in `tests/fixtures/rename-hashes.json`. After T006 the test loads the moved config and asserts identical hashes (freeze hashes are content-based, plan step 2).
- [ ] T005 Move the code: `git mv src/jtbd_pilot src/mobility_model_zoo/productdev/jtbd`. Add `src/mobility_model_zoo/__init__.py` and `src/mobility_model_zoo/productdev/__init__.py`. Rewrite every `jtbd_pilot` import in `src/`, `tests/` and `spike/*.py` to `mobility_model_zoo.productdev.jtbd`.
- [ ] T006 Move the configs: `git mv configs/*` to `configs/productdev/jtbd/` (keep the `domain/` subfolder). Update `DEFAULT_CONFIG` in `src/mobility_model_zoo/productdev/jtbd/config.py` to `configs/productdev/jtbd/pilot-v1.yaml`, and update every path inside the moved configs and in `tests/fixtures/`. Keep `benchmark_version: pilot-v1` unchanged (it is a version name, not a tool name).
- [ ] T007 Rename the CLI `pilot` to `jtbd` without an alias: typer app help text "JTBD task tool" in `src/mobility_model_zoo/productdev/jtbd/cli.py`, and every user-facing string that names the `pilot` command in `src/mobility_model_zoo/productdev/jtbd/` (error messages, report templates, docstrings).
- [ ] T008 Rewrite `pyproject.toml`: `name = "mobility-model-zoo"`, version `0.1.0`, description "A collection of mobility ML models, grouped by topic"; base dependencies inference-only (`torch`, `transformers`, `huggingface_hub>=1.19`, `safetensors`, `sentencepiece`); extra `jtbd` with the current pilot dependencies; extra `release` with `jsonschema`, `pyyaml`, `jinja2`, `typer`, `httpx`; scripts `jtbd = "mobility_model_zoo.productdev.jtbd.cli:app"` and `zoo = "mobility_model_zoo.release.cli:app"`; wheel packages `["src/mobility_model_zoo"]`. Run `uv lock`.
- [ ] T009 Run `uv sync --all-extras`, `uv run ruff check` and `uv run pytest`. Every existing test and T004 pass. Commit T004–T009 as one commit "Rename to mobility-model-zoo; pilot becomes jtbd".
- [ ] T010 [P] Rewrite every `pilot ...` command in `README.md` (for example `uv run pilot --help`, `pilot source fetch`, `pilot corpus redact`) and in the open tasks of `specs/001-jtbd-extraction-pilot/tasks.md` (001 tasks T032, T034, T035, T057, T058, T059, T072, T073, T081 and any other unchecked task) to `jtbd ...` and the new config paths. Add at the top of `specs/001-jtbd-extraction-pilot/{spec,plan,tasks,quickstart}.md`, `specs/001-jtbd-extraction-pilot/contracts/cli.md` and `specs/002-e2e-spike/{spec,plan,tasks}.md` one note: "Since feature 003 the CLI `pilot` is `jtbd`, the code is in `src/mobility_model_zoo/productdev/jtbd/` and the configs are in `configs/productdev/jtbd/`. Paths and commands below are historical."
- [ ] T011 [P] Write `tests/unit/test_no_pilot_commands.py`: fails if `README.md` or any unchecked task line in `specs/001-jtbd-extraction-pilot/tasks.md` contains the command `pilot ` (as `pilot source`, `pilot corpus`, `uv run pilot`, and so on). The benchmark name `pilot-v1` is allowed.
- [ ] T012 **(ops)** Rename the GitHub repository with `gh repo rename mobility-model-zoo` and update the local remote (`git remote set-url origin git@github.com:mhabedank/mobility-model-zoo.git`). GitHub keeps redirects from the old name.

### Hugging Face account

- [ ] T013 **(ops)** Create the Hugging Face organization `mobility-model-zoo` (free plan). Create two fine-grained tokens (contracts/workflows.md): `HF_RELEASE_TOKEN` with write access to the organization's repos and collections, stored as a GitHub repository secret; `HF_STAGING_TOKEN` with write access only to explicitly listed staging repos and no right to create repos (fine-grained tokens cannot use name patterns; each new `<model>-staging` repo is added by hand after `zoo init-model`), stored in the local `.env` only. Add `HF_STAGING_TOKEN=` to `.env.example`.

### Release scaffolding

- [ ] T014 Create the package `src/mobility_model_zoo/release/` with `__init__.py`, `errors.py` (exceptions mapped to exit codes per contracts/cli.md: 1 `GateFailed`, 2 usage, 3 `ImmutabilityRefused`, 4 `ApprovalRefused`, 5 `CredentialError`, 6 `HubError`) and `cli.py` (typer app `zoo` with empty subcommands `validate`, `init-model`, `stage`, `check`, `build`, `preview`, `publish`, `deprecate`, `index`, `audit`, `history-check`; one wrapper that maps exceptions to exit codes; human messages to stderr). Tokens are read only from the environment (`HF_RELEASE_TOKEN`, `HF_STAGING_TOKEN`) and are never printed.
- [ ] T015 [P] Copy `specs/003-model-zoo-hf-release/contracts/{topics,model,release-record,results}.schema.json` to `src/mobility_model_zoo/release/schemas/` and write `tests/release/test_schemas.py`: the copies equal the contract files byte for byte; a valid example of each file validates; the patterns from data-model.md are enforced, verbatim: topic `id` `^[a-z][a-z0-9]{1,15}$`; model `name` `^[a-z][a-z0-9]{1,15}-[a-z0-9]+(-[a-z0-9]+)+$`; `version` semantic `MAJOR.MINOR.PATCH`; `status` one of `experimental`, `released`, `deprecated`; `sha256` 64 hex characters; git commits 40 hex characters; `performance.budget.gpu` must be `false`; a non-Apache-2.0 `license` requires a non-null `license_exception`; a quality metric name containing "accuracy" is invalid.
- [ ] T016 Implement `src/mobility_model_zoo/release/registry.py`: load and schema-validate `zoo/topics.yaml`, every `zoo/models/<name>/model.yaml`, release records `zoo/models/<name>/releases/<version>.yaml` and results files; typed accessors (`topics()`, `model(name)`, `releases(name)` sorted by semantic version, `record(name, version)`, `results(name, version)`); a `write_record()` that preserves key order and comments-free YAML formatting.
- [ ] T017 Implement `src/mobility_model_zoo/release/hub.py`: the only module that calls `huggingface_hub.HfApi`. Functions: `repo_info`, `create_repo(private=...)` (never changes visibility of an existing repo), `list_tags`, `create_tag(exist_ok=False)`, `create_commit(operations)` as one commit, `create_branch`/overwrite for `rc-v<version>`, `download(repo, revision, path)`, `file_sha256_at(repo, revision, path)`, `add_to_collection`, `create_collection`, `validate_yaml(readme)` (POST `https://huggingface.co/api/validate-yaml` with `{"content": ..., "repoType": "model"}`). Map auth errors to `CredentialError` and network or 5xx errors to `HubError`.
- [ ] T018 [P] Create `tests/release/conftest.py` with a `FakeHub` that implements the `hub.py` interface in memory (repos with visibility, commits, tags, branches, files with content and sha256, collections, a configurable `validate_yaml` result and injectable failures), and a fixture that copies `tests/release/fixtures/registry/` into a temporary `zoo/`.
- [ ] T019 Create `zoo/topics.yaml` with two topics: `productdev` ("Product development", "Models that support product discovery in mobility, starting with jobs-to-be-done extraction.", `hf_collection: null`) and `sandbox` ("Pipeline tests", "Test models for the release pipeline. Never public.", `hf_collection: null`).

**Checkpoint**: The project is renamed, all tests pass, `uv run zoo --help` lists the commands, and the Hub layer is mockable.

---

## Phase 3: User Story 1 – First model published through the pipeline (Priority: P1) 🎯 MVP

**Goal**: A version tag starts checks, build and preview; a manual approval run publishes one atomic, tagged commit. Proven with the sandbox test model in a private repo.

**Independent Test**: quickstart.md scenarios 2–5: stage, tag, review the preview, publish `sandbox-pipeline-tiny` 0.1.0 to a private repo, download it by `revision='v0.1.0'`, and see every refusal case.

### Tests for User Story 1

- [ ] T020 [P] [US1] Create `tests/release/fixtures/registry/` with a complete, valid registry for `sandbox-pipeline-tiny` (model.yaml, `releases/0.1.0.yaml` with staged `files[]`, results files with `synthetic: true`, three example texts) and, generated by a helper in `tests/release/helpers.py`, one broken copy per gate rule.
- [ ] T021 [P] [US1] Write `tests/release/test_gate_rules.py`: for each of the gate rules 1–8, 11 and 14 (contracts/cli.md), the broken fixture fails exactly that rule with a message naming the field, and the valid fixture passes all of them.
- [ ] T022 [P] [US1] Write `tests/release/test_gate_required_fields.py` (SC-005): for every required field in `model.schema.json` and `release-record.schema.json`, delete it from the valid fixture, run `zoo check --offline` and assert exit 1, the field named in the output, and no call to any `FakeHub` write method.
- [ ] T023 [P] [US1] Write `tests/release/test_publish.py` against `FakeHub`: (a) publish creates the repo (private for sandbox), one commit with exactly `files[]` plus `README.md`, then tag `v0.1.0`; (b) a second publish of 0.1.0 exits 3 and changes nothing (SC-006); (c) wrong `--confirm` exits 4 before any write; (d) a missing `rc-v0.1.0` preview, a preview whose `build.json.tag_commit` differs from the tag commit, a card whose sha256 differs from `build.json.card_sha256`, or a model file that differs from `files[]` each exit 4 before any write; (d2) publish never calls the build or the model (no rebuild); (e) an injected failure after the commit and before the tag, followed by a rerun, creates only the tag and no second commit; (f) a missing token exits 5; (g) an existing public repo is never made private and an existing private repo is never made public.
- [ ] T024 [P] [US1] Write `tests/release/test_build.py`: `zoo build` twice on the same inputs produces byte-identical output directories and the same `build.json.card_sha256`; staged files with a wrong sha256 or size fail rule 5 and stop the build.

### Implementation for User Story 1

- [ ] T025 [P] [US1] Implement the sandbox test model in `src/mobility_model_zoo/sandbox/model.py`: `PipelineTestModel(nn.Module, PyTorchModelHubMixin)` with a tiny embedding plus linear layer (a few KB), fixed seed, and `predict(text: str) -> dict` returning `{"model": "sandbox-pipeline-tiny", "items": [{"kind": ..., "quote": <a sentence of the input>, "score": ...}]}` deterministically. Add `src/mobility_model_zoo/sandbox/build_test_model.py` (`python -m mobility_model_zoo.sandbox.build_test_model --out <dir>` writes `model.safetensors` and `config.json`) and `__init__.py`.
- [ ] T026 [P] [US1] Create the sandbox registry entry `zoo/models/sandbox-pipeline-tiny/`: `model.yaml` (topic `sandbox`, task `pipeline`, variant `tiny`, license `Apache-2.0`, `base_model: null`, languages `[de, en]`, `pipeline_tag: token-classification`, `library_name: pytorch`, repos `mobility-model-zoo/sandbox-pipeline-tiny` and `mobility-model-zoo/sandbox-pipeline-tiny-staging`, card texts that say it is a pipeline test model, `card.install` with `<tag>`, `card.how_to_run` that loads the model with `PipelineTestModel.from_pretrained("{repo_id}", revision="{revision}")` and prints `predict(...)`, using the placeholders `{repo_id}` and `{revision}` required by the schema); a complete `releases/0.1.0.yaml` (status `experimental`, `change_type: initial`, `sandbox: true`, `output_format_version: sandbox-v1`, `recipe.config: src/mobility_model_zoo/sandbox/build_test_model.py` with seed 0, `recipe.doc: docs/adding-a-model.md`, `provenance.sources: []`, `provenance.teachers: []`, `provenance.spike_data: false`, `evaluation.benchmark: synthetic`, `evaluation.reference: "none (synthetic test numbers)"`, `performance.hardware: "GitHub-hosted ubuntu-latest runner, CPU"`, `performance.budget: {ram_gb: 1, gpu: false}`; `files[]`, `staging.*` and `recipe.git_commit` are filled by `zoo stage` and before tagging); `results/0.1.0/quality.json` and `performance.json` with `synthetic: true`; three example texts in `examples/` without personal data.
- [ ] T027 [US1] Implement gate rules 1–8, 11 and 14 in `src/mobility_model_zoo/release/gate.py`, one function per rule returning `PASS`, `FAIL: <reason>` or `SKIP`, and `run_gate(model, version, offline)` that runs all rules and raises `GateFailed` listing every failure. Rule details from contracts/cli.md, including: rule 3 "status `experimental` exactly when version < 1.0.0" (FR-005a); rule 6 "`license` is Apache-2.0 or has `license_exception`; `base_model_license` is null only in the `sandbox` topic; every teacher has `training_on_outputs_permitted: true`"; rule 7 "`spike_data` MUST be `false` for any non-sandbox release; `synthetic: true` results only in the `sandbox` topic"; rule 8 checks `recipe.git_commit` with `git cat-file -e` and that `recipe.config` and `recipe.doc` exist at that commit; rule 11 allows only `files[]` and `README.md` in the upload and rejects any path under `data/`, `.env` or `*.jsonl`; rule 14 "`sandbox` is true exactly for the `sandbox` topic".
- [ ] T028 [US1] Implement `zoo validate [--all | <model>]` (offline rules only, no network) and `zoo check <model> <version> [--offline]` in `src/mobility_model_zoo/release/cli.py`, printing one line per rule.
- [ ] T029 [US1] Implement `zoo init-model <model>` in `src/mobility_model_zoo/release/publish.py`: uses `HF_RELEASE_TOKEN`; validates `model.yaml`; creates `<model>-staging` as a private repo, refuses if it exists and is public; prints a reminder to add the repo to `HF_STAGING_TOKEN`. Add a FakeHub test in `tests/release/test_publish.py`.
- [ ] T030 [US1] Implement `zoo stage <model> <version> --from <dir>` in `src/mobility_model_zoo/release/publish.py`: uses `HF_STAGING_TOKEN`; never creates repos (exit 2 "run `zoo init-model` first" if `<model>-staging` is missing, exit 1 if it is public); refuses files that rule 11 forbids; uploads every file in one commit; writes `files[]` (`path`, `sha256`, `size_bytes`) and `staging.revision` into the release record, creating the record from a template with the other fields empty if it does not exist; exit 3 if the record already has `published` set.
- [ ] T031 [US1] Implement the card renderer skeleton in `src/mobility_model_zoo/release/card.py` and `src/mobility_model_zoo/release/templates/model_card.md.j2`: front matter (license, language, library_name, pipeline_tag, base_model, tags including the topic, `mobility`, `mobility-model-zoo` and the status) and the 15 body sections from contracts/model-card.md with their headings and the data that US1 already has (title, status banner, summary, intended and out-of-scope use, input and output, how to run with the install line's `<tag>` replaced by `<model>/v<version>` and `how_to_run`'s `{repo_id}` and `{revision}` replaced by `repos.public` and `v<version>`, license, citation). Rendering is deterministic: sorted keys, LF line endings, no timestamps except the record's `date`.
- [ ] T032 [US1] Implement `zoo build <model> <version> --out <dir>` in `src/mobility_model_zoo/release/publish.py`: runs the gate, downloads `files[]` from `staging.repo` at `staging.revision`, verifies sha256 and size (rule 5), renders `README.md`, writes `build.json` (`card_sha256`, file list with sha256, `tag_commit`, staging revision).
- [ ] T033 [US1] Implement `zoo preview <model> <version> --build <dir>`: one commit of the build, including `build.json`, to the staging repo branch `rc-v<version>` (created or overwritten); prints the preview URL and `card_sha256`.
- [ ] T034 [US1] Implement `zoo publish <model> <version> --confirm <model>/v<version>` following steps 1–9 in contracts/cli.md. It publishes the reviewed preview and does **not** rebuild: confirm check (exit 4); download the head of staging branch `rc-v<version>` and check `build.json.tag_commit` equals the checked-out tag commit, the card's sha256 equals `build.json.card_sha256` and every model file matches `files[]` (exit 4); rerun gate rules 1–11 and 14 (exit 1); tag absent and version greater than every published one (exit 3); create the repo public for normal models and private for sandbox models; skip the commit if `main` already holds exactly the preview's card and model files; one commit with the card and model files (not `build.json`); `create_tag(exist_ok=False)`; write `published` (`repo_commit`, `tag`, `published_at`, `card_sha256`) into the release record.
- [ ] T035 [P] [US1] Write `.github/workflows/ci.yml`: on push and pull request, `actions/checkout` with `fetch-depth: 0`, `astral-sh/setup-uv`, `uv sync --all-extras` with the CPU-only torch index (no CUDA wheels), `uv run ruff check`, `uv run pytest`, `uv run zoo validate --all`. No secrets.
- [ ] T036 [P] [US1] Write `.github/workflows/release-verify.yml`: on push of tags matching `*/v*`, `actions/checkout` with `fetch-depth: 0` (gate rule 8 needs the full history), split the tag into model and version, `zoo check`, `zoo build --out build/`, `zoo preview`; write the gate table, the preview URL and `card_sha256` to `$GITHUB_STEP_SUMMARY`; upload `build/README.md` and `build/build.json` with `actions/upload-artifact`. Secret `HF_RELEASE_TOKEN`. Cache the CPU-only torch wheel.
- [ ] T037 [P] [US1] Write `.github/workflows/release-publish.yml`: `workflow_dispatch` with inputs `model`, `version`, `confirm`; `concurrency: release-${{ inputs.model }}`; check out the tag `<model>/v<version>` with `fetch-depth: 0`, `zoo publish --confirm` (no `zoo build`: it publishes the reviewed preview); then commit the updated release record (and, after US3, `zoo/MODELS.md`) to `main` with `GITHUB_TOKEN` (`contents: write`). Secret `HF_RELEASE_TOKEN`.
- [ ] T038 [US1] **(ops)** Open a pull request from `003-model-zoo-hf-release` to `main` with Phases 1–3 so far, wait for `ci.yml` to pass, and merge it. `workflow_dispatch` workflows can only be started from the default branch `main`, and release tags are created on `main` commits from now on.
- [ ] T039 [US1] **(ops)** Run quickstart.md scenarios 2–5 against the real Hub with `sandbox-pipeline-tiny` 0.1.0: stage, tag, review the preview, publish, download by `revision='v0.1.0'`, then each refusal row of scenario 5. Record the run links and the time from starting `release-publish` to the visible tag (SC-007, under 30 minutes) in `specs/003-model-zoo-hf-release/validation.md`.

**Checkpoint**: SC-001 (sandbox part), SC-005, SC-006 and SC-007 are met.

---

## Phase 4: User Story 2 – A visitor understands and trusts the model from its page (Priority: P1)

**Goal**: The card carries every required section with numbers that trace to results files, passes the Hub's validation without warnings, shows real example outputs, and has a usage example that runs on a clean machine.

**Independent Test**: The sandbox card from US1, rebuilt with US2, passes gate rules 9, 10, 12 and 13; a golden-file test pins its full content.

### Tests for User Story 2

- [ ] T040 [P] [US2] Write `tests/release/test_card_build.py`: a golden file `tests/release/fixtures/golden/sandbox-pipeline-tiny-0.1.0.README.md` equals the rendered card; every section heading from contracts/model-card.md is present and non-empty; no literal number appears in `model_card.md.j2`; the word "accuracy" does not appear in any rendered card; the quality section starts with "These numbers are agreement with <reference>; they are not measured against human ground truth." (contracts/model-card.md).
- [ ] T041 [P] [US2] Extend `tests/release/test_gate_rules.py` with rules 9, 10, 12 and 13: a card number not present in the results files fails rule 9; a quality metric without `reference`, `benchmark` or `n_items` fails rule 9; a `FakeHub.validate_yaml` warning fails rule 10b (warnings count as failures); a `how_to_run` that raises fails rule 12; fewer than three examples fail rule 13.

### Implementation for User Story 2

- [ ] T042 [US2] Complete `src/mobility_model_zoo/release/templates/model_card.md.j2` and `card.py` with the remaining sections from contracts/model-card.md: model-index front matter built from `quality.json` (task type from `pipeline_tag`, dataset type and name from the benchmark, one metric per entry); quality table (metric, value, description, reference, benchmark, `n_items`, date) with the agreement sentence above it; speed and memory table from `performance.json` with the hardware in every row and the budget (`ram_gb`, no GPU); training data provenance (source groups and teachers, plus the sentence that training data is not published, with reason); training recipe links to `recipe.doc` and `recipe.config` at `recipe.git_commit` on GitHub; a pinning note (`revision="<commit>"`); "About the zoo" links. For sandbox models, the banner says "Pipeline test model. Not for use." and provenance says "synthetic".
- [ ] T043 [US2] Implement rule 9 in `src/mobility_model_zoo/release/gate.py`: the renderer records every number it prints with its source (file and metric), and the rule fails for any number without a source; results files validate against `results.schema.json`.
- [ ] T044 [US2] Implement rule 10 in `gate.py`: (a) every required section present and non-empty; (b) `hub.validate_yaml(readme)` returns no errors and no warnings; also run `huggingface_hub.ModelCard(readme).validate()`.
- [ ] T045 [P] [US2] Implement `src/mobility_model_zoo/release/usage.py` and rule 12: create a fresh virtual environment with `uv venv`, install the package from the checkout at the tag commit with CPU-only torch, write `card.how_to_run` to a file with `{repo_id}` and `{revision}` replaced by `staging.repo` and `staging.revision`, run it with a 10-minute timeout and `HF_TOKEN` set to the release token, and require exit 0 (SC-004). When the GitHub repository is public, additionally check that the install line's tag exists with `git ls-remote`.
- [ ] T046 [P] [US2] Implement `src/mobility_model_zoo/release/examples.py` and rule 13: run the staged model on each text in `zoo/models/<name>/examples/` through the same `how_to_run` environment as T045 and embed the outputs in the card's Examples section (FR-018); at least three example texts are required.
- [ ] T047 [US2] Rebuild the sandbox card, update the golden file, and re-run quickstart.md scenario 3 for `sandbox-pipeline-tiny` 0.1.1 **(ops)**; confirm that rules 9, 10b, 12 and 13 pass on the real Hub and that the preview renders the model-index results. Add the result to `specs/003-model-zoo-hf-release/validation.md` (SC-002).

**Checkpoint**: SC-002, SC-004 and SC-008 are met for the sandbox model.

---

## Phase 5: User Story 3 – The collection is named and structured as a model zoo (Priority: P2)

**Goal**: The repository and the Hub present the zoo: overview per topic, one collection per topic, and a new topic needs no code change.

**Independent Test**: `zoo index` produces `zoo/MODELS.md` with a table per topic; adding a fixture topic `iot` with one model validates and indexes without code changes; sandbox models appear nowhere.

### Tests for User Story 3

- [ ] T048 [P] [US3] Write `tests/release/test_index.py`: `MODELS.md` has one table per non-sandbox topic with name, task, latest version, status and link; sandbox models are absent; a fixture registry with an added topic `iot` and model `iot-anomaly-test` validates and indexes without changing any code; publishing a model of a topic without `hf_collection` creates the collection once and writes its slug to `topics.yaml`, and a second model reuses it (FakeHub).

### Implementation for User Story 3

- [ ] T049 [US3] Implement `src/mobility_model_zoo/release/index.py` and `zoo index`: generate `zoo/MODELS.md` (a header saying it is generated, one table per topic in `topics.yaml` order, sandbox excluded, latest version by semantic version, link to `https://huggingface.co/<repos.public>`).
- [ ] T050 [US3] Extend `zoo publish` in `src/mobility_model_zoo/release/publish.py` (step 7 of contracts/cli.md): for non-sandbox models, create the topic collection in the organization if `hf_collection` is null (public, title = topic title, description = topic description), write the slug to `zoo/topics.yaml`, add the model with a note (summary, max 500 characters), then run `zoo index`. Extend `.github/workflows/release-publish.yml` to commit `zoo/topics.yaml` and `zoo/MODELS.md` as well.
- [ ] T051 [P] [US3] Rewrite `README.md` as the zoo overview (the `jtbd` commands were already updated in T010): what the zoo is, the topics, a link to `zoo/MODELS.md`, the task/release split (one tool per task, `jtbd` for JTBD; `zoo` for releases), how to add a topic or a model, how a release works (stage → tag → review preview → start publish), and the JTBD section with the `jtbd` commands and the new config paths. Keep the spike sections, with commands updated, under a "Spikes (not released)" heading.
- [ ] T052 [P] [US3] Write `docs/adding-a-model.md`: step by step for a new topic and a new model (topic entry, `model.yaml`, release record via `zoo stage`, results files, examples, `zoo validate`, tag, preview, publish), with the naming rule `<topic>-<task>-<variant>` "MUST NOT change after the first publication".

**Checkpoint**: US3 acceptance scenarios 1–3 hold; the sandbox model stays out of the overview and collections.

---

## Phase 6: User Story 4 – A new version replaces an old one without breaking users (Priority: P3)

**Goal**: Version rules, history on the card, deprecation and audit.

**Independent Test**: quickstart.md scenario 6: publish `sandbox-pipeline-tiny` 0.2.0; `revision='v0.1.0'` still returns 0.1.0; the default branch returns 0.2.0; the card lists both versions with their metrics side by side.

### Tests for User Story 4

- [ ] T053 [P] [US4] Write `tests/release/test_versions.py`: `change_type` rules (a changed `output_format_version` requires `major` from 1.0.0 on and at least `minor` below; `initial` only for the first version; `patch` only when files and results are unchanged); publishing 0.1.0 after 0.2.0 exits 3; the version history section lists every published version with date, status, change type, changes and the main quality metrics side by side; `zoo deprecate` sets `status: deprecated` with `reason` and `successor`, produces one card-only commit on `main`, and leaves files and tags unchanged; deprecating the latest version shows the banner, deprecating an older version only changes its history row; `zoo audit` fails when a staging or sandbox repo is public, when a tag points to a commit other than `published.repo_commit` or when the card hash differs.

### Implementation for User Story 4

- [ ] T054 [US4] Extend rule 3 in `src/mobility_model_zoo/release/gate.py` with the `change_type` rules from T053, comparing with the previous version's record.
- [ ] T055 [US4] Add the version history section to `model_card.md.j2` and `card.py`: one row per published version from all release records of the model plus the version being built, with metrics read from each version's `quality.json`.
- [ ] T056 [US4] Implement `zoo deprecate <model> <version> --reason <text> [--successor <version>]` in `src/mobility_model_zoo/release/publish.py`: update the record and push one card-only commit to `main` of the public repo (no tag change): with the deprecation banner if `<version>` is the latest published version, otherwise only its updated row in the version history. Add a `deprecate` job to `.github/workflows/release-publish.yml` triggered by an input `action: deprecate`.
- [ ] T057 [P] [US4] Implement `src/mobility_model_zoo/release/audit.py` and `zoo audit [<model>]`; also check that every `*-staging` repo and every sandbox repo is still private (FR-006a). Write `.github/workflows/zoo-audit.yml` (weekly schedule and `workflow_dispatch`, secret `HF_RELEASE_TOKEN`).
- [ ] T058 [US4] **(ops)** Run quickstart.md scenario 6 with `sandbox-pipeline-tiny` 0.2.0 and record the result in `specs/003-model-zoo-hf-release/validation.md`.

**Checkpoint**: All four stories work independently with the sandbox model.

---

## Phase 7: Hand-over to feature 004 and polish

**Purpose**: Prepare the span model's release and the repository's move to public.

- [ ] T059 [P] Create the span model draft `zoo/models/productdev-jtbd-span-xlmr/`: `model.yaml` (topic `productdev`, task `jtbd`, variant `span-xlmr`, license `Apache-2.0`, `base_model: FacebookAI/xlm-roberta-large`, `base_model_license: MIT`, languages `[de, en]`, `pipeline_tag: token-classification`, `library_name: pytorch`; card texts including in `limitations` that it produces no free-text actor and no English statement, FR-019) and a draft `releases/0.1.0.yaml` with `status: experimental`, `change_type: initial`, `spike_data: false`, and placeholders for staged files, results and recipe. Add three example texts without personal data to `examples/` (not from benchmark chunks).
- [ ] T060 Run `uv run zoo check productdev-jtbd-span-xlmr 0.1.0 --offline` (quickstart.md scenario 7). The only failures must be the fields feature 004 delivers. Write the list to `specs/003-model-zoo-hf-release/handover-004.md` (FR-020).
- [ ] T061 [P] Implement `src/mobility_model_zoo/release/history.py` and `zoo history-check` (research R11): scan all commits on all refs for forbidden paths (anything under `data/`, `.env`, `*.jsonl`, `*.safetensors`, `*.pt`, snapshot and raw-response directories) and run `gitleaks detect --log-opts=--all` for secrets; print offending commits; exit 0 or 1. Test with a temporary git repository in `tests/release/test_history.py`.
- [ ] T062 **(ops)** Run `uv run zoo history-check` once and record the result in `specs/003-model-zoo-hf-release/handover-004.md` (FR-003c). If anything is found, list the commits and the planned fix (history rewrite or fresh public repository); do not make the repository public in this feature.
- [ ] T063 [P] Add a test `tests/release/test_no_secrets_in_logs.py`: run `zoo check`, `zoo build` and `zoo publish` against `FakeHub` with a sentinel token value and assert it never appears in stdout or stderr (FR-012).
- [ ] T064 Run `uv run ruff check`, `uv run pytest` and `uv run zoo validate --all`; all pass.
- [ ] T065 Traceability check: every FR and SC in spec.md maps to at least one task, artifact or test; write the table to `specs/003-model-zoo-hf-release/validation.md`. SC-003 (reader test) is prepared as a questionnaire in `specs/003-model-zoo-hf-release/reader-test.md` with the seven questions from the spec and is run in feature 004 on the public span model card.

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: none.
- **Foundational (Phase 2)**: after Setup. T003 first. T004 → T005 → T006 → T007 → T008 → T009 in sequence (one commit); T010–T013 after T009; T014–T019 after T009. Blocks all stories.
- **US1 (Phase 3)**: after Phase 2. T038 (merge into `main`) and T013 (org and tokens) are needed before T039.
- **US2 (Phase 4)**: after US1's card skeleton (T031) and build (T032).
- **US3 (Phase 5)**: after US1's publish (T034); T051 and T052 can start right after Phase 2.
- **US4 (Phase 6)**: after US1's publish (T034) and US2's card (T042).
- **Phase 7**: T059–T060 after US2; T061–T062 any time after Phase 2; T064–T065 last.

### Within each story

Tests first (they fail), then implementation, then the ops run.

### Parallel opportunities

- Phase 1: T001 ∥ T002.
- Phase 2: after T009: T010 ∥ T011 ∥ T012 ∥ T013 ∥ T015 ∥ T018 ∥ T019; T016 and T017 can run in parallel with each other.
- US1: T020 ∥ T021 ∥ T022 ∥ T023 ∥ T024 (tests); T025 ∥ T026 ∥ T035 ∥ T036 ∥ T037; then T027 → T028, T029 → T030 → T032 → T033 → T034.
- US2: T040 ∥ T041; T045 ∥ T046 after T042.
- US3: T048 ∥ T051 ∥ T052.
- Phase 7: T059 ∥ T061 ∥ T063.

### Parallel example: User Story 1

```text
Together: T020 fixtures, T021 gate rule tests, T022 required-field test, T023 publish tests, T024 build tests
Together: T025 sandbox model, T026 sandbox registry entry, T035 ci.yml, T036 release-verify.yml, T037 release-publish.yml
```

## Implementation Strategy

### MVP (User Story 1)

1. Phases 1 and 2: constitution, license, rename, scaffolding.
2. Phase 3: gate, stage, build, preview, publish, workflows.
3. **Stop and validate**: quickstart scenarios 2–5 on the real Hub with the sandbox model (T039). This proves the pipeline end to end.

### Incremental delivery

1. US2: complete card standard and Hub validation → re-run on the sandbox.
2. US3: overview, collections, README.
3. US4: versions, deprecation, audit.
4. Phase 7: span model draft and dry run, history check → hand-over to feature 004, where the first public model is released.
