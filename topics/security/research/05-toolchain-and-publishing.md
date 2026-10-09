# 05 – Toolchain and publishing

Details with versions, code examples and verification status are in [notes/toolchain-and-publishing.md](notes/toolchain-and-publishing.md).

## State of the ecosystem (October 2026)

| Component | State | Meaning for us |
|---|---|---|
| TensorFlow | 2.21; `tf.lite` is to be split out of the TF package | Pin TF for the export; watch the converter in `ai-edge-litert` |
| **LiteRT for Microcontrollers** (ex TFLM) | active; `tflite-micro` Python interpreter for host tests | Reference runtime on all MCUs |
| **esp-tflite-micro + ESP-NN** | active, IDF 5.1–6.0 | portable int8 inference on the ESP32-S3 |
| **ESP-DL v3.3** + **ESP-PPQ 1.3** | active; accepts ONNX only; int8/int16/w8a16 | fastest inference on S3 and P4 (SIMD) |
| ST Edge AI Core 4.0 | supports STM32N6 and Stellar P3E | STM32 path, incl. `analyze`/`validate` |
| NXP eIQ (Toolkit, Neutron, Auto) | active | S32K3 and MCX N |
| ExecuTorch 1.5 | Cortex-M backend in beta, Ethos-U; **no ESP32** | optional for later |
| `litert-torch` (ex `ai-edge-torch`) | 0.9 | PyTorch → `.tflite`, second path |
| **emlearn** 0.23 | MIT, maintained | **Trees and ensembles → C**; ideal for CAN IDS |
| micromlgen / m2cgen | no release since 2022 | do not use |
| **microTVM** | removed from TVM (last in v0.18) | **do not use** |
| Edge Impulse | acquired by Qualcomm (announced 2025) | at most for quick baselines; not a core path because of SaaS lock-in |

## Recommended pipeline

```text
Data (DVC) → features (shared lib, also as a C implementation) → training
   ├─ classic:   sklearn RF/ExtraTrees  → emlearn → model.h
   ├─ NN: Keras 3 (TF backend) → int8 .tflite   → TFLM on ESP32 / STM32 / NXP
   └─ NN: Keras 3 → ONNX → ESP-PPQ → .espdl     → ESP-DL on ESP32-S3
        ↓
CI contract tests: tflite-micro interpreter == LiteRT (bit-exact), int8 vs. fp32 metrics,
                   arena size ≤ budget, C features == Python features (golden vectors)
        ↓
Firmware (ESP-IDF component) → QEMU smoke test → hardware-in-the-loop benchmark
        ↓
Hugging Face upload with model card and benchmark JSON
```

- **Classic ML first.** For CAN IDS based on timing and ID features, trees are often enough. They need
  only a few kB and run in the microsecond range. A neural network has to prove itself against this baseline.
- **Quantisation:** int8 PTQ by default, with a calibration set that **contains the rare attack classes**. QAT only
  if PTQ costs more than ~1 percentage point of F1. `tfmot` needs Keras 2, so QAT via PyTorch/PT2E or ESP-PPQ.
- **Build feature scaling into the model.** Then the firmware can pass int8 features directly from the CAN parser.

## Benchmarking

Methodology following **MLPerf Tiny**:

- Median latency over N ≥ 10 runs after warm-up, at a fixed clock frequency.
- Energy with a galvanically isolated DUT, measured with Joulescope, LPM01A or Nordic PPK2.
- Measure accuracy **on the device**.
- A dedicated "Mobility-Security-Tiny" harness with a `th_*` API, so that results are comparable.

**Metrics on the ESP32-S3:**

- Latency with `esp_timer_get_time()`, median and p99, including feature extraction.
- RAM: tensor arena plus heap; always state whether SRAM or PSRAM is used.
- Flash with `idf.py size`.
- CPU share at full bus load.

**CI without hardware:**

- **Espressif QEMU** emulates the ESP32-S3 **including TWAI/CAN**. This allows feeding CAN traces into the firmware.
  Whether the SIMD instructions are emulated is still open.
- **Renode** for STM32F4/H7 and i.MX RT.
- **Wokwi** as a GitHub Action, with a token.
- Use emulators only for functional tests, never for latency measurements.

## Hugging Face

- **One repository per model** under the organisation, following the example of the STM32 Model Zoo and Qualcomm AI Hub.
- `library_name: litert`. This is the official key for `.tflite`; there is no `tflite` key. Additionally a
  `config.json` with feature specification, window size, label map, quantisation parameters and thresholds. It also serves as
  firmware metadata.
