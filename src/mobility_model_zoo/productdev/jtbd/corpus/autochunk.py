"""Automatic chunking for technical spikes (spec 002, FR-S01/FR-S02).

Cuts contiguous windows of roughly 300-1500 tokens from snapshots listed in a snapshot map. Training
chunks (split `train`) come only from snapshots whose permitted use is `training_allowed`; evaluation
chunks (split `main`) come from snapshots marked `use: eval`. No snapshot supplies both.

Snapshot map format (YAML):

    snapshots:
      snap-0123456789ab: {plan_id: P02, use: train, sub_area: public_transport_rural,
                          language: en, region: DACH, country: DE, date: 2025-01-01}
"""

from __future__ import annotations

import random
import re
from pathlib import Path
from typing import Any

from mobility_model_zoo.productdev.jtbd.config import Settings
from mobility_model_zoo.productdev.jtbd.corpus.build import approx_tokens
from mobility_model_zoo.productdev.jtbd.corpus.store import load_chunks, save_chunk
from mobility_model_zoo.productdev.jtbd.errors import ValidationFailed
from mobility_model_zoo.productdev.jtbd.jsonio import read_yaml
from mobility_model_zoo.productdev.jtbd.schema import ChunkRecord
from mobility_model_zoo.productdev.jtbd.sources.snapshot import load_snapshot, snapshot_text

MIN_CHARS, TARGET_CHARS, MAX_CHARS = 1400, 3600, 5800
SENTENCE_END = re.compile(r"[.!?][\"'”“)\]]?\s")


def cut_ranges(text: str) -> list[tuple[int, int]]:
    """Consecutive windows that end at a sentence boundary where possible."""
    ranges: list[tuple[int, int]] = []
    start, n = 0, len(text)
    while start < n:
        while start < n and text[start].isspace():
            start += 1
        if n - start < MIN_CHARS:
            break
        end = min(start + TARGET_CHARS, n)
        match = SENTENCE_END.search(text, end, min(start + MAX_CHARS, n))
        end = match.end() if match else min(start + MAX_CHARS, n)
        ranges.append((start, end))
        start = end
    return ranges


def usable(window: str) -> bool:
    """Skip reference lists, tables and other text that is mostly not prose."""
    if not window.strip():
        return False
    letters = sum(ch.isalpha() for ch in window) / len(window)
    words = len(re.findall(r"[A-Za-zÄÖÜäöüß]{2,}", window))
    noise = window.lower().count("doi") + window.lower().count("http") + window.count("et al.")
    return letters >= 0.6 and words >= 150 and noise <= 4


ON_TOPIC_SHARE = 0.8
MIN_KEYWORD_HITS = 4


def keyword_hits(window: str, keywords: list[str]) -> int:
    words = re.findall(r"[a-zäöüß-]+", window.lower())
    return sum(1 for w in words if any(w.startswith(k) for k in keywords))


def _pick(pools: dict[str, list[tuple[int, int]]], quota: int, rng: random.Random
          ) -> list[tuple[str, tuple[int, int]]]:
    for windows in pools.values():
        rng.shuffle(windows)
    picked: list[tuple[str, tuple[int, int]]] = []
    order = sorted(pools)
    while len(picked) < quota and any(pools.values()):
        for snapshot_id in order:
            if pools[snapshot_id] and len(picked) < quota:
                picked.append((snapshot_id, pools[snapshot_id].pop()))
    return picked


def check_separation(settings: Settings, mapping: dict[str, Any],
                     exclude_benchmark: Path | None) -> dict[str, list[str]]:
    """Refuse training snapshots that share a source with the benchmark or spike data (R2).

    Runs when `--exclude-benchmark` is given or the config names `span_train.exclude_benchmark`.
    """
    from mobility_model_zoo.productdev.jtbd.corpus import separation

    if exclude_benchmark is None and not (settings.span_train or {}).get("exclude_benchmark"):
        return {}
    bench = separation.benchmark_sources(settings, exclude_benchmark)
    spike = separation.spike_snapshot_ids(settings)
    found = {}
    for snapshot_id, meta in sorted(mapping.items()):
        if meta["use"] == "train":
            rules = separation.violations(settings, snapshot_id, bench, spike)
            if rules:
                found[snapshot_id] = rules
    if found:
        listed = "; ".join(f"{k} ({', '.join(v)})" for k, v in found.items())
        raise ValidationFailed(f"training snapshots share a source with the benchmark or spike "
                               f"data: {listed}")
    return found


