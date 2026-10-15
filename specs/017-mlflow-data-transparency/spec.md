# Feature Specification: Transparency over training data, benchmarks and training runs (MLflow)

**Feature Branch**: `claude/mlflow-data-transparency`

**Created**: 2026-10-15

**Status**: Draft

**Input**: User description: "Momentan ist es sehr intransparent was wir an Trainingsdaten und Benchmarks haben. Auch wie das Training läuft. Ich würde gerne MLflow integrieren. […] Mich stört, dass ich keine Übersicht habe, dass ich nicht verstehe, wie groß Trainingssätze sind und wie viele wir haben, wann wir sie geändert haben usw. […] Klingt so, als sei es auf dem Spark besser aufgehoben."

(Translation: Right now it is very opaque what training data and benchmarks we have, and how training runs. The owner wants to integrate MLflow. What bothers the owner most is having no overview: not knowing how large the training sets are, how many there are, when they were changed. The MLflow server belongs on the DGX Spark.)

## Context

The facts the owner is missing mostly exist already, but they are scattered and partly only on disk:

- **Dataset register**: `topics/<topic>/compliance/datasets.yaml` (licence, permitted use, redistribution, approximate size, review dates) and, for productdev, `sources.yaml`.
- **Downloaded data**: `$MMZ_DATA/<id>/` with a `SOURCE.json` per dataset, outside the repository.
- **Frozen training sets**: for example `data/span-train-v1/frozen.json` and its rows.
- **Frozen benchmarks**: `topics/<topic>/benchmarks/<version>/manifest.json` (pilot-v1, pilot-v2, cluster-v1, can-ids-v1 to v3) with freeze date, counts and content hashes; `topics/productdev/benchmarks/current` names the current one.
- **Results**: `zoo/models/<name>/results/<version>/` (quality, performance) and the release records.
- **Change history**: only in git.

Training on the DGX Spark is visible only by following a log file over SSH and copying the results back afterwards. Comparing candidates means opening run folders one by one.

Decisions taken with the owner on 2026-10-15:

1. **MLflow** is the tool for following and comparing runs and for the data overview. No cloud tracking service.
2. **The MLflow server runs on the DGX Spark**, private, reached from the laptop through the owner's SSH connection. Long training runs must not depend on the laptop being awake.
3. **The repository stays the source of truth.** Registers, frozen benchmarks, release records and gate rules are unchanged in authority. MLflow is the lab notebook: it shows, compares and links, it never decides.
4. **Data overview first**: the overview of datasets and benchmarks is the first slice to ship, training-run logging follows.
5. **Only numbers, hashes and metadata go into MLflow**: never dataset text, chunks, labels, frames or personal data.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See all datasets and benchmarks at a glance (Priority: P1)

The owner wants to know, in one place, which datasets, frozen training sets and benchmark versions the zoo has, how large each is, what it may be used for, and when it last changed. They run one command on the laptop or the Spark and get a table: one row per dataset or benchmark version, with topic, kind (third-party dataset, training set, benchmark), size (megabytes, files, rows or chunks or frames or episodes, depending on the kind), class or label distribution where one exists, licence, permitted use (`training_allowed` or `benchmark_only`), freeze date, content hash, last change and which models use it.

**Why this priority**: This is the owner's main complaint. Nearly all the facts exist already, so this slice is cheap and immediately useful, even before any server is running.

**Independent Test**: With no tracking server configured, run the overview on a checkout with a populated `$MMZ_DATA` and on one without. Check that every dataset in every topic register and every benchmark version under `topics/*/benchmarks/` appears exactly once, that counts match the manifests, and that rows whose data is not downloaded say so instead of failing.

**Acceptance Scenarios**:

