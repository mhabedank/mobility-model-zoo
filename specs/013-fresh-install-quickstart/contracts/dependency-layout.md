# Contract: dependency layout and install lines

## `pyproject.toml`

```toml
dependencies = ["huggingface_hub>=1.19", "numpy>=1.26"]

[project.optional-dependencies]
# Text models (runtime python): scout-large, sandbox-pipeline-tiny
text = ["torch>=2.4", "transformers>=4.46", "safetensors>=0.4", "sentencepiece>=0.2"]
# JTBD task tool: needs the text stack
jtbd = ["mobility-model-zoo[text]", ...unchanged...]
# Edge models (runtime mcu): the published forest is a scikit-learn object
edge = [...unchanged..., "scikit-learn>=1.5", "joblib>=1.3"]
```

`release`, `edge-hw`, `edge-train`, `catalog`, `labeling-api` unchanged. `requires-python` stays
`>=3.12`.

## Install line per runtime

| runtime | extra | models today |
|---|---|---|
| `python` | `text` | scout-large, sandbox-pipeline-tiny |
| `mcu` | `edge` | picket-forest, picket-mlp, hum-fan, pace-cnn |

`card.install` of every `model.yaml` names its extra. The gate's fresh environment is built from
this line (see gate-and-card.md), so a snippet that imports beyond its extra fails the gate.

## Guarantees

- `pip install "mobility-model-zoo[edge] @ git+...@picket-forest/v0.2.1"` installs no torch,
  transformers, pandas or tensorflow; measured install under 200 MB.
- `pip install "mobility-model-zoo[text] @ git+...@scout-large/v0.1.3"` installs what
  `productdev.jtbd.span` imports at run time.
- `uv sync --extra jtbd ...` and `uv sync --extra edge ...` in every workflow keep working;
  `--no-install-package torch` stays valid where present.
- The user-facing module `security.can_ids.picket_forest` imports, outside the standard library,
  only `numpy`, `joblib` and `sklearn` (and `huggingface_hub` nowhere: downloads happen in the
  snippet, not in the module).
