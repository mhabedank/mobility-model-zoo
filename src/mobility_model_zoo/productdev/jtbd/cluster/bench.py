"""Benchmark `cluster-v1`: item pool, split by snapshot, stratified pairs, neighbourhood sets,
freezing (research R10, tasks T026 and T027).

The pool is built from a span run of the released scout-large over stored chunks of the configured
corpora; the extraction pilot's holdout chunks never enter it. Sources are split by snapshot into
`holdout` (re-pilot reserve), `dev` (tuning) and `test`, so near-duplicates cannot leak between
splits. Pairs are same-kind and stratified by two samplers that are not candidate encoders (LaBSE
cosine, lexical token-set ratio); sets are a seed item and its nearest neighbours of any kind.

Pool text stays under `data/cluster/` (never published, spec FR-027); the pair and set lists hold
ids, split and stratum only, and the manifest under `topics/productdev/benchmarks/` holds hashes.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from mobility_model_zoo.productdev.jtbd.cluster.bundle import items_from, read_bundle_lines
from mobility_model_zoo.productdev.jtbd.cluster.embed import EmbeddingCache, Encoder, make_encoder
from mobility_model_zoo.productdev.jtbd.config import Settings
from mobility_model_zoo.productdev.jtbd.errors import (
    FrozenHashMismatch,
    UsageError,
    ValidationFailed,
)
from mobility_model_zoo.productdev.jtbd.jsonio import read_jsonl, write_json, write_jsonl

SPLITS = ("dev", "test", "holdout")
STRATA = ("high", "middle", "random")
SAMPLERS = {"labse", "lexical"}
CANDIDATE_SETTINGS = ("cluster-baseline.yaml", "cluster-e5-small.yaml", "cluster-gte-base.yaml")
STATES = ("draft", "frozen", "piloted", "revise", "decided")
WORD = re.compile(r"[^\W\d_]{3}")  # a run of three letters in any script


def labelable(quote: str) -> bool:
    """Fragments without any word (".", "B.", "Dr.") are not sampled into pairs or sets: a
    reference cannot judge them, so labels on them measure nothing. They stay in the pool."""
    return bool(WORD.search(quote))


@dataclass(frozen=True)
class PoolItem:
    item_id: str
    kind: str
    quote: str
    source_id: str
    snapshot_id: str
    patterns_version: str | None
    split: str = ""


def cfg(settings: Settings) -> dict[str, Any]:
    if not settings.cluster:
        raise UsageError(f"{settings.config_path} has no `cluster` block (use cluster-v1.yaml)")
    return settings.cluster


def bench_dir(settings: Settings) -> Path:
    return settings.data_dir / "bench" / settings.benchmark_version


def manifest_path(settings: Settings) -> Path:
    return settings.benchmarks_dir / settings.benchmark_version / "manifest.json"


# ---- pool ----------------------------------------------------------------------------------------


def pool_from_config(config_path: Path, run_id: str) -> tuple[list[dict[str, Any]], list[PoolItem]]:
    """Bundle lines and pool items of one corpus: the span run over its stored chunks, without the
    chunks of its holdout split (the extraction pilot's holdout stays untouched)."""
    from mobility_model_zoo.productdev.jtbd.cluster.collect import source_lines
    from mobility_model_zoo.productdev.jtbd.config import load_settings
    from mobility_model_zoo.productdev.jtbd.corpus.store import chunk_map

    corpus = load_settings(config_path)
    holdout = set(chunk_map(corpus, "holdout"))
    chunks = {k: v for split in ("main", "train", "holdout")
              for k, v in chunk_map(corpus, split).items()}
    lines = without_holdout(source_lines(corpus, run_id), holdout)
    meta = {}
    for line in lines:
        chunk = chunks[line["source_id"].split(":", 1)[1]]
        meta[line["source_id"]] = (chunk.snapshot_id, chunk.redaction.patterns_version)
    return lines, pool_items(lines, meta)


def without_holdout(lines: list[dict[str, Any]], holdout_chunks: set[str]) -> list[dict[str, Any]]:
    """Drop sources whose chunk is in the extraction pilot's holdout (source id `<version>:<chunk>`)."""
    return [line for line in lines if line["source_id"].split(":", 1)[1] not in holdout_chunks]


def pool_items(lines: list[dict[str, Any]], meta: dict[str, tuple[str, str | None]]) -> list[PoolItem]:
    """Items of bundle lines; `meta` maps source id -> (snapshot id, redaction patterns version)."""
    items = items_from(read_bundle_lines(lines))
    return [PoolItem(i.item_id, i.kind, i.quote, i.source_id, *meta[i.source_id]) for i in items]


def split_snapshots(snapshots: list[str], dev_fraction: float, holdout_fraction: float, seed: int
                    ) -> dict[str, str]:
    """Snapshot -> split. Shuffled with the seed; the holdout reserve first, then dev, rest test."""
    ordered = sorted(set(snapshots))
    rng = np.random.default_rng(seed)
    rng.shuffle(ordered)
    n_hold = round(len(ordered) * holdout_fraction)
    n_dev = round(len(ordered) * dev_fraction)
    out = {}
    for i, snap in enumerate(ordered):
        out[snap] = "holdout" if i < n_hold else "dev" if i < n_hold + n_dev else "test"
    return out


# ---- samplers ------------------------------------------------------------------------------------


def check_samplers(cluster: dict[str, Any], config_dir: Path) -> None:
    """Samplers are LaBSE and lexical only, never a candidate encoder (research R10)."""
    names = {s.get("name") for s in cluster["pairs"]["samplers"]}
    if names != SAMPLERS:
        raise UsageError(f"pair samplers must be exactly {sorted(SAMPLERS)}, got {sorted(names)}")
    labse = next(s for s in cluster["pairs"]["samplers"] if s["name"] == "labse")
    for name in CANDIDATE_SETTINGS:
        path = config_dir / name
        if path.exists():
            encoder = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("encoder", {})
            if encoder.get("model_id") == labse["model_id"]:
                raise UsageError(f"sampler {labse['model_id']} is a candidate encoder in {name}")


def labse_encoder(cluster: dict[str, Any]) -> Encoder:
    labse = next(s for s in cluster["pairs"]["samplers"] if s["name"] == "labse")
    return make_encoder({"model_id": labse["model_id"], "revision": labse.get("revision"),
                         "licence_basis": labse.get("licence_basis"),
                         "pooling": labse.get("pooling", "pooler"), "batch_size": 64,
                         "max_length": 128})


LEXICAL_METHODS = ("token_sort_ratio", "token_set_ratio")


def lexical_similarity(quotes: list[str], method: str = "token_sort_ratio") -> np.ndarray:
    """Pairwise lexical similarity in [0, 1]. `token_sort_ratio` (default) compares whole word
    sequences regardless of order; `token_set_ratio` scores 1.0 whenever one quote's words are a
    subset of the other's, which makes every short generic quote a top pair."""
    from rapidfuzz import fuzz, process

    if method not in LEXICAL_METHODS:
        raise UsageError(f"lexical sampler method {method!r}: use one of {', '.join(LEXICAL_METHODS)}")
    if not quotes:
        return np.zeros((0, 0), dtype=np.float32)
    return process.cdist(quotes, quotes, scorer=getattr(fuzz, method), dtype=np.float32) / 100.0


def pair_id(a: str, b: str) -> str:
    lo, hi = sorted((a, b))
    return "pr-" + hashlib.sha256(f"{lo}|{hi}".encode()).hexdigest()[:12]


BANDS = {"high": 0.10, "middle": 0.50}  # upper bounds as shares of ranked candidate pairs


def sample_pairs(items: list[PoolItem], vectors: np.ndarray, n: int, shares: dict[str, float],
                 seed: int, split: str, neighbours: int = 10,
                 bands: dict[str, float] | None = None, similarity: dict | None = None,
                 lexical: str = "token_sort_ratio") -> list[dict[str, Any]]:
    """Same-kind pairs of one split, stratified. Candidate pairs are each item's nearest neighbours
    under either sampler, ranked by the larger of the two similarities; `high` draws from the top
    `bands.high` share of them, `middle` from the band up to `bands.middle`, `random` uniformly from
    all same-kind pairs. Order of a and b is random. `similarity`, if given, receives the sampler
    similarity of the drawn pairs per stratum (for the build report, never stored with the pairs)."""
    bands = {**BANDS, **(bands or {})}
    rng = np.random.default_rng(seed)
    by_kind: dict[str, list[int]] = defaultdict(list)
    for i, item in enumerate(items):
        by_kind[item.kind].append(i)
    candidates: dict[tuple[int, int], float] = {}
    for idx in by_kind.values():
        if len(idx) < 2:
            continue
        cos = vectors[idx] @ vectors[idx].T
        lex = lexical_similarity([items[i].quote for i in idx], lexical)
        for sims in (cos, lex):
            np.fill_diagonal(sims, -np.inf)
            k = min(neighbours, len(idx) - 1)
            top = np.argpartition(-sims, k - 1, axis=1)[:, :k]
            for r, cols in enumerate(top):
                for c in cols:
                    a, b = sorted((idx[r], idx[int(c)]))
                    candidates[(a, b)] = max(float(max(cos[r, c], lex[r, c])),
                                             candidates.get((a, b), -1.0))
    ranked = sorted(candidates, key=lambda p: (-candidates[p], items[p[0]].item_id,
                                               items[p[1]].item_id))
    cut_high = max(1, round(len(ranked) * bands["high"]))
    cut_middle = max(cut_high, round(len(ranked) * bands["middle"]))
    pools = {"high": ranked[:cut_high], "middle": ranked[cut_high:cut_middle]}
    taken: set[tuple[int, int]] = set()
    out = []
    targets = {s: round(n * shares.get(s, 0)) for s in STRATA}
    for stratum in ("high", "middle"):
        options = [p for p in pools[stratum] if p not in taken]
        picks = rng.permutation(len(options))[: targets[stratum]]
        for j in sorted(picks):
            taken.add(options[j])
            out.append((options[j], stratum))
    kinds = [k for k, idx in sorted(by_kind.items()) if len(idx) >= 2]
    tries = 0
    while sum(1 for _, s in out if s == "random") < targets["random"] and kinds and tries < 100 * n:
        tries += 1
        idx = by_kind[kinds[rng.integers(len(kinds))]]
        a, b = sorted(rng.choice(len(idx), 2, replace=False))
        p = (idx[a], idx[b])
        if p not in taken:
            taken.add(p)
            out.append((p, "random"))
    if similarity is not None:
        for (a, b), stratum in out:
            sim = candidates.get((a, b))
            if sim is not None:
                similarity.setdefault(stratum, []).append(sim)
    rows = []
    for (a, b), stratum in out:
        first, second = (a, b) if rng.random() < 0.5 else (b, a)
        rows.append({"pair_id": pair_id(items[a].item_id, items[b].item_id),
                     "a": items[first].item_id, "b": items[second].item_id,
                     "split": split, "stratum": stratum})
    return sorted(rows, key=lambda r: r["pair_id"])


def build_sets(items: list[PoolItem], vectors: np.ndarray, n_sets: int, size: int, seed: int,
               split: str) -> list[dict[str, Any]]:
    """`n_sets` sets of `size` items: a random seed item and its nearest neighbours of any kind.
    Seeds are not reused and are not inside an earlier set."""
    if len(items) < size:
        raise ValidationFailed(f"split {split} has {len(items)} items, fewer than a set of {size}")
    rng = np.random.default_rng(seed)
    order = list(rng.permutation(len(items)))
    used: set[int] = set()
    sets = []
    for seed_idx in order:
        if len(sets) == n_sets:
            break
        if seed_idx in used:
            continue
        sims = vectors @ vectors[seed_idx]
        sims[seed_idx] = np.inf
        members = [int(i) for i in np.argsort(-sims, kind="stable")[:size]]
        used.update(members)
        sets.append({"set_id": f"set-{split}-{len(sets) + 1:02d}", "split": split,
                     "items": sorted(items[i].item_id for i in members)})
    if len(sets) < n_sets:
        raise ValidationFailed(f"split {split}: only {len(sets)} of {n_sets} sets could be built")
    return sets


# ---- build ---------------------------------------------------------------------------------------


def build(settings: Settings, encoder: Encoder | None = None,
          corpora: list[tuple[list[dict[str, Any]], list[PoolItem]]] | None = None
          ) -> dict[str, Any]:
    """`jtbd cluster bench build`: pool, split, pairs and sets under data/cluster/bench/<version>/.
    `corpora` (bundle lines and pool items per corpus) and `encoder` replace the span runs and LaBSE
    in tests."""
    cluster = cfg(settings)
    check_samplers(cluster, settings.config_path.parent)
    state = load_manifest(settings)
    if state and state["state"] != "draft":
        raise FrozenHashMismatch(f"benchmark {settings.benchmark_version} is {state['state']}; "
                                 "a frozen benchmark is never rebuilt")
    if corpora is None:
        run = cluster["pool"].get("span_run")
        if not run:
            raise UsageError("cluster.pool.span_run is not set (task T063)")
        runs = run if isinstance(run, dict) else {c: run for c in cluster["pool"]["configs"]}
        corpora = [pool_from_config(settings.base / c, r) for c, r in sorted(runs.items())]
    lines = [line for corpus_lines, _ in corpora for line in corpus_lines]
    pool = [item for _, items in corpora for item in items]
    if len({i.item_id for i in pool}) != len(pool):
        raise ValidationFailed("item ids repeat across corpora")
    seed = int(cluster["seed"])
    splits = split_snapshots([i.snapshot_id for i in pool], float(cluster["dev_fraction"]),
                             float(cluster.get("holdout_fraction", 0.15)), seed)
    pool = sorted((PoolItem(**{**asdict(i), "split": splits[i.snapshot_id]}) for i in pool),
                  key=lambda i: i.item_id)
    if encoder is None:
        encoder = labse_encoder(cluster)
    cache = EmbeddingCache(settings.data_dir / "cache", encoder.model_id, encoder.revision,
                           getattr(encoder, "variant", ""))
    vectors = cache.get([i.quote for i in pool], encoder)
    pairs_cfg, sets_cfg = cluster["pairs"], cluster["sets"]
    pairs, sets, similarity = [], [], {}
    lexical = next(s for s in pairs_cfg["samplers"] if s["name"] == "lexical").get(
        "method", "token_sort_ratio")
    for k, split in enumerate(SPLITS):
        idx = [j for j, item in enumerate(pool) if item.split == split and labelable(item.quote)]
        sub = [pool[j] for j in idx]
        pairs += sample_pairs(sub, vectors[idx], int(pairs_cfg[split]), pairs_cfg["strata"],
                              seed + k, split, bands=pairs_cfg.get("bands"),
                              similarity=similarity.setdefault(split, {}), lexical=lexical)
        sets += build_sets(sub, vectors[idx], int(sets_cfg[split]), int(sets_cfg["size"]),
                           seed + 10 + k, split)
    out = bench_dir(settings)
    write_jsonl(out / "pool.jsonl", [asdict(i) for i in pool])
    write_jsonl(out / "pool-bundle.jsonl", lines)
    write_jsonl(out / "pairs.jsonl", pairs)
    write_jsonl(out / "sets.jsonl", sets)
    save_manifest(settings, {"version": settings.benchmark_version, "state": "draft",
                             "built_at": _now(), "hashes": {}, "counts": counts(pool, pairs, sets)})
    spread = {split: {st: {"min": round(min(v), 3), "median": round(float(np.median(v)), 3),
                           "max": round(max(v), 3)} for st, v in sorted(by.items())}
              for split, by in similarity.items()}
    return {"bench": str(out), **counts(pool, pairs, sets), "sampler_similarity": spread,
            "not_sampled_fragments": sum(1 for i in pool if not labelable(i.quote))}


def counts(pool: list[PoolItem], pairs: list[dict], sets: list[dict]) -> dict[str, Any]:
    return {
        "items": {s: sum(1 for i in pool if i.split == s) for s in SPLITS},
        "snapshots": {s: len({i.snapshot_id for i in pool if i.split == s}) for s in SPLITS},
        "pairs": {s: {st: sum(1 for p in pairs if p["split"] == s and p["stratum"] == st)
                      for st in STRATA} for s in SPLITS},
        "sets": {s: sum(1 for x in sets if x["split"] == s) for s in SPLITS},
    }


def load_pool(settings: Settings) -> dict[str, dict[str, Any]]:
    return {r["item_id"]: r for r in read_jsonl(bench_dir(settings) / "pool.jsonl")}


def load_pairs(settings: Settings, split: str | None = None) -> list[dict[str, Any]]:
    return [r for r in read_jsonl(bench_dir(settings) / "pairs.jsonl")
            if split is None or r["split"] == split]


def load_sets(settings: Settings, split: str | None = None) -> list[dict[str, Any]]:
    return [r for r in read_jsonl(bench_dir(settings) / "sets.jsonl")
            if split is None or r["split"] == split]


def pool_sources(settings: Settings, split: str):
    """Bundle sources of the pool whose items lie in one split (a source is one chunk of one
    snapshot, so all its items share the split)."""
    split_of = {r["source_id"]: r["split"] for r in read_jsonl(bench_dir(settings) / "pool.jsonl")}
    lines = [line for line in read_jsonl(bench_dir(settings) / "pool-bundle.jsonl")
             if split_of.get(line["source_id"]) == split]
    return read_bundle_lines(lines, f"pool-bundle ({split})")


# ---- manifest and freezing (T027) ----------------------------------------------------------------


def _now() -> str:
    return datetime.now(UTC).isoformat()


def load_manifest(settings: Settings) -> dict[str, Any] | None:
    path = manifest_path(settings)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def save_manifest(settings: Settings, manifest: dict[str, Any]) -> None:
    write_json(manifest_path(settings), manifest)


def current_hashes(settings: Settings) -> dict[str, str]:
    """Hashes of everything the reference labels depend on (data-model "Benchmark")."""
    from mobility_model_zoo.productdev.jtbd.cluster.prompt import prompt_sha256, wire_schema_sha256
    from mobility_model_zoo.productdev.jtbd.freeze import sha256_canonical

    cluster, base = cfg(settings), settings.base
    out = {
        "guideline": sha256_canonical(base / cluster["guideline"]),
        "examples": sha256_canonical(base / cluster["examples"]),
        "prompt": prompt_sha256(settings),
        "wire_schema": wire_schema_sha256(),
        "criteria": sha256_canonical(base / cluster["criteria"]),
        "budget": sha256_canonical(settings.paths["budget"]),
    }
    for name in ("pairs", "sets", "pool"):
        path = bench_dir(settings) / f"{name}.jsonl"
        if not path.exists():
            raise UsageError(f"{path} is missing; run `jtbd cluster bench build` first")
        out[name] = sha256_canonical(path)
    return out


REVISABLE = ("guideline", "examples", "prompt")


def freeze(settings: Settings) -> dict[str, Any]:
    """`jtbd cluster freeze`: draft -> frozen. After a `revise` decision it freezes the revised
    guideline, examples and prompt once more (everything else must be unchanged) for the re-pilot
    on the holdout split. Freezing a frozen benchmark again only verifies it."""
    manifest = load_manifest(settings)
    if manifest is None:
        raise UsageError("no benchmark to freeze; run `jtbd cluster bench build` first")
    hashes = current_hashes(settings)
    if manifest["state"] == "revise":
        changed = sorted(k for k, v in manifest["hashes"].items()
                         if hashes.get(k) != v and k not in REVISABLE)
        if changed:
            raise FrozenHashMismatch(f"only {', '.join(REVISABLE)} may change for the re-pilot; "
                                     f"changed: {', '.join(changed)}")
        manifest.setdefault("revisions", []).append({"at": _now(), "previous": manifest["hashes"]})
        manifest.update(hashes=hashes, state="frozen")
        manifest.setdefault("events", []).append({"at": _now(), "state": "frozen",
                                                  "event": "revised guideline frozen for re-pilot"})
        save_manifest(settings, manifest)
        return {"manifest": str(manifest_path(settings)), "state": "frozen", "revised": True}
    if manifest["state"] != "draft":
        verify(settings, manifest)
        return {"manifest": str(manifest_path(settings)), "state": manifest["state"], "verified": True}
    manifest.update(state="frozen", frozen_at=_now(), hashes=hashes,
                    retention_review_by=_review_date(cfg(settings)), reruns=0, events=[])
    save_manifest(settings, manifest)
    return {"manifest": str(manifest_path(settings)), "state": "frozen", "hashes": hashes}


def _review_date(cluster: dict[str, Any]) -> str:
    months = int((cluster.get("retention") or {}).get("review_by_months_after_freeze", 24))
    today = datetime.now(UTC).date()
    year, month = divmod(today.month - 1 + months, 12)
    return today.replace(year=today.year + year, month=month + 1, day=min(today.day, 28)).isoformat()


def verify(settings: Settings, manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    """Exit 3 when anything frozen changed since the freeze."""
    manifest = manifest or load_manifest(settings)
    if manifest is None or manifest["state"] == "draft":
        raise UsageError(f"benchmark {settings.benchmark_version} is not frozen")
    current = current_hashes(settings)
    changed = sorted(k for k, v in manifest["hashes"].items() if current.get(k) != v)
    if changed:
        raise FrozenHashMismatch(f"frozen artifacts changed since the freeze: {', '.join(changed)}")
    return manifest


def set_state(settings: Settings, state: str, event: str) -> dict[str, Any]:
    if state not in STATES:
        raise UsageError(f"unknown benchmark state {state}")
    manifest = load_manifest(settings) or {}
    manifest["state"] = state
    manifest.setdefault("events", []).append({"at": _now(), "state": state, "event": event})
    save_manifest(settings, manifest)
    return manifest
