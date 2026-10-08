<!--
Sync Impact Report
==================
Version change: 1.4.0 → 2.0.0
Bump rationale: MAJOR. Owner directions of 2026-10-08, made while merging the automotive security
work (feature 005) into the zoo. Three rules are removed or redefined in a way that is not backward
compatible:
- Principle VIII no longer makes Ludwig the primary training framework. Tools follow the task.
- Principles VI and IX no longer forbid publishing datasets outright. The rule now keeps datasets
  out of the git repository and allows publication only after a redistribution check.
- Principle V no longer fixes one universal budget ("little RAM, no dedicated GPU"). Each task
  defines its own budgets and reference hardware.
The ban on calling results "accuracy" is replaced by an honesty rule on metric naming that applies
to every task.

Modified principles:
- Scope note (before I): split into model-labeled tasks and ground-truth tasks.
- III. Measure Before Optimizing: reference per task; metric naming rule; frontier consensus only
  for model-labeled tasks; quality-vs-cost reporting uses the task's budgets.
- IV. Validate the Riskiest Assumption First: agreement pilot applies to model-labeled tasks.
- V. Small and Local by Default → V. Small and Local by Default, Budgets per Task.
- VI. Clean Provenance, Quality First: dataset declarations, redistribution check, share-alike and
  non-commercial rules; datasets stored outside the git repository.
- VIII. Fair Architecture Comparison: Ludwig rule removed; tool choice per task.
- IX. Reproducible, Dated Releases: raw-label retention for model-labeled tasks; dataset
  publication only after the redistribution check.

Modified sections:
- Preamble: topics security and condition monitoring named.
- Project Scope & Iterative Delivery: repository layout by topic.
- Resources & Cost Discipline: CI runners and hardware-in-the-loop bench boards added; "target
  hardware" generalised.
- Development Workflow & Quality Gates: "gate before reporting a result" per reference kind;
  "gate before a release" mentions dataset declarations.

Added sections: none (layout rule added to Project Scope).
Removed sections: none.

Previous reports: 1.3.0 → 1.4.0 changed model naming to `<name>-<variant>` with one Hugging Face
collection per topic; 1.2.0 → 1.3.0 made the project the multi-topic `mobility-model-zoo`, added
release rules to IX and the section "Tasks and Releases".

Templates reviewed (not modified; they read the constitution at runtime and quote none of the
changed rules):
- .specify/templates/plan-template.md ✅
- .specify/templates/spec-template.md ✅
- .specify/templates/tasks-template.md ✅

Follow-up (code that encodes rules changed here; handled by feature 005):
- release gate rule 10 and results.schema.json ban the word "accuracy";
- release-record.schema.json fixes `budget{ram_gb, gpu: false}`;
- the model card template has fixed "no GPU" and "source texts" wording.
-->

# mobility-model-zoo Constitution

An open-source collection of small, fast machine learning models for mobility, grouped by topic.
Each model solves one task, runs locally and is released with a versioned, honest model card.

The first topic is product development (`productdev`). Its first task is an extraction engine for
a problem discovery framework: it extracts jobs-to-be-done, pains and gains with graded evidence
from heterogeneous texts (papers, forums, reviews, chats). Further topics add their own tasks, for
example automotive security (`security`) and condition monitoring (`condition-monitoring`) with
models that run on microcontrollers.

## Core Principles

Scope of the principles: Principles I, II, VII and X are written for the JTBD extraction task and
apply to every model of that task. Every other principle, and every section below the principles,
applies to every model in the zoo.

Tasks differ in their quality reference:

- A **model-labeled task** has no ground truth; its reference is a benchmark labeled by reference
  models (today the JTBD task, labeled by frontier models). The rules marked "model-labeled tasks"
  apply to it.
- A **ground-truth task** has labels that come with its data (for example a dataset with recorded
  attacks or recorded faults). Its reference is the labels of named, frozen datasets.

