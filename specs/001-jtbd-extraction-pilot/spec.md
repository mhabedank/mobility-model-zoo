# Feature Specification: JTBD Extraction Pilot

> **Note (feature 003):** Since feature 003 the CLI `pilot` is `jtbd`, the code is in `src/mobility_model_zoo/productdev/jtbd/` and the configs are in `configs/productdev/jtbd/`. Paths and commands below are historical.

**Feature Branch**: `001-jtbd-extraction-pilot`

**Created**: 2026-09-25

**Status**: Draft

**Input**: User description: "Specify the pilot for the JTBD extraction project. Its purpose is to validate the riskiest assumption before any training: can frontier models label the extraction task consistently, and how far do small local models get without any training?" (full description: Mobility domain, five sub-areas, ~150 chunks, per-item schema, two or more frontier reference models, agreement measurements, zero-shot small-model baselines, go / revise / rethink decision criteria.)

## Purpose

The project plans to train a small local model to extract jobs, pains and gains with graded evidence. That plan rests on an untested assumption: that the labels are well-defined enough for frontier models to agree on them. If they do not agree, a small model cannot learn the labels and a benchmark cannot measure them.

The pilot tests this assumption on about 150 Mobility text chunks before any training data is generated. It also measures how far small local models get with no training at all. Those measurements give the first points on the quality-vs-throughput chart and show whether fine-tuning is needed.

## Clarifications

### Session 2026-09-25

- Q: Should a candidate for the later teacher model also run in the pilot, scored against the consensus but not part of it? → A: Yes. A third frontier model whose license permits training on its outputs labels all chunks and is scored like the baselines. *(Superseded on 2026-09-25 by the resources session below: two local teacher candidates on the DGX Spark.)*
- Q: Should the item kind count when items from two models are matched? → A: Match on quote-span overlap first. When several candidates overlap, the one with the same kind wins. Kind is never required for a match.
- Q: If the result is Revise, which chunks does the second run use? → A: About 30 extra holdout chunks with the same composition are set aside at collection time. They are labeled only in a rerun, and the decision after a rerun is based on the holdout agreement.
- Q: How many Revise cycles are allowed before the pilot moves to Rethink? → A: Exactly one rerun. If a dimension still misses its threshold on the holdout, the outcome for that dimension is Rethink.
- Q: How is a small-model or teacher-candidate item scored when it matches a contested reference item? → A: Neutrally. It counts as neither hit nor error, and it is counted and reported separately.

### Session 2026-09-29 (after the spike)

- Q: Do we apply for Reddit data access? → A: No. Reddit is dropped for pilot-v1; its share is covered by forums and reviews through the documented source-type substitution (FR-004, `configs/pilot-v1.yaml`). The Reddit fetcher and its `benchmark_only` guard stay in the code but are not used.
- Q: Which teacher candidates are scored against the reference, given that the OpenRouter models beat the local ones in the spike (mimo 0.80, deepseek 0.75, glm-5.3-flash 0.77, local qwen3.8 0.76; their ensemble 0.82)? → A: A mix plus an ensemble: local qwen3.8:27b and mimo-v2.6-pro, deepseek-v4.1-flash and glm-5.3-flash through OpenRouter, and their ensemble (item kept with at least two votes) as a fifth candidate (FR-019a, FR-019b). This supersedes "two local teacher candidates" from the resources session.
- Q: When is a teacher candidate fit to generate training data? → A: Relative to the reference: its composite reaches at least 90% of the frontier-versus-frontier composite on the same units (as in FR-031 (a)), and at least 98% of its outputs are schema-valid. Among fit candidates the one with the highest composite is recommended; within 0.02 the cheaper one wins (FR-031a).
- Q: Are near-miss teacher quotes repaired to the real source passage before scoring? → A: Both views. The verbatim check and all baseline and reference scores stay without repair. Teacher candidates are additionally scored with quote repair, because training data is built that way; FR-031a uses the repaired score. The repair rule is frozen in advance and the repair rate is reported (FR-026a).

### Session 2026-10-01 (analysis follow-up)

- Q: The constitution forbids spike results from changing a pilot's decision criteria, but the ensemble tie-break order came from spike measurements and the ensemble and repair rules sat in the decision criteria. How is that resolved? → A: Separate and neutralize. FR-031a stays in the decision criteria, justified from the FR-031 logic, not from spike values. The ensemble and quote-repair rules move to their own teacher-scoring configuration, frozen and hashed together with the criteria. Ensemble ties are broken by the alphabetical order of the member model IDs. No spike value enters a pilot rule (FR-015, FR-019b, FR-026a, FR-031a).
- Q: How does the ensemble decide relevance when the four teachers split 2:2? → A: The chunk counts as relevant, and items with at least two votes are kept (FR-019b).

