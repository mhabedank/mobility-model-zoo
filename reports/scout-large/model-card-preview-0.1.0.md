---
license: apache-2.0
language:
- de
- en
library_name: pytorch
pipeline_tag: token-classification
base_model: FacebookAI/xlm-roberta-large
tags:
- mobility
- mobility-model-zoo
- productdev
- jtbd
- experimental
- jobs-to-be-done
- product-discovery
- evidence-extraction
- span-extraction
- xlm-roberta
model-index:
- name: scout-large
  results:
  - task:
      type: token-classification
      name: 'Scout (large): jobs, pains and gains in mobility texts'
    dataset:
      type: pilot-v2
      name: pilot-v2 (frozen)
    metrics:
    - type: agreement_relevance
      value: 0.539185
      name: Agreement with the reference on relevance (kappa), 95% CI 0.249986-0.764049
    - type: agreement_item_matching
      value: 0.588235
      name: Agreement with the reference on item matching (f1), 95% CI 0.548562-0.625282
    - type: agreement_kind
      value: 0.831548
      name: Agreement with the reference on kind (kappa), 95% CI 0.778463-0.883767
    - type: agreement_actor_type
      value: 0.774281
      name: Agreement with the reference on actor type (kappa), 95% CI 0.69857-0.838218
    - type: agreement_evidence_type
      value: 0.848892
      name: Agreement with the reference on evidence type (quadratic_weighted_kappa), 95% CI 0.76975-0.908006
    - type: agreement_evidence_scope
      value: 0.758232
      name: Agreement with the reference on evidence scope (kappa), 95% CI 0.6683-0.833914
    - type: comparison_composite
      value: 0.723395
      name: Mean agreement over the dimensions this model outputs (relevance, item matching, kind, actor
        type, evidence type, evidence scope)
    - type: quotes_verbatim_rate
      value: 1.0
      name: Share of quotes that are verbatim spans of the input
    - type: schema_valid_rate
      value: 1.0
      name: Share of outputs valid against the jtbd-span-v1 schema
    - type: consistency_rate
      value: 1.0
      name: Share of passed consistency checks (dimensions, order, relevance)
    - type: contested_items
      value: 1574
      name: Benchmark items the reference models disagree on, reported separately and scored neutrally
    - type: comparison_composite_best_baseline
      value: 0.667169
      name: Same composite for the best zero-shot small baseline (baseline-gemma4-e4b)
    - type: comparison_composite_teacher
      value: 0.909491
      name: Same composite for the teacher (teacher-or-mimo-v2.6-pro)
    - type: comparison_composite_reference
      value: 1.0
      name: Same composite for the two reference models against each other, on consensus units
    - type: comparison_composite_reference_85pct
      value: 0.85
      name: '85% of the reference value: the pilot''s bar for a usable small model'
    - type: comparison_composite_mimo
      value: 0.909491
      name: Same composite for MiMo V2.6 Pro (teacher) (zero-shot, from its benchmark run)
    - type: comparison_composite_deepseek
      value: 0.835701
      name: Same composite for DeepSeek V4.1 Flash (zero-shot, from its benchmark run)
    - type: comparison_composite_qwen3_8_27b_dgx
      value: 0.890416
      name: Same composite for Qwen3.8 27B, DGX Spark (zero-shot, from its benchmark run)
    - type: comparison_composite_gemma4_e4b_dgx
      value: 0.667169
      name: Same composite for Gemma4 E4B, DGX Spark (zero-shot, from its benchmark run)
    - type: comparison_composite_qwen3_5_4b
      value: 0.615253
      name: Same composite for Qwen3.5 4B, 4 vCPU (zero-shot, from its benchmark run)
    - type: comparison_composite_ministral_3b
      value: 0.604384
      name: Same composite for Ministral 3B, 4 vCPU (zero-shot, from its benchmark run)
    - type: comparison_composite_gemma4_e2b
      value: 0.567877
      name: Same composite for Gemma4 E2B, 4 vCPU (zero-shot, from its benchmark run)
---

# Scout (large): jobs, pains and gains in mobility texts

