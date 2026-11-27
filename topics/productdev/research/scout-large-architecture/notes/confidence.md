# Confidence, Calibration and Uncertainty for scout-large (Encoder Span Extraction + Document Classification)

Scope note: Research done 2026-11-27. Sources from 2020–2022 are marked [older]; 2025–2026 are marked [recent]. A few standard references were not opened in this session; they are listed as "not verified this session" and should be checked before being cited in the final report. Numbers worked out by me (not taken from a source) are marked as inferences.

Context restated: XLM-RoBERTa-large, German+English, extracts verbatim spans (jobs/pains/gains) with a per-item score, classifies attributes per item, predicts document relevance as a probability. Thresholds (unit 0.5, relevance 0.70) tuned on 105 validation rows. Relevance kappa vs frontier-LLM reference = 0.54 (95% CI 0.25–0.76, n=147 units). Labels come from an LLM teacher; the two reference LLMs disagree on 1,574 items.

## 1. How calibrated are fine-tuned encoders out of the box? Do ELECTRA or newer encoders do better?

### Takeaway
Fine-tuned BERT/RoBERTa classifiers are reasonably calibrated in-domain and better than non-pretrained models out-of-domain, but still benefit from temperature scaling [older evidence]. A large 2022 study ranks ELECTRA as the best-calibrated common encoder, with RoBERTa/DeBERTa/XLNet ahead of BERT. Structured outputs (NER/span tagging) show clearly higher calibration error than sentence classification, so "the classifier looks calibrated" does not carry over to the span scores.

