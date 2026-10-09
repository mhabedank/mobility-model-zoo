# 06 – Competitive landscape of CAN intrusion detection (2026-10-09)

Where `picket-forest` and `picket-mlp` stand against open models, published results, embedded deployments, commercial products and hardware alternatives, and what we must change to have a defensible USP. Sources and verification marks (`[V]` checked in the source, `[U]` snippet or secondary) are in the notes:
[open models](notes/competition-open-models.md), [commercial and regulation](notes/competition-commercial.md), [hardware alternatives](notes/competition-hardware-alternatives.md); the literature base is [02 – Literature](02-literature.md).

Our own numbers below are **pre-zoo research results, not benchmark results** ([picket-forest research card](../reports/picket-forest/research-card.md)). They must be reproduced on the frozen benchmark `can-ids-v1` before any claim is made.

## 1. Findings

### Published numbers are mostly not comparable

- Near-perfect F1 (≥ 0.99) comes from random frame or window splits, Car-Hacking (HCRL) or per-class splits. Under per-capture, benign-only or cross-vehicle protocols the same model classes drop sharply (Koltai et al. 2026; Lazeski et al., VehicleSec 2026; Guerra et al. 2024 on ROAD).
- Re-runs of the same detector disagree: CANShield reports AUROC ≈ 1.00 on ROAD masquerade; Marfo et al. 2025 get 0.90–0.94, Koltai et al. MCC 50.
- F1 hides near-chance detection (DAGA: F1 97.8 with MCC 10; AutoHack replay: F1 0.68 with AUC 0.985). Lazeski et al. show that tree models reach F1 1.0 by memorising dataset constants (DoS = ID 0x000) and drop to F1 0 when the attack pattern changes.
- can-train-and-test (Lampe & Meng): about 61 % of the published benchmark rows report support-weighted instead of attack-class F1 (BusRecall replication package, Zenodo 2026). Recomputed attack-class F1 of the 18 original baselines reaches at most 0.44 (set_01, known vehicle) and 0.09 (set_02, unknown vehicle). Of 36 citing papers checked, none reports results on the official unknown-vehicle / unknown-attack splits with attack-class metrics.
- Cross-vehicle collapse: BusRecall measures within-vehicle F1 0.86 / AUROC 0.95 against cross-vehicle F1 0.04 / AUROC 0.54 (windows of 100 frames, random forest). The can-train-and-test authors find unknown vehicles hurt more than unknown attacks (average F1 0.498 → 0.421 over 18 models).
- No 2025–2026 CAN paper found reports false alarms per hour, time to alarm or recall at a fixed false-positive rate. The ORNL timing benchmark (Blevins et al. 2021) translates its best F1 0.99 into about 1,821 alerts per minute.

### Open models

25 open systems reviewed. None combines (a) a licensed, documented microcontroller-sized model, (b) evaluation on the unknown-vehicle and unknown-attack splits and on ROAD per capture, (c) false alarms per hour after an alarm stage plus on-device latency. Embedded projects cover (a) only (an int8 MLP on STM32F446, XGBoost in C on STM32H7; both report Car-Hacking accuracy only); the strong evaluators (KD-GAT, BusRecall, CANguard/PIRD) cover (b) partly but not (a) or (c). The Hugging Face Hub has no documented CAN IDS model and no mirror of ROAD or can-train-and-test.

### Embedded deployments

- MCU ML CAN IDS 2022–2026: no peer-reviewed work found with on-device latency at full 500 kbit/s load including feature extraction. The only verified MCU ML timing is from 2021 (ST SPC58, 6–11 ms per 24-frame window).
- Edge GPUs and Raspberry Pis: full-pipeline throughput 300–2,000 frames/s on a Pi, about 5,600 frames/s on a Jetson Xavier NX at 10 W; full bus load is about 4,000–8,000 frames/s. Energy is essentially unreported.
- Rule-based detectors are the real bar on MCUs: Bloom filters on Infineon AURIX need 1.7–3.9 µs per frame (Groza & Murvay 2019, CANARY 2021); an integer rule IDS fits in 804 B on an STM32F103 at full load, while a shallow GRU saturates an STM32H743 above 50 % bus load (Subaşı & Mercimek 2026). No code repository exists for any classical MCU IDS.

### Commercial products and regulation

