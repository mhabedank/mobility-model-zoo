# Feature Specification: Deduplication and clustering of JTBD items

**Feature Branch**: `009-jtbd-dedup-cluster`

**Created**: 2026-10-09

**Status**: Draft

**Input**: User description: "Deduplication and clustering of scout outputs: the interface between the JTBD extraction model (scout, output format jtbd-span-v1) and downstream opportunity methods (Ulwick's Outcome-Driven Innovation / opportunity landscape, Teresa Torres' Opportunity Solution Tree, and similar: Value Proposition Canvas, affinity diagrams, job maps, journey maps, Kano, prioritisation)." (full description: topic productdev, new task downstream of extraction; input scout outputs plus source metadata; versioned output with items, duplicate groups, hierarchical clusters, an empty statement slot and generic assignments; stable ids, persistent human corrections, source dates, deterministic handling of exact copies; own reference and benchmark; training-free baseline first; out of scope: prioritisation, scoring, generated statements, personas, ontology, changes to scout.)

## Purpose

`scout-large` finds jobs, pains and gains in single texts and quotes them verbatim. Across hundreds or thousands of texts the same need comes up again and again, in other words, in German and in English. A product team cannot work with ten thousand quotes; it works with opportunities: distinct needs, how often and in how many independent sources they come up, and how they relate to each other.

This feature builds the stage between extraction and the opportunity methods. It merges items that say the same thing into duplicate groups, arranges groups into a hierarchy of clusters, and hands the result over in one versioned format that both an Opportunity Solution Tree (Torres) and an outcome-driven opportunity landscape (Ulwick) can be built from without conversion. Every group and cluster stays traceable to the verbatim quotes it was built from.

Constitution principle X requires this to be a separate downstream stage: scout and its training objective stay unchanged. Because deduplication and clustering have no ground truth, this is a model-labeled task with its own frozen benchmark and its own agreement pilot. The first answer is the simplest one that needs no training; a trained model follows only if that answer is not good enough.

## Clarifications

### Session 2026-10-09

- Q: Is an item that only differs in specificity ("find a parking space" vs. "find a parking space downtown in the evening") a duplicate, a child in the hierarchy, or a different need? → A: A child in the hierarchy. "Duplicate" means the same need only. The guideline labels a pair as *same*, *more specific than* or *different*; a more specific duplicate group of the same kind becomes a child of the more general one, so the detail level stays visible (FR-008, FR-009).
- Q: May a cluster bundle a job together with its pains and gains? → A: Yes. Clusters may combine groups of different kind, so a cluster can be read as a job with its pains and gains (Opportunity Solution Tree). Duplicate groups and the specificity relation stay within one kind; an outcome-driven landscape is built by filtering by kind (FR-004, FR-011).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Duplicates become evidence-backed groups (Priority: P1)

A product researcher has run scout over a collection of texts. They run the deduplication stage over all scout outputs and get one entry per distinct job, pain or gain, each with its representative quote, every member quote with its source, the number of mentions and the number of independent sources.

**Why this priority**: This is the smallest result that is useful on its own. A deduplicated list with mention and source counts already replaces manual affinity sorting of raw quotes, and it is the input for every later level.

**Independent Test**: Run the stage on the scout outputs of a fixed set of texts. Check that every input item appears in exactly one group, that every quote is unchanged and points to its source and offsets, and that the counts match the members.

**Acceptance Scenarios**:

1. **Given** scout outputs for many texts, **When** the stage runs, **Then** every input item belongs to exactly one duplicate group, no item is dropped, and every quote is byte-identical to the scout output with its source id and offsets.
2. **Given** two items of different kind (for example a pain and a job), **When** the stage runs, **Then** they are never in the same duplicate group.
3. **Given** the same text collected twice, or a forum post quoted in a reply, **When** the stage runs, **Then** the identical copies are recognised without a model and counted once as an independent source.
4. **Given** a duplicate group, **When** it is read, **Then** its representative quote is one of its members' original quotes, never generated or edited text.
5. **Given** a German and an English item that say the same thing, **When** the stage runs, **Then** they can end up in the same group.

---

### User Story 2 - Quality is measured against a frozen reference (Priority: P1)

The project owner wants to know how good the deduplication and the clustering are before anyone builds an opportunity map on them. A frozen benchmark, labeled by frontier reference models under a written guideline, measures both levels separately, and the results are reported next to the cost of each candidate.

