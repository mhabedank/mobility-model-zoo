"""`jtbd cluster perf`: wall time and peak memory of the stage (research R17, task T056).

The stage runs in a child process with the Hugging Face hub offline, so models must be cached and
nothing is downloaded during the measurement. Input is the benchmark pool (`real`) or a scale set
made by resampling the pool's sources with unique source ids and a non-word suffix on every quote,
which defeats exact-copy merging (`scale-set`). The scale set measures time and memory only.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mobility_model_zoo.productdev.jtbd.cluster import bench
from mobility_model_zoo.productdev.jtbd.cluster.metrics import analysis_dir
from mobility_model_zoo.productdev.jtbd.cluster.stage import load_stage_settings
from mobility_model_zoo.productdev.jtbd.config import Settings
from mobility_model_zoo.productdev.jtbd.errors import ValidationFailed
from mobility_model_zoo.productdev.jtbd.jsonio import read_jsonl, write_json, write_jsonl
from mobility_model_zoo.productdev.jtbd.perf import hardware_info, process_rss_mb

OFFLINE = {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}


def item_count(lines: list[dict[str, Any]]) -> int:
    return sum(len(line["output"]["items"]) for line in lines)


def scale_lines(lines: list[dict[str, Any]], n: int) -> list[dict[str, Any]]:
    """At least `n` items: the sources again and again, copy k with source id `<id>~<k>`, its own
    origin and the suffix ` ~<k>` on every quote (span end moved by the suffix)."""
    if not lines or item_count(lines) == 0:
        raise ValidationFailed("the pool has no items to scale")
    out = [dict(line) for line in lines]
    total, k = item_count(lines), 0
    while total < n:
        k += 1
        for line in lines:
            if total >= n:
                break
            suffix = f" ~{k}"
            items = [{**it, "quote": it["quote"] + suffix, "end": it["end"] + len(suffix)}
                     for it in line["output"]["items"]]
            out.append({**line, "source_id": f"{line['source_id']}~{k}",
                        "origin": f"{line['origin']}#scale-{k}" if line.get("origin") else None,
                        "text_sha256": None, "output": {**line["output"], "items": items}})
            total += len(items)
    return out


def perf(settings: Settings, stage_path: Path, scale: int | None = None,
         hardware: str | None = None, lines: list[dict[str, Any]] | None = None
         ) -> dict[str, Any]:
    stage_settings, digest = load_stage_settings(stage_path)
    if lines is None:
        lines = list(read_jsonl(bench.bench_dir(settings) / "pool-bundle.jsonl"))
    origin = "real"
    if scale:
        lines, origin = scale_lines(lines, scale), "scale-set"
    with tempfile.TemporaryDirectory(prefix="cluster-perf-") as tmp:
        bundle = Path(tmp) / "input.jsonl"
        write_jsonl(bundle, lines)
        env = {**os.environ, **OFFLINE}
        start = time.monotonic()
        child = subprocess.Popen(
            [sys.executable, "-m", "mobility_model_zoo.productdev.jtbd.cluster.perfworker",
             str(Path(stage_path).resolve()), str(bundle)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        sampled: float | None = None
        while child.poll() is None:
            value = process_rss_mb(child.pid)
            if value is not None:
                sampled = value if sampled is None else max(sampled, value)
            time.sleep(0.05)
        out, err = child.communicate()
        wall = time.monotonic() - start
    if child.returncode != 0:
        raise ValidationFailed(f"perf worker failed: {err.strip()[-800:]}")
    measured = json.loads(out.strip().splitlines()[-1])
    peak = max(v for v in (sampled, measured["ru_maxrss_mb"]) if v is not None)
    name = stage_settings.get("name") or Path(stage_path).stem
    record = {
        "candidate": name, "settings": str(stage_path), "settings_sha256": digest,
        "origin": origin, "items": item_count(lines), "sources": len(lines),
        "wall_s": round(wall, 2), "stage_s": measured["stage_s"],
        "peak_rss_mb": round(peak, 1),
        "peak_rss_sampled_mb": None if sampled is None else round(sampled, 1),
        "groups": measured["groups"], "clusters": measured["clusters"],
        "hardware": hardware_info(hardware), "threads": measured["threads"],
        "conditions": "models cached beforehand; Hugging Face hub offline in the child process",
        "measured_at": datetime.now(UTC).isoformat(),
    }
    suffix = f"-scale{scale}" if scale else ""
    write_json(analysis_dir(settings) / f"perf-{name}{suffix}.json", record)
    return record
