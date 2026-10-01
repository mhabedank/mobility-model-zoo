<!--
Sync Impact Report
==================
Version change: 1.2.0 → 1.3.0
Bump rationale: MINOR. The project becomes a multi-topic model zoo (`mobility-model-zoo`). No
principle is removed or redefined: the JTBD-specific principles keep their full force for the
product development JTBD models, and the shared principles now apply to every model in the zoo.
Principle IX is expanded with release rules.

Modified principles:
- IX. Reproducible, Dated Releases: adds immutable published versions, publication only through
  the release pipeline with owner approval, and the ban on publishing datasets.
- Core Principles: a scope note states which principles apply zoo-wide and which apply to the
  product development JTBD models.

Modified sections:
- Preamble and "Project Scope & Iterative Delivery": describe the zoo, its topics and the JTBD
  extraction task as the first task.

Added sections:
- Tasks and Releases: one build-and-measure tool per task, shared by all its models; one common
  release record and release gate for every model; shared code is extracted only when a second
  task needs it.

Removed sections: none

Templates reviewed (not modified; they read the constitution at runtime):
- .specify/templates/plan-template.md ✅ (Constitution Check must name the task a model belongs to)
- .specify/templates/spec-template.md ✅
- .specify/templates/tasks-template.md ✅

Follow-up TODOs:
- Feature 004 (production span model) must use the release record and gate from feature 003.
-->

# mobility-model-zoo Constitution

An open-source collection of small, fast machine learning models for mobility, grouped by topic.
Each model solves one task, runs locally and is released with a versioned, honest model card.

The first topic is product development (`productdev`). Its first task is an extraction engine for
a problem discovery framework: it extracts jobs-to-be-done, pains and gains with graded evidence
from heterogeneous texts (papers, forums, reviews, chats). Later topics, for example cyber security
or IoT, add their own tasks.

## Core Principles

Scope of the principles: Principles I, II, VII and X are written for the JTBD extraction task and
apply to every model of that task. Principles III, IV, V, VI, VIII and IX, and every section below
the principles, apply to every model in the zoo. Where a zoo-wide principle names frontier labeling
(III, IV), a task whose reference is not frontier labeling (for example a dataset with ground-truth
labels) MUST name its reference in its spec and apply the same rules to it: a fixed, frozen
reference, honest naming of what the reference is, separate reporting of disputed items, and
quality-vs-throughput reporting.

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

- The reference for quality is a frontier-consensus benchmark, labeled independently by at
  least two frontier models from different model families.
- No benchmark labeling model may be used to generate training data.
- Benchmark items on which the labeling models do not agree MUST be marked as contested and
  reported separately; they MUST NOT be silently dropped or merged into the consensus score.
- Deterministic checks MUST run independently of any model judgment and be reported on
  their own: verbatim-quote match against the source, schema validity and internal
  consistency.
- Every change to model, prompt, data or pipeline MUST be evaluated on both quality and
  speed, and results MUST be reported as a quality-vs-throughput Pareto front.
- Results MUST be described as agreement with frontier models, not as accuracy against
  human ground truth. Human review MAY be added in later iterations.

Rationale: Without a fixed reference and honest labeling of what that reference is,
improvements cannot be told apart from noise or from overfitting to one model's taste.

### IV. Validate the Riskiest Assumption First

- Before any large-scale data generation, a pilot MUST measure inter-model agreement
  between the benchmark labeling models on every label dimension.
- If the labeling models cannot reach agreement on a label dimension, that dimension's
  definition MUST be revised and re-piloted before training on it begins.
- Success criteria and kill criteria MUST be written down before an experiment starts and
  MUST NOT be changed after results are seen without a documented rationale.

Rationale: If frontier models cannot agree on a label, a small model cannot learn it and
the benchmark cannot measure it. Finding that out after generating data wastes the budget.

### V. Small and Local by Default

- The target model MUST run on machines with little RAM and no dedicated GPU (for example
  via Ollama, or ONNX on CPU). Each spec that introduces or changes a model MUST state its
  concrete memory and hardware budget.
- Hosted APIs MAY be used for data generation and evaluation.
- Hosted APIs MUST NOT be a runtime dependency of the extraction engine.

Rationale: The engine is meant to run anywhere, cheaply, on private data, without a
network dependency or per-call cost.

### VI. Clean Provenance, Quality First

- Source selection is driven by data quality, not volume.
- Only sources that may lawfully be used for text and data mining MAY be included.
  Machine-readable opt-outs MUST be respected and platform access terms MUST be followed.
