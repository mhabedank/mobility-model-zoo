# Compressing and Speeding Up "scout-large" (XLM-R-large token classifier): Techniques, Numbers, Tooling

Scope note: researched 2026-11-27. Most primary numbers are from papers and docs dated 2019–2025; the year is given next to each one. Items marked "(abstract, not re-fetched)" are standard paper abstract claims cited to the primary arXiv page but not re-read in this session. Items under "Inferences" are my own reasoning or arithmetic and have no external source. Every technique below keeps the output extractive: the student or compressed model still emits per-token BIO tags over the original text, so spans stay verbatim.

Reference arithmetic used throughout (my own, from the public XLM-R configs: vocab 250,002; large = 24 layers × 1024 hidden; base = 12 × 768):
- XLM-R-large word-embedding matrix ≈ 250,002 × 1024 ≈ 256M params, so ≈ 46% of the 560M. The transformer body (the part that costs compute) is ≈ 300M.
- XLM-R-base embedding ≈ 192M of 278M total; body ≈ 86M.
- Per-token compute scales roughly with non-embedding parameters. Embedding lookup is a gather and costs almost nothing. **Vocabulary trimming therefore cuts RAM and disk but barely cuts latency. Latency comes from fewer or narrower layers, lower precision and less padding.**

---

## 1. Task-specific knowledge distillation into a small student (incl. new backbones)

### Takeaway
For multilingual NER, distilled students keep roughly 95–96% of the teacher's F1 at 6–13x parameter compression (XtremeDistil, 2020–21). Generic distillation such as DistilBERT or TinyBERT keeps about 97% on GLUE-style tasks at 2–7.5x. The best "scout-small" candidates are XLM-R-base (278M total / 86M body), Multilingual-MiniLM-L12-H384 (118M total / 21M body) and mmBERT-small (140M / 42M body). mmBERT's tokenizer has a documented weakness on NER/POS, so benchmark it against the XLM-R-vocab students before committing. Expect to lose a few F1 points against the teacher, then win part of them back with large-scale pseudo-labelling (section 2).

