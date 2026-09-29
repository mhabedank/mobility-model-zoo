# Spike report: spike-v2

> **Technical spike** (constitution v1.2.0). These are spike results, not benchmark results. The reference is a single model (Claude via subscription); there is no consensus between reference models and no contested set.

## Scores on the evaluation chunks (agreement with the Claude reference)

| Model | Role | relevance | item_matching | kind | actor_type | evidence_type | evidence_scope | Composite | schema_valid | quote_verbatim |
|---|---|---|---|---|---|---|---|---|---|---|
| spike-base | baseline | 0.785 | 0.301 | 0.701 | 0.326 | 0.615 | 0.508 | 0.540 | 1.000 | 0.447 |
| spike-base-spark | baseline | 0.785 | 0.353 | 0.637 | 0.409 | 0.693 | 0.505 | 0.564 | 1.000 | 0.486 |
| spike-tuned | baseline | -0.050 | 0.320 | 0.364 | 0.215 | 0.752 | 0.184 | 0.297 | 0.714 | 0.727 |
| spike-v3a | baseline | 0.785 | 0.492 | 0.475 | 0.649 | 0.713 | 0.598 | 0.619 | 1.000 | 0.807 |
| spike-v3b | baseline | 0.646 | 0.550 | 0.493 | 0.700 | 0.784 | 0.661 | 0.639 | 0.943 | 0.830 |
| teacher-or-deepseek-v4.1-flash | teacher_candidate | 0.788 | 0.601 | 0.822 | 0.784 | 0.797 | 0.700 | 0.749 | 0.971 | 0.833 |
| teacher-or-glm-5.3-flash | teacher_candidate | 1.000 | 0.518 | 0.723 | 0.775 | 0.863 | 0.742 | 0.770 | 1.000 | 0.609 |
| teacher-or-glm-5.3 | teacher_candidate | 1.000 | 0.528 | 0.793 | 0.777 | 0.870 | 0.688 | 0.776 | 1.000 | 0.598 |
| teacher-or-hy4-preview | teacher_candidate | 1.000 | 0.362 | 0.735 | 0.735 | 0.725 | 0.504 | 0.677 | 1.000 | 0.532 |
| teacher-or-mimo-v2.6-pro | teacher_candidate | 1.000 | 0.649 | 0.804 | 0.796 | 0.813 | 0.747 | 0.802 | 1.000 | 0.664 |
| teacher-or-qwen3.8-27b | teacher_candidate | 0.785 | 0.477 | 0.759 | 0.675 | 0.817 | 0.624 | 0.689 | 1.000 | 0.643 |

Evaluation chunks with a reference label: 35. All scores are underpowered by design (spike size).

## Runs and throughput (DGX Spark = development hardware, not target hardware)

