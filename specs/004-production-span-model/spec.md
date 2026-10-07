# Feature Specification: Production span model, first public release

**Feature Branch**: `004-production-span-model`

**Created**: 2026-10-02

**Status**: Draft

**Input**: User description: "Feature 004" — the production span model announced by feature 003: rebuild the fast span model from the spike under the regular constitution rules (non-spike training data from a permitted teacher, evaluation on the frozen benchmark, speed on the low-resource reference hardware) and publish it as the first public model of the zoo through the release pipeline of feature 003.

## Purpose

The spike (feature 002) showed that a small encoder can find jobs, pains and gains fast: it reads a 9,000-character interview in about two seconds on a laptop CPU, its quotes are always verbatim and its output cannot break. That spike model must never be published, because it was trained on spike data and measured against a single reference model on 35 chunks.

This feature builds the same kind of model again, the regular way: training data from the teacher the agreement pilot (feature 001) recommends, drawn only from sources that permit training, evaluation on the frozen benchmark with the same harness as every other model of the JTBD task, and speed and memory measured on the low-resource reference hardware. It then publishes the model as `mobility-model-zoo/scout-large` version `0.1.0`, status "experimental", through the release pipeline built in feature 003.

The feature is done when the model is public on Hugging Face, its page passes the reader test, and the repository is public.

## Clarifications

### Session 2026-10-07

- Q: What is the model called? → A: `scout-large` (owner decision): a short English name for the model family plus its size, under the constitution 1.4.0 naming rule `<name>-<variant>`. Topic (`productdev`) and task (`jtbd`) are fields of the model description and Hugging Face tags; the topic's Hugging Face collection "Product development" lists the model. The earlier working name was `productdev-jtbd-span-xlmr`; code paths (`mobility_model_zoo.productdev.jtbd.span`) and config file names keep their topic layout.

### Session 2026-10-02

- Q: Which quality bar must the span model meet before version 0.1.0 (experimental) is published? → A: It must beat every zero-shot small baseline from the pilot on the composite score on the frozen benchmark and pass every deterministic check. The page reports the numbers honestly, including where the model is weak. The pilot's 85%-of-reference bar is reported as a reference point, not as a release gate.
- Q: What happens if some label dimensions fail the agreement pilot? → A: The model outputs only the dimensions that passed. Dimensions that failed are left out of the output, and the page names them as a limitation. A failed attribute dimension does not block the release.
- Q: How large is the regular training set, and what is the cash budget? → A: About 1,000 training chunks from `training_allowed` sources, with a cash budget of at most €20 for teacher labeling and the reference hardware.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A trained span model with honest, comparable results (Priority: P1)

The project owner builds the span model from regular training data and measures it the same way every JTBD model is measured. The result shows, per dimension, how well the model agrees with the frontier reference on the frozen benchmark, how it compares with the zero-shot small baselines and the teacher, and how fast it is on the reference hardware.

**Why this priority**: Without a regular, measured model there is nothing to publish. This is also the first trained model measured on the frozen benchmark, so it tells the project whether the encoder approach holds up outside the spike.

**Independent Test**: Run the evaluation of the trained model on the frozen benchmark and the speed measurement on the reference hardware. The result lists every passed dimension with a confidence interval, the deterministic-check pass rates, the comparison with every pilot baseline and the teacher, and speed and peak memory, all labeled with the benchmark version.

**Acceptance Scenarios**:

1. **Given** the frozen benchmark and the pilot's recommended teacher, **When** training data is built, **Then** every training chunk comes from a `training_allowed` source that is not used by any benchmark or holdout chunk, and no spike data is included.
2. **Given** the trained model, **When** it is evaluated, **Then** it uses the same benchmark version, reference consensus, matching rules and scoring harness as the pilot baselines, and contested items are reported separately.
3. **Given** the trained model, **When** speed is measured, **Then** throughput, latency and peak memory come from the low-resource reference hardware, with the same model files and settings as the quality run.
4. **Given** decision thresholds (for example the cut-off for "is this unit an item"), **When** they are tuned, **Then** they are tuned on held-out training data only, never on benchmark or holdout chunks.

---

### User Story 2 - The model is public on Hugging Face (Priority: P1)

The project owner tags version `0.1.0` of the span model. The release pipeline from feature 003 checks the release record, builds the model page, waits for approval and publishes. A visitor can install the package, load the published version and run it on their own text on a machine without a GPU.

**Why this priority**: This is the overall goal of features 003 and 004: the first model of the zoo on Hugging Face.

**Independent Test**: After publication, on a clean machine within the stated hardware budget, copy the usage example from the public page, run it on one of the page's example texts and compare the output with the output shown on the page.

