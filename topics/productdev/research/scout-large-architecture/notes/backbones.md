# Multilingual encoder backbones (2024–2026) as replacements for XLM-RoBERTa-large in scout-large

Scope: German+English BIO span extraction plus sequence/attribute heads. About 1,000 training chunks. Deployment targets are 4 CPU cores with at most 4 GB RAM, Apple MPS and an NVIDIA DGX Spark. Research date: 27 Nov 2026.

Verification legend:
- **[V]**: read in this session from the primary source (model card or paper).
- **[R]**: from model-card or paper facts I already knew, with the URL given but not re-fetched this session. Check these before relying on them.
- **[C]**: vendor or marketing claim that no independent source has verified.

## Q1. Which multilingual (incl. German) encoders exist, and what are their specs?

### Takeaway
German+English-capable candidates fall into three tiers:
- **Modern MLM encoders with 8k context:** mmBERT-small and mmBERT-base (MIT), EuroBERT-210m, -610m and -2.1B, and LFM2.5-Encoder-230M and -350M (non-Apache licence).
- **RTD/ELECTRA-style encoders:** mDeBERTa-v3-base (2021) and the brand-new EdgeCoder-Multilingual-61M (Apache-2.0, released about 23 Nov 2026).
- **XLM-R derivatives extended to 8k:** BGE-M3 and mGTE. These are mostly retrieval-tuned.

ModernBERT, NeoBERT and Ettin are effectively English-only and do not fit a 28% German corpus. No mmBERT-large exists, and I found no mmBERT successor as of Nov 2026.

### Cited Findings