def _compliance_ingest(settings: Settings, mapping: dict[str, Any]):
    """Ingest checks of the compliance harness (feature 006, C-I1 … C-I7). Test fixtures without a
    register skip them; in the zoo repository a missing register is an error."""
    from mobility_model_zoo.compliance.findings import StageFailed
    from mobility_model_zoo.compliance.ingest import check_snapshots, harness_present
    from mobility_model_zoo.compliance.register import Register

    if not harness_present(settings.base):
        if settings.test_fixture:
            return None
        raise ValidationFailed("no compliance register (compliance/controller.yaml); ingest refused")
    reg = Register.load(settings.base)
    snaps = []
    for snapshot_id, meta in sorted(mapping.items()):
        snap = load_snapshot(settings, snapshot_id)
        snaps.append({"snapshot_id": snapshot_id, "origin_url": snap.origin_url,
                      "source_type": snap.source_type, "use": meta["use"]})
    from mobility_model_zoo.compliance.usage import declared_class

    target = declared_class(settings.base, (settings.span_train or {}).get("model"))
    findings = check_snapshots(reg, snaps, usage_class=target)
    if findings:
        raise ValidationFailed("compliance ingest check failed: "
                               + "; ".join(StageFailed(findings).failures[:10]))
    return reg


def autochunk(settings: Settings, map_path: Path, train: int, evaluation: int, seed: int,
              exclude_benchmark: Path | None = None) -> dict[str, Any]:
    if load_chunks(settings):
        raise ValidationFailed(f"{settings.chunks_dir} already has chunks; autochunk starts empty")
    mapping = read_yaml(map_path)["snapshots"]
    check_separation(settings, mapping, exclude_benchmark)
    creg = _compliance_ingest(settings, mapping)
    pools: dict[str, dict[str, list[tuple[int, int]]]] = {
        "train": {}, "eval": {}, "train_off": {}, "eval_off": {}}
    keywords = [k.lower() for k in settings.domain().get("topic_keywords", [])]
    texts: dict[str, str] = {}
    for snapshot_id, meta in sorted(mapping.items()):
        snapshot = load_snapshot(settings, snapshot_id)
        use = meta["use"]
        if use == "train" and snapshot.permitted_uses != "training_allowed":
            raise ValidationFailed(f"{snapshot_id} ({meta.get('plan_id')}) is "
                                   f"{snapshot.permitted_uses} and cannot supply training chunks")
        text = snapshot_text(settings, snapshot_id)
        texts[snapshot_id] = text
        windows = [r for r in cut_ranges(text) if usable(text[r[0]:r[1]])]
        if creg is not None:  # special categories are excluded for quarantining classes (C-I6)
            from mobility_model_zoo.compliance.ingest import window_allowed

            windows = [r for r in windows
                       if window_allowed(creg, snapshot.origin_url, text[r[0]:r[1]])]
        on = [r for r in windows if keyword_hits(text[r[0]:r[1]], keywords) >= MIN_KEYWORD_HITS]
        pools[use][snapshot_id] = on
        pools[f"{use}_off"][snapshot_id] = [r for r in windows if r not in on]
    rng = random.Random(seed)
    selected = []
    for split, use, quota in (("main", "eval", evaluation), ("train", "train", train)):
        n_on = round(quota * ON_TOPIC_SHARE)
        picked = [(s, r, "relevant") for s, r in _pick(pools[use], n_on, rng)]
        picked += [(s, r, "irrelevant")
                   for s, r in _pick(pools[f"{use}_off"], quota - len(picked), rng)]
        selected += [(split, s, r, intent) for s, r, intent in picked]
    # Training datasets (feature 004) mark off-topic windows, so their share can be reported;
    # spike chunks keep the uncurated `relevant`.
    mark_offtopic = settings.span_train is not None
    counts = {"main": 0, "train": 0}
    for n, (split, snapshot_id, (start, end), intent) in enumerate(selected, start=1):
        meta = mapping[snapshot_id]
        snapshot = load_snapshot(settings, snapshot_id)
        text = texts[snapshot_id][start:end].strip()
        save_chunk(settings, ChunkRecord.model_validate({
            "chunk_id": f"ch-{n:03d}",
            "snapshot_id": snapshot_id,
            "ranges": [(start, end)],
            "text": text,
            "token_count": approx_tokens(text),
            "split": split,
            "sub_area": meta["sub_area"],
            "source_type": snapshot.source_type,
            "region": meta["region"],
            "country": meta["country"],
            "language": meta["language"],
            "date": meta["date"],
            "license": snapshot.license,
            "relevance_intent": intent if mark_offtopic else "relevant",
            "redaction": {"patterns_version": settings.pilot.get("redaction_patterns_version",
                                                                 "redact-v1"),
                          "manual_review_at": None, "check_passed": False},
        }))
        counts[split] += 1
    return {"train": counts["train"], "main": counts["main"],
            "unused_windows": {k: sum(len(v) for v in p.values()) for k, p in pools.items()},
            "note": "relevance_intent is not curated for auto chunks (spike)"}
