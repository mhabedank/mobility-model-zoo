# Part A: Open CAN IDS models and code (competitive landscape)

Research date: 2026-10-09. Scope: CAN intrusion detection systems that are public as code and/or weights.
Marks: **[V]** = I opened the source (repo README/code, paper PDF, HF card, Zenodo record) and the claim is there.
**[U]** = only from a search snippet, abstract or secondary source, not checked in the primary text.
Stars, licence and last push come from the GitHub API on 2026-10-09 [V]. "none" licence = no licence file,
which legally means all rights reserved: we may run it for comparison but not copy code into our repo.

Our reference point: RF in C via emlearn (13 streaming timing/payload features per frame + alarm stage) and an
int8 MLP on 32 per-frame features; benchmark = can-train-and-test (4 vehicles, known/unknown vehicle x attack test
subsets) and ROAD.

Note on "Papers with Code": the site is no longer an independent index (redirects to Hugging Face since 2025),
so it was not used as a source. Kaggle was searched through its API (see section 4).

---

## 1. Overview table (identity)

| # | Name | Link | Code / weights licence | Last push | Stars | Paper |
|---|---|---|---|---|---|---|
| 1 | CANShield | https://github.com/shahriar0651/CANShield | none | 2025-06-19 | 26 | Shahriar et al., IEEE IoT-J 2023, arXiv 2205.01306 |
| 2 | Time-based CAN IDS benchmark (Mean, Binning, Gaussian, KDE) | https://github.com/pmoriano/can-time-based-ids-benchmark | GPL-3.0 | 2022-01-18 | 10 | Blevins et al., AutoSec 2021, arXiv 2101.05781 |
| 3 | Unsupervised online masquerade benchmark (4 non-DL detectors) | https://github.com/pmoriano/benchmarking-unsupervised-online-IDS-masquerade-attacks | MIT | 2024-08-23 | 3 | Moriano et al., arXiv 2406.13778 (v3 2025) |
| 4 | CAN-IDSs-on-the-ROAD (LSTM, DCNN; paper also RF, LightGBM, LCCDE, TAN) | https://github.com/lorenzo9uerra/CAN-IDSs-on-the-ROAD | MIT | 2026-09-30 | 11 | Guerra et al., CSCS @ ACM CCS 2024, arXiv 2408.17235 |
| 5 | KD-GAT (graph attention teacher + distilled student) | https://github.com/OSU-CAR-MSL/KD-GAT ; card https://huggingface.co/SidraBhatti/kd-gat-can-intrusion-detection | MIT | 2025-05-11 | 2 | Frenken et al., arXiv 2507.19686 (2025) |
| 6 | BusRecall (cross-vehicle forgetting, replication package) | https://zenodo.org/records/22228087 | MIT | 2026-09-01 | n/a (Zenodo, 4 downloads) | Kutlu, Bekar, Ağca, Bingöl, "Measuring source-vehicle forgetting in cross-vehicle CAN intrusion detection" (venue not stated) |
| 7 | CANguard / PIRD (per-ID residual + Isolation Forest) | https://github.com/ChandanHegde07/CANguard | Apache-2.0 | 2026-10-07 | 2 | arXiv 2608.05548 (preprint, 2026) |
| 8 | IDS-ML: Tree-based IDS, MTH-IDS, LCCDE | https://github.com/Western-OC2-Lab/Intrusion-Detection-System-Using-Machine-Learning | MIT | 2026-04-01 | 598 | Yang et al., GLOBECOM 2019; MTH-IDS IEEE IoT-J 9(1) 2022 (arXiv 2105.13289); LCCDE GLOBECOM 2022 (arXiv 2208.03399) |
| 9 | CNN + transfer learning IDS | https://github.com/Western-OC2-Lab/Intrusion-Detection-System-Using-CNN-and-Transfer-Learning | MIT | 2026-04-20 | 205 | Yang & Shami, IEEE ICC 2022, arXiv 2201.11812 |
| 10 | CAAE (semi-supervised convolutional adversarial autoencoder) | https://github.com/htn274/CanBus-IDS | none | 2022-09-14 | 47 | Hoang & Kim, Vehicular Communications 2022, arXiv 2204.01193 |
| 11 | ACGAN + OOD (known and unknown attacks) | https://github.com/evenchen6/CAN_GAN_Anomaly | none | 2025-10-02 | 20 | Zhao et al., ACM TECS 21(4) 2022 (PDF https://par.nsf.gov/servlets/purl/10388880) |
| 12 | CAN-AE-Transformer-IDS | https://github.com/d41sys/CAN-AE-Transformer-IDS | none | 2025-04-17 | 43 | Le et al., Knowledge-Based Systems 299:112091, 2024 |
| 13 | StatGraph (multi-view statistical graph + GCN) | https://github.com/wangkai-tech23/StatGraph | none | 2025-11-22 | 15 | Wang et al., arXiv 2311.07056 |
| 14 | LiPar (lightweight parallel CNN on frame images) | https://github.com/wangkai-tech23/LiPar | none | 2025-11-22 | 27 | Wang et al., arXiv 2311.08000 |
| 15 | Ensemble-IDS (GRU + "Latent AE") | https://github.com/sampathrajapaksha/Ensemble-IDS | none | 2023-10-03 | 13 | Rajapaksha et al., JISA 2023 ("Beyond vanilla") |
| 16 | CANival (time-interval likelihood + revised CANet) | https://github.com/trifle19/CANival | MIT | 2025-03-20 | 7 | Vehicular Communications 50, 2024 |
| 17 | X-CANIDS re-implementation | https://github.com/freundma/can-ids | GPL-3.0 | 2024-02-28 | 3 | original: Jeong et al., IEEE TVT 2024, arXiv 2303.12278 |
| 18 | CANTXSec (deterministic IDPS on STM32) | https://github.com/donadelden/CANTXSec | none | 2025-05-30 | 7 | Donadel et al., ACNS 2025, arXiv 2505.09384 |
| 19 | ai_can_anomaly_detection (J1939 truck, NUCLEO-H533RE) | https://github.com/asana17/ai_can_anomaly_detection ; data/runs on HF | MIT (code), CC-BY-4.0 (data) | 2026-09-30 | 0 | none (slides only) |
| 20 | CAN-Bus-IDS-STM32 (int8 MLP, STM32F446) | https://github.com/laithalarmouti/CAN-Bus-IDS-STM32 | NOASSERTION (badge says MIT) | 2026-04-05 | 0 | none |
| 21 | stm32H7-edge-ai-can-ids (XGBoost -> C via m2cgen) | https://github.com/AzizHrz/stm32H7-edge-ai-can-ids | none | 2026-08-28 | 0 | none |
| 22 | TinyML IDS for EVs (TFLite MLP on ESP32) | https://github.com/exorev07/TinyML-IDS | MIT | 2026-09-06 | 1 | none (README links a "related publication") |
| 23 | CAN-Bus-Supervised-IDS-STM32-EmbeddedML (1D CNN, X-CUBE-AI) | https://github.com/CPQE/CAN-Bus-Supervised-IDS-STM32-EmbeddedML | none | 2026-03-05 | 0 | none |
| 24 | can-train-and-test reference benchmark (18 scikit-learn IDS) | https://bitbucket.org/brooke-lampe/can-benchmark/src/master/ | not checked [U] | n/a | n/a | Lampe & Meng, Computers & Security 140 (2024) 103777, arXiv 2308.04972 |
| 25 | TinyCNNCANNet (13K-parameter CNN) | data only: https://huggingface.co/datasets/Thi-Thu-Huong/Multi-CAN-Datasets ; no code repo found | apache-2.0 claimed on the dataset repo | 2026-06-02 | n/a | Le et al., IEEE Access 14:14870, 2026 |

