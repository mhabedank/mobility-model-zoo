# Roadmap: scout-large 0.2.0 and after

Date: 2026-11-27. Status: plan, nothing started. Builds on the [architecture research](README.md) and on the owner decision of 2026-10-14 (option A, [`D-xi-teacher-labels-0.1.x`](../../../../compliance/decisions.yaml)).

## Decisions taken for this roadmap

| Question | Decision (owner, 2026-11-27) |
|---|---|
| Scope of 0.2.0 | Clean rebuild (option A) plus the unit-level head on XLM-R-large, calibration and the cheap speed fixes. Backbone comparison, distillation and INT8 come after 0.2.0. |
| Who writes the new labeling guideline | The owner writes a brief in their own words; a local non-Claude model turns it into guideline and examples; the owner approves. Same pattern as `cairn-teacher-v1`. |
| A small distilled model | Becomes its own model, `scout-small`, with its own card and release bar. scout-large stays the quality model and serves as its teacher. |
| Fit to the opportunity methods | The output must carry everything the Opportunity Solution Tree and the ODI opportunity landscape need from texts, so nothing is missing later. The interface is a quality criterion next to the scores. The new outputs go into guideline v3 and 0.2.0, not into a later version. See [the opportunity interface](../opportunity-interface/README.md). |
| Field list of 0.2.0 | Confirmed as listed in the opportunity interface: kind of job, role span, actor pairs, mode of transport, situation span, what the actor wants to improve, solution instead of need, means-end edges, order edges, language. Each field still has to pass its own agreement pilot in phase 3. |

## Where scout-large stands

scout-large 0.1.3 (weights of 0.1.0) is published as `experimental`. On `pilot-v2` it reaches a comparison composite of 0.72 against 0.67 for the best zero-shot baseline. Relevance kappa is 0.54 and item-matching F1 is 0.59, while the attributes reach kappa 0.76 to 0.85. On the reference machine (4 vCPU, 8 GB) it needs 8.1 s and 2.5 GB for the 9,240-character interview. The two criteria still open for `released` are the reader test and the clean-machine run.

Two facts set the frame for 0.2.0:

1. **The training data must be rebuilt.** Claude wrote guideline-v2 and examples-v2, which were the teacher's system prompt for `span-train-v1` ([provenance report](../../compliance/2026-10-14-guideline-provenance-principle-xi.md)). Option A replaces them: a new guideline and new examples written without Claude, a new benchmark labeled without Claude, teacher relabeling and a new scout-large version. 0.1.x stays published unchanged.
2. **The research names the head as the bottleneck, not the encoder.** Items are whole sentences or clauses, but the model decides token by token. A job that spans several sentences therefore falls apart into two items.

## Corrections to the research under Principle XI

The research was written without the option A frame. Three of its proposals change:

| Research proposal | Problem | What the roadmap does instead |
|---|---|---|
| Measure on `pilot-v2`, with inter-LLM agreement as upper bound | `pilot-v2` references include Claude labels. Principle XI keeps them only as frozen references for 0.1.x; they must not drive selection, tuning or success criteria of a new model. | 0.2.0 is selected and judged on a new benchmark, `pilot-v3`, labeled by two non-Claude model families. 0.1.3 is re-scored on `pilot-v3` as the baseline. `pilot-v2` figures appear only as history. |
| Soft labels from the disagreement of the teacher and the two reference LLMs (the 1,574 disputed items) | One of the two references is Claude. | Soft labels come only from non-Claude labelers of the training split: the teacher plus a second teacher of another family. The benchmark references never become training data. |
| EdgeCoder-Multilingual-61M as a student candidate, if the language expansion stays in Europe | The zoo roadmap already names Spanish, Polish **and Japanese** as the next languages (`scout-large-languages`). | EdgeCoder-M leaves the comparison unless Japanese is dropped. The sentence segmenter must handle Japanese from the start of `scout-small` work. |

## 0.2.0 in nine phases

The order follows the research: first be able to measure, then pull the safe levers, then change the formulation. Every score is reported for German and English separately; a change that helps one language and hurts the other does not pass.