### Session 2026-09-25 (resources)

Context: constitution v1.1.0 adds the Resources & Cost Discipline section. The resources are a DGX Spark (128 GB), a Claude subscription and an OpenRouter account.

- Q: Which models form the reference, and which are the teacher candidates? → A: The reference is Claude (via the subscription) and GPT (via OpenRouter). The teacher candidates are two local open-weight models from different families on the DGX Spark. This supersedes the earlier answer of "a third frontier model". *(Teacher candidates superseded on 2026-09-29 by the spike-learnings answer above: four single models and their ensemble.)*
- Q: What does "do not crawl the web twice" mean? → A: Every fetched source is kept as a complete raw snapshot with license, legal basis and permitted uses. Later phases reuse the snapshots and only add new sources.
- Q: How may Reddit be used? → A: Only through the official Data API, and only as `benchmark_only`. Arctic Shift may be used only to find thread IDs.
- Q: What is the cash budget? → A: At most €20 in total for the pilot. The subscription and the local hardware are not counted.
- Q: Which GPT model is the second reference, given the budget? → A: The smaller (mini) tier of the current GPT generation. The flagship would break the €20 budget. This is recorded as a deviation from the frontier requirement, and the report states it.

## User Scenarios & Testing *(mandatory)*

The primary user is the project owner (the researcher running the pilot). Secondary readers of the pilot report are future contributors who need to know why the label scheme looks the way it does.

### User Story 1 - Assemble a compliant, balanced pilot corpus (Priority: P1)

The project owner collects about 150 self-contained Mobility text chunks from lawful sources. The chunks are balanced across the five sub-areas and four source types, cover German and English, and include deliberate irrelevant and near-miss chunks. Each chunk carries full metadata, and usernames and direct identifiers are removed before any model sees it.

**Why this priority**: Every other measurement depends on this corpus. A corpus skewed toward one source type or one evidence level would make the agreement numbers meaningless.

**Independent Test**: Can be fully tested by producing the corpus plus a composition summary and checking the summary against the balance and metadata rules, without running any model.

**Acceptance Scenarios**:

1. **Given** the finished corpus, **When** its composition summary is produced, **Then** it shows counts per sub-area, source type, language, region and relevance intent, and every target in FR-003 to FR-007 is met or the shortfall is explained.
2. **Given** any chunk in the corpus, **When** its record is inspected, **Then** source, source type, sub-area, region, language, date and license are all present, and no username or direct identifier remains in the text.
3. **Given** a chunk that is a reply in a thread or chat, **When** it is read on its own, **Then** it contains the parent context needed to understand it.

---

### User Story 2 - Establish the frontier reference and measure agreement (Priority: P1)

The project owner writes a labeling guideline, freezes it together with the decision criteria, and has at least two frontier models from different model families label every chunk independently. The owner then gets agreement per label dimension and the results of the deterministic checks.

**Why this priority**: This is the riskiest assumption the pilot exists to test. The go / revise / rethink decision depends mainly on these numbers.

**Independent Test**: Can be fully tested with the corpus from Story 1: run the reference labeling, then check that raw labels, consensus, contested items, agreement per dimension and deterministic-check results all exist and can be traced back to the chunks.

**Acceptance Scenarios**:

1. **Given** the frozen guideline and corpus, **When** each reference model labels all chunks, **Then** every raw label is stored with model identifier, model version, labeling date and guideline version.
2. **Given** the raw labels of all reference models, **When** agreement is computed, **Then** a value is reported for each dimension: relevance, item matching, kind, actor type, evidence type (weighted for ordinal distance) and evidence scope. Each value comes with the number of units it was computed on.
3. **Given** two reference models' items for the same chunk, **When** they disagree on whether an item exists or on any of its categorical attributes, **Then** that item is marked contested for the affected dimension and is reported separately. It is neither dropped nor merged into the consensus.
4. **Given** any model output, **When** the deterministic checks run, **Then** each item's quote is checked verbatim against the chunk, each output is checked against the schema, and internal-consistency rules are applied. Pass rates are reported per model, independently of any agreement score.

---

### User Story 3 - Understand disagreements and propose guideline revisions (Priority: P2)

The project owner reviews the disagreements between reference models, sorts them into categories (for example, the boundary between anecdote and routine, or pain versus negated gain), and turns the most frequent categories into concrete guideline revisions.