---

## 2. Technical comparison

Abbreviations: CH = HCRL Car-Hacking; ctt = can-train-and-test; sup = needs attack labels; unsup = benign-only training.

| # | Input granularity and features | Model, size, quantised? | Data and evaluation protocol | Reported metrics (exact names, split) | Latency / hardware | Labels and training data | Verdict as baseline on our benchmark |
|---|---|---|---|---|---|---|---|
| 1 CANShield | Signal level: decoded signals in a data queue, window w = 50, three views with sampling periods 1, 5, 10 (multi-scale "images" of signals) [V] | 3 convolutional autoencoders + ensemble; params not stated; TFLite conversion "quantizes the weights" with no detection loss [V] | SynCAN and ROAD (signal-translated, 7 primary signals); trained on normal traces, tested on attack traces [V] | SynCAN: AUROC avg 0.952 (CANShield-Ens), per attack 0.870 (continuous) to 0.997 (flooding); TPR/FPR e.g. flooding 0.988/0.009 [V]. ROAD: "AUROC score of ~1.00"; AUPRC per attack 0.99 (max coolant) to 1.0 (speedometer, correlated, reverse light on), 0.997 reverse light off; "perfect precision, recall, and F1" at a tuned threshold [V] | ~1 ms per process on i9 laptop, ~10 ms on Raspberry Pi (1.5 GHz quad core) [V] | unsup (benign only) [V] | **Yes, on ROAD only** (needs decoded signals; ctt has no DBC). Strongest open masquerade reference. Not MCU-sized. |
| 2 Time-based benchmark | Per frame, inter-arrival time per arbitration ID; Binning counts messages per window [V] | Statistical rules per ID (Mean, Binning, Gaussian, KDE); tiny [V] | ROAD: train on 10 ambient dyno logs, test on all fabrication attack logs (1,588,263 msgs, 61,516 attacks) [V] | AUC-PR: Binning 87.63 %, Mean 68.90 %, Gaussian 0.00 %, KDE 0.02 % (with outliers) [V]; best F1 Binning 0.990, Mean 0.986 at thresholds chosen on test data [V] | Binning ran on Raspberry Pi 3B+ OBD-II plug-in [V] | unsup [V] | **Yes, mandatory trivial baseline** on both datasets. Paper itself computes "~1,821 alerts per minute" at 98.6 % precision [V]: exactly the gap our alarm stage targets. No masquerade coverage (stated by authors) [V]. |
| 3 Masquerade online benchmark | Signal time series in sliding windows (ω 50–400, offset δ) ; correlation / distribution / clustering of signals [V] | Matrix Correlation Distribution, Matrix Correlation Correlation, Ganesan17, Moriano22 (hierarchical clustering); non-DL [V] | ROAD masquerade attacks, online sliding-window evaluation [V] | AUC-ROC heatmaps; mostly 0.3–0.77; best Moriano22 0.89 on correlated-signal attack [V] | best method has "higher computational overhead" (abstract) [V] | unsup [V] | **Yes on ROAD masquerade.** Useful as an honest lower bar: shows masquerade is hard without DL. |
| 4 CAN-IDSs-on-the-ROAD | Per frame: ID + 8 payload bytes (DLC missing in ROAD); DCNN 29-frame window; TAN/LSTM sequences [V] | RF, LightGBM, LCCDE, LSTM, DCNN (Inception-ResNet-based, 18 % of original params), DCNNv2, TAN [V] | ROAD raw, CH, IVN challenge; **random 80/20 split**, SMOTE to 100,000 samples per attack [V] | ROAD multiclass F1: RF/LightGBM/LCCDE mostly 0.0–0.68 on masquerade/fabrication [V]; ROAD binary F1: LSTM 1.0000 on every attack, TAN 0.0194–0.9976 [V] | not reported for inference | sup [V] | **Yes, after replacing the split** with per-capture/temporal. The LSTM F1 = 1.0 under a random split is a red flag for leakage, worth reproducing under our protocol. |
| 5 KD-GAT | Window -> graph: nodes = CAN IDs, node features = mean payload + count (10-dim), edges = sequential co-occurrence [V] | GAT teacher 4,999,426 params; student 316,034 params; float, PyTorch Geometric [V] | CH, HCRL Car-Survival, **ctt sets 01–04 with the provided held-out test** [V] | Test F1 (student): CH 0.9997, Car-Survival 0.9929, ctt Set01 0.8808, Set02 0.2442, Set03 0.8606, Set04 0.6135 [V] | not reported | sup, focal loss for imbalance 36:1 to 927:1 [V] | **Yes, the only DL with full ctt results.** Directly beatable on ctt Set02/Set04 and on size (316k params vs our KB-sized models). |
| 6 BusRecall | Non-overlapping 100-frame windows; "vocab" features (ID histogram) vs "portable" timing/distribution features; also raw ID sequences [V] | Small NN, continual-learning variants (LwF, replay buffer) [V] | ctt v1.5 four-vehicle orders and ROAD attack families; temporal contiguous train/val blocks; separate selection vs reporting halves [V] | Zero-shot: within-vehicle AUROC mean 0.949, F1 mean 0.863; **cross-vehicle AUROC mean 0.538, F1 mean 0.042** (32 cells) [V] | not reported | sup [V] | **Yes, as protocol and number to beat for cross-vehicle.** Also found that 656 of 1,077 rows of the published ctt baseline use weighted metrics [V]. |
| 7 CANguard / PIRD | Per-ID sliding windows, 14 behavioural features (IAT, DLC, payload), per-ID z-score residuals [V] | Isolation Forest, 200 trees [V] | CH temporal 40/20/40 split; ROAD per-capture split with calibration on pre-injection normals; cross-condition transfer and a single global threshold [V] | ROAD per capture F1: correlated_signal 0.898, fuzzing 0.273, max_speedometer 0.698 (FPR 0.020–0.053) [V]; CH DoS F1 0.017 [V]; also reports Recall@FPR, FPR@recall, false alarms per hour [V] | peak memory ~525 MB (window table) [V] | unsup [V] | **Yes.** Closest in philosophy (streaming per-ID features, deployment metrics, honest protocol). Weak on DoS and cross-ID fuzzing, not MCU-ready. |
| 8 MTH-IDS / LCCDE | Per frame: CAN ID + payload bytes [U]; KPCA/feature selection [V] | DT, RF, ET, XGBoost, stacking + CL-k-means anomaly tier (MTH-IDS); LightGBM/XGBoost/CatBoost ensemble (LCCDE) [V] | CH ("CAN-intrusion-dataset") and CICIDS2017; **70/30 hold-out + 10-fold CV**, no per-capture split [V] | MTH-IDS: accuracy 99.99 % on CH, F1 0.963 on unknown attacks (abstract) [V] | < 0.6 ms per packet on Raspberry Pi 3 [V] | sup (+ unsup tier) [V] | **Yes, as the popular supervised tree baseline** (598 stars). Guerra et al. show LCCDE collapsing on ROAD (F1 0.0–0.68) [V]. |
| 9 CNN transfer learning | Frames converted to images [V] | VGG16/19, Xception, Inception, ResNet, InceptionResNet + ensembles, PSO tuning [V] | CH and CICIDS2017 [V]; split not checked [U] | "over 99.25 % detection rates and F1-scores" [V] | not checked | sup [V] | **No.** ImageNet-scale backbones; irrelevant for MCU, only as "big model" contrast. |
| 10 CAAE | 29 consecutive CAN IDs as 29x29 bit image (ID only, no payload) [V] | Conv. adversarial autoencoder, 2.15 M params (total incl. decoder/discriminators) [V] | CH; normal frames 70/15/15 split, attack share 10–70 %, labels for 10 % [V] | F1 0.9984, error rate 0.1 % with 40 % labelled frames; unknown attacks F1 ≈ 0.98 [V] | 0.63 ms GPU, 0.69 ms CPU per frame (i7-7700, GTX 1060) [V] | semi-sup (~60k labels) [V] | **Maybe.** ID-only input runs on ctt, but TF 1.15 and CH-only tuning. |
| 11 ACGAN + OOD | 48 CAN IDs as 48x48 image [V] | ACGAN classifier + real/fake classifier; 104,518 params = 418.1 KB fp32 / 104.5 KB int8 [V] | CH, balanced 40,000 train / 25,000 test images, one attack held out as "unknown" [V] | macro F1; e.g. GEAR F1 99.53 %; CNN baseline 70.65 % on unknown DoS [V] | 0.538 ms single core, 0.203 ms multicore, Raspberry Pi 4 (Cortex-A72), TVM-compiled C [V]; pretrained `pkl` params shipped [V] | sup + OOD [V] | **Maybe.** Small enough to be a fair NN comparison; ID-only. |
| 12 CAN-AE-Transformer-IDS | Windows of 29 (CH) / 15 (ROAD) frames, time-embedded transformer + AE [V] | size not checked [U] | CH, ROAD fabrication, ROAD masquerade; **shuffled windows, 80/20** (trainTestSplit.py) [V] | not verified [U] | not checked | sup (multiclass) [V] | **Maybe** on ROAD; needs re-split. |
| 13 StatGraph | Timing correlation graphs + coupling relationship graphs per window, GCN; per-message labels ("1/1") [V] | GCN, 4 layers (CH) / 1 layer (ROAD), 32 hidden units [V] | CH and ROAD; split not found in text [U] | ROAD F1: correlated-signal masquerade 0.9960, max speedometer masquerade 0.9622, reverse light off/on 0.9332/0.9338; CH mixing fabrication F1 0.9403 [V] | evaluated on Jetson Nano / Jetson Orin platforms [V] | sup [V] | **Maybe.** Strong ROAD masquerade claims; reproduce under per-capture split. |
| 14 LiPar | Frames -> RGB images [V] | Parallel lightweight CNN; branch sizes < 0.5 MB, smallest branch 0.06 MB [V] | CH only; **random 7:2:1 image split** [V] | STParNet accuracy 0.9998, AUC 1.00000 [V] | throughput only (items/s) [V] | sup [V] | **No.** CH-only, random split, image pipeline. |
| 15 Ensemble-IDS | GRU on ID sequences + "Latent AE" on payload with Cramér's-V feature selection [V] | size not checked | ROAD + one other public dataset, 13 attacks incl. masquerade [U] | not verified; "near real-time detection latency of 25 ms" [U] | 25 ms [U] | unsup [U] | **Maybe** on ROAD (masquerade). |
| 16 CANival | Time-interval likelihood + signal-based revised CANet [V] | TensorFlow; "more than 1 day" training on Ryzen 7 / 64 GB [V] | X-CANIDS dataset and SynCAN [V] | TPR 0.960 / 0.912, TNR 0.997 / 0.996 (X-CANIDS / SynCAN) [U] | not checked | unsup [U] | **No.** Needs signal datasets we do not use. |
| 17 X-CANIDS (re-impl.) | Decoded signals, time-series windows (t = 0.01 s, w = 200) [V] | BiLSTM autoencoder [V] | Re-impl. targets SynCAN and ROAD signals; original: own Hyundai data [V] | original: not verified [U] | original: deterministic detection latency 38.25–73.25 ms on Jetson AGX Xavier [V] | unsup [V] | **Maybe** on ROAD signals; GPL-3.0. |
| 18 CANTXSec | Physical ECU activation (transmit) lines, not traffic statistics [V] | Deterministic logic on STM32 Nucleo H743ZI2 [V] | Own physical testbed [V] | 100 % detection, 100 % prevention of frame injection attacks [V] | real time on STM32 [V] | none (no ML) [V] | **No** (needs extra wiring). Relevant as the "zero false positive" non-ML competitor. |
| 19 ai_can_anomaly_detection | 17 decoded J1939 signals on a 100 ms grid; row AE + window AE + rules [V] | AEs exported to ONNX, int8-quantised, C code generated for NUCLEO-H533RE under μT-Kernel [V] | Univ. Turku Renault truck logs, benign only; synthetic anomalies (bias ramps, replays); folds 0–3 [V] | Detected events per attack and false alarms per hour; targets 1.5/h (rows) + 0.5/h (windows); measured 2.0–3.4/h on test logs [V] | runs on board, priority-scheduled tasks [V] | unsup [V] | **No** for our datasets (J1939 signals, synthetic attacks), but a **direct design peer**: MCU + int8 + FP/h budgets + evidence storage. |
| 20 CAN-Bus-IDS-STM32 | Per frame, 11 features: ID, DLC, 8 bytes, inter-arrival time [V] | MLP 3,013 params, 11.77 KB fp32, full int8 8.06 KB, 2.62 KB RAM, X-CUBE-AI [V] | CH, balanced to 491,847 frames per class; split type not stated [U] | "Overall accuracy: 99.92 %" [V] | "sub-millisecond" (claim) [V] | sup [V] | **Embedded peer, weak as baseline**: same size class as our MLP, but only accuracy on CH. Easy to retrain on ctt. |
| 21 stm32H7-edge-ai-can-ids | Per frame, 12 features: CAN_ID, IAT_ID, entropy, rate_50ms, Data0–7 [V] | XGBoost 100 trees depth 4, 5 classes, exported to C with m2cgen; ~256 KB code, ~33 % of 1 MB flash (-O0) [V] | CH [V]; split not checked [U] | classification reports only (not checked) [U] | "order of 10–50 µs per frame (estimated)" [V] | sup [V] | **Embedded peer for our RF-in-C path.** Not a quality baseline. |
| 22 TinyML IDS (ESP32) | Per frame, 10 features: ID, DLC, 8 bytes (no timing) [V] | TFLite MLP 48.68 KB, 30 KB tensor arena [V] | OTIDS, **80/20 stratified random split** [V] | 87.05 % test accuracy (MLP), 90.79 % for a 2.61 MB comparison model [V] | on ESP32 (not quantified) | sup [V] | **No.** Weak, but shows the typical hobby/student embedded baseline. |
| 23 CAN-Bus-Supervised-IDS-STM32 | ROAD extracted signals resampled to 200 Hz [V] | 1D CNN, X-CUBE-AI on STM32H723ZG [V] | ROAD (also tried OTIDS, SynCAN) [V] | not verified [U] | on STM32H723 (not quantified) | sup [V] | **No** (no metrics, no licence). Shows others try ROAD on STM32. |
| 24 can-benchmark (ctt reference) | Per frame: timestamp, arbitration ID, data field [V] | 18 scikit-learn models (NB, KNN, LR, SVMs, DT, ET, GB, IF, RF, k-means, BIRCH, LOF, MLP, RBM) [V] | ctt sub-datasets with the four test subsets [V] | Accuracy, Precision, Recall (TPR), F1; e.g. set 01/test 01: RF F1 0.0015, LR 0.9878, IF 0.9812, MLP 0.9811 [V]. Many rows are weighted averages (recall equals accuracy) [V], confirmed by BusRecall [V] | training/testing time in ns [V] | both [V] | **Yes, but recompute.** Use positive-class F1 / AUC-PR; the published numbers are not comparable as printed. |
| 25 TinyCNNCANNet | CNN on CAN frames (details in paper) [U] | 13K params, 0.04 MB [V card] | CAN-FD (2021), CICIoV 2024, Multi-Fuzzer-CAN, "SynCAN 2025" [V card] | "100 % accuracy" on SynCAN OOD vs EfficientCANNet 86.82 % [V card] | 0.16–0.51 ms inference (hardware not stated on card) [V card] | sup [U] | **No code found.** Only the data repo (which re-licenses third-party datasets as Apache-2.0). |

