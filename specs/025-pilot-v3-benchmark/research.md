# Research: Benchmark pilot-v3

Date: 2026-11-28. Inputs: the [spec](spec.md), the approved brief (`topics/productdev/guideline/scout-v3/brief.yaml`), and a read-only map of the existing jtbd code (the label runner, matching, consensus, metrics, decision, freeze, corpus, sources, budget and compliance pre-send).

## R1. Where the v3 code lives

- **Decision:** A new subpackage `src/mobility_model_zoo/productdev/jtbd/v3/` holds everything specific to pilot-v3: the labeler schemas, passes, token matching, agreement statistics, decision rule, sampler, benchmark freeze and report. A new CLI group `jtbd v3 …` exposes it. The existing `jtbd label` dispatches to the v3 pass runner when the config has a `v3:` block, so labeling keeps one entry point, one Claude gate and one package check.
- **Rationale:** The v1 schema, `wire_schema()` and `freeze.schema_sha256()` are pinned by tests and frozen into pilot-v1 and pilot-v2 manifests, so they must not change. The `cluster/` subpackage (feature 009) already shows the pattern of a task-specific benchmark next to the shared runner.
- **Alternatives:** Extending `schema.py` and `decision.py` in place was rejected because it would break frozen hashes and the hard-coded `THRESHOLD_KEYS`. A separate `jtbd v3 label` command was rejected because a second runner would duplicate the gate, the package check and the budget logic.

## R2. Pass instructions are part of the approved package (Principle XI)

- **Decision:** The fixed text that tells a labeler what to return in each pass, the "pass instructions", is added to the brief under a new key `pass_instructions` (pass1, pass2, pass3) as a Claude draft. The owner approves the content, and the package is assembled again with the three texts as `instructions/pass{1,2,3}.md`. The owner then approves the package hashes again. The prompt builder reads only package files. The JSON wire schemas carry no `description` or `title` text.
- **Rationale:** Constitution 3.2.0 allows Claude-drafted instructions that a teacher or reference reads only inside an owner-approved package. The v1 `INSTRUCTIONS` constant in `prompt.py` is code text that a labeler reads; repeating that pattern for v3 would put unapproved Claude text into the teacher's prompt. Descriptions in a JSON schema are text the model reads too, so they are stripped.
- **Alternatives:** Hard-coding minimal instructions in code was rejected under XI. Leaving instructions out entirely was rejected because the passes would then be undefined for the labeler.
- **Consequence:** The first task of implementation is an owner gate: approve the pass instructions, reassemble, approve the hashes. The existing approval of 2026-11-28 becomes stale by design, because `assemble` drops an approval of older files.

## R3. The labeler schema per pass

- **Decision:** Pydantic models in `v3/schema.py`, one per pass:
  - pass 1: `{relevant, items: [{kind, quote, actor_type, evidence_type, evidence_scope}]}`;
  - pass 2: `{items: [{index, job_kind, mode, improve, states_solution, executor_role, situation}]}`, with pointers as verbatim strings or null;
  - pass 3: `{links: [{from, to, relation}]}`.

  Code merges them into one v3 labeler output per chunk. Code also adds the offsets by locating quotes and pointers, and adds the language by detection. The merged shape maps one to one onto `jtbd-span-v2`, without `score`.
- **Rationale:** Smaller schemas per pass are easier for both a local 27B model and a remote model to fill under constrained decoding. Fixing the items before pass 2 is what the brief approved, and it keeps attributes comparable between references.
- **Alternatives:** One combined schema was rejected because the owner decided on passes (P16).

## R4. Calling a backend three times per chunk

- **Decision:** `Backend.call(system, user, schema, chunk_id)` stays single-turn.
  - The system prompt is the same for all three passes of a chunk: the package guideline and examples, plus the pass instructions file of that pass.
  - For passes 2 and 3, code appends the fixed items to the user message as a JSON list. That list is data, built by code from the labeler's own pass-1 answer.
  - Raw files are named `raw/<chunk>.p<pass>.a<attempt>.json`, are written exclusively and are never overwritten.
  - Each pass has its own retry budget, as `max_retries` does today.
  - A chunk whose pass 1 fails is excluded. A chunk whose pass 2 or 3 fails keeps the earlier passes, and the failed pass is recorded as excluded for that field group.
- **Rationale:** No backend change is needed beyond a configurable schema name in `OpenRouterBackend` (it is hard-coded to `extraction_output` today). The version guard keeps working per call.
- **Alternatives:** A multi-turn chat was rejected because the backends are single-turn and a chat would make the passes depend on each other's wording.

## R5. Token IoU for matching

- **Decision:**
  - Tokens are the Unicode word runs (`\w+`) of the chunk text, with their character offsets.
  - An item's token set is the set of tokens its located span overlaps.
  - IoU is the size of the intersection over the size of the union of the two token sets.
  - Matching stays one to one with the Hungarian algorithm, as in `matching.match_items`, with the cutoff 0.5 from the brief. Ties are broken by the highest IoU first.
  - The F1 at any overlap (IoU > 0) is reported beside it.
- **Rationale:** The brief defines the cutoff on tokens. The character IoU at 0.3 of v1 stays for pilot-v1 and v2.
- **Alternatives:** Model tokenizers were rejected, because the result would depend on the reference model.

## R6. Agreement statistics without new dependencies

