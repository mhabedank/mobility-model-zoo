# Roadmap

Basis: [research](research/README.md). As of: 2026-10-07.

## Goal and guard rails (decision of 2026-10-07)

- **Goal:** Visible reputation in mobility, ML/AI and automotive security. Bring several solid, well
  documented models to Hugging Face quickly instead of polishing a single one for months.
- **Licence:** Models should be **usable commercially**. We therefore train only on data under CC BY or MIT
  (or comparable). NC datasets (HCRL, SynCAN, TU/e) appear at most as a comparison benchmark.
- **Framework:** For each model we choose what fits best (sklearn/emlearn, Keras or PyTorch). There is no fixed rule.
- **Hardware:** For now only the existing **ESP32** and hardly any budget. On-device benchmarks run over
  **test vectors via UART**, which needs no CAN bus. A CAN transceiver (SN65HVD230, ~3 €) is optional for a live demo.
- **No own vehicle data** in this phase. Data marketplaces or cooperation partners are conceivable later.
- **Hugging Face organisation** already exists.

### Fast-track plan

| # | Model | Data (licence) | Status |
|---|---|---|---|
| 1 | `picket-forest` (formerly `can-ids-tiny`): per-frame CAN attack detection with features for unseen vehicles, random forest → C (emlearn) | can-train-and-test (CC BY 4.0; reachable via Bitbucket) | v0.1 done ([model card](reports/picket-forest/research-card.md)); open: latency on real hardware, upload |
| 2 | `v2x-misbehavior-tiny` | VeReMi Extension (CC BY 4.0) | Clarify data access |
| 3 | `gnss-spoofing-tiny` | Aissou GPS Spoofing (CC BY 4.0) | Clarify data access |

**What the models should highlight:** honest evaluation (unseen vehicles, unseen attacks, false alarms per hour),
measurements from the real ESP32, and model cards that clearly delimit the intended use.

## Assessment of the low-hanging fruits

Each problem area is assessed against four criteria:

- **Data:** Are there public, openly licensed data?
- **MCU:** Does the model run on an ESP32-S3-class device?
- **Hardware:** How much additional hardware do we need?
- **Novelty/value:** Is it new on Hugging Face or scientifically interesting?

| Rank | Candidate | Data | MCU | Hardware | Novelty/value | Overall |
|---|---|---|---|---|---|---|
| **1** | **CAN IDS at ID/timing level** | ✅ CC BY (can-train-and-test, CAN-MIRGU) | ✅ | low (ESP32-S3 + transceiver) | medium: the topic is known, but **honest evaluation and MCU measurements** are missing almost everywhere | ⭐⭐⭐⭐⭐ |
| **2** | **GNSS jamming/spoofing detector** (u-blox measurements: C/N0, AGC, clock drift, position jumps) | ✅ CC BY (Aissou), Jammertest 2025 (licence open) | ✅ 1–10 Hz | low (u-blox module) | high: nothing available on Hugging Face; also relevant for micromobility and telematics | ⭐⭐⭐⭐ |
| **3** | **V2X misbehaviour detector** | ✅ CC BY (VeReMi family) | ✅ | none | medium: realistically rather on a V2X SoC | ⭐⭐⭐⭐ |
| **4** | **Signal-level masquerade detection** (small autoencoder per ID group) | ◐ ROAD (confirm licence), SynCAN (NC only) | ✅ | low | high: closes the gap of pure timing IDS | ⭐⭐⭐⭐ |
| 5 | Clock-skew sender identification | ◐ own data (ECUPrint without licence) | ✅ | MCP2518FD for hardware timestamps | high | ⭐⭐⭐ |
| 6 | Driver profile / theft protection | ◐ NC only (HCRL Driving), KCID open | ✅ | none | medium | ⭐⭐⭐ |
| 7 | EVSE anomaly (power curves) | ◐ CICEVSE2024 (licence conflict) | ✅ | none | medium; ESP32 prior work exists | ⭐⭐⭐ |
| 8 | Keyless/UWB relay, e-scooter BLE, TPMS, LIN | ❌ own data collection | ✅ | medium (UWB, SDR, scooter) | **very high: no datasets exist yet** | ⭐⭐ (later, then as a dataset publication of its own) |

## Phases

### Phase 0 – Research ✅

- Threat landscape, literature, datasets, hardware, toolchain (this PR)

### Phase 1 – Foundation

