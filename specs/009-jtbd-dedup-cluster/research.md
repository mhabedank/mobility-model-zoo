# Research: Deduplication and clustering of JTBD items

Feature: [spec.md](spec.md) · Plan: [plan.md](plan.md) · Date: 2026-10-09

Each entry: decision, rationale, alternatives considered. No spike or pilot measurement sets a rule here; numbers below are starting values that the agreement pilot and the development split confirm or replace (constitution IV).

## R1. Where the task lives: `jtbd cluster`, package `productdev/jtbd/cluster/`

- **Decision**: New task `jtbd-cluster` in topic `productdev`. Code in the subpackage `src/mobility_model_zoo/productdev/jtbd/cluster/`, commands as the sub-app `jtbd cluster …`, configs in `configs/productdev/jtbd/`, task document `topics/productdev/tasks/jtbd-cluster.md`.
- **Rationale**: The stage consumes JTBD items and reuses the JTBD settings, data layout, labeling backends, budget ledger, freeze manifests, pre-send checks and bootstrap metrics. Placing it next to `span/` reuses them by import; nothing has to be moved into a shared module yet (constitution, Tasks and Releases: extract shared code only when a second task needs it). The task keeps its own benchmark, metrics and harness, so it is a separate task with its own tool surface, as `security can-ids` is under `security`.
- **Alternatives**: a separate top-level CLI (`cluster`), rejected: duplicates settings and labeling plumbing; a shared `productdev/common/` module now, rejected: premature extraction.

## R2. Input bundle `jtbd-cluster-input-v1`

- **Decision**: One JSON Lines file per run. Each line is one source: `source_id`, `source_class`, `date` (or null), optional `origin` (thread or URL path that groups replies), optional `text_sha256`, and the unchanged scout output (`jtbd-span-v1`). `jtbd cluster collect` builds such a bundle from stored corpus chunks and span runs; external users write it themselves.
- **Rationale**: Scout outputs carry no source metadata; the stage needs date, class and an independence key (FR-001, FR-007, FR-016). A bundle keeps the stage usable outside the zoo's own corpus.
- **Alternatives**: reading the corpus store directly, rejected: ties the stage to the zoo's data layout and excludes users' own texts.

## R3. Independent sources without author metadata

- **Decision**: The independence unit is `origin` when given, else `source_id`; sources with the same `text_sha256` collapse into one unit. Author names are not used.
- **Rationale**: The corpus removes usernames before labeling (constitution VI), so author metadata does not exist in the zoo's data and must not be reintroduced. For forums, the thread URL is the closest lawful proxy. The rule used is recorded per group (FR-007).
- **Alternatives**: pseudonymous author hashes, rejected: re-identifiable linkage of a person's posts, against data minimisation.

## R4. Exact copies before any model (FR-005)

- **Decision**: Normalise each quote (Unicode NFKC, casefold, collapse whitespace, strip surrounding punctuation) and hash it with its kind. Items with the same key are must-linked before similarity. Within one independence unit they count as one source; across units as separate sources.
- **Rationale**: Deterministic, cheap, explains reposts and quoted replies. Two different threads with the same sentence are still two independent mentions.
- **Alternatives**: MinHash near-duplicate detection, rejected for v1: near-identical paraphrases are the similarity step's job.

## R5. Text representation: multilingual sentence embeddings of the quote only