### Cited Findings
- **XtremeDistil (ACL 2020):** multilingual NER over 41 languages. It compresses mBERT by up to 35x in parameters and 51x in batch-inference latency while keeping 95% of F1. Its stage-wise scheme uses the teacher's internal representations and works with any teacher architecture. — [Mukherjee & Awadallah, ACL 2020](https://aclanthology.org/2020.acl-main.202); [arXiv 2004.05686](https://arxiv.org/abs/2004.05686v2)
- **XtremeDistilTransformers (2021), WikiAnn 41 languages:**
  - mBERT teacher: 91.86 avg F1, 179M params.
  - XtremeDistil: 88.64 F1, 28M params (6.4x compression, about 96% retention).
  - Smallest XtremeDistilTransformers: 88.18 F1, 14M params (12.8x compression, within 4% F1 of mBERT).
  — [arXiv 2106.04563](https://arxiv.org/pdf/2106.04563)
- **DistilBERT (2019):** 40% smaller and 60% faster, keeping 97% of BERT's language-understanding performance (GLUE, not NER). — [arXiv 1910.01108](https://arxiv.org/abs/1910.01108) (abstract, not re-fetched)
- **TinyBERT (2019/20):** the 4-layer TinyBERT keeps more than 96.8% of BERT-base on GLUE while being 7.5x smaller and 9.4x faster. It uses layer-wise distillation (embeddings, hidden states, attention matrices, logits) plus task-specific data augmentation. — [arXiv 1909.10351](https://arxiv.org/abs/1909.10351) (abstract, not re-fetched)
- **mmBERT (Sep 2025):**
  - mmBERT-small: 140M total, 42M non-embedding, 22 layers, 384 hidden.
  - mmBERT-base: 307M total, 110M non-embedding, 22 layers, 768 hidden.
  - Both use a 256k Gemma-2 tokenizer, FlashAttention-2 and unpadding, with 8192-token context. XLM-R and MiniLM cap at 512.
  — [mmBERT paper, arXiv 2509.06888](https://arxiv.org/html/2509.06888v1)
- **mmBERT on XTREME (zero-shot cross-lingual, trained on English):**

  | Model | WikiANN NER | UDPOS |
  |---|---|---|
  | mDistilBERT | 54.5 | 67.1 |
  | Multilingual MiniLM | 59.2 | 74.2 |
  | mmBERT-small | 54.3 | 70.6 |
  | XLM-R-base | 61.4 | 74.3 |
  | mmBERT-base | 58.2 | 74.0 |

  So on NER both mmBERT sizes trail XLM-R-base, and mmBERT-small trails Multilingual-MiniLM. The authors attribute this to "the lack of a consistent prefix whitespace token during pre-training" and expect prefix spaces to help. — [arXiv 2509.06888](https://arxiv.org/html/2509.06888v1); [HF blog: mmBERT](https://huggingface.co/blog/mmbert)
- **mmBERT speed:** mmBERT-base is more than 2x faster than older multilingual encoders on variable-length input and about 4x faster on long contexts. mmBERT-small is about 2x faster than mmBERT-base. These are relative GPU numbers; no CPU numbers are given. — [arXiv 2509.06888](https://arxiv.org/html/2509.06888v1)
- **EuroBERT-210m (Mar 2025):** a European-language encoder. The paper has a per-language NER table (Table 13), but I could not extract the German row. A heise.de practitioner test found German results at least as good as older German-only models and clearly better than ModernBERT; this is anecdotal, with no F1 given. About 6% of the training data is German. German PII token-classification fine-tunes exist, for example OpenMed's 210M ONNX/Android model. — [EuroBERT, arXiv 2503.05500](https://arxiv.org/pdf/2503.05500); [heise](https://heise.de/-10329005); [OpenMed PII German EuroMed 210M](https://huggingface.co/OpenMed/OpenMed-PII-German-EuroMed-Large-210M-v1-onnx-android)

### Inferences
- **Candidate ranking for scout-small (DE+EN):**
  1. **XLM-R-base**, same tokenizer as the teacher. Distilling into it is simplest: logits align token by token with no subword re-mapping. Its body is about 3.5x cheaper than large.
  2. **Multilingual-MiniLM-L12-H384**, which also uses the XLM-R tokenizer. Its body is about 21M (from its HF model card; not re-fetched here), roughly 14x less compute than large, with NER (59.2) close to XLM-R-base (61.4) on XTREME.
  3. **mmBERT-small**: fastest at long context, but weaker on NER and uses a different tokenizer.
  4. **EuroBERT-210m**: plausible, but there is no German NER number yet.
- **Tokenizer match:** a student with the same tokenizer as the teacher can learn from token-level soft labels (KL on per-subword BIO distributions) and from hidden-state or attention distillation. A student with a different tokenizer needs labels projected at word or character level: use the teacher's span outputs, or average teacher logits per word. That is fine for BIO, but it rules out direct layer distillation.
- **Expected retention:** extrapolating from XtremeDistil (about 95–96% at 6–13x) and TinyBERT (about 97% at 7.5x), expect about 94–98% of the teacher's agreement-with-LLM-labels F1 for a 4–10x smaller student, before self-training. This is an estimate; no paper distils XLM-R-large itself for German/English NER.
- **Speed estimate for the release target (not measured):** body compute falls by about 7x (mmBERT-small) to 14x (MiniLM) against XLM-R-large. Applied to today's 8.1 s on 4 vCPU, a MiniLM or mmBERT-small student lands at roughly 0.6–1.5 s in FP32, before INT8. Peak RAM should fall well under 1 GB. XLM-R-base lands at roughly 2–3 s.
- **Distillation recipe that fits this setup:** train the student on the union of gold LLM-labelled data and teacher soft labels on unlabelled interviews. Loss = CE on hard labels + KL on teacher token distributions. Add an intermediate-layer MSE when the tokenizer matches. Distil the classification heads too, from the teacher's head logits.

### Gaps
- No published number for distilling XLM-R-large specifically into a small multilingual student for German NER.
- EuroBERT-210m German NER F1 (Table 13) was not extracted.
- EdgeCoder-61M: not researched. I found nothing on it as a multilingual NER backbone, and the name suggests a code model.
- mmBERT's NER result is zero-shot cross-lingual (trained on English, tested on all languages). In-language German fine-tuning may close part of the gap; this is untested.

---

## 2. The large model as pseudo-labeller on unlabelled in-domain text (self-training)

### Takeaway
Teacher pseudo-labels or soft labels on unlabelled text are the standard way to train small NER students. NuNER (EMNLP 2024) shows that a 125M encoder trained on LLM-annotated data reaches LLM-level transfer when fine-tuned. Unfiltered noisy pseudo-labels can hurt, so use soft labels, filter by confidence, and keep a gold-labelled validation set.

### Cited Findings
- **NuNER (EMNLP 2024):** GPT-3.5 annotated a subset of C4, giving 24.4M words with 4.38M annotations over 200k concepts. RoBERTa-base (125M) was further pre-trained on this data. The result beats GPT-3.5 and competes with GPT-4 in-context learning once more than about a dozen examples per entity type are seen, while being 56x smaller. Model and dataset are MIT-licensed. — [NuNER, ACL Anthology](https://aclanthology.org/2024.emnlp-main.660); [arXiv 2402.15343](https://arxiv.org/html/2402.15343v1)
- **Compact BERT-style NER students:** training combines a KL distillation loss on teacher logits with a pseudo-label loss, using the teacher's argmax on unlabelled examples as targets. — [arXiv 1910.06294](https://arxiv.org/pdf/1910.06294.pdf)
- **Speech NER (2022):** a LUKE teacher pseudo-labels a large unlabelled set, and a DistilBERT student trains first on that data, then on the gold data. This is the closest published analogue to "big teacher + unlabelled pool + small student". — [arXiv 2209.13736](https://arxiv.org/pdf/2209.13736.pdf)
- **UniTrans (2020):** the teacher's soft labels on unlabelled target-language text train the student, and a voting scheme adds high-confidence hard pseudo-labels. — [arXiv 2007.07683](https://arxiv.org/pdf/2007.07683v1.pdf)
- **Mixture of Short-channel Distillers (2022):** distils through several teacher-to-student layer channels using soft labels on unlabelled data (cross-lingual NER). — [arXiv 2212.03506](https://ar5iv.labs.arxiv.org/html/2212.03506)
- **Risk:** SLaM (2023) argues that training on noisy teacher pseudo-labels "can significantly degrade student generalization" and proposes mixing in student labels. — [arXiv 2302.03806](https://arxiv.org/pdf/2302.03806)

### Inferences
- **Cost is not an issue.** At 1,260 chunks/min on the DGX Spark, the teacher pseudo-labels about 1.8M chunks per day. Generating 100k–1M soft-labelled in-domain chunks takes hours.
- **Soft labels beat hard labels here:** they carry the teacher's uncertainty at span boundaries, which is exactly where extractive agreement with LLM labels is won or lost.
- **Prefer the closest available labels:** quality is measured against frontier-LLM labels, and the teacher is itself an approximation of those. Where LLM labels exist, train the student on them directly. Use teacher soft labels for scale and LLM labels as the anchor (NuNER-style).

### Gaps
- I found no paper that quantifies the gain from adding N unlabelled pseudo-labelled examples for a small multilingual NER student. The DualNER, UniTrans and MSD result tables were not extracted.

---

## 3. Quantization: INT8 / INT4 / FP16 / BF16 and per-platform tooling

### Takeaway
On CPU, dynamic INT8 through ONNX Runtime/Optimum typically gives about 2–3x speedup and 4x smaller weights. For NER the accuracy effect ranges from negligible (−0.6 F1) to catastrophic (−14 F1), so validate per model. Exclude sensitive layers or use static/QAT if it degrades. FP16/BF16 is the safe default on GPU and Apple. On the AMD EPYC target use the `avx512_vnni` preset if the CPU is Zen 4 or newer, otherwise `avx2`. AMX (Intel only) does not apply.

### Cited Findings
- **Microsoft (Apr 2022):** dynamic INT8 quantization degraded a production NER transformer by about 14 F1. The team switched to FP16 instead: checkpoint about 1.8 GB → 0.9 GB, and ONNX Runtime + FP16 gave 2.88x throughput over PyTorch on a T4 GPU. — ["Scaling-up PyTorch inference… with ONNX Runtime", Microsoft Open Source Blog, 2022](https://opensource.microsoft.com/blog/?p=90966)
- **Chalmers thesis (biomedical NER, BioBERT):** pruning plus ONNX Runtime 8-bit dynamic quantization cut CPU latency from 32.52 ms to 12.02 ms (2.6x). F1 went 0.954 → 0.948. The quantization effect is not isolated from pruning. — [Chalmers ODR](https://odr.chalmers.se/bitstreams/2a911d3d-e854-467b-9a02-6b9ad5d58216/download)
- **Optimum benchmark runs (DistilBERT, CoNLL-2003, 2022):** dynamic quantization left F1 roughly unchanged, with latency around 59 ms → 22 ms. The tables are garbled and the hardware is unclear. — [HF fxmarty CoNLL-2003 run](https://huggingface.co/fxmarty/20220712-h07m20s32_example_conll2003)
- **Community INT8 ONNX NER model (Portuguese legal NER):** reports 2.6–3.0x over transformers+torch on a 12th-gen Intel CPU with AVX-VNNI. F1 not reported. — [HF model card](https://huggingface.co/luizedu91/ner-bert-lenerbr-onnx-int8)
- **Optimum ONNX Runtime quantization tooling:**
  - `optimum-cli onnxruntime quantize` with presets `--arm64`, `--avx2`, `--avx512`, `--avx512_vnni` and `--tensorrt`, plus `--per_channel`.
  - Dynamic: `AutoQuantizationConfig.avx512_vnni(is_static=False)`.
  - Static: calibration via `AutoCalibrationConfig.minmax`, needing about 50+ samples.
  — [HF Optimum-ONNX quantization guide](https://huggingface.co/docs/optimum-onnx/onnxruntime/usage_guides/quantization)
- **Intel CPUs:** BF16 on Sapphire Rapids AMX through Optimum gave about 3x faster transformer predictions (2023). Intel/Tencent report about 2x BERT throughput from INT8 on 4th-gen Xeon with a fused BERT op. AMX exists only on Intel 4th/5th-gen Xeon, and OpenVINO auto-converts to BF16 when AMX is present. — [HF blog: Sapphire Rapids inference](https://huggingface.co/blog/intel-sapphire-rapids-inference); [Intel/Tencent brief](https://intel.com/content/www/us/en/products/docs/accelerator-engines/advanced-matrix-extensions/tencent-solution-brief.html); [Intel AMX quick start](https://cdrdv2-public.intel.com/794448/AMX%20Quick%20Start%20Guide.pdf)
- **CTranslate2:** lists XLM-RoBERTa among supported architectures. For BERT and DistilBERT it implements only the encoder (plus pooler); "task-specific layers" must run in PyTorch. FP16 and INT8 variants are documented. — [CTranslate2 Transformers guide](https://opennmt.net/CTranslate2/guides/transformers.html)
- **llama.cpp / ggml:** supports BERT-family models, mainly as embedding models through `/embedding` with pooling. A GGUF of an XLM-R NER model exists (F32/Q8_0/Q4_K), but it targets a third-party runtime ("CrispEmbed"). I could not confirm that llama.cpp runs a token-classification head. — [llama.cpp README](https://raw.githubusercontent.com/ggml-org/llama.cpp/b9222/README.md); [cstr/xlmr-ner-hrl-GGUF](https://huggingface.co/cstr/xlmr-ner-hrl-GGUF)
- **Apple Silicon:**
  - MLX benchmark (2025): XLM-R-base at batch size 1 runs at about 5.7 ms on M2 Max (MLX GPU), 17 ms on M1, and 7 ms on an NVIDIA A10 (CUDA). At batch 32: 49 ms (M2 Max), 269 ms (M1), 27 ms (A10).
  - MLX-GPU is about 2–3x faster than MLX-CPU.
  - PyTorch CPU ran BERT-base at about 100 ms average against 557 ms for MLX-CPU on M1.
  — [arXiv 2510.18921](https://arxiv.org/html/2510.18921v1)
- **Apple Neural Engine:** Apple's ANE-optimized DistilBERT in CoreML measured about 4.4 ms per inference, about 10x faster than PyTorch CPU (hobbyist report, unsure the ANE was actually used). A ModernBERT-on-ANE write-up says speed plus accuracy needs architecture rewrites and careful FP16 numerics; over 40% of latency first came from ops not mapped to the ANE. — [anentropic/experiments-coreml-ane-distilbert](https://github.com/anentropic/experiments-coreml-ane-distilbert); [Deploying ModernBERT on ANE](https://engineered.at/articles/deploying-modernbert-on-apple-neural-engine)

### Inferences
- **CPU release path:**
  1. Export with `optimum-cli export onnx --task token-classification`.
  2. Apply ORT graph optimization (attention/LayerNorm/GELU fusion).
  3. Dynamic INT8 with per-channel weights.
  4. Check F1 and span agreement on held-out LLM-labelled interviews.
  5. If the drop exceeds about 0.5 F1, exclude the classifier head and the first/last layers from quantization, or use static calibration or QAT.

  Expected: about 2–3x on the CPU path, roughly 4x smaller weights for the quantized matrices. With an INT8 small student on top of distillation, CPU time for the 9,240-character text plausibly falls to about 0.3–0.7 s (estimate).
- **The AMD EPYC target:** Zen 4 (Genoa/Bergamo) and later support AVX-512 VNNI and BF16, but not AMX. Zen 2/3 (Rome/Milan) have AVX2 only. Check `lscpu` flags (`avx512_vnni`, `avx512_bf16`). The Intel AMX numbers above do not transfer.
- **INT4/weight-only quantization** mainly helps memory-bound LLM decoding. Encoders on batch-of-chunks input are compute-bound, so INT4 gives size savings with little or no speedup on CPU, and adds quantization risk for token boundaries. Not recommended beyond INT8 for this task.
- **NVIDIA (GB10):**
  - FP16/BF16 with SDPA/FlashAttention is the safe path, using `torch.compile` or ONNX Runtime CUDA/TensorRT EP.
  - TensorRT INT8 requires calibration.
  - At 0.12 s per interview the large model is already fast enough there, so the GPU mostly matters as the pseudo-labelling engine.
- **Apple:**
  - Simplest: MPS/MLX in FP16.
  - Highest efficiency: CoreML on ANE, but it needs model surgery and validation of FP16 numerics.
  - ONNX Runtime CoreML EP: no evidence found.
  - A small student in FP16 on M3 Pro should land well under 0.2 s for this text (estimate from the 0.84 s large baseline and a 3.5–14x compute reduction).

### Gaps
- No controlled study isolates INT8 dynamic quantization on a standard NER benchmark for XLM-R; the reported effects range from −0.6 to −14 F1.
- No ONNX Runtime CoreML EP benchmarks for BERT token classification found.
- No measured OpenVINO numbers on AMD EPYC found.
- No TensorRT or `torch.compile` encoder numbers for GB10 found.
- 2026 maturity of the `optimum-onnx` split package: only the docs page was confirmed.

---

## 4. Pruning (layer dropping, structured/block/movement) and vocabulary trimming

### Takeaway
Dropping top layers is a strong cheap baseline: up to 40% smaller while keeping up to 98% of performance (Sajjad et al., 2020–23). Structured/block pruning gives about 2.4x speed at about 1 F1 loss on SQuAD (2021). Vocabulary trimming removes most of the 256M embedding parameters with no measurable loss at about 30–60k tokens (classification/NLI; NER not tested). That is a big RAM/disk win, but nearly zero latency gain.

### Cited Findings
- **Layer dropping:** BERT, RoBERTa and XLNet pruned up to 40% (by dropping layers) keep up to 98% of performance. Dropping top layers works consistently well, lower layers matter most, and some tasks need only 3 layers to stay within 1%. The authors recommend top-layer dropping as a baseline for distilled models. — [Sajjad et al., arXiv 2004.03844](https://arxiv.org/abs/2004.03844)
- **Block pruning (2021):** BERT 2.4x faster and 74% smaller on SQuAD v1 with about a 1% F1 drop. — [Lagunas et al., arXiv 2109.04838](https://arxiv.org/abs/2109.04838) (abstract, not re-fetched)
- **CoFi structured pruning (2022):** over 10x speedups with a small accuracy drop on GLUE/SQuAD. — [Xia et al., arXiv 2204.00408](https://arxiv.org/abs/2204.00408) (abstract, not re-fetched)
- **Movement pruning (2020):** combined with distillation it reaches minimal accuracy loss down to 3% of encoder weights. The sparsity is unstructured. — [Sanh et al., arXiv 2005.07683](https://arxiv.org/abs/2005.07683) (abstract, not re-fetched)
- **Vocabulary trimming (Ushio et al., EMNLP Findings 2023), XLM-R-base results:**
  - Size: 278M total → 109M with top-30K vocab, 132M with top-60K.
  - Full per-language trim: German keeps 91K vocab (156M params, 56%); English keeps 173K (219M, 79%).
  - Post-fine-tuning trim, German NLI: 79.9 → 79.9 at 30K and 60K, 78.9 at 10K. German sentiment: 73.2 → 73.7 (30K), 72.4 (10K).
  - Post-fine-tuning trimming is more robust; pre-fine-tuning trimming varies (e.g., about −5 on Arabic sentiment).
  - About 30K tokens (39% of parameters) keeps NLI performance.
  - NER/token tasks were not evaluated. Library: [asahi417/lm-vocab-trimmer](https://github.com/asahi417/lm-vocab-trimmer).
  — [Ushio et al., ACL Anthology](https://aclanthology.org/2023.findings-emnlp.981); [ar5iv](https://ar5iv.labs.arxiv.org/html/2305.15020)
- **Gurgurov et al. (2025):** apply vocabulary trimming plus distillation plus pruning to XLM-R-base and mBERT. Restricting to the top 40K tokens per language caused no measurable loss. — [arXiv 2505.16956](https://arxiv.org/html/2505.16956v2)

### Inferences
- **Vocabulary trimming for scout-large (post-fine-tuning, DE+EN top-n from the in-domain corpus plus a general DE/EN corpus):**
  - At about 60K tokens the embedding shrinks from about 256M to about 61M params, giving a total of about 365M instead of 560M.
  - That is about 0.8 GB less in FP32, or about 0.4 GB in FP16.
  - Latency gain: only marginal.
  - Risk for extraction: unknown-token handling. Any input subword outside the kept vocab must map to `<unk>` or be re-tokenized. Use a coverage check on a large in-domain sample. The tool re-maps the tokenizer, so outputs remain verbatim offsets.
- **Same lever on the student:**
  - XLM-R-base trimmed to 60K ≈ 132M params, which falls inside the 30–150M "scout-small" target.
  - Multilingual-MiniLM trimmed to 60K ≈ 21M + 23M ≈ 45M params.
- **Layer dropping on the teacher (e.g., keep the bottom 12–16 of 24 layers, then re-fine-tune or distil):** about 1.5–2x faster with a likely small loss. This is the cheapest experiment, but it gives less than switching to a smaller backbone.
- **Unstructured sparsity (movement pruning) does not speed up dense CPU/GPU kernels** without sparse runtimes (e.g., DeepSparse), so prefer structured pruning or a smaller student.

### Gaps
- No published vocabulary-trimming results on NER/token classification. The XLM-R-large trim was not tested in the paper.
- Block-pruning and CoFi numbers are from English GLUE/SQuAD, not multilingual NER.

---

## 5. Runtime tricks and tool maturity

### Takeaway
Cheap engineering wins come from less padding (sort by length, dynamic padding), sensible thread settings, and choosing windows and stride to minimize duplicate tokens. Model2Vec-style static embeddings are a poor fit for contextual BIO tagging. For an encoder head, ONNX Runtime (+ Optimum) is the most mature cross-platform runtime. CTranslate2 supports the XLM-R encoder, but the head must run outside it. llama.cpp/ggml is embedding-oriented.

### Cited Findings
- **mmBERT:** uses unpadding and FlashAttention-2 inherited from ModernBERT, the source of its more than 2x speed on variable-length batches. — [arXiv 2509.06888](https://arxiv.org/html/2509.06888v1)
- **Batching on Apple Silicon MLX is sublinear:** BERT-base batch 1 → 32 raises latency about 9x on M2 Max, so batching helps throughput. — [arXiv 2510.18921](https://arxiv.org/html/2510.18921v1)
- **CTranslate2:** XLM-RoBERTa supported; encoder only, with task heads run in PyTorch. — [CTranslate2 guide](https://opennmt.net/CTranslate2/guides/transformers.html)
- **llama.cpp:** BERT support exists, aimed at embeddings. — [llama.cpp README](https://raw.githubusercontent.com/ggml-org/llama.cpp/b9222/README.md)

### Inferences (no external source; general engineering practice)
- **Windows and stride:** a 9,240-character interview is roughly 2,300–2,700 XLM-R tokens. With 512-token windows, overlap stride is pure duplicate compute: stride 128 adds about 33% extra tokens. Use 512 windows with a small overlap (about 32–64 tokens) and merge spans at the seams. A long-context student (mmBERT, 8k) could process the whole interview in one pass, removing seam handling. On CPU, attention cost at 2.5k tokens is still modest for a 384-hidden model.
- **CPU threads:**
  - Set intra-op threads equal to physical cores (4).
  - Run one session and batch the chunks of one document together.
  - Avoid oversubscription between PyTorch/ORT and tokenizer threads, e.g., set `TOKENIZERS_PARALLELISM=false` during inference or pin threads.
  - ORT `SessionOptions.intra_op_num_threads=4` with graph optimization level ALL.
- **Padding:** sort chunks by length and use dynamic padding to the longest in the batch. Gains are proportional to padding waste. They are small for fixed 512-token windows and larger for variable-length segments, such as splitting by speaker turn.
- **Early exit** (per-layer confidence) is possible for classification but awkward for token-level BIO, where every token needs the final layer. Low priority.
- **Model2Vec/static embeddings:** they produce one vector per token type with no context, so they cannot resolve BIO boundaries that depend on context. Not suitable for this extractive task (reasoned conclusion; not checked against a published benchmark).
- **candle (Rust):** has XLM-R/BERT examples in its repo (unverified in this session). It is viable for a small-footprint deployment but needs a hand-written head and less tooling than ONNX Runtime.

### Gaps
- No measured numbers found for sort-by-length or dynamic padding on CPU token classification.
- Candle token-classification support and 2026 maturity not verified.
- No published evaluation of Model2Vec on NER found.
- OpenVINO token-classification numbers on AMD CPUs not found.

---

## Summary playbook (synthesized; numbers are estimates unless cited above)

| Step | Size effect | Expected speed (CPU, 4 vCPU) | Expected quality loss | Tooling |
|---|---|---|---|---|
| ORT export + graph fusion (FP32) | none | ~1.2–1.5x (est.) | none | Optimum / ONNX Runtime |
| Dynamic INT8 (per-channel), large model | weights ~4x smaller | ~2–3x (cited range) | −0.1 to −14 F1 (cited range); validate | `optimum-cli onnxruntime quantize --avx512_vnni` / `--avx2` |
| Vocab trim to ~60K DE+EN, large | 560M → ~365M params | ~1.0x | ~0 on classification/NLI (cited); NER untested | lm-vocab-trimmer |
| Top-layer dropping 24 → 12–16 + re-distil | −30–45% body | ~1.5–2x | ≤2% (cited up to 98% retention) | HF Transformers |
| Distil into XLM-R-base (+ trim) | ~132M with 60K vocab | ~3.5x | ~2–5% relative (est., XtremeDistil-like) | HF Trainer, custom KD loss |
| Distil into Multilingual-MiniLM-L12-H384 (+ trim) | ~45–118M | ~10–14x | ~3–6% relative (est.) | same tokenizer as XLM-R |
| Distil into mmBERT-small | 140M (42M body) | ~7x, plus long context | NER weaker on XTREME (cited); test | different tokenizer: word-level KD |
| + teacher pseudo-labels on large unlabelled corpus | none | none | recovers part of the gap (NuNER-style evidence) | DGX Spark for labelling |
| FP16/BF16 on GPU / Apple | 2x smaller | GPU ~2–3x (cited 2.88x ORT FP16 on T4) | ~0 | torch SDPA, ORT CUDA/TRT EP, MLX, CoreML |
