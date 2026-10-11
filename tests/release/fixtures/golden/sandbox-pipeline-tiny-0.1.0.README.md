---
license: apache-2.0
language:
- de
- en
library_name: pytorch
pipeline_tag: token-classification
tags:
- mobility
- mobility-model-zoo
- sandbox
- pipeline
- experimental
- pipeline-test
model-index:
- name: sandbox-pipeline-tiny
  results:
  - task:
      type: token-classification
      name: Pipeline test model (tiny)
    dataset:
      type: synthetic
      name: synthetic (frozen)
    metrics:
    - type: item_f1
      value: 0.5
      name: Synthetic item matching F1 (test number)
---

# Pipeline test model (tiny)

**Version 0.1.0** · 2026-10-01 · status: **experimental** · topic: [Pipeline tests](https://huggingface.co/mobility-model-zoo) · task: `pipeline`

**Usage:** Commercial use permitted · licence Apache-2.0.

> **Pipeline test model.** Not for use. Never public.

## Summary

A tiny deterministic test model. It exists only to test the release pipeline and is never public.

`sandbox-pipeline-tiny` belongs to the topic **Pipeline tests** (`sandbox`), task `pipeline`, variant `tiny`.

## Intended use

Testing the release pipeline of the mobility model zoo.

## Out-of-scope use

Any real use. The model has random weights and its outputs mean nothing.

## Input and output

Input: a text. Output: JSON with one item per sentence (`kind`, `quote`, `score`).

## How to run it

```bash
pip install "mobility-model-zoo @ git+https://github.com/mhabedank/mobility-model-zoo@sandbox-pipeline-tiny/v0.1.0"
```

```python
import json

from mobility_model_zoo.sandbox.model import PipelineTestModel

model = PipelineTestModel.from_pretrained("mobility-model-zoo/sandbox-pipeline-tiny", revision="v0.1.0")
print(json.dumps(model.predict("Der Bus fährt nur zweimal am Tag. Für den Weg zur Arbeit ist das zu selten."), ensure_ascii=False, indent=2))
```

The tag `v0.1.0` always points to this version. For strict reproducibility, pin the commit hash of that tag instead (`revision="<commit>"`).

## Examples

### Example 1: `01-bus.txt`

Input:

```text
Der Bus fährt nur zweimal am Tag. Für den Weg zur Arbeit ist das zu selten.
```

Output:

```json
{"items": [], "run": "2959b92f"}
```

### Example 2: `02-bike-lanes.txt`

Input:

```text
I would cycle more if the bike lanes were separated from the road.
```

Output:

```json
{"items": [], "run": "738199a2"}
```

### Example 3: `03-delay-app.txt`

Input:

```text
Die App zeigt die Verspätung erst an, wenn ich schon am Bahnsteig stehe.
```

Output:

```json
{"items": [], "run": "07389382"}
```

## Quality

These numbers are agreement with none (synthetic test numbers); they are not measured against human ground truth. Benchmark: `synthetic`. **Synthetic test numbers.**

| Metric | Value | What it measures | Reference | Benchmark | Items | Date |
|--------|-------|------------------|-----------|-----------|-------|------|
| `item_f1` | 0.5 | Synthetic item matching F1 (test number) | none (synthetic) | synthetic | 3 | 2026-10-01 |

## Speed and memory

Budget: 1 GB RAM, no GPU. Measured on: GitHub-hosted ubuntu-latest runner, CPU. **Synthetic test numbers.**

| Metric | Value | Unit | What it measures | Hardware | Items | Date |
|--------|-------|------|------------------|----------|-------|------|
| `seconds_per_text` | 0.01 | s | Synthetic time per example text (test number) | GitHub-hosted ubuntu-latest runner, CPU | 3 | 2026-10-01 |
| `peak_memory_mb` | 300 | MB | Synthetic peak memory (test number) | GitHub-hosted ubuntu-latest runner, CPU | 3 | 2026-10-01 |

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

| Version | Date | Status | Change | Changes | `item_f1` |
|---------|------|--------|--------|---------|------|
| 0.1.0 | 2026-10-01 | experimental | initial | First test release. | 0.5 |

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