| Run | Model | Split | Status | Excluded | Calls | Mean latency s | Chunks/min |
|---|---|---|---|---|---|---|---|
| `run-baseline-spike-base-main-3223351c` | spike-base | main | complete | 0 | 35 | 44.900 | 1.340 |
| `run-baseline-spike-base-spark-main-3223351c` | spike-base-spark | main | complete | 0 | 35 | 45.400 | 1.320 |
| `run-baseline-spike-tuned-main-3223351c` | spike-tuned | main | complete | 10 | 45 | 93.100 | 0.640 |
| `run-baseline-spike-v3a-main-3223351c` | spike-v3a | main | complete | 0 | 35 | 42.400 | 1.420 |
| `run-baseline-spike-v3b-main-3223351c` | spike-v3b | main | complete | 2 | 41 | 73.600 | 0.810 |
| `run-reference-claude-reference-main-3223351c` | claude-reference | main | complete | 0 | 35 | 36.400 | 1.650 |
| `run-teacher_candidate-teacher-glm4.7-main-3223351c` | teacher-glm4.7 | main | complete | 0 | 35 | 17.400 | 3.450 |
| `run-teacher_candidate-teacher-or-deepseek-v4.1-flash-main-3223351c` | teacher-or-deepseek-v4.1-flash | main | complete | 1 | 36 | 120.200 | 0.500 |
| `run-teacher_candidate-teacher-or-deepseek-v4.1-flash-train-3223351c` | teacher-or-deepseek-v4.1-flash | train | complete | 1 | 209 | 28.500 | 2.100 |
| `run-teacher_candidate-teacher-or-glm-5.3-flash-main-3223351c` | teacher-or-glm-5.3-flash | main | complete | 0 | 35 | 38.800 | 1.550 |
| `run-teacher_candidate-teacher-or-glm-5.3-flash-train-3223351c` | teacher-or-glm-5.3-flash | train | complete | 0 | 200 | 41.200 | 1.460 |
| `run-teacher_candidate-teacher-or-glm-5.3-main-3223351c` | teacher-or-glm-5.3 | main | complete | 0 | 35 | 4.700 | 12.640 |
| `run-teacher_candidate-teacher-or-hy4-preview-main-3223351c` | teacher-or-hy4-preview | main | complete | 0 | 35 | 14.700 | 4.080 |
| `run-teacher_candidate-teacher-or-mimo-v2.6-pro-main-3223351c` | teacher-or-mimo-v2.6-pro | main | complete | 0 | 35 | 133.000 | 0.450 |
| `run-teacher_candidate-teacher-or-mimo-v2.6-pro-train-3223351c` | teacher-or-mimo-v2.6-pro | train | complete | 0 | 200 | 96.100 | 0.620 |
| `run-teacher_candidate-teacher-or-qwen3.8-27b-main-3223351c` | teacher-or-qwen3.8-27b | main | complete | 0 | 35 | 21.800 | 2.750 |
| `run-teacher_candidate-teacher-or-qwen3.8-flash-main-3223351c` | teacher-or-qwen3.8-flash | main | running | 5 | 10 | 264.100 | 0.230 |
| `run-teacher_candidate-teacher-qwen3.6-main-3223351c` | teacher-qwen3.6 | main | complete | 0 | 35 | 12.400 | 4.820 |
| `run-teacher_candidate-teacher-qwen3.6-train-3223351c` | teacher-qwen3.6 | train | complete | 7 | 193 | 11.600 | 5.160 |
| `run-teacher_candidate-teacher-qwen3.8-main-3223351c` | teacher-qwen3.8 | main | complete | 0 | 35 | 24.100 | 2.490 |
| `run-teacher_candidate-teacher-qwen3.8-train-3223351c` | teacher-qwen3.8 | train | complete | 0 | 200 | 19.600 | 3.050 |

## Training data

- 200 SFT examples from `run-teacher_candidate-teacher-qwen3.8-train-3223351c`
- 14 teacher items dropped (quote not verbatim)
- 0 chunks skipped (no valid teacher output)

## Deviations

- retried 0 chunks after backend failures
- retried 2 chunks after backend failures
- retried 4 chunks after backend failures
- retried 49 chunks after backend failures
- retried 9 chunks after backend failures
- spike-base: server does not enforce the JSON schema; outputs validated after generation
- spike-tuned: server does not enforce the JSON schema; outputs validated after generation
- teacher-or-deepseek-v4.1-flash: provider chosen by OpenRouter per request
- teacher-or-glm-5.3-flash: provider chosen by OpenRouter per request
- teacher-or-glm-5.3: provider chosen by OpenRouter per request
- teacher-or-hy4-preview: provider chosen by OpenRouter per request
- teacher-or-mimo-v2.6-pro: provider chosen by OpenRouter per request
- teacher-or-qwen3.8-27b: provider chosen by OpenRouter per request
- teacher-or-qwen3.8-flash: provider chosen by OpenRouter per request
- temperature not settable on the Claude subscription CLI path
- user-level ~/.claude/CLAUDE.md may be loaded as context by the CLI

## Findings