**Why this priority**: Constitution principles III and IV. Without a reference, "good grouping" is a matter of taste, and nobody can tell whether a later model is better than the baseline. The agreement pilot also answers the riskiest assumption of this task (FR-024).

**Independent Test**: Freeze the benchmark, run the agreement pilot between the reference models, then score the training-free baseline with the task's harness. The report lists agreement per level with confidence intervals, contested cases separately, and the baseline's scores and run time on the reference hardware.

**Acceptance Scenarios**:

1. **Given** the guideline, **When** at least two frontier reference models from different families label the benchmark, **Then** their agreement is reported per level (duplicate, cluster) and cases they disagree on are marked contested and reported separately.
2. **Given** a level on which the reference models do not reach the agreement threshold, **When** the pilot ends, **Then** that level's definition is revised and re-piloted before any candidate is tuned or trained on it.
3. **Given** the training-free baseline, **When** it is scored, **Then** the deduplication and clustering scores are reported separately, each named as agreement with the named reference models on the named benchmark version.
4. **Given** thresholds of the baseline, **When** they are tuned, **Then** they are tuned on a development split, never on benchmark items.

---

### User Story 3 - Groups form a hierarchy of opportunities (Priority: P2)

The product researcher wants to see which needs belong together. The stage arranges duplicate groups into a hierarchy of clusters, so that a cluster can be read as an opportunity with sub-opportunities, and opens directly as the opportunity layer of an Opportunity Solution Tree.

**Why this priority**: Clusters are what turns a long list of needs into a map. They build on the groups of User Story 1.

**Independent Test**: Run the stage with clustering on the same texts. Check that every group has exactly one parent cluster or is a top-level node, that the hierarchy has no cycles, and that each cluster's counts equal the sum over its descendants.

**Acceptance Scenarios**:

1. **Given** duplicate groups, **When** clustering runs, **Then** every group and every cluster has at most one parent, the result is a forest without cycles, and every node can be traced down to its member quotes.
2. **Given** a cluster, **When** it is read, **Then** it shows the number of mentions, the number of independent sources and the distribution of actor type and evidence over everything below it.
3. **Given** a cluster, **When** it is read, **Then** it has a representative original quote and an empty statement slot, and no generated label.
4. **Given** two groups of the same kind where one states a more specific version of the other's need, **When** clustering runs, **Then** the more specific group is a child of the more general group, not merged into it.
5. **Given** a job and pains or gains that belong to it, **When** clustering runs, **Then** they can be in the same cluster, the cluster shows its distribution by kind, and filtering the result by kind yields one-kind lists without losing any group.

---

### User Story 4 - An opportunity map can be continued (Priority: P2)

A team works on its opportunity map for weeks. New texts arrive, and the team has merged, split and moved groups by hand. When the stage runs again, existing groups and clusters keep their ids, the team's corrections stay in place, and new items are added to existing groups where they belong.

**Why this priority**: An opportunity map is a living document. If ids change or manual work is lost on every run, the output can only be used once.

**Independent Test**: Run the stage on a set of texts, record a merge, a split and a move as corrections, add new texts and run again. Check that untouched groups keep their ids, that all three corrections hold, and that the change report lists what is new, grown, merged or split.

**Acceptance Scenarios**:

1. **Given** a previous result and new texts, **When** the stage runs again, **Then** every group and cluster whose members are unchanged keeps its id, and new items either join an existing group or form a new one with a new id.
2. **Given** recorded human corrections (merge, split, move), **When** the stage runs again, **Then** every correction is still in effect, and corrections take precedence over the automatic result.
3. **Given** a correction that refers to items no longer present, **When** the stage runs again, **Then** it is reported as stale, not silently dropped or silently applied.
4. **Given** two runs, **When** the second finishes, **Then** a change report lists new, grown, merged, split and removed groups and clusters with their ids.
5. **Given** the same inputs, corrections and settings, **When** the stage runs twice, **Then** the outputs are identical.

---

### User Story 5 - Downstream methods can attach their own information (Priority: P3)

A downstream step (a person or a later model) writes a normalised statement for a cluster, assigns groups to the steps of a job map or the stages of a journey, or marks a Kano category. These additions live in the same format and survive re-runs. Source dates travel with every item so that trends over time can be shown.