1. **Given** the registers and benchmark folders of all topics, **When** the owner runs the overview, **Then** every registered dataset, frozen training set and benchmark version is listed once with its size, counts, licence, permitted use, freeze date and hash.
2. **Given** a dataset that is registered but not downloaded on this machine, **When** the overview runs, **Then** the row shows the register values (for example the approximate size) and marks the measured values as "not downloaded here", and the command still succeeds.
3. **Given** a benchmark whose manifest holds per-class counts (for example attack families or label kinds), **When** the overview runs, **Then** the distribution is shown.
4. **Given** the owner wants a narrower view, **When** they filter by topic, kind or permitted use, **Then** only matching rows are shown.
5. **Given** the overview is needed in another tool, **When** the owner asks for machine-readable output, **Then** the same rows come out in a structured format.

---

### User Story 2 - See when and how data changed (Priority: P1)

The owner wants to understand the history: when a dataset was registered, when its licence or permitted use was last reviewed, when a training set or benchmark was frozen, which version superseded which, and what changed between two versions (counts, hashes, splits).

**Why this priority**: "When did we change it" is half of the complaint. Without history the overview is a snapshot that cannot explain why a result moved.

**Independent Test**: Pick a benchmark family with several versions (can-ids-v1 to v3) and a register entry that was edited. Check that the history shows each version with its freeze date and the commit that introduced it, and that a comparison of two versions shows their count and hash differences.

**Acceptance Scenarios**:

1. **Given** a benchmark family with several frozen versions, **When** the owner asks for its history, **Then** each version is listed in order with freeze date, the version it supersedes, the commit that froze it and its counts.
2. **Given** two versions of the same benchmark or training set, **When** the owner compares them, **Then** differences in counts, splits, class distribution and hashes are shown.
3. **Given** a register entry whose licence, permitted use or size was edited, **When** the owner views its history, **Then** each change shows its date, commit and the old and new value.
4. **Given** a frozen benchmark whose manifest content differs from its recorded hash, **When** the overview runs, **Then** it reports the mismatch prominently (a frozen benchmark must never change).

---

### User Story 3 - Browse data versions in MLflow (Priority: P2)

The owner opens the MLflow interface in the laptop's browser and finds an experiment for datasets in which every dataset and benchmark version is one entry, with its sizes and distributions as numbers, its licence and permitted use as attributes, and its freeze date and hash as labels. They sort, filter and chart growth over time there, next to the training runs.

**Why this priority**: It gives the overview a visual, sortable home next to the runs, but the command-line overview (Story 1) already delivers the core value.

**Independent Test**: With the server on the Spark running, publish the overview and open the datasets experiment in the browser through the owner's SSH tunnel. Check that each version appears once, that publishing again without changes creates no duplicates, and that no text or personal data is stored.

**Acceptance Scenarios**:

1. **Given** a configured tracking location, **When** the owner publishes the overview, **Then** each dataset and benchmark version appears as one entry in the datasets experiment.
2. **Given** a version that was published before and has not changed, **When** the owner publishes again, **Then** the existing entry is updated, not duplicated.
3. **Given** a version that changed (new hash), **When** the owner publishes, **Then** a new entry is created and the old one stays, so history is visible.
4. **Given** no tracking location is configured, **When** the owner publishes, **Then** the command says so clearly and the local overview still works.

---

### User Story 4 - Follow a training run live (Priority: P2)

The owner starts a training run on the Spark (for example a span-model candidate) and, instead of following a log file over SSH, opens the browser and sees the run appear with its settings, a live loss and metric curve, its progress and its status. When it finishes, its final metrics, timing and hardware are there; when it fails, it is marked failed.