**Why this priority**: A "revise" outcome is useless without knowing what to revise. This analysis also explains any "go" result.

**Independent Test**: Can be tested with the labels from Story 2 alone: every contested item is assigned to a category, and every proposed revision points to the category and example items that motivate it.

**Acceptance Scenarios**:

1. **Given** all contested items, **When** the disagreement analysis is done, **Then** each contested item belongs to exactly one primary disagreement category and each category has a count and at least one example.
2. **Given** the disagreement categories, **When** revisions are proposed, **Then** each revision names the guideline section it changes, the category it addresses and the expected effect on agreement.

---

### User Story 4 - Measure zero-shot small-model baselines and teacher candidates (Priority: P2)

The project owner runs 2–3 small local models (up to about 4B parameters) and the teacher candidates (FR-019a, FR-019b) with the same guideline and no training. Each model is scored against the frontier consensus per dimension. For the small models, throughput, peak memory and latency are measured on the low-resource reference hardware; their quality runs may happen on the development hardware with identical model files (FR-029).

**Why this priority**: This decides whether fine-tuning is needed at all and gives the first points on the quality-vs-throughput chart. It depends on the consensus from Story 2.

**Independent Test**: Can be tested once a consensus exists: each baseline model yields per-dimension scores against the consensus, deterministic-check pass rates, and throughput, peak memory and latency figures from the reference hardware.

**Acceptance Scenarios**:

1. **Given** the consensus, **When** a small model processes all chunks, and its performance is measured on the reference hardware with the same model file, **Then** its per-dimension scores, deterministic-check pass rates, throughput, p50/p95 latency per chunk and peak memory are recorded.
2. **Given** a small model that returns an empty item list for a chunk the consensus also leaves empty, **When** it is scored, **Then** that empty result counts as correct.
3. **Given** a small model output that fails the schema, **When** it is scored, **Then** the failure is counted against the model and not silently repaired or skipped.
4. **Given** the consensus, **When** each teacher candidate processes all chunks (or, for the ensemble, is combined from their outputs), **Then** its per-dimension scores, check pass rates, model digest or provider model version, quantization and license basis are recorded, and the report states whether it is fit to generate training data.

---

### User Story 5 - Deliver the pilot report and decision (Priority: P2)

The project owner produces one pilot report that combines agreement per dimension, disagreement categories, proposed guideline changes, baseline results placed on the quality-vs-throughput chart, and a go / revise / rethink decision derived from the pre-recorded criteria.

**Why this priority**: The report is the deliverable. It turns the measurements into a decision and records why.

**Independent Test**: Can be tested by giving the report to a reader who did not run the pilot and checking that they reach the same decision from the pre-recorded criteria and the reported numbers.

**Acceptance Scenarios**:

1. **Given** the agreement results and the recorded decision criteria, **When** the decision is derived, **Then** it follows mechanically from the decision table in FR-030. Any deviation is documented with a rationale.
2. **Given** the baseline results, **When** the report is produced, **Then** each small model appears as a point on the quality-vs-throughput chart, labeled with the benchmark version.
3. **Given** the report, **When** it describes quality, **Then** it states agreement with frontier models and never presents it as accuracy against human ground truth.

---

### Edge Cases

- **Chunk with no extractable items but relevant to Mobility**: a valid result is relevant with an empty item list. Relevance and item presence are separate dimensions.
- **Irrelevant chunk where a model still extracts items**: this is flagged by the internal-consistency check and counts as disagreement on relevance.
- **Quote that differs from the source only in whitespace, line breaks or typographic quote characters**: it counts as verbatim after that limited normalization. Any other difference, including a translated or paraphrased quote, fails the check. For teacher candidates, a near-miss quote is additionally repaired for the separate repaired score (FR-026a); the check result itself does not change.
- **German chunk**: the quote stays in German and the normalized statement is in English. A German quote that has been translated fails the verbatim check.
- **Two models extract the same item with overlapping but different quote spans**: this is resolved by the item-matching rule (FR-020) and is not treated as disagreement.
- **One model splits an item that the other model keeps as one**: this is handled by the matching rule and counted as its own disagreement category.
- **A reference model refuses, times out or returns malformed output for a chunk**: the chunk is retried a fixed number of times. After that the failure is recorded and the chunk is excluded from agreement for that model, with the exclusion count reported.
- **A chunk turns out to contain personal data that was missed**: it is removed or re-redacted, and labeling for that chunk is repeated before agreement is computed.
- **Model version changes during labeling**: all chunks for one reference model must be labeled with one model version. If the provider changes the version mid-run, that model's labeling is repeated.
- **A dimension has too few units to compute a stable agreement value** (for example, very few "measurement" items): the value is reported with its unit count and confidence interval and marked as underpowered, not suppressed.
- **Revise outcome and rerun**: a rerun uses a new guideline version and a new benchmark version. It is labeled on both the main corpus and the holdout set (FR-002a). The decision uses the holdout agreement. Agreement on the main corpus is reported next to it and marked as optimistic.