- **Decision**: Embed each quote alone with a multilingual encoder via `transformers` (mean pooling, L2 normalisation, model's required prefix such as `query: ` for E5). Candidates, at most three on the benchmark: `intfloat/multilingual-e5-small` (MIT), `intfloat/multilingual-e5-base` (MIT), `Alibaba-NLP/gte-multilingual-base` (Apache-2.0). Model id and revision are pinned in the stage config; licence basis is recorded there.
- **Rationale**: German and English in one vector space (User Story 1, scenario 5); permissive licences for commercial use; base-size models fit the time budget on 4 vCPU. The quote alone respects FR-002.
- **Alternatives**: `BAAI/bge-m3` (MIT), measured once as an informative ceiling, too slow for FR-021 on the reference VM; LaBSE, reserved for benchmark sampling (R10) so the sampler is not a candidate; models with non-commercial licences, excluded.

## R6. Embedding cache

- **Decision**: Embeddings are cached in the map directory, keyed by (model id, revision, normalised quote hash). A re-run embeds only new quotes.
- **Rationale**: Re-runs become fast, and old items keep bit-identical vectors, which keeps ids stable (FR-017, FR-020) even across library updates.
- **Alternatives**: recompute each run, rejected: slow and can flip edge cases on another machine.

## R7. Deduplication: sparse neighbour graph and average linkage within kind

- **Decision**: Per kind, compute the k nearest neighbours (k = 30, cosine, in blocks) and keep edges above a candidate floor. Agglomerative clustering with average linkage on that sparse connectivity, cut at distance `1 − t_dup`. Exact-copy must-links are merged first. `t_dup` is tuned on the development split for pair F1.
- **Rationale**: A full 50,000 × 50,000 matrix does not fit 4 GB; the sparse graph does. Average linkage avoids the chaining of a plain threshold graph (A≈B≈C but A≠C). Kind separation is structural (FR-004).
- **Alternatives**: connected components of a threshold graph, rejected: chaining; HDBSCAN, rejected: leaves noise points, while every item must be in a group (FR-003); centroid "leader" clustering, rejected: order-dependent.

## R8. Specificity relation: multilingual NLI on candidate pairs

- **Decision**: For group pairs of the same kind whose representatives have similarity in the band `[t_spec, t_dup)` and are neighbours, run a multilingual NLI cross-encoder (`MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`, MIT, licence of its training data checked before use) in both directions. If A entails B with probability ≥ `t_nli` and B does not entail A, A is more specific than B. Each group takes as parent its most similar more-general candidate. Cycles are broken by dropping the weakest edge, ties by id.
- **Rationale**: A more specific need entails the general one ("find a parking space downtown at night" ⇒ "find a parking space"), which symmetric embeddings cannot express. NLI runs only on a few thousand candidate pairs, so it fits the budget.
- **Alternatives**: length or centroid-distance heuristics, rejected: no direction signal; an LLM judge at runtime, rejected: hosted APIs must not be a runtime dependency (constitution V). If the pilot shows the references cannot agree on specificity, the relation is not produced and the groups become siblings in their cluster, with that stated in the report (R12).

## R9. Clusters: average linkage on group centroids across kinds

- **Decision**: Every duplicate group gets the normalised mean of its members' embeddings. Groups of all kinds are clustered with average linkage on a k-nearest-neighbour graph of centroids, cut at one or more configured thresholds (`levels: [t_c1, t_c2]`, coarser above finer), giving one or two cluster levels. A child group from R8 sits under its parent group and inherits the parent's cluster. Representatives: the member quote with the highest mean similarity to the node's items, ties by item id.
- **Rationale**: Mixing kinds is allowed (spec FR-011); pains and gains about the same job are near it in embedding space. Configurable levels give an Opportunity Solution Tree its opportunity and sub-opportunity layers.
- **Alternatives**: topic models (BERTopic), rejected: adds a heavy stack and produces generated labels; one cluster level only, kept as the configurable default if a second level does not reach agreement.

## R10. Benchmark `cluster-v1`

- **Decision**:
  - **Item pool**: outputs of the released `scout-large` on stored, redacted chunks of the pilot-v2 main split and `span-train-v1`; the pilot holdout stays untouched. Sources are split by snapshot into development (30%) and test (70%); thresholds are tuned on development only.
  - **Pairs** (same kind): about 1,200 test and 400 development pairs, stratified by similarity under two samplers that are not candidates (LaBSE cosine and a lexical token-set ratio): one third high, one third middle, one third random. Plus 300 holdout pairs for one re-pilot.
  - **Sets** (any kind): 12 test and 4 development sets of 40 items, each a seed item and its neighbourhood, for cluster membership.
  - Manifest with hashes only under `topics/productdev/benchmarks/cluster-v1/`, frozen with the guideline and the decision criteria before labeling.
- **Rationale**: Random pairs are almost all "different" and say nothing about the decision boundary; stratified sampling with non-candidate samplers avoids building the benchmark around one candidate. Splitting by snapshot prevents near-duplicate leakage between development and test.
- **Alternatives**: labeling full groupings of thousands of items, rejected: too expensive and unreliable for an LLM; labeling only pairs, rejected: cannot measure clusters.

## R11. Reference labeling

- **Decision**: The two existing reference models (`claude-reference`, family anthropic-claude, and `gpt-mini-reference`, family openai-gpt) label independently with a frozen prompt from the cluster guideline. Pairs go in batches of 20 with answers `same | a_more_specific | b_more_specific | different`; each set is answered as a partition into clusters that must cover every item exactly once (checked deterministically, invalid answers retried up to the runner's limit, then excluded and counted). Calls go through the existing backends, pre-send checks, approved routes, write-once raw responses and the budget ledger under the new budget `cluster-v1`. A small batch runner in `cluster/label.py` does this, because the existing runner works per chunk.
- **Rationale**: Same reference families and safeguards as the extraction benchmark (constitution III, VI). Batching keeps cost low: about 80 pair calls and 16 set calls per model.
- **Alternatives**: extending `labeling/runner.py` to non-chunk units, rejected: wide change to a frozen-path module for a different unit type.

## R12. Agreement pilot and decision criteria (frozen before labeling)

- **Decision**, written to `configs/productdev/jtbd/cluster-criteria.yaml` and hashed into the manifest:
  - Duplicate level: Cohen's kappa between the references on `same` vs. not-same ≥ 0.60.
  - Specificity level: kappa on {A more specific, B more specific, neither} over pairs both call not-same ≥ 0.40.
  - Cluster level: B-cubed F1 between the two references' partitions, averaged over sets, ≥ 0.60.
  - Below a threshold: revise the guideline once and re-pilot on the 300 holdout pairs and 4 fresh sets. Still below: that level is "rethink"; for specificity and clusters the stage still runs, but the level is reported as unmeasured, and for duplicates the task stops.
  - Baseline bar (SC-003): candidate's agreement with the consensus ≥ 85% of the reference-vs-reference value, per level. Contested pairs (references disagree) are reported separately and scored neutrally.
- **Rationale**: Same structure as the extraction pilot (go, revise, rethink; one rerun; holdout), so results are read the same way. Kappa thresholds follow common practice for "substantial" (0.6) and "moderate" (0.4) agreement; specificity is expected to be harder.
- **Alternatives**: single composite threshold, rejected: hides which level fails.

## R13. Stable ids across runs (FR-017)

- **Decision**: Item id = `it-` + 12 hex of SHA-256 over (source id, start, end, kind). Group and cluster ids are sequential (`dg-000001`, `cl-000001`) from counters in the map's `state.json`. After a run, new nodes are matched to the previous run's nodes by member overlap (Jaccard over item ids) with a one-to-one assignment; matched nodes keep their id. Merge: the surviving id is the one with the most previous members, ties to the older id. Split: the part with the most previous members keeps the id, others get new ids. Every change goes to `changes.json`.
- **Rationale**: Deterministic, explainable, and an unchanged group always keeps its id.
- **Alternatives**: content-hash group ids, rejected: any new member changes the id.

## R14. Human corrections (FR-018)

- **Decision**: `corrections.yaml` in the map directory, edited by people or with `jtbd cluster correct`. Operations: `merge` (groups, recorded as must-link between their items), `split` (item sets, recorded as cannot-link), `move` (node to a new parent, recorded as a pin), `representative` (item id for a node). They are recorded by item id, not by group id, and applied after the automatic step on every run, in file order. An operation whose items are all missing is reported as stale; one that would mix kinds in a duplicate group or a specificity link is refused with a message.
- **Rationale**: Item ids are stable, group ids can change, so constraints on items survive re-grouping. Applying after the automatic step keeps the automatic result measurable on its own.
- **Alternatives**: editing the output file directly, rejected: overwritten on the next run.

## R15. Statements and assignments (FR-014, FR-015, FR-019)

- **Decision**: Stored in `annotations.jsonl` in the map directory, keyed by node id: `statement` (text, author `person` or `model:<id>`, date) and `assignments` (`scheme`, `value`, `origin`). Merged into the output on every run; if a node's id disappears, its annotations are listed as orphaned in the change report.
- **Rationale**: Annotations survive re-runs and stay separate from the automatic result; this feature never writes a statement itself.
- **Alternatives**: annotations inside `corrections.yaml`, rejected: mixes structure edits with content.

## R16. Output `jtbd-cluster-v1` and views

- **Decision**: One JSON document per run (schema in [contracts/cluster-output.schema.json](contracts/cluster-output.schema.json)) with `items`, `groups`, `clusters`, `settings`, `inputs` and `checks`. `jtbd cluster report` renders two views from it, without changing it: a Markdown tree (cluster → group → child group, with counts and representative quotes) for an Opportunity Solution Tree, and a CSV of groups by kind with mention and source counts for an outcome-driven list.
- **Rationale**: SC-006 asks that a person builds both views from one result in under 30 minutes; the views are renderings, not a second format.

## R17. Budgets and measurement

- **Decision**: Stage settings for the measured candidate in `configs/productdev/jtbd/cluster-baseline.yaml`; budget block `cluster-v1` in `budget.yaml` (€20 cash, reference VM 8 GB RAM, 4 vCPU, no GPU). Speed is measured with `jtbd cluster perf` on the reference VM in a child process (wall time, peak RSS, no network after model download): once on all available real items, and once on a 50,000-item scale set made by resampling real items with unique source ids and a non-word suffix that defeats exact-copy merging. The scale set is labeled as such and used only for time and memory.
- **Rationale**: FR-021 and SC-005 need a 50,000-item measurement; the zoo's stored corpus holds fewer real items, and the report says so.

## R18. Dependencies

- **Decision**: New extra `cluster = [numpy, scipy, scikit-learn, pyyaml, jsonschema, typer]` for users who only run the stage; the base install provides `torch` and `transformers` for the encoders. The `jtbd` extra already contains everything for building and measuring.
- **Rationale**: A model user who runs scout and then the stage should not need the whole JTBD tool chain.