**Version 0.1.0** · 2026-10-07 · status: **experimental** · topic: [Product development](https://huggingface.co/mobility-model-zoo) · task: `jtbd`

> **Experimental.** The output format may change in a minor version before 1.0.0.

## Summary

Finds jobs-to-be-done, pains and gains in German and English mobility texts and quotes them verbatim, with actor type, evidence type and evidence scope. On the frozen benchmark pilot-v2 (guideline v2) it reaches a comparison composite of 0.72, against 0.67 for the best zero-shot small model, measured as agreement with two frontier reference models (Claude and the GPT mini tier). It reads a 9,240-character interview in 8.1 s on 4 CPU cores with 2.5 GB of memory, in 0.84 s on the GPU of a MacBook M3 Pro and in 0.12 s on a DGX Spark, where it processes 1,260 texts per minute; the generative models of the pilot manage between 0.4 and 10 per minute.

![Quality against texts per minute for scout-large on four machines and for the generative models of the pilot](https://raw.githubusercontent.com/mhabedank/mobility-model-zoo/refs/tags/scout-large/v0.1.0/docs/recipes/figures/scout-large-quality-speed.png)

![Time to process 10,000 texts for scout-large on four machines and for the generative models of the pilot](https://raw.githubusercontent.com/mhabedank/mobility-model-zoo/refs/tags/scout-large/v0.1.0/docs/recipes/figures/scout-large-10k-texts.png)

`scout-large` belongs to the topic **Product development** (`productdev`), task `jtbd`, variant `large`. Base model: [`FacebookAI/xlm-roberta-large`](https://huggingface.co/FacebookAI/xlm-roberta-large).

## Intended use

Product discovery in mobility: finding what people try to get done (jobs), what gets in their way (pains) and what they would gain, in interviews, forum posts, reviews, studies and other texts. Every item comes with the sentence or clause it was found in, so a person can check it. The output is input for later steps (deduplication, clustering, prioritization), which this model does not do.

## Out-of-scope use

Decisions about individuals; profiling or identifying the authors of texts; texts outside mobility (it was trained on mobility texts only); treating the output as a complete or final list of needs without human review.

## Input and output

Input: a text in German or English, any length (it is read in overlapping 512-token windows). Output: JSON in the format `jtbd-span-v1`: `output_format_version`; `relevant` (does the text contain jobs, pains or gains at all) and `relevance_probability`; `dimensions`, the attribute dimensions this model produces (here `actor_type`, `evidence_type` and `evidence_scope`); and `items`. Each item has `kind` (job, pain or gain), `quote` with its character offsets `start` and `end` (always a verbatim span of the input), a `score`, and one value per produced dimension. An empty list is a valid result.

## How to run it

```bash
pip install "mobility-model-zoo @ git+https://github.com/mhabedank/mobility-model-zoo@scout-large/v0.1.0"
```

```python
import json

from mobility_model_zoo.productdev.jtbd.span import SpanExtractor

model = SpanExtractor.from_pretrained("mobility-model-zoo/scout-large", revision="v0.1.0")
print(json.dumps(model.extract("Ich wohne am Stadtrand und arbeite im Schichtdienst. Nach 22 Uhr fährt kein Bus mehr, also nehme ich das Auto, obwohl ich lieber Bahn fahren würde. Wenn es einen Nachtbus gäbe, würde ich das Auto verkaufen."), ensure_ascii=False, indent=2))
```

The tag `v0.1.0` always points to this version. For strict reproducibility, pin the commit hash of that tag instead (`revision="<commit>"`).

## Examples

### Example 1: `01-night-shift.txt`

Input:

```text
Ich wohne am Stadtrand und arbeite im Schichtdienst. Nach 22 Uhr fährt kein Bus mehr, also nehme ich das Auto, obwohl ich lieber Bahn fahren würde. Wenn es einen Nachtbus gäbe, würde ich das Auto verkaufen.
```

Output:

```json
{
  "output_format_version": "jtbd-span-v1",
  "relevant": true,
  "relevance_probability": 0.9999,
  "dimensions": [
    "actor_type",
    "evidence_type",
    "evidence_scope"
  ],
  "items": [
    {
      "kind": "pain",
      "quote": "Nach 22 Uhr fährt kein Bus mehr, also nehme ich das Auto, obwohl ich lieber Bahn fahren würde.",
      "start": 53,
      "end": 147,
      "score": 0.9571,
      "actor_type": "individual",
      "evidence_type": "routine",
      "evidence_scope": "multiple"
    }
  ]
}
```

### Example 2: `02-depot-charging.txt`

Input:

```text
Our fleet manager told us that charging the delivery vans takes most of the night. Two of the six chargers in the depot are often broken, so drivers start their morning routes with half a battery.
```

Output:

```json
{
  "output_format_version": "jtbd-span-v1",
  "relevant": true,
  "relevance_probability": 0.9999,
  "dimensions": [
    "actor_type",
    "evidence_type",
    "evidence_scope"
  ],
  "items": [
    {
      "kind": "pain",
      "quote": "Our fleet manager told us that charging the delivery vans takes most of the night.",
      "start": 0,
      "end": 82,
      "score": 0.9738,
      "actor_type": "worker",
      "evidence_type": "observation",
      "evidence_scope": "multiple"
    },
    {
      "kind": "pain",
      "quote": "Two of the six chargers in the depot are often broken, so drivers start their morning routes with half a battery.",
      "start": 83,
      "end": 196,
      "score": 0.9977,
      "actor_type": "worker",
      "evidence_type": "observation",
      "evidence_scope": "quantified"
    }
  ]
}
```

### Example 3: `03-cargo-bike.txt`

Input:

```text
Mit dem Lastenrad bringe ich die Kinder in zehn Minuten zur Kita. Schwierig wird es nur, wenn der Radweg zugeparkt ist und ich auf die Straße ausweichen muss.
```

Output:

```json
{
  "output_format_version": "jtbd-span-v1",
  "relevant": true,
  "relevance_probability": 0.9997,
  "dimensions": [
    "actor_type",
    "evidence_type",
    "evidence_scope"
  ],
  "items": [
    {
      "kind": "job",
      "quote": "Mit dem Lastenrad bringe ich die Kinder in zehn Minuten zur Kita.",
      "start": 0,
      "end": 65,
      "score": 0.9909,
      "actor_type": "individual",
      "evidence_type": "routine",
      "evidence_scope": "quantified"
    },
    {
      "kind": "pain",
      "quote": "Schwierig wird es nur, wenn der Radweg zugeparkt ist und ich auf die Straße ausweichen muss.",
      "start": 66,
      "end": 158,
      "score": 0.9975,
      "actor_type": "individual",
      "evidence_type": "routine",
      "evidence_scope": "multiple"
    }
  ]
}
```

## Quality

These numbers are agreement with the consensus of claude-reference and gpt-mini-reference (frontier reference models); they are not measured against human ground truth. Benchmark: `pilot-v2`.

| Metric | Value | What it measures | Reference | Benchmark | Items | Date |
|--------|-------|------------------|-----------|-----------|-------|------|
| `agreement_relevance` | 0.5392 | Agreement with the reference on relevance (kappa), 95% CI 0.249986-0.764049 | the consensus of claude-reference and gpt-mini-reference (frontier reference models) | pilot-v2 | 147 | 2026-10-07 |
| `agreement_item_matching` | 0.5882 | Agreement with the reference on item matching (f1), 95% CI 0.548562-0.625282 | the consensus of claude-reference and gpt-mini-reference (frontier reference models) | pilot-v2 | 1164 | 2026-10-07 |
| `agreement_kind` | 0.8315 | Agreement with the reference on kind (kappa), 95% CI 0.778463-0.883767 | the consensus of claude-reference and gpt-mini-reference (frontier reference models) | pilot-v2 | 412 | 2026-10-07 |
| `agreement_actor_type` | 0.7743 | Agreement with the reference on actor type (kappa), 95% CI 0.69857-0.838218 | the consensus of claude-reference and gpt-mini-reference (frontier reference models) | pilot-v2 | 404 | 2026-10-07 |
| `agreement_evidence_type` | 0.8489 | Agreement with the reference on evidence type (quadratic_weighted_kappa), 95% CI 0.76975-0.908006 | the consensus of claude-reference and gpt-mini-reference (frontier reference models) | pilot-v2 | 340 | 2026-10-07 |
| `agreement_evidence_scope` | 0.7582 | Agreement with the reference on evidence scope (kappa), 95% CI 0.6683-0.833914 | the consensus of claude-reference and gpt-mini-reference (frontier reference models) | pilot-v2 | 380 | 2026-10-07 |
| `comparison_composite` | 0.7234 | Mean agreement over the dimensions this model outputs (relevance, item matching, kind, actor type, evidence type, evidence scope) | the consensus of claude-reference and gpt-mini-reference (frontier reference models) | pilot-v2 | 150 | 2026-10-07 |
| `quotes_verbatim_rate` | 1 | Share of quotes that are verbatim spans of the input | the consensus of claude-reference and gpt-mini-reference (frontier reference models) | pilot-v2 | 1441 | 2026-10-07 |
| `schema_valid_rate` | 1 | Share of outputs valid against the jtbd-span-v1 schema | the consensus of claude-reference and gpt-mini-reference (frontier reference models) | pilot-v2 | 150 | 2026-10-07 |
| `consistency_rate` | 1 | Share of passed consistency checks (dimensions, order, relevance) | the consensus of claude-reference and gpt-mini-reference (frontier reference models) | pilot-v2 | 150 | 2026-10-07 |
| `contested_items` | 1574 | Benchmark items the reference models disagree on, reported separately and scored neutrally | the consensus of claude-reference and gpt-mini-reference (frontier reference models) | pilot-v2 | 150 | 2026-10-07 |
| `comparison_composite_best_baseline` | 0.6672 | Same composite for the best zero-shot small baseline (baseline-gemma4-e4b) | the consensus of claude-reference and gpt-mini-reference (frontier reference models) | pilot-v2 | 150 | 2026-10-07 |
| `comparison_composite_teacher` | 0.9095 | Same composite for the teacher (teacher-or-mimo-v2.6-pro) | the consensus of claude-reference and gpt-mini-reference (frontier reference models) | pilot-v2 | 150 | 2026-10-07 |
| `comparison_composite_reference` | 1 | Same composite for the two reference models against each other, on consensus units | the consensus of claude-reference and gpt-mini-reference (frontier reference models) | pilot-v2 | 150 | 2026-10-07 |
| `comparison_composite_reference_85pct` | 0.85 | 85% of the reference value: the pilot's bar for a usable small model | the consensus of claude-reference and gpt-mini-reference (frontier reference models) | pilot-v2 | 150 | 2026-10-07 |
| `comparison_composite_mimo` | 0.9095 | Same composite for MiMo V2.6 Pro (teacher) (zero-shot, from its benchmark run) | the consensus of claude-reference and gpt-mini-reference (frontier reference models) | pilot-v2 | 150 | 2026-10-07 |
| `comparison_composite_deepseek` | 0.8357 | Same composite for DeepSeek V4.1 Flash (zero-shot, from its benchmark run) | the consensus of claude-reference and gpt-mini-reference (frontier reference models) | pilot-v2 | 150 | 2026-10-07 |
| `comparison_composite_qwen3_8_27b_dgx` | 0.8904 | Same composite for Qwen3.8 27B, DGX Spark (zero-shot, from its benchmark run) | the consensus of claude-reference and gpt-mini-reference (frontier reference models) | pilot-v2 | 150 | 2026-10-07 |
| `comparison_composite_gemma4_e4b_dgx` | 0.6672 | Same composite for Gemma4 E4B, DGX Spark (zero-shot, from its benchmark run) | the consensus of claude-reference and gpt-mini-reference (frontier reference models) | pilot-v2 | 150 | 2026-10-07 |
| `comparison_composite_qwen3_5_4b` | 0.6153 | Same composite for Qwen3.5 4B, 4 vCPU (zero-shot, from its benchmark run) | the consensus of claude-reference and gpt-mini-reference (frontier reference models) | pilot-v2 | 150 | 2026-10-07 |
| `comparison_composite_ministral_3b` | 0.6044 | Same composite for Ministral 3B, 4 vCPU (zero-shot, from its benchmark run) | the consensus of claude-reference and gpt-mini-reference (frontier reference models) | pilot-v2 | 150 | 2026-10-07 |
| `comparison_composite_gemma4_e2b` | 0.5679 | Same composite for Gemma4 E2B, 4 vCPU (zero-shot, from its benchmark run) | the consensus of claude-reference and gpt-mini-reference (frontier reference models) | pilot-v2 | 150 | 2026-10-07 |

## Speed and memory

Budget: 4 GB RAM, no GPU. Measured on: railway service, 4 vCPU limit, 8 GB RAM limit, no GPU (x86_64, 4 vCPU, 8.0 GB RAM, AMD EPYC 9655 96-Core Processor, CPU only).

| Metric | Value | Unit | What it measures | Hardware | Items | Date |
|--------|-------|------|------------------|----------|-------|------|
| `latency_9k_chars_s` | 8.106 | s | Median time to process a 9240-character text, model loaded | railway service, 4 vCPU limit, 8 GB RAM limit, no GPU (x86_64, 4 vCPU, 8.0 GB RAM, AMD EPYC 9655 96-Core Processor, CPU only) |  | 2026-10-07 |
| `load_time_s` | 12.23 | s | Time to load the model from local files | railway service, 4 vCPU limit, 8 GB RAM limit, no GPU (x86_64, 4 vCPU, 8.0 GB RAM, AMD EPYC 9655 96-Core Processor, CPU only) |  | 2026-10-07 |
| `peak_ram_gb` | 2.488 | GB | Peak memory of the process while loading and processing | railway service, 4 vCPU limit, 8 GB RAM limit, no GPU (x86_64, 4 vCPU, 8.0 GB RAM, AMD EPYC 9655 96-Core Processor, CPU only) |  | 2026-10-07 |
| `chunks_per_min` | 21.62 | chunks/min | Throughput over the 150 benchmark chunks | railway service, 4 vCPU limit, 8 GB RAM limit, no GPU (x86_64, 4 vCPU, 8.0 GB RAM, AMD EPYC 9655 96-Core Processor, CPU only) | 150 | 2026-10-07 |
| `chunks_per_min_mac_m3pro_cpu` | 77.35 | chunks/min | Throughput over the 150 benchmark chunks, one at a time (development hardware) | MacBook Pro, Apple M3 Pro, 36 GB, CPU only | 150 | 2026-10-07 |
| `latency_9k_chars_s_mac_m3pro_cpu` | 1.936 | s | Median time to process the 9,240-character text, model loaded (development hardware) | MacBook Pro, Apple M3 Pro, 36 GB, CPU only | None | 2026-10-07 |
| `chunks_per_min_mac_m3pro_gpu` | 231.1 | chunks/min | Throughput over the 150 benchmark chunks, one at a time (development hardware) | MacBook Pro, Apple M3 Pro, 36 GB, GPU (MPS) | 150 | 2026-10-07 |
| `latency_9k_chars_s_mac_m3pro_gpu` | 0.8404 | s | Median time to process the 9,240-character text, model loaded (development hardware) | MacBook Pro, Apple M3 Pro, 36 GB, GPU (MPS) | None | 2026-10-07 |
| `chunks_per_min_dgx_spark_gpu` | 1260 | chunks/min | Throughput over the 150 benchmark chunks, one at a time (development hardware) | NVIDIA DGX Spark (GB10), GPU (CUDA) | 150 | 2026-10-07 |
| `latency_9k_chars_s_dgx_spark_gpu` | 0.1219 | s | Median time to process the 9,240-character text, model loaded (development hardware) | NVIDIA DGX Spark (GB10), GPU (CUDA) | None | 2026-10-07 |
| `comparison_chunks_per_min_claude` | 2.934 | chunks/min | Claude Opus 5.5 (reference): texts per minute on the benchmark chunks (60 / median call latency while labeling the benchmark) | Anthropic, Claude Code CLI (subscription) | 150 | 2026-10-07 |
| `comparison_chunks_per_min_gpt_mini` | 9.677 | chunks/min | GPT-5.4 mini (reference): texts per minute on the benchmark chunks (sample at concurrency 1) | OpenAI via OpenRouter | 20 | 2026-10-07 |
| `comparison_chunks_per_min_mimo` | 0.9583 | chunks/min | MiMo V2.6 Pro (teacher): texts per minute on the benchmark chunks (60 / median call latency while labeling the benchmark) | OpenRouter, provider chosen per request | 150 | 2026-10-07 |
| `comparison_chunks_per_min_deepseek` | 0.3978 | chunks/min | DeepSeek V4.1 Flash: texts per minute on the benchmark chunks (60 / median call latency while labeling the benchmark) | OpenRouter, provider chosen per request | 182 | 2026-10-07 |
| `comparison_chunks_per_min_qwen3_8_27b_dgx` | 2.148 | chunks/min | Qwen3.8 27B, DGX Spark: texts per minute on the benchmark chunks (60 / median call latency while labeling the benchmark) | NVIDIA DGX Spark (GB10), GPU, Ollama | 150 | 2026-10-07 |
| `comparison_chunks_per_min_gemma4_e4b_dgx` | 7.509 | chunks/min | Gemma4 E4B, DGX Spark: texts per minute on the benchmark chunks (60 / median call latency while labeling the benchmark) | NVIDIA DGX Spark (GB10), GPU, Ollama | 150 | 2026-10-07 |
| `comparison_chunks_per_min_qwen3_5_4b` | 0.9249 | chunks/min | Qwen3.5 4B, 4 vCPU: texts per minute on the benchmark chunks (jtbd perf on the reference machine, one chunk at a time) | railway service, 4 vCPU limit, 8 GB RAM limit, no GPU | 150 | 2026-10-07 |
| `comparison_chunks_per_min_ministral_3b` | 0.6933 | chunks/min | Ministral 3B, 4 vCPU: texts per minute on the benchmark chunks (jtbd perf on the reference machine, one chunk at a time) | railway service, 4 vCPU limit, 8 GB RAM limit, no GPU | 150 | 2026-10-07 |
| `comparison_chunks_per_min_gemma4_e2b` | 1.456 | chunks/min | Gemma4 E2B, 4 vCPU: texts per minute on the benchmark chunks (jtbd perf on the reference machine, one chunk at a time) | railway service, 4 vCPU limit, 8 GB RAM limit, no GPU | 150 | 2026-10-07 |

## Limitations and risks

- Quality numbers are agreement with frontier reference models (Claude and, for budget reasons, the mini tier of the GPT family) on the frozen benchmark pilot-v2 with guideline v2, not a check against human judgement.
- Its weakest dimensions are relevance (kappa 0.54) and item matching (F1 0.59): it does not always agree with the references on whether a text is about mobility needs at all, or on which statements count as items. Even the two reference models disagree on which statements are items; the pilot recorded item matching as an open question.
- It does not produce a free-text actor or an English statement of the job, pain or gain, which the generative approach does; it gives the actor type and the verbatim quote only.
- Items are whole sentences or clauses; a job that spans several sentences is split.
- It was trained on labels from one teacher model (MiMo V2.6 Pro), mostly on parliamentary hearings and plenary debates in English and German; forum and review texts were not available for training, so informal user language is less well covered.
- Trained on German and English mobility texts; other languages and domains are untested.
- Speed comparisons with generative models use one request at a time for every model (their median call latency on the benchmark). Hosted models can run many requests in parallel, at a cost per text and subject to rate limits; scout-large runs locally and can be batched as well.
- Texts can contain personal data. The model does not remove it; redact texts before sharing outputs.

## Training data provenance

| Source | License | Permitted use | Count |
|--------|---------|---------------|-------|
| https://committees-api.parliament.uk/api/OralEvidence/13304/Document/Html | Open Parliament Licence v3.0 | training_allowed | 20 |
| https://committees-api.parliament.uk/api/OralEvidence/13735/Document/Html | Open Parliament Licence v3.0 | training_allowed | 18 |
| https://committees-api.parliament.uk/api/OralEvidence/15426/Document/Html | Open Parliament Licence v3.0 | training_allowed | 16 |
| https://committees-api.parliament.uk/api/OralEvidence/15514/Document/Html | Open Parliament Licence v3.0 | training_allowed | 15 |
| https://committees-api.parliament.uk/api/OralEvidence/16532/Document/Html | Open Parliament Licence v3.0 | training_allowed | 15 |
| https://committees-api.parliament.uk/api/OralEvidence/16765/Document/Html | Open Parliament Licence v3.0 | training_allowed | 16 |
| https://committees-api.parliament.uk/api/OralEvidence/17341/Document/Html | Open Parliament Licence v3.0 | training_allowed | 15 |
| https://committees-api.parliament.uk/api/OralEvidence/17431/Document/Html | Open Parliament Licence v3.0 | training_allowed | 16 |
| https://data.oireachtas.ie/akn/ie/debateRecord/joint_committee_on_transport/2025-07-02/debate/mul@/main.xml | Oireachtas (Open Data) PSI Licence (CC BY 4.0) | training_allowed | 17 |
| https://data.oireachtas.ie/akn/ie/debateRecord/joint_committee_on_transport/2025-12-17/debate/mul@/main.xml | Oireachtas (Open Data) PSI Licence (CC BY 4.0) | training_allowed | 18 |
| https://data.oireachtas.ie/akn/ie/debateRecord/joint_committee_on_transport/2026-01-21/debate/mul@/main.xml | Oireachtas (Open Data) PSI Licence (CC BY 4.0) | training_allowed | 15 |
| https://data.oireachtas.ie/akn/ie/debateRecord/joint_committee_on_transport_and_communications/2022-09-14/debate/mul@/main.xml | Oireachtas (Open Data) PSI Licence (CC BY 4.0) | training_allowed | 16 |
| https://data.oireachtas.ie/akn/ie/debateRecord/joint_committee_on_transport_tourism_and_sport/2017-12-13/debate/mul@/main.xml | Oireachtas (Open Data) PSI Licence (CC BY 4.0) | training_allowed | 16 |
| https://data.oireachtas.ie/akn/ie/debateRecord/joint_committee_on_transport_tourism_and_sport/2019-02-27/debate/mul@/main.xml | Oireachtas (Open Data) PSI Licence (CC BY 4.0) | training_allowed | 19 |
| https://doi.org/10.1016/j.tranpol.2020.11.004 | CC-BY-4.0 | training_allowed | 14 |
| https://doi.org/10.1186/s42774-020-00054-7 | CC-BY-4.0 | training_allowed | 2 |
| https://dserver.bundestag.de/btp/20/20022.pdf | amtliches Werk § 5 UrhG | training_allowed | 18 |
| https://dserver.bundestag.de/btp/20/20030.pdf | amtliches Werk § 5 UrhG | training_allowed | 20 |
| https://dserver.bundestag.de/btp/20/20054.pdf | amtliches Werk § 5 UrhG | training_allowed | 19 |
| https://dserver.bundestag.de/btp/20/20062.pdf | amtliches Werk § 5 UrhG | training_allowed | 18 |
| https://dserver.bundestag.de/btp/20/20066.pdf | amtliches Werk § 5 UrhG | training_allowed | 19 |
| https://dserver.bundestag.de/btp/20/20074.pdf | amtliches Werk § 5 UrhG | training_allowed | 20 |
| https://dserver.bundestag.de/btp/20/20102.pdf | amtliches Werk § 5 UrhG | training_allowed | 20 |
| https://dserver.bundestag.de/btp/20/20114.pdf | amtliches Werk § 5 UrhG | training_allowed | 20 |
| https://dserver.bundestag.de/btp/20/20118.pdf | amtliches Werk § 5 UrhG | training_allowed | 18 |
| https://dserver.bundestag.de/btp/20/20122.pdf | amtliches Werk § 5 UrhG | training_allowed | 19 |
| https://dserver.bundestag.de/btp/20/20130.pdf | amtliches Werk § 5 UrhG | training_allowed | 20 |
| https://dserver.bundestag.de/btp/20/20142.pdf | amtliches Werk § 5 UrhG | training_allowed | 20 |
| https://dserver.bundestag.de/btp/20/20154.pdf | amtliches Werk § 5 UrhG | training_allowed | 19 |
| https://dserver.bundestag.de/btp/20/20178.pdf | amtliches Werk § 5 UrhG | training_allowed | 18 |
| https://dserver.bundestag.de/btp/20/20182.pdf | amtliches Werk § 5 UrhG | training_allowed | 19 |
| https://dserver.bundestag.de/btp/20/20194.pdf | amtliches Werk § 5 UrhG | training_allowed | 20 |
| https://record.senedd.wales/Committee/15088 | Senedd Commission copyright (free reproduction with acknowledgement) | training_allowed | 17 |
| https://www.europarl.europa.eu/doceo/document/CRE-9-2024-02-27-ITM-003_EN.html | © European Union, reuse with attribution | training_allowed | 12 |
| https://www.govinfo.gov/content/pkg/CHRG-112shrg73204/html/CHRG-112shrg73204.htm | public domain (17 U.S.C. § 105) | training_allowed | 16 |
| https://www.govinfo.gov/content/pkg/CHRG-114hhrg20105/html/CHRG-114hhrg20105.htm | public domain (17 U.S.C. § 105) | training_allowed | 18 |
| https://www.govinfo.gov/content/pkg/CHRG-115hhrg27720/html/CHRG-115hhrg27720.htm | public domain (17 U.S.C. § 105) | training_allowed | 16 |
| https://www.govinfo.gov/content/pkg/CHRG-116hhrg41285/html/CHRG-116hhrg41285.htm | public domain (17 U.S.C. § 105) | training_allowed | 18 |
| https://www.govinfo.gov/content/pkg/CHRG-116shrg52614/html/CHRG-116shrg52614.htm | public domain (17 U.S.C. § 105) | training_allowed | 16 |
| https://www.govinfo.gov/content/pkg/CHRG-117hhrg46928/html/CHRG-117hhrg46928.htm | public domain (17 U.S.C. § 105) | training_allowed | 18 |
| https://www.govinfo.gov/content/pkg/CHRG-118hhrg55550/html/CHRG-118hhrg55550.htm | public domain (17 U.S.C. § 105) | training_allowed | 16 |
| https://www.govinfo.gov/content/pkg/CHRG-118hhrg56115/html/CHRG-118hhrg56115.htm | public domain (17 U.S.C. § 105) | training_allowed | 20 |
| https://www.parlament.gv.at/dokument/XXVIII/NRSITZ/57/fname_1729016.pdf | amtliches Werk (§ 7 öUrhG) | training_allowed | 1 |
| https://www.parlament.gv.at/gegenstand/XXVIII/NRSITZ/57 | freies Werk § 7 öUrhG | training_allowed | 3 |
| https://www.parliament.scot/api/sitecore/CustomMedia/OfficialReport?meetingId=16372 | Scottish Parliament copyright licence (commercial and non-commercial reuse) | training_allowed | 20 |
| https://zenodo.org/api/records/15325897/files/Mobility_BG01_anonymised.docx/content | CC-BY-4.0 | training_allowed | 10 |
| https://zenodo.org/api/records/15325897/files/Mobility_BG02_anonymised.docx/content | CC-BY-4.0 | training_allowed | 9 |
| https://zenodo.org/api/records/15325897/files/Mobility_BG03_anonymised.docx/content | CC-BY-4.0 | training_allowed | 11 |
| https://zenodo.org/api/records/15325897/files/Mobility_BG04_anonymised.docx/content | CC-BY-4.0 | training_allowed | 8 |
| https://zenodo.org/api/records/15325897/files/Mobility_BG05_anonymised.docx/content | CC-BY-4.0 | training_allowed | 7 |
| https://zenodo.org/api/records/15325897/files/Mobility_BG06_anonymised.docx/content | CC-BY-4.0 | training_allowed | 6 |
| https://zenodo.org/api/records/15325897/files/Mobility_BG07_anonymised.docx/content | CC-BY-4.0 | training_allowed | 8 |
| https://zenodo.org/api/records/15325897/files/Mobility_BG08_anonymised.docx/content | CC-BY-4.0 | training_allowed | 6 |
| https://zenodo.org/api/records/15325897/files/Mobility_BG09_anonymised.docx/content | CC-BY-4.0 | training_allowed | 9 |
| https://zenodo.org/api/records/15325897/files/Mobility_BG10_anonymised.docx/content | CC-BY-4.0 | training_allowed | 9 |
| https://zenodo.org/api/records/15325897/files/Mobility_IE01_anonymised.docx/content | CC-BY-4.0 | training_allowed | 7 |
| https://zenodo.org/api/records/15325897/files/Mobility_IE02_anonymised.docx/content | CC-BY-4.0 | training_allowed | 7 |
| https://zenodo.org/api/records/15325897/files/Mobility_IE03_anonymised.docx/content | CC-BY-4.0 | training_allowed | 6 |
| https://zenodo.org/api/records/15325897/files/Mobility_IE04_anonymised.docx/content | CC-BY-4.0 | training_allowed | 4 |
| https://zenodo.org/api/records/15325897/files/Mobility_IE05_anonymised.docx/content | CC-BY-4.0 | training_allowed | 4 |
| https://zenodo.org/api/records/15325897/files/Mobility_IE06_anonymised.docx/content | CC-BY-4.0 | training_allowed | 5 |
| https://zenodo.org/api/records/15325897/files/Mobility_IE07_anonymised.docx/content | CC-BY-4.0 | training_allowed | 5 |
| https://zenodo.org/api/records/15325897/files/Mobility_IE08_anonymised.docx/content | CC-BY-4.0 | training_allowed | 7 |
| https://zenodo.org/api/records/15325897/files/Mobility_IE09_anonymised.docx/content | CC-BY-4.0 | training_allowed | 7 |
| https://zenodo.org/api/records/15325897/files/Mobility_IE10_anonymised.docx/content | CC-BY-4.0 | training_allowed | 17 |
| https://zenodo.org/api/records/15325897/files/Mobility_IE11_anonymised.docx/content | CC-BY-4.0 | training_allowed | 15 |
| https://zenodo.org/api/records/15325897/files/Mobility_LT01_anonymised.docx/content | CC-BY-4.0 | training_allowed | 12 |
| https://zenodo.org/api/records/15325897/files/Mobility_LT02_anonymised.docx/content | CC-BY-4.0 | training_allowed | 9 |
| https://zenodo.org/api/records/15325897/files/Mobility_LT03_anonymised.docx/content | CC-BY-4.0 | training_allowed | 10 |
| https://zenodo.org/api/records/15325897/files/Mobility_LT04_anonymised.docx/content | CC-BY-4.0 | training_allowed | 9 |
| https://zenodo.org/api/records/15325897/files/Mobility_LT05_anonymised.docx/content | CC-BY-4.0 | training_allowed | 9 |
| https://zenodo.org/api/records/15325897/files/Mobility_LT06_anonymised.docx/content | CC-BY-4.0 | training_allowed | 11 |
| https://zenodo.org/api/records/15325897/files/Mobility_LT07_anonymised.docx/content | CC-BY-4.0 | training_allowed | 10 |
| https://zenodo.org/api/records/15325897/files/Mobility_LT08_anonymised.docx/content | CC-BY-4.0 | training_allowed | 12 |
| https://zenodo.org/api/records/15325897/files/Mobility_LT09_anonymised.docx/content | CC-BY-4.0 | training_allowed | 11 |
| https://zenodo.org/api/records/15325897/files/Mobility_LT10_anonymised.docx/content | CC-BY-4.0 | training_allowed | 8 |
| https://zenodo.org/api/records/15325897/files/Mobility_PT01_anonymised.docx/content | CC-BY-4.0 | training_allowed | 7 |
| https://zenodo.org/api/records/15325897/files/Mobility_PT02_anonymised.docx/content | CC-BY-4.0 | training_allowed | 9 |
| https://zenodo.org/api/records/15325897/files/Mobility_PT03_anonymised.docx/content | CC-BY-4.0 | training_allowed | 10 |
| https://zenodo.org/api/records/15325897/files/Mobility_PT04_anonymised.docx/content | CC-BY-4.0 | training_allowed | 9 |
| https://zenodo.org/api/records/15325897/files/Mobility_PT05_anonymised.docx/content | CC-BY-4.0 | training_allowed | 8 |
| https://zenodo.org/api/records/15325897/files/Mobility_PT06_anonymised.docx/content | CC-BY-4.0 | training_allowed | 9 |
| https://zenodo.org/api/records/15325897/files/Mobility_PT07_anonymised.docx/content | CC-BY-4.0 | training_allowed | 8 |
| https://zenodo.org/api/records/15325897/files/Mobility_PT08_anonymised.docx/content | CC-BY-4.0 | training_allowed | 7 |
| https://zenodo.org/api/records/15325897/files/Mobility_PT09_anonymised.docx/content | CC-BY-4.0 | training_allowed | 7 |
| https://zenodo.org/api/records/15325897/files/Mobility_PT10_anonymised.docx/content | CC-BY-4.0 | training_allowed | 7 |
| https://zenodo.org/api/records/15325897/files/Mobility_PT11_anonymised.docx/content | CC-BY-4.0 | training_allowed | 5 |

| Teacher | License basis | Training on outputs permitted |
|---------|---------------|-------------------------------|
| `teacher-or-mimo-v2.6-pro` | MIT (HF XiaomiMiMo/MiMo-V2.6-Pro-RL); HF XiaomiMiMo/MiMo-V2.6-Pro-RL license tag mit, checked 2026-10-06 | yes |

The training data itself is not published. Datasets stay internal so that the people who wrote the source texts are protected and source terms are respected (project constitution, Principle VI); the model, the method, the prompts and the evaluation results are published.

## Training recipe

- Recipe: [docs/recipes/productdev-jtbd-span-xlmr.md](https://github.com/mhabedank/mobility-model-zoo/blob/4a7091af7166b9e5a6c802e7d5c6ec9f9a45de46/docs/recipes/productdev-jtbd-span-xlmr.md)
- Configuration: [configs/productdev/jtbd/span-xlmr.yaml](https://github.com/mhabedank/mobility-model-zoo/blob/4a7091af7166b9e5a6c802e7d5c6ec9f9a45de46/configs/productdev/jtbd/span-xlmr.yaml)
- Commit: `4a7091af7166b9e5a6c802e7d5c6ec9f9a45de46`

## Version history

| Version | Date | Status | Change | Changes | `agreement_relevance` | `agreement_item_matching` | `agreement_kind` |
|---------|------|--------|--------|---------|------|------|------|
| 0.1.0 | 2026-10-07 | experimental | initial | First production release of the span extractor, rebuilt without spike data. | 0.5392 | 0.5882 | 0.8315 |

## License

Apache-2.0

## Citation

```bibtex
@misc{mobility-model-zoo-scout,
  title  = {Scout (large): jobs, pains and gains in mobility texts, mobility-model-zoo},
  author = {Habedank, Martin},
  year   = {2026},
  url    = {https://huggingface.co/mobility-model-zoo/scout-large}
}
```

## About the zoo

Part of [mobility-model-zoo](https://huggingface.co/mobility-model-zoo), a collection of small, fast mobility models grouped by topic. Topic collection: [Product development](https://huggingface.co/mobility-model-zoo). Source code, recipes and release records: [https://github.com/mhabedank/mobility-model-zoo](https://github.com/mhabedank/mobility-model-zoo).
