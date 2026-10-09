# 03 – Datasets

Details on around 40 datasets with sizes, formats, criticism and verification status are in [notes/datasets.md](notes/datasets.md).

> ⚠️ Many licence pages (HCRL, UNB/CIC, Zenodo, IEEE DataPort) were not directly
> reachable during the research. Licence statements marked `[CONFLICT]` or `[UNVERIFIED]` must be checked by hand
> before any use for published models. Then archive the licence text, e.g. under `datasets/<name>/LICENSE-snapshot.txt`.

## Licences: what may we publish?

| Licence type | Re-host the data? | Publish models openly? |
|---|---|---|
| **CC BY 4.0 / MIT** | yes, with attribution | yes |
| **CC BY-NC(-SA)** | no, or non-commercial only | legally unresolved; common practice: weights under an NC licence, state the training data |
| **CC BY-NC-ND** | no, not even cleaned mirrors | as above |
| **Own academic terms** (HCRL, SynCAN) | no | as NC; SynCAN additionally forbids any use in the field |
| **No licence** (TEXBAT, ECUPrint) | no (all rights reserved) | for research and benchmarks only |

**Proposed policy:**

1. Models that we publish **openly and usable commercially** are trained only on CC BY or MIT data
   or on **self-recorded** data.
2. We use NC datasets only for **comparison (benchmark)**. If we train on them, the weights appear
   under `cc-by-nc-4.0` or `other`, with the restriction carried over.
3. We re-host raw data only if the licence allows it. Otherwise we publish loaders and download scripts.

## Recommended starter datasets

| Dataset | Domain | Licence | Why |
|---|---|---|---|
| **can-train-and-test** (Lampe & Meng, DTU) | CAN, 4 vehicles, 7.5 GB | **CC BY 4.0** [V-S] | Built specifically against the HCRL weaknesses; test splits on unseen vehicles; frame-level features |
| **CAN-MIRGU** (VehicleSec 2024) | CAN, real driving with ADAS | **CC BY 4.0** (UCI) [V-S] | 17 h of normal driving, 26 physically verified attacks, plus masquerade/suspension; candump format |
| **ROAD** (ORNL, PLOS ONE 2024) | CAN raw + decoded signals | probably CC BY 4.0 (Zenodo) [CONFLICT] | Most realistic stealthy attacks; signal version for masquerade models |
| **VeReMi / Extension / NextGen** | V2X (simulated) | **CC BY 4.0** [V-GH] | 5 / 19 / 15 misbehaviour types; small per-message features |
| **GPS Spoofing Detection on UAS** (Aissou, Mendeley) | GNSS tracking features | **CC BY 4.0** [V-S] | 13 features × 8 channels; directly MCU-suitable |
| **SimulaMet Jammertest 2025** (IEEE DataPort) | GNSS NMEA from u-blox/Quectel | [UNVERIFIED] | Low-rate data from production devices, over 2000 km of driving; fits the MCU scenario exactly |
| **comma2k19** | CAN + IMU + GNSS (without attacks) | **MIT** | Normal data for plausibility models; already on Hugging Face |
| **AutoHack** (VehicleSec 2026, Best Artifact) | 3 synchronous CAN buses, Hyundai 2023 | "free for everyone", exact licence [UNVERIFIED] | Newest and most realistic dataset; keep an eye on it |

## Benchmark only (non-commercial or unclear)

| Dataset | Licence | Note |
|---|---|---|
| HCRL Car-Hacking, OTIDS, Survival, CAN-FD, Driving Dataset | academic/NC [CONFLICT] | Car-Hacking is **trivially solvable** and has artefacts; only as a plausibility check |
| SynCAN (ETAS) | NC, **not in the field** | Very good for signal autoencoders; not for products |
| TU Eindhoven CAN v2 | CC BY-NC 4.0 | – |
| CICIoV2024, CICEVSE2024 (UNB CIC) | [CONFLICT]: CIC standard vs. CC BY-NC-ND | CICIoV is considered trivially separable |
| X-CANIDS (IEEE DataPort) | presumably CC BY [UNVERIFIED] | 688 signals; select subsets for MCU |
| GEM-CAN (autonomous shuttle) | CC BY-NC [V-S] | Explicitly for on-device IDS |
| TOW-IDS (automotive Ethernet) | subscribers only | cannot be re-hosted |
| TEXBAT / OAKBAT (GNSS IQ) | no licence / registration | Raw IQ data only; need a software receiver for low-rate features |
| ECUPrint (CAN voltage, 500 MS/s) | no licence | The clock-skew part is usable for TinyML |

**Do not use:** `Thi-Thu-Huong/Multi-CAN-Datasets` on Hugging Face. This dataset apparently bundles HCRL and SynCAN data against their terms.

## Tools for signal decoding

- **opendbc** (comma.ai, MIT): over 70 DBC files for many manufacturers
- **cantools** (Python, DBC/ARXML), **canmatrix**, **cabana**
- **CAN-D** (ORNL; used to produce the ROAD signals), **READ**, **LibreCAN** (reverse engineering without DBC)

## Gaps: public data is missing here

| Domain | Status | Idea for own collection |
|---|---|---|
| Keyless/UWB relay | no data | ESP32 + DW3000 UWB: record CIR, first path, ToF and RSSI under relay attacks |
| E-scooter/micromobility | no data | BLE and UART captures (e.g. Ninebot/Xiaomi) with attack scenarios |
| SOME/IP (real vehicle) | no data | vsomeip plus an attack injector |
| ISO 15118 / PLC | no data | – |
| CAN voltage (Scission etc.) | only ECUPrint, without licence | own analogue front end |
| LIN, TPMS | hardly any data | SDR (433 MHz) or LIN bus capture in the lab |

Own datasets under CC BY 4.0 would be **citable contributions** and could appear on Hugging Face first.

## What already exists on Hugging Face

- `commaai/comma2k19` (MIT, normal data)
- `asana17/ai_can_anomaly_detection_data` / `_runs`: J1939 trucks, quantised models plus C code. This is the **closest predecessor**.
- `keyvan-ai/SecIDS-v2`: TCN CAN IDS for Jetson Nano, not MCU class.
- `buckeyeguy/GraphIDS`: evaluation artefacts only.
- **Not found:** TFLite Micro or ESP32/STM32 models for CAN, V2X or GNSS security. ROAD,
  can-train-and-test, CAN-MIRGU and VeReMi are not there either. We could provide them as clean Parquet mirrors,
  with attribution and only where the licence allows it.