**Why this priority**: The format must not need to change for each method later on. The slots are cheap now and expensive to retrofit.

**Independent Test**: Add a statement and two assignments from different schemes to a cluster, mark one as human and one as model, run the stage again, and check that all three are still attached and that every item still carries its source date.

**Acceptance Scenarios**:

1. **Given** a group or cluster, **When** an assignment is added, **Then** it records the scheme, the value and whether a person or a model made it, and any number of schemes can coexist.
2. **Given** a statement or assignment on a group or cluster, **When** the stage runs again and the node keeps its id, **Then** the statement and assignments are kept.
3. **Given** source metadata with a date, **When** the output is read, **Then** every item carries that date, and items without a date are marked as undated.

### Edge Cases

- **A text with no items** (scout returned an empty list): it contributes nothing and is counted as processed, not as an error.
- **A single item that matches no other item**: it forms a group of one. Groups of one are valid and kept.
- **Very short or generic quotes** ("Das nervt.", "It's expensive."): they are grouped like any other item; the guideline states how far context from the quote alone can be used, and the stage never pulls in text outside the scout quote.
- **One author repeats the same complaint in several posts**: mentions count every occurrence; independent sources count the author or thread once where that metadata exists.
- **Source metadata missing** (no author, thread or date): independence falls back to the source id and the item is marked undated; the run does not fail.
- **The same quote extracted twice from overlapping texts** of one source: recognised as an exact copy and counted once.
- **A scout output in a different format version**: the stage refuses it with a clear message instead of guessing.
- **A human correction contradicts a kind rule** (merging a pain group with a job group into one duplicate group, or making a pain group the more specific child of a job group): refused with a message; kind separation of duplicates and of the specificity relation holds (FR-004). Moving groups of different kind into one cluster is allowed (FR-011).
- **A correction refers to an item that a later run no longer contains**: reported as stale (User Story 4, scenario 3).
- **Input far larger than the measured volume**: the stage still produces a correct result; the run time is reported, and the budget in FR-021 states what is guaranteed.
- **Reference models disagree on a pair**: the pair is contested and reported separately, never merged into the consensus score.

## Requirements *(mandatory)*

### Input

- **FR-001**: The stage MUST accept scout outputs in format `jtbd-span-v1` for any number of texts, together with per-source metadata: source id, source class, date, and, where available, author or thread. It MUST refuse any other format version with a message.
- **FR-002**: The stage MUST NOT change, shorten, translate or regenerate any quote, and MUST NOT read text outside the quotes and their recorded offsets.

### Deduplication

