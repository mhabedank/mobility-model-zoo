"""Training one span-model candidate (feature 004, research R8-R9, T027).

Plain PyTorch with `transformers` (deviation from Ludwig, plan.md Complexity Tracking). Ported from
the spike's train_span.py without its spike imports. The loss is

    bio_weight x CE(BIO tokens) + relevance_weight x BCE(relevance)
    + CE(unit kind) over units fully inside a window + sum of CE(attribute) over item units,

with attribute heads only for the dimensions the model produces. The best epoch on the validation
rows (snapshots held out of training) is kept; the benchmark is never used here.
"""

from __future__ import annotations

import random
import time
from pathlib import Path
from typing import Any

import torch
from torch import nn

from mobility_model_zoo.productdev.jtbd.span.extractor import SpanExtractor, default_config
from mobility_model_zoo.productdev.jtbd.span.model import (
    ATTRIBUTE_LABELS,
    BIO_LABELS,
    UNIT_LABELS,
    SpanTagger,
)
from mobility_model_zoo.productdev.jtbd.span.rows import align_units
from mobility_model_zoo.productdev.jtbd.span.units import windows

MIN_IOU = 0.3


def encode(tokenizer: Any, row: dict[str, Any], dimensions: dict[str, list[str]],
           max_length: int, stride: int) -> list[dict[str, Any]]:
    """Training windows of one row: BIO labels per token, and the units fully inside the window
    with their token indices, unit label and (for item units) attribute labels."""
    enc = windows(tokenizer, row["text"], max_length, stride)
    labeled = align_units(row["text"], row["items"])
    out = []
    for w in range(len(enc["input_ids"])):
        offsets = enc["offset_mapping"][w]
        real = [(s, e) for s, e in offsets if e > s]
        if not real:
            continue
        lo, hi = real[0][0], real[-1][1]
        window_units = []
        for (a, b), item in labeled:
            if a < lo or b > hi:
                continue  # cut by the window edge; another window covers the unit
            idx = [t for t, (s, e) in enumerate(offsets) if e > s and s < b and e > a]
            if idx:
                window_units.append({
                    "tokens": idx,
                    "label": UNIT_LABELS.index(item["kind"]) if item else 0,
                    **({d: labels.index(item[d]) for d, labels in dimensions.items()}
                       if item else {})})
        bio = [-100 if e <= s else 0 for s, e in offsets]
        for item in sorted(row["items"], key=lambda i: i["span"][0]):
            a, b = item["span"]
            idx = [t for t, (s, e) in enumerate(offsets)
                   if e > s and s < b and e > a and bio[t] == 0]  # first item wins on overlaps
            for n, t in enumerate(idx):
                bio[t] = BIO_LABELS.index(f"{'B' if n == 0 else 'I'}-{item['kind']}")
        out.append({"input_ids": torch.tensor(enc["input_ids"][w]),
                    "attention_mask": torch.tensor(enc["attention_mask"][w]),
                    "bio": torch.tensor(bio), "units": window_units,
                    "relevant": float(row["relevant"])})
    return out


def iou(a: tuple[int, int], b: tuple[int, int]) -> float:
    inter = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    union = max(a[1], b[1]) - min(a[0], b[0])
    return inter / union if union else 0.0


def decide(scored: list[dict[str, Any]], unit_threshold: float, relevance_threshold: float
           ) -> tuple[bool, list[dict[str, Any]]]:
    """The extractor's decision rule (extractor.extract) on precomputed unit scores."""
    kept = [u for u in scored if u["score"] >= unit_threshold]
    relevant = max((u["score"] for u in kept), default=0.0) >= relevance_threshold
    return relevant, kept if relevant else []


def validation_metrics(rows: list[dict[str, Any]], scored: dict[str, list[dict[str, Any]]],
                       dimensions: list[str], unit_threshold: float,
                       relevance_threshold: float) -> dict[str, Any]:
    """Item F1 (IoU >= 0.3, greedy), agreement on kind and produced attributes for matched items,
    relevance agreement; score = (item F1 + mean attribute agreement) / 2."""
    tp = fp = fn = matched = relevance_ok = 0
    correct = {k: 0 for k in ["kind", *dimensions]}
    for row in rows:
        relevant, items = decide(scored[row["chunk_id"]], unit_threshold, relevance_threshold)
        relevance_ok += relevant == row["relevant"]
        gold = list(row["items"])
        for item in items:
            span = (item["start"], item["end"])
            best = max(gold, key=lambda g: iou(span, tuple(g["span"])), default=None)
            if best and iou(span, tuple(best["span"])) >= MIN_IOU:
                tp += 1
                matched += 1
                gold.remove(best)
                for k in correct:
                    correct[k] += item[k] == best[k]
            else:
                fp += 1
        fn += len(gold)
    f1 = 2 * tp / (2 * tp + fp + fn) if tp else 0.0
    agreement = {k: round(v / matched, 4) if matched else 0.0 for k, v in correct.items()}
    mean_attr = sum(agreement.values()) / len(agreement)
    return {"item_f1": round(f1, 4), "relevance_agreement": round(relevance_ok / len(rows), 4)
            if rows else 0.0, **{f"{k}_agreement": v for k, v in agreement.items()},
            "score": round((f1 + mean_attr) / 2, 4)}


