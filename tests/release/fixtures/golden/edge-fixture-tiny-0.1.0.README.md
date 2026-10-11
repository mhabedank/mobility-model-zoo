---
license: apache-2.0
language: []
library_name: litert
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
- name: edge-fixture-tiny
  results:
  - task:
      type: tabular-classification
      name: Edge pipeline test model (tiny)
    dataset:
      type: synthetic
      name: synthetic (frozen)
    metrics:
    - type: int8_accuracy
      value: 0.5
      name: Synthetic share of correct classes (test number)
---

# Edge pipeline test model (tiny)

**Version 0.1.0** · 2026-10-08 · status: **experimental** · topic: [Pipeline tests](https://huggingface.co/mobility-model-zoo) · task: `pipeline`

**Usage:** Commercial use permitted · licence Apache-2.0.

> **Pipeline test model.** Not for use. Never public.

## Summary

A tiny deterministic int8 model. It exists only to test the release pipeline for microcontroller models and is never public.

`edge-fixture-tiny` belongs to the topic **Pipeline tests** (`sandbox`), task `pipeline`, variant `tiny`. Trained from scratch.

## Intended use

Testing the release pipeline of the mobility model zoo for microcontroller models.

## Out-of-scope use

Any real use. The model has random weights and its outputs mean nothing.

## Input and output

Input: 8 int8 values. Output: 2 int8 scores.

## How to run it

```bash
pip install "mobility-model-zoo[edge] @ git+https://github.com/mhabedank/mobility-model-zoo@edge-fixture-tiny/v0.1.0"
```

```python
from huggingface_hub import hf_hub_download

from mobility_model_zoo.edge.int8.model import QModel
from mobility_model_zoo.edge.int8.reference import run_model

model = QModel.load(hf_hub_download("mobility-model-zoo/edge-fixture-tiny", "model.npz", revision="v0.1.0"))
print(run_model(model, [0, 1, 2, 3, 4, 5, 6, 7]).tolist())
```

On the device (C, int8 engine of the zoo):

```c
/* Sources generated from mobility-model-zoo/edge-fixture-tiny at v0.1.0: `uv run edge build`. */
#include "model_zoo.h"

static int8_t arena[MI_ZOO_ARENA_SIZE];
int8_t in[8] = {0, 1, 2, 3, 4, 5, 6, 7}, out[2];
mi_invoke(&mi_model_edge_fixture_tiny, in, out, arena, sizeof arena);
```

The tag `v0.1.0` always points to this version. For strict reproducibility, pin the commit hash of that tag instead (`revision="<commit>"`).

## Examples

### Example 1: `01-random.json`

Source: synthetic. Input (8 int8 values):

```json
[-21, 94, 118, -55, -99, 26, 42, 71]
```

Expected output (bit-exact on the host reference and on the device):

```json
[-90, 18]
```

### Example 2: `02-random.json`

Source: synthetic. Input (8 int8 values):

```json
[36, 55, 106, 106, 109, 92, 56, 107]
```

Expected output (bit-exact on the host reference and on the device):

```json
[-36, -36]
```

### Example 3: `03-random.json`

Source: synthetic. Input (8 int8 values):

```json
[-125, -122, 76, -17, 63, -4, 102, -112]
```

Expected output (bit-exact on the host reference and on the device):

```json
[62, 54]
```

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
