# Feature Specification: Mobility model zoo with versioned Hugging Face releases

**Feature Branch**: `003-model-zoo-hf-release`

**Created**: 2026-10-01

**Status**: Draft

**Input**: User description: "Rename the project sensibly. It becomes a collection of ML/AI models in the mobility domain with different topics. This one (JTBD extraction) is product development, but technical models can be added, for example cyber security or IoT models. A 'Mobility Model Zoo' or similar. All models get versions, and CI/CD uploads them, probably to Hugging Face first. Easier integration via n8n or similar comes later. The quality of the release must be very good: description, quality metrics, maybe an input field to try it. We are successful when the first model has landed on Hugging Face."

## Purpose

The project today is a single JTBD extraction engine. It becomes a collection of mobility models, grouped by topic. The JTBD extraction models are the first topic, "product development". Later topics (for example cyber security or IoT) can be added without restructuring the project.

Every model in the collection is versioned and published to Hugging Face by an automated release pipeline. A published model page is complete enough that a visitor can understand what the model does, how good it is, where it fails, and how to run it. A try-it field in the browser follows in a later feature.

The first model is a production version of the fast span model from the spike: an encoder that classifies sentences and clauses as job, pain or gain with actor type and evidence grade, in under one second per interview on a laptop. The spike model itself is not published. Building the production span model is a separate feature (004), because it depends on the agreement pilot (001).

This feature delivers everything the release needs except the model: the rename, the zoo structure, the release record, the model page standard and the release pipeline. It is done when the pipeline has published a test model end to end to a non-public sandbox repository, and when a dry run on the span model's draft release record reports as missing only the fields that feature 004 delivers. The overall goal, the first model on Hugging Face, is reached when feature 004 hands its production span model to this pipeline.

## Clarifications

### Session 2026-10-01

- Q: Which model is released first, given that both existing models are spike models and spike models must not be released? → A: The small, fast span model. The spike artifact is not released; a production version is built first under the regular constitution rules. The constitution's ban on releasing spike models stays.
- Q: What is the new project name? → A: `mobility-model-zoo`.
- Q: Which Hugging Face namespace? → A: A dedicated Hugging Face organization named after the project.
- Q: Which form does the try-it field take in the first release? → A: A free CPU Hugging Face Space for the span model, with a text field and example texts. (Superseded during planning, see below.)
- Q: Does making the span model production-ready stay in this feature? → A: No. It becomes feature 004. This feature (003) covers rename, zoo structure, release record, model page standard and release pipeline with dry run; the first real publication happens when 004 delivers the model.
- Q: How is a release triggered, and does a public release need approval? → A: A version tag per model starts the pipeline. Checks and the dry run run automatically; the pipeline then shows the built model page and waits for the owner's explicit approval before publishing.
- Q: Where does the pipeline get the model files, which are trained on the DGX Spark or locally and are not in the repository? → A: The training run uploads the finished files to a private staging repository in the Hugging Face organization and records their checksums in the release record. The pipeline fetches them from staging, verifies the checksums and publishes.
- Q: How are models named on Hugging Face? → A: `<topic>-<task>-<variant>` under the organization, for example `mobility-model-zoo/productdev-jtbd-span-xlmr`.
- Q: Which version and status does the first public model get? → A: `0.1.0`, status "experimental". Below 1.0 the output format may still change; `1.0.0` comes only when format and quality are stable.
- Q (during planning): Does the private GitHub repository become public? → A: Yes, before the first public model (feature 004), after a check that no data, keys or raw text are in the git history. It stays private during this feature.
- Q (during planning): Which license? → A: Apache-2.0 for code and models.
- Q (during planning): Does the PoC tool `pilot` keep its name? → A: No, it becomes `jtbd`. Tooling is per task (shared by all models of that task); releasing is common to all models (`zoo`).
- Q (during planning): How is the try-it field hosted, now that free Hugging Face organizations can no longer run Gradio or Docker Spaces? → A: The try-it field is deferred to a later feature. The first release has the model page and a copy-paste usage example, but no input field.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - First model published on Hugging Face through the pipeline (Priority: P1)

The project owner creates a version tag for one model. The release pipeline checks that the release is complete, builds the model package and the model page, and shows the page for review. After the owner approves, it publishes both to Hugging Face under that version. The owner did not upload anything by hand.

**Why this priority**: This is the stated success criterion. It proves the whole chain from repository to public model page.

**Independent Test**: Within this feature: trigger a release of a small test model to a non-public sandbox repository in the organization, then open its page and download the published version by its version identifier. With feature 004: the same for the production span model, publicly.

**Acceptance Scenarios**:

1. **Given** a model with a complete release record, **When** the owner tags version `X` and approves the built page, **Then** the model files and the model page appear on Hugging Face under version `X` without manual upload steps.
2. **Given** a release record with a missing required part (for example no evaluation results or no license), **When** the release is triggered, **Then** the pipeline stops before uploading anything and names the missing part.
3. **Given** version `X` is already published, **When** a release for version `X` is triggered again, **Then** the pipeline refuses and the published version stays unchanged.
4. **Given** a release is triggered, **When** the pipeline runs, **Then** no training data, raw source text or credentials are uploaded.
5. **Given** the checks have passed and the page is built, **When** the owner has not approved yet or rejects, **Then** nothing is published, and a rejected version can be fixed and tagged as a new version.

---

### User Story 2 - A visitor understands and trusts the model from its page (Priority: P1)

A product manager or researcher finds the model on Hugging Face. From the page alone they learn what the model does, which topic it belongs to, which languages and inputs it handles, how good it is (with the reference it was measured against), how fast it is on which hardware, its known limits, its license and how to run it.

**Why this priority**: The user asked for very good release quality. A model without a trustworthy page is not usable by others.

**Independent Test**: Give the published page to someone who did not work on the project. They answer a fixed set of questions (what it does, input language, quality and against what, speed and on which hardware, main limitations, license, how to run it) from the page alone.

**Acceptance Scenarios**:

1. **Given** a published model, **When** a visitor opens its page, **Then** the page contains every section of the model page standard (FR-010).
2. **Given** a published model, **When** a visitor reads the quality section, **Then** each number states what it measures, the reference it was measured against, the evaluation set and its size, and the date.
3. **Given** a model with status "experimental", **When** the page is shown, **Then** the status and what it means are visible at the top of the page.
4. **Given** the page's usage example, **When** a visitor copies and runs it, **Then** it produces output on the example text.

---

### User Story 3 - The collection is named and structured as a model zoo (Priority: P2)

The project is renamed to `mobility-model-zoo`. The repository, the documentation and the Hugging Face presence use the new name. Each model belongs to exactly one topic, and the overview lists all models with topic, task, current version and status.

**Why this priority**: The name and structure must be fixed before the first public release, because published names are hard to change later.

**Independent Test**: Read the repository overview and the Hugging Face collection page. Both use the new name, list the first model under the topic "product development", and show how a new topic would be added.

**Acceptance Scenarios**:

1. **Given** the renamed project, **When** a reader opens the repository overview, **Then** it explains the zoo, lists the topics and lists every model with topic, task, current version and status.
2. **Given** a new model in a new topic (for example IoT), **When** it is added, **Then** it follows the same release record, model page standard and release pipeline without changes to the existing models.
3. **Given** the Hugging Face presence, **When** a visitor opens it, **Then** published models are grouped by topic.

---

### User Story 4 - A new version replaces an old one without breaking users (Priority: P3)

The owner publishes version 2 of a model. Users who pinned version 1 still get version 1. The page shows a changelog with what changed and how the quality numbers moved.

**Why this priority**: Versioning is required for every model, but it only matters once there is a second version.

**Independent Test**: Publish two versions of a test model and download each by its version identifier; check the changelog on the page.

**Acceptance Scenarios**:

1. **Given** versions 1 and 2 are published, **When** a user requests version 1, **Then** they get exactly the files of version 1.
2. **Given** version 2 is published, **When** a visitor opens the page, **Then** the changelog lists version 2 with its date, what changed and its quality numbers next to those of version 1.

### Edge Cases

- **The release record is incomplete or inconsistent** (for example the version in the record differs from the triggered version): the pipeline stops before uploading and reports the reason.
- **Hugging Face is unreachable or rejects the upload halfway:** the version is either fully published or not at all from a user's point of view; a retry of the same version completes it without producing a second, different version.
- **The staged model files do not match the checksums in the release record, or are missing:** the pipeline stops before publishing and names the mismatching files.
- **The upload credential is missing or expired:** the pipeline fails with a clear message and nothing is published.
- **A model's license or its teachers' terms do not permit publication:** the release gate blocks it.
- **A published version later turns out to be broken:** it is marked as deprecated on its page with the reason; it is not silently overwritten or deleted.

## Requirements *(mandatory)*

### Naming and structure

