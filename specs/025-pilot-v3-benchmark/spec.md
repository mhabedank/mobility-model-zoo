# Feature Specification: Benchmark pilot-v3 for scout guideline v3

**Feature Branch**: `claude/025-pilot-v3-benchmark`

**Created**: 2026-11-28

**Status**: Draft

**Input**: User description: "scout-large 0.2.0 roadmap phase 3: benchmark pilot-v3 for the guideline v3 package (owner hash-approved 2026-11-28). Build what the agreement pilot needs and then run it: a labeler-facing v2 wire schema and a prompt builder that renders the approved package; labeling in three passes; the metric sheet of the brief; a pilot-v3 benchmark config with a frozen holdout and an enriched link sub-sample; the agreement pilot with the two non-Claude references, full reference labeling if it passes, and the zero-shot baselines re-measured. Constraints: Principle XI, thresholds frozen before the pilot, budget per benchmark, German and English reported separately. Out of scope: teacher relabeling and model training."

## Purpose

scout-large 0.2.0 is selected and judged on a new benchmark, `pilot-v3`, whose reference labels come from two model families that are not Claude (roadmap phase 3; constitution Principle XI). The labels follow guideline v3. The owner approved its content after two Fable reviews and approved the assembled package with hashes on 2026-11-28 (`topics/productdev/guideline/scout-v3/package/approval.json`).

The benchmark carries more than the old one. Besides relevance and the items with their kind, actor and evidence, it covers the fields of the opportunity interface: kind of job, mode of transport, what the actor wants to improve, solution instead of need, the role and situation pointers, and three kinds of link between items. Each field must earn its place: it is produced only where the two references agree on it above a threshold fixed before the pilot, separately for German and English. A field that fails is listed as absent, so the gap stays visible.

This feature builds what that pilot needs, runs it and, if the core passes, labels and freezes the full benchmark. It ends with the zero-shot baselines measured on it. Teacher labels for the training data (phase 4) and any model training are separate features.

## Scope

- **In**:
  - fetching, chunking and redacting new benchmark sources until the samples can be filled;
  - the labeler-facing output schema of guideline v3;
  - the prompt that renders the approved package;
  - labeling in three passes;
  - the metric sheet and decision rule of the brief;
  - the pilot-v3 benchmark config, its chunk texts, holdout and enriched link sub-sample;
  - the budget config of the benchmark;
  - the agreement pilot per field and per language;
  - one guideline revision round if the decision rule calls for it;
  - full reference labeling;
  - the frozen benchmark;
  - the zero-shot baselines;
  - the pilot report.
- **Out**:
  - teacher relabeling and `span-train-v2` (phase 4);
  - training, tuning or selecting a model (phases 5 to 8);
  - cairn reading `jtbd-span-v2`;
  - changes to the content of guideline v3 outside the revision round the decision rule allows.

## Clarifications

### Session 2026-11-28

- Q: pilot-v2 holds only 180 chunks (German 92 main and 19 holdout, English 58 main and 11 holdout). That is fewer than the pilot alone needs. Where do the additional benchmark texts come from? → A: Reuse the pilot-v2 texts, and fetch new sources whose permitted use includes benchmarking from the resource index. They are chunked and redacted like the existing ones, and share no source with any training data (FR-008).
- Q: What is the cash cap of the pilot-v3 budget? → A: EUR 25, covering the remote reference and the zero-shot baselines; the local reference costs no cash (FR-016).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Label a chunk with the approved guideline (Priority: P1)

The owner starts a labeling run with one of the two references on a set of benchmark chunks. The run reads the approved guideline v3 package, refuses to start if the package changed or lost its approval, labels each chunk in three passes and stores one output per chunk in the labeler-facing v2 format, with every pass's raw answer kept.

**Why this priority**: Nothing else can run without it, and it shows on its own that the guideline is usable by a model that is not Claude.

**Independent Test**: Run one reference on a handful of chunks with a mock and with a real backend. Each stored output validates against the v2 labeler schema. The guideline text in the prompt is byte-identical to the approved package. A changed package file stops the run with exit 3, and an unapproved package stops it with exit 7.

**Acceptance Scenarios**:

