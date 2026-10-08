"""Propose data/chunks/selection.yaml for pilot-v1 (001 T033), without manual work.

Stage 1, `candidates`: cut every benchmark snapshot of the source plan into sentence-bounded
windows (corpus.autochunk.cut_ranges), keep prose windows, and let a local model on the DGX Spark
classify each one: language, relevance (relevant / near_miss / irrelevant), sub-area, whether
affected people speak about their own experience, and quality. Answers are cached in
data/analysis/selection/candidates.jsonl, so the stage can be resumed.

Stage 2, `select`: choose about 185 windows greedily so that the pilot's composition targets hold
(configs/productdev/jtbd/pilot-v1.yaml): source-type shares, 15-25% near-miss or irrelevant,
10-15% non-EU, both languages >= 35%, DACH the largest region, each sub-area 15-25% of the
relevant chunks; at most MAX_PER_SNAPSHOT windows per snapshot. Writes data/chunks/selection.yaml
for `jtbd corpus build`. `jtbd corpus split` then separates main and holdout.

Snapshots reserved for training (feature 004) are never proposed.

    uv run python scripts/pilot/propose_selection.py candidates
    uv run python scripts/pilot/propose_selection.py select --total 185
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
from collections import Counter
from pathlib import Path

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "data/sources/source-plan.yaml"
SNAPSHOTS = ROOT / "data/snapshots"
OUT = ROOT / "data/analysis/selection"
SELECTION = ROOT / "data/chunks/selection.yaml"
RESERVED = ROOT / "data/sources/reserved-for-training.yaml"
SUB_AREAS = ["public_transport_rural", "logistics_delivery", "emobility_charging",
             "car_ownership_use", "sharing_platforms"]
MODEL = "qwen3.8:27b"
SEED = 20261006
MAX_CANDIDATES = 16       # per snapshot (large transcripts: keyword windows plus a few random)
MAX_PER_SNAPSHOT = 4
MAX_PER_FORUM_SNAPSHOT = 4

SCHEMA = {
    "type": "object",
    "properties": {
        "language": {"enum": ["de", "en", "other", "mixed"]},
        "relevance": {"enum": ["relevant", "near_miss", "irrelevant"]},
        "sub_area": {"enum": [*SUB_AREAS, "none"]},
        "affected_voice": {"type": "boolean"},
        "self_contained": {"type": "boolean"},
        "quality": {"type": "integer", "minimum": 1, "maximum": 5},
    },
    "required": ["language", "relevance", "sub_area", "affected_voice", "self_contained",
                 "quality"],
}
PROMPT = """Classify this text excerpt for a benchmark on mobility needs (jobs-to-be-done,
pains and gains of people in mobility).

- language: de, en, other, or mixed (several languages)
- relevance:
  relevant = people's goals, problems, needs or benefits in mobility are expressed or described
  (public transport in rural areas, delivery and logistics work, electric vehicle charging,
  owning and using a car, sharing and micromobility)
  near_miss = vehicles or transport appear, but not as needs of people in mobility (motorsport,
  hobby, vehicle technology, model railways, procedural talk)
  irrelevant = not about mobility
- sub_area: the best fitting area for relevant text, else none
- affected_voice: true if people describe their own experience or needs (citizens, workers,
  drivers, users), false for purely academic, procedural or political rhetoric
- self_contained: true if the excerpt can be understood without the surrounding text
- quality: 1 (garbled, tables, references) to 5 (clear, rich prose)

Answer only with JSON.

