"""`PipelineTestModel`: a tiny, deterministic model that exercises the release pipeline.

It has random weights from a fixed seed. Its output has a realistic shape (one item per sentence
with kind, quote and score), but means nothing. It is not a spike model and is never public.
"""

from __future__ import annotations

import re

import torch
from huggingface_hub import PyTorchModelHubMixin
from torch import nn

KINDS = ["job", "pain", "gain"]
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


class PipelineTestModel(
    nn.Module,
    PyTorchModelHubMixin,
    library_name="pytorch",
    tags=["mobility-model-zoo", "sandbox"],
    license="apache-2.0",
):
    def __init__(self, vocab: int = 256, dim: int = 8, seed: int = 0):
        super().__init__()
        generator = torch.Generator().manual_seed(seed)
        self.embed = nn.Embedding(vocab, dim)
        self.head = nn.Linear(dim, len(KINDS) + 1)
        with torch.no_grad():
            self.embed.weight.copy_(torch.randn(vocab, dim, generator=generator))
            self.head.weight.copy_(torch.randn(len(KINDS) + 1, dim, generator=generator))
            self.head.bias.zero_()
        self.vocab = vocab

    def forward(self, byte_ids: torch.Tensor) -> torch.Tensor:
        return self.head(self.embed(byte_ids).mean(dim=0))

    @torch.no_grad()
    def predict(self, text: str) -> dict:
        items = []
        for sentence in (s.strip() for s in SENTENCE_END.split(text)):
            if not sentence:
                continue
            ids = torch.tensor(list(sentence.encode("utf-8")), dtype=torch.long) % self.vocab
            probs = torch.softmax(self(ids), dim=-1)
            best = int(probs.argmax())
            if best < len(KINDS):
                items.append(
                    {"kind": KINDS[best], "quote": sentence, "score": round(float(probs[best]), 2)}
                )
        return {"model": "sandbox-pipeline-tiny", "items": items}
