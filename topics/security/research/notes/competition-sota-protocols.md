# Part B: State of the art, evaluation protocols and USP options for `can-ids-v1`

Date: 2026-10-09. Scope: published numbers on can-train-and-test (CT&T) and ROAD, cross-dataset and realistic-evaluation studies, data efficiency for new vehicles, an honest comparison with our pre-zoo results, and a proposal for the headline metrics, USP and baselines of `can-ids-v1`.

**Tags.** [V] = verified in the opened source (full text or official abstract, as stated). [U] = snippet, abstract-only where the claim needs full text, or secondary source. [D] = derived by us from numbers printed in a source (e.g. attack-class F1 recomputed from printed TP/FP/FN counts). [O] = our own pre-zoo numbers from the repository (not benchmark results). Numbers are quoted as printed; nothing is extrapolated unless marked as a calculation.

---

## 0. Corrections to existing notes

The repo notes (`research/02-literature.md`, `research/notes/threats-and-papers.md`) contain some errors. Fix them before anything is cited.

| Existing note says | Correct | Tag |
|---|---|---|
| can-sleuth = arXiv 2408.17235 | arXiv 2408.17235 is Guerra et al., "AI-Driven IDS on the ROAD Dataset" (doi 10.1145/3689936.3694696). can-sleuth has a conference version at EICC 2024 (doi 10.1145/3655693.3655696) and a journal version in IJIS 24(5), 2025 (doi 10.1007/s10207-025-01038-8). The author manuscript is at https://eprints.lancs.ac.uk/id/eprint/232827/. | [V] |
| can-train-and-test: "later journal version; venue not confirmed" | Computers & Security 140 (2024) 103777, doi 10.1016/j.cose.2024.103777. Its abstract matches arXiv 2308.04972; the tables were not compared because of a ScienceDirect 403. There is also a short VTC2023-Fall version, doi 10.1109/VTC2023-Fall60731.2023.10333756. | [V] abstract / [U] tables |
| CT&T on GitHub | The data is on Bitbucket (`brooke-lampe/can-train-and-test`, `-v1.5`, `can-benchmark`) and on DTU Data (doi 10.11583/DTU.24805533). The GitHub repo returns 404. | [V] |
| Koltai et al. "show large swings between datasets"; "cross-dataset" | Correct, but they always **train and test within the same dataset** and never transfer. They do **not** use CT&T. Venue: ACSW'26 workshop (EuroS&P workshops 2026). | [V] |
| Shortcut paper: "Elsevier 2026", ID lookup AUC 0.97–0.99, timing-only RF 0.995 | Heydari, Nyarko, Alam, *Array* 31 (2026) 101112, doi 10.1016/j.array.2026.101112 (CC BY). The ID-lookup AUC (0.970 on Car-Hacking, 0.986 on Survival) comes from a search snippet only. **The timing-only RF figure could not be verified** (full text returned 403). | [V] abstract / [U] numbers |
| Lazeski et al., 4 authors | 5 authors (+ Wiesmaier). VehicleSec '26 pp. 135–145. PDF: https://www.usenix.org/system/files/vehiclesec26-lazeski.pdf | [V] |
| CT&T author "Lampe" vs "Kidmose" | Probably the same person: later papers list Brooke Elizabeth Kidmose with the same DTU address. | [U] |

---

## 1. Published results

### 1.1 can-train-and-test (Lampe & Meng; arXiv 2308.04972; Computers & Security 140, 2024)

**Structure** [V]. Four sets. Each has `train_01` and four test splits: `test_01_known_vehicle_known_attack`, `test_02_unknown_vehicle_known_attack`, `test_03_known_vehicle_unknown_attack`, `test_04_unknown_vehicle_unknown_attack`. Frame columns: timestamp, arbitration_id, data_field, attack.

| Set | Known vehicle | Unknown vehicle | Train samples |
|---|---|---|---|
| set_01 | 2011 Chevrolet Impala | 2016 Chevrolet Silverado | 10,653,152 |
| set_02 | 2011 Chevrolet Traverse | 2017 Subaru Forester | 17,340,826 |
| set_03 | 2016 Chevrolet Silverado | 2017 Subaru Forester | 12,025,781 |
| set_04 | 2017 Subaru Forester | 2011 Chevrolet Traverse | 9,492,819 |

There are 9 attack types: DoS, double/triple combined spoofing, fuzzing, gear, interval, RPM (driving and accessory), speed (driving and accessory), standstill and systematic [V]. Version 1.5 splits training into `train_01_attack_free` and `train_02_with_attacks`. It adds `test_05_suppress` (unlabelled, because frames are deleted) and `test_06_masquerade` (timed and untimed) [V].

**Main pitfall: most published "F1" on CT&T is support-weighted F1.**

- In the original benchmark (18 scikit-learn models, per frame, default parameters), 10 of the 17 models with results report F1 values that **do not match attack-class F1** [D, recomputed from the printed TP/FP/FN].
- For those 10 models, recall equals accuracy, which is the signature of scikit-learn `average="weighted"`.
- BIRCH "wins" with F1 0.96–0.998 while TP = 0 in all 16 cells [D].
- can-sleuth confirms that it uses weighted P/R/F1 [V].
- The BusRecall replication code also notes the weighted column [V].

Averages over models as published (weighted) [V]:

- **Per test:** test_01 0.4983, test_02 0.4214, test_03 0.4581, test_04 0.4472.
- **Per set:** set_01 0.4562, set_02 0.4973, set_03 0.5293, set_04 0.5330.
- **Authors' conclusion:** an unknown vehicle hurts more than an unknown attack.

#### Table 1: Per-cell results on the official four-way splits (frame-level attack-class F1 unless noted)