**Acceptance Scenarios**:

1. **Given** a trained model that meets the release bar (FR-015), **When** the owner tags `scout-large` `0.1.0` and approves the built page, **Then** the model and its page are public under that version with no manual upload step.
2. **Given** the dry run of the release record, **When** it runs, **Then** every release gate rule passes, including the fields that feature 003's dry run reported as missing.
3. **Given** the public page, **When** a visitor runs the copy-paste example, **Then** it produces output on the example text without a hosted API and without a GPU.
4. **Given** a model that does not meet the release bar, **When** a release is attempted, **Then** nothing is published and the reason is recorded.

---

### User Story 3 - A visitor understands the model's strengths and limits (Priority: P2)

A product manager or researcher reads the model page. They learn what the model finds, in which languages, how well it agrees with the frontier reference, how it compares with small general models and with the generative approach, how fast it is on modest hardware, which dimensions it leaves out and why, and where it fails.

**Why this priority**: The page is what makes the model usable by others; the reader test from feature 003 is run on this page.

**Independent Test**: Run the reader test from feature 003 (`specs/003-model-zoo-hf-release/reader-test.md`) with a person who did not work on the project.

**Acceptance Scenarios**:

1. **Given** the public page, **When** a reader answers the seven fixed questions from the page alone, **Then** at least six answers are correct.
2. **Given** a pilot dimension that failed, **When** the page is read, **Then** the limitations name the missing dimension and the reason.
3. **Given** the quality section, **When** it is read, **Then** every number is described as agreement with the named frontier reference on the named benchmark version, and the model's comparison composite (FR-015) is shown next to the best zero-shot baseline and the teacher.

---

### User Story 4 - The repository is public and the spike code is retired (Priority: P3)

The span model's code lives in the project's regular package for the JTBD task, not in the spike folder, and the GitHub repository becomes public so that the model page's install instruction and training recipe reference work for everyone.

**Why this priority**: Required by feature 003 before the first public model, but it is a one-time step once the model exists.

**Independent Test**: From a machine without access rights, open the repository, follow the recipe reference on the model page to the recipe commit, and install the package with the instruction on the page.

**Acceptance Scenarios**:

1. **Given** the history check from feature 003, **When** it runs right before the repository is made public, **Then** it reports zero findings.
2. **Given** the public repository, **When** a visitor follows the page's recipe reference, **Then** it leads to the commit, configuration and recipe document the model was built with.
3. **Given** the spike folder, **When** the production model is built, **Then** no production code, training run or published file depends on it.

### Edge Cases

- **The pilot is not finished** (benchmark not frozen, no recommended teacher): training data generation does not start. This feature waits; nothing is trained on guesses.
- **The pilot decision is Revise**: the feature uses the benchmark version and guideline version the final decision is based on (for example `pilot-v2`) and states it on the page.
- **The pilot recommends no fit teacher**: the feature stops before data generation and records why. Training on an unfit teacher is not allowed.
- **Relevance or kind fails the pilot**: the model cannot produce its core output. The feature stops and records the reason; the release is not attempted. (Failed attribute dimensions only remove those attributes, see FR-006.)
- **Fewer than about 1,000 suitable training chunks exist in stored `training_allowed` snapshots**: new sources are fetched once under the pilot's provenance rules; if the budget or lawful sources run out first, the actual size is recorded and used; below 600 usable chunks the feature stops before training.
- **The teacher's labels for a chunk fail the schema or the verbatim check**: unverifiable items are repaired or dropped by the pilot's frozen quote-repair rule; chunks without any valid output are excluded and counted.
- **The model does not beat every zero-shot baseline**: it is not published. The result is still reported as a measured, unpublished model.
- **The model does not fit the memory budget on the reference hardware**: it is not published; a smaller or quantized variant is a new decision recorded in the plan, measured again with identical files for quality and speed.
- **Texts longer than one input window, or in neither German nor English**: long texts are read in overlapping windows; other languages are processed but untested, and the page says so.
- **A published file later turns out wrong**: the version is marked deprecated with a reason and fixed in a new version, never overwritten (feature 003).

## Requirements *(mandatory)*

### Dependency on the pilot

- **FR-001**: Training data generation MUST NOT start before the pilot (feature 001) has frozen its benchmark, reached its decision, and named the label dimensions that passed and the recommended teacher.
- **FR-002**: The model MUST be evaluated on the benchmark version the pilot's final decision is based on, with the same consensus, matching rules, deterministic checks and scoring harness as the pilot baselines and teacher candidates.

### Training data