**Why this priority**: This is the second complaint ("how training runs"). It depends on the server (Story 3's setup) and on changes to each task's tools, so it follows the data overview.

**Independent Test**: Start a short training run of one task on the Spark with the tracking location set. Check in the browser that the run shows its settings and updating metrics while it runs, and the final state after it ends. Repeat with the tracking server stopped: the training must finish normally.

**Acceptance Scenarios**:

1. **Given** a configured tracking location, **When** a training or tuning run starts, **Then** it appears in its task's experiment with its configuration, code commit, hardware and start time.
2. **Given** a running training, **When** an epoch or evaluation step ends, **Then** its metrics appear in the run within a minute.
3. **Given** a run that ends, fails or is interrupted, **Then** its final status is recorded.
4. **Given** the tracking server is unreachable, **When** a run starts or loses the connection, **Then** the run continues and completes, its own result files are complete as today, and it warns that tracking was incomplete.

---

### User Story 5 - Every run and model is linked to its data (Priority: P2)

For any training or evaluation run, the owner sees which dataset versions it trained on and which benchmark version it was measured against; for any dataset or benchmark version, the owner sees which runs used it. Release records can name the run a released model came from.

**Why this priority**: This is what turns two separate overviews into transparency: a result can always be traced to its data. It needs Stories 3 and 4.

**Independent Test**: Run one training and one evaluation, then check in both directions: run → data versions, data version → runs. Check that a release record carrying a run reference passes the release gate, and one without still passes.

**Acceptance Scenarios**:

1. **Given** a training run, **When** the owner opens it, **Then** it names each training set version (with hash) it used.
2. **Given** an evaluation run, **When** the owner opens it, **Then** it names the frozen benchmark version it was measured on.
3. **Given** a dataset or benchmark version, **When** the owner looks it up, **Then** the runs that used it are listed.
4. **Given** a release record, **When** it names a run, **Then** the reference is checked for form and shown in the release evidence; release records without one stay valid.

---

### User Story 6 - Compare candidates side by side (Priority: P3)

When several candidates of one task have run (for example span-model candidates c1 to c4, or picket-forest settings), the owner compares them in one table and chart: settings, quality metrics on the same benchmark version, training time and budget-relevant measurements.

**Why this priority**: Useful for decisions, but the existing Pareto and results commands already cover the formal decision. This story makes the exploration easier.

**Independent Test**: With three finished candidates of one task, open the comparison and check that settings and metrics line up and that runs measured on different benchmark versions are not silently mixed.

**Acceptance Scenarios**:

1. **Given** several finished runs of one task, **When** the owner compares them, **Then** their settings and metrics appear side by side.
2. **Given** runs measured on different benchmark versions, **When** they are compared, **Then** the benchmark version is visible on each and they can be filtered by it.

---

### Edge Cases

- A dataset is registered in two topics, or one benchmark builds on another (`based_on`, `supersedes`): it is listed once per version, with the relation shown.
- `$MMZ_DATA` points to a missing or partially downloaded folder: measured values are marked partial, register values still shown.
- A benchmark manifest is malformed or a referenced file is missing: the row is reported as an error, the rest of the overview still prints.
- A frozen benchmark's content no longer matches its recorded hash: reported as an integrity failure (constitution IX).
- The overview runs in CI or on a fresh clone with no data and no tracking location: it still lists everything from the repository and exits successfully.
- The Spark is off or the tunnel is down while the owner publishes: the command fails clearly for publishing only; nothing is half-written.
- A training run is restarted with the same configuration: it is a new run; earlier runs stay.
- Training runs on the laptop (for example on its GPU) or on the hardware-in-the-loop runner: they log to the same server when the tracking location is set and record their hardware.
- A run tries to record a value that looks like free text from a dataset (a quote, a chunk, a payload): it is refused by the privacy guard.
- Labeling and teacher runs: Claude never appears as a labeler, teacher or judge in any logged run (Principle XI); the logged metadata names the actual models used.
- The tracking store on the Spark is lost: it can be restored from the last backup, and the data overview (Stories 1–3) can be rebuilt entirely from the repository and `$MMZ_DATA`.

## Requirements *(mandatory)*

### Functional Requirements

**Data and benchmark overview (Stories 1–2)**

- **FR-001**: The zoo MUST provide one command that lists every registered third-party dataset of every topic, every frozen training set and every frozen benchmark version, one row per version.
- **FR-002**: Each row MUST show topic, kind, identifier and version, licence, permitted use, redistribution, size in megabytes, file count, the item counts that fit the kind (rows, chunks, frames, episodes, captures, recordings), the class or label distribution where the source records one, freeze date, content hash, last change date and the models that use it.
- **FR-003**: The overview MUST work from the repository alone; measured values that need downloaded data MUST be marked "not downloaded here" when the data is absent, never guessed.
- **FR-004**: The overview MUST support filtering by topic, kind and permitted use, and MUST offer a machine-readable output with the same content.
- **FR-005**: The zoo MUST show the history of a dataset, training set or benchmark family: each version with freeze date, superseded version, the commit that introduced it, and each register change with date, commit, old and new value.
- **FR-006**: The zoo MUST compare two versions of the same training set or benchmark and show differences in counts, splits, class distribution and hashes.
- **FR-007**: The overview MUST verify the content hash of every frozen benchmark it can check and report any mismatch as an integrity failure.
- **FR-008**: The overview MUST NOT read or print dataset content beyond counting and hashing it.

**Tracking server and configuration (Story 3, all logging)**

- **FR-009**: A private MLflow tracking server MUST run on the DGX Spark, reachable only through the owner's authenticated connection, not from the open network.
- **FR-010**: The tracking location MUST be set only through the environment (the `.env` file); no code or configuration file in the repository may hard-code it.
- **FR-011**: Without a tracking location, every existing command MUST behave exactly as today; CI and the base install MUST NOT need the tracking software, which ships as a new optional extra.
- **FR-012**: The tracking store MUST be backed up on a schedule, and a restore MUST be documented and tested once.
- **FR-013**: Setting up, starting, stopping, updating and restoring the server MUST be documented as owner steps and scripted where possible.

**Data versions in MLflow (Story 3)**

- **FR-014**: The overview MUST be publishable to an experiment for datasets, one entry per dataset or benchmark version, with sizes and distributions as metrics, licence and permitted use as parameters, and identifier, version, freeze date and hash as tags.
- **FR-015**: Publishing MUST be idempotent: an unchanged version (same hash) updates its entry; a changed version creates a new entry; old entries are kept.
- **FR-016**: Publishing MAY attach a profile report per version (distributions, lengths, outliers) that contains only aggregates, never content.

**Run logging (Stories 4–6)**

- **FR-017**: The training, tuning and evaluation commands of every task (JTBD span model, JTBD clustering, CAN intrusion detection, sound anomaly, activity recognition) and the hardware-in-the-loop measurements MUST log to their task's experiment when a tracking location is set.
- **FR-018**: Each run MUST record its configuration (file and values), code commit and whether the tree was clean, hardware, start and end time, status, metrics over time where the run produces them, and final metrics.
- **FR-019**: Each training run MUST record the training set versions and hashes it used; each evaluation run MUST record the frozen benchmark version it was measured on.
- **FR-020**: Logging MUST never make a run fail or change its results: when the server is unreachable the run continues, its own result files stay complete, and it warns that tracking was incomplete.
- **FR-021**: Logging MUST add no more than a small, measured overhead to run time (see SC-006).
- **FR-022**: A release record MAY name the run a model version came from; the release gate MUST check the reference's form when present and MUST NOT require it.
- **FR-023**: Model weights MUST NOT be stored in the tracking store; runs reference the trained files by path and hash, and released models by their published revision.

**Privacy, compliance and source of truth**

- **FR-024**: Nothing logged MUST contain dataset text, chunks, quotes, labels, payloads, frames, timestamps lists or personal data. A guard MUST refuse free-text values and artifacts that are not on an allow-list of aggregate kinds.
- **FR-025**: The registers, frozen benchmarks, release records and gate rules MUST stay the only source of truth. No gate, decision or report MUST read its inputs from the tracking store.
- **FR-026**: Claude MUST NOT appear in any logged data work as labeler, teacher, judge or data generator (Principle XI); tracking features that call a language model to judge or label MUST NOT be used with Claude.
- **FR-027**: The compliance register and generated documents (record of processing, privacy notice where relevant) MUST be updated if the tracking store is a new place where processing records are kept.

**History of past work**

- **FR-028**: Historical training and evaluation results that already exist in the repository [NEEDS CLARIFICATION: Should past results (scout-large 0.1.0–0.1.3, picket-forest 0.2.0–0.2.1, cluster-v1 runs) be imported into MLflow as runs marked "imported", or does tracking start with new runs only?]

**Visibility outside the terminal and MLflow**

- **FR-029**: The overview [NEEDS CLARIFICATION: Should a generated overview file (for example `docs/data-inventory.md`) be committed and kept current by CI, like the compliance documents, or is the command plus MLflow enough?]

### Key Entities

- **Dataset version**: one registered third-party dataset as downloaded; identifier, topic, licence, permitted use, redistribution, approximate and measured size, counts, source hash, register history.
- **Training set version**: one frozen set of rows or chunks built for training; identifier, version, freeze date, hash, counts, split sizes, label distribution, the datasets it was built from.
- **Benchmark version**: one frozen benchmark; identifier, version, task, freeze date, hash, counts, class distribution, the version it supersedes or is based on, the datasets it draws on.
- **Run**: one training, tuning, evaluation or measurement execution; task, configuration, commit, hardware, times, status, metrics, the data and benchmark versions it used.
- **Model version**: as today in the release record; may reference the run it came from.
- **Tracking server**: the private MLflow instance on the Spark with its store and backups.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The owner can answer "how many datasets and benchmarks do we have, how large is each, and when did each last change" in under one minute, with one command.
- **SC-002**: 100 % of registered datasets and frozen benchmark versions appear in the overview; counts match the frozen manifests exactly.
- **SC-003**: For any benchmark family, the owner can name every version, its freeze date and how it differs from the previous one in under two minutes.
- **SC-004**: The owner can follow a running training on the Spark from the laptop's browser without opening an SSH shell, with metrics no more than one minute behind.
- **SC-005**: For every run logged after this feature, the training set and benchmark versions it used can be found in one step, in both directions.
- **SC-006**: Run-time overhead of logging stays below 2 % on a typical training run; a run with the server down completes with identical result files.
- **SC-007**: A scan of the tracking store finds no dataset text, chunk, label or personal data.
- **SC-008**: With no tracking location set, the full existing test suite and CI pass unchanged, and the base install size does not grow.
- **SC-009**: Restoring the tracking store from backup is done once successfully and takes under 30 minutes.
- **SC-010**: Cash cost of the feature is zero (local compute only).

## Assumptions

- The owner is the only user; no multi-user permissions are needed. Access goes through the owner's existing SSH access to the Spark.
- The Spark has enough disk for the tracking store: metrics, parameters, small aggregate reports; no weights (FR-023).
- The backup target is a second machine or disk the owner already has (the laptop or an external drive); the plan names it.
- `$MMZ_DATA` exists on the machines where data is downloaded; the overview runs where the data is, and publishes from there.
- Frozen manifests already hold counts and hashes for benchmarks; frozen training sets have a freeze file with a hash. Datasets whose register lacks counts get measured values only where they are downloaded.
- The datasets overview is a new view on existing facts. It adds no new register fields unless the plan finds a gap (for example a missing hash).
- Cost tier: local compute only (constitution, Resources & Cost Discipline). No cash budget is needed.
- The website and Hugging Face model cards are out of scope; nothing from the tracking store is published.
- Spikes (constitution, Technical Spikes) may log to the same server in their own experiment, labeled "spike", and never count as benchmark results.