Every task names its reference in its first spec or task document.

### I. Problem-First, Not Persona-First

- The model MUST receive a problem domain as input and MUST NOT receive a persona, user
  segment or role description.
- Actors (who has the job, pain or gain) MUST be extracted as output fields grounded in the
  source text, never supplied as input.
- Personas MUST NOT be defined upstream of extraction; they emerge downstream through
  clustering of extracted items.

Rationale: Feeding a persona biases extraction toward what that persona is assumed to need
and hides actors nobody anticipated. Discovery starts from the problem.

### II. Grounded Evidence over Plausibility

- Every extracted item (job, pain, gain, actor) MUST carry at least one verbatim quote from
  the source text that supports it. Items without a verbatim quote are invalid.
- Evidence grades MUST reflect how directly the text supports the claim, not how plausible
  or common the claim is in general.
- When the grade is uncertain, the lower grade MUST be assigned.
- An empty result MUST be accepted as a valid, correct output. Neither prompts, training
  data nor metrics may penalize a correct empty result or reward filling it.

Rationale: The downstream framework prioritizes problems by evidence. A plausible but
ungrounded item is worse than no item, because it looks like evidence and is not.

### III. Measure Before Optimizing

- Every task MUST have a fixed, frozen quality reference: the labels of named datasets for
  ground-truth tasks, a consensus benchmark for model-labeled tasks.
- Model-labeled tasks: the benchmark MUST be labeled independently by at least two frontier
  models from different model families. No benchmark labeling model may be used to generate
  training data. Items on which the labeling models do not agree MUST be marked as contested and
  reported separately; they MUST NOT be silently dropped or merged into the consensus score.
- Ground-truth tasks: test data MUST NOT be used for training, threshold tuning or model
  selection, and the split MUST be frozen before it is first used for a result.
- Deterministic checks MUST run independently of any model judgment and be reported on their own
  (for example verbatim-quote match, schema validity, internal consistency, or bit-exact agreement
  between the deployed numeric format and its host reference).
- Every change to model, prompt, data or pipeline MUST be evaluated on both quality and the
  budgets of its task (Principle V), and results MUST be reported as a quality-vs-cost Pareto
  front where more than one candidate exists.
- Metric naming: use the metric that is needed or useful, including accuracy. Every reported
  metric MUST state what it is measured against (dataset labels, consensus of named reference
  models, or human review), and its name MUST NOT suggest more than that reference supports.
  Agreement with reference models is reported as agreement, not as accuracy.

Rationale: Without a fixed reference and honest labeling of what that reference is,
improvements cannot be told apart from noise or from overfitting to one model's taste.

### IV. Validate the Riskiest Assumption First

- Model-labeled tasks: before any large-scale data generation, a pilot MUST measure
  inter-model agreement between the benchmark labeling models on every label dimension. If the
  labeling models cannot reach agreement on a label dimension, that dimension's definition MUST
  be revised and re-piloted before training on it begins.
- Every task MUST name its riskiest assumption in its first spec (for example that the labels of
  a dataset transfer to unseen vehicles) and test it before scaling up.
- Success criteria and kill criteria MUST be written down before an experiment starts and
  MUST NOT be changed after results are seen without a documented rationale.

Rationale: If frontier models cannot agree on a label, a small model cannot learn it and
the benchmark cannot measure it. Finding that out after generating data wastes the budget.

### V. Small and Local by Default, Budgets per Task

- Models are small and run locally by default. Hosted APIs MAY be used for data generation and
  evaluation. Hosted APIs MUST NOT be a runtime dependency of any model in the zoo.
- Each task MUST define the budgets that matter for its target and problem (for example memory,
  flash, compute, latency, throughput, energy, cash per run, hardware class) and MUST name its
  reference hardware. Each spec that introduces or changes a model MUST state its concrete
  budget values.