| Set / split | Lampe & Meng best model, **attack-F1 recomputed** [D] | can-logic rules (Lampe & Meng, ACM IoT 2023), F1 [D] / FPR | **Ours, picket-forest, no CAN ID [O]** |
|---|---|---|---|
| set_01 / test_01 known-known | 0.444 (ExtraTrees, FPR 0.0008) | 0.684 / 0.0006 | 0.971 (FPR 0.00057) |
| set_01 / test_02 unk. vehicle | 0.131 (GB, FPR 0.35) | 0.082 / 0.58 | 0.994 (0.00017) |
| set_01 / test_03 unk. attack | 0.066 (IsolationForest) | 0.468 / 0.0001 | 0.650 (0.00018) |
| set_01 / test_04 unk.-unk. | 0.057 (GB) | 0.004 / 0.28 | 0.471 (0.00007) |
| set_02 / test_01 | 0.572 (RF) | 0.641 / 0.00004 | 0.871 (0.00011) |
| set_02 / test_02 | 0.046 (LogReg) | 0.004 / 0.99 | 0.895 (0.00027) |
| set_02 / test_03 | 0.023 (RF) | 0.544 | 0.967 (0.00015) |
| set_02 / test_04 | 0.027 (KNN) | 0.008 / 0.99 | 0.931 (0.00040) |
| set_03 / test_01 | 0.893 (DT, FPR 0.0004) | 0.800 / 0.0002 | 0.963 (0.00013) |
| set_03 / test_02 | 0.377 (MLP) | 0.044 / 0.75 | 0.824 (0.00243) |
| set_03 / test_03 | 0.025 (MiniBatch k-means) | 0.399 | 0.928 (0.00004) |
| set_03 / test_04 | 0.051 (k-means) | 0.053 / 0.75 | 0.949 (0.00032) |
| set_04 / test_01 | 0.623 (DT) | 0.803 / 0.0006 | 0.984 (0.00033) |
| set_04 / test_02 | 0.202 (GNB) | 0.006 / 0.995 | 0.733 (0.00189) |
| set_04 / test_03 | 0.440 (RF) | 0.537 | 0.931 (0.00228) |
| set_04 / test_04 | 0.211 (GNB) | 0.050 / 0.995 | 0.897 (0.00410) |

Notes on Table 1:

- **Lampe & Meng column** [D]: LinReg and LOF were excluded from the recomputation because their appendix rows look shuffled between sets. Examples: MLP attack-F1 is 0.255 on set_01/test_01 and 0.767 on set_03/test_01; LogReg's printed "0.9878" on set_01/test_01 is 0.398 attack-F1.
- **can-logic** [V source, D metrics]: three hand rules (interval too short, ID repeated three times, ID not on a whitelist). It collapses on unknown vehicles (FPR 0.28–0.995) **because of the ID whitelist**.

#### Table 2: Other published CT&T results

| Paper | Split used | Unit / metric | Model / size | Numbers | Tag |
|---|---|---|---|---|---|
| can-sleuth, EICC 2024 / IJIS 2025 | v1.5, all four test splits (+05/06) | frame, **weighted** F1, G-mean, FPR | 16 sklearn models, default parameters | Average over sets and tests (excl. test_05), Acc/F1/FPR: Bernoulli RBM 0.9904/0.9857/0.0000 (consistent with "all benign"); LogReg 0.9856/0.9825/0.0039; LinSVM 0.9866/0.9823/0.0023; MLP 0.9343/0.9555/0.0576; RF F1 0.9313; GB 0.8683. MLP on set_01, weighted F1: test_01 0.9866, test_02 0.9609, test_03 0.9965, test_04 0.9981. MLP known vs unknown vehicle on subset 2: 0.9988/0.8904 vs 0.8774/0.8512. Std of F1 across models on CT&T: 0.2392 | [V] |
| KD-GAT, Frenken et al., ITSC 2025 (arXiv 2507.19686) | v1.5, "test set compiled by the providers" (treated as test_01) | 50-frame windows, window is attack if any frame is | GAT teacher 4,999,426 params, student 316,034 | Student Acc/P/R/F1: set_01 .9929/.9993/.7874/.8808; set_02 .9818/.2034/.3055/.2442; set_03 .9824/1.0/.7554/.8606; set_04 .8707/1.0/.4425/.6135 | [V] |
| VGAE+GAT distillation, Frenken et al. (arXiv 2508.04845) | v1.5, test_01 only | 100-frame graph windows, Acc/F1 % | AE 184K/87K, classifier 3.56M/55K params (teacher/student) | set_01 99.38/89.86; set_02 99.61/79.67; set_03 99.29/95.10; set_04 96.47/91.99 | [V] |
| BusRecall replication (Kutlu et al., Zenodo 10.5281/zenodo.21889099, .22228087; no paper found) | v1.5 official splits | 100-frame windows, attack-F1 | RF, 200 trees | test_01: set_01 0.976, set_02 0.653, set_03 0.954. set_01/test_02 0.944, set_01/test_03 0.156, set_02/test_02 0.046. **Cross-vehicle mean F1 0.042 (AUROC 0.538) vs 0.863 within vehicle** | [V] (code inspected) |
| ECF-IDS, Li et al., IEEE TNSM 2024 | **Random 70/30** after deduplication, not the official splits | frame | Cuckoo filter + BERT | set_03 "all data" F1 99.86%. Its baselines are copied from Lampe & Meng test_01, so the comparison is not like for like | [V] |
| KDBC (IEEE TIFS 2025) | set_03, random 70/30 | frame, F1 with **normal as the positive class** | BERT → CNN-BiLSTM, 264,833 params | F1 0.9978 | [V] |
| E-UniCon (KBS 2025) | random 10% sample, 7:3 split | 64-frame windows, 10 classes | EfficientNet-Lite0, 2.54M params | Forester F1 0.9866 | [V] |
| can-fp, Kidmose & Meng, PST 2024 | ? | FPR study | – | no numbers obtained (paywall) | [U] |
| Lazeski et al., VehicleSec 2026 | per-attack trees | frame | decision trees | fuzzing F1 0.937 on CT&T; trees use the interval first and sometimes absolute timestamps | [V] |

**Bottom line for CT&T.**

