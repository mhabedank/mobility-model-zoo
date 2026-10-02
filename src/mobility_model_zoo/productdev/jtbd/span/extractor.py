"""SpanExtractor: load a span model and extract jobs, pains and gains (contracts/python-api.md).

Inference half of the span model: standard library, `torch`, `transformers`, `huggingface_hub`
and `safetensors` only, so the base install is enough to run a published model.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import torch

from mobility_model_zoo.productdev.jtbd.span.model import (
    ATTRIBUTE_LABELS,
    BIO_LABELS,
    KINDS,
    UNIT_LABELS,
    SpanTagger,
)
from mobility_model_zoo.productdev.jtbd.span.units import (
    MAX_LENGTH,
    STRIDE,
    UNIT_SPLIT,
    unit_token_index,
    units,
    windows,
)

OUTPUT_FORMAT_VERSION = "jtbd-span-v1"
CONFIG_FILE = "span_config.json"
WEIGHTS_FILE = "model.safetensors"
# Every file a model directory may contain (contracts/model-files.md).
MODEL_FILES = frozenset({
    WEIGHTS_FILE, "config.json", CONFIG_FILE, "tokenizer.json", "tokenizer_config.json",
    "special_tokens_map.json", "sentencepiece.bpe.model",
})
SCORE_DIGITS = 4
# The jtbd-span-v1 JSON Schema (validated by `jtbd check`; not needed at inference time).
SCHEMA_PATH = Path(__file__).with_name("jtbd-span-v1.schema.json")


class SpanExtractor:
    def __init__(self, model: SpanTagger, tokenizer: Any, config: dict[str, Any],
                 device: str = "cpu"):
        self.model = model.to(device).eval()
        self.tokenizer = tokenizer
        self.config = config
        self.device = device

    # ---- loading and saving ----------------------------------------------------------------------
    @classmethod
    def from_pretrained(cls, name_or_path: str | Path, revision: str | None = None,
                        device: str = "cpu", token: str | None = None) -> SpanExtractor:
        directory = Path(name_or_path)
        if not directory.is_dir():
            from huggingface_hub import snapshot_download

            directory = Path(snapshot_download(str(name_or_path), revision=revision, token=token))
        config = json.loads((directory / CONFIG_FILE).read_text(encoding="utf-8"))
        version = config.get("output_format_version")
        if version != OUTPUT_FORMAT_VERSION:
            raise ValueError(f"unknown output_format_version {version!r} in {CONFIG_FILE}")
        if config.get("unit_labels") != UNIT_LABELS or config.get("bio_labels") != BIO_LABELS:
            raise ValueError(f"{CONFIG_FILE} has label sets this code does not know")
        dimensions = config.get("dimensions") or {}
        for name, labels in dimensions.items():
            if ATTRIBUTE_LABELS.get(name) != labels:
                raise ValueError(f"{CONFIG_FILE} has unknown labels for dimension {name!r}")

        from safetensors.torch import load_file
        from transformers import AutoConfig, AutoTokenizer

        model = SpanTagger.from_config(AutoConfig.from_pretrained(directory), dimensions)
        state = load_file(str(directory / WEIGHTS_FILE))
        heads = {k.split(".")[2] for k in state if k.startswith("heads.attrs.")}
        if heads != set(model.dimensions):
            raise ValueError(f"attribute heads in {WEIGHTS_FILE} {sorted(heads)} do not match the "
                             f"dimensions in {CONFIG_FILE} {sorted(model.dimensions)}")
        try:
            model.load_state_dict(state, strict=True)
        except RuntimeError as exc:
            raise ValueError(f"{WEIGHTS_FILE} does not match the model: {exc}") from exc
        return cls(model, AutoTokenizer.from_pretrained(directory), config, device)

    def save_pretrained(self, directory: str | Path) -> None:
        """Write the files of contracts/model-files.md, and nothing else."""
        import shutil
        import tempfile

        from safetensors.torch import save_file

        out = Path(directory)
        out.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            staging = Path(tmp)
            state = {k: v.detach().cpu().contiguous() for k, v in self.model.state_dict().items()}
            save_file(state, str(staging / WEIGHTS_FILE), metadata={"format": "pt"})
            self.model.encoder.config.save_pretrained(staging)
            self.tokenizer.save_pretrained(staging)
            config = {**self.config, "output_format_version": OUTPUT_FORMAT_VERSION,
                      "unit_labels": UNIT_LABELS, "bio_labels": BIO_LABELS,
                      "dimensions": self.model.dimensions}
            (staging / CONFIG_FILE).write_text(
                json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            # Library extras (for example a chat template) are not part of the model files.
            for path in staging.iterdir():
                if path.name in MODEL_FILES:
                    shutil.move(str(path), out / path.name)

    # ---- properties --------------------------------------------------------------------------------
    @property
    def dimensions(self) -> list[str]:
        return list(self.model.dimensions)

    @property
    def output_format_version(self) -> str:
        return OUTPUT_FORMAT_VERSION

    @property
    def thresholds(self) -> dict[str, float]:
        values = self.config.get("thresholds") or {}
        return {"unit": float(values.get("unit", 0.5)),
                "relevance": float(values.get("relevance", values.get("unit", 0.5)))}

    @property
    def window_settings(self) -> tuple[int, int]:
        values = self.config.get("windows") or {}
        return int(values.get("max_length", MAX_LENGTH)), int(values.get("stride", STRIDE))

    # ---- extraction ----------------------------------------------------------------------------------
    def extract(self, text: str) -> dict[str, Any]:
        """Relevance and items of `text` (any length) in the jtbd-span-v1 format."""
        result: dict[str, Any] = {"output_format_version": OUTPUT_FORMAT_VERSION,
                                  "relevant": False, "relevance_probability": 0.0,
                                  "dimensions": self.dimensions, "items": []}
        if not text.strip():
            return result
        scored, relevance_probability = self.score_units(text)
        threshold = self.thresholds
        kept = [u for u in scored if u["score"] >= threshold["unit"]]
        relevant = max((u["score"] for u in kept), default=0.0) >= threshold["relevance"]
        result["relevant"] = relevant
        result["relevance_probability"] = round(relevance_probability, SCORE_DIGITS)
        if relevant:
            result["items"] = [
                {"kind": u["kind"], "quote": text[u["start"]:u["end"]], "start": u["start"],
                 "end": u["end"], "score": round(u["score"], SCORE_DIGITS),
                 **{d: u[d] for d in self.dimensions}}
                for u in kept
            ]
        return result

    def extract_many(self, texts: list[str]) -> list[dict[str, Any]]:
        return [self.extract(text) for text in texts]

    @torch.inference_mode()
    def score_units(self, text: str, batch_size: int = 8) -> tuple[list[dict[str, Any]], float]:
        """Every unit of `text` with its item score, kind and attributes, plus the mean
        probability of the relevance head. Token states are averaged over overlapping windows."""
        max_length, stride = self.window_settings
        enc = windows(self.tokenizer, text, max_length, stride)
        sums: dict[tuple[int, int], list] = {}
        relevance: list[float] = []
        for b in range(0, len(enc["input_ids"]), batch_size):
            ids = torch.tensor(enc["input_ids"][b:b + batch_size], device=self.device)
            mask = torch.tensor(enc["attention_mask"][b:b + batch_size], device=self.device)
            states, _, rel = self.model(ids, mask)
            states = states.float().cpu()
            relevance += torch.sigmoid(rel.float()).cpu().tolist()
            for w in range(ids.shape[0]):
                for t, (s, e) in enumerate(enc["offset_mapping"][b + w]):
                    if e <= s:
                        continue  # special or padding token
                    entry = sums.setdefault((s, e), [0, None])
                    entry[0] += 1
                    entry[1] = states[w, t] if entry[1] is None else entry[1] + states[w, t]
        tokens = sorted(sums)
        mapping = unit_token_index(units(text), tokens)
        if not mapping:
            return [], sum(relevance) / max(len(relevance), 1)
        pooled = torch.stack([
            torch.stack([sums[tokens[i]][1] / sums[tokens[i]][0] for i in idx]).mean(0)
            for _, idx in mapping
        ]).to(self.device)
        unit_probs = self.model.unit_logits(pooled).softmax(-1).float().cpu()
        attrs = {d: logits.argmax(-1).cpu().tolist()
                 for d, logits in self.model.attribute_logits(pooled).items()}
        scored = []
        for n, ((a, b), _) in enumerate(mapping):
            probs = unit_probs[n]
            scored.append({
                "start": a, "end": b, "score": 1.0 - float(probs[0]),
                "kind": KINDS[int(probs[1:].argmax())],
                **{d: self.model.dimensions[d][attrs[d][n]] for d in self.model.dimensions},
            })
        return scored, sum(relevance) / len(relevance)


def default_config(**extra: Any) -> dict[str, Any]:
    """The span_config.json fields every model has; training adds its own fields via `extra`."""
    return {"output_format_version": OUTPUT_FORMAT_VERSION, "unit_labels": UNIT_LABELS,
            "bio_labels": BIO_LABELS, "windows": {"max_length": MAX_LENGTH, "stride": STRIDE},
            "unit_split": UNIT_SPLIT, "thresholds": {"unit": 0.5, "relevance": 0.5}, **extra}