- **Decision:**
  - Cohen's kappa and the linear weighted kappa reuse `metrics.kappa`.
  - Krippendorff's alpha with the MASI distance (Passonneau 2006) for `mode` and `improve` is written in `v3/agreement.py`, in about 40 lines: nominal alpha with a custom distance, two coders, both-empty counted as agreement.
  - Gwet's AC1 is written there too.
  - Bootstrap intervals reuse `metrics.bootstrap_ci`: they resample chunks, use 2,000 resamples and a fixed seed recorded in the criteria.
  - Every statistic gets a unit test against a hand-computed fixture to three decimals (SC-002).
- **Rationale:** The formulas are short and standard. A dependency such as `nltk` or `krippendorff` would add a large package, or would not support MASI with two coders the way the brief defines it.
- **Alternatives:** `nltk.metrics.agreement` with `masi_distance` was rejected as a heavy dependency, and its behaviour with empty sets differs from the brief.

## R7. The decision rule as data

- **Decision:**
  - `configs/productdev/jtbd/criteria-pilot-v3.yaml` is a verbatim copy of the brief's `pilot_thresholds`: definitions, thresholds with threshold and floor, `reported_only`, `decision`, `keep_always_stop` and `per_language`. Added are the bootstrap seed and the number of resamples.
  - `v3/decision.py` implements the rule as a pure function, with input the estimate, the interval, the units, the floor, the threshold and the step, and output one of: produced, revise, extend, underpowered, not produced, pilot stopped.
  - The function has one test per branch of the rule.
  - The criteria file is frozen into the manifest before the first label (Principle IV). The freeze refuses a copy that differs from the brief's `pilot_thresholds`.
- **Rationale:** The rule then has one source, the approved brief, and one executable form.

## R8. The benchmark directory

- **Decision:** pilot-v3 gets its own `paths.benchmarks: topics/productdev/benchmarks-v3` and its own data root `data/pilot-v3/`. The freeze follows the newer state machine of `cluster/bench.py`: draft, then criteria frozen, then pilot labeled, then decided, then (in one revise round) revised and rescored, then full labeled, then frozen.
- **Rationale:** A shared `topics/productdev/benchmarks` would move the `current` pointer, and so `analysis_dir`, of pilot-v1.

## R9. New benchmark sources

- **Decision:**
  1. Query the resource index with `zoo catalog query` for German and English mobility sources whose permitted use allows benchmarking.
  2. Build a fetch list and fetch each source once with `jtbd source fetch --permitted-uses benchmark_only`.
  3. Cut chunks with `autochunk` into a pilot-v3 store (map entries `use: eval`).
  4. Redact with `redact-v2`, review with the local PII model, and require a full redact-check.
  5. Run a new reverse separation check in `corpus/separation.py`: every pilot-v3 snapshot is compared against the snapshots, URLs, content hashes and supersessions of `span-train-v1` and any training dataset config. A hit refuses the freeze.
  6. Reuse the pilot-v2 chunk texts; their labels are never read.

  Target pool: at least 500 usable chunks per language before sampling. That covers 100 pilot, 100 holdout, up to 200 enriched and the full benchmark. English needs the most new sources; it has 69 chunks today.
- **Rationale:** `benchmark_only` exists in `PermittedUses` and keeps these texts out of every training set by construction. The reverse check closes the gap that separation runs only from the training side today.
- **Alternatives:** Adding a new permitted-use value was rejected as unnecessary.

## R10. Sampling

- **Decision:** `v3/sample.py` draws everything with a seeded `random.Random` per language:
  - the random pilot of 100;
  - the holdout of 100, locked;
  - the enriched link sub-sample of 100, extended once to 200 if needed. It comes only from chunks outside pilot and holdout in which a word of `link_connectives` occurs: the closed lists, plus the role-word condition for `actor_pair`, approximated by at least two distinct `executor_role`-like noun hits from a small fixed list kept in the criteria file and flagged as an approximation in the report.
  - The full benchmark is the rest of the pool, with its size written down after the pilot (spec Assumptions).

  Link prevalence is computed from the random pilot only.
- **Rationale:** This follows the brief, and it reuses the `keyword_hits` pattern of `autochunk`.
- **Open point carried to tasks:** The brief's role-word condition is not checkable as written. It was noted in the review-2 change log. The approximation needs the owner's nod when the criteria are frozen.

## R11. Budget and prices

- **Decision:** `configs/productdev/jtbd/budget-pilot-v3.yaml` has a cap of EUR 25 and the OpenRouter price of `ref-deepseek-v4.1-flash`, plus the prices of the baselines, all read from OpenRouter on the day the config is committed. The estimate multiplies by the number of passes: 3 calls per chunk for pass 1 and 2, and pass 3 only on chunks with at least two items (estimated from the pilot). The local reference costs nothing and is recorded with EUR 0.
- **Rationale:** `budget.yaml` is part of pilot-v1's frozen hashes and must not change. A named budget per benchmark follows `budget-cluster.yaml`.

## R12. The local reference

- **Decision:** `ref-qwen3.8-27b` runs through the existing Ollama backend on the DGX Spark (`host: spark`, VPN), with temperature 0 and seed 0, and its digest recorded as the model version. Runs are resumable, as today. The pilot of 200 chunks is about 600 calls at about 30 s each, roughly 5 hours. The time is reported but is not a gate.

## R13. The compliance pre-send scope

- **Decision:** The v3 runner passes `scope="benchmark:pilot-v3"` to `presend.check_batch`, as `cluster/label.py` does. The remote reference uses only its signed-off route (C-P4, C-P5).
