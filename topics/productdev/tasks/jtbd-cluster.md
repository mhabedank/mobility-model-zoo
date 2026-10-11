# Task: Deduplication and clustering of JTBD items (`jtbd-cluster`)

Stage between the extraction model (`scout-large`, output `jtbd-span-v1`) and the opportunity methods (Opportunity Solution Tree, outcome-driven opportunity landscape and similar). Spec: [specs/009-jtbd-dedup-cluster/spec.md](../../../specs/009-jtbd-dedup-cluster/spec.md).

## Scope

- **In:** merging items that state the same need into duplicate groups (within one kind); the relation "more specific than" between groups of one kind; clusters of groups across kinds in one or two levels; counts of mentions and independent sources; continuity across runs (stable ids, human corrections, change report); empty slots for statements and assignments; source dates.
- **Out:** prioritisation and opportunity scoring; importance and satisfaction values (they come from surveys); generating normalised statements or labels; personas; any ontology or fixed taxonomy; changes to scout or its training objective (constitution X).

## Reference

Model-labeled task. The reference is the consensus of two frontier reference models from different families, `claude-reference` (anthropic-claude) and `gpt-mini-reference` (openai-gpt), on the frozen benchmark `cluster-v1`, labeled under the guideline [guideline/cluster-v1/](../guideline/cluster-v1/guideline-cluster-v1.md). Pairs on which the two disagree are contested and reported separately. Every metric is reported as agreement with these reference models, never as accuracy.

## Benchmark `cluster-v1`

Built from outputs of the released `scout-large` on stored, redacted chunks (pilot-v2 main split and `span-train-v1`; the pilot holdout is never used). Sources are split by snapshot into development (30%) and test; thresholds are tuned on development only.

- **Pairs** (same kind): 1,200 test, 400 development and 300 holdout pairs, stratified by similarity under two samplers that are not candidates (LaBSE cosine and a lexical token-set ratio).
- **Sets** (any kind): 12 test, 4 development and 4 holdout sets of 40 items, each a seed item and its neighbourhood, labeled as a fine partition and an optional coarser one.
- The manifest under `topics/productdev/benchmarks/cluster-v1/` holds hashes only, never text.

## Metrics

| Measurement level | Metric | Against |
|---|---|---|
| duplicate | pair precision, recall, F1; B-cubed precision, recall, F1 | consensus of the reference models |
| specificity | precision, recall, F1 of "more specific than" | consensus of the reference models |
| cluster (per produced level) | B-cubed F1 | each reference model's partition |
| reference agreement | Cohen's kappa (duplicate, specificity), B-cubed F1 (clusters) | reference model against reference model |

Thresholds for the agreement pilot are frozen in `configs/productdev/jtbd/cluster-criteria.yaml` before labeling. A measurement level that fails the pilot is not produced.

## Tool

`uv run jtbd cluster …` (`collect`, `run`, `check`, later `bench`, `freeze`, `label`, `agreement`, `decide`, `tune`, `score`, `perf`, `correct`, `annotate`, `report`). Package `src/mobility_model_zoo/productdev/jtbd/cluster/`. Data and outputs live in `data/cluster/`, never in the repository.

## Riskiest assumption

The reference models agree on what is the same need and what belongs together. The agreement pilot measures this per level before any threshold is tuned (constitution IV).

## Hardware budget

Reference hardware as for extraction: 8 GB RAM, 4 vCPU, no GPU. 50,000 items deduplicated and clustered in at most 15 minutes with at most 4 GB peak RAM, without a hosted API and, after the models have been downloaded once, without network access. Every measurement records whether it used real items or the labeled scale set.

## Status

Feature 009 in progress: deduplication (user story 1) implemented and tested on fictional fixtures with fixed vectors. Real encoders wait for pinned revisions and recorded licences; no benchmark, no measurement yet.