1. **Given** the approved package, **When** a reference labels a chunk, **Then** pass 1 yields the items with quote, kind, actor type, evidence type and scope; pass 2 adds the other attributes and the pointers to those fixed items; pass 3 adds links if the chunk has at least two items.
2. **Given** a pointer in pass 2 that is not a verbatim part of the chunk, **When** the output is stored, **Then** the pointer is empty and the run counts it as invalid; it is not retried.
3. **Given** a model id or backend that is Claude, **When** a run is started, **Then** it stops with exit 7 before anything is sent.
4. **Given** a chunk with fewer than two items, **When** pass 3 would run, **Then** it is skipped and the chunk has no links.

---

### User Story 2 - Score the agreement pilot per field and language (Priority: P1)

After both references have labeled the pilot chunks, the owner runs the agreement step. It matches the items of the two references one to one. It computes each field's agreement figure as the brief defines it, with a bootstrap interval over chunks, separately for German and English. It applies the decision rule and writes a report that says for every field and language: produced, revise, extend, underpowered or not produced, and whether a keep-always field stopped the pilot.

**Why this priority**: The pilot result decides which fields scout-large 0.2.0 may produce. Without it the benchmark cannot be frozen.

**Independent Test**: Feed two hand-made label sets with known agreement into the step and check every figure, interval and decision against values computed by hand. Include a field with fewer than 30 units, a field between floor and threshold, and a keep-always field below its floor.

**Acceptance Scenarios**:

1. **Given** two label sets, **When** items overlap with token IoU of at least 0.5, **Then** they are matched one to one, the highest overlap first, and item F1 is reported both at this cutoff and at any overlap.
2. **Given** matched items, **When** list fields are scored, **Then** mode and improve use Krippendorff's alpha with the MASI distance, and two empty lists count as agreement.
3. **Given** links of both references, **When** links are scored, **Then** only links between matched items count, with the end-to-end figure reported beside them.
4. **Given** a field with fewer than 30 units, **When** the rule is applied, **Then** the field is marked underpowered and the sample is extended once before any other decision.
5. **Given** relevance or item matching below its floor in one language, **When** the rule is applied, **Then** the pilot stops in that language and the report says the guideline goes back to the owner.

---

### User Story 3 - Draw and freeze the pilot-v3 chunks (Priority: P2)

The owner prepares the benchmark chunks:

- a random pilot sample of 100 chunks per language;
- a holdout of the same size, kept locked;
- an enriched link sub-sample of 100 chunks per language, extendable once to 200, drawn only from chunks in which code finds a word of the closed connective lists;
- the remaining chunks for full labeling.

All chunks pass the redaction pipeline. None shares a source with any training data. Their ids and hashes are frozen together with the guideline package hashes, the label schema and the criteria before any reference labels them.

**Why this priority**: The pilot needs the samples, but the sampling logic can be built and tested before the texts exist.

**Independent Test**: Run the draw on a fixture corpus. The samples are disjoint, reproducible from the seed and per language, and the enriched sample contains only chunks with a connective. The freeze refuses later changes without a new version and a rationale.

**Acceptance Scenarios**:

1. **Given** the chunk pool, **When** the samples are drawn twice with the same seed, **Then** they are identical.
2. **Given** the enriched sub-sample, **When** link prevalence is reported, **Then** it is computed from the random pilot only.
3. **Given** a frozen benchmark, **When** a chunk, the guideline package or the criteria change, **Then** labeling refuses to run (exit 3).

---

### User Story 4 - Label the full benchmark and measure the baselines (Priority: P3)

If the pilot passes in a language, both references label the full benchmark in that language with the same three passes. The consensus and contested entries are frozen per field. The zero-shot baselines are measured on the frozen benchmark with the same passes and scored against the consensus.

**Why this priority**: This is the end product for phase 5 onwards. It depends on the pilot passing.

**Independent Test**: On a fixture benchmark with mock backends, the full run produces consensus and contested files per field and language, and the baseline scores use exactly the fields that passed.

**Acceptance Scenarios**:

1. **Given** a field that is not produced in a language, **When** the benchmark is frozen, **Then** the field is absent from that language's consensus and listed as absent in the benchmark manifest.
2. **Given** the frozen benchmark, **When** a baseline is scored, **Then** its figures are reported per field and per language with bootstrap intervals.

### Edge Cases

