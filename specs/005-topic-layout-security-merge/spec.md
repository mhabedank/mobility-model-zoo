# Feature Specification: Topic layout and security merge

**Feature Branch**: `005-topic-layout-security-merge`

**Created**: 2026-10-07

**Status**: Draft

**Input**: User description: "Merge the mobility-security-ml repository into the mobility-model-zoo and restructure the zoo repository around topics (one topic = one Hugging Face collection). Combine both unmerged branches of mobility-security-ml (research and `can-ids-tiny` from `claude/clever-goldberg-ygio83`; hardware-in-the-loop bench, dataset downloader and real-data models from `claude/cool-volta-rqsgdx`). Drop their separate Hugging Face pipeline and automatic dataset mirroring. New topics `security` and `condition-monitoring`. Code in `src/mobility_model_zoo/<topic>/<task>`, shared code for datasets and edge deployment, non-code per topic in `topics/<topic>/`. Preserve git history, archive the old repository and delete its secrets. All artifacts in English. No model is published in this feature."

## Context

The zoo repository (`mhabedank/mobility-model-zoo`) holds one published model (`scout-large`, topic `productdev`) and the shared release tool. A second repository, `mhabedank/mobility-security-ml`, was started for TinyML models in automotive security. Its `main` branch holds only an initial commit. Its content lives in two branches that were built in parallel and never merged:

| Source branch | Content |
|---|---|
| `claude/clever-goldberg-ygio83` | German research documents (threat landscape, literature, datasets, hardware, toolchain, research notes), a roadmap, the model `can-ids-tiny` (random forest exported to C, ESP32 and ESP8266 firmware, model card, trained on can-train-and-test, CC BY 4.0), CAN feature, dataset and metric code, a setup script for cloud machines |
| `claude/cool-volta-rqsgdx` | `hilbench`, a hardware-in-the-loop test bench (simulated boards, emulated ESP32, real boards), an int8 inference engine with a bit-exact reference, TFLite import, a dataset registry and downloader that verifies provider licenses, trained models `can_ids_road` (ROAD, CC BY 4.0), `mimii_fan_ae` (MIMII, CC BY-SA 4.0) and `har_cnn1d` (UCI HAR, CC BY 4.0), synthetic bench references, CI workflows and its own Hugging Face publishing path |

Owner decisions of 2026-10-07: combine both branches; publish only through the zoo release pipeline; add the topics `security` and `condition-monitoring`; lay out the repository by topic; keep the git history and archive the old repository.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One repository, laid out by topic (Priority: P1)

The owner opens the zoo repository and finds every topic (and so every Hugging Face collection) in the same place: what the topic is about, its research and literature, the datasets it uses and where they come from, its reports and its build recipes. The JTBD material that today sits in loose top-level folders lives under its topic, next to the new security and condition-monitoring material.

**Why this priority**: The layout is the frame every later step fills. Moving content first and restructuring later would move it twice.

**Independent Test**: On the merged branch, list the top level and `topics/`: each registered topic has one folder with the same internal sections, no JTBD-only folder remains at the top level, the full test suite passes and the release audit for `scout-large` still passes.

**Acceptance Scenarios**:

1. **Given** the restructured repository, **When** the owner lists `topics/`, **Then** there is exactly one folder per topic registered in `zoo/topics.yaml` (`productdev`, `security`, `condition-monitoring`; `sandbox` needs none), each with a README that states what the topic covers and links its Hugging Face collection.
2. **Given** the move of the JTBD folders, **When** the test suite and `zoo audit` run, **Then** both pass with the same results as before the move.
3. **Given** the published `scout-large` card and its install line, **When** a reader follows them after the move, **Then** every link and the install line still resolve (they point at fixed commits and tags).
4. **Given** the new topic layout, **When** a contributor reads the "adding a model" guide, **Then** it says where code, configuration, research, dataset entries, reports and recipes of a new topic or task go.

---

### User Story 2 - Security and condition-monitoring content arrives in the zoo (Priority: P1)