### Cited Findings
- [older, EMNLP 2020] Desai & Durrett studied BERT and RoBERTa on NLI, paraphrase detection and commonsense reasoning. Out of the box the models are calibrated in-domain, and out-of-domain they are much better calibrated than non-pretrained baselines (ESIM). Temperature scaling (one scalar on the logits) effectively reduces in-domain ECE further, and label smoothing (deliberately raising empirical uncertainty) helps calibration out-of-domain. Metric: ECE. — [Desai & Durrett, Calibration of Pre-trained Transformers (arXiv 2003.07892)](https://arxiv.org/abs/2003.07892); [ACL Anthology](https://aclanthology.org/2020.emnlp-main.21)
- [older, EMNLP Findings 2021] A follow-up studied how calibration changes with model size. It reports that post-hoc calibration further reduces calibration error for all models in-domain. — [2021.findings-emnlp.180](https://aclanthology.org/2021.findings-emnlp.180) (seen only as a search snippet; not opened)
- [older, EMNLP Findings 2022] Xiao et al. ran a large-scale study over four dimensions (PLM choice, PLM size, uncertainty quantifier, fine-tuning loss) on three classification tasks, including domain shift. In-domain, XLNet, ELECTRA, RoBERTa and DeBERTa have lower ECE than BERT. The PLM ranking by ECE is fairly stable across tasks. Their recommendations: (1) use ELECTRA, (2) use larger PLMs where feasible, (3) use temperature scaling as the uncertainty quantifier, (4) fine-tune with focal loss. — [Xiao et al., Uncertainty Quantification with Pre-trained Language Models (arXiv 2210.04714)](https://arxiv.org/abs/2210.04714)
- [older] Chen et al., "A Close Look into the Calibration of Pre-trained Language Models", asks (1) whether PLMs become calibrated during training and (2) how effective existing calibration methods are. — [arXiv 2211.00151](https://arxiv.org/pdf/2211.00151.pdf) (abstract only seen; detailed findings not verified)
- [recent, 2024] "The Reliability Paradox" links shortcut learning to miscalibration and reports DeBERTa with higher ECE than BERT on several tasks. This conflicts with Xiao et al.'s DeBERTa-over-BERT ranking, so the encoder ranking depends on the task/setup. — [arXiv 2412.15269](https://arxiv.org/pdf/2412.15269)
- [older, ACL 2020] Jagannatha & Yu report that neural networks show high calibration error on structured NLP tasks (POS, NER, span QA). Because the output space of a sequence labeller is huge, each full output has small probability, so standard binary/multi-class calibration does not transfer directly. — [Jagannatha & Yu, Calibrating Structured Output Predictors for NLP (arXiv 2004.04361)](https://arxiv.org/abs/2004.04361); [ACL Anthology](https://aclanthology.org/2020.acl-main.188)

### Inferences
- XLM-RoBERTa-large is in the "RoBERTa family" that Xiao et al. rank ahead of BERT, but none of the sources measured XLM-R specifically or German text. Swapping in ELECTRA/mDeBERTa for calibration alone is not justified by evidence: the effect is modest, rankings conflict across papers (Xiao vs. Reliability Paradox), and temperature scaling closes much of the gap at nearly no cost.
- The weakest calibration is most likely in the span scores, not the relevance head. Jagannatha & Yu show that structured outputs are worse calibrated than plain classification, and scout's span scores are aggregated token probabilities.
- Out-of-the-box calibration evidence is measured against gold human labels. Scout is trained on, and judged against, LLM teacher labels, so "calibrated" here can only mean "calibrated against the teacher/reference LLMs". That is a different and noisier target (see section 5).

### Gaps
- I found no published calibration numbers for XLM-RoBERTa-large or mDeBERTa-v3 on German token classification.
- I found no 2025–2026 study that systematically compares the calibration of ModernBERT/EuroBERT-class encoders. Treat any claim that "newer encoders are better calibrated" as unverified.

## 2. Post-hoc calibration: temperature/Platt/isotonic, per-class, and span-level scores

### Takeaway
For the document relevance head and the per-item attribute classifiers, temperature scaling (1 parameter) or Platt scaling (2 parameters) is the right choice at n≈100. Isotonic regression needs more data. For spans, the established method calibrates each entity (span) as a binary "is this span correct?" event, using a small calibrator over features of the span. It does not trust any single raw aggregate (min, mean or product of token probabilities).

### Cited Findings
- Temperature scaling (one scalar on the logits) is "widely effective" for in-domain calibration of BERT/RoBERTa. — [Desai & Durrett 2020](https://arxiv.org/abs/2003.07892)
- Xiao et al. recommend temperature scaling as the default uncertainty quantifier after comparing it with other quantifiers across PLMs. — [arXiv 2210.04714](https://arxiv.org/abs/2210.04714)
- [older] Jagannatha & Yu propose a general calibration scheme for "output entities of interest" in structured prediction. It can be used with any binary calibration method and any neural model. It beats existing calibration techniques on NER, POS and QA, and stays better out of domain. Used as an uncertainty-aware, entity-specific decoding step, the calibrator also improves task performance at no extra training cost. — [arXiv 2004.04361](https://arxiv.org/abs/2004.04361)
- [older] For sequence-level uncertainty in NER, Vazhentsev et al. aggregate token uncertainties into a sequence score by maximum (for Mahalanobis-distance methods) or by summation (for other methods). A sequence counts as an error if any token is wrong. — [Vazhentsev et al., ACL 2022 (full text)](https://aclanthology.org/2022.acl-long.566.pdf)
- Not verified this session (standard reference): Guo et al. 2017, "On Calibration of Modern Neural Networks", introduced temperature scaling and showed it beats Platt/isotonic/histogram binning on many vision/NLP classifiers — [arXiv 1706.04599](https://arxiv.org/abs/1706.04599)

### Inferences
- Relevance head: fit one temperature T (or Platt a,b) by minimising NLL on held-out data, then re-tune the 0.70 threshold on the calibrated probability. With 105 rows, 1–2 parameters is about all the data can support. Isotonic regression (a step function with many free steps) will overfit at this n.
- Attribute classifiers: one shared temperature per attribute head, not per class. Per-class (vector) scaling multiplies the parameters and is not supportable with ~100 documents unless classes have many items each.
- Span scores, practical recipe (inference, based on Jagannatha & Yu's "entity as binary event" framing):
  1. For each predicted span, compute a few cheap features: mean token probability, min token probability, product (or mean log-probability, which is length-normalised), boundary-token probabilities (B- tag prob, prob that the token after the span is O), span length, item type (job/pain/gain), and the document relevance score.
  2. Label each predicted span correct/incorrect against the reference, using exact match or a relaxed overlap threshold (decide and document which).
  3. Fit a logistic regression on those features (a handful of parameters). That gives a calibrated P(span correct).
  - Why not a raw aggregate? Products shrink with length (long spans look unsure). Means hide a single weak boundary token. Min is sensitive to one token. Boundary errors are the most common span error type, so boundary probabilities are usually the most informative feature. This last point is a widely held view, not verified here; test it on the data.
- Calibrate span scores with item-level cross-validation grouped by document. All items from one document should sit in the same fold, so that leakage between correlated items does not inflate apparent calibration.

### Gaps
- I did not find a head-to-head study comparing min vs. mean vs. product vs. boundary-based span scoring for calibration on a BIO tagger. Jagannatha & Yu's exact feature set and calibrator type (I recall a tree-based forecaster) were not verified from the full text in this session.
- Netcal (a Python library with temperature/Platt/isotonic/BBQ and ECE/reliability diagrams) was not checked in this session.

## 3. Uncertainty methods: ensembles, MC dropout, SNGP, Mahalanobis, evidential, Laplace — cost vs. benefit on 4-core CPU

### Takeaway
The strongest CPU-friendly evidence favours deterministic, single-pass methods. The plain max-softmax baseline plus temperature scaling is a strong default. Mahalanobis distance on the encoder's features, with spectral normalisation of the classifier layer (MD SN), matched or beat MC dropout and deep ensembles for misclassification detection in Transformer text classification. However, for token-level NER no method clearly beat the max-softmax baseline. SNGP did badly on NER. MC dropout and ensembles multiply inference cost (N forward passes or N models) and are hard to justify for an XLM-R-large model on 4 CPU cores.

### Cited Findings
- [older, ACL 2022] Vazhentsev et al. ran the first study of uncertainty estimation (UE) for Transformer NER (CoNLL-2003), plus text classification (SST-2, CoLA, MRPC), mostly with ELECTRA. The metric was the area under the risk-coverage curve (RCC-AUC), at token and sequence level. — [ACL Anthology](https://aclanthology.org/2022.acl-long.566); [full text PDF](https://aclanthology.org/2022.acl-long.566.pdf)
  - Deep ensembles impose "substantial computational and memory overhead" in training, inference and weight storage, which they call a serious obstacle to deployment. — [same PDF](https://aclanthology.org/2022.acl-long.566.pdf)
  - Standard MC dropout gives big improvements over the softmax-response (SR = 1 − max prob) baseline on all text classification datasets and on sequence-level CoNLL-2003. But "for token-level CoNLL-2003, none of the considered methods substantially outperform the baseline." — [same PDF](https://aclanthology.org/2022.acl-long.566.pdf)
  - Their diverse DPP MC dropout (DDPP) costs "less than 0.5% of the overhead introduced by the standard MC dropout" at inference and beats the baseline on sequence-level NER, though not standard MC dropout itself. — [same PDF](https://aclanthology.org/2022.acl-long.566.pdf)
  - Loss regularisation (metric regularisation, CER) helps text classification but "appears to be malignant for NER". — [same PDF](https://aclanthology.org/2022.acl-long.566.pdf)
  - SNGP gives substantial gains on MRPC/SST-2 but "significantly falls behind the trivial baseline on CoNLL-2003". The authors attribute this to SNGP being designed for classification. — [same PDF](https://aclanthology.org/2022.acl-long.566.pdf)
  - Conclusion: computationally cheap UE methods "perform on par or even better than computationally intensive MC dropout and deep ensemble". Mahalanobis distance with spectral normalisation (MD SN) is best among the cheap methods. — [same PDF](https://aclanthology.org/2022.acl-long.566.pdf)
- [older] Xin et al. (ACL 2021) compared models and confidence estimators for selective prediction in NLP. Newer pre-trained transformers improve both accuracy and confidence estimation. They propose an error-regularisation trick that improves confidence estimation "without much extra compute". — [ACL Anthology 2021.acl-long.84](https://aclanthology.org/2021.acl-long.84)
- [older] Varshney, Mishra & Baral ran a large selective-prediction study over 17 datasets. They tested whether task-specific methods beat the simple MaxProb baseline. — [arXiv 2203.00211](https://arxiv.org/pdf/2203.00211v1.pdf) (abstract only seen; their headline finding, which I recall as "MaxProb is hard to beat consistently", was not verified here)

### Inferences
- Cost on 4-core CPU (my estimate from the method definitions): MC dropout with K samples ≈ K× encoder cost. An ensemble of M models ≈ M× compute and M× memory (XLM-R-large ≈ 560M parameters, so roughly 2.2 GB per fp32 copy). Both are impractical for a large encoder on 4 cores. Single-pass options add near-zero cost:
  - temperature/Platt scaling
  - Mahalanobis distance on the [CLS]/mean-pooled embedding for the relevance head (one matrix–vector product per document)
  - a learned span-correctness calibrator (section 2)
- Mahalanobis/feature-density scores mainly detect out-of-distribution or atypical inputs (for example a document type not seen in training). That suits "flag for review", but such a score is not a probability and must not be shown as one.
- For spans specifically, the Vazhentsev result (nothing beats max-softmax at token level) suggests putting effort into how token scores are aggregated into span scores and into calibrating that aggregate, not into Bayesian machinery.
- Cheap "ensemble" alternatives exist if variance is wanted: checkpoint ensembles or last-layer-only ensembles (several heads on one shared encoder pass). Cost is roughly one encoder pass plus a few small heads. I did not find direct evidence for these on NER in this session.

### Gaps
- Evidential deep learning and last-layer Laplace approximations for Transformer NER: no evidence gathered in this session. Both are single-pass and cheap at inference, but I cannot report their measured benefit for span extraction.
- TorchUncertainty (library) was not checked.
- No 2025–2026 benchmark of UE methods specifically for encoder span extraction was found.

## 4. Conformal prediction, risk control and selective prediction; is ~100 validation documents enough?

### Takeaway
Conformal methods for NER now exist [recent, 2026], and conformal prediction has been applied to token/entity-level document extraction with good results. The marginal guarantee holds for any calibration size n. But with ~100 documents, the coverage you actually get from one calibration set swings by several percentage points around the target. Item-level data is clustered within documents, which strains the exchangeability assumption. The authors of the main tutorial suggest n≈1000 for most purposes. The pragmatic route for scout is selective prediction (an abstain/flag-for-review band) evaluated with risk-coverage curves, with cross-validation and bootstrapping to report uncertainty. Formal guarantees should wait until a larger calibration set (several hundred documents) exists.

### Cited Findings
- [recent, 2026] Singer, Sengupta & Pazdernik build prediction sets of full-sentence NER labellings (top-k label sequences from CRF-based models) that are "guaranteed to contain the correct labeling with a user-specified confidence level". They also build subsequence (entity-span) level sets with class-conditional coverage. The framework handles variation by sentence length, language, entity type and number of entities. Four NER models on three benchmarks. — [arXiv 2601.16999](https://arxiv.org/abs/2601.16999)
- [recent, AISTATS 2026] Conference version: Mondrian conformal prediction stratified by input length and language, hybrid probability-index nonconformity scores, and a modified RAPS procedure. Experiments on CoNLL++, CoNLL-Reduced and WikiNEuRal. — [PMLR v300](https://proceedings.mlr.press/v300/singer26a.html); [AISTATS poster](https://virtual.aistats.org/virtual/2026/poster/11341)
- [recent, IJDAR 2026] Split conformal prediction applied to token-level and entity-level key information extraction with multimodal transformers. Reported 98.3% marginal coverage at α=0.02, with 70% of predictions being high-confidence singletons. — [DFKI PDF](https://www-live.dfki.de/fileadmin/user_upload/import/17320_s10032-026-00572-y.pdf) (numbers from search snippet; full text not read)
- Angelopoulos & Bates: the conformal coverage guarantee holds for any n, but it is an average over calibration draws. For one fixed calibration set, realised coverage varies and can be bounded with a δ parameter. The needed n can be computed explicitly, and they conclude n=1000 "is sufficient for most purposes". — [A Gentle Introduction to Conformal Prediction (arXiv 2107.07511)](https://arxiv.org/abs/2107.07511)
- Once the calibration split is fixed, the coverage probability on later exchangeable data is Beta-distributed. The test set's finite size adds further variance to observed coverage. — [arXiv 2605.24983](https://arxiv.org/pdf/2605.24983) (partial view; treat as secondary)
- Selective prediction is evaluated with the risk-coverage curve and its area (RCC-AUC, El-Yaniv & Wiener 2010), or with the reversed pair proportion (RPP) metric from Xin et al. 2021. — [Vazhentsev et al. 2022, §4.1](https://aclanthology.org/2022.acl-long.566.pdf)
- [older] "Post-Abstention" (Varshney & Baral, ACL 2023) studies what to do after a model abstains (for example re-attempting the abstained instances). It shows risk improvements on 11 QA datasets. — [arXiv 2305.01812](https://arxiv.org/abs/2305.01812)
- Not verified this session (standard references): conformal risk control, which controls expected loss such as the false-negative rate of a multi-label/span set — [Angelopoulos et al., arXiv 2208.02814](https://arxiv.org/abs/2208.02814). Libraries: MAPIE (scikit-learn compatible; classification, multi-label risk control) — [GitHub](https://github.com/scikit-learn-contrib/MAPIE); crepes (conformal classifiers/regressors, Mondrian) — [GitHub](https://github.com/henrikbostrom/crepes).

### Inferences
- Rough numbers at scout's n (my calculation using the standard split-conformal Beta result above). With n=105 and target 90% coverage, the realised coverage for a given calibration set follows about Beta(96, 10): mean ≈ 0.906, standard deviation ≈ 0.028. So any single calibration draw could give roughly 85%–96% coverage. With n=1000, the standard deviation falls to ≈ 0.009. The ~100-doc set therefore gives a valid-on-average but imprecise guarantee.
- Exchangeability: scout's units are items nested in documents. Conformal calibration should be done at document level, or use item-level scores with document-grouped splits. Treating 1,000 items from 105 documents as 1,000 independent calibration points overstates precision.
- Fit to scout's outputs:
  - Relevance: a conformal set over {relevant, not relevant}. Items whose set is {both} are the natural "review" queue. This is the binary case of what MAPIE supports.
  - Span extraction: conformal risk control on a recall/FNR-type loss ("include every candidate span with calibrated score ≥ λ, choose λ so that expected missed-reference-span rate ≤ α") fits an extractive model well. The output remains verbatim spans, only the number shown changes.
- Practical recipe for now: (a) Calibrate (sections 2/3). (b) Pick two thresholds per output: accept above t_hi, reject below t_lo, send the band in between to review. (c) Choose them from a risk-coverage curve built with 5-fold document-grouped cross-validation over all labelled data, not only the 105 rows. (d) Report bootstrapped confidence intervals (resampling documents) for the risk at the chosen coverage. The kappa CI of 0.25–0.76 already shows how wide document-level intervals are at this n.
- Getting more calibration data is the highest-leverage step. A few hundred more teacher-labelled (or, better, human-adjudicated) documents tightens every estimate above. Cost: LLM labelling only, no model change.

### Gaps
- I did not verify that the 2026 conformal NER methods work with a plain softmax BIO tagger (they describe CRF-based top-k sequence sets). Adapting them to a non-CRF XLM-R tagger may need a k-best decoder.
- I found no study of conformal prediction calibrated against LLM-generated (rather than human) labels. The guarantee then holds only relative to the label source used for calibration.

## 5. Learning from noisy/soft LLM teacher labels and teacher disagreement

### Takeaway
Training on soft targets (distributions) instead of hard majority labels is well supported as a way to improve calibration. The evidence comes from human-annotator studies and recent LLM-to-BERT distillation preprints. Calibrating against the full annotator distribution, not the voted label, gives the best calibration. Scout's two reference LLMs and its teacher can provide such distributions, and the 1,574 contested items are exactly where soft targets matter. The LeWiDi shared tasks supply the evaluation vocabulary: soft metrics and distance to the label distribution.

### Cited Findings
- [recent, 2025] LeWiDi-2025 (third edition, at NLPerspectives/EMNLP 2025) evaluates in two ways: soft-label prediction (population-level judgment distributions) and perspectivist prediction (individual annotator labels). It moved entirely to soft metrics and covers NLI, irony, sarcasm and paraphrase tasks. — [arXiv 2510.08460](https://arxiv.org/abs/2510.08460v2)
- Soft-label metrics in LeWiDi-2025: Manhattan distance for binary datasets, Wasserstein distance for Likert-scale ones. — [Opt-ICL at LeWiDi-2025 (arXiv 2510.07105)](https://arxiv.org/pdf/2510.07105)
- [recent] The DeMeVa team compared in-context learning with LLMs against label distribution learning on RoBERTa, and argued the latter is promising for soft-label prediction. — [arXiv 2509.09524](https://arxiv.org/pdf/2509.09524)
- [recent] LPI-RIT extended the DisCo architecture with annotator metadata and loss reweighting to model disagreement. — [arXiv 2508.08163](https://arxiv.org/abs/2508.08163v1)
- [recent, 2026] Calibrating against majority-voted one-hot labels is a limiting assumption when annotators disagree. Calibrating against the full annotator distribution gives the best overall calibration. — [arXiv 2603.22879](https://arxiv.org/html/2603.22879v1) (search snippet; not read in full)
- [recent, 2026] An LLM's predicted class plus its verbal confidence was turned into a soft target for fine-tuning a BERT classifier. The distilled BERT had lower ECE and Brier score than the LLM itself on the reported datasets. — [arXiv 2605.11954](https://arxiv.org/pdf/2605.11954) (snippet)
- [recent, 2025] LLMs used as annotators produce hard and soft labels. A classifier fine-tuned on these is then calibrated, compared against a majority-vote baseline. — [arXiv 2503.00489](https://arxiv.org/html/2503.00489v1)
- [older] Soft labels built from human annotator confidence or probabilistic judgments improve classifier performance and calibration, needing fewer annotators than aggregating many hard labels. — [Findings EMNLP 2023 (White Rose eprint)](https://eprints.whiterose.ac.uk/223247/1/2023.findings-emnlp.355.pdf); [arXiv 2207.00810](https://arxiv.org/pdf/2207.00810.pdf)
- [recent] "Soft-Label Training Preserves Epistemic Uncertainty". — [arXiv 2511.14117](https://ar5iv.labs.arxiv.org/html/2511.14117) (title only seen; claims not verified)
- Label smoothing raises empirical uncertainty and helps out-of-domain calibration of BERT/RoBERTa. — [Desai & Durrett 2020](https://arxiv.org/abs/2003.07892)
- Xiao et al. recommend focal loss for fine-tuning as part of a well-calibrated pipeline. — [arXiv 2210.04714](https://arxiv.org/abs/2210.04714)
- Practitioner (not peer-reviewed): soft-label distillation from LLM ensembles captures nuance that hard labels miss. — [Superhuman blog](https://blog.superhuman.com/soft-label-distillation-pipeline/)

### Inferences
- Relevance head: replace the hard teacher label with a soft target. Example: if teacher, reference-LLM-A and reference-LLM-B vote 2:1, the target is ≈0.67. Even better, use each LLM's own probability or verbal confidence if available. Train with cross-entropy against that distribution (or KL divergence). This is cheap (no inference change) and directly teaches the model that contested documents are uncertain.
- Spans/tokens: build token-level soft BIO targets from the overlap of spans extracted by several LLMs. A token inside spans from 2 of 3 teachers gets P(I)≈0.67. Contested items become lower-score extractions instead of noisy hard labels. This adapts LeWiDi-style label-distribution learning to token classification; I found no paper doing exactly this for LLM-teacher span extraction.
- Evaluation consequence: on contested items, judge confidence against the disagreement rate, not against one LLM's label. Report a soft metric (Manhattan or Brier against the soft target) alongside hard F1 and kappa. Kappa 0.54 vs. one frontier LLM is partly a ceiling effect if the reference LLMs disagree with each other. Report inter-LLM kappa as the ceiling.
- Label smoothing is a weaker, uniform substitute for real soft labels. Use real disagreement signals where available, and label smoothing (≈0.1) only where there is a single teacher label.

### Gaps
- No controlled study found that tests multiple LLM teachers → soft labels → calibration of an encoder in one comparison. The available evidence uses single-LLM verbal confidence or human annotators.
- No evidence found specifically on soft-label training for span extraction or BIO tagging.
- Whether the 1,574 contested items differ systematically (e.g. ambiguous categories vs. boundary disagreements) is a data question for the author.

## 6. Evaluation metrics and model-card reporting

### Takeaway
Use proper scoring rules (Brier, NLL) and reliability diagrams for calibration. Use risk-coverage curves (AURC / RCC-AUC) for "does the score rank errors correctly / is abstention useful". Evaluate spans at entity level (one correct/incorrect event per predicted span), not per token. With ~100 documents, use few bins, bootstrap confidence intervals and document-grouped cross-validation, and state the label source (LLM teacher) explicitly on the model card.

### Cited Findings
- ECE: the weighted average gap between accuracy and confidence across confidence bins. It is the standard metric in pretrained-transformer calibration studies. — [Desai & Durrett 2020](https://arxiv.org/abs/2003.07892)
- RCC-AUC (area under risk-coverage curve) measures how well an uncertainty score supports rejecting errors; lower is better. RPP (reversed pair proportion) measures how often a more-confident instance has a higher loss than a less-confident one. — [Vazhentsev et al. 2022](https://aclanthology.org/2022.acl-long.566.pdf); [Xin et al. 2021](https://aclanthology.org/2021.acl-long.84)
- For NER, uncertainty can be evaluated at token level (each token an instance) and at sequence level (an error if any token is wrong). Results differ markedly between the two: MC dropout helps at sequence level but not token level on CoNLL-2003. — [Vazhentsev et al. 2022](https://aclanthology.org/2022.acl-long.566.pdf)
- Under disagreement, soft metrics (Manhattan/Wasserstein distance to the label distribution) are the LeWiDi standard. — [LeWiDi-2025](https://arxiv.org/abs/2510.08460v2); [Opt-ICL](https://arxiv.org/pdf/2510.07105)
- With conformal methods, report empirical coverage and set size. Realised coverage on a finite test set has its own sampling variance. — [Angelopoulos & Bates](https://arxiv.org/abs/2107.07511); [arXiv 2605.24983](https://arxiv.org/pdf/2605.24983)

### Inferences
- Recommended evaluation protocol for scout (inference):
  1. Unit of analysis:
     - relevance = document
     - attributes = item
     - spans = predicted span (precision side: P(correct)) and reference span (recall side: was it found at score ≥ t?)
  2. Calibration: Brier score and NLL (proper scoring rules, less bin-sensitive than ECE). ECE with 5–10 equal-mass bins, since equal-width bins at n≈100 leave many bins nearly empty. Reliability diagram with per-bin bootstrap confidence intervals.
  3. Ranking/abstention: risk-coverage curve and AURC. Report "error rate at 80% / 90% coverage" and the share of items sent to review at the chosen thresholds.
  4. Disagreement-aware: split all metrics into consensus items (reference LLMs agree) and contested items (the 1,574). Expect, and check, lower confidence on contested items. Report the inter-LLM agreement ceiling.
  5. Statistics: 5-fold document-grouped cross-validation. Use a document-level bootstrap (≥1,000 resamples) for 95% confidence intervals on every number. State n.
- Model-card section "Confidence & uncertainty" should state:
  - what the score means ("calibrated probability that this extracted span matches the reference LLM's extraction", not "probability that it is true")
  - the calibration method and the data it was fit on (n docs, languages DE/EN split)
  - Brier/ECE with confidence intervals
  - a reliability diagram
  - a risk-coverage curve
  - recommended thresholds (accept / review / reject) with expected error and review rate
  - known failure modes (domain shift, contested categories)
  - that labels are LLM-generated and the reference LLMs disagree on a stated share of items
  - per-language breakdown, since calibration may differ between German and English (not verified for this model)

### Gaps
- I found no standard definition of "span-level ECE" in the sources gathered. The entity-as-binary-event framing (Jagannatha & Yu) is the closest precedent.
- netcal / TorchUncertainty / MAPIE / crepes API details were not verified in this session. Check current versions before recommending specific function calls.