## Requirements *(mandatory)*

### Functional Requirements

**Domain and corpus**

- **FR-001**: The pilot MUST use Mobility as its problem domain, defined as moving people and goods, including vehicles, transport services, infrastructure, parking, energy and charging, logistics, work in these fields, regulation, and economic and societal effects. The domain definition MUST be written in the guideline and given to every model as input. No persona, user segment or role description may be given as input.
- **FR-002**: The corpus MUST contain about 150 chunks (acceptable range 140–160). Each chunk MUST be a self-contained unit of roughly 300–1500 tokens.
- **FR-002a**: In addition to the main corpus, about 30 holdout chunks MUST be collected under the same rules and composition targets (FR-003 to FR-012). Holdout chunks MUST NOT be labeled by any model, or read during disagreement analysis, before a rerun. They are labeled only in a rerun after a Revise decision. If the first result is Go or Rethink, they stay unused and remain available for a later benchmark version.
- **FR-003**: Relevant chunks MUST be balanced across the five sub-areas (public transport and rural mobility; logistics and delivery; e-mobility and charging; car ownership and use; sharing and platforms). No sub-area may fall below 15% or exceed 25% of relevant chunks.
- **FR-004**: Chunks MUST be balanced across the four source types (scientific papers and industry studies; Reddit; forums and reviews; conversational transcripts). No source type may fall below 18% or exceed 32% of all chunks.
- **FR-005**: About 20% of chunks (acceptable range 15–25%) MUST be irrelevant to the domain or near-misses (for example, cars as hobby or collector objects, motorsport, transport metaphors). They MUST be spread across source types.
- **FR-006**: 10–15% of chunks MUST come from outside Europe. The rest MUST come from Europe, with the DACH region as the largest single regional group.
- **FR-007**: The corpus MUST contain both German and English chunks, with each language making up at least 35% of chunks.
- **FR-008**: The corpus MUST include enough papers and industry studies that observation- and measurement-level evidence is likely to appear in at least 30 items in the consensus. If the reference labels show fewer, the report MUST say so and mark those evidence levels as underpowered.
- **FR-009**: A chunk that is a reply in a thread or chat MUST include the context needed to understand it (for example, the parent post or preceding turns).
- **FR-010**: Each chunk MUST record source, source type, sub-area, region, language, date and license as metadata. No model may be asked to predict any of these attributes.
- **FR-011**: Only sources that may lawfully be used for text and data mining MAY be included. Machine-readable opt-outs and platform access terms MUST be respected. Each source MUST record its legal basis and permitted uses (`benchmark_only` or `training_allowed`). Reddit content MUST be retrieved only through the official Reddit Data API and MUST be marked `benchmark_only`. Archive indexes such as Arctic Shift MAY be used only to find thread identifiers, never as a source of text.
- **FR-012**: Usernames and direct identifiers MUST be removed from every chunk before any model labels it. The removal MUST be verifiable by a check on the stored chunk text.
- **FR-013**: The retention period for the pilot corpus and raw labels MUST be recorded with the dataset. The corpus MUST NOT be published.
- **FR-013a**: Every source used MUST be stored once as a complete raw snapshot (the whole document, thread or transcript, not only the chunk), with retrieval date, origin, license, legal basis and permitted uses. Chunks MUST reference their snapshot and their position in it. Holdout chunks and later project phases MUST draw from existing snapshots before any source is fetched again. A source MUST NOT be fetched a second time unless it is new or a documented update is needed.

**Guideline and reference labeling**