- **FR-003**: The stage MUST place every input item in exactly one duplicate group. Deduplication merges and MUST NOT delete: every member stays listed with its source id, offsets, kind, score, attributes and source date.
- **FR-004**: Items of different kind MUST NOT be in the same duplicate group.
- **FR-005**: Exact copies (identical quote from identical or copied source text, for example a text collected twice, a quoted forum reply or a repost) MUST be recognised deterministically, without a model, before any similarity step.
- **FR-006**: Each duplicate group MUST carry: its id, kind, members, one representative quote chosen deterministically from its members, the number of mentions, the number of independent sources, and the distribution of actor type, evidence type and evidence scope over its members.
- **FR-007**: Independent sources MUST be counted by author or thread where that metadata exists, otherwise by source id, and the record MUST state which rule was used.
- **FR-008**: What counts as a duplicate MUST be defined in a written guideline with examples in German and English. The guideline MUST label a pair of items as *same* (duplicate), *more specific than* (one states a narrower version of the other's need, for example "find a parking space downtown in the evening" vs. "find a parking space") or *different*. Only *same* merges items into one duplicate group.

### Clustering

- **FR-009**: The stage MUST arrange duplicate groups into a hierarchy in which every group and cluster has at most one parent, without cycles. A duplicate group whose need is a more specific version of another group's need of the same kind MUST be that group's child; otherwise a group's parent is a cluster or none.
- **FR-010**: Each cluster MUST carry: its id, its parent id (or none), its children, a representative original quote, and the number of mentions, the number of independent sources, the distribution by kind and the attribute distributions aggregated over all items below it.
- **FR-011**: A cluster MAY combine duplicate groups of different kind, so that a job and its pains and gains can form one cluster. Duplicate groups and the specificity relation (FR-009) MUST stay within one kind. Filtering the output by kind MUST yield one-kind lists in which every group of that kind appears exactly once.
- **FR-012**: Deduplication and clustering MAY be produced by one tool as two levels, but MUST be measured and reported separately.

### Output and downstream slots

- **FR-013**: The output MUST be one versioned, documented format (working name `jtbd-cluster-v1`) with the levels item, duplicate group and cluster, plus the run's settings, input format version and the ids of the inputs it was built from.
- **FR-014**: Every group and cluster MUST have a statement slot for a normalised statement (for example an outcome statement or an opportunity label). This feature MUST NOT fill it; it is empty unless a later step or a person writes it.
- **FR-015**: Every group and cluster MUST have a list of assignments, each with a scheme, a value and its origin (person or model, with the model's name). No scheme is built into the format, and no scheme MAY be used as input to extraction.
- **FR-016**: Every item MUST carry its source date, or be marked undated.

### Continuity and human corrections

- **FR-017**: When the stage runs again on extended input, every group and cluster whose members are unchanged MUST keep its id. When groups merge or split, the rule for which id survives MUST be fixed and documented, and the change MUST appear in a change report.
- **FR-018**: Human corrections (merge, split, move to another parent, set representative quote) MUST be stored separately from the automatic result, MUST take precedence over it on every later run, and MUST be reported as stale when they no longer apply.
- **FR-019**: Statements and assignments MUST stay attached to their group or cluster across runs as long as its id is kept.
- **FR-020**: Given identical inputs, corrections and settings, the output MUST be identical.

### Budgets

- **FR-021**: The stage MUST deduplicate and cluster the items of 10,000 texts (about 50,000 items) in at most 15 minutes, with at most 4 GB of RAM at peak, on the task's low-resource reference hardware (8 GB RAM, 4 vCPU, no GPU). It MUST NOT need a hosted API or network connection at runtime.

### Measurement

- **FR-022**: The task MUST have a frozen benchmark of item pairs and groups drawn from real scout outputs, labeled independently by at least two frontier reference models from different families under the guideline of FR-008: pairs as *same*, *more specific than* or *different*, and cluster membership across kinds. Benchmark manifests MUST contain hashes only, never text.
- **FR-023**: Scores MUST be reported per level: for deduplication pair precision, recall and F1 and B-cubed precision, recall and F1; for the specificity relation precision, recall and F1 of *more specific than*; for clustering B-cubed F1 and a measure of agreement on the hierarchy. Each number MUST be named as agreement with the named reference models on the named benchmark version, with a confidence interval, and contested cases MUST be reported separately.
- **FR-024**: Before any threshold is tuned or any model is trained, an agreement pilot MUST measure agreement between the reference models on each level. A level below its threshold MUST be redefined and re-piloted. Thresholds and kill criteria MUST be written down before the pilot runs.
- **FR-025**: The first candidate MUST be training-free (multilingual similarity with a kind filter and a threshold or hierarchical grouping), tuned on a development split only. A trained model MAY follow only if the baseline misses the quality bar set before measurement; it is then released under its own model name through the zoo's release pipeline. Every candidate MUST be reported on quality and on the budgets of FR-021.
- **FR-026**: Deterministic checks MUST run independently of any model judgment and be reported on their own: every input item in exactly one group, quotes byte-identical, no group mixing kinds, hierarchy without cycles, counts consistent with members, output valid against the format.

### Provenance and personal data

- **FR-027**: Benchmark items MUST come from scout outputs on corpus chunks that passed the JTBD corpus redaction, from sources whose records allow the use. Reference-model labels, benchmark text and development data MUST NOT be published, and their retention MUST be stated.
- **FR-028**: Items sent to a reference model MUST pass the existing pre-send personal data check and go only through approved labeling routes.

### Key Entities

- **Item**: One scout finding: kind, verbatim quote, source id, offsets, score, attributes, source date. Never altered.
- **Source**: A collected text with its metadata (id, class, date, author or thread where available). Defines independence.
- **Duplicate group**: Items of one kind that state the same need. Holds members, a representative quote, counts and attribute distributions, a statement slot and assignments. May be the child of a more general group of the same kind.
- **Cluster**: A node in the hierarchy above duplicate groups, possibly combining kinds. Holds parent, children, a representative quote, aggregated counts including the distribution by kind, a statement slot and assignments.
- **Assignment**: A link from a group or cluster to a value in an external scheme, with its origin.
- **Correction**: A human merge, split, move or choice of representative, stored apart from the automatic result and applied on every run.
- **Change report**: What a run changed compared with the previous one, by id.
- **Benchmark**: Frozen pairs and groups with reference labels, contested cases and a manifest of hashes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a run over real scout outputs, 100% of input items are in exactly one group, 100% of quotes are byte-identical to the input, and 0 groups mix kinds.
- **SC-002**: The agreement pilot reports, for each level, agreement between the reference models with a confidence interval and a go, revise or stop decision against thresholds written down before the pilot.
- **SC-003**: The training-free baseline reaches at least 85% of the reference models' mutual agreement on deduplication pair F1, or the gap is reported and a trained candidate is decided on (FR-025).
- **SC-004**: After adding 10% new texts to a previous run, at least 95% of groups whose members did not change keep their id, and 100% of human corrections that still apply remain in effect.
- **SC-005**: The items of 10,000 texts are deduplicated and clustered in at most 15 minutes with at most 4 GB of RAM on the reference hardware, without network access.
- **SC-006**: A person who did not build the stage turns one result into the opportunity layer of an Opportunity Solution Tree and into a list of needs with mention and source counts, without converting the format, in under 30 minutes.
- **SC-007**: Total cash spent on reference labeling and reference hardware stays at or below €20.

## Assumptions

- The task is new and lives in topic `productdev`, downstream of `jtbd` extraction. Its scope (in and out) is stated here as its first spec; a task document under `topics/productdev/tasks/` names reference, benchmark, metrics, tool and budget.
- Riskiest assumption (constitution IV): frontier reference models agree on what is the same need and what belongs together. The agreement pilot (FR-024) tests this before any tuning.
- Input is the output of `scout-large`; the format also accepts outputs of later scout variants or of reference models as long as they use `jtbd-span-v1`.
- Reference hardware is the one the JTBD task already uses (8 GB RAM, 4 vCPU, no GPU); development runs on the MacBook or the DGX Spark at no cash cost.
- Budget values in FR-021 are a first setting chosen to match scout's throughput; they can be revised in the plan with a recorded rationale.
- The quality bar for the baseline (SC-003) follows the pilot's 85%-of-reference mark; the go thresholds of the agreement pilot are set in the plan before it runs.
- The labeling backends, pre-send checks and consensus logic of `jtbd` are reused. Code is moved into a shared module only where this second task actually needs it (constitution, Tasks and Releases).
- The €20 cash budget is separate from earlier features' budgets.
- Out of scope: prioritisation and opportunity scoring; importance and satisfaction values (they come from surveys); generating normalised statements or labels; persona building; any ontology or fixed taxonomy; any change to scout or its training objective; a user interface for editing corrections (corrections are recorded in a file).

## Constitution Compliance

- **I. Problem-first**: No persona, segment or scheme is input to extraction or to grouping; assignments are added downstream (FR-015). Personas remain out of scope.
- **II. Grounded evidence**: Quotes are never changed, every group and cluster traces to verbatim member quotes, representatives are original quotes, no generated text (FR-002, FR-003, FR-006, FR-014).
- **III. Measure before optimizing**: Own frozen benchmark by two reference model families, contested cases separate, deterministic checks on their own, results named as agreement, quality reported with budgets (FR-022, FR-023, FR-025, FR-026).
- **IV. Riskiest assumption first**: Agreement pilot per level before tuning or training; thresholds and kill criteria written down first (FR-024).
- **V. Small and local**: Concrete budget on the reference hardware, no runtime API (FR-021).
- **VI. Clean provenance**: Benchmark from redacted, permitted sources; no published text or labels; pre-send check and approved routes (FR-027, FR-028).
- **VII. Metadata over inference**: Date, source class and author or thread come from source metadata, never predicted (FR-001, FR-007, FR-016).
- **VIII. Fair comparison**: Every candidate measured with the same benchmark and harness of this task (FR-025).
- **IX. Reproducible releases**: Deterministic output (FR-020); a trained model, if any, is released only through the release pipeline (FR-025).
- **X. Scope discipline**: Deduplication and clustering are a separate downstream stage; scout and its training objective are unchanged; prioritisation stays out of scope.
