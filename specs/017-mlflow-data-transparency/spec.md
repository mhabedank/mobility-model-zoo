# Feature Specification: Transparency over training data, benchmarks and training runs (MLflow)

**Feature Branch**: `claude/mlflow-data-transparency`

**Created**: 2026-10-15

**Status**: Draft (revised 2026-10-16: tracking store on the laptop, see decision 2)

**Input**: User description: "Momentan ist es sehr intransparent was wir an Trainingsdaten und Benchmarks haben. Auch wie das Training läuft. Ich würde gerne MLflow integrieren. […] Mich stört, dass ich keine Übersicht habe, dass ich nicht verstehe, wie groß Trainingssätze sind und wie viele wir haben, wann wir sie geändert haben usw. […] Klingt so, als sei es auf dem Spark besser aufgehoben."

(Translation: Right now it is very opaque what training data and benchmarks we have, and how training runs. The owner wants to integrate MLflow. What bothers the owner most is having no overview: not knowing how large the training sets are, how many there are, when they were changed. The MLflow server belongs on the DGX Spark. Superseded on 2026-10-16, see decision 2.)

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
2. **The MLflow server runs on the owner's laptop** (revised 2026-10-16), on its loopback interface only. Nothing of the tracking feature runs as a service on the DGX Spark. Training runs on the Spark write an offline run log into their own output folder; the owner fetches these logs over the existing SSH access and syncs them into the laptop store. Long training runs still never depend on the laptop being awake.
3. **The repository stays the source of truth.** Registers, frozen benchmarks, release records and gate rules are unchanged in authority. MLflow is the lab notebook: it shows, compares and links, it never decides.
4. **Data overview first**: the overview of datasets and benchmarks is the first slice to ship, training-run logging follows.
5. **Only numbers, hashes and metadata go into MLflow**: never dataset text, chunks, labels, frames or personal data.
6. **Past results are imported** once as runs marked "imported" (final values only), so the history in MLflow starts with the first published model, not with this feature.
7. **No committed overview file**: the command and MLflow are the two places to look; nothing extra is generated into the repository.

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

**Independent Test**: With the server on the laptop running, publish the overview and open the datasets experiment in the laptop's browser. Check that each version appears once, that publishing again without changes creates no duplicates, and that no text or personal data is stored.

**Acceptance Scenarios**:

1. **Given** a configured tracking location, **When** the owner publishes the overview, **Then** each dataset and benchmark version appears as one entry in the datasets experiment.
2. **Given** a version that was published before and has not changed, **When** the owner publishes again, **Then** the existing entry is updated, not duplicated.
3. **Given** a version that changed (new hash), **When** the owner publishes, **Then** a new entry is created and the old one stays, so history is visible.
4. **Given** no tracking location is configured, **When** the owner publishes, **Then** the command says so clearly and the local overview still works.

---

### User Story 4 - Follow a training run (Priority: P2)

The owner starts a training run on the Spark (for example a span-model candidate). Instead of reading a log file over SSH, they run one command on the laptop that fetches the run's offline log and syncs it, then see the run in the browser with its settings, its loss and metric curve so far, its progress and its status. Running the command again during training adds the epochs since the last sync. When the run finishes, its final metrics, timing and hardware are there; when it fails, it is marked failed. A training run on the laptop itself logs straight to the laptop's server and is visible live.