Excerpt:
"""


def plan_entries() -> list[dict]:
    plan = yaml.safe_load(PLAN.read_text())
    reserved = set((yaml.safe_load(RESERVED.read_text()) or {}).get("snapshots", [])) \
        if RESERVED.exists() else set()
    entries = []
    for kind in ("papers", "transcripts", "forum_review"):
        for e in plan.get(kind, []):
            if not isinstance(e, dict):
                continue
            single = e.get("snapshot")
            snaps = e.get("snapshots") or (single if isinstance(single, list)
                                            else [single] if single else [])
            for s in snaps:
                if s in reserved:
                    continue
                entries.append({**e, "snapshot_id": s, "kind": kind})
    return entries


def snapshot_meta(snapshot_id: str) -> dict:
    return yaml.safe_load((SNAPSHOTS / snapshot_id / "source.yaml").read_text())


def windows(text: str) -> list[tuple[int, int]]:
    from mobility_model_zoo.productdev.jtbd.corpus.autochunk import cut_ranges, usable

    return [r for r in cut_ranges(text) if usable(text[r[0]:r[1]])]


def keyword_score(text: str, keywords: list[str]) -> int:
    from mobility_model_zoo.productdev.jtbd.corpus.autochunk import keyword_hits

    return keyword_hits(text, keywords)


def classify(base_url: str, text: str) -> dict:
    r = httpx.post(f"{base_url}/api/chat", timeout=600, json={
        "model": MODEL, "stream": False, "think": False, "format": SCHEMA,
        "options": {"temperature": 0, "num_ctx": 16384},
        "messages": [{"role": "user", "content": PROMPT + text}]})
    r.raise_for_status()
    return json.loads(r.json()["message"]["content"])


def stage_candidates() -> None:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    base_url = os.environ["OLLAMA_HOST"].rstrip("/")
    keywords = [k.lower() for k in yaml.safe_load(
        (ROOT / "configs/productdev/jtbd/domain/mobility.yaml").read_text())["topic_keywords"]]
    OUT.mkdir(parents=True, exist_ok=True)
    cache_path = OUT / "candidates.jsonl"
    done = set()
    if cache_path.exists():
        done = {json.loads(line)["window_id"] for line in cache_path.read_text().splitlines()}
    rng = random.Random(SEED)
    todo = []
    for e in plan_entries():
        text = (SNAPSHOTS / e["snapshot_id"] / "text.txt").read_text(encoding="utf-8")
        wins = windows(text)
        if len(wins) > MAX_CANDIDATES:
            scored = sorted(wins, key=lambda r: -keyword_score(text[r[0]:r[1]], keywords))
            top = scored[:MAX_CANDIDATES - 3]
            rest = [w for w in wins if w not in top]
            wins = sorted(top + rng.sample(rest, min(3, len(rest))))
        for start, end in wins:
            todo.append((e, start, end, text[start:end]))
    print(f"{len(todo)} windows, {len(done)} cached", file=sys.stderr, flush=True)
    with cache_path.open("a", encoding="utf-8") as cache:
        for n, (e, start, end, window) in enumerate(todo, 1):
            window_id = f"{e['snapshot_id']}:{start}-{end}"
            if window_id in done:
                continue
            try:
                label = classify(base_url, window)
            except (httpx.HTTPError, ValueError, KeyError) as exc:
                print(f"skip {window_id}: {exc}", file=sys.stderr, flush=True)
                continue
            cache.write(json.dumps({"window_id": window_id, "snapshot_id": e["snapshot_id"],
                                    "plan_id": e["id"], "kind": e["kind"], "start": start,
                                    "end": end, **label}, ensure_ascii=False) + "\n")
            cache.flush()
            if n % 25 == 0:
                print(f"{n}/{len(todo)}", file=sys.stderr, flush=True)


# ---- stage 2 ----------------------------------------------------------------------------------
def entry_region(e: dict, meta: dict) -> tuple[str, str]:
    region = e.get("region") or "DACH"
    country = e.get("country") or {"DACH": "DE", "EU_other": "EU", "non_EU": "XX"}[region]
    if country == "EU":
        country = "XX"
    return region, country


def entry_date(e: dict, meta: dict) -> str:
    if e.get("date"):
        return str(e["date"])
    match = re.search(r"\b(19|20)\d{2}\b", str(e.get("title", "")))
    if match:
        return f"{match.group(0)}-01-01"
    return str(meta["retrieved_at"])[:10]


def penalty(chosen: list[dict], total: int) -> float:
    """Distance of a selection from the composition targets, with inner margins so that a
    stratified main/holdout split stays inside the ranges. Lower is better; quality breaks ties."""
    n = len(chosen)
    rel = [c for c in chosen if c["relevance"] == "relevant"]
    types = Counter(c["source_type"] for c in chosen)
    areas = Counter(c["sub_area"] for c in rel)

    def outside(value: float, low: float, high: float) -> float:
        return max(0.0, low - value) + max(0.0, value - high)

    p = abs(total - n) * 0.05
    for area in SUB_AREAS:
        p += outside(areas[area] / max(1, len(rel)), 0.17, 0.23) * 4
    for stype in ("paper", "transcript"):
        p += outside(types[stype] / n, 0.20, 0.30) * 3
    p += outside(types["forum_review"] / n, 0.20, 0.60) * 3
    p += outside((n - len(rel)) / n, 0.17, 0.23) * 4
    p += outside(sum(c["region"] == "non_EU" for c in chosen) / n, 0.11, 0.14) * 4
    for lang in ("de", "en"):
        p += outside(sum(c["language"] == lang for c in chosen) / n, 0.38, 1.0) * 3
    regions = Counter(c["region"] for c in chosen)
    if regions["DACH"] <= max(regions["EU_other"], regions["non_EU"]):
        p += 1
    p -= sum(c["affected_voice"] * 0.5 + c["quality"] * 0.1 for c in chosen) / n * 0.01
    return p


def rebalance(chosen: list[dict], pool: list[dict], total: int, rng: random.Random,
              rounds: int = 20000) -> list[dict]:
    """Improve the greedy selection by single swaps (and additions up to `total`) that lower the
    penalty, respecting the per-snapshot limits."""
    chosen, pool = list(chosen), list(pool)
    per_snap = Counter(c["snapshot_id"] for c in chosen)

    def fits(c: dict, out: dict | None = None) -> bool:
        limit = MAX_PER_FORUM_SNAPSHOT if c["source_type"] == "forum_review" else MAX_PER_SNAPSHOT
        used = per_snap[c["snapshot_id"]] - (out is not None and out["snapshot_id"] ==
                                              c["snapshot_id"])
        return used < limit

    best = penalty(chosen, total)
    for _ in range(rounds):
        new = rng.choice(pool)
        if len(chosen) < total and rng.random() < 0.3:
            if not fits(new):
                continue
            trial, out = chosen + [new], None
        else:
            out = rng.choice(chosen)
            if not fits(new, out):
                continue
            trial = [c for c in chosen if c is not out] + [new]
        score = penalty(trial, total)
        if score < best:
            best, chosen = score, trial
            pool.remove(new)
            per_snap[new["snapshot_id"]] += 1
            if out is not None:
                pool.append(out)
                per_snap[out["snapshot_id"]] -= 1
    return chosen


def stage_select(total: int) -> None:
    entries = {e["snapshot_id"]: e for e in plan_entries()}
    cands = [json.loads(line) for line in (OUT / "candidates.jsonl").read_text().splitlines()]
    cands = [c for c in cands if c["snapshot_id"] in entries and c["language"] in ("de", "en")
             and c["self_contained"] and c["quality"] >= 3]
    for c in cands:
        e = entries[c["snapshot_id"]]
        c["source_type"] = {"papers": "paper", "transcripts": "transcript",
                            "forum_review": "forum_review"}[c["kind"]]
        c["region"], c["country"] = entry_region(e, snapshot_meta(c["snapshot_id"]))
        if e.get("near_miss") and c["relevance"] == "relevant":
            c["relevance"] = "near_miss"  # planned near-miss sources stay near-miss
        if c["relevance"] == "relevant" and c["sub_area"] == "none":
            c["sub_area"] = e.get("sub_area") if isinstance(e.get("sub_area"), str) else None
        if c["relevance"] == "relevant" and c["sub_area"] not in SUB_AREAS:
            c["relevance"] = "drop"
    cands = [c for c in cands if c["relevance"] != "drop"]

    target = {
        "source_type": {"paper": 0.30 * total, "transcript": 0.30 * total,
                        "forum_review": 0.40 * total},
        "off": 0.20 * total,                      # near_miss + irrelevant
        "non_EU": 0.125 * total,
        "en": 0.42 * total,
        "sub_area": 0.80 * total / 5,             # per sub-area, among relevant
    }

    def deficit(counts: Counter) -> float:
        d = 0.0
        for k, v in target["source_type"].items():
            d += max(0.0, v - counts[("type", k)]) * 2
        d += max(0.0, target["off"] - counts["off"]) * 6
        d += max(0.0, target["non_EU"] - counts["non_EU"]) * 3
        d += max(0.0, target["en"] - counts["en"]) * 2
        for area in SUB_AREAS:
            d += max(0.0, target["sub_area"] - counts[("area", area)]) * 4
        return d

    def add(counts: Counter, c: dict) -> Counter:
        new = counts.copy()
        new[("type", c["source_type"])] += 1
        new["off"] += c["relevance"] != "relevant"
        new["non_EU"] += c["region"] == "non_EU"
        new["en"] += c["language"] == "en"
        if c["relevance"] == "relevant":
            new[("area", c["sub_area"])] += 1
        return new

    def overshoot(counts: Counter, c: dict) -> bool:
        n = sum(counts[("type", k)] for k in target["source_type"]) + 1
        caps = {"paper": 0.31, "transcript": 0.31, "forum_review": 0.62}
        if counts[("type", c["source_type"])] + 1 > caps[c["source_type"]] * total:
            return True
        if c["relevance"] != "relevant" and counts["off"] + 1 > 0.24 * total:
            return True
        if c["region"] == "non_EU" and counts["non_EU"] + 1 > 0.14 * total:
            return True
        if c["relevance"] == "relevant" and counts[("area", c["sub_area"])] + 1 > 0.24 * 0.8 * \
                total:
            return True
        return n > total

    rng = random.Random(SEED)
    rng.shuffle(cands)
    chosen, counts, per_snap = [], Counter(), Counter()
    while len(chosen) < total:
        best, best_gain = None, None
        for c in cands:
            limit = MAX_PER_FORUM_SNAPSHOT if c["source_type"] == "forum_review" \
                else MAX_PER_SNAPSHOT
            if per_snap[c["snapshot_id"]] >= limit or overshoot(counts, c):
                continue
            gain = deficit(counts) - deficit(add(counts, c))
            score = (gain, c["affected_voice"], c["quality"])
            if best_gain is None or score > best_gain:
                best, best_gain = c, score
        if best is None:
            break
        chosen.append(best)
        cands.remove(best)
        counts = add(counts, best)
        per_snap[best["snapshot_id"]] += 1

    chosen = rebalance(chosen, cands, total, rng)
    chosen.sort(key=lambda c: (c["source_type"], c["snapshot_id"], c["start"]))
    chunks = []
    for n, c in enumerate(chosen, 1):
        e = entries[c["snapshot_id"]]
        meta = snapshot_meta(c["snapshot_id"])
        chunks.append({
            "chunk_id": f"ch-{n:03d}", "snapshot_id": c["snapshot_id"],
            "ranges": [[c["start"], c["end"]]],
            "sub_area": c["sub_area"] if c["relevance"] == "relevant" else "none",
            "region": c["region"], "country": c["country"], "language": c["language"],
            "date": entry_date(e, meta), "relevance_intent": c["relevance"],
            "plan_id": e["id"],
        })
    SELECTION.parent.mkdir(parents=True, exist_ok=True)
    SELECTION.write_text(yaml.safe_dump({"chunks": [{k: v for k, v in ch.items() if k != "plan_id"}
                                                    for ch in chunks]}, sort_keys=False,
                                        allow_unicode=True), encoding="utf-8")
    summary = {
        "chosen": len(chunks),
        "source_type": dict(Counter(c["source_type"] for c in chosen)),
        "relevance": dict(Counter(c["relevance"] for c in chosen)),
        "sub_area_relevant": dict(Counter(c["sub_area"] for c in chosen
                                          if c["relevance"] == "relevant")),
        "language": dict(Counter(c["language"] for c in chosen)),
        "region": dict(Counter(c["region"] for c in chosen)),
        "affected_voice": sum(c["affected_voice"] for c in chosen),
        "snapshots": len({c["snapshot_id"] for c in chosen}),
    }
    (OUT / "selection-summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["candidates", "select"])
    parser.add_argument("--total", type=int, default=185)
    args = parser.parse_args()
    stage_candidates() if args.stage == "candidates" else stage_select(args.total)