- Budgets MUST be measured on the reference hardware or, where that is not available, on a named
  substitute. Every measurement MUST record its origin: real target hardware, emulator or
  simulator. Results from an emulator or simulator MUST NOT be presented as hardware results.

Rationale: The models are meant to run where the problem is, cheaply, on private data, without
a network dependency or per-call cost. What "small" means depends on the target: a laptop CPU for
text extraction, a microcontroller for a CAN bus monitor.

### VI. Clean Provenance, Quality First

- Source selection is driven by data quality, not volume.
- Only sources that may lawfully be used for text and data mining or training MAY be included.
  Machine-readable opt-outs MUST be respected and platform access terms MUST be followed.
- Every source and every dataset MUST record its origin and license. Datasets are declared per
  topic with license, permitted use (`training_allowed` or `benchmark_only`), redistribution
  (`allowed`, `not_allowed` or `unclear`), commercial use and retention period.
- A source or dataset under a non-commercial license MUST be `benchmark_only`. A `benchmark_only`
  source MUST NOT enter training data.
- Share-alike terms of training data carry over: a model trained on share-alike data MUST be
  released under a compatible license.
- Personal data MUST be minimized: usernames and direct identifiers MUST be removed before
  labeling. Raw data MUST be retained only as long as needed, and the retention period
  MUST be stated for each dataset and each snapshot store. "Needed" includes reuse of raw
  snapshots in later iterations (see Resources & Cost Discipline).
- A teacher model MAY be used only if its license and provider terms permit training other
  models on its outputs.
- Datasets MUST NOT be stored in the git repository. They live in separate storage: a local
  cache, an object store or Hugging Face dataset repositories.
- A dataset MAY be published (including third-party data, for example as a curated data
  compendium) only if its declaration says `redistribution: allowed` after its license and terms
  were checked, with attribution as the license requires, and only if it contains no personal
  data beyond what was already lawfully public and redacted. Texts collected under text and data
  mining rules (the JTBD sources) are `not_allowed`.

Rationale: An open-source model is only usable by others if its training inputs were
lawfully obtained and handled with respect for the people who wrote them. Keeping data out of git
keeps the repository small; checking redistribution first keeps publication lawful.

### VII. Metadata over Inference

- Anything knowable at collection time (region, source type, date, language, and similar
  attributes) MUST be stored as metadata on the source record.
- The model MUST NOT be asked to predict attributes that are available as metadata.

Rationale: Collected facts are exact and free; inferred ones are noisy and cost model
capacity that belongs to the extraction task.

### VIII. Fair Architecture Comparison

- Every approach for a task MUST be evaluated with the same benchmark version and the same
  evaluation harness.
- Tools follow the task: each task chooses the training framework and tooling best suited to
  its problem and states the choice and the reason in its first spec or task document.

Rationale: Architecture decisions are only meaningful when every candidate is measured the
same way. A fixed framework would force the wrong tool onto some tasks.

### IX. Reproducible, Dated Releases

- Every model, dataset and benchmark MUST be versioned and reproducible from configuration.
- A benchmark version MUST be frozen once it has been used for an evaluation. Changes
  produce a new benchmark version.
- Model-labeled tasks: raw labels from every labeling model MUST be retained together with the
  model identifier, model version and labeling date, so that later human review can measure both
  our models and the benchmark itself.
- Releases are dated snapshots with no maintenance promise.
- Retraining on a new base model MUST follow a documented, repeatable recipe.
- A published model version MUST be immutable. A fix is a new version; a broken version is
  marked deprecated, never silently overwritten or deleted.
- Models MUST be published only through the release pipeline, after its release gate passes and
  after the project owner approves the reviewed model card.
- Training data, raw source text and labeling outputs MUST NOT be published. Datasets follow
  Principle VI: published only with `redistribution: allowed`, versioned and with attribution.

Rationale: Frontier models and base models change quickly. Frozen, dated artifacts keep
results comparable and let the benchmark itself be audited later.