- **FR-014**: A written labeling guideline MUST define relevance, the three item kinds (job, pain, gain), the five actor types (individual, worker, organization, public sector, society), the five ordinal evidence types (opinion < anecdote < routine < observation < measurement), the three evidence scopes (single, multiple, quantified), the verbatim-quote rule, the English normalized statement, and the rule that uncertain grades take the lower value. It MUST include worked examples, among them at least one correct empty result.
- **FR-015**: The guideline, the output schema, the decision criteria (FR-030, FR-031, FR-031a) and the teacher-scoring configuration (the ensemble rule of FR-019b and the quote-repair rule of FR-026a) MUST be versioned and frozen before the first reference labeling run. Changing them after results are seen MUST produce a new version with a documented rationale.
- **FR-016**: For each chunk, a model MUST output a relevance judgment and a list of items (possibly empty). Each item has kind, verbatim supporting quote, actor (free text), actor type, normalized English statement, evidence type and evidence scope.
- **FR-017**: At least two frontier models from different model families MUST label every chunk independently, using the same guideline and schema and without seeing each other's output. Documented deviation (plan.md, Complexity Tracking): for budget reasons, the GPT-family reference is the mini tier of the current GPT generation, not the flagship. The report MUST state this.
- **FR-018**: Every raw label from every model (reference and baseline) MUST be retained unmodified, with model identifier, model version, labeling date, guideline version and run settings.
- **FR-019**: The reference models used in the pilot MUST be recorded as benchmark labelers. They are therefore excluded from later use as training-data generators.
- **FR-019a**: Four single-model teacher candidates MUST also label every chunk: the local open-weight model qwen3.8:27b on the development hardware (DGX Spark), and three open-weight models through OpenRouter (mimo-v2.6-pro, deepseek-v4.1-flash, glm-5.3-flash). OpenRouter is used for them because their weights do not fit the development hardware (119 GB usable memory): MiMo-V2.6-Pro has 1.02T total parameters, GLM-5.3-Flash 320B and DeepSeek-V4.1-Flash about 284B, all far above 119 GB at 4-bit, and the official Ollama library offers the latter two only as cloud models (checked 2026-10-01; cost order, constitution Resources & Cost Discipline). All candidates MUST come from model families that differ from both reference families. Each MUST have a license that permits training other models on its outputs. For local candidates the exact model file (digest) and quantization MUST be recorded; for OpenRouter candidates the provider model version, the allowed quantizations and the reasoning setting. Each teacher candidate MUST use the same guideline and schema, MUST NOT contribute to the consensus or to the contested set, and MUST be scored against the consensus exactly like the small baselines (FR-028) and pass the same deterministic checks (FR-026). The license basis for teacher use MUST be recorded for each candidate.
- **FR-019b**: The ensemble of the four teacher candidates MUST be scored as a fifth teacher candidate. It is computed offline from their stored outputs, with no extra model calls: relevance by majority vote, with a 2:2 split counting as relevant; items grouped greedily by span overlap with the FR-020 minimum IoU (members processed in alphabetical order of their model IDs, each item joining the group it overlaps most, at most one item per member and group, a new group when no group reaches the minimum IoU) and kept when at least two candidates found them; attributes by majority vote. Ties are broken by the alphabetical order of the member model IDs; quote, actor and statement are taken from the alphabetically first member in the group. The combination rule is part of the teacher-scoring configuration, which MUST be frozen together with the decision criteria (FR-015) before the teacher candidates are scored. No value measured in a spike may set any part of this rule (constitution, Technical Spikes).

**Matching, consensus and contested items**

- **FR-020**: Items from different models on the same chunk MUST be aligned by a written, deterministic matching rule based on overlap of the quoted spans in the source text. When an item overlaps several candidates, a candidate with the same kind wins, and among equals the one with the largest overlap wins. Kind MUST NOT be a precondition for a match, so kind disagreements stay visible in the kind dimension. The rule MUST allow one-to-one matching only and MUST record unmatched items.
- **FR-021**: The consensus MUST contain the relevance judgments and the matched items on which the reference models agree. For each item it MUST also hold the per-dimension attribute values on which they agree.
- **FR-022**: Every item that is unmatched, or matched but disagreeing on any categorical dimension, MUST be marked contested for the affected dimension(s). Contested items MUST be kept, reported separately, and excluded from consensus scores for those dimensions.

**Measurements**

- **FR-023**: Agreement between the reference models MUST be reported per dimension:
  - relevance: chance-corrected agreement (kappa)
  - item matching: agreement on item existence (F1 between models over matched and unmatched items)
  - kind, actor type and evidence scope: chance-corrected agreement on matched items
  - evidence type: weighted chance-corrected agreement that accounts for ordinal distance

  Each value MUST come with its unit count and a confidence interval. When more than two reference models are used, a multi-rater agreement measure MUST be used, and pairwise values MUST also be shown.