- **FR-003**: Training data MUST be labeled by the teacher the pilot recommends (pilot FR-031a), with the same guideline version and output schema as the benchmark. No benchmark reference model may label training data.
- **FR-004**: Training chunks MUST come only from sources with permitted use `training_allowed`. No source that supplies a benchmark or holdout chunk may supply a training chunk. Spike data MUST NOT be used.
- **FR-005**: The training set MUST contain about 1,000 chunks, cut under the pilot's corpus rules (size, metadata, crawl once). Before labeling, every chunk MUST pass pattern redaction, an automated identifier scan and a review by a local model that lists and removes personal data of private individuals until it finds none (amended 2026-10-06: the owner does no manual review; same procedure as the pilot, 001 research R7). If fewer than 600 usable chunks remain after redaction and teacher labeling, the model MUST NOT be trained, and the outcome is recorded. Stored snapshots MUST be used first; a source is fetched only if it is new. The actual size, its composition by source type, language and sub-area, and the number of excluded chunks MUST be recorded.
- **FR-005a**: Teacher items with a non-verbatim quote MUST be handled with the pilot's frozen quote-repair rule (repaired or dropped), and the repair rate MUST be recorded.
- **FR-005b**: The training set and the teacher's raw outputs MUST have a stated retention period and MUST NOT be published.

### Model

- **FR-006**: The model MUST find items as verbatim sentences or clauses of the input and classify each as job, pain or gain, decide whether the text is relevant at all, and output each attribute dimension (actor type, evidence type, evidence scope) only if that dimension passed the pilot. A dimension that failed MUST be absent from the output, not filled with a guess.
- **FR-007**: The model MUST accept German and English text of any length and MUST return an empty item list as a valid result. It MUST receive no persona or role as input.
- **FR-008**: The model MUST NOT deduplicate, cluster or prioritize items.
- **FR-009**: The memory and hardware budget is: at most 4 GB of RAM at peak while processing a 9,000-character text, on a CPU without a GPU, on the low-resource reference hardware (8 GB RAM, 4 vCPU, no GPU). The model MUST NOT need a network connection or hosted API at runtime.
- **FR-010**: Every decision threshold MUST be tuned on data split off from the training set, never on benchmark or holdout chunks.
- **FR-011**: The model MUST be reproducible from a versioned configuration and a recipe document at a recorded commit; the recipe MUST cover data building, training, threshold tuning, evaluation and staging.
- **FR-012**: The model's code MUST live in the regular package of the JTBD task and MUST provide the loading and extraction interface agreed in the feature 003 hand-over (`specs/003-model-zoo-hf-release/handover-004.md`), so the page's usage example works unchanged. Production code MUST NOT depend on the spike folder.

### Measurement

- **FR-013**: The evaluation MUST report, for every dimension the model outputs: agreement with the frontier consensus with a confidence interval, the contested-item count reported separately, and the deterministic-check pass rates (verbatim quotes, schema validity, internal consistency). It MUST place the model on the task's quality-vs-throughput chart next to the pilot baselines.
- **FR-014**: Throughput, latency per 9,000-character text and peak memory MUST be measured on the low-resource reference hardware, with the same model files and settings as the quality evaluation. Model loading time MUST be reported separately.

### Release

- **FR-015**: The release bar for `0.1.0` is: the model's comparison composite on the frozen benchmark — the composite over exactly the dimensions the model outputs (relevance, item matching, kind and the produced attributes), computed the same way for every compared model — is higher than that of every zero-shot small baseline in the pilot; 100% of quotes are verbatim, 100% of outputs are schema-valid and 100% pass the consistency check; and the budget in FR-009 is met. A model that misses the bar MUST NOT be published.
- **FR-016**: The model MUST be published only through the release pipeline of feature 003, as `mobility-model-zoo/scout-large` version `0.1.0` with status "experimental", after the release gate passes and the owner approves the page.
- **FR-017**: The release record MUST be completed with every field the feature 003 dry run reported as missing: the staged model files with checksums, the recipe commit, configuration and document, the memory budget, the training sources and teacher with their license basis, the quality results and the performance results.
- **FR-018**: The model page MUST state: the benchmark and guideline version; the reference models; the comparison composite (FR-015) of the model next to the best zero-shot baseline, the teacher and the pilot's 85%-of-reference mark; the dimensions left out and why; what the model does not produce compared with the generative approach (free-text actor, English statement); and speed and memory on the reference hardware. Its three example texts MUST show the published model's real output.
- **FR-019**: The GitHub repository MUST be made public before the release is approved, after the feature 003 history check is rerun and reports zero findings.

### Key Entities