**Baseline**
- **XLM-RoBERTa-large** (`FacebookAI/xlm-roberta-large`), 2019: 560M params, 24 layers, hidden size 1024, 250k SentencePiece vocab, 100 languages, 512 positions, MLM on 2.5 TB CC-100, MIT licence. [R] — [HF card](https://huggingface.co/FacebookAI/xlm-roberta-large), [paper](https://arxiv.org/abs/1911.02116)

**mmBERT (JHU CLSP), paper 8 Sep 2025, MIT licence** [V] — [HF mmBERT-base](https://huggingface.co/jhu-clsp/mmBERT-base), [arXiv 2509.06888](https://arxiv.org/html/2509.06888)
- **`jhu-clsp/mmBERT-base`:** 307M total, 110M non-embedding. 22 layers, hidden size 768, FFN 1152, 12 heads.
- **`jhu-clsp/mmBERT-small`:** 140M total, 42M non-embedding. 22 layers, hidden size 384, 6 heads.
- **Shared by both sizes:**
  - Context: 8,192 tokens.
  - Tokenizer: Gemma-2, 256k vocab.
  - Training: more than 3T tokens. 2.3T across 60 languages, then 600B across 110 languages, then a 100B decay phase covering 1,833 languages.
  - Objective: MLM with an inverse mask schedule (30% → 15% → 5%).
  - Architecture: ModernBERT (FlashAttention-2, unpadding).

**EuroBERT, arXiv 2503.05500 (v3), March 2025** [V for architecture and data] — [paper](https://arxiv.org/pdf/2503.05500)
- **Sizes:** `EuroBERT/EuroBERT-210m`, `-610m` and `-2.1B`.
  - 210m: 12 layers, hidden size 768.
  - 610m: 26 layers, hidden size 1152, GQA with 6 KV heads.
  - 2.1B: 32 layers, hidden size 2304.
- **Architecture:** Llama-style encoder with RMSNorm, SwiGLU and RoPE (θ = 250k). Llama-3 tokenizer, 128k vocab. Context 8,192.
- **Data:** 5T tokens (4.8T pre-training plus 200B annealing) in 15 languages, including English and German.
- **Objective:** MLM at a 50% masking ratio, lowered to 10% during annealing.
- **Licence:** Apache-2.0 on HF. [R] Model support in transformers is now native: there is a `model_doc/eurobert` page. [V-search] — [transformers docs](https://huggingface.co/docs/transformers/model_doc/eurobert)

**mDeBERTa-v3-base** (`microsoft/mdeberta-v3-base`), 2021
- 86M backbone plus about 190M embedding (about 280M total), 12 layers, hidden size 768, 250k vocab, CC-100, MIT licence. [R] — [HF card](https://huggingface.co/microsoft/mdeberta-v3-base)
- Objective: RTD (ELECTRA-style) with gradient-disentangled embedding sharing. [V] — [arXiv 2111.09543](https://arxiv.org/abs/2111.09543)
- EuroBERT's tables label it "mDeBERTa-v3-280M". [V] — [EuroBERT paper](https://arxiv.org/pdf/2503.05500)

**EdgeCoder-Multilingual-61M** (`knowledgator/EdgeCoder-Multilingual-61M`), arXiv 2611.31495v1, 23 Nov 2026, Apache-2.0 [V] — [paper](https://arxiv.org/html/2611.31495), [HF card](https://huggingface.co/knowledgator/EdgeCoder-Multilingual-61M)
- **Architecture:** DeBERTa-v2/v3 architecture, 16 layers, hidden size 384, FFN 1536, 6 heads.
- **Embeddings:** factorized (a 128-d table projected to 384). mDeBERTa-v3 tokenizer, 251k vocab.
- **Parameters:** 61.0M total, 28.4M non-embedding.
- **Context:** 8,192.
- **Languages and data:** 46 languages including German. About 1.085T tokens.
- **Objective:** RTD plus boundary-window reconstruction.

**EdgeCoder-31M** (`knowledgator/EdgeCoder-31M`): English-only, 8 layers, DeBERTa-v3 tokenizer (128k vocab), about 1.01T tokens. [V] — [paper](https://arxiv.org/html/2611.31495). Its licence was not checked.

**LFM2.5-Encoder-350M / -230M** (`LiquidAI/LFM2.5-Encoder-350M`), blog 28 Jul 2026 [V] — [HF card](https://huggingface.co/LiquidAI/LFM2.5-Encoder-350M)
- **350M:** about 354.5M params, hidden size 1024. **230M:** about 229.7M params, hidden size 1024.
- **Architecture:** hybrid of gated short convolutions and GQA, made bidirectional. 65,536 vocab, 8,192 context.
- **Languages:** 15, including German.
- **Objective:** MLM, adapted from the LFM2.5-350M decoder base.
- **Loading:** needs `trust_remote_code=True`.
- **Licence:** LFM Open License v1.0, not Apache. A community card points to a commercial-use revenue threshold in Section 5. [V-search] — [litert card](https://huggingface.co/litert-community/LFM2.5-Encoder-350M)

**Other candidates, mostly retrieval-tuned**
- **mGTE MLM** (`Alibaba-NLP/gte-multilingual-mlm-base`): 305M, RoPE, 8,192 context, Apache-2.0. EuroBERT uses it as a baseline. [R] — [HF](https://huggingface.co/Alibaba-NLP/gte-multilingual-mlm-base)
- **BGE-M3:** XLM-R-large extended to 8,192, MIT, embedding-tuned. [R] — [HF](https://huggingface.co/BAAI/bge-m3)
- **jina-embeddings-v3:** XLM-R-large plus RoPE. CC-BY-NC-4.0, so it is **not usable commercially**. [R] — [HF](https://huggingface.co/jinaai/jina-embeddings-v3)

**XLM-V** (`facebook/xlm-v-base`), 2023
- XLM-R-base with a 1M-token vocab, about 778M params, mostly embeddings, MIT licence. [R] — [arXiv 2301.10472](https://arxiv.org/abs/2301.10472)
- Superseded by the 2025 encoders.

**English-only models (do not fit)**
- **ModernBERT** (`answerdotai/ModernBERT-base` 149M and `-large` 395M), Dec 2024. Trained on 2T English and code tokens, 8,192 context, alternating local (128-token window) and global attention, unpadding, FA2, Apache-2.0. [R] — [arXiv 2412.13663](https://arxiv.org/abs/2412.13663)
- **ModernBERT's German is poor.** On German MLDR it scores 11.3 (150M) and 25.3 (395M), against 68.1 for EuroBERT-210m. On German NER it scores 89.4 (150M) and 81.5 (395M), against 96.4 for XLM-R-560M. [V] — [EuroBERT paper, Tables 9/13](https://arxiv.org/pdf/2503.05500)
- **NeoBERT** (`chandar-lab/NeoBERT`): 250M, 2T tokens, 4,096 context, English evaluations only (GLUE, MTEB-en), ICLR 2026. [V-search] — [arXiv 2502.19587](https://arxiv.org/html/2502.19587v2)
- **Ettin** (`jhu-clsp/ettin-encoder-{17m,32m,68m,150m,400m,1b}`): paired encoders and decoders, 2T tokens, MIT licence, English. [V-search] — [HF](https://huggingface.co/jhu-clsp/ettin-encoder-32m), [arXiv 2507.11412](https://arxiv.org/abs/2507.11412)

**German-only (no English)**
- **ModernGBERT** (134M and 1B) and LLäMmlein2Vec, from Würzburg, LREC 2026.
- ModernGBERT-1B reaches SuperGLEBer 0.808, about 4% above GBERT-large. [V-search] — [arXiv 2505.13136](https://arxiv.org/html/2505.13136v2)
- These models lack English, which makes up 72% of the corpus.

**2026 additions**
- **NeoMME-260M / 800M** (H Company, 3 Sep 2026): multimodal multilingual encoders, masked-diffusion objective, 16,384 context, 131k BPE vocab, about 524B tokens, Apache-2.0. No text-only, NER or German benchmarks are reported, and German is not explicitly listed. [V] — [HF blog](https://huggingface.co/blog/Hcompany/neomme)
- **IBM Granite Embedding Multilingual R2:**
  - 311M model: a 22-layer ModernBERT with a 262k vocab.
  - 97M model: a compact variant.
  - Apache-2.0, but these are embedding models rather than MLM backbones. [V-search] — [HF blog](https://huggingface.co/blog/ibm-granite/granite-embedding-multilingual-r2)

### Inferences
- **Compute per token tracks non-embedding parameters,** because embedding lookups are cheap.
  - XLM-R-large has about 560M − 250k×1024 ≈ 300M non-embedding params.
  - mmBERT-base (110M) needs about 2.7× less compute per token.
  - mmBERT-small (42M) needs about 7× less.
  - EdgeCoder-M-61M (28M) needs about 10× less.
  - EuroBERT-610m has about 460M non-embedding params, so it is *more* expensive than XLM-R-large.
  - EuroBERT-210m has about 115M.
- **RAM:** fp32 weights of mmBERT-base are about 1.2 GB and XLM-R-large about 2.2 GB, so all small and base candidates fit easily in 4 GB.

### Gaps
- I did not read the explicit 46-language list in Appendix B of the ModernELECTRA paper. German inclusion is confirmed by the HF model card and implied by "all 24 EU languages".
- I did not verify the EdgeCoder-31M licence.
- I did not find a ModernGBERT licence.
- I did not find a layer count for LFM2.5-Encoder.
- The EuroBERT Apache-2.0 licence and the mGTE, BGE-M3 and Jina facts were not re-fetched this session.

## Q2. Performance on token classification, NER and QA (German), and is RTD better per parameter?

### Takeaway
NER and token classification are consistently the weak spot of the new MLM encoders. On NER, XLM-R remains equal or better:
- mmBERT-base trails XLM-R-base by 3.2 F1 on WikiANN.
- On German XGLUE NER, EuroBERT-210m trails XLM-R-large by about 4.6 F1, and EuroBERT-610m roughly matches it (96.0 vs 96.4).

mmBERT clearly wins on classification and QA (XNLI, TyDiQA, MLQA, German XNLI). There is good evidence that RTD is more sample- and compute-efficient for classification:
- DeBERTa-v3 beat ELECTRA and DeBERTa on GLUE, and mDeBERTa-base beat XLM-R-base on XNLI by 3.6.
- mDeBERTa-v3-base ties XLM-R-large on German NER (96.4).

EdgeCoder-M-61M does *not* beat mmBERT-small on multilingual NER or QA.

### Cited Findings
- **XTREME, base models (XLM-R-base / mGTE-base / mmBERT-base)** [V] — [mmBERT paper](https://arxiv.org/html/2509.06888)

  | Task | XLM-R-base | mGTE-base | mmBERT-base |
  |---|---|---|---|
  | XNLI | 74.6 | 73.9 | 77.1 |
  | PAWS-X | 85.9 | 86.4 | 87.7 |
  | MLQA | 62.1 | 64.3 | 66.0 |
  | TyDiQA | 70.5 | 69.9 | 74.5 |
  | **WikiANN NER** | **61.4** | 60.7 | **58.2** |
  | UDPOS | 74.3 | 74.3 | 74.0 |

- The mmBERT text says it "ties on NER", but its table shows a 3.2-point gap. [V] — [mmBERT paper](https://arxiv.org/html/2509.06888)
- **mmBERT-small** scores 54.3 on WikiANN, against 59.2 for Multilingual MiniLM. [V] — [mmBERT paper](https://arxiv.org/html/2509.06888)
- **mmBERT does not compare against XLM-R-large.** [V] — [mmBERT paper](https://arxiv.org/html/2509.06888)
- **German-specific mmBERT numbers:**
  - XNLI-de: 77.0 (small), 79.6 (base), 72.5 (EuroBERT).
  - PAWS-X-de: 89.8, 90.7 and 87.8.
  - No German NER or QA numbers are given. [V] — [mmBERT paper](https://arxiv.org/html/2509.06888)
- **German NER, XGLUE NER (CoNLL-02/03 subsets, F1)** [V] — [EuroBERT paper, Table 13](https://arxiv.org/pdf/2503.05500)

  | Model | German NER F1 |
  |---|---|
  | XLM-R-280M | 94.5 |
  | **XLM-R-560M** | **96.4** |
  | XLM-R-3.5B | 96.4 |
  | mDeBERTa-v3-280M | 96.4 |
  | mGTE-305M | 94.0 |
  | EuroBERT-210m | 91.8 |
  | EuroBERT-610m | 96.0 |
  | EuroBERT-2.1B | 94.2 |

  - Overall NER: XLM-R-560M 96.1, mDeBERTa 96.2, EuroBERT-210m/610m/2.1B 94.7/95.9/95.2.
  - Caveat: the appendix describes "English-only training", yet the absolute F1 values are unusually high for zero-shot. The protocol may differ from classic CoNLL entity-level F1.
- **EuroBERT authors on NER:** "On the NER task, EuroBERT lags behind XLM-RoBERTa." They attribute this to tokenizer fertility: models are better when entities split into fewer tokens. They posit that "token classification tasks may benefit from larger vocabularies, with lower fertility, such as the one used in the XLM-RoBERTa family." [V] — [EuroBERT paper §3](https://arxiv.org/pdf/2503.05500)
- **EuroBERT classification results, XNLI (all languages):** XLM-R-560M 81.7, EuroBERT-610m 81.9, EuroBERT-2.1B 84.1, mDeBERTa 79.5. EuroBERT-210m (76.6) is roughly at XLM-R-base level (74.1). [V] — [EuroBERT paper Table 1](https://arxiv.org/pdf/2503.05500)
- **LFM2.5 17-task sequence-classification mean (5 seeds, vendor-run)** [C] — [HF card](https://huggingface.co/LiquidAI/LFM2.5-Encoder-350M)

  | Model | 17-task mean |
  |---|---|
  | XLM-R-XL | 83.06 |
  | ModernBERT-large | 81.68 |
  | XLM-R-large | 81.34 |
  | LFM2.5-350M | 81.02 |
  | mDeBERTa-v3 | 80.37 |
  | LFM2.5-230M | 79.29 |
  | XLM-R-base | 77.46 |
  | EuroBERT-210m | 76.87 |
  | EuroBERT-610m | 75.87 |
  | EuroBERT-2.1B | 72.19 |

  - No NER numbers are reported.
- **EdgeCoder-Multilingual-61M, XTREME zero-shot, 26 seen languages:** single seed, Knowledgator-run. XLM-R is not compared anywhere in the paper. [V] — [ModernELECTRA paper Table 10](https://arxiv.org/html/2611.31495)

  | Model | WikiANN | UDPOS | XQuAD | MLQA | Avg |
  |---|---|---|---|---|---|
  | EdgeCoder-M-61M | 57.4 | 77.9 | 69.4 | 62.0 | 67.8 |
  | mmBERT-small | 59.4 | 72.4 | 73.0 | 66.2 | 70.0 |
  | Multilingual MiniLM | 58.9 | 79.4 | n/a | n/a | 67.3 |

  - Across all XTREME languages, the averages are 62.7 (EdgeCoder-M-61M), 66.4 (MiniLM) and 68.1 (mmBERT-small).
- **DeBERTaV3 (RTD + gradient-disentangled embedding sharing):**
  - DeBERTaV3-large reaches GLUE 91.37, which is +1.37 over DeBERTa and +1.91 over ELECTRA.
  - mDeBERTa-base reaches 79.8 on XNLI zero-shot, +3.6 over XLM-R-base. [V] — [arXiv 2111.09543](https://arxiv.org/abs/2111.09543)
- **ELECTRA:** RTD learns from all tokens rather than only the 15% that are masked, which makes it more compute-efficient. ELECTRA-large matched RoBERTa and XLNet at about a quarter of their compute. [R] — [arXiv 2003.10555](https://arxiv.org/abs/2003.10555)
- **ModernELECTRA GLUE (English, dev, single seed)** [V] — [paper Table 7](https://arxiv.org/html/2611.31495)

  | Model | GLUE |
  |---|---|
  | EdgeCoder-31M | 86.0 |
  | Ettin-32m | 83.5 |
  | MiniLM-L12 | 84.6 |
  | BERT-base | 84.7 |
  | EdgeCoder-M-61M | 85.1 |
  | mmBERT-small | 84.7 |

  - Its authors say the RTD and window-loss benefit comes with "no controlled ablation".

### Inferences
- For a span-extraction model, the strongest evidence-based options are:
  - **mDeBERTa-v3-base:** RTD, about half of XLM-R-large's compute, and ties XLM-R-large on German NER. Its downside is a 512-token pre-training window. Relative positions let it go longer, but quality beyond 512 is unproven, and CPU attention is slow at long lengths.
  - **mmBERT-base:** 8k context and fast, but expect about 2–3 F1 lower NER at equal data.
- The task is quote-span extraction rather than entity NER. Spans are longer, so tokenizer fertility matters less than for short entities, but this is untested.
- **Small data (about 1,000 chunks):** mmBERT and EuroBERT gains appear mostly on classification and QA with large training sets. No source tests the 1k-example regime. The sequence-level heads (relevance, attribute kinds) are where mmBERT's classification strength is most likely to pay off.
- **EdgeCoder-M-61M is attractive for CPU speed, about 10× less compute than XLM-R-large,** but:
  - Its NER and QA scores trail mmBERT-small.
  - It is four days old.
  - It has single-seed results.
  - It has no XLM-R comparison.

  Treat it as an experimental third option, not a primary replacement.

### Gaps
- I found no GermEval-14, CoNLL-03-de (in-language) or GermanQuAD numbers for mmBERT, EuroBERT, EdgeCoder or LFM2.5.
- I found no head-to-head of mmBERT against XLM-R-*large* on any token task.
- I found no small-data (≤1k examples) fine-tuning studies for these encoders.
- The XLM-R-large WikiANN score (about 65 in XTREME) was not re-fetched.

## Q3. Architectural features for speed and long text, and CPU/ONNX/MPS compatibility

### Takeaway
ModernBERT-family speedups (unpadding, FlashAttention-2, local/global attention) are largely **GPU features**. On CPU and MPS the models fall back to SDPA or eager attention, so the main CPU win is fewer non-embedding parameters. An 8k context lets 512/128 sliding windows go away, but attention cost still grows with length.

ONNX export for ModernBERT exists in Optimum, after a fix. CoreML ports exist but need op workarounds. DeBERTa-style relative attention (mDeBERTa, EdgeCoder) is the slowest on CPU at long lengths, and FlashDeBERTa is GPU/Triton-only. LFM2.5 is explicitly CPU-first.

### Cited Findings
- **mmBERT speed:** more than 2× faster than comparable models on variable-length inputs and about 4× faster on long contexts. mmBERT-small is about 2× faster than mmBERT-base. Both handle 8,192 tokens, whereas XLM-R stops at 512. Speed was measured on GPU. [V] — [mmBERT paper](https://arxiv.org/html/2509.06888)
- **ModernBERT architecture:** alternating attention (a global layer every third layer, otherwise a 128-token local window), unpadding and FA2. [R] — [arXiv 2412.13663](https://arxiv.org/abs/2412.13663)
- **ModernBERT ONNX:** Optimum PR #2208 added ONNX export-optimization support (fixing issue #2177). Users report export tracebacks for fine-tuned models on older versions. [V-search] — [optimum PR](https://github.com/huggingface/optimum/pull/2208), [HF discussion](https://huggingface.co/answerdotai/ModernBERT-base/discussions/77)
- **ModernBERT on CoreML / Apple Neural Engine:** over 40% of latency initially came from a few ops not mapped to the ANE. An accuracy fix required a LayerNorm→RMSNorm equivalence. [V-search] — [engineered.at](https://engineered.at/articles/deploying-modernbert-on-apple-neural-engine)
- **Community CoreML conversions** of ModernBERT-base and -large exist. [V-search] — [finnvoorhees/ModernBERT-CoreML](https://huggingface.co/finnvoorhees/ModernBERT-CoreML)
- **ONNX Runtime CPU gaps:** one multilingual-embedder ONNX/CoreML project had to patch about 15 missing bf16 CPU kernels in ORT. [V-search] — [HF](https://huggingface.co/usama99athar/multilingual-embedders-onnx-coreml)
- **FlashDeBERTa** (Apache-2.0) offers Triton kernels for disentangled attention. On an L4 at 4,096 tokens it runs 10.2× faster with 93% less memory, and the reference implementation runs out of memory at 8,192 tokens. It is GPU-only. The ModernELECTRA paper reports **no CPU, ONNX or quantization benchmarks**. [V] — [paper](https://arxiv.org/html/2611.31495)
- **EdgeCoder model card:** weights are BF16 safetensors, and the long-input example targets CUDA with `flashdeberta`. ONNX is not mentioned. [V] — [HF card](https://huggingface.co/knowledgator/EdgeCoder-Multilingual-61M)
- **LFM2.5-Encoder speed:**
  - 3.3× faster than ModernBERT-base at 8k tokens on CPU.
  - On Apple GPU, ModernBERT-base is faster at short lengths, and LFM2.5 overtakes it as inputs grow.
  - No absolute latencies are given, and ONNX and llama.cpp are not mentioned. [C] — [HF card](https://huggingface.co/LiquidAI/LFM2.5-Encoder-350M)
- **EuroBERT long context:** it maintains quality on long documents (MLDR and SeaHorse by length quantile). Annealing with random lengths up to 8,192 avoided degradation. [V] — [EuroBERT paper](https://arxiv.org/pdf/2503.05500)

### Inferences
- For the 4-core, ≤4 GB CPU target, the practical ranking by expected throughput is:
  1. EdgeCoder-M-61M.
  2. mmBERT-small.
  3. mmBERT-base or EuroBERT-210m.
  4. mDeBERTa-v3-base.
  5. XLM-R-large.
  6. EuroBERT-610m (worse than the baseline).
- All of these should export via ONNX (ModernBERT, Llama-style and DebertaV2 are standard Optimum architectures), with int8 dynamic quantization as the usual CPU path. This should be checked per model.
- On MPS, the FA2 and unpadding paths are unavailable. Expect standard SDPA behaviour.
- Moving from 512/128 windows to 2k–8k contexts helps cross-sentence spans. On CPU, however, quadratic attention in global layers can make one 8k pass slower than sixteen 512-token windows. Benchmark chunk lengths of 1k–2k first.

### Gaps
- I found no published CPU-latency benchmark comparing mmBERT, EuroBERT, EdgeCoder and XLM-R under ONNX.
- I found no confirmed ONNX export reports for mmBERT, EdgeCoder or LFM2.5.

## Q4. Verification of the EdgeCoder-31M / Multilingual-61M LinkedIn claims

### Takeaway
The headline numbers match Knowledgator's own preprint:
- EdgeCoder-31M: 8 layers, about 1T tokens, 8,192 context, GLUE 86.0.
- EdgeCoder-Multilingual-61M: 46 languages, GLUE 85.1 vs 84.7 for mmBERT-small, and 140.5M/61M = 2.3× smaller.

German is included, and the 61M model is Apache-2.0. The claims are narrow, though:
- GLUE is **English-only**.
- On multilingual XTREME and MTEB, EdgeCoder-M-61M is *behind* mmBERT-small: XTREME 67.8 vs 70.0, WikiANN 57.4 vs 59.4, MTEB-multilingual 43.8 vs 50.7.
- All results are single-seed, self-reported and not peer-reviewed.
- The BERT-large 85.2 comparison point was not located in the paper.

### Cited Findings
- **Paper:** "ModernELECTRA: Replaced-Token Detection with Boundary-Window Reconstruction for Compact Encoders that Classify and Embed", arXiv 2611.31495v1, 23 Nov 2026. Authors: Shtopko, Stepanov, Vodianytskyi, Lukashov (Knowledgator). The paper is CC-BY-4.0. [V] — [arXiv](https://arxiv.org/html/2611.31495)
- **EdgeCoder-31M:** 8 layers, 31.0M params, GLUE 86.0 vs 83.5 for Ettin-32m, 84.6 for MiniLM-L12 and 84.7 for BERT-base. MTEB-en v2 is 51.1. [V] — [arXiv](https://arxiv.org/html/2611.31495)
- **Baselines** were copied from other papers, and the authors warn that "differences of a few tenths should not be over-interpreted". [V] — [arXiv](https://arxiv.org/html/2611.31495)
- **EdgeCoder-M-61M details:**
  - 46 languages: all 24 EU languages, 12 Slavic languages and Latin. German appears on the model card.
  - Apache-2.0.
  - Discriminator-only checkpoint (no fill-mask head).
  - Loads via `AutoModel` / `AutoModelForTokenClassification`. [V] — [HF card](https://huggingface.co/knowledgator/EdgeCoder-Multilingual-61M)
- **The "ModernELECTRA" name is misleading.** The backbone is DeBERTa-v2/v3, with disentangled relative attention, no RoPE and no ModernBERT blocks, combined with an 8k-context curriculum. [V] — [arXiv](https://arxiv.org/html/2611.31495)
- **Limitations the authors state:** no controlled ablation of the window loss, single seed, GLUE↔MTEB trade-off depending on λ, and poor token-level results on unseen languages. [V] — [arXiv](https://arxiv.org/html/2611.31495)
- **Secondary coverage** repeats Knowledgator's claims without independent verification. [V-search] — [Data Phoenix](https://dataphoenix.info/news/modernelectra-boundary-window-preprint)

### Inferences
- The LinkedIn framing (GLUE vs BERT-large) is accurate for English classification. It says little about German span extraction, where mmBERT-small and XLM-R are stronger on the available token-level evidence.
- EdgeCoder-M-61M has the same tokenizer as mDeBERTa-v3 (251k vocab), so its German subword fertility should be like mDeBERTa's and XLM-R's. That is good for NER-type tasks, per EuroBERT's fertility analysis.

### Gaps
- I did not locate the "BERT-large 85.2" figure from the post in the paper.
- I found no independent replication, and no German-specific results for EdgeCoder.

## Q5. Known pitfalls: fine-tuning stability, small data, German tokenization

### Takeaway
The main risks are:
- **Tokenizer fertility:** EuroBERT's Llama-3 128k vocab measurably hurts NER. mmBERT uses Gemma-2 256k, and mDeBERTa and EdgeCoder use 250k SentencePiece. XLM-R's 250k remains a strong reference for German compounds.
- **Hyperparameter sensitivity:** the new encoders need learning-rate sweeps, and EuroBERT-2.1B notably underperformed without a thorough grid search.
- **Tokenizer and loading bugs** in fresh releases.
- **Evaluation gap:** every reported result comes from large training sets; none tests about 1k examples.

### Cited Findings
- **EuroBERT tokenizer effect on NER:** models are significantly better when entities split into fewer tokens, and F1 is comparable when fertility is matched. Doubling EuroBERT-210m's vocab would add about 100M params. [V] — [EuroBERT paper](https://arxiv.org/pdf/2503.05500)
- **EuroBERT fine-tuning protocol:**
  - Sweep of 10 log-spaced learning rates from 1e-5 to 1e-4, 10% warmup, linear decay.
  - Per-task best learning rates around 1.3e-5 to 4.6e-5, with Adam β2 of 0.95–0.98 and ε of 1e-5 to 1e-8.
  - EuroBERT-2.1B "benefits significantly from a more thorough grid search". [V] — [EuroBERT paper App. E](https://arxiv.org/pdf/2503.05500)
- **mmBERT example learning rates:** 3e-5 for XNLI (3 epochs, batch size 32, weight decay 0.01) and 2e-5 for the reranker. [V] — [HF card](https://huggingface.co/jhu-clsp/mmBERT-base)
- **EdgeCoder XTREME fine-tuning:** learning rates {1, 2, 3, 5, 8}e-5, 10% warmup, no weight decay, 10 epochs for WikiANN. Results are single seed. [V] — [arXiv](https://arxiv.org/html/2611.31495)
- **Ettin tokenizer bug:** a community "tokenizer-fix" re-upload of the Ettin encoder exists (stefan-it), which suggests a shipped tokenizer issue in a 2025 encoder. [V-search, details not read] — [HF](https://huggingface.co/stefan-it/ettin-encoder-400m-tokenizer-fix)
- **Custom code:** LFM2.5-Encoder requires `trust_remote_code`. The EdgeCoder model card's widget lists a custom training class (`FlashDebertaV2ForWindowElectraTraining`), unlike its usage section. [V] — [LFM card](https://huggingface.co/LiquidAI/LFM2.5-Encoder-350M), [EdgeCoder card](https://huggingface.co/knowledgator/EdgeCoder-Multilingual-61M)
- **Cross-paper comparisons are unreliable:** NeoBERT's reported MTEB retrieval baselines (21–32) differ from ModernBERT's own figures (38–42) for the same models. [V-search] — [HF papers](https://huggingface.co/papers/2502.19587)

### Inferences
- With about 1,000 chunks, run at least 3 seeds and a learning-rate sweep per backbone. Differences under about 1–2 F1 will be noise.
- Check for BIO label alignment issues:
  - Gemma and Llama BPE tokenizers handle leading spaces differently from XLM-R SentencePiece.
  - Verify `offset_mapping` and word alignment on German compounds and quotes before training.

### Licence summary (for Apache-2.0 commercial use)

| Licence | Models | Commercial use |
|---|---|---|
| Apache-2.0 | EdgeCoder-M-61M [V], EuroBERT [R], NeoMME [V], mGTE [R], ModernBERT [R], Granite R2 [V-search] | OK |
| MIT | mmBERT [V], XLM-R / mDeBERTa / XLM-V [R], Ettin [V-search], BGE-M3 [R] | OK |
| LFM Open License v1.0 | LFM2.5-Encoder [V] | Not Apache; a revenue threshold applies |
| CC-BY-NC-4.0 | jina-embeddings-v3 [R] | Excluded (non-commercial) |

### Gaps
- I found no published reports of training instability (loss spikes or divergence) for mmBERT, EuroBERT or EdgeCoder fine-tuning.
- I found no German compound-splitting fertility comparison across the Gemma-2, Llama-3, XLM-R and mDeBERTa tokenizers.