- Every source MUST record its origin and license.
- Personal data MUST be minimized: usernames and direct identifiers MUST be removed before
  labeling. Raw data MUST be retained only as long as needed, and the retention period
  MUST be stated for each dataset and each snapshot store. "Needed" includes reuse of raw
  snapshots in later iterations (see Resources & Cost Discipline).
- Every source MUST record its permitted uses (`benchmark_only` or `training_allowed`),
  derived from its license, legal basis and access terms. A `benchmark_only` source MUST NOT
  enter training data.
- A teacher model MAY be used only if its license and provider terms permit training other
  models on its outputs.
- Datasets are for internal use and MUST NOT be published. Published artifacts are the
  model, the method, the prompts and the evaluation results.

Rationale: An open-source model is only usable by others if its training inputs were
lawfully obtained and handled with respect for the people who wrote them.

### VII. Metadata over Inference

- Anything knowable at collection time (region, source type, date, language, and similar
  attributes) MUST be stored as metadata on the source record.
- The model MUST NOT be asked to predict attributes that are available as metadata.

Rationale: Collected facts are exact and free; inferred ones are noisy and cost model
capacity that belongs to the extraction task.

### VIII. Fair Architecture Comparison

- Every approach (fine-tuned small decoder, encoder pipeline, external models) MUST be
  evaluated with the same benchmark version and the same evaluation harness.
- Ludwig is the primary training framework. Deviations MUST be justified in the plan.

Rationale: Architecture decisions are only meaningful when every candidate is measured the
same way.

### IX. Reproducible, Dated Releases

- Every model, dataset and benchmark MUST be versioned and reproducible from configuration.
- A benchmark version MUST be frozen once it has been used for an evaluation. Changes
  produce a new benchmark version.
- Raw labels from every labeling model MUST be retained together with the model identifier,
  model version and labeling date, so that later human review can measure both our models
  and the benchmark itself.
- Releases are dated snapshots with no maintenance promise.
- Retraining on a new base model MUST follow a documented, repeatable recipe.
- A published model version MUST be immutable. A fix is a new version; a broken version is
  marked deprecated, never silently overwritten or deleted.
- Models MUST be published only through the release pipeline, after its release gate passes and
  after the project owner approves the reviewed model card.
- Datasets, training data, raw source text and labeling outputs MUST NOT be published.

Rationale: Frontier models and base models change quickly. Frozen, dated artifacts keep
results comparable and let the benchmark itself be audited later.

### X. Scope Discipline

- The model extracts. It MUST NOT deduplicate, cluster or prioritize.
- Deduplication, clustering (including persona formation) and prioritization are separate
  downstream stages and MUST NOT be folded into the extraction model or its training
  objective.

Rationale: A narrow task is what makes a small, fast model feasible and measurable.

## Project Scope & Iterative Delivery

- The zoo is organized in topics. Each model belongs to exactly one topic and is named
  `<topic>-<task>-<variant>`. A new topic MUST NOT require changes to existing models.
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

- Resource inventory (as of 2026-09-25; updated by PATCH amendment):
  - A DGX Spark with 128 GB unified memory: local compute for teacher runs, data
    generation, training and quality evaluation.
  - A Claude subscription (flat rate): Claude labeling within the provider's terms.
  - An OpenRouter account (pay-per-use): only for models that are available neither
    locally nor through the subscription.
- Cost order: work MUST use local compute first, then the subscription, then pay-per-use
  APIs. Choosing a more expensive tier MUST be justified in the plan.
- Budgets: every spec that incurs cash costs MUST state a cash budget. Pay-per-use keys MUST
  carry a hard spending limit at or below that budget. Exceeding the budget requires a spec
  amendment.
- Development hardware is not target hardware: throughput, latency and memory of target and
  baseline models MUST be measured on the low-resource reference hardware stated in the spec
  (Principle V). Quality runs MAY use development hardware only with identical model files,
  quantization and settings.
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
- Gate before large-scale data generation: the inter-model agreement pilot (Principle IV)
  MUST be complete and every label dimension used for training MUST have passed it. Technical
  spikes are exempt within their stated bounds (see "Technical Spikes").
- Gate before an experiment: success and kill criteria MUST be recorded, and so MUST the cash
  budget if the experiment incurs cash costs.
- Gate before reporting a result: deterministic checks, consensus score, contested-item
  report and the quality-vs-throughput Pareto front MUST all be produced with a named,
  frozen benchmark version.
- Gate before a release: model, configuration, prompts and evaluation results MUST be
  reproducible from the versioned configuration, and every included source MUST have
  recorded origin and license.
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

**Version**: 1.3.0 | **Ratified**: 2026-09-25 | **Last Amended**: 2026-10-01
