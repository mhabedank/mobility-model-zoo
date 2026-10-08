# Research: TinyML for automotive and mobility security

As of: 2026-10-07

## Structure

- **Summaries** (`01`–`05`) for decisions and planning (originally written in German).
- **English raw notes** under [`notes/`](notes/) with all details, sources and the verification status of every claim:
  - [notes/threats-and-papers.md](notes/threats-and-papers.md): 18 problem areas, 92 references
  - [notes/datasets.md](notes/datasets.md): around 40 datasets incl. licences
  - [notes/hardware.md](notes/hardware.md): around 40 MCUs/SoCs, CAN hardware, lab setup
  - [notes/toolchain-and-publishing.md](notes/toolchain-and-publishing.md): training, conversion, benchmarking, Hugging Face, repo structure

### Verification status and limitations

During the research a proxy blocked many primary sources: arXiv, IEEE, ACM, huggingface.co, Zenodo,
the HCRL pages, UNB/CIC and most vendor pages. Verification was therefore done via search results and
directly readable GitHub sources, for example ESP-IDF `soc_caps.h`, PyPI and the `huggingface_hub` source code.
The raw notes mark every claim:

| Mark | Meaning |
|---|---|
| `[V]` | verified (primary source, GitHub code or search result with a source quote) |
| `[V-partial]` / `[S]` | partly verified or secondary source only |
| `[U]` / `[unverified]` | not verified, from background knowledge; **verify before use** |

**Before every publication on Hugging Face** the licence pages of the datasets used must be checked
by hand and archived.

## Key findings

1. **CAN intrusion detection is the most mature TinyML target.** There is already peer-reviewed work with models
   that actually run on MCUs. Example: a CNN IDS on an nRF52840 with **20 kB flash / 26 kB RAM**
   (Im & Lee, IEEE ESL 2025). Others exist on STM32F746 and RISC-V. Compute is not a bottleneck; an ESP32-S3 has
   more than enough.
2. **The biggest scientific risk is the data, not the models.** The popular HCRL Car-Hacking dataset
   has recording artefacts: pauses after attacks, attacks recorded while stationary, normal traffic while driving.
   A simple ID lookup reaches a ROC-AUC of 0.97–0.99 on it. Many published results of "99.9 %" are
   therefore shortcut learning. **Our added value comes from honest evaluation**: across datasets,
   across vehicles, false positives per hour, on-device measurements.
3. **Openly licensed, realistic datasets exist.** Under **CC BY 4.0**, i.e. with open publication of the models:
   can-train-and-test (4 vehicles), CAN-MIRGU (real driving, 26 physically verified attacks),
   the VeReMi family (V2X) and the GPS spoofing dataset by Aissou. ROAD is probably CC BY 4.0 as well;
   the licence still needs to be confirmed. HCRL, SynCAN and TU Eindhoven are usable **non-commercially only**.
4. **On Hugging Face the niche is open.** No TFLite Micro, ESP32 or STM32 security model for
   automotive was found. The closest predecessor is `asana17/ai_can_anomaly_detection_runs`.
5. **Hardware:** For prototyping the **ESP32-S3** is recommended. It is cheap, has SIMD (ESP-NN/ESP-DL), a
   CAN controller (TWAI, CAN 2.0 only) as well as Wi-Fi and BLE.
   - **Production-like:** **NXP S32K344** (AEC-Q100, ASIL-D, HSE, 6× CAN FD).
   - **High end with NPU:** **STM32N6** (NPU with 600 GOPS, 3× FDCAN). The same toolchain targets the automotive-grade **Stellar P3E**.
   - **New:** ESP32-C5 and ESP32-S31 have CAN FD on the chip.
6. **Toolchain:**
   - Classic ML (random forest, extra trees) is exported to C with **emlearn**. For CAN IDS this is often the best tool.
   - Neural networks: Keras 3 → **int8 `.tflite`**. This file runs on ESP32, STM32 and NXP, plus ONNX → ESP-PPQ → `.espdl`
     for maximum speed on the ESP32-S3.
   - **microTVM is dead**; we do not use it.
7. **Low-hanging fruits:**
   1. CAN IDS at ID and timing level
   2. GNSS jamming and spoofing detector based on the u-blox measurements
   3. V2X misbehaviour detector
   4. Signal-level masquerade detection

   Details in the [roadmap](../roadmap.md).

## Gaps suited for own contributions

For the following topics **no public datasets** and hardly any ML literature were found:

- Keyless entry / UWB relay attacks
- E-scooter / micromobility security (BLE, UART bus)
- TPMS spoofing
- LIN bus
- real SOME/IP data
- ISO 15118 (charging)

These are candidates for own datasets and thus for own publications, both papers and datasets on Hugging Face.