- `pipeline_tag: tabular-classification`. An anomaly detection tag does not exist.
- Tags: `tinyml`, `tflite`, `int8`, `esp32-s3`, `stm32`, `can-bus`, `automotive`, `intrusion-detection`, `cybersecurity`.
- **Files per repo:** `README.md` (model card), `config.json`, `model_fp32.onnx`, `model_int8.tflite`,
  `model_int8.espdl`, `model_data.h`, `benchmarks/<target>.json`, `eval/results.json`, `LICENSE`.
- **Upload** with `huggingface_hub` (CLI `hf`): `create_repo`, `upload_folder`, `create_tag`. Only from CI on
  release tags, with a fine-grained org token.
- **Gating** (`extra_gated_fields`) only for sensitive artefacts such as attack generators, adversarial trace sets or
  raw captures from real vehicles. Plain IDS classifiers usually need no gating.

### Additional model card sections for security models

- **Intended Use:** defensive research, lab tests, teaching. **Not** a certified safety mechanism and no
  claim to ISO/SAE 21434 or R155.
- **Out of Scope:** in-vehicle use on public roads without validation by the OEM; active countermeasures; use as an attack oracle.
- **Threat Model:** which attacks are covered and which are not.
- **Operating Envelope:** bus, bit rate, vehicle or dataset domain, **false alarms per driving hour**.
- **Deployment Specs** per target platform: latency, RAM, flash, energy, runtime version.
- **Quantisation impact:** fp32 vs. int8 per attack class.
- **Generalisation limits:** results across vehicles and datasets.
- **Adversarial robustness:** or explicitly "not evaluated".
- **Dual-use statement:** what was withheld and why.
- **Data provenance and licence inheritance.**
- Link to `SECURITY.md` for responsible disclosure.

## Adversarial robustness

Adaptive attackers deliberately evade an ML IDS. Literature: Longari/Zanero (evasion against CAN IDS),
CANEDERLI (arXiv 2404.04648), arXiv 2506.10620 and DUET for voltage IDS.

**Protocol:**

- Evasive examples must be **valid CAN traffic**:
  - valid IDs and DLC, bytes in 0–255
  - timing ≥ physical frame time
  - the attack effect is preserved
- Pure feature-space attacks without constraints (FGSM/PGD) overestimate the vulnerability.
- **Attack the int8 model as it is deployed.**
- Attacks on trees: decision-based, HopSkipJump, MILP (via ART).
- Report robustness curves over the perturbation budget.
- Defence: **hybrid of rules and ML.** Period checks and ID allowlists cost almost nothing on the MCU and make evasion much harder.

## Repo structure (proposal for phase 1)

```text
mobility-security-ml/
├── pyproject.toml            # uv workspace
├── packages/
│   ├── msml-data/            # dataset loaders, log parsers (candump/ASC/BLF), leak-free splits
│   ├── msml-features/        # feature extraction (Python; parity with the C version)
│   ├── msml-export/          # tflite int8, onnx, espdl, emlearn, C arrays, validation
│   ├── msml-bench/           # HIL runner (th_* API), energy measurement, result schema
│   ├── msml-adv/             # adversarial evaluation with CAN constraints
│   └── msml-hub/             # model card rendering, HF upload, licence check
├── models/<model-name>/      # conf/ (Hydra), train/export/evaluate, dvc.yaml, firmware/, card/
├── firmware/components/      # ESP-IDF: msml_runtime, msml_can, msml_features, msml_bench
├── datasets/                 # download scripts, dataset cards, licence snapshots (no NC raw data in git)
├── docs/  SECURITY.md
└── .github/workflows/
```

Tools: **uv** (TF and PyTorch as separate dependency groups), **Hydra**, **DVC**, **MLflow** (self-hosted),
ESP-IDF component manager, **pytest-embedded**.

## Regulatory notes

These notes are **not verified and not legal advice**.

- **EU AI Act:** A small IDS classifier is not a general-purpose AI model. It would be high-risk only as a safety component of a
  regulated product. Open research models benefit from exemptions for research and open source. Keep the framing
  "research only, not for in-vehicle use".
- **Cyber Resilience Act:** Type-approved vehicles are exempt; R155/R156 apply to them. Free open-source software
  outside commercial activity is not covered. If we later sold firmware or dongles, obligations such as SBOM
  and vulnerability management would apply. Therefore create `SECURITY.md` from the start and generate SBOMs in CI.