- **Divergent items:** the references find different items, so few are matched. Item matching F1 decides, and attribute agreement is computed only on the matched items, so a field can look good on few units. The unit count is always reported, and fields under 30 units are underpowered.
- **No items in the pilot sample:** a language has no items at all in the pilot sample. Every field is underpowered, and the sample is extended once.
- **Unparseable pass 2 or 3:** a reference returns an answer that cannot be parsed. It is retried a fixed number of times and then recorded as an excluded chunk, never repaired by hand.
- **Model version changes mid-run:** the run stops, as the current runner already does.
- **Changed guideline:** guideline v3 is changed in the revision round. The package is assembled and approved again, and the revised fields are scored on the fresh holdout, never on the pilot sample again.
- **Busy local GPU:** the local reference's GPU is shared with other work. The run is resumable and keeps finished chunks.
- **Mixed-language chunk:** a chunk mixes languages. It is counted under its main language, as detected by code.

## Requirements *(mandatory)*

### Functional Requirements

**Labeling**

- **FR-001**: The labeling output of guideline v3 MUST follow a labeler-facing schema that mirrors `jtbd-span-v2`, but without scores, character offsets and the language field. Code adds the offsets by locating quotes and pointers, and adds the language by detection.
- **FR-002**: The system prompt of a v3 run MUST be built from the approved package only: the guideline text and the example files, byte for byte, plus fixed output instructions. Every run MUST check the package with `jtbd guide check` first: exit 3 for a changed package, exit 7 for an unapproved one with Claude drafts.
- **FR-003**: A v3 run MUST label in the three passes of the brief (`assembly.passes`).
  - Pass 1 returns items with quote, kind, actor type, evidence type and scope.
  - Pass 2 receives the fixed items and returns the remaining attributes and the pointers.
  - Pass 3 receives the fixed items and returns links; it runs on every chunk with at least two items.
  - Each reference runs all passes on its own items.
  - Raw answers of every pass MUST be stored and never overwritten.
- **FR-004**: A quote that cannot be located verbatim MUST follow the existing quote rule. A pointer that cannot be located MUST be set to empty and counted per field and run; it MUST NOT be retried.
- **FR-005**: The zero-shot baselines MUST use the same three passes and prompts as the references.
- **FR-006**: Every run MUST pass the Claude gate (exit 7) and record the model that produced each pass.

**Benchmark data**

- **FR-007**: The benchmark MUST draw:
  - a random pilot sample of 100 chunks per language;
  - a locked holdout of the same size;
  - an enriched link sub-sample of 100 chunks per language, extendable once to 200, drawn only from chunks in which code finds a word of `link_connectives`;
  - the full benchmark from the remaining chunks.

  All draws MUST be seeded and reproducible.
- **FR-008**: The benchmark chunks MUST come from the pilot-v2 chunk texts (labels not used) plus new sources from the resource index whose permitted use includes benchmarking. New sources are fetched once, registered, chunked and redacted with the existing pipeline. Every chunk MUST pass redaction and share no source (snapshot, normalised URL, content hash or supersession) with any training data. Enough chunks per language MUST exist to fill all the samples of FR-007 before the benchmark is frozen; the report states how many came from each source class.
- **FR-009**: Before any reference labels a chunk, the system MUST freeze in one benchmark manifest the chunk ids and text hashes, the guideline package hashes, the labeler schema, the criteria (the thresholds and decision rule of the brief) and the budget config. A later change MUST need a new version with a rationale.

**Agreement and decision**

- **FR-010**: The agreement step MUST compute every figure of `pilot_thresholds.definitions` and `reported_only`, per field and per language, with 95 % bootstrap intervals that resample chunks. That includes:
  - item matching;
  - kappas on matched items;
  - weighted kappa for evidence type;
  - MASI alpha for list fields;
  - two numbers per pointer;
  - links on matched pairs;
  - the order-relation kappa.
- **FR-011**: The decision step MUST apply the brief's `decision`, `keep_always_stop` and `per_language` rules exactly. Each field and language MUST get one outcome: produced, revise, extend, underpowered, not produced or pilot stopped. The figures and unit counts behind each outcome MUST be reported.
- **FR-012**: If a field falls in the revise band, one guideline revision round MUST be possible. The owner approves the revised package again, and the revised field is scored on the fresh holdout. A second revision MUST NOT be possible in this feature.
- **FR-013**: The pilot report MUST state:
  - link prevalence from the random pilot only;
  - the invalid-pointer counts;
  - excluded chunks;
  - the cost per reference;
  - all figures separately for German and English.