- **FR-024**: Agreement MUST also be broken down by language and by source type, and region outside Europe versus inside Europe, so that systematic weaknesses become visible.
- **FR-025**: Free-text fields (actor, normalized statement) are not agreement-gated. A sample of matched pairs MUST be included in the disagreement analysis so that systematic divergence is visible.
- **FR-026**: Deterministic checks MUST run on every output of every model, independently of any model judgment:
  - verbatim quote match against the chunk text (after only the normalization defined in Edge Cases)
  - schema validity
  - internal consistency, at least: irrelevant chunks have no items, all enumerated fields hold allowed values, and a "quantified" scope is backed by a quote that contains a quantity

  Pass rates MUST be reported per model and per check.
- **FR-026a**: For teacher candidates only, the pilot MUST additionally score outputs after quote repair: a quote that fails the verbatim check is replaced by the source passage it matches if a fuzzy match reaches a similarity of at least 90 (0–100 scale) and the passage is 0.8–1.25 times the quote's length; otherwise the item is dropped. The repair rule is part of the teacher-scoring configuration and MUST be frozen with the decision criteria (FR-015). Repair MUST NOT change the verbatim-check pass rates (FR-026), which always refer to the raw output, and MUST NOT be applied to reference or baseline models. The report MUST show each teacher candidate's raw and repaired scores and its repair rate (repaired, dropped). The FR-019b ensemble is built from repaired items.
- **FR-027**: Every contested item MUST be assigned to one primary disagreement category from a category list built during analysis. Categories MUST be reported with counts and examples. Proposed guideline revisions MUST each reference the categories they address.
- **FR-028**: 2–3 small local models of up to about 4B parameters MUST each be run zero-shot (no fine-tuning) on all chunks with the same guideline and schema as the reference models. Each MUST be scored against the consensus on every dimension in FR-023, with contested items excluded and reported separately. An evaluated item that matches (by the FR-020 rule) a reference item contested on item existence MUST be scored neutrally: it is neither a hit nor a false positive. The number of such items MUST be reported per model. The same applies to attribute dimensions on which the matched reference item is contested.
- **FR-029**: For each small model, the pilot MUST measure on the reference hardware: throughput (chunks per minute and output tokens per second), p50 and p95 latency per chunk, and peak memory. Frontier throughput and cost of the reference labeling MUST be recorded as well. Quality runs of the small models MAY run on the development hardware (DGX Spark), but only with the same model files, quantization and settings as the measurement on the reference hardware.

**Decision and report**

- **FR-030**: The go / revise / rethink decision MUST be derived from this table (initial values, to be confirmed and frozen per FR-015):

  | Condition | Decision |
  |-----------|----------|
  | Relevance kappa ≥ 0.8 AND evidence-type weighted kappa ≥ 0.6 AND every other dimension meets its threshold | **Go** |
  | Evidence-type weighted kappa in [0.4, 0.6), OR relevance kappa < 0.8, OR any other dimension below its threshold | **Revise** the affected definitions and rerun |
  | Evidence-type weighted kappa < 0.4 | **Rethink** the evidence scale (takes precedence over Revise) |

  After a rerun, the same table is applied to the agreement measured on the holdout set. At most one rerun is allowed. If a dimension still misses its threshold after the rerun, the outcome for that dimension is **Rethink**, not a second Revise.

  Thresholds for the other dimensions: kind, actor type and evidence scope need kappa ≥ 0.6, and item matching needs F1 ≥ 0.7. Missing any of them means Revise for the affected definition.
