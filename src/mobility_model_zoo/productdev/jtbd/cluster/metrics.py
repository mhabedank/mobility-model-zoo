"""Agreement and scores per measurement level (research R12, task T030).

Levels:
- `duplicate`: same vs. not-same on pairs (Cohen's kappa between references; pair and B-cubed
  precision, recall and F1 for candidates).
- `specificity`: {a more specific, b more specific, neither} over pairs both references call
  not-same (kappa); precision, recall and F1 of the directed "more specific than" relation.
- `cluster_level_1` and `cluster_level_2`: B-cubed F1 between partitions of the neighbourhood sets
  (fine partitions, and coarse partitions where both references gave one).

Pairs the references disagree on are contested: reported separately and scored neutrally (neither
hit nor error). Every number is agreement with the named reference models, not accuracy.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from mobility_model_zoo.productdev.jtbd.metrics import bootstrap_ci, f1, kappa

LEVELS = ("duplicate", "specificity", "cluster_level_1", "cluster_level_2")
DIRECTION = {"a_more_specific": "a", "b_more_specific": "b", "different": "neither", "same": None}


def _r(x: float | None) -> float | None:
    return None if x is None or math.isnan(x) else round(float(x), 4)


# ---- B-cubed (Amigó et al. 2009) -----------------------------------------------------------------


def bcubed(predicted: dict[str, Any], gold: dict[str, Any]) -> tuple[float, float, float]:
    """B-cubed precision, recall and F1 of two partitions given as item -> cluster label, over the
    items both partitions contain."""
    items = sorted(set(predicted) & set(gold))
    if not items:
        return (math.nan, math.nan, math.nan)
    by_pred, by_gold = defaultdict(set), defaultdict(set)
    for i in items:
        by_pred[predicted[i]].add(i)
        by_gold[gold[i]].add(i)
    precision = recall = 0.0
    for i in items:
        p, g = by_pred[predicted[i]], by_gold[gold[i]]
        both = len(p & g)
        precision += both / len(p)
        recall += both / len(g)
    precision, recall = precision / len(items), recall / len(items)
    return precision, recall, (2 * precision * recall / (precision + recall)
                               if precision + recall else 0.0)


def partition(clusters: list[dict[str, Any]]) -> dict[str, str]:
    return {m: c["cluster_id"] for c in clusters for m in c["members"]}


def coarse_partition(clusters: list[dict[str, Any]], coarse: list[dict[str, Any]] | None
                     ) -> dict[str, str] | None:
    if not coarse:
        return None
    group_of = {c: g["group_id"] for g in coarse for c in g["clusters"]}
    return {m: group_of[c["cluster_id"]] for c in clusters for m in c["members"]}


# ---- pair metrics --------------------------------------------------------------------------------


def pair_prf(predicted_same: dict[str, bool], gold_same: dict[str, bool]) -> dict[str, float | None]:
    tp = sum(1 for p, g in gold_same.items() if g and predicted_same.get(p))
    fp = sum(1 for p, g in gold_same.items() if not g and predicted_same.get(p))
    fn = sum(1 for p, g in gold_same.items() if g and not predicted_same.get(p))
    precision = tp / (tp + fp) if tp + fp else math.nan
    recall = tp / (tp + fn) if tp + fn else math.nan
    return {"precision": _r(precision), "recall": _r(recall), "f1": _r(f1(tp, fp, fn)),
            "n": len(gold_same)}


def specificity_prf(predicted: dict[str, str], gold: dict[str, str]) -> dict[str, float | None]:
    """Directed relation: a hit needs the same direction; `neither` and `same` are negatives."""
    tp = fp = fn = 0
    for pid, g in gold.items():
        gd, pd = DIRECTION.get(g), DIRECTION.get(predicted.get(pid, "different"))
        g_pos, p_pos = gd in ("a", "b"), pd in ("a", "b")
        if p_pos and g_pos and pd == gd:
            tp += 1
        else:
            fp += p_pos
            fn += g_pos
    precision = tp / (tp + fp) if tp + fp else math.nan
    recall = tp / (tp + fn) if tp + fn else math.nan
    return {"precision": _r(precision), "recall": _r(recall), "f1": _r(f1(tp, fp, fn)),
            "n": len(gold)}


# ---- reference vs. reference ---------------------------------------------------------------------


def _ci(units: list[tuple[str, Any]], stat, boot: dict[str, Any]) -> tuple[float | None, float | None]:
    low, high = bootstrap_ci(units, stat, int(boot.get("resamples", 1000)), int(boot.get("seed", 0)))
    return _r(low), _r(high)


def _kappa_stat(payloads: list) -> float:
    return kappa([p[0] for p in payloads], [p[1] for p in payloads])


def _mean_stat(payloads: list) -> float:
    vals = [p for p in payloads if not math.isnan(p)]
    return sum(vals) / len(vals) if vals else math.nan


def agreement(pairs_a: dict[str, str], pairs_b: dict[str, str], sets_a: dict[str, dict],
              sets_b: dict[str, dict], boot: dict[str, Any]) -> dict[str, Any]:
    """Reference-vs-reference statistics per level with bootstrap CIs (resampling pairs or sets)."""
    common = sorted(set(pairs_a) & set(pairs_b))
    dup = [(p, (pairs_a[p] == "same", pairs_b[p] == "same")) for p in common]
    not_same = [p for p in common if pairs_a[p] != "same" and pairs_b[p] != "same"]
    spec = [(p, (DIRECTION[pairs_a[p]], DIRECTION[pairs_b[p]])) for p in not_same]
    out: dict[str, Any] = {}
    for level, units in (("duplicate", dup), ("specificity", spec)):
        value = _kappa_stat([u for _, u in units]) if units else math.nan
        low, high = _ci(units, _kappa_stat, boot)
        out[level] = {"statistic": "cohen_kappa", "value": _r(value), "ci_low": low, "ci_high": high,
                      "n": len(units),
                      "contested": sum(1 for _, (x, y) in units if x != y)}
    for level, part in (("cluster_level_1", lambda s: partition(s["clusters"])),
                        ("cluster_level_2", lambda s: coarse_partition(s["clusters"], s.get("coarse")))):
        units = []
        for set_id in sorted(set(sets_a) & set(sets_b)):
            pa, pb = part(sets_a[set_id]), part(sets_b[set_id])
            if pa is not None and pb is not None:
                units.append((set_id, bcubed(pa, pb)[2]))
        value = _mean_stat([u for _, u in units]) if units else math.nan
        low, high = _ci(units, _mean_stat, boot)
        out[level] = {"statistic": "bcubed_f1", "value": _r(value), "ci_low": low, "ci_high": high,
                      "n": len(units)}
    return out


def consensus(pairs_a: dict[str, str], pairs_b: dict[str, str], names: tuple[str, str]
              ) -> tuple[list[dict], list[dict]]:
    agreed, contested = [], []
    for p in sorted(set(pairs_a) & set(pairs_b)):
        if pairs_a[p] == pairs_b[p]:
            agreed.append({"pair_id": p, "label": pairs_a[p]})
        else:
            contested.append({"pair_id": p, "labels": {names[0]: pairs_a[p], names[1]: pairs_b[p]}})
    return agreed, contested


# ---- candidate scores ----------------------------------------------------------------------------


def duplicate_partition(consensus_pairs: list[dict], pairs: dict[str, dict]) -> dict[str, int]:
    """Gold duplicate groups over the items of consensus pairs: components of the `same` edges."""
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for c in consensus_pairs:
        a, b = pairs[c["pair_id"]]["a"], pairs[c["pair_id"]]["b"]
        find(a), find(b)
        if c["label"] == "same":
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[max(ra, rb)] = min(ra, rb)
    roots = sorted({find(x) for x in parent})
    index = {r: n for n, r in enumerate(roots)}
    return {x: index[find(x)] for x in parent}


def candidate_pair_labels(pairs: Iterable[dict], group_of: dict[str, str],
                          parent_of: dict[str, str | None] | None = None) -> dict[str, str]:
    """The label a stage result implies for a pair: `same` if both items share a duplicate group,
    a "more specific" label if one item's group is a descendant of the other's in the specificity
    relation, else `different`."""
    parent_of = parent_of or {}

    def ancestors(g: str) -> set[str]:
        seen = set()
        while parent_of.get(g) and parent_of[g] not in seen:
            g = parent_of[g]
            seen.add(g)
        return seen

    out = {}
    for p in pairs:
        ga, gb = group_of.get(p["a"]), group_of.get(p["b"])
        if ga is None or gb is None:
            continue
        if ga == gb:
            out[p["pair_id"]] = "same"
        elif gb in ancestors(ga):
            out[p["pair_id"]] = "a_more_specific"
        elif ga in ancestors(gb):
            out[p["pair_id"]] = "b_more_specific"
        else:
            out[p["pair_id"]] = "different"
    return out


def score_candidate(predicted: dict[str, str], consensus_pairs: list[dict], contested: list[dict],
                    pairs: dict[str, dict], group_of: dict[str, str],
                    sets: dict[str, list[str]], cluster_of: dict[str, str] | None,
                    reference_sets: dict[str, dict[str, dict]], reference: dict[str, Any]
                    ) -> dict[str, Any]:
    """Scores per level against the consensus; contested pairs are counted, not scored. `reference`
    is the reference-vs-reference statistic per level (agreement.json) for the ratio."""
    gold = {c["pair_id"]: c["label"] for c in consensus_pairs if c["pair_id"] in predicted}
    dup_gold = {p: g == "same" for p, g in gold.items()}
    dup_pred = {p: predicted[p] == "same" for p in gold}
    levels: dict[str, Any] = {}
    dup_kappa = kappa([dup_pred[p] for p in sorted(gold)], [dup_gold[p] for p in sorted(gold)]) \
        if gold else math.nan
    gold_partition = duplicate_partition(consensus_pairs, pairs)
    bp, br, bf = bcubed({i: group_of[i] for i in gold_partition if i in group_of}, gold_partition)
    levels["duplicate"] = {**pair_prf(dup_pred, dup_gold), "kappa": _r(dup_kappa),
                           "bcubed": {"precision": _r(bp), "recall": _r(br), "f1": _r(bf)}}
    spec_gold = {p: g for p, g in gold.items() if g != "same"}
    spec_pairs = [p for p in sorted(spec_gold) if predicted[p] != "same"]
    spec_kappa = kappa([DIRECTION[predicted[p]] for p in spec_pairs],
                       [DIRECTION[spec_gold[p]] for p in spec_pairs]) if spec_pairs else math.nan
    levels["specificity"] = {**specificity_prf(predicted, spec_gold), "kappa": _r(spec_kappa)}
    if cluster_of is not None:
        values = []
        for set_id, items in sorted(sets.items()):
            pred = {i: cluster_of[i] for i in items if i in cluster_of}
            refs = [partition(r[set_id]["clusters"]) for r in reference_sets.values() if set_id in r]
            values += [bcubed(pred, ref)[2] for ref in refs]
        levels["cluster_level_1"] = {"bcubed_f1": _r(_mean_stat(values) if values else math.nan),
                                     "n": len(values)}
    for level, value_key in (("duplicate", "kappa"), ("specificity", "kappa"),
                             ("cluster_level_1", "bcubed_f1")):
        if level not in levels:
            continue
        ref = (reference.get(level) or {}).get("value")
        own = levels[level].get(value_key)
        levels[level]["ratio_to_reference"] = _r(own / ref) if own is not None and ref else None
    return {"levels": levels, "consensus_pairs": len(gold), "contested_pairs": len(contested),
            "contested_rule": "neutral: contested pairs are neither hits nor errors"}


# ---- `jtbd cluster agreement` --------------------------------------------------------------------


def analysis_dir(settings) -> Any:
    return settings.data_dir / "analysis" / settings.benchmark_version


def run_agreement(settings, split: str) -> dict[str, Any]:
    """Reference-vs-reference statistics of one split, consensus and contested pairs; advances the
    benchmark from `frozen` to `piloted`."""
    import yaml

    from mobility_model_zoo.productdev.jtbd.cluster import bench
    from mobility_model_zoo.productdev.jtbd.cluster.label import reference_runs
    from mobility_model_zoo.productdev.jtbd.jsonio import read_jsonl, write_json, write_jsonl

    runs = reference_runs(settings, split)
    names = tuple(sorted(runs))
    pairs = [{r["pair_id"]: r["label"] for r in read_jsonl(runs[n] / "pairs.jsonl")} for n in names]
    sets = [{r["set_id"]: r for r in read_jsonl(runs[n] / "sets.jsonl")} for n in names]
    criteria = yaml.safe_load((settings.base / bench.cfg(settings)["criteria"]).read_text())
    stats = agreement(pairs[0], pairs[1], sets[0], sets[1], criteria.get("bootstrap") or {})
    agreed, contested = consensus(pairs[0], pairs[1], names)
    out = analysis_dir(settings)
    write_jsonl(out / f"consensus-{split}.jsonl", agreed)
    write_jsonl(out / f"contested-{split}.jsonl", contested)
    result = {
        "benchmark_version": settings.benchmark_version, "split": split,
        "references": list(names), "runs": [runs[n].name for n in names],
        "levels": stats, "consensus_pairs": len(agreed), "contested_pairs": len(contested),
        "statement": f"agreement between {names[0]} and {names[1]} on "
                     f"{settings.benchmark_version} ({split}); not measured against human labels",
    }
    # The development split serves tuning only; the pilot decides on test (or holdout).
    write_json(out / ("agreement-dev.json" if split == "dev" else "agreement.json"), result)
    manifest = bench.load_manifest(settings)
    if split != "dev" and manifest and manifest["state"] == "frozen":
        bench.set_state(settings, "piloted", f"agreement on {split}")
    return result
