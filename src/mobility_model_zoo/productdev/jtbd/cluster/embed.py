"""Sentence embeddings of quotes and their cache (research R5, R6).

`HFEncoder` loads a multilingual encoder at a pinned revision and refuses to load without one or
without a recorded licence basis (T008); a model that needs remote code also needs a pinned
`code_revision`, because its `auto_map` may point to another repository whose code would otherwise
be loaded from `main`. `TableEncoder` gives fixed vectors from a JSON table and is
used by tests and dry runs, so nothing is downloaded there. Vectors are L2-normalised float32 rows.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from mobility_model_zoo.productdev.jtbd.cluster.bundle import normalise_quote, sha256_hex
from mobility_model_zoo.productdev.jtbd.errors import UsageError


class Encoder(Protocol):
    model_id: str
    revision: str
    variant: str

    def embed(self, quotes: list[str]) -> np.ndarray: ...


def require_pinned(settings: dict[str, Any], what: str) -> None:
    """A real model is loaded only at a pinned revision with a recorded licence basis."""
    if not settings.get("revision"):
        raise UsageError(f"{what} {settings.get('model_id')!r}: pin `revision` before use (T008)")
    if not settings.get("licence_basis"):
        raise UsageError(f"{what} {settings.get('model_id')!r}: record `licence_basis` before use "
                         "(T008)")
    if settings.get("trust_remote_code") and not settings.get("code_revision"):
        raise UsageError(f"{what} {settings.get('model_id')!r}: pin `code_revision` of the remote "
                         "code before use (T008)")


def normalise_rows(vectors: np.ndarray) -> np.ndarray:
    vectors = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / np.where(norms == 0, 1, norms)


POOLINGS = ("mean", "cls")


class HFEncoder:
    """`transformers` encoder on CPU, mean-pooled or first-token (CLS) pooled as the model expects."""

    def __init__(self, settings: dict[str, Any]):
        require_pinned(settings, "encoder")
        import torch
        from transformers import AutoModel, AutoTokenizer

        self._torch = torch
        self.model_id = settings["model_id"]
        self.revision = settings["revision"]
        self.prefix = settings.get("prefix", "")
        self.batch_size = int(settings.get("batch_size", 64))
        self.max_length = int(settings.get("max_length", 128))
        self.pooling = settings.get("pooling", "mean")
        if self.pooling not in POOLINGS:
            raise UsageError(f"encoder pooling {self.pooling!r}: use one of {', '.join(POOLINGS)}")
        remote = bool(settings.get("trust_remote_code", False))
        code = {"trust_remote_code": True, "code_revision": settings["code_revision"]} if remote else {}
        self.variant = variant_of(settings)
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id, revision=self.revision, **code)
        self.model = AutoModel.from_pretrained(self.model_id, revision=self.revision, **code).eval()

    def embed(self, quotes: list[str]) -> np.ndarray:
        torch = self._torch
        rows = []
        with torch.inference_mode():
            for i in range(0, len(quotes), self.batch_size):
                batch = [self.prefix + q for q in quotes[i:i + self.batch_size]]
                enc = self.tokenizer(batch, padding=True, truncation=True,
                                     max_length=self.max_length, return_tensors="pt")
                states = self.model(**enc).last_hidden_state
                if self.pooling == "cls":
                    rows.append(states[:, 0].float().numpy())
                    continue
                mask = enc["attention_mask"].unsqueeze(-1).to(states.dtype)
                rows.append(((states * mask).sum(1) / mask.sum(1).clamp(min=1)).float().numpy())
        dim = self.model.config.hidden_size
        return normalise_rows(np.concatenate(rows) if rows else np.zeros((0, dim)))


def variant_of(settings: dict[str, Any]) -> str:
    """Settings besides model and revision that change the vectors; part of the cache identity."""
    parts = {k: settings.get(k) for k in ("prefix", "pooling", "max_length", "code_revision")}
    if not any(parts.values()):
        return ""
    return json.dumps(parts, sort_keys=True)


class TableEncoder:
    """Fixed vectors by quote from a JSON table; other quotes get a seeded random unit vector."""

    def __init__(self, table: dict[str, list[float]], dim: int, model_id: str = "table",
                 revision: str = "fixture"):
        self.table = {normalise_quote(q): v for q, v in table.items()}
        self.dim = dim
        self.model_id = model_id
        self.revision = revision
        self.variant = ""

    @classmethod
    def from_file(cls, path: Path | str) -> TableEncoder:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(raw.get("vectors", {}), int(raw["dim"]), revision=sha256_hex(json.dumps(raw))[:12])

    def embed(self, quotes: list[str]) -> np.ndarray:
        rows = []
        for quote in quotes:
            key = normalise_quote(quote)
            if key in self.table:
                rows.append(np.asarray(self.table[key], dtype=np.float32))
            else:
                seed = int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16)
                rows.append(np.random.default_rng(seed).standard_normal(self.dim).astype(np.float32))
        return normalise_rows(np.stack(rows) if rows else np.zeros((0, self.dim)))


def make_encoder(settings: dict[str, Any], base: Path | None = None) -> Encoder:
    if settings.get("backend") == "table":
        table = Path(settings["table"])
        return TableEncoder.from_file(table if table.is_absolute() or base is None else base / table)
    return HFEncoder(settings)


class EmbeddingCache:
    """Vectors by (model, revision, normalised quote), stored in the map directory (research R6).

    A re-run embeds only new quotes; stored vectors are reused byte for byte."""

    def __init__(self, map_dir: Path | str | None, model_id: str, revision: str, variant: str = ""):
        self.vectors: dict[str, np.ndarray] = {}
        self.path: Path | None = None
        if map_dir is not None:
            name = sha256_hex(f"{model_id}@{revision}" + (f"#{variant}" if variant else ""))[:16]
            self.path = Path(map_dir) / "cache" / "embeddings" / f"{name}.npz"
            if self.path.exists():
                with np.load(self.path, allow_pickle=False) as data:
                    self.vectors = dict(zip(data["keys"].tolist(), data["vectors"], strict=True))

    @staticmethod
    def key(quote: str) -> str:
        return sha256_hex(normalise_quote(quote))

    def get(self, quotes: list[str], encoder: Encoder) -> np.ndarray:
        keys = [self.key(q) for q in quotes]
        missing: dict[str, str] = {}
        for k, q in zip(keys, quotes, strict=True):
            if k not in self.vectors and k not in missing:
                missing[k] = q
        if missing:
            new = encoder.embed(list(missing.values()))
            self.vectors.update(zip(missing, new, strict=True))
            self._save()
        if not keys:
            return np.zeros((0, 0), dtype=np.float32)
        return np.stack([self.vectors[k] for k in keys]).astype(np.float32)

    def _save(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        keys = sorted(self.vectors)
        tmp = self.path.with_suffix(".tmp.npz")
        np.savez(tmp, keys=np.array(keys), vectors=np.stack([self.vectors[k] for k in keys]))
        tmp.replace(self.path)