1. On the official unknown-vehicle splits (test_02, test_04), every published method we found reaches **attack-F1 ≤ 0.38** at frame level [D], or a **cross-vehicle mean F1 of 0.042** at window level (BusRecall) [V].
2. The near-perfect numbers (≥ 0.99) come from weighted F1, random splits, or test_01 only.
3. Nobody reports event-level metrics, false alarms per hour, or time to detection on CT&T.

**Data-quality flag** [D, ours and BusRecall agent]: several splits have identical frame and attack counts across sets.

- set_01/test_04 equals set_02/test_01 (the dataset's tables: 13,220,567 / 13,220,110 frames; our loader: 13,220,555 frames and 14,244 attack frames).
- set_03/test_04 equals set_04/test_01.
- set_03/test_02 equals set_04/test_03.
- The last two are consistent (Forester in both). The first is not: set_01/test_04 should be the Silverado ("unknown" for set_01), and set_02/test_01 should be the Traverse ("known" for set_02).
- **Our own loader labels them Silverado and Traverse respectively, with identical counts.** One of the two is mislabelled in the dataset or by us.
- If set_02/test_01 is really Silverado data, then set_02's "known vehicle" test is actually cross-vehicle. That would explain why our set_02/test_01 is the weakest test_01 (F1 0.871, 12.9 false alarms/h).
- **Action for `can-ids-v1`:** hash all CSVs, deduplicate across sets, and verify the vehicle by ID inventory before freezing.

### 1.2 ROAD (Verma et al., PLOS ONE 19(1) e0296879, 2024; Zenodo 10462796)

**Dataset facts** [V]:

- **Size and setup:** one undisclosed vehicle from the mid-2010s; 12 ambient captures (10 dynamometer, 2 road; about 3 h) and 33 attack captures (about 30 min).
- **Fabrication captures:** real "flam" injection, one spoofed frame directly after each legitimate frame of the target ID.
- **Masquerade captures:** **simulated in post-processing** by removing the legitimate target frame before each injected frame.
- **Fuzzing:** IDs 0x000–0xFF with payload FF…FF every 5 ms; "designed to be easy to detect".
- **Accelerator attack:** no injected frames; timing undisturbed.
- **Raw logs:** raw candump for all 45 captures.
- **CAN-D signal translations:** only for the ambient captures and 17 attack captures (13 masquerade + 4 accelerator).
- **Labels:** intervals are labelled, not frames, so frame labels must be derived from the metadata.
- **Obfuscation:** IDs are remapped and payloads scrambled per ID.
- **Baselines:** the paper reports no detection results of its own.

| Paper | ROAD variant / protocol | Unit / metric | Model / size | Numbers | Tag |
|---|---|---|---|---|---|
| Blevins et al., AutoSec 2021 (arXiv 2101.05781) | **raw, fabrication + fuzzing only** (16 logs, 1,588,263 msgs, 3.9% attack). Train on 10 ambient dyno logs (108.2 min) | frame, AUC-PR (aggregate) | timing: Mean, Binning, Gaussian, KDE | AUC-PR: Binning 87.63% (82.18% without outliers); Mean 68.90%; Gaussian 0.00%; KDE 0.02%. Best F1: Binning 0.990, Mean 0.986. **Thresholds tuned on test.** Even the best detector gives "~1,821 alerts per minute". Binning ran on a Raspberry Pi 3B+ | [V] |
| CANShield, Shahriar et al., IoT-J 2023 (arXiv 2205.01306) | **signal, masquerade** (5 types); 3 h train / 30 min test | AUROC, AUPRC | 3 CNN-AE ensemble, 525 KB (CANet: 8,718 KB) | AUROC "~1.00" for all; AUPRC 0.99–1.0 (read from figure) | [V] |
| Moriano et al., AutoSec 2022 (arXiv 2201.02665) | **signal, masquerade**; whole-capture decision | p-values | correlation clustering + CluSim | Ward linkage detects all 5 (p ≤ 0.008). Single linkage misses 2 | [V] |
| Moriano et al., JISA 2026 (arXiv 2406.13778) | **signal, masquerade**, online sliding windows | window AUC-ROC | 4 unsupervised, non-DL | Average of max over the window grid: Moriano22 0.73, matrix methods 0.67, Ganesan17 0.61. "No free lunch". The grid max is effectively tuned on test | [V] |
| Marfo, Moriano et al., TIFS 2025 (arXiv 2408.05427) | **signal, masquerade**, 3 h / 30 min | AUC-ROC per attack | node2vec + signal stats → RF (100 trees) / XGB | 0.99 on every attack. **Their reruns:** Moriano 0.93–0.97, CANShield 0.90–0.94. Time to window 0.44–1.85 s | [V] |
| Koltai, Ács, Gazdag 2026 (arXiv 2606.30430) | benign-only training. **Raw injection** for frame methods; **signal modification** for AEs. 1 s windows; best-F1 threshold, source of the threshold not stated | bACC / F1 / MCC (%) | 5 re-implementations | MBA-OCSVM 96.49/96.32/93.28; AssocRules 57.75/68.12/26.96; FlowNGram 55.60/63.30/11.61; CANet-AE 69.65/15.57/17.18; **CANShield-AE 76.24/65.69/50.15** | [V] |
| MR-TCN, Hellemans et al., T-ITS 26(11) 2025 (doi 10.1109/TITS.2025.3590301) | **raw**, fuzzing + fabrication + masquerade pooled, accelerator excluded; **per-class 60/20/20 window split** (leakage-prone) | 64-frame windows | supervised TCN, 3-bit on FPGA | F1 0.9975 (software), 0.9986 (3-bit). DWS-CNN baseline 0.6565 | [V] |
| Guerra et al., CSCS 2024 (arXiv 2408.17235) | **raw**, random 80/20 + oversampling | frame, multiclass and binary | RF, LightGBM, LSTM, DCNN, … | Multiclass LSTM avg F1 0.5963 (vs 0.9778 on HCRL). Binary per-attack models ≈ 1.0 | [V] |
| Hossain & Moriano (arXiv 2602.02781) | **raw**, fuzzing + 5 fabrication, random 70/30 | frame, MCC | DT/RF/ET/XGB/DNN | clean MCC 0.908 (RF); under PGD, e.g. RF on fuzzing drops to 0.812 at ε = 5 | [V] |
| PIRD, Hegde & Reddy (arXiv 2608.05548) | **raw, per capture**; calibrated on each capture's pre-attack part ("tens of seconds"); fabrication vs masquerade not stated | frame F1 | per-ID residuals + Isolation Forest | Mean F1: correlated 0.898, speedometer 0.698, light off 0.657, light on 0.544, coolant 0.265, fuzzing 0.273. FPR 2–5% | [V] |
| can-sleuth | – | – | – | **does not evaluate ROAD** ("not labeled") | [V] |

**Bottom line for ROAD.**

- Results cannot be compared across papers: variant, split and unit all differ.
- Supervised random-split papers report F1 ≥ 0.99. Per-capture or benign-only protocols report much less.
- The same detector scores differently depending on who runs it. CANShield gets ~1.00 in its own paper, 0.90–0.94 in Marfo's rerun and MCC 0.50 in Koltai's.
- Max Engine Coolant has one capture per variant, so its numbers are unstable everywhere.

---

## 2. Cross-dataset and realistic-evaluation studies

| Study | What they did | Key findings | Tag |
|---|---|---|---|
| **can-sleuth** (Kidmose, Kidmose, Meng; IJIS 2025) | 16 sklearn IDS on 6 datasets: HCRL Car-Hacking, HCRL Survival, CT&T v1.5, UNIMORE Bus-Off, DAGA, Ventus. Weighted P/R/F1, G-mean, FPR | CT&T exposes overfitting to one vehicle; single-vehicle sets cannot. Train-test interdependence in DAGA: 6 of 9 models score better on the leaky split. Removing the timestamp hurts RF "catastrophically". Suppress attacks cannot be scored with frame labels. **Caveat:** weighted F1 flatters all results | [V] |
| **Koltai, Ács, Gazdag** (arXiv 2606.30430; ACSW'26) | 5 IDS re-implemented, benign-only, 7 datasets (no CT&T). Code: github.com/CrySyS/Cross-Dataset-Study-of-Automotive-IDS-Evaluation | No method wins everywhere, and each does best on its home dataset. MBA-OCSVM is the most stable frame-level method (bACC ≥ 82.78 except DAGA). Signal AEs collapse outside SynCAN. **Metric lesson:** on DAGA, MBA-OCSVM has F1 97.82 but MCC 10.05. Per-family best F1: DoS 94.2, replay ≤ 50.7, suspension ≤ 13.5. Recommends bACC, F1, MCC, ROC-AUC and per-family breakdowns. **No false-alarm rate or latency reported** | [V] |
| **Heydari, Nyarko, Alam** (Array 31, 2026) | Corrected Car-Hacking and Survival; LR, RF, XGB, MLPs, IF; controls: fixed-ID lookup, timing, payload-only; stress test holding out the top-5 IDs; chronological Car→Survival transfer | Fixed baselines get lower and less stable under ID hold-out. Car→Survival transfer is only between two lab corpora. The ID-lookup AUC is 0.970 / 0.986 [U, snippet] | [V] abstract |
| **Lazeski et al.** (VehicleSec 2026) | Per-attack interpretable decision trees on Car-Hacking, Survival, OTIDS, CT&T, HCRL Challenge 2020; adaptive attacker | DoS is always ID 0x000 with a zero payload (one split, F1 1.0). Spoofing payloads never occur in benign traffic (F1 1.0). The Challenge test spoofing differs from training: **FPR 1.000, F1 0.000**. Fuzzing trees use absolute timestamps. Replay F1 0.547–0.764 with trees of up to 10,707 nodes. "The bottleneck is dataset realism, not model choice." Proposes spec/DBC rule pre-filters followed by ML | [V] |
| **Blevins et al.** (AutoSec 2021) | 4 timing detectors on ROAD fabrication/fuzzing | Distribution-agnostic methods beat distribution-fitting ones by ≥ 55% AUC-PR. 98.6% precision still means ~1,821 alerts/min, which is not deployable | [V] |
| **AutoHack**, Song et al. (VehicleSec 2026, Best Artifact; https://www.usenix.org/system/files/vehiclesec26-song.pdf) | 2023 Hyundai, 3 buses (C/P/B-CAN); physically verified attacks, including UDS and timing-opaque replay; competition | Competition teams reached 39–66% weighted F1. RF baseline: replay **F1 0.68 but AUC 0.985**; spoofing F1 0.79, AUC 0.99; DoS 1.0. Joint multi-bus training lowers per-bus F1 (RF B-CAN 0.84 → 0.68) | [V] |
| **Moriano et al.** (JISA 2026) | Online windows on ROAD masquerade, includes test time per window | Best average AUC 0.73; the best method is ≥ 4× slower; no method is best for every attack | [V] |
| **SoK FL-IDS** (arXiv 2607.10914) | Audit of 60+ FL-IDS papers | Artificial IID splits, trivial benchmarks, weak adversarial evaluation, real-time CAN constraints ignored | [V] abstract |
| Liu et al., T-ITS 2025 (arXiv 2505.17274) | IDS re-implemented on real vehicle data | Real CAN periods are not constant | [V] summary |
| Longari et al. (arXiv 2506.10620, doi 10.1145/3737294) | Gradient-based evasion, white/grey/black box | Success depends on dataset, IDS and attacker knowledge | [V] abstract |
| Pollicino, Stabili, Marchetti 2023 (arXiv 2307.04561) | 8 timing detectors re-implemented on Ventus and OTIDS | Timing detectors need per-dataset retuning | [V] |

**Synthesis.**

**Which models generalise best?**

- There is no consistent winner (Koltai).
- Simple distribution-agnostic timing/count detectors beat distribution fitting (Blevins).
- MBA-OCSVM is the most stable benign-only frame method (Koltai).
- The MLP keeps 0.85–0.96 weighted F1 on an unseen vehicle (can-sleuth). Weighted F1 hides attack misses, though, so the attack-class picture is far worse (Table 1).
- Tree models reach near-perfect scores mostly by memorising dataset constants (Lazeski).
- Whitelists and ID features break on new vehicles (can-logic, BusRecall).

**Which metrics expose weaknesses?**

- **MCC or balanced accuracy instead of (weighted) F1.** DAGA: F1 97.8 vs MCC 10.
- **Per-attack-family F1 instead of pooled AUC.** AutoHack replay: F1 0.68 vs AUC 0.985.
- **Held-out vehicles and IDs.**
- **False positive rate converted to alerts per unit time.** Blevins: ~1,821/min.

**What nobody reports.** We found no 2025–2026 CAN paper that reports **false alarms per hour, event-level detection rate, time to detection, or recall at a fixed FPR** on a public benchmark. Blevins (alerts/min) and Moriano and Marfo (time per window, time to window 0.44–1.85 s) come closest [V]. This is the largest open gap.

---

## 3. Data efficiency: benign-only training, adaptation to a new vehicle, learning phases

| Approach | Data needed | Result | Tag / source |
|---|---|---|---|
| Moore et al. 2017, inter-signal arrival | **5 s** of normal data per model | TPR 0.9998, FDR 0.00298 | [V] abstract, https://archive.cps-vo.org/node/46971 |
| Young et al. 2019, interval vs frequency | "a few seconds" of clean traffic | Interval IDS: **30% FPR on vehicle 2** (about 30 of 137 IDs aperiodic). The frequency method was better | [V] https://par.nsf.gov/servlets/purl/10094275 |
| SAIDuCANT (Olufowobi et al. 2019) | about **120 s** of normal driving | ≤ 1 FP before attack onset vs > 100 for other timing IDS | [V] |
| Cho & Shin CIDS (USENIX Sec 2016) | Online RLS, updates every 20 msgs per ID. The threat model assumes 420 s clean first | FPR 0.055% at 100% TPR for timed masquerade. Needs retuning per dataset | [V] |
| EASI (Kneib et al., NDSS 2020) | **first 200 frames per ECU**; **2.61 s** training on an MCU | 99.98% sender identification; incremental updates supported | [V] |
| Viden (CCS 2017) | 2–3 messages per voltage instance; online RLS | 0.2% false identification | [V] arXiv 1708.08414 |
| Blevins (ROAD) | 108.2 min of ambient | see 1.2 | [V] |
| PIRD (Hegde, 2026) | tens of seconds per capture | F1 0.27–0.90, FPR 2–5%; no cross-vehicle test | [V] |
| CANShield | 3 h (ROAD), 16.5 h (SynCAN); "sufficient training data" listed as a limitation | see 1.2 | [V] |
| CANet | 12.5 h (real vehicle), 16.5 h (SynCAN) | – | [V] arXiv 1906.02492 |
| **CAN-ODTL** (Rajapaksha et al., VehicleSec 2023) | 3 M ROAD frames ≈ **30 min**; recommends **30–60 min** for the initial model, then on-device last-layer retraining per drive | Last-layer retraining ≈ full retraining; > 99% detection; 125 ms latency on Raspberry Pi | [V] https://www.ndss-symposium.org/wp-content/uploads/2023/02/vehiclesec2023-23088-paper.pdf |
| Hoang & Kim 2022, SupCon transfer (arXiv 2207.10814) | **labelled target attacks** needed; 65k–250k msgs per attack file | Fuzzy FN down to 0.06% (Soul), 0.47% (Spark) | [V] |
| CANTransfer (SAC 2020) | one-shot, **new attacks** (not new vehicles) | +26.6% over the best baseline | [V] abstract |
| Whitehead 2026 (Cal Poly MS thesis) | **75% less** vehicle-specific training data | F1 0.99997 vs 0.99903 | [V] flyer only |
| MAML + LSTM few-shot (Springer 2026) | 5–10 labelled samples of a new attack | 96.45% / 96.55% accuracy | [U] |
| Xiang et al. 2026 preprint (preprints.org 202609.1557) | verified-clean prefixes of the target vehicle | not readable | [U] |
| Federated: Althunayyan H-FL (Future Internet 2024); FedLiTeCAN (arXiv 2512.24088); Digregorio/CANdito FL (arXiv 2506.04978) | non-IID clients | H-FL F1 up to +10.63%; FedLiTeCAN 98.5% acc, 0.4 MB; federated CANdito below centralised | [V] |
| Althunayyan "Tiny Online Learning" (Cardiff thesis, ORCA 184547) | – | F1 0.993/0.984/0.975 per CAN ID | [U] (403) |
| AUTOSAR IdsM R24-11; ETAS CycurIDS; Argus, Upstream, Vector | – | No public learning-phase duration. IdsM only qualifies and filters events | [V] (IdsM spec), [V] none found |

**Takeaways.**

1. Timing-based detectors are fitted on **seconds to minutes** of clean traffic. Their problem is false positives on aperiodic or mode-dependent IDs (Young: 30% FPR), not a lack of data.
2. Learned sequence and signal models want **30 min to 16 h**.
3. Transfer and few-shot gains in the literature are mostly **supervised**, so they need labelled attacks on the target vehicle.
4. **No opened source reports a rigorous normal-only few-shot adaptation to a new vehicle with a data-vs-false-alarm curve.** This is a gap we can fill.

---

## 4. Honest comparison with our pre-zoo numbers

Sources:

- `topics/security/reports/picket-forest/protocol_results.json`, `research-card.md`
- `topics/security/reports/picket-mlp/research-report.json`, `README.md`

These are **not benchmark results**. They were not frozen, they are single runs without seeds or CIs, and the dataset split is not deduplicated.

### 4.1 picket-forest (RF, 30 trees, 12 features without CAN ID, k-of-window alarm) on CT&T

**Where it looks strong**

- **Attack-class F1 on the official splits is far above everything we found published** (Table 1). Averages over sets: 0.947 / 0.861 / 0.869 / 0.812 for test_01–04 [O]. Published bests on unknown-vehicle splits are attack-F1 ≤ 0.38 [D], and BusRecall's cross-vehicle mean is 0.042 [V].
  - Plausible reasons: relative per-ID timing and payload-change features rather than raw fields, no ID or whitelist, attack-class thresholds chosen on held-out training captures, and frame features computed with streaming state.
  - **This gap is large enough to be suspicious.** It must be re-checked on the frozen, deduplicated `can-ids-v1` split before anyone claims it.
- **Frame FPR stays at 4e-5 to 4e-3 on unknown vehicles** [O]. can-logic, which relies on a whitelist, reaches FPR 0.28–0.995 there [D].
- **It reports event-level metrics** (episode recall, time to alarm, false alarms/h), which no published CT&T or ROAD work does.
- **It is deployable:** 10.4 KB detector RAM and bit-exact C on ESP32/ESP32-S3 in QEMU [O]. KD-GAT's student has 316k parameters; VGAE+GAT's has 55k [V].

**Where it looks weak**

- **Pooled frame F1 is dominated by DoS frames.** In set_01/test_02, frame F1 is 0.994, but per-attack recall is force-neutral 0.216, rpm 0.428 and standstill 0.39. The default alarm rule detects only **12% of episodes** (median latency 2.7 s) [O]. Our own headline number therefore has the same flaw that we criticise in weighted F1. Use per-attack macro and event-level metrics instead.
- **Event-level detection is poor.** With the default rule (3 flagged frames in 200 ms), episode recall is 5–100% per cell and averages 36–71% per split [O]. A false-alarm budget of ≤ 2/h was the selection criterion.
- **Unknown vehicles cause false-alarm storms.** In set_04 (Forester → Traverse), test_02 has 948 false alarms/h and test_04 has 1,317/h [O].
  - **With the CAN ID feature, the same cells fall to 1.6/h and 0/h** [O].
  - So dropping the CAN ID is not uniformly better. The "no vehicle-specific configuration" claim costs a lot on this pair. Its cost must be measured, not assumed.
- **Unknown attacks are a weak spot.** set_01/test_03 has F1 0.650 (AUC-PR 0.587); set_01/test_04 has F1 0.471 (AUC-PR 0.357). Fuzzing recall is 0.445 when unseen, systematic 0.334 [O].
- **Timing-opaque attacks are not covered.** Masquerade (CT&T v1.5 test_06) and suppress (test_05) are not evaluated.
- **Possible split contamination.** set_02/test_01 may be another vehicle's capture (§1.1 data-quality flag).
- **Metric-code oddity.** For several k=1 alarm rules, `median_latency_ms` is null (−1 in our dump) while episode recall is > 0, e.g. set_01/test_02 k1_w50 [O]. Check `metrics.py` before freezing.

### 4.2 picket-mlp (int8 MLP 32-64-32-2, 5 KB params) on ROAD

Test set: held-out `_2` attack captures plus every 4th ambient capture, 2.2 M frames. Frame-level precision 0.659, recall 0.817, F1 0.730, FPR 0.0076 (int8) [O].

**Strong**

- The **per-capture hold-out** is a stricter protocol than the random 70/30 or 80/20 splits behind the ROAD F1 ≥ 0.99 claims (Guerra, Hossain, MR-TCN).
- The int8 model matches TFLite bit-exactly (0 mismatches).

**Weak**

- **FPR 0.76% is not deployable.** At an assumed 1,000–2,000 frames/s, that is roughly 7–15 flagged benign frames per second before aggregation. This is our own back-of-the-envelope calculation; the ROAD frame rate was not measured.
- **Features include the 11 raw ID bits and a known-ID flag.** This is exactly the ID-lookup shortcut identified by Heydari et al. and Lazeski et al., and on a single vehicle it inflates the scores.
- **Fabrication, masquerade and fuzzing are pooled.** No per-attack or per-variant numbers.
- **Not comparable to existing work:**
  - Blevins (AUC-PR 0.876, fabrication + fuzzing only, thresholds tuned on test).
  - Koltai MBA-OCSVM (F1 96.3% on 1 s windows, benign-only).
  - The signal-level masquerade papers (AUROC 0.90–1.00).
  - Per-attack AUC-PR and window-level scores are missing.
- **Only one vehicle,** so ROAD says nothing about generalisation.

---

## 5. Proposal for `can-ids-v1`

### 5.1 Headline metrics and why

1. **Event recall at a fixed false-alarm budget (primary headline).**
   - Report the share of attack episodes detected at ≤ 1 false alarm/h and at ≤ 10 false alarms/h on the deployed alarm stage. Show both the median over the 4 sets and the **worst set**, per split.
   - Episodes and the false-alarm rate are counted after the alarm stage, as in our `metrics.py`.
   - Why:
     - An operator or IdsM sees alarms, not frames.
     - Blevins showed that 98.6% precision still means ~1,821 alerts/min.
     - No published CT&T or ROAD result reports this, so we would set the reference.
     - A fixed budget avoids threshold-tuning-on-test, which affects Blevins, Moriano and possibly Koltai.
2. **Time to alarm: median and p95** per detected episode. Why: no paper reports it on these datasets, and it matters for an MCU sitting on the bus.
3. **Frame-level attack-class AUC-PR and MCC**, per attack family (macro over families) and pooled. Report **attack-class F1 only, never weighted F1**. Why: weighted F1 made BIRCH with TP = 0 "win" in the original CT&T benchmark, and F1 hides near-chance detection where MCC does not (Koltai, DAGA). The per-family macro removes the DoS dominance that inflates our own pooled F1.
4. **Recall at fixed frame FPR (1e-4, 1e-5)** as a secondary, threshold-free comparison with frame-level papers.
5. **On-device cost with feature extraction included:**
   - RAM
   - Flash
   - worst-case cycles per frame on the reference MCU, and headroom at 100% bus load
   - At 500 kbit/s, an 8-byte standard frame of ~110–135 bits with stuffing gives roughly 3,700–4,500 frames/s. This is our own calculation; it must be confirmed on the HIL bench.
   - Report whether each measurement comes from a real board, an emulator or the simulator.
6. **Split reporting:**
   - Always the four CT&T cells separately, plus the worst set, plus the ROAD per-variant results:
     - fabrication (raw)
     - masquerade (raw, and signal if used)
     - fuzzing
     - accelerator, reported separately or excluded with a reason
   - Add CT&T v1.5 `test_06_masquerade` as a timing-opaque cell.
   - `test_05_suppress` cannot be frame-labelled. Score it only at event level (alarm within the suppression interval), or leave it out.

### 5.2 Candidate USP dimensions where a small MCU model can credibly win

| # | USP | Evidence that the gap exists | Our current standing | Risk |
|---|---|---|---|---|
| 1 | **First operational (event-level) results on official cross-vehicle/cross-attack splits**: detection rate at ≤ 1 and ≤ 10 false alarms/h, plus time to alarm | No 2025–26 paper reports false alarms/h, time to detection or recall at fixed FPR on CT&T or ROAD [V, §2]. Koltai reports no false-alarm rate or latency [V]. Blevins frames the problem as alerts/min [V] | We already compute it [O]. Numbers are weak (episode recall 36–71% at ≤ 2/h on validation) | Low, since it is a contribution of protocol and measurement. Our numbers may look modest, but they will be the only ones |
| 2 | **Vehicle-agnostic detection without ID whitelists or DBC** (works on an unknown vehicle out of the box) | Whitelists collapse (can-logic FPR 0.28–0.995 on unknown vehicles [D]); cross-vehicle F1 0.042 (BusRecall [V]); published unknown-vehicle attack-F1 ≤ 0.38 [D]; ID-lookup shortcuts inflate single-vehicle scores (Heydari, Lazeski [V]) | Frame attack-F1 0.73–0.99 on unknown-vehicle cells [O], **but** 948–1,317 false alarms/h on set_04 | Medium. The frame-level lead needs re-verification on deduplicated splits, and the false-alarm storms must be fixed (see #3) |
| 3 | **Benign-only on-vehicle calibration in minutes, on the MCU** (e.g. learn per-ID period and payload-change statistics, or recalibrate thresholds, from N minutes of clean driving), with a published **calibration-time vs false-alarms/h curve** | Timing detectors need seconds to minutes [V], but aperiodic IDs cause FPR up to 30% (Young [V]). Learned models need 30 min–16 h (CAN-ODTL, CANShield, CANet [V]). CAN-ODTL adapts on a Raspberry Pi, not an MCU [V]. EASI trains in 2.61 s on an MCU, but for sender ID, not intrusion [V]. **No rigorous normal-only few-shot new-vehicle result found** [V, §3] | Not built. Our set_04 false-alarm storm comes from persistent per-ID false positives, which is exactly what a learning phase targets [O] | Medium. Needs a clean "warm-up" prefix per test vehicle in the benchmark. CT&T `train_01_attack_free` (v1.5) and the ROAD ambient captures provide it |
| 4 | **Verified deployed arithmetic at ECU scale**: bit-exact C/int8 with feature extraction included, ≤ 16 KB RAM, cycles per frame at full bus load on a real board | Published CT&T DL models have 55k–5M parameters (KD-GAT, VGAE) [V]. MR-TCN targets an FPGA [V]. Rasp-Pi-class deployments (Blevins, CAN-ODTL) [V]. MCU peers report model-only footprints (Im & Lee, nRF52840: 20.44 kB flash [V in repo notes]). No one reports accuracy *of the deployed arithmetic* on the official splits | 10.4 KB RAM, bit-exact in QEMU [O]. Real-board latency is still missing | Low technically. Needs the HIL measurement |
| 5 | **Timing-opaque coverage (masquerade/suspension) at MCU scale** with a small per-ID payload/statistics model | Masquerade is the hard case: CANShield (525 KB) drops from ~1.00 to 0.90–0.94 (Marfo) and to MCC 0.50 (Koltai) when rerun [V]. Online window methods average ≤ 0.73 AUC (Moriano 2026) [V]. Per-family F1 for replay ≤ 50.7 and suspension ≤ 13.5 (Koltai) [V] | Not evaluated. picket-mlp mixes masquerade into a pooled score [O] | High. Strongest scientific win if it works, but we have no evidence yet |
| (6) | Robustness to an adaptive, timing-aware attacker within the CAN protocol | RF MCC drops 0.908 → 0.812 under PGD on ROAD (Hossain & Moriano) [V]. Lazeski's adaptive attacker defeats learned rules [V]. Longari [V] | None | Secondary; adopt later as a stress test |

**Recommendation.** Lead with **#1 + #2 + #4** as the defensible USP ("the only CAN IDS with event-level, cross-vehicle results measured on the deployed MCU code"). Build **#3** as the next model feature: it directly fixes our worst weakness and fills a documented gap. Treat **#5** as research.

### 5.3 Baselines that `can-ids-v1` must include

**Shortcut controls** (must be reported, because they show what the dataset gives away):

- **ID lookup:** per-ID attack prior learned on train (Heydari et al.).
- **Timing-only RF:** features `dt_id`, `dt_ratio` only.
- **Our RF with the CAN ID:** the `full` variant, to quantify the ID shortcut per cell.

**Classic, benign-only:**

- **Per-ID interval detector:** Song et al. 2016 / Blevins "Mean".
- **Blevins "Binning"** (best in their benchmark).
- **can-logic three-rule detector** (interval, repetition, whitelist). Its published per-cell confusion counts give a sanity check of our loader.
- **MBA-OCSVM** (most stable benign-only method in Koltai). A re-implementation exists in the CrySyS repo.
- **Isolation Forest** on our features.
- **PIRD-style per-ID residual + IF**, calibrated on a clean prefix. This is the natural baseline for USP #3.

**Classic, supervised** (Lampe & Meng / can-sleuth style, rescored with attack-class metrics):

- Default scikit-learn RF, ExtraTrees, DT, GB, LogReg and MLP on raw timestamp/ID/bytes.
- These re-create the published table under a correct metric.
- RF with 200 trees on 100-frame windows, following BusRecall, for the window-level comparison.

**Recent / deep** (at least one per family, as size-matched or full-size references):

| Baseline | Why include it |
|---|---|
| KD-GAT student (316k params) or VGAE+GAT student (55k) (Frenken et al.) | the only recent DL with per-set CT&T numbers |
| CANShield (signal-level masquerade; its CNN-AE also exists in the CrySyS code) | the reference for ROAD masquerade |
| CANet-LSTM-AE (CrySyS re-implementation) | – |
| MR-TCN or a small TCN on 64-frame windows | quantised and hardware-oriented; ROAD |
| Marfo et al. node2vec + RF | best ROAD masquerade result, 0.99 AUC |
| CAN-ODTL-style last-layer adaptation | the adaptation baseline for USP #3 |

**MCU peers** (where code exists; report footprint next to accuracy):

- Im & Lee dual-branch CNN (nRF52840).
- TPI-IDS / PIB-IDS (STM32), if code becomes available.

Code availability: the CrySyS re-implementations are confirmed by the Koltai paper [V]. Code for the other baselines was not checked and is [U].

---

## 6. Sources (opened unless marked [U])

- Lampe & Meng, can-train-and-test: arXiv 2308.04972; Computers & Security 140 (2024) 103777, doi 10.1016/j.cose.2024.103777; data doi 10.11583/DTU.24805533; Bitbucket brooke-lampe/can-train-and-test(-v1.5)
- Lampe & Meng, can-logic, ACM IoT 2023 (DTU Orbit PDF via Wayback)
- Kidmose & Meng, can-sleuth, EICC 2024, doi 10.1145/3655693.3655696
- Kidmose, Kidmose, Meng, can-sleuth, IJIS 24(5) 2025, doi 10.1007/s10207-025-01038-8; https://eprints.lancs.ac.uk/id/eprint/232827/
- Kidmose & Meng, can-fp, PST 2024 [U]
- Frenken et al., KD-GAT, ITSC 2025, arXiv 2507.19686; VGAE+GAT, arXiv 2508.04845
- Kutlu et al., BusRecall replication, Zenodo doi 10.5281/zenodo.21889099, 10.5281/zenodo.22228087
- Li et al., ECF-IDS, IEEE TNSM 2024, doi 10.1109/TNSM.2024.3394842
- Verma et al., ROAD, PLOS ONE 19(1) e0296879, doi 10.1371/journal.pone.0296879; https://zenodo.org/records/10462796
- Blevins et al., arXiv 2101.05781 (AutoSec 2021)
- Shahriar et al., CANShield, arXiv 2205.01306
- Moriano et al., arXiv 2201.02665 (AutoSec 2022); arXiv 2406.13778 (JISA 2026)
- Marfo, Moriano et al., arXiv 2408.05427 (TIFS 2025)
- Hellemans et al., MR-TCN, doi 10.1109/TITS.2025.3590301
- Guerra et al., arXiv 2408.17235, doi 10.1145/3689936.3694696
- Hossain & Moriano, arXiv 2602.02781
- Hegde & Reddy, PIRD, arXiv 2608.05548
- Koltai, Ács, Gazdag, arXiv 2606.30430; code: github.com/CrySyS/Cross-Dataset-Study-of-Automotive-IDS-Evaluation
- Heydari, Nyarko, Alam, Array 31 (2026) 101112, doi 10.1016/j.array.2026.101112 (abstract only)
- Lazeski et al., https://www.usenix.org/system/files/vehiclesec26-lazeski.pdf; dataset tudatalib 5167 (access denied)
- Song et al., AutoHack, https://www.usenix.org/system/files/vehiclesec26-song.pdf
- SoK FL-IDS, arXiv 2607.10914; Liu et al., arXiv 2505.17274; Longari et al., arXiv 2506.10620; Pollicino et al., arXiv 2307.04561
- Moore et al. 2017, https://archive.cps-vo.org/node/46971
- Young et al. 2019, https://par.nsf.gov/servlets/purl/10094275
- Olufowobi et al., SAIDuCANT, https://rcl.ece.iastate.edu/sites/default/files/papers/OluYou19A.pdf
- Cho & Shin, CIDS, https://rtcl.eecs.umich.edu/rtclweb/assets/publications/2016/sec16-final165_final.pdf
- Kneib et al., EASI, https://www.ndss-symposium.org/wp-content/uploads/2020/02/24025.pdf
- Viden, arXiv 1708.08414
- Hanselmann et al., CANet, arXiv 1906.02492
- Kukkala et al., INDRA, arXiv 2007.08795
- Rajapaksha et al., CAN-ODTL, https://www.ndss-symposium.org/wp-content/uploads/2023/02/vehiclesec2023-23088-paper.pdf
- Hoang & Kim, arXiv 2207.10814
- Tariq et al., CANTransfer, doi 10.1145/3341105.3373868
- Althunayyan et al., arXiv 2408.08433; arXiv 2505.11551; H-FL, Future Internet 16(12) 451; ORCA 184547 [U]
- FedLiTeCAN, arXiv 2512.24088; Digregorio et al., arXiv 2506.04978
- AUTOSAR CP R24-11 IdsM SWS, https://autosar.org/fileadmin/standards/R24-11/CP/AUTOSAR_CP_SWS_IntrusionDetectionSystemManager.pdf
- [U] Whitehead thesis flyer (Cal Poly 2026); MAML+LSTM, Springer 2026, doi prefix 10.1007/978-3-032-23450-6_16; Xiang et al., preprints.org 202609.1557