- In-vehicle products are mostly rule- or signature-based (ETAS CycurIDS, AUTOCRYPT, Cymotive, Karamba; NXP TJA115x ID lists in hardware); ML runs in cloud security operations centres (Upstream, VicOne xNexus). No vendor publishes a reproducible benchmark; detection claims are marketing statements.
- AUTOSAR standardises the event plumbing (IdsM API, filters, reporting), not the detection method. UN R155 requires detection, response and forensics capabilities but not a specific in-vehicle IDS; Annex 5 mitigation M15 says detection of malicious CAN messages "should be considered". GB 44495-2024 is more concrete (secondary source only).

### Hardware alternatives

Secure transceivers block foreign IDs but not a compromised ECU sending its own IDs; SecOC on classic CAN spends 4 of 8 bytes, is applied to few messages in practice, has had keys extracted (RAV4 Prime, 2024) and cannot stop bus-off attacks; CANsec for CAN XL is a draft standard. An IDS keeps value for the existing fleet (EU average vehicle age 12.7 years), unprotected messages, senders with valid keys, DoS and bus-off, OBD dongles and the R155 detection and forensics duties.

### Data efficiency

Timing detectors fit on seconds to two hours of benign traffic but suffer from aperiodic IDs (2–30 % false-positive rate); learned models need 30–60 min (CAN-ODTL) to 16 h. Transfer and few-shot adaptation found in the literature needs labelled attacks on the target vehicle. No rigorous result for "a few minutes of benign traffic on a new vehicle, on the device" was found.

## 2. Where we stand (pre-zoo numbers, to be reproduced)

| Split (can-train-and-test, mean of 4 sets) | picket-forest frame F1 | Best recomputed published baseline |
|---|---|---|
| known vehicle, known attacks | 0.947 | ≤ 0.89 (set-dependent) |
| unknown vehicle, known attacks | 0.861 | ≤ 0.40 (set-dependent) |
| known vehicle, unknown attacks | 0.869 | – |
| unknown vehicle, unknown attacks | 0.812 | – |

Weak points: false alarms on unknown vehicles (median 45.7 per hour, mean 260, one vehicle pair dominates); unseen systematic ID scans (recall 0.33) and unseen fuzzing (0.45); masquerade not covered; no real-board latency yet; the published model has no untouched test set. The gap to the published baselines is large enough that leakage must be ruled out before it is stated (features contain no absolute timestamps and no raw CAN ID, but the benchmark has to prove it).

`picket-mlp` has only been trained and tested on one vehicle (ROAD); it has no evidence on any of the dimensions above yet.

## 3. USP candidates

| # | USP | Evidence that the gap exists | What it needs from us |
|---|---|---|---|
| 1 | Honest cross-vehicle quality: attack-class metrics on the official unknown-vehicle and unknown-attack splits, published baselines recomputed on the same protocol | §1: no comparable published result; recomputed baselines ≤ 0.44 | Frozen `can-ids-v1`, baselines re-run in our harness, leakage checks (ID-lookup and shuffled-label controls) |
| 2 | Few false alarms on a new vehicle after a short benign-only calibration on the device | No such result in the literature; our weakest number | A calibration phase: per-ID whitelist and timing statistics learned in N minutes of normal traffic, measured as false alarms per hour versus calibration time |
| 3 | Full bus load on a low-cost MCU with the whole chain measured (features, model, alarm) and energy per frame | No MCU ML CAN IDS with full-load, full-pipeline latency found | Real ESP32 (and an automotive-class MCU if available) with a CAN transceiver, 500 kbit/s replay at 100 % load, power measurement |
| 4 | Open and auditable: the first documented CAN IDS on Hugging Face, open benchmark and harness, C code under Apache-2.0 | Vendors closed; HF empty; no classical MCU IDS code | Already our release path; card with protocol, limits and dual-use note |
| 5 | Hybrid rules plus model: cheap rules for what rules do well (unknown ID, DLC change, rate), the forest for timing and payload anomalies | Lazeski et al. recommend rule pre-filtering; rules are the MCU bar | Rule layer learned during calibration (#2); closes the unseen scan and fuzzing gaps |

Out of reach for now: masquerade and timing-opaque replay (need signal-level or physical-layer features), and competing with rule engines on raw speed.
