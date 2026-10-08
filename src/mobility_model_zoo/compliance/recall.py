"""Redaction recall on the synthetic test set (decision D9: at least 0.95).

Two pipelines are measured: the jtbd pattern redaction (what is replaced before labeling) and the
compliance PII scan (what blocks a batch before it leaves the machine, check C-P2). A gold span counts
as caught when a hit overlaps it. The local model review (`jtbd corpus pii-review`) comes on top and
is not part of this deterministic measurement.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from mobility_model_zoo.compliance.scan import pii

DEFAULT_SET = (
    Path(__file__).resolve().parents[3]
    / "tests"
    / "fixtures"
    / "compliance"
    / "redaction-set"
    / "items.jsonl"
)


def _redaction_hits(text: str) -> list[tuple[int, int]]:
    from mobility_model_zoo.productdev.jtbd.corpus.redact import PATTERNS

    return [(m.start(), m.end()) for _, pattern, _ in PATTERNS for m in re.finditer(pattern, text)]


def measure(items: list[dict[str, Any]]) -> dict[str, Any]:
    per_kind: dict[str, dict[str, int]] = {}
    for item in items:
        red = _redaction_hits(item["text"])
        scan = [(h.start, h.end) for h in pii(item["text"])]
        for span in item["spans"]:
            k = per_kind.setdefault(span["kind"], {"n": 0, "redaction": 0, "scan": 0, "combined": 0})
            k["n"] += 1
            hit_r = any(s < span["end"] and e > span["start"] for s, e in red)
            hit_s = any(s < span["end"] and e > span["start"] for s, e in scan)
            k["redaction"] += hit_r
            k["scan"] += hit_s
            k["combined"] += hit_r or hit_s
    total = {
        key: sum(v[key] for v in per_kind.values()) for key in ("n", "redaction", "scan", "combined")
    }
    rate = lambda d, key: round(d[key] / d["n"], 4) if d["n"] else None  # noqa: E731
    return {
        "items": len(items),
        "recall": {key: rate(total, key) for key in ("redaction", "scan", "combined")},
        "per_kind": {
            kind: {key: rate(v, key) for key in ("redaction", "scan", "combined")} | {"n": v["n"]}
            for kind, v in sorted(per_kind.items())
        },
    }


def load(path: Path = DEFAULT_SET) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
