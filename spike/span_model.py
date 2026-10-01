"""Encoder span model for JTBD extraction (spike, attempt 4: a fast non-generative architecture).

One forward pass per 512-token window instead of generating JSON token by token:
- the text is split into sentences and clauses (units); a unit head decides for each unit whether
  it is a job, pain, gain or no item (items are almost always whole sentences or clauses); a BIO
  token head is trained alongside as an auxiliary task,
- three heads classify each span's actor type, evidence type and evidence scope from the mean of
  its token states,
- a relevance head on the first token decides whether the chunk is relevant at all.
Quotes are always verbatim, because they are character spans of the input. The model produces no
free-text actor or English statement.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import torch
from torch import nn

KINDS = ["job", "pain", "gain"]
UNIT_LABELS = ["O", *KINDS]
BIO = ["O"] + [f"{p}-{k}" for k in KINDS for p in ("B", "I")]
ATTRS = {
    "actor_type": ["individual", "worker", "organization", "public_sector", "society"],
    "evidence_type": ["opinion", "anecdote", "routine", "observation", "measurement"],
    "evidence_scope": ["single", "multiple", "quantified"],
}
MAX_LENGTH, STRIDE = 512, 128
MIN_SPAN_TOKENS = 3
UNIT_THRESHOLD = 0.5  # probability that a unit is an item (unit head), or BIO mass (token models)
# Sentence and clause ends: . ! ? ; followed by whitespace, or a blank line. A single line break
# is not an end, because PDF text breaks lines inside sentences.
UNIT_END = re.compile(r"(?<=[.!?;])\s+|\n\s*\n")


def units(text: str) -> list[tuple[int, int]]:
    """Sentence and clause spans of `text` (character offsets, whitespace trimmed)."""
    spans, start = [], 0
    for m in [*UNIT_END.finditer(text), None]:
        end = m.start() if m else len(text)
        a, b = start, end
        while a < b and text[a].isspace():
            a += 1
        while b > a and text[b - 1].isspace():
            b -= 1
        if b > a:
            spans.append((a, b))
        if m:
            start = m.end()
    return spans


class SpanTagger(nn.Module):
    def __init__(self, encoder_name: str, encoder=None, context: bool = False):
        super().__init__()
        from transformers import AutoModel

        self.encoder = encoder or AutoModel.from_pretrained(encoder_name)
        hidden = self.encoder.config.hidden_size
        # With context, a unit is seen together with its neighbours and the document (window).
        self.context = context
        head_in = 4 * hidden if context else hidden
        self.dropout = nn.Dropout(0.1)
        self.bio = nn.Linear(hidden, len(BIO))
        self.attrs = nn.ModuleDict({a: nn.Linear(head_in, len(v)) for a, v in ATTRS.items()})
        self.relevance = nn.Linear(hidden, 1)
        self.unit = nn.Linear(head_in, len(UNIT_LABELS))
        self.task = "unit"
        self.threshold = UNIT_THRESHOLD
        self.relevance_threshold = UNIT_THRESHOLD

    def features(self, unit_vectors: torch.Tensor, doc: torch.Tensor) -> torch.Tensor:
        """Head input for a sequence of unit vectors [n, hidden] in text order."""
        if not self.context:
            return unit_vectors
        zero = torch.zeros_like(unit_vectors[:1])
        prev = torch.cat([zero, unit_vectors[:-1]])
        nxt = torch.cat([unit_vectors[1:], zero])
        return torch.cat([unit_vectors, prev, nxt, doc.expand_as(unit_vectors)], dim=-1)

    def forward(self, input_ids, attention_mask):
        states = self.encoder(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state
        states = self.dropout(states)
        return states, self.bio(states), self.relevance(states[:, 0]).squeeze(-1)

    def classify(self, pooled: torch.Tensor) -> dict[str, torch.Tensor]:
        return {a: head(pooled) for a, head in self.attrs.items()}


def save(model: SpanTagger, tokenizer, encoder_name: str, out: Path, meta: dict) -> None:
    out.mkdir(parents=True, exist_ok=True)
    model.encoder.save_pretrained(out / "encoder")
    tokenizer.save_pretrained(out / "encoder")
    heads = {k: v for k, v in model.state_dict().items() if not k.startswith("encoder.")}
    torch.save(heads, out / "heads.pt")
    (out / "span_model.json").write_text(json.dumps(
        {"encoder_name": encoder_name, "task": model.task, "context": model.context, "bio": BIO,
         "unit_labels": UNIT_LABELS,
         "unit_threshold": model.threshold, "relevance_threshold": model.relevance_threshold,
         "attrs": ATTRS, **meta}, indent=2) + "\n")


def load(path: Path, device: str = "cpu") -> tuple[SpanTagger, object]:
    from transformers import AutoModel, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(path / "encoder")
    encoder = AutoModel.from_pretrained(path / "encoder")
    meta = json.loads((path / "span_model.json").read_text())
    model = SpanTagger("", encoder=encoder, context=meta.get("context", False))
    model.load_state_dict(torch.load(path / "heads.pt", map_location="cpu"), strict=False)
    model.task = meta.get("task", "token")
    model.threshold = meta.get("unit_threshold", UNIT_THRESHOLD)
    model.relevance_threshold = meta.get("relevance_threshold", model.threshold)
    return model.to(device).eval(), tokenizer


def windows(tokenizer, text: str) -> dict[str, torch.Tensor]:
    """Overlapping windows of MAX_LENGTH tokens (STRIDE tokens overlap) covering all of `text`.

    Built by hand: transformers 5 `return_overflowing_tokens` stops after two windows and drops
    the rest of longer texts. Special and padding tokens get the offset (0, 0).
    """
    enc = tokenizer(text, add_special_tokens=False, return_offsets_mapping=True)
    ids, offsets = enc["input_ids"], enc["offset_mapping"]
    size = MAX_LENGTH - 2  # room for <s> and </s>
    starts = list(range(0, max(len(ids) - STRIDE, 1), size - STRIDE)) or [0]
    rows = {"input_ids": [], "attention_mask": [], "offset_mapping": []}
    for start in starts:
        part = ids[start:start + size]
        span = [tuple(o) for o in offsets[start:start + size]]
        pad = MAX_LENGTH - len(part) - 2
        rows["input_ids"].append([tokenizer.cls_token_id, *part, tokenizer.sep_token_id]
                                 + [tokenizer.pad_token_id] * pad)
        rows["attention_mask"].append([1] * (len(part) + 2) + [0] * pad)
        rows["offset_mapping"].append([(0, 0), *span, (0, 0)] + [(0, 0)] * pad)
    return {k: torch.tensor(v) for k, v in rows.items()}


@dataclass
class Span:
    start: int
    end: int
    kind: str
    actor_type: str
    evidence_type: str
    evidence_scope: str
    score: float


@torch.no_grad()
def predict(model: SpanTagger, tokenizer, text: str, device: str = "cpu",
            batch_size: int = 8, decode: str = "unit") -> tuple[bool, float, list[Span]]:
    """Relevance, its probability and the item spans of `text` (any length).

    decode="unit": each sentence or clause becomes an item when its tokens' mean job/pain/gain
    probability reaches UNIT_THRESHOLD (items are almost always whole sentences or clauses).
    decode="token": contiguous B/I token runs become items.
    """
    enc = windows(tokenizer, text)
    offsets = enc["offset_mapping"]
    # Average token states and BIO probabilities over overlapping windows, keyed by char offsets.
    token_state: dict[tuple[int, int], list] = {}
    rel_probs, cls_states = [], []
    for b in range(0, len(enc["input_ids"]), batch_size):
        ids = enc["input_ids"][b:b + batch_size].to(device)
        mask = enc["attention_mask"][b:b + batch_size].to(device)
        states, bio, rel = model(ids, mask)
        probs = bio.softmax(-1).float().cpu()
        states = states.float().cpu()
        cls_states.append(states[:, 0])
        rel_probs += torch.sigmoid(rel.float()).cpu().tolist()
        for w in range(ids.shape[0]):
            for t, (s, e) in enumerate(offsets[b + w].tolist()):
                if e <= s:
                    continue  # special or padding token
                entry = token_state.setdefault((s, e), [0, None, None])
                entry[0] += 1
                entry[1] = probs[w, t] if entry[1] is None else entry[1] + probs[w, t]
                entry[2] = states[w, t] if entry[2] is None else entry[2] + states[w, t]
    tokens = sorted(token_state)
    labels = [BIO[int((token_state[k][1] / token_state[k][0]).argmax())] for k in tokens]
    confidence = [float((token_state[k][1] / token_state[k][0]).max()) for k in tokens]
    relevant_prob = sum(rel_probs) / len(rel_probs)

    def pool(idx: list[int]) -> torch.Tensor:
        return torch.stack([token_state[tokens[i]][2] / token_state[tokens[i]][0]
                            for i in idx]).mean(0)

    doc = torch.cat(cls_states).mean(0).to(device)
    groups, current = [], None
    if decode == "unit":
        position, unit_tokens = 0, []
        for a, b in units(text):
            idx = []
            while position < len(tokens) and tokens[position][0] < b:
                if tokens[position][1] > a:
                    idx.append(position)
                position += 1
            if idx:
                unit_tokens.append(((a, b), idx))
        unit_features = (model.features(torch.stack([pool(idx) for _, idx in unit_tokens])
                                        .to(device), doc) if unit_tokens else None)
        unit_probs = (model.unit(unit_features).softmax(-1).float().cpu()
                      if unit_tokens and model.task == "unit" else None)
        for n, ((a, b), idx) in enumerate(unit_tokens):
            if model.task == "unit":
                probs = unit_probs[n]
                score = 1 - float(probs[0])
                kind = KINDS[int(probs[1:].argmax())]
            else:
                mean = torch.stack([token_state[tokens[i]][1] / token_state[tokens[i]][0]
                                    for i in idx]).mean(0)
                mass = {k: float(mean[BIO.index(f"B-{k}")] + mean[BIO.index(f"I-{k}")])
                        for k in KINDS}
                kind = max(mass, key=mass.get)
                score = mass[kind]
            if score >= model.threshold:
                groups.append({"kind": kind, "tokens": idx, "span": (a, b), "score": score,
                               "feature": unit_features[n] if model.task == "unit" else None})
        labels = []
    for i, label in enumerate(labels):
        if label == "O":
            current = None
            continue
        prefix, kind = label.split("-")
        if current is None or prefix == "B" or kind != current["kind"]:
            current = {"kind": kind, "tokens": []}
            groups.append(current)
        current["tokens"].append(i)
    spans = []
    for g in groups:
        if len(g["tokens"]) < MIN_SPAN_TOKENS and "span" not in g:
            continue
        feature = g.get("feature")
        if feature is None:
            feature = model.features(pool(g["tokens"]).unsqueeze(0).to(device), doc)[0]
        attrs = {a: ATTRS[a][int(logits.argmax())]
                 for a, logits in model.classify(feature.unsqueeze(0)).items()}
        start, end = g.get("span") or (tokens[g["tokens"][0]][0], tokens[g["tokens"][-1]][1])
        while start < end and text[start].isspace():
            start += 1
        score = g.get("score") or sum(confidence[i] for i in g["tokens"]) / len(g["tokens"])
        spans.append(Span(start, end, g["kind"], score=round(score, 3), **attrs))
    # The relevance head is weak (few irrelevant training chunks), so it is only reported. A chunk
    # is relevant when its most confident item reaches relevance_threshold (chosen on the
    # validation chunks); items are kept down to the lower unit threshold for recall.
    relevant = max((s.score for s in spans), default=0.0) >= model.relevance_threshold
    return relevant, relevant_prob, spans if relevant else []