- **FR-001**: The project MUST be renamed to `mobility-model-zoo`. The name MUST be used consistently in the repository, the documentation, the package name and the Hugging Face presence. The proof-of-concept tool `pilot` MUST be renamed to `jtbd`, the tool for the JTBD task, shared by every JTBD model. Models MUST be published under a dedicated Hugging Face organization named after the project.
- **FR-002**: The constitution MUST be amended so that its scope covers a collection of models in several topics. The current JTBD extraction rules MUST remain in force for the product development topic. Rules that apply to every model (versioning, provenance, release gate, small and local by default) MUST be stated for the whole zoo.
- **FR-003**: Each model MUST belong to exactly one topic. The first topic is "product development" (short form `productdev`); the topic list MUST be extendable without changing existing models. Each topic MUST have a fixed short form used in model names.
- **FR-003a**: Every model MUST be named `<topic>-<task>-<variant>` in lowercase with hyphens, for example `productdev-jtbd-span-xlmr`. The name is used for the Hugging Face repository, the version tag and the release record, and MUST NOT change after the first publication. The pipeline MUST refuse a release whose name does not follow the scheme or whose topic short form is unknown.
- **FR-003b**: The repository MUST carry an Apache-2.0 license file, and every published model MUST be licensed Apache-2.0 unless its base model or teacher terms require otherwise; the release gate MUST check this.
- **FR-003c**: The repository MUST become public before the first public model release. Before that, a check MUST confirm that the full git history contains no data files, raw source text, labeling outputs or credentials.
- **FR-004**: The repository MUST contain an overview listing every model with topic, task, current version, status (FR-005a) and a link to its Hugging Face page.

### Versioning and release record

- **FR-005**: Every model MUST have a version identifier that follows semantic versioning. Each version MUST be dated. For models: a change to the output format is a major change (from 1.0.0 on), a retrained model or a quality change is a minor change, and a change to the model page or packaging only is a patch. Below 1.0.0 the output format MAY change in a minor version, and the page MUST say so.
- **FR-005a**: Statuses are "experimental" (below 1.0.0, output format may change), "released" (1.0.0 or later) and "deprecated" (with a reason and a pointer to the successor). A version below 1.0.0 MUST have status "experimental".
- **FR-006**: Every model version MUST have a release record in the repository that, together with the model's description file, contains at least: model name, topic, version, date, task, base model, license, location of the model files in the private staging repository with a checksum per file, training recipe reference, data provenance summary (origin and license of sources, without the data itself), evaluation results with reference and evaluation set, speed and memory on the stated reference hardware, known limitations, and status.
- **FR-006a**: Model files MUST reach the pipeline only through a private staging repository in the Hugging Face organization. Staging repositories MUST NOT be public and MUST NOT contain training data.
- **FR-007**: A published version MUST be immutable. Re-publishing an existing version MUST be refused. A fix MUST be published as a new version.
- **FR-008**: Each published version MUST be retrievable by its version identifier, and the latest version MUST be what a user gets by default.

### Release pipeline

- **FR-009**: Publishing MUST happen through an automated pipeline started by a version tag for one model in the repository, not by manual upload. The tag MUST identify the model and the version. The pipeline MUST:
  - check the release record for completeness and consistency,
  - fetch the model files from the private staging repository and verify them against the checksums in the release record,
  - check the constitution's release gate (reproducible from versioned configuration, recorded origin and license of every source, teacher terms permit training on outputs),
  - build the model package and the model page from the release record,
  - show the built page and wait for the owner's explicit approval,
  - publish both under the version only after approval,
  - and stop before uploading anything if any check fails or approval is not given.
- **FR-010**: Every model page MUST contain these sections, generated from the release record: summary; topic and task; intended use and out-of-scope use; input and output format with an example; how to run it (copy-paste example); quality results with reference, evaluation set, size and date; speed and memory with the hardware; limitations and risks; training data provenance (summary, no data); training recipe reference; license; version history; citation. The page MUST also carry machine-readable metadata for license, languages, task, base model, tags (including the topic) and evaluation results, so that Hugging Face search and filters work.
- **FR-011**: The pipeline MUST NOT upload training data, raw source text, labeling outputs or credentials. Only model files, the model page and files needed to run the model MAY be published.
- **FR-012**: The upload credential MUST be stored as a secret of the pipeline and MUST NOT appear in the repository or in logs. Training machines that write to staging MUST use a separate credential that can write only to the listed staging repositories and cannot create repositories or publish to public ones. Staging repositories are created with the release credential.
- **FR-013**: The pipeline MUST offer a dry run that performs every check and builds the package and page without publishing, so the page can be reviewed before release.

### Quality and honesty of published results

- **FR-014**: Quality numbers on the page MUST be described as agreement with the named reference models, not as accuracy against human ground truth (constitution Principle III).
- **FR-015**: Spike models and spike results MUST NOT be published (constitution, Technical Spikes). Every published model MUST carry its status (FR-005a), shown at the top of its page with what it means for users.
- **FR-016**: Every published number MUST be traceable to a stored evaluation result in the repository for that version.

### First release

- **FR-017**: The first public model MUST be the production span model from feature 004 in the product development topic, published as version `0.1.0` with status "experimental".
- **FR-018**: The model page of the first model MUST include at least three example texts without personal data, each with the model's output, so visitors see real behavior without running it. A try-it field is out of scope for this feature.

### Hand-over from feature 004

