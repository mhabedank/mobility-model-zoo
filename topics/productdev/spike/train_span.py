"""Train the encoder span model (topics/productdev/spike/span_model.py) on the four-teacher ensemble labels.

Training data: the spike's 200 train chunks labeled by the ensemble strategy that produced the
v3b training data (topics/productdev/spike/ensemble.py EXPORT, quotes repaired to source spans). 20 chunks are held
out for choosing the best epoch; the 35 evaluation chunks are never used here.

Run: uv run --with torch --with transformers --with sentencepiece --with protobuf \
         python topics/productdev/spike/train_span.py [--encoder FacebookAI/xlm-roberta-base] [--epochs 12]
On another machine (e.g. the DGX Spark, see topics/productdev/spike/train_span_spark.sh): export the labeled rows
here with --export-rows rows.jsonl [--teachers], then train there with --rows rows.jsonl; this
needs only torch and transformers, not the mobility_model_zoo.productdev.jtbd package.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

import torch
from torch import nn

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "spike"))

from span_model import (  # noqa: E402
    ATTRS,
    BIO,
    UNIT_LABELS,
    SpanTagger,
    predict,
    save,
    units,
    windows,
)


def iou(a: tuple[int, int], b: tuple[int, int]) -> float:
    inter = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    union = max(a[1], b[1]) - min(a[0], b[0])
    return inter / union if union else 0.0


def teacher_labels(settings, chunk_ids: set[str]) -> list[dict]:
    """The same chunks labeled by each single teacher (repaired quotes): more, noisier examples."""
    from ensemble import EXPORT, MODELS, RUN

    from mobility_model_zoo.productdev.jtbd.corpus.store import chunk_map
    from mobility_model_zoo.productdev.jtbd.ensemble import with_repair
    from mobility_model_zoo.productdev.jtbd.runs import load_outputs

    _, models, _ = EXPORT
    chunks = chunk_map(settings, "train")
    rows = []
    for m in models:
        for chunk_id, out in sorted(load_outputs(settings, RUN.format(MODELS[m], "train")).items()):
            if chunk_id not in chunk_ids or out.relevant is None:
                continue
            text = chunks[chunk_id].text
            items = with_repair(out, text) if out.relevant else []
            rows.append({"chunk_id": f"{chunk_id}@{m}", "text": text, "relevant": out.relevant,
                         "items": [{"span": it.span, "kind": it.kind, "actor_type": it.actor_type,
                                    "evidence_type": it.evidence_type,
                                    "evidence_scope": it.evidence_scope} for it in items]})
    return rows


def ensemble_labels(settings) -> list[dict]:
    from ensemble import DIM_PRIORITY, EXPORT, MODELS, QUOTE_PRIORITY, RUN

    from mobility_model_zoo.productdev.jtbd.corpus.store import chunk_map
    from mobility_model_zoo.productdev.jtbd.ensemble import combine
    from mobility_model_zoo.productdev.jtbd.runs import load_outputs

    _, models, min_votes = EXPORT
    chunks = chunk_map(settings, "train")
    outputs = {m: load_outputs(settings, RUN.format(MODELS[m], "train")) for m in models}
    combined = combine(outputs, models, min_votes, chunks, 0.3, DIM_PRIORITY, QUOTE_PRIORITY)
    rows = []
    for chunk_id, out in sorted(combined.items()):
        if out.relevant is None:
            continue
        rows.append({"chunk_id": chunk_id, "text": chunks[chunk_id].text, "relevant": out.relevant,
                     "items": [{"span": it.span, "kind": it.kind, "actor_type": it.actor_type,
                                "evidence_type": it.evidence_type,
                                "evidence_scope": it.evidence_scope} for it in out.items]})
    return rows


def unit_items(row: dict) -> list[tuple[tuple[int, int], dict | None]]:
    """Each unit with the item it belongs to: the item overlapping it most, if that overlap covers
    at least half of the unit or half of the item."""
    out = []
    for a, b in units(row["text"]):
        best, best_overlap = None, 0
        for item in row["items"]:
            s, e = item["span"]
            overlap = max(0, min(b, e) - max(a, s))
            if overlap > best_overlap and (overlap >= 0.5 * (b - a) or overlap >= 0.5 * (e - s)):
                best, best_overlap = item, overlap
        out.append(((a, b), best))
    return out


def encode(tokenizer, row: dict) -> list[dict]:
    """Training windows of one chunk: token BIO labels, and the units fully inside the window with
    their token indices, label and item attributes."""
    enc = windows(tokenizer, row["text"])
    labeled_units = unit_items(row)
    out = []
    for w in range(len(enc["input_ids"])):
        offsets = enc["offset_mapping"][w].tolist()
        real = [(s, e) for s, e in offsets if e > s]
        lo, hi = real[0][0], real[-1][1]
        window_units = []
        for (a, b), item in labeled_units:
            if a < lo or b > hi:
                continue  # the unit is cut by the window edge; another window covers it
            idx = [t for t, (s, e) in enumerate(offsets) if e > s and s < b and e > a]
            if idx:
                window_units.append({
                    "tokens": idx,
                    "label": UNIT_LABELS.index(item["kind"]) if item else 0,
                    **({k: ATTRS[k].index(item[k]) for k in ATTRS} if item else {})})
        labels = [-100 if e <= s else 0 for s, e in offsets]
        spans = []
        for item in sorted(row["items"], key=lambda i: i["span"][0]):
            a, b = item["span"]
            idx = [t for t, (s, e) in enumerate(offsets) if e > s and s < b and e > a]
            idx = [t for t in idx if labels[t] == 0]  # first item wins on overlaps
            if not idx:
                continue
            for n, t in enumerate(idx):
                labels[t] = BIO.index(f"{'B' if n == 0 else 'I'}-{item['kind']}")
            spans.append({"tokens": idx, **{k: ATTRS[k].index(item[k]) for k in ATTRS}})
        out.append({"input_ids": enc["input_ids"][w], "attention_mask": enc["attention_mask"][w],
                    "labels": torch.tensor(labels), "spans": spans, "units": window_units,
                    "relevant": float(row["relevant"])})
    return out


def evaluate(model, tokenizer, rows, device) -> dict:
    tp = fp = fn = 0
    correct = {k: 0 for k in ["kind", *ATTRS]}
    matched = rel_ok = 0
    for row in rows:
        relevant, _, spans = predict(model, tokenizer, row["text"], device)
        rel_ok += relevant == row["relevant"]
        gold = list(row["items"])
        for sp in spans:
            best = max(gold, key=lambda g: iou((sp.start, sp.end), tuple(g["span"])), default=None)
            if best and iou((sp.start, sp.end), tuple(best["span"])) >= 0.3:
                tp += 1
                matched += 1
                gold.remove(best)
                for k in correct:
                    correct[k] += getattr(sp, k) == best[k]
            else:
                fp += 1
        fn += len(gold)
    f1 = 2 * tp / (2 * tp + fp + fn) if tp else 0.0
    accs = {k: round(v / matched, 3) if matched else 0.0 for k, v in correct.items()}
    return {"item_f1": round(f1, 3), "relevance_acc": round(rel_ok / len(rows), 3), **accs,
            "score": round((f1 + sum(accs.values()) / len(accs)) / 2, 4)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--encoder", default="FacebookAI/xlm-roberta-base")
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--lr", type=float, default=4e-5)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--out", type=Path, default=ROOT / "data/models/span-xlmr")
    parser.add_argument("--seed", type=int, default=20261001)
    parser.add_argument("--teachers", action="store_true",
                        help="also train on each single teacher's labels of the train chunks")
    parser.add_argument("--rows", type=Path,
                        help="train on exported rows (no mobility_model_zoo package needed)")
    parser.add_argument("--export-rows", type=Path, help="write the labeled rows and stop")
    parser.add_argument("--context", action="store_true",
                        help="unit and attribute heads also see the neighbouring units and the window")
    parser.add_argument("--val-from", type=Path,
                        help="span_model.json of an earlier run: reuse its validation chunks")
    args = parser.parse_args()
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = ("cuda" if torch.cuda.is_available()
              else "mps" if torch.backends.mps.is_available() else "cpu")

    if args.rows:
        rows = [json.loads(line) for line in args.rows.read_text().splitlines()]
        val_rows = [r for r in rows if r["split"] == "val"]
        train_rows = [r for r in rows if r["split"] == "train"]
    else:
        from mobility_model_zoo.productdev.jtbd.config import load_settings

        settings = load_settings(ROOT / "configs/productdev/jtbd/spike-v1.yaml")
        rows = ensemble_labels(settings)
        if args.val_from:
            val_ids = set(json.loads(args.val_from.read_text())["val_chunk_ids"])
            val_rows = [r for r in rows if r["chunk_id"] in val_ids]
            train_rows = [r for r in rows if r["chunk_id"] not in val_ids]
        else:
            random.shuffle(rows)
            val_rows, train_rows = rows[:20], rows[20:]
        if args.teachers:
            train_rows += teacher_labels(settings, {r["chunk_id"] for r in train_rows})
    if args.export_rows:
        with args.export_rows.open("w") as f:
            for split, part in (("val", val_rows), ("train", train_rows)):
                for r in part:
                    f.write(json.dumps({**r, "split": split}, ensure_ascii=False) + "\n")
        print(f"wrote {len(val_rows)} val and {len(train_rows)} train rows to {args.export_rows}")
        return

    from transformers import AutoTokenizer, get_linear_schedule_with_warmup

    tokenizer = AutoTokenizer.from_pretrained(args.encoder)
    train = [w for r in train_rows for w in encode(tokenizer, r)]
    print(f"{len(train_rows)} train chunks -> {len(train)} windows, {len(val_rows)} val chunks, "
          f"device {device}", flush=True)

    model = SpanTagger(args.encoder, context=args.context).to(device)
    optim = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    steps = args.epochs * ((len(train) + args.batch - 1) // args.batch)
    sched = get_linear_schedule_with_warmup(optim, int(0.1 * steps), steps)
    ce, bce = nn.CrossEntropyLoss(ignore_index=-100), nn.BCEWithLogitsLoss()
    best = None
    for epoch in range(1, args.epochs + 1):
        model.train()
        random.shuffle(train)
        start, total = time.time(), 0.0
        for b in range(0, len(train), args.batch):
            batch = train[b:b + args.batch]
            ids = torch.stack([w["input_ids"] for w in batch]).to(device)
            mask = torch.stack([w["attention_mask"] for w in batch]).to(device)
            labels = torch.stack([w["labels"] for w in batch]).to(device)
            states, bio, rel = model(ids, mask)
            loss = 0.5 * ce(bio.reshape(-1, len(BIO)), labels.reshape(-1))
            loss = loss + 0.5 * bce(rel, torch.tensor([w["relevant"] for w in batch],
                                                      device=device))
            unit_pooled, unit_labels = [], []
            pooled, targets = [], {k: [] for k in ATTRS}
            for w, win in enumerate(batch):
                if not win["units"]:
                    continue
                vectors = torch.stack([states[w, u["tokens"]].mean(0) for u in win["units"]])
                features = model.features(vectors, states[w, 0])
                for u, feature in zip(win["units"], features, strict=True):
                    unit_pooled.append(feature)
                    unit_labels.append(u["label"])
                    if u["label"]:
                        pooled.append(feature)
                        for k in ATTRS:
                            targets[k].append(u[k])
            if unit_pooled:
                loss = loss + ce(model.unit(torch.stack(unit_pooled)),
                                 torch.tensor(unit_labels, device=device))
            if pooled:
                logits = model.classify(torch.stack(pooled))
                for k in ATTRS:
                    loss = loss + ce(logits[k], torch.tensor(targets[k], device=device))
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optim.step()
            sched.step()
            optim.zero_grad()
            total += loss.item()
        model.eval()
        metrics = evaluate(model, tokenizer, val_rows, device)
        print(f"epoch {epoch}: loss {total / (len(train) / args.batch):.3f}, "
              f"{time.time() - start:.0f}s, val {metrics}", flush=True)
        if best is None or metrics["score"] > best["score"]:
            best = {**metrics, "epoch": epoch}
            save(model, tokenizer, args.encoder, args.out,
                 {"best_epoch": epoch, "val": metrics, "train_chunks": len(train_rows),
                  "val_chunk_ids": [r["chunk_id"] for r in val_rows]})
    print(f"best {best} -> {args.out}", flush=True)


if __name__ == "__main__":
    main()
