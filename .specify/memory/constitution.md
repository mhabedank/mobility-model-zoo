<!--
Sync Impact Report
==================
Version change: 2.3.0 → 3.0.0
Bump rationale: MAJOR. Owner direction of 2026-10-13: "never use claude as a tool for AI
learning or extraction. not even in the slightest." Withdraws a permission the constitution gave
(Claude labeling within the provider's terms, Claude as a benchmark reference labeler) and adds a
principle that admits no deviation, which changes the general deviation rule. Practice that was
compliant under 2.3.0 is non-compliant now.

Owner decisions (2026-10-13): total ban (training, teacher, synthetic data, labels, benchmark
references, judges, selection signals, the task itself, extraction of Claude); existing Claude
reference labels kept as they are; Claude stays a development assistant whose outputs never become
model data.

Modified principles:
- III. Measure Before Optimizing: benchmark labelers exclude Claude.
- VI. Clean Provenance, Restrictions Carry Over: a teacher is never Claude.

Added sections:
- XI. No Claude in Model Learning or Extraction.

Modified sections:
- Resources & Cost Discipline: inventory as of 2026-10-13, Claude subscription for development
  assistance only; cost order and subscription-model rule exclude Claude from data work.
- Technical Spikes: the Claude ban is listed among the rules spikes are not exempt from.
- Development Workflow & Quality Gates: release gate checks for Claude-produced inputs; new gate
  before labeling, data generation and evaluation runs; Principle XI admits no deviation.

Removed sections: none.

Previous reports: 2.2.0 → 2.3.0 (MINOR, 2026-10-12) added Roadmap and Delivery Pace and its gate;
2.1.0 → 2.2.0 (MINOR, 2026-10-10, feature 010) allowed `experimental` releases below production
readiness; 2.0.0 → 2.1.0 (MINOR, 2026-10-10, feature 011) added the usage class of every model, NC
models under an NC licence with the suffix `-nc`, restrictions of inputs carrying over and pinned
third-party models; 1.4.0 → 2.0.0 made tools and budgets per task, replaced the "accuracy" ban by a
metric naming rule and allowed dataset publication after a redistribution check; 1.3.0 → 1.4.0
changed model naming to `<name>-<variant>`; 1.2.0 → 1.3.0 made the project the multi-topic
`mobility-model-zoo`.

Templates reviewed (not modified; they read the constitution at runtime and quote none of the
changed rules):
- .specify/templates/plan-template.md ✅
- .specify/templates/spec-template.md ✅
- .specify/templates/tasks-template.md ✅

Follow-up (outside this amendment; code and records now non-compliant):
- configs/productdev/jtbd/cluster-v1.yaml `reference_models` and topics/productdev/tasks/
  jtbd-cluster.md name claude-reference: cluster-v1 stays as it is; the next cluster benchmark
  version and any new labeling run need a second non-Claude family.
- configs/productdev/jtbd/models.yaml `claude-reference`, labeling backends `claude_cli` and
  `anthropic_api`: must be blocked for labeling, teacher, judge and data generation roles, with a
  gate check that fails any run recording a Claude model.
- compliance/providers.yaml `claude-api` ("future reference labeler") and decision D-claude-api
  (future Claude reference labels via the API): superseded; record a new decision.
- zoo check: release gate check that no input behind a model was produced by Claude, apart from
  the labels Principle XI keeps.
-->

# mobility-model-zoo Constitution

An open collection of small, fast machine learning models for mobility, grouped by topic. Each
model solves one task, runs locally and is released with a versioned, honest model card that states
what users may do with it: under an open licence, or under a restricted one (for example
non-commercial) where its inputs require it.

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
  models from different model families, none of them Claude (Principle XI). No benchmark labeling model may be used to generate
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

### VI. Clean Provenance, Restrictions Carry Over

- Source selection is driven by data quality, not volume.
- Only sources that may lawfully be used for text and data mining or training MAY be included.
  Machine-readable opt-outs MUST be respected and platform access terms MUST be followed.
- Every source and every dataset MUST record its origin and license. Datasets are declared per
  topic with license, permitted use (`training_allowed` or `benchmark_only`), redistribution
  (`allowed`, `not_allowed` or `unclear`), commercial use and retention period.
- Every model has a usage class, derived from the most restrictive of its inputs: training and
  fine-tuning data, base model, teacher outputs, and third-party models it loads at run time.
  An input that permits non-commercial use only makes the model non-commercial (NC); an input
  under share-alike terms makes it share-alike. Restrictions carry over; they are never dropped.
- A source or dataset under a non-commercial license MAY enter training data only of NC models.
  Its declaration records `commercial_use: false`. Data whose license, platform terms or
  machine-readable opt-out forbid training altogether is `benchmark_only`, and a `benchmark_only`
  source MUST NOT enter training data of any model.
- Using data or models only to measure (benchmarks, agreement pilots, comparison baselines) does
  not change the usage class of the model being measured, provided their license permits that use.
- Share-alike terms of training data carry over: a model trained on share-alike data MUST be
  released under a compatible license.
- Personal data MUST be minimized: usernames and direct identifiers MUST be removed before
  labeling. Raw data MUST be retained only as long as needed, and the retention period
  MUST be stated for each dataset and each snapshot store. "Needed" includes reuse of raw
  snapshots in later iterations (see Resources & Cost Discipline).
- A teacher model MAY be used only if it is not Claude (Principle XI) and its license and
  provider terms permit training other models on its outputs. Terms that permit this for non-commercial use only make the student NC.
  Outputs of an NC model (labels, generated data, stored embeddings) are NC data and MUST NOT
  enter training data of a model that is not NC.
- Third-party models (base models, encoders, classifiers loaded by a pipeline stage) MUST be
  pinned to a revision, and remote code they load to its own commit. Their license basis MUST be
  recorded and MUST include the licenses of the training data their model card names. Where the
  weights carry a more permissive license than their documented training data, the training data
  governs. A stage that loads a restricted third-party model MUST state the restriction in its
  documentation and in the metadata of its output.
- Datasets MUST NOT be stored in the git repository. They live in separate storage: a local
  cache, an object store or Hugging Face dataset repositories.
- A dataset MAY be published (including third-party data, for example as a curated data
  compendium) only if its declaration says `redistribution: allowed` after its license and terms
  were checked, with attribution as the license requires, and only if it contains no personal
  data beyond what was already lawfully public and redacted. Texts collected under text and data
  mining rules (the JTBD sources) are `not_allowed`.

Rationale: A model is only usable by others if its inputs were lawfully obtained and handled
with respect for the people who wrote them, and if its users learn every restriction those inputs
impose. Carrying restrictions over lets the zoo use good non-commercial material without passing a
hidden risk to users. Keeping data out of git keeps the repository small; checking redistribution
first keeps publication lawful.

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
- Every release has a status. `released` MUST be used only for a production-ready model: it meets
  the success criteria and budgets of its task on the frozen benchmark, including the operational
  criteria the task defines (for example false alarms per hour). A model that does not yet meet
  them MAY be published with status `experimental`. Its model card MUST say that it is not
  production ready, name every criterion it misses with the measured value, and make no claim
  beyond the evidence. A kill outcome (Principle IV) blocks the claims it concerns, not an
  `experimental` release; the card reports the outcome.
- Training data, raw source text and labeling outputs MUST NOT be published. Datasets follow
  Principle VI: published only with `redistribution: allowed`, versioned and with attribution.
- Every release record and model card MUST state the model's usage class (Principle VI) and its
  license. A model MUST NOT be released under a license less restrictive than its usage class; it
  MAY be released more restrictively than its inputs require.
- An NC model MUST be released under a license that forbids commercial use and carries every
  other restriction of its inputs (for example CC BY-NC 4.0, or CC BY-NC-SA 4.0 with share-alike
  inputs). It carries the name suffix `-nc` (see "Project Scope & Iterative Delivery").
  "Non-commercial" MUST appear in the Hugging Face license tag, at the top of the model card, in
  the release record and on the zoo website, and the card MUST name the inputs that make the
  model NC. Code in the repository keeps the repository license; the restriction applies to
  the released weights and data.
- Compliance takes precedence over unrestricted use: where the two conflict, the zoo releases a
  model with restrictions (non-commercial, share-alike, attribution, use limits from provider
  terms) rather than leave a restriction out, and users learn the restrictions before download.

Rationale: Frozen, dated artifacts keep results comparable and let the benchmark itself be
audited later, because frontier models and base models change quickly. Marking the usage class
where users look first keeps a restricted model from being used beyond its license. The status
tells users at a glance whether a model is ready for use or a documented research result, so an
honest model that falls short can still be shared without overstating it.

### X. Scope Discipline

- The model extracts. It MUST NOT deduplicate, cluster or prioritize.
- Deduplication, clustering (including persona formation) and prioritization are separate
  downstream stages and MUST NOT be folded into the extraction model or its training
  objective.

Rationale: A narrow task is what makes a small, fast model feasible and measurable.

### XI. No Claude in Model Learning or Extraction

Claude means every model of Anthropic's Claude family, under any name and through any access
path: consumer apps, Claude Code, the Anthropic API, cloud platforms and resellers (for example
OpenRouter, Amazon Bedrock, Google Vertex AI).

- Claude MUST NOT be used as a tool for AI learning or extraction, not even in the slightest. No
  Claude output, in whole, in part or in derived form (paraphrased, filtered, aggregated,
  embedded), MAY become:
  - training, fine-tuning or pre-training data, teacher outputs, distillation targets, synthetic
    or augmented data, preference or reward data of any model;
  - labels of any kind, including benchmark reference labels, consensus or adjudication of
    contested items, and agreement pilots (Principles III and IV);
  - evaluation judgments (model-as-judge), or any signal used for model selection, threshold
    tuning, prompt optimization or the success and kill criteria of an experiment;
  - worked or few-shot examples, gold items or label examples that a model sees as input or
    learns from.
- Claude MUST NOT perform the task of any model in the zoo (for example extracting jobs, pains,
  gains and actors from source texts, or judging whether two items belong together), not as a
  reference, a baseline, a spike, a one-off test or an example.
- No extraction of Claude itself: the zoo MUST NOT try to replicate, imitate or approximate
  Claude's capabilities, behaviour, output distribution or weights by any method.
- Claude MAY be used as a development assistant: writing and reviewing code, specs, plans,
  documentation, model cards, compliance records and resource metadata (for example the URL,
  licence, language and permitted use of a source, without its content). What Claude writes in
  this role MUST NOT be used as model input data, and Claude MUST NOT read source texts to label
  or extract items for any model.
- The ban holds whatever the provider terms, licence, access path, cost, usage class or spike
  status. It admits no deviation (see "Development Workflow & Quality Gates").
- Every labeling, data generation and evaluation run MUST record the model that produced its
  output. A run that records a Claude model MUST fail its gate.
- Existing labels: the Claude reference labels produced before 2026-10-13 in the benchmarks
  pilot-v1, pilot-v2 and cluster-v1 and in the spike spike-v2 stay as they are, in the role they
  have (frozen benchmark references, decision D-claude-risk-0.1.x). No new Claude output is
  produced for any purpose this principle names, and every new benchmark version is labeled
  without Claude.

Rationale: The owner rules out any use of Claude for building or teaching other AI, without
exception. A narrow carve-out for development work keeps the assistant usable while drawing a
hard line: nothing Claude writes is ever data a model learns from or is measured against.

## Project Scope & Iterative Delivery

- The zoo is organized in topics. Each model belongs to exactly one topic. A model is named
  `<name>-<variant>`: a short, memorable English name for the model family and a size or
  variant (for example `scout-large`). A non-commercial model (Principle VI) carries the suffix
  `-nc` (`<name>-<variant>-nc`, for example `scout-large-nc`); a model whose usage class changes
  is a new model with a new name. Topic and task are recorded in the model description,
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

## Roadmap and Delivery Pace

- The zoo keeps one roadmap of planned releases in three calendar horizons: the next quarter and
  the two half-years after it. It is a plan, not a commitment, and is maintained as one versioned
  record in the repository.
- Every roadmap entry MUST record the horizon it was first planned in. That value MUST NOT be
  changed afterwards. Moving an entry records its new horizon in addition, with the date and
  reason of the move; dropping an entry records the date and reason instead of deleting it
  silently.
- An entry counts as delivered only when its release is published through the release pipeline
  (Principle IX), and its record MUST then carry the publication date. Finished work that is not
  published is not delivered.
- Pace review: at the end of every quarter, and before the horizons are rolled forward, a pace
  review MUST compare plan and actual for the closed period and report, per entry, whether it was
  delivered early, on time or late against the horizon it was first planned in (with the slip in
  horizons and days), which entries were moved or dropped, the number of releases delivered per
  quarter, and the share of planned entries delivered. The review is stored, dated, in the
  repository.
- Re-planning MUST use the measured pace: the next horizons are filled according to what the
  last reviews show the project actually delivers, not according to a fixed assumption. When the
  project is ahead, later entries are pulled forward; when it is behind, entries are moved or
  re-scoped with a stated reason. Because the work is AI-assisted, the pace is expected to change
  quickly; the review is where the plan follows it.
- Measurement is honest: an entry is never re-dated to hide a slip, a late entry is reported as
  late even after it was re-planned, and an entry that was pulled forward is reported as early.

Rationale: A plan is only useful if the project learns from how far reality departs from it.
Keeping the first planned horizon fixed and counting only published releases makes the pace
measurable, and basing each new plan on the measured pace keeps the roadmap neither timid nor
wishful.

## Resources & Cost Discipline

- Resource inventory (as of 2026-10-13; updated by PATCH amendment):
  - A DGX Spark with 128 GB unified memory: local compute for teacher runs, data
    generation, training and quality evaluation.
  - A Claude subscription (flat rate): development assistance only (Claude Code). Never
    labeling, data generation, evaluation or any other use that Principle XI forbids.
  - An OpenRouter account (pay-per-use): only for models that are available neither
    locally nor through the subscription.
  - GitHub CI runners: unit tests, simulated microcontroller boards and emulated ESP32 boards.
  - A hardware-in-the-loop bench with microcontroller boards (ESP8266, ESP32 family,
    RP2040/RP2350, STM32F446, nRF52840), run on a self-hosted runner when one is registered.
- Cost order: work MUST use local compute first, then a subscription, then pay-per-use
  APIs. Choosing a more expensive tier MUST be justified in the plan. The Claude subscription is
  not a tier for labeling, data generation or evaluation (Principle XI).
- Budgets: every spec that incurs cash costs MUST state a cash budget. Pay-per-use keys MUST
  carry a hard spending limit at or below that budget. Exceeding the budget requires a spec
  amendment.
- Development hardware is not target hardware: the budgets of a task (Principle V) MUST be
  measured on its reference hardware as stated in the spec. Quality runs MAY use development
  hardware only with identical model files, numeric format and settings.
- Subscription models: use MUST follow the provider's terms. Outputs of a subscription model
  count as outputs of that provider for Principles III and VI. A model whose terms forbid
  training other models on its outputs MUST NOT be a teacher. Claude is never a teacher, labeler
  or judge, whatever its terms (Principle XI).
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
  teacher licensing, the Claude ban (Principle XI), clean provenance, crawl once, redaction, local-first cost order and budgets.
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
  reproducible from the versioned configuration; every included source, dataset and third-party
  model MUST have recorded origin, license and permitted use; and the usage class derived from all
  inputs MUST NOT be less restrictive than the released license and its marking. The release
  status MUST follow Principle IX: `released` only when the task's success criteria and budgets
  are met, otherwise `experimental` with the unmet criteria on the model card. No training data,
  teacher output or evaluation behind the model was produced by Claude, apart from the existing
  benchmark labels that Principle XI keeps as they are.
- Gate before a labeling, data generation or evaluation run: no model in the run is Claude
  (Principle XI).
- Gate before rolling the roadmap forward: the pace review of the closed quarter (see "Roadmap
  and Delivery Pace") MUST be complete, and the new plan MUST state how it uses the measured pace.
- Any violation of a principle MUST be documented in the plan's complexity or deviation
  section with a rationale and the simpler alternative that was rejected. Principle XI admits no
  deviation: a plan that would violate it is rejected, not justified.

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

**Version**: 3.0.0 | **Ratified**: 2026-09-25 | **Last Amended**: 2026-10-13