| # | Phase | Main output | Exit criterion | Depends on |
|---|---|---|---|---|
| 0 | **Infrastructure on `main`** | Claude gate (`labeling/gate.py`), registry entries of the non-Claude reference models, the reference routes and constitution 3.1.0. Today these live only on the unmerged cairn branch (73 commits ahead of `main`). | `jtbd label` on `main` refuses any Claude model (exit 7) | none |
| 1 | **Interface contract** | The field list of [the opportunity interface](../opportunity-interface/README.md) confirmed by the owner, and a draft of the output format `jtbd-span-v2`: the new item attributes (kind of job, mode of transport, what the actor wants to improve, solution instead of need), span pointers (role of the executor, situation), actor pairs, means-end and order edges, and the language. Each field names the method step it feeds. | Field list confirmed by the owner (2026-11-27); schema draft committed once the brief fixes the value lists | none |
| 2 | **Guideline v3** | Owner brief → guideline and examples by a local non-Claude writer → owner approval with hashes. The brief covers the core items and every field of phase 1; definitions and value lists are the owner's. Allowed inputs: the requirement lists of 001 T043/T044, the qwen categories of the contested entries and the GPT side of those pairs (`D-xi-rewrite-requirements`, `D-xi-contested-input`). The old guideline texts, examples and `revisions.md` are not inputs. | `approval.json` for guideline-v3 | 0, 1 |
| 3 | **Benchmark `pilot-v3`** | Fresh reference labels by two non-Claude families (default: the cluster-v3 pair, qwen3.8-27b local and deepseek-v4.1-flash on the signed-off route). Agreement pilot first, **per field and per language**, then full labeling. A field that misses its pilot threshold is not produced and is listed as absent. Chunk texts of `pilot-v2` may be reused, since texts are not Claude output; its labels are not. Size chosen so that bootstrap intervals separate about 2 F1 per language. Zero-shot baselines re-measured. | Core references agree above a threshold fixed before the pilot; each new field passed or recorded as absent; benchmark frozen with a holdout | 2 |
| 4 | **Training data `span-train-v2`** | Teacher pilot on `pilot-v3` dev, teacher relabeling of the existing training chunks, then several thousand more chunks with a set target per language (at least 30% German, which v1 missed with 28%). A second teacher of another family labels the same split for soft labels. Redaction pipeline unchanged. | Rows frozen; language targets met; cost within the budget config | 2, 3 (teacher choice) |
| 5 | **Measurement basis** (research experiment 0) | Document-grouped 5-fold cross-validation, 3 seeds, bootstrap over documents, scores split into consensus and disputed items, reference agreement as ceiling. Runs tracked in MLflow (feature 017). | Intervals narrow enough to separate 2 F1 per language | 3, 4 |
| 6 | **Cheap fixes** (experiment 1) | Windows at sentence boundaries with 32 to 64 tokens of overlap, max-context stitching, ONNX export, temperature scaling for relevance and attributes, a span calibrator, a review band (accept, review, reject) | Brier and ECE fall; item F1 equal or better; per language | 5 |
| 7 | **Unit-level head** (experiment 2) | Deterministic sentence and clause segmentation with offsets (German and English now, built so that Spanish, Polish and Japanese can follow), unit CRF or biaffine over units, item-pooled attributes with an ordinal loss for evidence type, relevance derived from items, normalised losses, soft labels from phase 4. **Interface heads**: one head per new item attribute, span pointers within the item's window, and a relation head over pairs of items for actor pairs, means-end and order edges. | Item F1 and composite above the control beyond the bootstrap interval, per language; the new heads do not pull the core below the same model without them | 5, 6 |
| 8 | **Selection and release** | Three benchmark candidates (the cap in the recipe), each with its reason written down before scoring: **C1** the 0.1.x architecture retrained on `span-train-v2`, the control that separates the data effect from the head effect; **C2** the unit head with the interface heads; **C3** C2 with soft labels. Interface tests I1 to I5. Perf on the reference VM, card, staging, release. | Release bar below | 7 |

Phases 2 and 3 carry the risk, and the new fields add to it: every field needs its own agreement between the references. The cairn work showed that two references can fail to agree on a fuzzy label (duplicate kappa 0.40 on cluster-v2). The same stop rule applies here: if the `pilot-v3` agreement pilot misses its threshold, the guideline goes back to the owner once. If it misses again, the item definition is rethought before anything is trained.