def score_rows(extractor: SpanExtractor, rows: list[dict[str, Any]]
               ) -> dict[str, list[dict[str, Any]]]:
    extractor.model.eval()
    return {row["chunk_id"]: extractor.score_units(row["text"])[0] for row in rows}


def load_encoder(name: str, revision: str | None):
    from transformers import AutoModel, AutoTokenizer

    kwargs = {"revision": revision} if revision and not Path(name).is_dir() else {}
    return AutoModel.from_pretrained(name, **kwargs), AutoTokenizer.from_pretrained(name, **kwargs)


def train_candidate(recipe: dict[str, Any], dimensions: list[str], train_rows: list[dict],
                    val_rows: list[dict], out: Path, device: str = "cpu",
                    meta: dict[str, Any] | None = None, max_epochs: int | None = None,
                    log=print) -> dict[str, Any]:
    from transformers import get_linear_schedule_with_warmup

    hp = recipe["training"]
    epochs = int(max_epochs or hp["max_epochs"])
    seed = int(hp["seed"])
    random.seed(seed)
    torch.manual_seed(seed)
    rng = random.Random(seed)
    max_length, stride = int(recipe["windows"]["max_length"]), int(recipe["windows"]["stride"])
    labels = {d: ATTRIBUTE_LABELS[d] for d in dimensions}

    encoder, tokenizer = load_encoder(recipe["base_encoder"]["name"],
                                      recipe["base_encoder"].get("revision"))
    model = SpanTagger(encoder, labels).to(device)
    config = default_config(
        model=recipe.get("model"), base_encoder=recipe["base_encoder"],
        windows={"max_length": max_length, "stride": stride},
        training={**hp, "max_epochs": epochs}, **(meta or {}))
    extractor = SpanExtractor(model, tokenizer, config, device)

    windows_train = [w for r in train_rows for w in encode(tokenizer, r, labels, max_length,
                                                           stride)]
    log(f"{len(train_rows)} train rows -> {len(windows_train)} windows, {len(val_rows)} val rows, "
        f"device {device}")
    batch_size = int(hp["batch_size"])
    optim = torch.optim.AdamW(model.parameters(), lr=float(hp["lr"]),
                              weight_decay=float(hp["weight_decay"]))
    steps = epochs * max(1, (len(windows_train) + batch_size - 1) // batch_size)
    sched = get_linear_schedule_with_warmup(optim, int(float(hp["warmup"]) * steps), steps)
    ce, bce = nn.CrossEntropyLoss(ignore_index=-100), nn.BCEWithLogitsLoss()
    bio_weight, rel_weight = float(hp["bio_loss_weight"]), float(hp["relevance_loss_weight"])
    best: dict[str, Any] | None = None
    history = []
    for epoch in range(1, epochs + 1):
        model.train()
        rng.shuffle(windows_train)
        start, total = time.time(), 0.0
        for b in range(0, len(windows_train), batch_size):
            batch = windows_train[b:b + batch_size]
            ids = torch.stack([w["input_ids"] for w in batch]).to(device)
            mask = torch.stack([w["attention_mask"] for w in batch]).to(device)
            bio_targets = torch.stack([w["bio"] for w in batch]).to(device)
            states, bio, rel = model(ids, mask)
            loss = bio_weight * ce(bio.reshape(-1, len(BIO_LABELS)), bio_targets.reshape(-1))
            loss = loss + rel_weight * bce(rel, torch.tensor([w["relevant"] for w in batch],
                                                             device=device))
            unit_vectors, unit_targets, item_vectors = [], [], []
            attr_targets: dict[str, list[int]] = {d: [] for d in labels}
            for w, window in enumerate(batch):
                for unit in window["units"]:
                    vector = states[w, unit["tokens"]].mean(0)
                    unit_vectors.append(vector)
                    unit_targets.append(unit["label"])
                    if unit["label"]:
                        item_vectors.append(vector)
                        for d in labels:
                            attr_targets[d].append(unit[d])
            if unit_vectors:
                loss = loss + ce(model.unit_logits(torch.stack(unit_vectors)),
                                 torch.tensor(unit_targets, device=device))
            if item_vectors and labels:
                logits = model.attribute_logits(torch.stack(item_vectors))
                for d in labels:
                    loss = loss + ce(logits[d], torch.tensor(attr_targets[d], device=device))
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), float(hp["grad_clip"]))
            optim.step()
            sched.step()
            optim.zero_grad()
            total += loss.item()
        thresholds = extractor.thresholds
        metrics = validation_metrics(val_rows, score_rows(extractor, val_rows), dimensions,
                                     thresholds["unit"], thresholds["relevance"])
        history.append({"epoch": epoch, "loss": round(total, 4), **metrics})
        log(f"epoch {epoch}: loss {total:.3f}, {time.time() - start:.0f}s, val {metrics}")
        if best is None or metrics["score"] > best["score"]:
            best = {**metrics, "epoch": epoch}
            extractor.config = {**config, "training": {**config["training"], "best_epoch": epoch},
                                "validation": metrics, "epochs": history}
            extractor.save_pretrained(out)
    return {"out": str(out), "best": best, "epochs": history}