- **FR-019**: The release record format MUST let feature 004 describe the production span model completely, including its memory and hardware budget, speed and peak memory measured on the low-resource reference hardware, the frozen benchmark version of its results, and what it does not produce compared to the generative approach (free-text actor and English statement).
- **FR-020**: Before feature 004 is complete, a dry run on a draft release record for the span model MUST report as missing only the fields that feature 004 delivers (staged files, results, recipe), so that format gaps are found before the real release.
- **FR-021**: The pipeline MUST be tested end to end by publishing a small test model to a non-public sandbox repository in the organization. The test model MUST NOT be a spike model and MUST NOT be made public.

### Key Entities

- **Topic**: A thematic area of the zoo (product development, later for example cyber security or IoT). Has a name, a short description and a list of models.
- **Model**: A named model in the zoo. Belongs to one topic, has a task, a license and a list of versions.
- **Model version**: One immutable published state of a model. Has a version identifier, date, status, model files, release record and model page.
- **Release record**: The versioned, human-readable description of a model version in the repository, from which the model page and machine-readable metadata are built.
- **Model page**: The public description on Hugging Face, generated from the release record.
- **Staging repository**: A private repository in the Hugging Face organization where a training run places the finished model files for a version, before release.
- **Release pipeline**: The automated process that checks, builds and publishes a model version.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The test model is published to the sandbox repository under a version identifier through the release pipeline with zero manual upload steps, and the dry run for the span model's draft release record reports as missing only the fields that feature 004 delivers. (Overall goal, reached with feature 004: the production span model is published publicly the same way.)
- **SC-002**: The published model page contains 100% of the sections required by FR-010, and its machine-readable metadata passes Hugging Face's own metadata validation without warnings.
- **SC-003**: A reader who did not work on the project answers at least 6 of 7 fixed questions (what it does, input language, quality and against what, speed and on which hardware, main limitations, license, how to run it) correctly from the page alone.
- **SC-004**: The copy-paste usage example on the page runs successfully on a clean machine that meets the stated hardware budget.
- **SC-005**: A release with a deliberately removed required field is blocked by the pipeline in 100% of test runs, and nothing is uploaded.
- **SC-006**: Re-triggering a release for an already published version leaves that version byte-identical.
- **SC-007**: From the owner's approval to the version being visible on Hugging Face takes under 30 minutes.
- **SC-008**: Every number on the published page can be traced to a stored evaluation result in the repository.

## Assumptions

- Hugging Face is the only publication target in this feature. A try-it field, integration with automation tools such as n8n, hosted inference APIs and other registries are out of scope and follow in later features.
- The release pipeline runs on the repository's existing hosting (GitHub) and uses its built-in automation and secret storage.
- Models are published publicly, consistent with the constitution: the model, method, prompts and evaluation results are published; datasets are not.
- The model license follows the base model and teacher terms; the current base models (Qwen3-4B-Instruct-2507, XLM-RoBERTa-large) are Apache 2.0 and MIT, which permit publication.
- The cash budget for this feature is €0. A try-it field is out of scope: free Hugging Face organizations cannot host Gradio or Docker Spaces (checked 2026-10-01); the hosting options are compared in research.md for the later feature. The training data budget belongs to feature 004.
- Renaming the GitHub repository keeps redirects from the old name, so existing links keep working.
- Feature 004 (production span model) depends on feature 001: the benchmark must be frozen and the agreement pilot passed before regular training data is generated. It moves the span code out of the spike folder, trains on non-spike data from permitted teachers, and evaluates against the frozen benchmark on the low-resource reference hardware. Its spec is written separately.
- The generative 4B model is not part of this feature. It can follow later as a second model in the zoo.
- The quality bar "very good" is made concrete by the model page standard (FR-010) and SC-002 to SC-004, based on Hugging Face's model card guidance (model card sections, metadata, evaluation results, limitations).

## Constitution Compliance

- **Principle III (Measure before optimizing)**: Published numbers are labeled as agreement with named reference models (FR-014) and are traceable (FR-016).
- **Principle V (Small and local)**: Each model page states memory and hardware (FR-010); the usage example runs locally without hosted APIs (SC-004).
- **Principle VI (Clean provenance)**: Datasets are not published (FR-011); the page includes a provenance summary only; teacher terms are checked by the release gate (FR-009).
- **Principle IX (Reproducible, dated releases)**: Semantic versions, dates, immutability and the release gate (FR-005 to FR-009).
- **Technical Spikes**: Spike models and spike results are not released (FR-015). The pipeline test uses a non-spike test model in a non-public sandbox (FR-021).
- **Principles IV and VIII**: Training data generation and the fair comparison for the span model are handled in feature 004.
- **Project Scope**: Broadening the scope to a multi-topic zoo requires a constitution amendment (FR-002).