**Why this priority**: This is the second complaint ("how training runs"). It depends on the server (Story 3's setup) and on changes to each task's tools, so it follows the data overview. A live view of Spark runs is given up for a fetch-and-sync step, because nothing may run as a service on the Spark (decision 2).

**Independent Test**: Start a short training run of one task on the Spark in offline mode. Sync it once mid-run and once after it ends; check in the browser that the run shows its settings and the metrics up to each sync, then the final state, and that the second sync added only the new epochs. Start a short run on the laptop with the server running and stop the server mid-run: the training must finish normally.

**Acceptance Scenarios**:

1. **Given** a configured tracking location or offline mode, **When** a training or tuning run starts, **Then** it appears in its task's experiment (offline runs after the next sync) with its configuration, code commit, hardware and start time.
2. **Given** a running training on the laptop, **When** an epoch or evaluation step ends, **Then** its metrics appear in the run within a minute. **Given** a running training on the Spark, **When** the owner syncs, **Then** every epoch completed so far appears, and nothing is duplicated.
3. **Given** a run that ends, fails or is interrupted, **Then** its final status is recorded (for offline runs, at the next sync; a run whose log has no end is shown as running).
4. **Given** the tracking server is unreachable, **When** a run starts or loses the connection, **Then** the run continues and completes, its own result files are complete as today, and it warns that tracking was incomplete.
5. **Given** an offline log that was synced, **When** it is synced again unchanged, **Then** nothing changes in the store.

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

- One benchmark builds on another (`based_on`, `supersedes`): each is listed once per version, with the relation shown.
- The same dataset id appears in two topics: `zoo data validate` already refuses duplicate ids; if it happens anyway, the overview shows an error row for the id instead of two silent rows.
- `$MMZ_DATA` points to a missing or partially downloaded folder: measured values are marked partial, register values still shown.
- A benchmark manifest is malformed or a referenced file is missing: the row is reported as an error, the rest of the overview still prints.
- A frozen benchmark's content no longer matches its recorded hash: reported as an integrity failure (constitution IX).
- The overview runs in CI or on a fresh clone with no data and no tracking location: it still lists everything from the repository and exits successfully.
- The laptop's server is not started while the owner publishes or syncs: the command fails clearly for publishing or syncing only; nothing is half-written, and a later sync resumes where the last one stopped.
- An offline log's last line is incomplete because the run is still writing: sync ignores that line and picks it up next time.
- An offline log was edited by hand: sync applies the privacy guard again and refuses values that do not pass.
- A training run is restarted with the same configuration: it is a new run; earlier runs stay.
- Training runs on the laptop (for example on its GPU) log live to the laptop's server; runs on the hardware-in-the-loop runner or any other machine without the server use offline mode like the Spark. All record their hardware.
- A run tries to record a value that looks like free text from a dataset (a quote, a chunk, a payload): it is refused by the privacy guard.
- Labeling and teacher runs: Claude never appears as a labeler, teacher or judge in any logged run (Principle XI); the logged metadata names the actual models used.
- The tracking store on the laptop is lost: it can be restored from the last backup; the data overview (Stories 1–3) can be rebuilt entirely from the repository and `$MMZ_DATA`, and Spark runs can be synced again from their offline logs.

## Requirements *(mandatory)*

### Functional Requirements

**Data and benchmark overview (Stories 1–2)**

- **FR-001**: The zoo MUST provide one command that lists every active registered third-party dataset of every topic, every frozen training set and every frozen benchmark version, one row per version. Datasets with status `rejected` or `broken_at_source` MUST always be counted and MUST be listed on request.
- **FR-002**: Each row MUST show topic, kind, identifier and version, licence, permitted use, redistribution, size in megabytes, file count, the item counts that fit the kind (rows, chunks, frames, episodes, captures, recordings), the class or label distribution where the source records one, freeze date, content hash, last change date and the models that use it.
- **FR-003**: The overview MUST work from the repository alone; measured values that need downloaded data MUST be marked "not downloaded here" when the data is absent, never guessed.
- **FR-004**: The overview MUST support filtering by topic, kind and permitted use, and MUST offer a machine-readable output with the same content.
- **FR-005**: The zoo MUST show the history of a dataset, training set or benchmark family: each version with freeze date, superseded version, the commit that introduced it, and each register change with date, commit, old and new value.
- **FR-006**: The zoo MUST compare two versions of the same training set or benchmark and show differences in counts, splits, class distribution and hashes.
- **FR-007**: The overview MUST verify the content hash of every frozen benchmark it can check and report any mismatch as an integrity failure.
- **FR-008**: The overview MUST NOT read or print dataset content beyond counting and hashing it.

**Tracking server and configuration (Story 3, all logging)**

- **FR-009**: A private MLflow tracking server MUST run on the owner's laptop, listening on its loopback interface only, not reachable from any network. Nothing of the tracking feature may run as a service on the DGX Spark, and nothing may need a port on the Spark besides SSH.
- **FR-010**: The tracking mode MUST be set only through the environment: `MLFLOW_TRACKING_URI` (from the process or the `.env` file) for live logging on the laptop, and `MMZ_TRACKING_OFFLINE=1` for offline logging, which the Spark scripts set for their training containers. No code, script or configuration file in the repository may hard-code a server address.
- **FR-011**: Without a tracking location, every existing command MUST behave exactly as today; CI and the base install MUST NOT need the tracking software, which ships as a new optional extra.
- **FR-012**: The tracking store MUST be backed up automatically (each time the server stops and before each upgrade, keeping the last 14), and a restore MUST be documented and tested once.
- **FR-013**: Setting up, starting, stopping, updating and restoring the server MUST be documented as owner steps and scripted where possible.

**Data versions in MLflow (Story 3)**

- **FR-014**: The overview MUST be publishable to an experiment for datasets, one entry per dataset or benchmark version, with sizes and distributions as metrics, licence and permitted use as parameters, and identifier, version, freeze date and hash as tags.
- **FR-015**: Publishing MUST be idempotent: an unchanged version (same hash) updates its entry; a changed version creates a new entry; old entries are kept.
- **FR-016**: Publishing MAY attach a profile report per version (distributions, lengths, outliers) that contains only aggregates, never content.

**Run logging (Stories 4–6)**

- **FR-017**: The training, tuning and evaluation commands of every task (JTBD span model, JTBD clustering, CAN intrusion detection, sound anomaly, activity recognition) and the hardware-in-the-loop measurements MUST log to their task's experiment when a tracking location is set.
- **FR-018**: Each run MUST record its configuration (file and values), code commit and whether the tree was clean, hardware, start and end time, status, metrics over time where the run produces them, and final metrics.
- **FR-019**: Each training run MUST record the training set versions and hashes it used; each evaluation run MUST record the frozen benchmark version it was measured on. Measurement runs (speed, memory, on-device checks) record the model version and hardware instead; when they use evaluation data, they also record its hash.
- **FR-020**: Logging MUST never make a run fail or change its results: when the server is unreachable the run continues, its own result files stay complete, and it warns that tracking was incomplete. Offline logging writes only its own log files next to the run's sidecar, never into a folder that is staged or published.
- **FR-021**: Logging MUST add no more than a small, measured overhead to run time (see SC-006).
- **FR-022**: A release record MAY name the run a model version came from; the release gate MUST check the reference's form when present and MUST NOT require it.
- **FR-023**: Model weights MUST NOT be stored in the tracking store; runs reference the trained files by path and hash, and released models by their published revision.

**Privacy, compliance and source of truth**

- **FR-024**: Nothing logged MUST contain dataset text, chunks, quotes, labels, payloads, frames, timestamps lists or personal data. A guard MUST refuse free-text values and artifacts that are not on an allow-list of aggregate kinds.
- **FR-025**: The registers, frozen benchmarks, release records and gate rules MUST stay the only source of truth. No gate, decision or report MUST read its inputs from the tracking store.
- **FR-026**: Claude MUST NOT appear in any logged data work as labeler, teacher, judge or data generator (Principle XI); tracking features that call a language model to judge or label MUST NOT be used with Claude.
- **FR-027**: The compliance register and generated documents (record of processing, privacy notice where relevant) MUST be updated if the tracking store is a new place where processing records are kept.

**Offline runs (Story 4, revised 2026-10-16)**

- **FR-030**: In offline mode a run MUST write everything it would log (the same values, after the same privacy guard) to an append-only log next to its sidecar, without needing the tracking software or a network. A command on the laptop MUST sync offline logs into the store: idempotently, appending only events not yet synced, keeping the run's own start and end times and per-step metrics, and applying the privacy guard again. A script MUST fetch only the offline logs and sidecars from the Spark over SSH.

**History of past work**

- **FR-028**: Historical training and evaluation results that already exist in the repository (`zoo/models/<name>/results/<version>/`, release records, and the run records of frozen benchmarks such as cluster-v1) MUST be importable once into their task's experiment as runs marked "imported". An imported run carries the final metrics, the model version, the benchmark and training set versions it names and the commit of its record; it has no metric curves. Importing again MUST NOT create duplicates. Values missing from a record are left empty, never reconstructed.

**Visibility outside the terminal and MLflow**

- **FR-029**: The overview MUST be available through the command and in MLflow only. No generated overview file is committed to the repository and CI does not maintain one.

### Key Entities

- **Dataset version**: one registered third-party dataset as downloaded; identifier, topic, licence, permitted use, redistribution, approximate and measured size, counts, source hash, register history.
- **Training set version**: one frozen set of rows or chunks built for training; identifier, version, freeze date, hash, counts, split sizes, label distribution, the datasets it was built from.
- **Benchmark version**: one frozen benchmark; identifier, version, task, freeze date, hash, counts, class distribution, the version it supersedes or is based on, the datasets it draws on.
- **Run**: one training, tuning, evaluation or measurement execution; task, configuration, commit, hardware, times, status, metrics, the data and benchmark versions it used.
- **Model version**: as today in the release record; may reference the run it came from.
- **Tracking server**: the private MLflow instance on the owner's laptop with its store and backups.
- **Offline run log**: the append-only record of one run written where no server is reachable (the Spark); synced into the store and kept as a second copy of the run.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The owner can answer "how many datasets and benchmarks do we have, how large is each, and when did each last change" in under one minute, with one command.
- **SC-002**: 100 % of registered datasets and frozen benchmark versions appear in the overview; counts match the frozen manifests exactly.
- **SC-003**: For any benchmark family, the owner can name every version, its freeze date and how it differs from the previous one in under two minutes.
- **SC-004**: The owner can see a running or finished training on the Spark in the laptop's browser, with every epoch completed so far, within two minutes and with one command, without opening a shell on the Spark or reading a log file. Training runs on the laptop show metrics no more than one minute behind.
- **SC-005**: For every run logged after this feature, the training set and benchmark versions it used can be found in one step, in both directions.
- **SC-005a**: Every model version with a results folder or release record appears in MLflow as an imported run, and its final metrics match the repository record exactly.
- **SC-006**: Run-time overhead of logging stays below 2 % on a typical training run; a run with the server down completes with identical result files.
- **SC-007**: A scan of the tracking store finds no dataset text, chunk, label or personal data.
- **SC-008**: With no tracking location set, the full existing test suite and CI pass unchanged, and the base install size does not grow.
- **SC-009**: Restoring the tracking store from backup is done once successfully and takes under 30 minutes.
- **SC-010**: Cash cost of the feature is zero (local compute only).

## Principles touched

**Touched**: III (results name their frozen benchmark), IV (riskiest assumption: logging never harms a run, tested first), V (local only), VI (licence and permitted use visible; no data copied), VIII (comparisons filtered by benchmark version), IX (integrity of frozen benchmarks; release records stay authoritative), XI (no Claude anywhere in logged data work or on the server), Resources & Cost Discipline (no cash cost), Technical Spikes (own experiment, never benchmark results) and Development Workflow & Quality Gates. The plan's Constitution Check states how each is met.

**Not touched**: I, II, VII and X (JTBD extraction behaviour).

## Assumptions

- The owner is the only user; no multi-user permissions are needed. The store is on the owner's laptop; the Spark is reached only through the owner's existing SSH access, as today for training.
- The laptop has enough disk for the tracking store: metrics, parameters, small aggregate reports; no weights (FR-023).
- The backup target is a folder or external drive the owner already has; the plan names the default.
- `$MMZ_DATA` exists on the machines where data is downloaded; the overview runs where the data is, and publishes from there.
- Frozen manifests already hold counts and hashes for benchmarks; frozen training sets have a freeze file with a hash. Datasets whose register lacks counts get measured values only where they are downloaded.
- The datasets overview is a new view on existing facts. It adds no new register fields unless the plan finds a gap (for example a missing hash).
- Cost tier: local compute only (constitution, Resources & Cost Discipline). No cash budget is needed.
- The website and Hugging Face model cards are out of scope; nothing from the tracking store is published.
- Spikes (constitution, Technical Spikes) may log to the same store in their own experiment, labeled "spike", and never count as benchmark results.
