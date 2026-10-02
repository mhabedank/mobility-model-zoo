"""SpanTagger: a multilingual encoder with unit, BIO, relevance and attribute heads (research R6).

Inference half of the span model: `torch` and `transformers` only. Head tensors are stored under
the prefix `heads.` (contracts/model-files.md). Attribute heads exist only for the dimensions the
model produces; a dimension that failed the pilot has no head.
"""

from __future__ import annotations

import torch
from torch import nn

KINDS = ["job", "pain", "gain"]
UNIT_LABELS = ["O", *KINDS]
BIO_LABELS = ["O"] + [f"{p}-{k}" for k in KINDS for p in ("B", "I")]
ATTRIBUTE_LABELS: dict[str, list[str]] = {
    "actor_type": ["individual", "worker", "organization", "public_sector", "society"],
    "evidence_type": ["opinion", "anecdote", "routine", "observation", "measurement"],
    "evidence_scope": ["single", "multiple", "quantified"],
}


class SpanTagger(nn.Module):
    def __init__(self, encoder: nn.Module, dimensions: dict[str, list[str]]):
        super().__init__()
        unknown = set(dimensions) - set(ATTRIBUTE_LABELS)
        if unknown:
            raise ValueError(f"unknown attribute dimensions: {sorted(unknown)}")
        self.encoder = encoder
        hidden = encoder.config.hidden_size
        self.dimensions = {d: list(dimensions[d]) for d in ATTRIBUTE_LABELS if d in dimensions}
        self.dropout = nn.Dropout(0.1)
        self.heads = nn.ModuleDict({
            "bio": nn.Linear(hidden, len(BIO_LABELS)),
            "relevance": nn.Linear(hidden, 1),
            "unit": nn.Linear(hidden, len(UNIT_LABELS)),
            "attrs": nn.ModuleDict({d: nn.Linear(hidden, len(labels))
                                    for d, labels in self.dimensions.items()}),
        })

    @classmethod
    def from_config(cls, config, dimensions: dict[str, list[str]]) -> SpanTagger:
        """Random-initialised encoder from a `transformers` config (weights are loaded later)."""
        from transformers import AutoModel

        return cls(AutoModel.from_config(config), dimensions)

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor):
        """Token states, BIO logits per token and the relevance logit per window."""
        states = self.encoder(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state
        states = self.dropout(states)
        return states, self.heads["bio"](states), self.heads["relevance"](states[:, 0]).squeeze(-1)

    def unit_logits(self, pooled: torch.Tensor) -> torch.Tensor:
        return self.heads["unit"](pooled)

    def attribute_logits(self, pooled: torch.Tensor) -> dict[str, torch.Tensor]:
        return {d: head(pooled) for d, head in self.heads["attrs"].items()}