- **FR-031**: Fine-tuning MUST be classified as optional rather than required if at least one zero-shot small model reaches ≥ 85% of the reference quality at ≥ 10x the reference throughput. "Reference quality" is the composite agreement between the frontier reference models (frontier versus frontier, on the same dimensions and scoring as the small models). "Reference throughput" is the frontier reference labeling rate in chunks per minute, as recorded under FR-029. The report MUST note that this compares hosted with local throughput and that hosted throughput depends on provider rate limits. To keep the ratio comparable, the small model and the frontier pair MUST be scored with the same metric per dimension (kappa, weighted kappa or F1) on the same set of units. The ratio is therefore computed against (a) frontier-versus-frontier agreement restricted to consensus units and (b) frontier-versus-frontier agreement on all units. Both ratios MUST be reported, and the classification uses (a). The reference throughput comes from the GPT mini-tier model, which makes the 10x hurdle stricter than it would be against a flagship model. The report MUST state this.
- **FR-031a**: A teacher candidate (FR-019a, FR-019b) MUST be classified as fit to generate training data if its composite agreement with the consensus, scored after quote repair (FR-026a), reaches at least 90% of the reference quality, computed as ratio (a) in FR-031 (frontier-versus-frontier agreement restricted to consensus units, same metric per dimension), and at least 98% of its outputs are schema-valid. Among fit candidates, the report MUST recommend the one with the highest composite. If another fit candidate is within 0.02 of it, the one with the lower recorded cost per chunk MUST be recommended. If no candidate is fit, the report MUST say so and name the dimensions that miss. Rationale for the values, independent of any spike result: FR-031 accepts a small model at 85% of the reference quality; a teacher's outputs become the training targets, so it must sit closer to the reference (90%), and its output must be almost always usable (98% schema-valid, the same tolerance as SC-002's 2% exclusions). 0.02 is below the typical width of the composite confidence interval, so smaller gaps are not treated as real differences.
- **FR-032**: The pilot report MUST contain: corpus composition; agreement per dimension with confidence intervals and breakdowns; deterministic-check results; contested-item summary; disagreement categories; proposed guideline revisions; baseline and teacher-candidate results per dimension, with the FR-031a classification for each teacher candidate and the recommended teacher; the quality-vs-throughput chart with each small model as a point; the decision with the path through FR-030; and the benchmark and guideline versions used.
- **FR-033**: The report MUST describe quality as agreement with frontier models and MUST NOT present it as accuracy against human ground truth.
- **FR-034**: The pilot benchmark (corpus, guideline, consensus, contested set) MUST be frozen under a version identifier once it is used for the baseline evaluation, and it MUST be reproducible from recorded configuration.

### Key Entities

- **Source**: the document, thread or transcript a chunk comes from. Has origin, source type, license, access terms and date.
- **Chunk**: a self-contained text unit of 300–1500 tokens drawn from a source. Has sub-area, region, language, relevance intent (relevant / irrelevant / near-miss), date, license and redacted text.
- **Labeling Guideline**: the versioned written definition of the task, domain, categories, rules and worked examples, shared by all models.
- **Label Run**: one model's pass over the corpus. Has model identifier, family, version, date, guideline version, settings and raw outputs.
- **Extraction Output**: one model's result for one chunk: a relevance judgment and a list of items.
- **Item**: kind, verbatim quote, actor, actor type, normalized statement, evidence type, evidence scope.
- **Item Match**: an alignment of items across label runs for the same chunk, including unmatched items.
- **Consensus Entry**: the agreed relevance or item with its agreed attributes. **Contested Entry**: a disagreement with its affected dimensions and disagreement category.
- **Deterministic Check Result**: per output and item, pass or fail for each check.
- **Teacher Candidate Result**: per teacher candidate: per-dimension scores against the consensus, check pass rates, model digest and quantization (local) or provider model version, quantizations and reasoning setting (OpenRouter), and the recorded license basis. For the ensemble: its member candidates and the frozen combination rule.
- **Baseline Result**: a small model's per-dimension scores, check pass rates, throughput, latency and peak memory on the reference hardware.
- **Benchmark Version**: the frozen bundle of corpus, guideline, consensus and contested set that results refer to.
- **Pilot Report**: the deliverable that combines all of the above with the decision.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The corpus and the holdout set each meet every composition target in FR-002 to FR-007, and 100% of chunks carry complete metadata and pass the identifier-removal check.
- **SC-002**: 100% of chunks are labeled by every reference model, or every exception is recorded with its cause. At most 2% of chunks are excluded per model.
- **SC-003**: Agreement is reported for all six dimensions, each with unit count and confidence interval. No dimension is left unreported.
- **SC-004**: 100% of contested items are assigned a disagreement category, and every proposed guideline revision points to at least one category.
- **SC-005**: At least two small local models are fully evaluated, each with per-dimension quality, throughput, p50/p95 latency and peak memory measured on the reference hardware.
- **SC-005a**: All five teacher candidates (four single models and the ensemble) are fully evaluated against the consensus on all six dimensions, and the report states for each whether it is fit to generate training data.
- **SC-006**: A reader who did not run the pilot reaches the same go / revise / rethink decision from the report's numbers and the pre-recorded criteria alone.
- **SC-007**: Any pilot result can be traced from the report back to the raw label, model version, guideline version and chunk that produced it.
- **SC-008**: The decision criteria were recorded before the first reference labeling run. This is verifiable from version dates.
- **SC-009**: Total cash spent on the pilot stays at or below €20, including one holdout rerun, as shown by the recorded costs.
- **SC-010**: Every chunk traces back to a stored raw snapshot, and no source was fetched twice.

## Constitution Alignment

