---
license: apache-2.0
language: []
library_name: sklearn
pipeline_tag: tabular-classification
tags:
- mobility
- mobility-model-zoo
- sandbox
- pipeline
- experimental
- tinyml
- microcontroller
- ESP32-S3
- pipeline-test
model-index:
- name: edge-fixture-forest
  results:
  - task:
      type: tabular-classification
      name: Edge pipeline test model (forest)
    dataset:
      type: synthetic
      name: synthetic (frozen)
    metrics:
    - type: int8_accuracy
      value: 0.5
      name: Synthetic share of correct classes (test number)
---

# Edge pipeline test model (forest)

**Version 0.1.0** · 2026-10-08 · status: **experimental** · topic: [Pipeline tests](https://huggingface.co/mobility-model-zoo) · task: `pipeline`

**Usage:** Commercial use permitted · licence Apache-2.0.

> **Pipeline test model.** Not for use. Never public.

## Summary

A tiny deterministic random forest exported to C. It exists only to test the release pipeline for microcontroller models and is never public.

`edge-fixture-forest` belongs to the topic **Pipeline tests** (`sandbox`), task `pipeline`, variant `forest`. Trained from scratch.

## Intended use

Testing the release pipeline of the mobility model zoo for microcontroller models.

## Out-of-scope use

Any real use. The model has random weights and its outputs mean nothing.

## Input and output

Input: CAN frames in bus order. Output: an attack score per frame and an alarm flag.

## How to run it

Requires Python 3.12 or newer.

```bash
pip install "mobility-model-zoo[edge] @ git+https://github.com/mhabedank/mobility-model-zoo@edge-fixture-forest/v0.1.0"
```

```python
import joblib
from huggingface_hub import hf_hub_download

saved = joblib.load(hf_hub_download("mobility-model-zoo/edge-fixture-forest", "model.joblib", revision="v0.1.0"))
print(saved["threshold"])
```

On the device (C, tree model exported with emlearn; build with `-ffp-contract=off`):

```c
/* Sources and generated headers from mobility-model-zoo/edge-fixture-forest at v0.1.0. */
#include "picket_forest.h"

static picket_forest_t ids;
picket_forest_init(&ids);
float score;
int alarm = picket_forest_process(&ids, ts_us, can_id, dlc, data, &score);
```

The tag `v0.1.0` always points to this version. For strict reproducibility, pin the commit hash of that tag instead (`revision="<commit>"`).

## Examples

### Example 1: `01-dos.json`

Source: synthetic (dos attack). 600 CAN frames in bus order; the detector raises 1 alarm, at frame 241. First five frames:

| Time (µs) | ID | DLC | Data |
|-----------|----|-----|------|
| 0 | 0x162 | 8 | 00 BF 5F 10 00 00 62 90 |
| 21 | 0x177 | 8 | 00 82 41 10 00 00 77 4A |
| 1013 | 0x6AD | 8 | 00 94 4A 10 00 00 AD 9B |
| 4371 | 0x583 | 8 | 00 C9 64 10 00 00 83 C0 |
| 10123 | 0x177 | 8 | 01 84 42 10 00 00 77 4E |

The full example with the expected score of every frame is `examples/01-dos.json` in the repository; the release gate reproduces every score and alarm bit-exactly with the C code of this release.

### Example 2: `02-fuzzing.json`

Source: synthetic (fuzzing attack). 600 CAN frames in bus order; the detector raises 1 alarm, at frame 199. First five frames:

| Time (µs) | ID | DLC | Data |
|-----------|----|-----|------|
| 0 | 0x3BA | 8 | 00 94 4A 10 00 00 BA A8 |
| 4928 | 0x465 | 8 | 00 AA 55 10 00 00 65 74 |
| 5833 | 0x0AF | 8 | 00 53 29 10 00 00 AF 3B |
| 7133 | 0x51D | 8 | 00 56 2B 10 00 00 1D AE |
| 8290 | 0x688 | 8 | 00 1B 0D 10 00 00 88 C0 |

The full example with the expected score of every frame is `examples/02-fuzzing.json` in the repository; the release gate reproduces every score and alarm bit-exactly with the C code of this release.

### Example 3: `03-scan.json`

Source: synthetic (scan attack). 600 CAN frames in bus order; the detector raises 1 alarm, at frame 4. First five frames:

| Time (µs) | ID | DLC | Data |
|-----------|----|-----|------|
| 0 | 0x0EA | 8 | 00 66 33 10 00 00 EA 93 |
| 2842 | 0x69F | 8 | 00 0F 07 10 00 00 9F C5 |
| 5151 | 0x21E | 8 | 00 10 08 10 00 00 1E 46 |
| 5234 | 0x1A9 | 8 | 00 1A 0D 10 00 00 A9 E0 |
| 5867 | 0x474 | 8 | 00 68 34 10 00 00 74 20 |

The full example with the expected score of every frame is `examples/03-scan.json` in the repository; the release gate reproduces every score and alarm bit-exactly with the C code of this release.

## Quality

Quality is measured against the labels of the datasets named below, on test data not used for training. Reference: synthetic labels (test numbers). Benchmark: `synthetic`. **Synthetic test numbers.**

| Metric | Value | What it measures | Reference | Benchmark | Items | Date |
|--------|-------|------------------|-----------|-----------|-------|------|
| `int8_accuracy` | 0.5 | Synthetic share of correct classes (test number) | synthetic labels | synthetic | 3 | 2026-10-08 |

## Speed and memory

Budget: 16 KB RAM, 64 KB flash on ESP32-S3. **Synthetic test numbers.**

| Metric | Value | Unit | What it measures | Measured on | Items | Date |
|--------|-------|------|------------------|-------------|-------|------|
| `latency_us` | 12 | us | Synthetic median latency (test number) | ESP32 in QEMU, 240 MHz (emulator) | 3 | 2026-10-08 |
| `flash_kb` | 1.5 | KiB | Synthetic flash (test number) | host simulator (simulator) | None | 2026-10-08 |
| `ram_kb` | 0.2 | KiB | Synthetic RAM (test number) | host simulator (simulator) | None | 2026-10-08 |

## Limitations and risks

Random weights. The outputs are deterministic but meaningless.

## Training data provenance

No training sources: this is a synthetic pipeline test model.

The training data itself is not published. Datasets stay internal so that the people who wrote the source texts are protected and source terms are respected (project constitution, Principle VI); the model, the method, the prompts and the evaluation results are published.

## Training recipe

- Recipe: [docs/adding-a-model.md](https://github.com/mhabedank/mobility-model-zoo/blob/<git-commit>/docs/adding-a-model.md)
- Configuration: [src/mobility_model_zoo/sandbox/build_test_model.py](https://github.com/mhabedank/mobility-model-zoo/blob/<git-commit>/src/mobility_model_zoo/sandbox/build_test_model.py)
- Commit: `<git-commit>`

## Version history

| Version | Date | Status | Change | Changes | `int8_accuracy` |
|---------|------|--------|--------|---------|------|
| 0.1.0 | 2026-10-08 | experimental | initial | First test release. | 0.5 |

## License

Apache-2.0
Commercial use permitted · licence Apache-2.0.

## Citation

```bibtex
@misc{mobility-model-zoo,
  title  = {mobility-model-zoo},
  author = {Habedank, Martin},
  year   = {2026},
  url    = {https://huggingface.co/mobility-model-zoo}
}
```

## About the zoo

Part of [mobility-model-zoo](https://huggingface.co/mobility-model-zoo), a collection of small, fast mobility models grouped by topic. Topic collection: [Pipeline tests](https://huggingface.co/mobility-model-zoo). Source code, recipes and release records: [https://github.com/mhabedank/mobility-model-zoo](https://github.com/mhabedank/mobility-model-zoo).