### Release bar of 0.2.0 (to commit before the first training run)

Principle IV requires the bar in the new recipe config before training. Proposal:

- Keep the 0.1.x bar: beat every zero-shot baseline on the comparison composite; quotes, schema and consistency at 100%; at most 4 GB peak memory; at most 10 s for the 9,240-character interview on the reference machine.
- New: beat 0.1.3, re-scored on `pilot-v3`, on item-matching F1 and on relevance beyond the bootstrap interval, in German and in English.
- New: report calibration (ECE, Brier) for relevance and the item score on the card.
- New: pass the interface tests I1 to I4 of [the opportunity interface](../opportunity-interface/README.md): contract, lossless build of the OST and ODI exports, traceability to quotes, agreement per field. A field that failed its pilot goes on the card as an unmet criterion.
- New: the practitioner test I5 (an outside person reaches the opportunity layer of an OST in under half an hour). Together with the reader test it is required for `released`, not for `experimental`.
- For status `released`, also run the reader test and the clean-machine run on the 0.2.0 card. That replaces the open `scout-large-reader-test` entry for 0.1.x. Without them 0.2.0 goes out as `experimental` with an honest card.

The thresholds of the new conditions are the owner's to set.

## After 0.2.0

| Track | Content | Research experiment | Precondition |
|---|---|---|---|
| **scout-small 0.1.0** (new model) | Backbone comparison with the unit head: mDeBERTa-v3-base, mmBERT-base, mmBERT-small, GLiNER2.5-multi fine-tuned; XLM-R-large as reference; learning-rate sweep and 3 seeds each. Then distillation from scout-large 0.2.0 on 100k+ unannotated mobility texts that already include Spanish, Polish and Japanese, with the LLM-labeled rows as anchor. Then dynamic INT8 with validation (at most 0.5 F1 loss per language) and thread pinning. No vocabulary trimming. | 3, 4, 5 | scout-large 0.2.0 released; a licensed unannotated corpus |
| **scout-large more languages** (existing roadmap entry `scout-large-languages`) | Spanish, Polish, Japanese: sources with `training_allowed`, per-language test sets labeled by non-Claude references, a segmenter for Japanese, per-language thresholds | none | Resource index first version (already the precondition on the roadmap) |
| **Risk control** | Conformal sets or risk control, per language | from the confidence notes | Several hundred calibration documents per language |
| **cairn reads `jtbd-span-v2`** (cairn feature) | cairn's input schema is pinned to `jtbd-span-v1`. The next cairn feature reads v2, carries the new fields into groups and clusters, and builds the OST and ODI exports that interface test I2 needs. Test I2 can only pass for 0.2.0 once this exists, so it runs in parallel with phases 5 to 7. | none | phase 1 (format draft) |
| **Moments and job steps** (cairn feature) | Fill the assignment slot for experience-map moments and job-map steps from the situation spans and order edges | none | scout-large 0.2.0 with those fields |

The research expects scout-small to read the interview in about 0.3 to 1.5 s on four CPU cores, against 8.1 s today. That is an estimate from parameter counts, not a measurement.

## Open points

- **Brief seeding:** the field list is confirmed (2026-11-27). Still open: whether the requirement list of the opportunity interface may seed the owner's brief in the same way as the 001 lists (`D-xi-rewrite-requirements`).
- **Phase 0 route:** either the cairn feature (022) merges first and brings the gate with it, or the gate, registry and constitution 3.1.0 are extracted into a small PR of their own. The second option does not wait for cairn.
- **Writer model for phase 1:** a local non-Claude model with a clean licence, chosen when the brief exists.
- **Teacher for phase 3:** decided by the teacher pilot. The 0.1.x teacher (`teacher-or-mimo-v2.6-pro`) is a candidate, not a default.
- **Label budget:** a new budget config per dataset and benchmark. Local labeling on the DGX Spark is slow (about 10 minutes per 20 cluster pairs for qwen in October), and the GPU is shared with other work.
- **Zoo roadmap entry:** once this plan is accepted, add a `scout-large` 0.2.0 entry to `zoo/roadmap/roadmap.yaml` and replace `scout-large-reader-test`.
