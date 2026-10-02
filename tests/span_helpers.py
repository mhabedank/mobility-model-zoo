"""A tiny random span model built without network access (feature 004, T011).

Encoder: XLM-RoBERTa architecture with hidden size 32, 2 layers, 2 heads. Tokenizer: a word-level
tokenizer trained on a few German and English sentences, with offsets. Weights are random with a
fixed seed, so outputs are deterministic but meaningless.
"""

from __future__ import annotations

from pathlib import Path

import torch

from mobility_model_zoo.productdev.jtbd.span.extractor import SpanExtractor, default_config
from mobility_model_zoo.productdev.jtbd.span.model import ATTRIBUTE_LABELS, SpanTagger

SENTENCES = [
    "Im Landkreis fährt der letzte Bus um 18 Uhr.",
    "Wer abends aus der Stadt zurück will, muss ein Taxi nehmen.",
    "Ich pendle jeden Tag 40 Kilometer zur Arbeit, weil es keine andere Verbindung gibt.",
    "The charger at the depot was broken again; we lost two hours.",
    "Drivers want to plan their breaks around charging.",
    "63% of respondents said the app is too slow.",
]

ALL = tuple(ATTRIBUTE_LABELS)


def tiny_tokenizer():
    from tokenizers import Tokenizer, models, pre_tokenizers, trainers
    from transformers import PreTrainedTokenizerFast

    tok = Tokenizer(models.WordLevel(unk_token="<unk>"))
    tok.pre_tokenizer = pre_tokenizers.Whitespace()
    trainer = trainers.WordLevelTrainer(special_tokens=["<s>", "<pad>", "</s>", "<unk>"])
    tok.train_from_iterator(SENTENCES, trainer)
    return PreTrainedTokenizerFast(
        tokenizer_object=tok, bos_token="<s>", eos_token="</s>", cls_token="<s>",
        sep_token="</s>", pad_token="<pad>", unk_token="<unk>")


def tiny_extractor(dimensions: tuple[str, ...] = ALL, seed: int = 7,
                   thresholds: dict | None = None) -> SpanExtractor:
    from transformers import XLMRobertaConfig

    tokenizer = tiny_tokenizer()
    config = XLMRobertaConfig(
        vocab_size=len(tokenizer), hidden_size=32, num_hidden_layers=2, num_attention_heads=2,
        intermediate_size=64, max_position_embeddings=520, pad_token_id=tokenizer.pad_token_id,
        bos_token_id=tokenizer.bos_token_id, eos_token_id=tokenizer.eos_token_id)
    torch.manual_seed(seed)
    model = SpanTagger.from_config(config, {d: ATTRIBUTE_LABELS[d] for d in dimensions})
    extra = {"model": "tiny-fixture"}
    if thresholds is not None:
        extra["thresholds"] = thresholds
    return SpanExtractor(model, tokenizer, default_config(**extra))


def build_tiny_model(directory: Path, dimensions: tuple[str, ...] = ALL, seed: int = 7,
                     thresholds: dict | None = None) -> Path:
    # Low thresholds so the random model returns items to check.
    tiny_extractor(dimensions, seed, thresholds or {"unit": 0.0, "relevance": 0.0}) \
        .save_pretrained(directory)
    return directory
