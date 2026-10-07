# Python API contract: `SpanExtractor`

Module: `mobility_model_zoo.productdev.jtbd.span`. Importable with the base install only (`torch`, `transformers`, `huggingface_hub`, `safetensors`, `sentencepiece`). This is the interface the published model card's usage example calls (feature 003 hand-over).

```python
from mobility_model_zoo.productdev.jtbd.span import SpanExtractor

model = SpanExtractor.from_pretrained(
    "mobility-model-zoo/scout-large",  # or a local directory
    revision="0.1.0",                                # tag or commit; ignored for directories
    device="cpu",                                    # default "cpu"; "cuda" and "mps" allowed
)
result = model.extract(text)  # dict, JSON-serializable, jtbd-span-v1
```

## `SpanExtractor.from_pretrained(name_or_path, revision=None, device="cpu", token=None)`

- A local directory is loaded directly; anything else is resolved with `huggingface_hub.snapshot_download(repo_id, revision=revision, token=token)`.
- Reads `span_config.json`, builds the encoder from `config.json` (no download of the base model), loads `model.safetensors` (encoder and heads) and the tokenizer from the same directory.
- Raises `ValueError` if `span_config.json` names an unknown `output_format_version` or if a head in the weights does not match the produced dimensions.
- Puts the model in eval mode; no gradients.

## `SpanExtractor.extract(text: str) -> dict`

- Accepts any length; an empty or whitespace-only string returns `{"relevant": false, "relevance_probability": 0.0, "items": [], …}`.
- Deterministic for the same files, text and device.
- Output: [span-output.schema.json](span-output.schema.json). Items are sorted by `start`.

## `SpanExtractor.extract_many(texts: list[str]) -> list[dict]`

Same as `extract` for each text; used by `jtbd span label` and `jtbd perf`.

## `SpanExtractor.save_pretrained(directory)`

Writes the files listed in [model-files.md](model-files.md). Used by `jtbd span train` and `tune`.

## Properties

- `dimensions: list[str]` — produced attribute dimensions.
- `output_format_version: str` — `jtbd-span-v1`.