### Also seen, not ranked (older, incomplete or off-target)
- CAN-ADF (Tariq et al., Comput. & Security 2020), MIT, last push 2020: https://github.com/shahroztariq/CAN-ADF [V]; CANTransfer (SAC 2020), MIT: https://github.com/shahroztariq/CANTransfer [V].
- GIDS re-implementation (only the image conversion step is published): https://github.com/EunSeong-Seo/GIDS-GAN_based_Intrusion_Detection_System_for_In-Vehicle_Network [V].
- KG-ID knowledge-graph IDS with a C detection module (DBC-based, rule-like, auditable): https://github.com/jingzhuwang/KG-ID, no licence [V].
- LSF-IDS (BERT -> DNN distillation), code without README: https://github.com/Zhou-CyberSecurity-AI/CAN-BERTtoDNN [V].
- CanBERT+ (OSU SecLab, 2026, no licence): https://github.com/OSUSecLab/CanBERTplus [V].
- LRAE low-rank autoencoder on SynCAN (WINCOM 2025): https://github.com/nadiml/LowRankAutoencoder_CAN_Bus_Intrusion_Detection [V].
- GB-IDS (graph analysis, ICCC 2023): https://github.com/faiimea/GB-IDS [V]; CF-AIDS GRU + Gabor (IEEE Access 2023), MIT: https://github.com/Arupreza/CF-AIDS-Comprehensive-Frequency-Agnostic-Intrusion-Detection-System-on-In-Vehicle-Network [V].
- can-sleuth (Kidmose et al.): no public code repository found on GitHub [V for the search, U for absence].
- Koltai et al. cross-dataset benchmark framework (arXiv 2606.30430, ACSW'26): no code link on the arXiv page [V].

---

## 3. Hugging Face Hub (searched 2026-10-09 via the Hub API)

Queries: "CAN bus", can-bus, canbus, car-hacking, carhacking, hcrl, can-ids, canids, intrusion, can-intrusion,
in-vehicle, automotive, vehicle-ids, automotive-ids, otids, ciciov, can-fd (models, datasets, spaces). Result: the Hub has
almost nothing for CAN IDS. Everything relevant:

| Repo | Type | Downloads (last 30 d, API) | Likes | Licence | Content | Mark |
|---|---|---|---|---|---|---|
| asana17/ai_can_anomaly_detection_data | dataset | 5,355 | 0 | CC-BY-4.0 | J1939 truck signal grid (benign), train/calibration/test rows | [V] |
| asana17/ai_can_anomaly_detection_runs | model (ONNX, int8, generated C) | 0 | 1 | MIT | runs, thresholds, quantised models, board code | [V] |
| SidraBhatti/kd-gat-can-intrusion-detection | model card only (no weights) | 0 | 0 | MIT | points to OSU-CAR-MSL/KD-GAT | [V] |
| anddali/vehicle-ids-anomaly-detector | model (sklearn pickle, 1.57 GB) | 0 | 0 | Apache-2.0 | MTH-IDS-style stacking + Isolation Forest on CH; Tier 1 accuracy 0.9586, Tier 2 accuracy 0.6103 | [V] |
| anddali/vehicle-ids-tracker | space (Gradio) | n/a | 0 | n/a | demo of the above | [V] |
| nitin540/canids | model (ViT, 343 MB safetensors, no card) | 4 | 0 | none | unknown training data | [V] |
| nitin540/canids2 | model | 0 | 0 | none | empty-ish | [V] |
| Muggle-ZzzH/CAN304-IDS | model (empty folders, no card) | 0 | 0 | none | placeholder | [V] |
| Thi-Thu-Huong/Multi-CAN-Datasets | dataset | 15 | 0 | apache-2.0 (claimed) | CAN-FD2021, CICIoV2024, Multi-FuzzerCAN, SynCAN2025 for TinyCNNCANNet | [V] |
| emgena/emgena_robotics_can_bus_telemetry_guard_mcp_teaser | dataset | 93 | 0 | apache-2.0 | commercial robotics bus-load teaser, not IDS | [V] |

No ROAD, can-train-and-test or Car-Hacking mirror and no trained CAN IDS with a proper card exists on the Hub
(false positives like `tgerm/test_can_dataset` are robot "can" episodes) [V]. **Implication:** a well-documented,
licensed, small CAN IDS model with a model card and honest protocol would be the first credible entry on the Hub.

## 4. Kaggle and Zenodo (for completeness)

- Kaggle API search: only re-uploads of datasets, e.g. `pranavjha24/car-hacking-dataset` (3,143 downloads, labelled MIT,
  which is not the original licence), `bikashkundu/can-hcrl-otids` (727), `pushpakattarde/ciciov2024decimalcsv` (969).
  No CAN IDS model in Kaggle Models for "CAN intrusion" [V].
- Zenodo: BusRecall (#6), GEM-CAN dataset (GEM e6 autonomous vehicle, ~143K frames, CC-BY-NC-3.0, 383 downloads,
  https://zenodo.org/records/19161139) [V], ROAD (https://zenodo.org/records/10462796, already in our notes).

---

## 5. Cross-cutting findings that matter for our USP

1. **Protocol is the weak spot everywhere.** Most open repos use random frame/window splits (#4, #8, #12, #14, #22) or Car-Hacking
   only (#8–#11, #14, #20–#22). Those that use per-capture or cross-vehicle splits (#6, #7, KD-GAT on ctt #5) report
   large drops: KD-GAT test F1 0.24 on ctt Set02, BusRecall cross-vehicle AUROC 0.538 [V].
2. **Nobody reports alarm-level false-positive rates on ctt/ROAD with an MCU model.** Blevins et al. compute ~1,821
   alerts/min for their best timing detector [V]; CANguard reports FP/h but is a 525 MB Python pipeline [V];
   asana17 reports FP/h on an MCU but on J1939 signals with synthetic anomalies [V].
3. **Embedded peers exist but are weak on evidence.** #20 (int8 MLP, 8.06 KB, STM32F446) and #21 (XGBoost to C via
   m2cgen, STM32H7) are architecturally almost identical to our two models, but only show Car-Hacking accuracy [V].
4. **Masquerade needs signals.** The strong ROAD masquerade results (CANShield, StatGraph) use decoded signals or
   graphs and are not MCU-sized; pure timing detectors fail by design (Blevins, Moriano) [V].
5. **Licences:** of the 25, only #2, #3, #4, #5, #6, #7, #8, #9, #16, #17, #19, #22 carry an OSI licence; the much-cited
   CANShield, CAAE, ACGAN, StatGraph, LiPar and CAN-AE-Transformer have none [V].
6. **Published ctt baseline numbers need recomputing** (weighted vs positive-class metrics) [V].

---

## 6. Summary: the 5 strongest open competitors

| Rank | Competitor | Good at | Bad at |
|---|---|---|---|
| 1 | **CANShield** (#1) | Best open signal-level masquerade detector; AUROC 0.952 avg on SynCAN, ~1.00 on ROAD; benign-only training; TFLite-quantised | Needs decoded signals (no ctt), 3 CNN autoencoders, ~10 ms on a Raspberry Pi, no licence, no false-alarm-rate reporting |
| 2 | **KD-GAT** (#5) | Only DL model with results on the full can-train-and-test; 316k-param distilled student; MIT | Supervised; collapses on unseen vehicle/attack sets (test F1 0.24 Set02, 0.61 Set04); GNN stack (PyG), not MCU-deployable |
| 3 | **Time-based benchmark** (#2, ORNL) | Unsupervised, tiny, ran on a Pi OBD plug-in; Binning F1 0.990 / AUC-PR 87.6 % on ROAD fabrication | Thresholds tuned on test; ~1,821 alerts/min at its best point; blind to masquerade; GPL-3.0 |
| 4 | **CANguard / PIRD** (#7) | Benign-only per-ID streaming features, honest per-capture ROAD protocol, cross-condition tests, FP/h and Recall@FPR | Fails DoS (F1 0.017) and cross-ID fuzzing (ROAD F1 0.27); Python pipeline with ~525 MB peak memory; preprint |
| 5 | **MTH-IDS / LCCDE** (#8, 598 stars) | De facto supervised tree baseline; < 0.6 ms per packet on a Raspberry Pi 3; MIT | 99.99 % accuracy only on Car-Hacking with a 70/30 split; LCCDE F1 drops to 0.0–0.68 on ROAD (Guerra et al.); not MCU-sized as stacked ensemble |

**Where a real USP is open:** an MCU-sized (KB), licensed, documented model that is evaluated on can-train-and-test
with unseen-vehicle/unseen-attack subsets and on ROAD per capture, and that reports false alarms per hour after an
alarm stage, plus on-device latency. None of the 25 open systems covers all of these; the embedded peers (#20, #21) cover
size but not evaluation, and the strong evaluators (#5, #6, #7) cover evaluation but not size or FP/h on MCU.
