"""Helpers of the cluster tests (feature 009). No test downloads a model."""

from __future__ import annotations

import json
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "cluster"
BUNDLES = FIXTURE / "bundles"
SETTINGS = FIXTURE / "settings.yaml"


def span_output(items: list[dict], dimensions=("actor_type",), relevant: bool = True) -> dict:
    return {"output_format_version": "jtbd-span-v1", "relevant": relevant,
            "relevance_probability": 0.9 if relevant else 0.1, "dimensions": list(dimensions),
            "items": items}


def source_line(source_id: str, items: list[dict], **extra) -> dict:
    line = {"input_format_version": "jtbd-cluster-input-v1", "source_id": source_id,
            "source_class": "report", "date": "2026-03-01", "output": span_output(items)}
    line.update(extra)
    return line


def item(kind: str, quote: str, start: int = 0, actor: str | None = "individual") -> dict:
    out = {"kind": kind, "quote": quote, "start": start, "end": start + len(quote), "score": 0.9}
    if actor:
        out["actor_type"] = actor
    return out


def write_bundle(path: Path, lines: list[dict]) -> Path:
    path.write_text("".join(json.dumps(line, ensure_ascii=False) + "\n" for line in lines),
                    encoding="utf-8")
    return path