The content of both security branches is in the zoo repository with its history, in the topic layout, in English, and reconciled where the two branches overlap. The models that exist in the old repository are registered as zoo models with names following `<name>-<variant>`, and each can be checked by the release gate without being published.

**Why this priority**: This is the merge itself. Without it the old repository cannot be retired.

**Independent Test**: `git log --follow` on a moved file shows commits from the old branches; `zoo check` runs for each registered security and condition-monitoring model and reports either a pass or a concrete list of missing evidence; nothing is created on Hugging Face.

**Acceptance Scenarios**:

1. **Given** a file that came from either source branch, **When** the owner views its history, **Then** the original commits, authors and dates are visible.
2. **Given** the German research documents, **When** they arrive, **Then** they are in English under `topics/security/research/`, with every cited paper, dataset and license kept.
3. **Given** two CAN intrusion detectors (`can-ids-tiny` on can-train-and-test, `can_ids_road` on ROAD), **When** they are registered, **Then** both are models of topic `security`, task CAN intrusion detection, with names under the naming rule, and they are measured with one shared evaluation protocol for that task.
4. **Given** `mimii_fan_ae` and `har_cnn1d`, **When** they are registered, **Then** they belong to topic `condition-monitoring`, and their mobility relevance and limits are stated.
5. **Given** synthetic bench references (`can_ids_mlp`, `sensor_ae`, `imu_gnss_cnn1d`), **When** the content is merged, **Then** they stay test fixtures of the bench and are not registered as zoo models.
6. **Given** the old Hugging Face publishing path and its automatic dataset mirroring, **When** the content is merged, **Then** neither remains in the repository, any staging repositories it created are listed for the owner, and each dataset declaration records whether redistribution is allowed, not allowed or unclear.

---

### User Story 3 - Datasets are declared, downloadable and license-checked per topic (Priority: P2)

For each topic, a reader sees which datasets are used, from where, under which license, with which permitted use (training or benchmark only), and how to fetch them. A contributor runs one command to download a dataset from its original provider into a local directory outside the repository; another command checks that the provider still declares the recorded license.

**Why this priority**: Every non-JTBD model needs ground-truth data from third parties. Provenance and licenses decide whether a model may be published at all.

**Independent Test**: List the datasets of `security`; download one small dataset into a temporary directory; run the license check; confirm the repository contains no dataset files.

**Acceptance Scenarios**:

1. **Given** the dataset declarations, **When** a contributor lists them, **Then** each entry shows topic, provider, license, permitted use, commercial use, approximate size and status (for example `rejected` or `broken at source` with a reason).
2. **Given** a dataset download, **When** it finishes, **Then** origin, license, retrieval date and checksum are recorded next to the data, and nothing lands inside the repository.
3. **Given** a provider changes the declared license, **When** the scheduled license check runs, **Then** it fails and names the dataset.
4. **Given** a dataset declared `benchmark_only` (for example a non-commercial CAN dataset), **When** a training run uses it, **Then** the run is refused.

---

### User Story 4 - Edge models can be built, verified on devices and released (Priority: P2)

A contributor builds a microcontroller model, checks that the device produces the same output as the host reference, measures latency and memory on simulated, emulated or real boards, and records those measurements as the speed evidence a release needs. The release tool accepts firmware and C-header artifacts and a microcontroller as the reference hardware.

**Why this priority**: The release gate and model card today assume a Python model measured on a CPU or GPU. Without this story, no security model can pass the gate.

**Independent Test**: Run the bench against the simulated board in CI; run `zoo check` on one edge model with its device measurements; render its model card preview.

**Acceptance Scenarios**:

1. **Given** the merged bench, **When** CI runs, **Then** unit tests, the full bench suite on the simulated board and on the emulated ESP32 pass, and firmware builds for all targets report flash and RAM use.
2. **Given** an edge model with measurements from a named board, **When** its model card is rendered, **Then** it states the board, clock, latency, flash and RAM, whether the numbers come from a real board, an emulator or a simulator, and how to use the model on a device.
3. **Given** a measurement from an emulator or simulator only, **When** the release gate runs, **Then** it refuses a release with status other than `experimental` until a real-board measurement exists.
4. **Given** the real-board CI job, **When** no self-hosted runner with boards is registered, **Then** it is skipped, not failed.

---

### User Story 5 - Credentials and pipelines live only in the zoo; the old repository is retired (Priority: P3)

All CI and release credentials needed for any topic are configured in the zoo repository. The old repository points to the zoo, is archived and holds no secrets.

**Why this priority**: Comes last, after the content is safely merged and CI is green.

**Independent Test**: List secrets and variables in both repositories; open the old repository's README; confirm it is archived.

**Acceptance Scenarios**:

1. **Given** the merged workflows, **When** the owner lists the zoo's secrets, **Then** every secret a workflow references exists, and the list matches a documented table of credentials (name, purpose, scope, which workflow uses it, how to rotate it).
2. **Given** the old repository, **When** the merge is on `main` of the zoo, **Then** its `main` README says where the content now lives, its branches remain readable, it is archived and it has no secrets or variables left.
3. **Given** any commit in the merged history, **When** the secret scan runs, **Then** it finds no credentials.

---

### Edge Cases

- A file exists in both source branches at the same path (`README.md`, `pyproject.toml`, `.gitignore`, `uv.lock`, `LICENSE`): the zoo's version wins; useful content is moved into topic documents; nothing is merged blindly.
- The two CAN codebases overlap (feature extraction, metrics, dataset loading): one implementation per concern remains, and the other is removed with a note in the research log; whichever is kept must still produce the published numbers of the model that used it, or the difference is recorded.
- Binary artifacts in the source branches (firmware images, trained weights, a 44,000-line generated C header, test vectors): build outputs are not committed again if they can be rebuilt; release artifacts go to staging through `zoo stage`, not into git.
- History rewriting moves files to new paths; commit hashes in the old repository change in the zoo. Commit messages that refer to paths are left unchanged.
- MIMII-trained weights are under CC BY-SA 4.0: the model license must follow, and the card must say so.
- ROAD license is marked "to be confirmed" in one branch and CC BY 4.0 in the other: the dataset entry records what the provider declares today, and the license check is the source of truth.
- `can-mirgu` is broken at the provider: it stays declared with status `broken at source`, so nobody tries again blindly.
- The constitution names Ludwig as the primary training framework and assumes frontier labeling as the reference; edge models use other frameworks and ground-truth datasets. These rules are amended or scoped to their task, not violated silently.
- The private staging repositories created by the old `hub` workflow (`hilbench-*`) exist on Hugging Face outside the zoo naming rule.

## Requirements *(mandatory)*

### Functional Requirements

**Layout**

- **FR-001**: The repository MUST have one folder `topics/<topic>/` per public topic registered in `zoo/topics.yaml`, with the same sections in each: `README.md` (scope, tasks, link to the Hugging Face collection), `research/`, `datasets.yaml`, `reports/`, `recipes/`, and topic-specific sections where needed (for example `guideline/` for JTBD).
- **FR-002**: Code MUST stay under `src/mobility_model_zoo/<topic>/<task>/`; code used by more than one task MUST live in a shared module for datasets (`data`) or edge deployment (`edge`). Configuration MUST live under `configs/<topic>/<task>/`.
- **FR-003**: The JTBD-only top-level folders (`guideline/`, `reports/`, `benchmarks/`, `spike/`, `deploy/`, `docs/recipes/`) MUST move under `topics/productdev/` (together with the productdev scripts from `scripts/pilot`, `scripts/span`, `scripts/railway` and `scripts/spark`), and every reference in code, configuration, tests and the current model records MUST follow.
- **FR-004**: Published `scout-large` versions MUST keep passing `zoo audit` and their published cards, links and install lines MUST keep resolving.
- **FR-005**: The top-level README MUST list the topics with their collections and models and explain the layout in one short section; `docs/adding-a-model.md` MUST describe where each part of a new topic or task goes.

