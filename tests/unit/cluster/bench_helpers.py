"""A small synthetic benchmark for the user story 2 tests (feature 009): fictional quotes, fixed
vectors, mock reference models. Nothing is downloaded and nothing is sent anywhere."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

import yaml
from cluster_helpers import item, source_line

from mobility_model_zoo.productdev.jtbd.cluster.bench import PoolItem, pool_items
from mobility_model_zoo.productdev.jtbd.cluster.embed import TableEncoder

REPO = Path(__file__).resolve().parents[3]
MINI = REPO / "tests" / "fixtures" / "mini-corpus"
TOPICS = ("bus", "tram", "parking", "bike", "charging", "train")
WORDS = {"job": "I want to {t} reliably every morning",
         "pain": "The {t} situation annoys me every day",
         "gain": "A better {t} option would save me time"}


@dataclass
class BenchEnv:
    root: Path
    config: Path
    lines: list[dict]
    items: list[PoolItem]

    def settings(self):
        from mobility_model_zoo.productdev.jtbd.config import load_settings

        return load_settings(self.config)

    def encoder(self):
        return TableEncoder({}, dim=16)

    def build(self):
        from mobility_model_zoo.productdev.jtbd.cluster.bench import build

        return build(self.settings(), encoder=self.encoder(), corpora=[(self.lines, self.items)])


def corpus(n_snapshots: int = 24) -> tuple[list[dict], list[PoolItem]]:
    lines, meta = [], {}
    for s in range(n_snapshots):
        quotes, start = [], 0
        for kind, template in WORDS.items():
            for variant in ("", " again"):
                q = template.format(t=TOPICS[(s + len(quotes)) % len(TOPICS)]) + variant + f" ({s})"
                quotes.append(item(kind, q, start))
                start += len(q) + 1
        sid = f"fx:chunk-{s:03d}"
        lines.append(source_line(sid, quotes, origin=f"https://forum.example/t/{s}"))
        meta[sid] = (f"snap-{s:03d}", "redact-v2")
    return lines, pool_items(lines, meta)


def make_env(root: Path, **cluster_overrides) -> BenchEnv:
    root.mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO / "configs/productdev/jtbd/cluster-criteria.yaml", root / "criteria.yaml")
    (root / "budget.yaml").write_text(yaml.safe_dump(
        {"budget_eur": 20, "key_cap_eur": 18, "openrouter_fee": 0.055, "prices": {}}))
    (root / "models.yaml").write_text(yaml.safe_dump({"models": [
        {"model_id": "mock-a", "family": "fam-a", "backend": "mock", "host": "local",
         "role": "reference", "benchmark_labeler": True},
        {"model_id": "mock-b", "family": "fam-b", "backend": "mock", "host": "local",
         "role": "reference", "benchmark_labeler": True},
        {"model_id": "mock-small", "family": "fam-c", "backend": "mock", "host": "local",
         "role": "baseline"},
    ]}))
    cluster = {
        "pool": {"span_run": None, "configs": [], "splits": ["main"], "exclude_splits": ["holdout"]},
        "split_by": "snapshot", "dev_fraction": 0.30, "holdout_fraction": 0.15, "seed": 7,
        "pairs": {"test": 30, "dev": 12, "holdout": 9,
                  "strata": {"high": 0.34, "middle": 0.33, "random": 0.33}, "same_kind_only": True,
                  "samplers": [{"name": "labse", "model_id": "sentence-transformers/LaBSE",
                                "revision": "836121a0533e5664b21c7aacc5d22951f2b8b25b",
                                "licence_basis": "Apache-2.0"},
                               {"name": "lexical", "method": "token_set_ratio"}]},
        "sets": {"test": 2, "dev": 1, "holdout": 1, "size": 8, "neighbourhood_k": 7},
        "reference_models": ["mock-a", "mock-b"], "batch_size": 20, "max_retries": 1,
        "guideline": str(REPO / "topics/productdev/guideline/cluster-v1/guideline-cluster-v1.md"),
        "examples": str(REPO / "topics/productdev/guideline/cluster-v1/examples.yaml"),
        "criteria": "criteria.yaml",
    }
    cluster.update(cluster_overrides)
    config = {
        "root": ".", "benchmark_version": "cluster-test", "test_fixture": True,
        "budget_name": "cluster-test",
        "paths": {"guideline": str(MINI / "guideline.md"), "examples": str(MINI / "examples"),
                  "domain": str(MINI / "domain.yaml"), "models": "models.yaml",
                  "criteria": str(MINI / "decision-criteria.yaml"),
                  "teacher_scoring": str(MINI / "teacher-scoring.yaml"), "budget": "budget.yaml",
                  "data": "data", "benchmarks": "benchmarks", "reports": "reports", "mock": "mock"},
        "cluster": cluster,
    }
    path = root / "cluster-test.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False))
    lines, items = corpus()
    return BenchEnv(root, path, lines, items)


def answer_units(env: BenchEnv, model: str, split: str, pair_label=None, set_answer=None) -> None:
    """Mock answers for every unit of a split. pair_label(pair) -> label; set_answer(items) -> dict."""
    from mobility_model_zoo.productdev.jtbd.cluster.label import units_for

    directory = env.root / "mock" / model
    directory.mkdir(parents=True, exist_ok=True)
    pair_label = pair_label or (lambda p: "different")
    set_answer = set_answer or (lambda ids: {"clusters": [{"cluster_id": "c1", "members": ids}],
                                             "coarse": None})
    for unit in units_for(env.settings(), split):
        if unit["type"] == "pairs":
            answer = {"pairs": [{"pair_id": p["pair_id"], "label": pair_label(p)}
                                for p in unit["pairs"]]}
        else:
            answer = set_answer(list(unit["items"]))
        (directory / f"{unit['unit']}.json").write_text(json.dumps(answer))