### X. Scope Discipline

- The model extracts. It MUST NOT deduplicate, cluster or prioritize.
- Deduplication, clustering (including persona formation) and prioritization are separate
  downstream stages and MUST NOT be folded into the extraction model or its training
  objective.

Rationale: A narrow task is what makes a small, fast model feasible and measurable.

## Project Scope & Iterative Delivery

- The zoo is organized in topics. Each model belongs to exactly one topic. A model is named
  `<name>-<variant>`: a short, memorable English name for the model family and a size or
  variant (for example `scout-large`). Topic and task are recorded in the model description,
  published as Hugging Face tags, and every topic has one Hugging Face collection that lists its
  models. Names never change after the first publication. A new topic MUST NOT require changes
  to existing models.
- Repository layout: one topic is one Hugging Face collection and one folder `topics/<topic>/`
  that holds everything of that topic that is not package code or configuration (research,
  dataset declarations, reports, recipes and topic-specific material). Package code lives in
  `src/mobility_model_zoo/<topic>/<task>/`, configuration in `configs/<topic>/<task>/`. The top
  level of the repository only holds material shared by all topics.
- The project proceeds iteratively: each iteration starts with the simplest setup that
  yields measurable results, then improves step by step.
- Each iteration MUST produce a measurable result against the current frozen benchmark
  before the next layer of complexity is added.
- JTBD extraction task, in scope: extraction of jobs-to-be-done, pains, gains and actors, each
  with verbatim evidence and an evidence grade, from heterogeneous texts in a given problem
  domain.
- JTBD extraction task, out of scope: deduplication, clustering, persona building,
  prioritization, and any attribute available as collection metadata.
- Mobility is the first domain. Domain-specific choices MUST be isolated in configuration,
  prompts or data so that later domains do not require changes to the engine.
- Every new task MUST define its scope (in and out) in its first spec.

## Tasks and Releases

- How a model is built and measured belongs to its task. Each task has one build-and-measure
  tool (for JTBD extraction: `jtbd`), shared by every model of that task, so that all models of a
  task use the same benchmark version and the same evaluation harness (Principle VIII).
- How a model is released is the same for every model, whatever its task: one release record per
  version in the repository, one release gate (`zoo check`) and one release pipeline.
- Code shared between tasks is extracted into a common module only when a second task needs it,
  not in advance.

Rationale: Tasks differ in data, references and metrics, so a single build pipeline for all of
them would be the wrong abstraction. Releases must look the same everywhere, because that is what
users of the zoo rely on.

## Resources & Cost Discipline

- Resource inventory (as of 2026-10-08; updated by PATCH amendment):
  - A DGX Spark with 128 GB unified memory: local compute for teacher runs, data
    generation, training and quality evaluation.
  - A Claude subscription (flat rate): Claude labeling within the provider's terms.
  - An OpenRouter account (pay-per-use): only for models that are available neither
    locally nor through the subscription.
  - GitHub CI runners: unit tests, simulated microcontroller boards and emulated ESP32 boards.
  - A hardware-in-the-loop bench with microcontroller boards (ESP8266, ESP32 family,
    RP2040/RP2350, STM32F446, nRF52840), run on a self-hosted runner when one is registered.
- Cost order: work MUST use local compute first, then the subscription, then pay-per-use
  APIs. Choosing a more expensive tier MUST be justified in the plan.
- Budgets: every spec that incurs cash costs MUST state a cash budget. Pay-per-use keys MUST
  carry a hard spending limit at or below that budget. Exceeding the budget requires a spec
  amendment.
- Development hardware is not target hardware: the budgets of a task (Principle V) MUST be
  measured on its reference hardware as stated in the spec. Quality runs MAY use development
  hardware only with identical model files, numeric format and settings.