**Merge**

- **FR-006**: The content of both source branches MUST be imported with its commit history, rewritten to the target paths.
- **FR-007**: The repository MUST register the topics `security` and `condition-monitoring` in `zoo/topics.yaml`; the Hugging Face collections MUST be created only when the first model of a topic is published, and until then the entry records that no collection exists yet.
- **FR-008**: `can-ids-tiny` and `can_ids_road` MUST be registered as models of topic `security`, `mimii_fan_ae` and `har_cnn1d` as models of topic `condition-monitoring`, each under a name that follows `<name>-<variant>` (chosen in planning: `picket-forest`, `picket-mlp`, `hum-fan`, `pace-cnn`), with model records the release gate can check. None of them is published in this feature.
- **FR-009**: Each new task (CAN intrusion detection, machine-sound anomaly detection, activity recognition from IMU data) MUST state its scope (in and out), its reference data, its metrics and its evaluation protocol in a task document, as the constitution requires of every new task.
- **FR-010**: Overlapping code from the two branches MUST be reduced to one implementation per concern; for each dropped part, the research log MUST say what was dropped and why.
- **FR-011**: The separate Hugging Face publishing code and workflow, including its automatic dataset mirroring, MUST be removed. No dataset is published in this feature; publishing datasets (for example as a data compendium on Hugging Face) is a later feature that starts from the redistribution status recorded in the declarations (FR-014).
- **FR-012**: All research documents, the roadmap, dataset documentation, model cards and READMEs from the source branches MUST be in English, keeping every citation, link, dataset and license statement.
- **FR-013**: Build outputs that can be regenerated (firmware images, generated headers, trained weights, logs) MUST NOT be committed again unless a test needs them as fixed input; the recipe to regenerate them MUST be documented.

**Datasets**

- **FR-014**: Every dataset a topic uses or has rejected MUST be declared in `topics/<topic>/datasets.yaml` with provider, source URL, license, permitted use (`training_allowed` or `benchmark_only`), redistribution (`allowed`, `not_allowed` or `unclear`, with the basis of the decision), commercial use, retention period, approximate size and status with reason.
- **FR-015**: A shared command MUST list declared datasets, download a dataset from its original provider into a local directory outside the repository and record origin, license, retrieval date and checksum next to the data.
- **FR-016**: A shared command and a scheduled CI job MUST compare the license each provider declares today with the declared license and fail on a mismatch.
- **FR-017**: Training MUST refuse a dataset declared `benchmark_only`.

**Edge models and releases**

- **FR-018**: The hardware-in-the-loop bench MUST run in CI against a simulated board and an emulated ESP32 and MUST build firmware for every declared target; the real-board job MUST run only on a self-hosted runner and be skipped when none exists.
- **FR-019**: The release record, gate and model card MUST support edge models: artifacts such as C headers, int8 weights and firmware; a microcontroller as reference hardware; latency, flash and RAM as speed evidence; and the origin of each measurement (real board, emulator, simulator).
- **FR-020**: The release gate MUST refuse a non-`experimental` release of an edge model whose speed evidence does not include a real board.
- **FR-021**: The model license MUST be compatible with the licenses of its training datasets (for example CC BY-SA 4.0 for a model trained on MIMII), and the gate MUST check this against the dataset declarations.

**Credentials and retirement**

- **FR-022**: The zoo repository MUST hold every secret and variable its workflows reference; a document MUST list each credential with purpose, scope, using workflow and rotation steps. Secrets MUST NOT be committed.
- **FR-023**: A one-time secret and forbidden-path scan MUST run over the full merged history before the merge reaches `main`.
- **FR-024**: After the merge is on the zoo's `main`, the old repository MUST get a `main` README pointing to the zoo, MUST have its secrets and variables deleted and MUST be archived. Its branches MUST stay readable.
- **FR-025**: Private staging repositories created by the old publishing path MUST be listed for the owner; deleting them is the owner's decision.