- Source fetching: 4 of 21 plain fetches returned bot-challenge or JavaScript shells (PMC reCAPTCHA, Swiss parliament). Added a guard; used Europe PMC, Hansard and Swiss OData APIs instead.
- Publisher sites (Elsevier, MDPI) block automated access entirely; open copies via OpenAlex worked only for DLR and EconStor.
- `claude -p --bare` ignores the subscription login; the CLI must run without `--bare`.
- Redaction: PDF extraction inserts spaces into e-mail addresses ("name@dlr .de"); pattern made tolerant (redact-v2).
- Auto-chunking from PDFs keeps hyphenation and line-break artifacts ("appr opriate", "Früh- anwender:innen").
- Spot check of redaction: 6 random chunks plus an '@' scan across all 235 chunks; no usernames (sources are papers and parliamentary records).
- Auto-chunking whole Bundestag protocols produced mostly off-topic windows (e.g. Greek debt debate). Fixed with domain topic keywords: 80% on-topic, 20% random windows (spike data rebuilt, first attempt kept in data/spike-discarded).
- Teacher run: the Spark became unreachable from the Mac mid-run (49 of 200 train chunks timed out, eval run could not start). Added `pilot label --retry-failed` (backend failures retried, schema failures kept). No schema failures from the teacher on 151 answered chunks; quote_verbatim only 62% (Claude: 92%).
- Teacher retry: 42 of 49 recovered; 7 train chunks (ch-229 to ch-235) timed out again when the Spark dropped off. SFT export: 193 examples, 481 unverified items dropped. Teacher on the 35 eval chunks: composite 0.64 (item F1 0.44), quote_verbatim 0.56.
- Mac sleep dropped the VPN several times; `caffeinate` is needed for long runs.
- Ludwig 0.17.9 crashes with Qwen (no BOS token) in `remove_left_padding`; patched with a one-line sed in train.sh.
- Ludwig loads LLMs in fp32 without gradient checkpointing by default. With ~5.5k-token examples this filled the Spark's shared 119 GB, the machine hung for about 5 hours (SSH and Ollama unresponsive, 3 of 552 steps done); the container had to be killed. Moved training to MLX on the MacBook (see plan Complexity Tracking).
- SFT examples are ~5.5k tokens, of which ~4k are the guideline repeated in every example; this dominates training time (MLX 4-bit on M3 Pro: ~52 s per step, ~8 h for 3 epochs).
- mlx_lm.server ignores response_format and serves its model as "default_model"; one server per model.
- MLX training next to mlx_lm.server (base benchmark) ran out of Metal GPU memory on the 36 GB MacBook after ~10 minutes (kIOGPUCommandBufferCallbackErrorOutOfMemory). spike/run_mac.sh now runs base benchmark, training and tuned benchmark strictly one after another. Background jobs started from the Claude session also died with the session; the pipeline now runs under nohup.
- Base model (Qwen3-4B 4-bit, zero-shot, MLX): composite 0.54 (teacher 0.64); relevance 0.79, item F1 0.30, actor type 0.33; quote_verbatim 0.45; schema 100% without enforced schema.
- mlx_lm.server 0.31.3 silently ignores --adapter-path for "default_model" (load() remaps the model name before the adapter lookup). The first "tuned" run was the base model again (33/35 byte-identical outputs); set aside as failed-adapter-ignored-*. Workaround: pass {"adapters": path} per request (models.yaml extra_body).
- Port 8081 was taken by an unrelated Expo dev server; the readiness check (any HTTP answer) did not notice. Tuned model moved to 8082.
- Qwen3 chat template renders an empty <think></think> block in the trained assistant turn, so the tuned model emits it; parse_json_text now skips a leading think block.
- FINE-TUNING FAILED: the final adapter (549 steps) answers {"relevant": false, "items": []} for all 35 eval chunks (composite 0.0), even for a training example. Teacher-forced probability of "relevant": true on a relevant training example: base 0.05, step 100 0.82, step 549 0.35. Likely cause: with batch size 1, mlx_lm averages the loss per example, so short "irrelevant/empty" examples (18 irrelevant + 11 relevant-but-empty, the latter created by dropping unverified teacher items) weigh their decision tokens ~50x more than long examples; mean completion loss (0.08) hides it. Checkpoint 100 generates malformed output ('</tool_call>' prefix, broken JSON, 0/35 schema-valid).
- Training data is thin: median 3 items per example vs. ~11 per chunk in the Claude reference, because 481 unverified teacher items were dropped.
- Attempt 2 (started 2026-09-27 ~23:50): (1) SFT export repairs near-miss teacher quotes with the verbatim source passage (rapidfuzz partial alignment, score >= 90, length 0.8-1.25x): 412 repaired, 69 dropped (was 481 dropped); examples whose items were all dropped are skipped; 1,189 items, median 5 per example (was 740 / 3). (2) Custom MLX script spike/train_mlx.py: loss summed over answer tokens / mean answer length, plain ChatML template without think block. (3) Checkpoints every 61 steps, chosen by generation on the 10 validation examples (spike/select_checkpoint.py), never on the benchmark. Attempt-1 config kept in data/spike/adapter-mlx/adapter_config.json, runs set aside as failed-*.
- Spark smoke tests (2026-09-28, 8 longest examples, 1 epoch, host watchdog): with gradient checkpointing + AMP, available memory still fell by 7-22 GB per step (98 -> 28 GB after 4 steps; watchdog stopped test 1 at 60 GB and test 2 at 30 GB). Cause: PyTorch's caching allocator keeping blocks for every new sequence length on unified memory. With PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True memory stayed flat at 65-74 GB available (~45-55 GB used), all 8 steps done, ~7 s per step (MacBook: ~55 s). Prebuilt image spike/Dockerfile.ludwig (spike-ludwig:0.17.9: Ludwig, BOS patch, expandable_segments, TORCH_MEM_FRACTION=0.55) removes the 5-13 min pip install per run.
- Open before a full Spark run: check whether Ludwig averages the loss per example (the attempt-1 collapse cause).
- Teacher comparison on the 35 eval chunks: glm-4.7-flash (MIT, MoE 30B) composite 0.50 vs qwen3.6:35b 0.64; without relevance 0.60 vs 0.61; quote_verbatim 0.58 vs 0.56. glm marked all 35 chunks relevant; Claude marks only 2 irrelevant (ch-029, ch-032), so relevance kappa drops to 0 for two misses. The spike eval set has too few irrelevant chunks for a stable relevance kappa (the pilot's relevance_intent quotas were skipped in the spike).
- Teacher comparison: qwen3.8:27b (dense 27B, Apache-2.0) composite 0.76 (without relevance 0.71) vs qwen3.6:35b 0.64 (0.61); item F1 0.50 vs 0.44, evidence scope 0.71 vs 0.46, quote_verbatim 0.67 vs 0.56; ~24 s per chunk on the Spark (same as qwen3.6). Dense 27B beats the 35B MoE (~3B active) clearly. Candidate for the next teacher.
- OpenRouter teacher comparison (spike-v2 budget, 2026-09-29): reasoning could not be disabled for deepseek-v4.1-flash, glm-5.3, glm-5.3-flash (run with reasoning effort low, 16k output tokens); qwen3.8-27b and hy4-preview ran without reasoning. qwen3.8-flash dropped: its only provider (Alibaba) aborts strict-JSON generation ('Model output became abnormal'), 0/35. Results (composite / without relevance / quote_verbatim): glm-5.3 0.78/0.73/60% (EUR 0.13), glm-5.3-flash 0.77/0.72/61% (EUR 0.02), qwen3.8-27b full precision 0.69/0.67/64% (EUR 0.11) vs local Q4 0.76/0.71/67%, hy4-preview 0.68/0.61/53% (EUR 0.10). No hosted model beats the local qwen3.8:27b by more than the noise of 35 chunks; by the cost order the local model stays the teacher. glm-5.3-flash is the cheap second-family candidate for a two-teacher agreement filter.
- OpenRouter late finishers: mimo-v2.6-pro composite 0.80 / without relevance 0.76, item F1 0.65, quote_verbatim 66% (EUR 0.12, ~133 s/chunk); deepseek-v4.1-flash 0.75 / 0.74, item F1 0.60, quote_verbatim 83% (EUR 0.18, 1 chunk excluded, ~120 s/chunk). Both reason before answering even at effort low (deepseek up to ~13k reasoning tokens). Item F1 0.65 vs 0.50 for the local qwen3.8:27b (think off) is beyond the noise of 35 chunks. Open: local qwen3.8:27b with thinking on as the fair, free comparison. Total OpenRouter spend of the comparison: USD 0.89.
- Offline ensemble test (spike/ensemble.py, 35 eval chunks, no model calls; quote repair applied to every strategy): single mimo 0.81 composite / item F1 0.73; single qwen3.8 local 0.77 / 0.60 (quote repair alone lifts item F1 by 0.08-0.10); all five models with >=2 votes 0.82 / 0.75, attributes best (actor 0.81, evidence type 0.84, scope 0.77); cheap four-model ensemble (mimo, deepseek, glm-5.3-flash, qwen3.8 local, >=2) 0.82 / 0.72. Ensemble gain over the best single model is 0.01-0.02 on the composite, within the noise of 35 chunks; clearest gain is on the attributes. Strategies were fixed before scoring. Next: compare students trained on qwen3.8-only data vs ensemble data.
- Student v2 (MLX, qwen3.6 data, token loss, checkpoint 122 chosen on 10 validation examples) vs Claude: composite 0.30 vs base 0.54. 10/35 answers broken (7+ ran into the 4096-token limit in repetition loops; 1 invalid escape from PDF hyphenation), which counts against every dimension (relevance kappa -0.05). Better than base: quote_verbatim 73% vs 45%, evidence type 0.75 vs 0.62, item F1 0.32 vs 0.30. Worse: kind 0.36, evidence scope 0.18. The checkpoint selection on 10 validation examples scored against teacher answers (0.74) did not predict the benchmark.
- Student v3a (Spark, Ludwig with token-loss patch, qwen3.8:27b data with repaired quotes, 200 examples, 3 epochs, final weights) vs Claude: composite 0.62 vs base 0.56 (same bf16 base on vLLM); item F1 0.49 vs 0.35 (teacher 0.50), actor type 0.65 vs 0.41, evidence scope 0.60 vs 0.51, quote_verbatim 81% vs 49%, schema 100%, no broken answers; worse: kind 0.48 vs 0.64. Training 57 min, lowest available memory 68 GB. First student that beats its base model.

## v3a kind drop (2026-09-29)

Kind confusion against the Claude consensus (items matched at IoU >= 0.3; rows = consensus, cols = model):

| consensus -> | base: gain/job/pain | v3a: gain/job/pain | teacher qwen3.8: gain/job/pain |
|---|---|---|---|
| gain | 17 / 4 / 2 | 15 / 12 / 7 | 22 / 3 / 3 |
| job | 6 / 9 / 2 | 4 / 13 / 14 | 5 / 15 / 6 |
| pain | 5 / 3 / 52 | 4 / 2 / 80 | 1 / 1 / 88 |

v3a finds many more pains correctly (80 vs 52) but labels about half of the consensus jobs as pain and a
third of the gains as job. Kind distribution of the training items: v3a data job 19 % / gain 30 % / pain 51 %;
v3b ensemble data job 23 % / gain 30 % / pain 47 %; Claude consensus job 24 % / gain 25 % / pain 51 %.
The job/gain boundary is the weak spot; v3b uses deepseek (best single-model kind) as the kind tie-breaker.

## v3b training started (2026-09-29)

Data: `sft-v3b.jsonl` from `spike/ensemble.py --export` (mimo + deepseek + glm-5.3-flash + qwen3.8, item kept
with >= 2 votes): 200 examples, 1,464 items (v3a: 1,125), 34 irrelevant. TOKEN_NORM 777 (v3a 619).
Same Ludwig v3 config as v3a. vLLM was stopped for the run (with vLLM up only ~69 GB were free, training
needs ~50 GB and the watchdog stops at 30 GB free).

## v3b result (2026-09-29)

Trained 59 min on the Spark (600 steps, lowest available memory 65 GB). Eval on the 35 main chunks via vLLM
(bf16 base + LoRA). The first eval pass lost 9 chunks to a network outage (VPN dropped, not the model); they
were rerun with `--retry-failed --workers 2`.

| model | relevance | item F1 | kind | actor_type | evidence_type | evidence_scope | composite | quotes verbatim | schema valid |
|---|---|---|---|---|---|---|---|---|---|
| base (Spark) | 0.79 | 0.35 | 0.64 | 0.41 | 0.69 | 0.51 | 0.56 | 49 % | 35/35 |
| v3a (qwen3.8 data) | 0.79 | 0.49 | 0.48 | 0.65 | 0.71 | 0.60 | 0.62 | 81 % | 35/35 |
| v3b (4-teacher ensemble) | 0.65 | 0.55 | 0.49 | 0.70 | 0.78 | 0.66 | 0.64 | 83 % | 33/35 |

- v3b beats v3a on every item dimension (F1 CI 0.48-0.62 vs 0.44-0.54, overlapping) and matches 180 items vs 142.
  Composite without relevance: v3a 0.59, v3b 0.64.
- Relevance drops 0.79 -> 0.65, but the eval set has only 2 irrelevant chunks (CI 0.00-1.00), so this is noise
  plus the 2 excluded chunks.
- New failure mode: v3b sometimes loops until max_tokens (4096). 7 of 35 first attempts ran to the limit,
  2 chunks (ch-011, ch-020) failed twice. v3a never did. Likely cause: longer targets (TOKEN_NORM 777 vs 619)
  and more items per chunk; candidates: repetition penalty at inference, capping items per example, or
  stopping at an earlier checkpoint.
- Kind is still the weak spot (0.49 vs base 0.64); the ensemble data did not fix the job/gain confusion.