- Subscription models: use MUST follow the provider's terms. Outputs of a subscription model
  count as outputs of that provider for Principles III and VI. A model whose terms forbid
  training other models on its outputs MUST NOT be a teacher.
- Crawl once: every fetched source MUST be stored as a complete raw snapshot with retrieval
  date, origin, license, legal basis and permitted uses. Later iterations MUST reuse the
  snapshots. A source is fetched again only when it is new or when a documented update is
  needed.

Rationale: The project runs on a small cash budget and strong local hardware. Fixing the cost
order and crawling each source once keeps experiments cheap and repeatable. Keeping development
and target hardware apart stops fast development machines from hiding a model that is too slow
for its real target.

## Technical Spikes

A spike is a small, bounded run that tests the whole pipeline or one risky step before the gates
that normally precede it are met, for example an end-to-end run from sources to a fine-tuned model
before the agreement pilot is complete.

- A spike MUST be its own feature spec, MUST call itself a spike and MUST state its size bounds
  (number of chunks for training data and for evaluation) and its cash budget.
- A spike is exempt from exactly two rules: the gate before large-scale data generation
  (Principle IV and "Development Workflow & Quality Gates"), and the requirement that reported
  results use a named, frozen benchmark version (Principle III). Every other principle still
  applies in full, including verbatim-quote grounding, benchmark labelers never acting as teachers,
  teacher licensing, clean provenance, crawl once, redaction, local-first cost order and budgets.
- Spike results MUST be labeled "spike" and MUST NOT be presented as benchmark results, used to
  pass or fail a gate, or used to change the decision criteria of a pilot.
- Spike training data and spike models MUST NOT be released and MUST NOT be reused as training
  data for non-spike models. Spike data follows the same retention rules as other datasets.
- Spike findings (what broke, what was slow, what cost too much) SHOULD be written down and fed
  into the next regular spec.

Rationale: An early end-to-end run finds integration problems cheaply. Keeping spikes small,
labeled and walled off from gates and releases stops them from turning into unmeasured shortcuts.

## Development Workflow & Quality Gates

- Every spec and every plan MUST list which principles it touches and state how it
  complies. The plan's Constitution Check gate MUST verify this before design work and
  again after it.
- Gate before large-scale data generation (model-labeled tasks): the inter-model agreement pilot
  (Principle IV) MUST be complete and every label dimension used for training MUST have passed
  it. Technical spikes are exempt within their stated bounds (see "Technical Spikes").
- Gate before an experiment: success and kill criteria MUST be recorded, and so MUST the cash
  budget if the experiment incurs cash costs.
- Gate before reporting a result: every result MUST name a frozen benchmark version and report
  the deterministic checks. Model-labeled tasks additionally report the consensus score, the
  contested-item report and the quality-vs-cost Pareto front. Ground-truth tasks additionally
  report the result of the deployed numeric format (for example int8 on the bit-exact host
  reference), not only the training-time format.
- Gate before a release: model, configuration, prompts and evaluation results MUST be
  reproducible from the versioned configuration, and every included source and dataset MUST have
  recorded origin, license and permitted use.
- Any violation of a principle MUST be documented in the plan's complexity or deviation
  section with a rationale and the simpler alternative that was rejected.

## Governance

- This constitution takes precedence over other project practices and guidance.
- Amendments require a written rationale and a version bump. The rationale MUST be recorded
  with the amendment.
- Versioning follows semantic versioning:
  - MAJOR: a principle is removed or redefined in a backward-incompatible way, or governance
    rules change incompatibly.
  - MINOR: a principle or section is added, or guidance is materially expanded.
  - PATCH: clarifications, wording and typo fixes that do not change meaning.
- Compliance review: every spec, plan and review MUST check compliance with the principles
  it touches. Non-compliance blocks the gate in question until it is resolved or justified
  as a documented deviation.

**Version**: 2.0.0 | **Ratified**: 2026-09-25 | **Last Amended**: 2026-10-08
