"""JTBD span extractor (feature 004). Importable with the base install only.

    from mobility_model_zoo.productdev.jtbd.span import SpanExtractor

    model = SpanExtractor.from_pretrained("mobility-model-zoo/productdev-jtbd-span-xlmr",
                                          revision="0.1.0")
    model.extract(text)

Training, rows, tuning, evaluation and the `jtbd span` commands live in sibling modules that
need the `[jtbd]` extra; they are never imported here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mobility_model_zoo.productdev.jtbd.span.extractor import SpanExtractor

__all__ = ["SpanExtractor"]


def __getattr__(name: str):
    # Lazy, so `jtbd` commands that never load a model do not import torch.
    if name == "SpanExtractor":
        from mobility_model_zoo.productdev.jtbd.span.extractor import SpanExtractor

        return SpanExtractor
    raise AttributeError(name)