**Constitution**

- **FR-026**: The constitution MUST be amended before implementation where its rules are specific to JTBD or to the old layout: ground-truth datasets as a reference, metric naming, tools and budgets per task, measurement origin, dataset storage and redistribution, and the topic layout. Done as constitution 2.0.0 (2026-10-08); this feature's code, gate and card MUST follow it.

### Key Entities

- **Topic**: a subject area of the zoo, mirrored as one Hugging Face collection; has an id, title, description, collection reference and a folder under `topics/`.
- **Task**: a problem within a topic with one build-and-measure tool, one evaluation protocol and a scope; owns code and configuration.
- **Model**: a named, versioned artifact family `<name>-<variant>` belonging to one topic and task; has a model record and release records.
- **Dataset declaration**: a third-party dataset used or rejected by a topic, with provider, license, permitted use, retention, size and status.
- **Device measurement**: latency, flash and RAM of a model on a named target, with its origin (real board, emulator, simulator) and date.
- **Credential**: a CI secret or variable with purpose, scope, using workflow and rotation steps.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100 % of files from both source branches are either present in the zoo with history or listed in the research log as intentionally dropped, with a reason.
- **SC-002**: Every public topic has the same set of sections; `zoo validate --all` confirms the required sections (README, dataset declarations, research, reports, recipes) for every public topic.
- **SC-003**: The full test suite and `zoo audit` pass on the merged branch; the published `scout-large` card shows no broken link.
- **SC-004**: Four models (two `security`, two `condition-monitoring`) are registered and each gets a definite answer from the release gate: pass, or a list of missing evidence.
- **SC-005**: Zero dataset files and zero credentials in the merged history, confirmed by the repository scan and the secret scan.
- **SC-006**: The old repository is archived with zero secrets and variables, and its README points to the zoo.
- **SC-007**: Zero files in German among the merged documents.

## Assumptions

- The owner reviews only the release of models (memory: autonomy); restructuring, translation and merge are carried out and verified automatically.
- History is imported by rewriting the source branches to target paths and merging them with unrelated histories; small fixups after the import are separate commits.
- The topic id `condition-monitoring` and the title "Condition monitoring" are used; the Hugging Face collection is created by the release pipeline with the first publication in that topic.
- Model names are chosen during planning; the snake_case names from the old branches are working titles only.
- The repository `mhabedank/mobility-datasets` (KITTI downloader) is out of scope; it can be folded in later through the same dataset declaration format.
- No cash cost is expected; emulators and simulators run on free CI runners. A real-board runner is optional.
- Hardware budget for edge models: the boards in the bench inventory (ESP8266, ESP32 family, RP2040/RP2350, STM32F446, nRF52840). Each model's task document states its own memory budget (Principle V).

## Constitution Compliance

| Principle | How this feature complies |
|---|---|
| III Measure Before Optimizing | Each new task gets a frozen evaluation protocol before results are reported (FR-009). |
| V Small and Local by Default | Edge models run on microcontrollers; measurements on the reference board (FR-019, FR-020). |
| VI Clean Provenance | Dataset declarations with license, permitted use, redistribution, commercial use, retention (FR-014 to FR-017); data never in git; no dataset published in this feature (FR-011). |
| VIII Fair Architecture Comparison | One evaluation protocol per task for both CAN detectors (US2 scenario 3); each task states its tools and the reason (constitution 2.0.0). |
| IX Reproducible, Dated Releases | Only the zoo pipeline publishes (FR-011); published versions stay auditable (FR-004). |
| Project Scope | New tasks state their scope (FR-009); a new topic changes no existing model (FR-004). |
| Tasks and Releases | Shared code is extracted because three tasks use it (FR-002). |
| Governance | Constitution 2.0.0 with version bump and rationale, done before implementation (FR-026). |