**Full benchmark**

- **FR-014**: If the core passes in a language, both references MUST label the full benchmark of that language. The system MUST then freeze consensus and contested entries per field, keep the holdout locked, and list every field that is not produced as absent in the manifest.
- **FR-015**: The system MUST measure the zero-shot baselines on the frozen benchmark, per field and language, with bootstrap intervals.

**Budget and compliance**

- **FR-016**: The benchmark MUST have its own budget config. Labeling MUST refuse to run past it, as the existing budget guard does. The cash cap is EUR 25, covering the remote reference and the zero-shot baselines; the local reference costs no cash.
- **FR-017**: Texts sent to the remote reference MUST use only its signed-off route (`deepseek-v41flash-openrouter-digitalocean`, allowed for references only) and pass the existing pre-send compliance checks.

### Key Entities

- **Guideline package**: the approved guideline v3 (`guideline.md`, 16 example files, `package.json`, `approval.json`). It is read only; any change means a new assembly and a new approval.
- **Labeler output (v3)**: what a reference returns for one chunk after the three passes: relevant, items with attributes and pointers, links. It validates against the labeler-facing schema.
- **Pass record**: the raw answer, parsed answer, model version and validity counts of one pass on one chunk.
- **Benchmark manifest (pilot-v3)**: the frozen chunk ids and hashes, the samples (pilot, holdout, enriched, full), the package hashes, the schema, the criteria, the budget, the reference run ids, the per-field outcome per language, and the fields listed as absent.
- **Agreement report**: per field and language, the estimate, interval, unit count, outcome and the figures reported only.
- **Consensus and contested entries**: per field and language, the entries both references agree on and those they do not. Contested entries are kept, not dropped.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every output stored by a v3 labeling run validates against the labeler schema. Every quote and pointer in it is a verbatim part of its chunk or is recorded as invalid. That holds for 100 % of stored outputs.
- **SC-002**: The agreement step reproduces hand-computed figures on a fixture with known answers to the third decimal. The decision step gives the outcome the brief's rules prescribe for every case in that fixture.
- **SC-003**: The pilot report gives an outcome with estimate, interval and unit count for every field in the brief, in German and in English. No field is decided on fewer than 30 units without being marked underpowered.
- **SC-004**: No labeling, scoring or baseline run of this feature records a Claude model. Every run checked the guideline package before sending anything. Both are shown by the gate fields of all run manifests.
- **SC-005**: The benchmark manifest is frozen before the first reference label is written. Every later change is recorded as a new version with a rationale.
- **SC-006**: The cash spent stays within the budget config, and the report states the actual cost per reference.
- **SC-007**: If the pilot passes, the frozen pilot-v3 holds consensus labels per produced field for both languages, and every baseline is scored on it. If the pilot stops in a language, the report says which field stopped it and why.

## Assumptions

- **Fixed inputs.** The brief's metric definitions, thresholds, decision rule, sample sizes and connective lists are the provisional values approved by the owner on 2026-11-28. This feature freezes them before the pilot (Principle IV) and does not change them, except through FR-012.
- **References.** The two references are the default of the roadmap: `ref-qwen3.8-27b`, run locally, and `ref-deepseek-v4.1-flash` on its signed-off route. Both are registered on `main` (PR #62).
- **Constitution.** Constitution 3.2.0 (PR #64) and the guideline v3 work (PRs #63 and #65) are merged before the first real labeling run. Code and tests can be built before that.
- **Full benchmark size.** The full benchmark is sized after the pilot. The size is chosen so that bootstrap intervals separate about 2 F1 points per language, computed from the pilot's variance, and written down before full labeling starts.
- **Old labels unused.** The Claude reference labels of pilot-v2 are not read, used or compared with anything in this feature. Only chunk texts may be reused, because texts are not Claude output.
- **Existing machinery reused.** The redaction pipeline, the budget guard, the run manifests, the freeze mechanism and the Claude gate stay as they are and are reused.
- **Language.** Code detects the language per chunk. German and English are the only languages in this benchmark.