- [ ] Make decisions (see [Open decisions](#open-decisions))
- [ ] Repo skeleton: uv workspace, `packages/msml-data`, `msml-features`, `msml-export`, CI (lint and tests)
- [ ] **Check the licences of the starter datasets by hand** and store snapshots under `datasets/<name>/`
  (can-train-and-test, CAN-MIRGU, ROAD, VeReMi, Aissou)
- [ ] Dataset loaders with **leak-free splits** (temporal, per recording, per vehicle)
- [ ] Shared **evaluation protocol** as code: AUC-PR, F1, recall at fixed FPR, FP per hour, detection latency
- [ ] Model card template for security models (`tools/hf/`)
- [ ] `SECURITY.md`
- [ ] Order hardware (see [shopping list](research/04-hardware.md#shopping-list-for-the-start-proposal))

### Phase 2 – Model 1: `can-ids-timing-tiny`

**Goal:** window-based CAN IDS on an ESP32-S3 on the classic CAN bus.

- **Features** per window of N frames or T ms:
  - IAT deviation per ID
  - ID frequencies
  - unknown IDs
  - payload Hamming distance to the predecessor with the same ID
  - byte entropy
  - DLC anomalies
- **Models:**
  - Baseline: rules (period check, ID allowlist)
  - Random forest / extra trees with emlearn
  - small int8 MLP or 1D CNN with TFLM and ESP-DL
- **Data:**
  - Training and test on can-train-and-test, incl. splits with unseen vehicles
  - Cross-test on CAN-MIRGU and ROAD
  - Car-Hacking only as a plausibility check
- **Firmware:**
  - ESP-IDF component: TWAI capture, ring buffer, features in C with a parity test against Python
  - Inference at a fixed rate
  - Output as an IdsM-style security event
- **Measurement:**
  - Latency incl. features
  - RAM/flash
  - CPU load at 100 % bus load (replay via CANable)
  - Energy
- **Publication:** first model on Hugging Face with a complete model card and benchmark JSON, plus
  Parquet mirrors of the CC BY datasets, where the licence allows it.

### Phase 3 – Models 2–4 (can run in parallel)

- **`gnss-interference-tiny`:**
  - Jamming and spoofing detection from UBX/NMEA measurements on an ESP32-S3 with a u-blox module
  - Data: Aissou, Yunnan University, Jammertest 2025
  - optionally own recordings, labelled via the `jammertest-plan`
- **`v2x-misbehavior-tiny`:** per-message plausibility and misbehaviour classifier on VeReMi Extension and NextGen.
- **`can-masquerade-ae-tiny`:** signal-level autoencoder per ID group on ROAD signals.
  A variant based on SynCAN appears only under an NC licence.
- Add adversarial evaluation (`msml-adv`) for model 1.

### Phase 4 – Production-like targets and own datasets

- Port to **S32K344** (eIQ/TFLM, CMSIS-NN) and **STM32N6** (NPU). Comparison in one
  benchmark table across all target platforms.
- CAN FD (MCP2518FD or ESP32-C5/S31), clock-skew fingerprinting with hardware timestamps.
- **Own datasets** in the gaps: UWB/keyless relay, e-scooter BLE/UART, LIN, TPMS. Publication
  under CC BY 4.0 on Hugging Face, ideally with an accompanying paper.

## Open decisions

1. **Name of the Hugging Face organisation** and who gets write access.
2. **Licence policy for models:** Open only (CC BY and own data), or additionally NC models based on HCRL and SynCAN?
3. **Framework:** Is Keras 3 set as the main NN path, or does the team prefer PyTorch? PyTorch means more
   conversion effort towards `.tflite`; the path via ONNX to ESP-DL stays the same.
4. **Hardware budget:** only the starter kit list, or NUCLEO-N6, S32K344-EVB and an energy meter right away?
5. **Access to vehicles** to record normal data passively. This is important for generalisation across vehicles.
6. **Publication strategy:** Hugging Face only, or papers as well (e.g. VehicleSec, escar, AutoSec)?

## Open verification tasks from the research

- Licences: ROAD (CC BY vs. NC-SA), CICIoV2024/CICEVSE2024, AutoHack, Jammertest 2025, X-CANIDS.
- Literature: all entries marked `[unverified]` in [notes/threats-and-papers.md](research/notes/threats-and-papers.md),
  especially VeReMi, SAVIOR, Plug-N-Pwned, Brokenwire, CANet and the authors of the STM32 chapters.
- Exact MCU figures from the full texts (TPI/PIB IDS, INDRA, Crocioni et al.).
- Toolchain: Does the static int8 path via `litert-torch` arrive in TFLM? Does QEMU emulate the S3 SIMD instructions?
- Standards: Check the statements on R155/R156, ISO/SAE 21434 and AUTOSAR IdsM against the original texts.