| Principle | How this pilot complies |
|-----------|-------------------------|
| I. Problem-First | Models get the domain definition, not a persona (FR-001). Actor and actor type are output fields (FR-016). |
| II. Grounded Evidence | Every item needs a verbatim quote (FR-016, FR-026). Uncertain grades take the lower value (FR-014). Empty results are valid and scored as correct (US4, FR-014). |
| III. Measure Before Optimizing | Reference from ≥2 model families (FR-017). Contested items are kept separately (FR-022). Deterministic checks are reported on their own (FR-026). Quality-vs-throughput chart (FR-032). Results are framed as agreement, not accuracy (FR-033). Labelers are excluded from training-data generation (FR-019). |
| IV. Riskiest Assumption First | This pilot is the agreement gate. Criteria are frozen before labeling (FR-015, SC-008). |
| V. Small and Local | Baselines are measured on stated low-resource hardware (FR-029, Assumptions). Hosted models are used only for reference labeling. |
| VI. Clean Provenance | Lawful sources, license, legal basis and permitted uses per source, Reddit as `benchmark_only`, identifier removal, stated retention, no publication (FR-011 to FR-013a). |
| VII. Metadata over Inference | Region, language, source type, sub-area and date are metadata and are never predicted (FR-010). |
| VIII. Fair Comparison | All baselines use the same benchmark version and scoring (FR-028, FR-034). Training framework is not in scope. |
| IX. Reproducible Releases | Raw labels are kept with model version and date (FR-018). Benchmark is frozen and versioned (FR-034). |
| X. Scope Discipline | Only extraction is labeled and scored. No deduplication, clustering or prioritization. |
| Resources & Cost Discipline | Cost order: local (DGX Spark: local teacher candidate, baseline quality runs), then subscription (Claude), then pay-per-use (GPT and the three teacher candidates that do not run locally via OpenRouter, reference VM). Cash budget of €20 with a hard cap on the key (SC-009). Crawl once (FR-013a, SC-010). Development and target hardware kept apart (FR-029). |

## Out of Scope

- Model training or fine-tuning of any kind. The spike's training learnings (token-weighted loss, Spark memory watchdog and limits, checkpoint selection) are recorded in `specs/002-e2e-spike` and the spike report and belong to the later training feature.
- Large-scale data generation
- Deduplication, clustering, persona formation and prioritization
- Human review or human ground truth labels
- Publication of the corpus, labels or consensus (the method, prompts and evaluation results may be shared later)

## Assumptions

- **Reference hardware**: a rented cloud VM with 8 GB RAM, 4 vCPU and no dedicated GPU, running models quantized for local inference and with no network access during measurement. This is the concrete budget required by Principle V.
- **Reference models**: exactly two frontier models from different families form the reference: Claude, run headless through the existing Claude subscription, and GPT, the mini tier of the current generation for budget reasons, run through OpenRouter with a fixed provider. Because the GPT side is not a flagship model, the report MUST state this and check whether disagreements come mainly from one reference model. Claude's sampling temperature cannot be set on this path, and this is documented as a deviation. The teacher candidates (FR-019a, FR-019b) are kept out of the consensus, so they never act as tie-breakers.
- **Resources**: a DGX Spark with 128 GB unified memory (local models, teacher candidates, baseline quality runs), a Claude subscription and an OpenRouter account, as listed in the constitution (Resources & Cost Discipline).
- **Item matching**: the minimum span overlap for a match is set in the guideline and frozen with it (FR-020 defines the tie-breaking).
- **Zero-shot**: small models receive the same guideline text, including its worked examples, as the reference models. No other examples, retrieval or fine-tuning are used.
- **Composite quality** (for FR-031): the unweighted mean of the per-dimension scores against the consensus, computed the same way for every model.
- **Retention**: the pilot corpus and raw labels are kept while the pilot benchmark version is in use for evaluation, and are reviewed for deletion no later than 24 months after freezing.
- **Conversational transcripts** come from publicly available interviews, podcasts, hearings or similar sources whose terms permit text and data mining. Private chats are not used.
- **Sub-area assignment** is made by the project owner at collection time as metadata. Chunks that touch several sub-areas get their primary one.
- **Confidence intervals** are computed by resampling chunks, so that items from the same chunk are not treated as independent.
- **Cash budget**: at most €20 in total for the pilot, including one holdout rerun. The expected spend is about €10 (GPT and three teacher candidates via OpenRouter, a few hours of the reference VM, and a buffer). The OpenRouter key carries a hard spending limit at or below the budget. The subscription and the DGX Spark are not counted.