- **Training set**: About 1,000 chunks from `training_allowed` sources, labeled by the recommended teacher, with source, language, sub-area, repair counts and retention. Never published.
- **Span model version**: The trained model files, thresholds and configuration for one version, with the dimensions it outputs and the recipe commit it was built from.
- **Evaluation result**: Per-dimension agreement, check pass rates and contested counts on a named benchmark version, plus speed and memory on the reference hardware. The source of every number on the page.
- **Release record**: The feature 003 record for `scout-large` `0.1.0`, completed by this feature.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The span model is publicly available on Hugging Face as version `0.1.0`, published through the release pipeline with zero manual upload steps.
- **SC-002**: On the frozen benchmark, the model's comparison composite (FR-015) is higher than that of every zero-shot small baseline from the pilot, and 100% of its quotes are verbatim and 100% of its outputs are schema-valid.
- **SC-003**: On the low-resource reference hardware, the model processes a 9,000-character text in at most 10 seconds (excluding loading) with peak memory of at most 4 GB.
- **SC-004**: A reader who did not work on the project answers at least 6 of the 7 reader-test questions correctly from the public page alone.
- **SC-005**: The copy-paste usage example on the public page runs on a clean machine without a GPU and reproduces the page's example output: the same items (kind, start, end, attributes) and scores within 1e-4.
- **SC-006**: Zero training chunks come from a source that also supplies a benchmark or holdout chunk, from a `benchmark_only` source or from spike data, as shown by the recorded provenance.
- **SC-007**: Total cash spent by this feature stays at or below €20, as shown by the recorded costs.
- **SC-008**: Every number on the public page traces to a stored evaluation result for version `0.1.0`.

## Assumptions

- The model architecture is the one from the spike: a multilingual encoder (XLM-RoBERTa-large, MIT) that classifies sentences and clauses, with heads for relevance, kind and the attributes. Spike measurements guide the design but set no rule, threshold or criterion of this feature (constitution, Technical Spikes).
- The low-resource reference hardware is the one defined by the pilot: a rented VM with 8 GB RAM, 4 vCPU and no GPU, deleted after measurement. Its cost counts against the €20 budget.
- Cost order: the teacher runs locally if the pilot recommends a local model; otherwise through OpenRouter under a key with a hard limit at or below the budget. Training runs on the DGX Spark or the MacBook at no cash cost.
- The budget of €20 is separate from the pilot's €20 budget.
- The release pipeline, release record format, model page standard and history check from feature 003 are used unchanged. A format gap found here is fixed in feature 003's tooling as a patch, not worked around.
- The try-it field, integration with automation tools and the generative 4B model remain out of scope.
- Retention for the training set and teacher outputs follows the pilot: kept while the model version is current, reviewed for deletion no later than 24 months after the training data is frozen.
- The pilot's holdout chunks stay unused here; they remain reserved for the pilot's own rerun and later benchmark versions.

## Constitution Compliance

- **I. Problem-first**: The model receives only the text, no persona (FR-007); actor type is extracted, not supplied.
- **II. Grounded evidence**: Items are verbatim spans of the input; empty results are valid (FR-006, FR-007).
- **III. Measure before optimizing**: Same frozen benchmark, consensus, contested-item report, deterministic checks and quality-vs-throughput chart as the pilot (FR-002, FR-013). Numbers are agreement with frontier models (FR-018). Benchmark labelers do not make training data (FR-003).
- **IV. Validate the riskiest assumption first**: Data generation waits for the pilot, and only passed dimensions are trained and output (FR-001, FR-006). The release bar is written down before training (FR-015).
- **V. Small and local**: Concrete budget of 4 GB RAM, CPU only, on the reference hardware; no runtime API (FR-009, FR-014).
- **VI. Clean provenance**: `training_allowed` sources only, teacher license checked, redaction of every chunk with model-assisted review (FR-005), crawl once, stated retention, no published data (FR-003 to FR-005b).
- **VII. Metadata over inference**: The model predicts no attribute available as collection metadata (language, source type, region, date).
- **VIII. Fair architecture comparison**: Same benchmark version and harness as every other JTBD model (FR-002). Ludwig is the primary framework; the encoder span model needs custom heads, so any deviation must be justified in the plan.
- **IX. Reproducible, dated releases**: Versioned recipe at a recorded commit, immutable version, release only through the pipeline with owner approval (FR-011, FR-016, FR-017).
- **X. Scope discipline**: No deduplication, clustering or prioritization (FR-008).
- **Technical Spikes**: No spike data, model or result is reused or published; spike code is retired from production (FR-004, FR-012).
- **Resources & Cost Discipline**: Local first, €20 cash budget with a hard key limit, development and reference hardware kept apart (FR-014, SC-007).
