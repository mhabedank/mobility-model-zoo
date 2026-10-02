"""Throughput, latency and peak memory (FR-029, research.md R6).

Local runs happen on the low-resource reference VM with the same model digest as the quality run
on the Spark. The frontier reference throughput is a short GPT sample at concurrency 1.
"""

from __future__ import annotations

import math
import os
import platform
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mobility_model_zoo.productdev.jtbd import budget
from mobility_model_zoo.productdev.jtbd.config import Settings
from mobility_model_zoo.productdev.jtbd.corpus.store import load_chunks
from mobility_model_zoo.productdev.jtbd.errors import ValidationFailed
from mobility_model_zoo.productdev.jtbd.jsonio import read_json, write_json
from mobility_model_zoo.productdev.jtbd.labeling.base import make_backend
from mobility_model_zoo.productdev.jtbd.labeling.ollama import OllamaBackend, model_digest, resolve_host
from mobility_model_zoo.productdev.jtbd.labeling.prompt import build_system_prompt
from mobility_model_zoo.productdev.jtbd.labeling.runner import estimate_for
from mobility_model_zoo.productdev.jtbd.runs import load_run_manifest
from mobility_model_zoo.productdev.jtbd.schema import wire_schema


def percentile(values: list[float], q: float) -> float | None:
    """Linear-interpolated percentile, q in [0, 100]."""
    if not values:
        return None
    ordered = sorted(values)
    k = (len(ordered) - 1) * q / 100
    low, high = math.floor(k), math.ceil(k)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (k - low)


def ollama_rss_mb(proc_root: Path = Path("/proc")) -> float | None:
    """Sum of VmRSS over Ollama processes, in MB. None when /proc is unavailable."""
    if not proc_root.exists():
        return None
    total_kb = 0
    for pid_dir in proc_root.iterdir():
        if not pid_dir.name.isdigit():
            continue
        try:
            cmdline = (pid_dir / "cmdline").read_bytes().replace(b"\0", b" ").decode(
                errors="replace")
            if "ollama" not in cmdline:
                continue
            for line in (pid_dir / "status").read_text().splitlines():
                if line.startswith("VmRSS:"):
                    total_kb += int(line.split()[1])
        except (OSError, ValueError):
            continue
    return total_kb / 1024


class PeakSampler:
    def __init__(self, interval_s: float = 0.1, proc_root: Path = Path("/proc")):
        self.interval_s = interval_s
        self.proc_root = proc_root
        self.peak: float | None = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def _loop(self) -> None:
        while not self._stop.is_set():
            value = ollama_rss_mb(self.proc_root)
            if value is not None:
                self.peak = value if self.peak is None else max(self.peak, value)
            self._stop.wait(self.interval_s)

    def __enter__(self) -> PeakSampler:
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._stop.set()
        self._thread.join()


def hardware_info(label: str | None) -> dict[str, Any]:
    info: dict[str, Any] = {"label": label, "machine": platform.machine(),
                            "vcpus": os.cpu_count()}
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                info["cpu_model"] = line.split(":", 1)[1].strip()
                break
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                info["mem_total_mb"] = round(int(line.split()[1]) / 1024)
                break
    except OSError:
        info["note"] = "/proc not available; run perf on the Linux reference VM"
    return info


def _quality_run(settings: Settings, model_id: str, quality_run: str | None):
    if quality_run:
        return load_run_manifest(settings, quality_run)
    candidates = []
    for path in sorted(settings.runs_dir.glob("run-*/manifest.json")):
        data = read_json(path)
        if data["model_id"] == model_id and data["split"] == "main" and data["backend"] == "ollama":
            candidates.append(data["run_id"])
    if len(candidates) != 1:
        raise ValidationFailed(
            f"found {len(candidates)} quality runs for {model_id}; pass --quality-run <run_id>")
    return load_run_manifest(settings, candidates[0])


def perf_local(settings: Settings, model_id: str, host: str, warmup: int,
               quality_run: str | None, hardware: str | None) -> dict[str, Any]:
    entry = settings.model(model_id)
    quality = _quality_run(settings, model_id, quality_run)
    digest = model_digest(resolve_host(host), entry.api_model)
    if digest != quality.model_version:
        raise ValidationFailed(
            f"digest on {host} ({digest[:12]}) differs from quality run {quality.run_id} "
            f"({quality.model_version[:12]}); pull the identical model file")
    backend = OllamaBackend(settings, entry, host)
    system, schema = build_system_prompt(settings), wire_schema()
    chunks = load_chunks(settings, "main")
    for chunk in chunks[:warmup]:
        backend.call(system, chunk.text, schema, chunk.chunk_id)
    latencies, out_tokens = [], 0
    start = time.monotonic()
    with PeakSampler() as sampler:
        for chunk in chunks:
            result = backend.call(system, chunk.text, schema, chunk.chunk_id)
            latencies.append(result.latency_ms)
            out_tokens += int(result.usage.get("completion_tokens") or 0)
    wall_s = time.monotonic() - start
    result = {
        "model_id": model_id,
        "model_digest": digest,
        "quality_run": quality.run_id,
        "host": host,
        "hardware": hardware_info(hardware),
        "warmup_chunks": warmup,
        "n_chunks": len(chunks),
        "wall_seconds": round(wall_s, 2),
        "chunks_per_min": round(len(chunks) / wall_s * 60, 4) if wall_s else None,
        "output_tok_per_s": round(out_tokens / wall_s, 3) if wall_s else None,
        "latency_p50_ms": percentile(latencies, 50),
        "latency_p95_ms": percentile(latencies, 95),
        "peak_rss_mb": round(sampler.peak, 1) if sampler.peak is not None else None,
        "measured_at": datetime.now(UTC).isoformat(),
    }
    write_json(settings.analysis_dir / "perf" / f"{model_id}.json", result)
    return result


def perf_frontier(settings: Settings, run_id: str, sample: int) -> dict[str, Any]:
    run = load_run_manifest(settings, run_id)
    entry = settings.model(run.model_id)
    chunks = load_chunks(settings, "main")[:sample]
    estimate = estimate_for(settings, entry, len(chunks))
    budget.guard(settings, estimate, entry.backend)
    backend = make_backend(settings, entry, entry.backend, None)
    system, schema = build_system_prompt(settings), wire_schema()
    latencies, spent = [], 0.0
    start = time.monotonic()
    try:
        for chunk in chunks:
            result = backend.call(system, chunk.text, schema, chunk.chunk_id)
            latencies.append(result.latency_ms)
            spent += result.cost_eur
    finally:
        budget.record(settings, f"perf-frontier-{run_id}", entry.backend, estimate, spent)
    wall_s = time.monotonic() - start
    result = {
        "model_id": run.model_id,
        "reference_run": run_id,
        "concurrency": 1,
        "n_chunks": len(chunks),
        "chunks_per_min": round(len(chunks) / wall_s * 60, 4) if wall_s else None,
        "latency_p50_ms": percentile(latencies, 50),
        "latency_p95_ms": percentile(latencies, 95),
        "cost_eur": round(spent, 6),
        "note": "hosted throughput depends on routing and provider rate limits",
        "measured_at": datetime.now(UTC).isoformat(),
    }
    write_json(settings.analysis_dir / "perf" / "frontier.json", result)
    return result


DEFAULT_PERF_TEXT = Path("configs/productdev/jtbd/perf/interview-9k-de.txt")
LATENCY_REPEATS = 5


def process_rss_mb(pid: int, proc_root: Path = Path("/proc")) -> float | None:
    """VmRSS of one process in MB; None when /proc is unavailable."""
    try:
        for line in (proc_root / str(pid) / "status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) / 1024
    except (OSError, ValueError):
        return None
    return None


def _student_run(settings: Settings, sha: str, quality_run: str | None):
    if quality_run:
        run = load_run_manifest(settings, quality_run)
    else:
        found = [read_json(p)["run_id"] for p in sorted(settings.runs_dir.glob("run-*/manifest.json"))
                 if read_json(p).get("backend") == "span"
                 and read_json(p).get("settings", {}).get("model_sha256") == sha]
        if len(found) != 1:
            raise ValidationFailed(f"found {len(found)} span quality runs for model {sha[:12]}; "
                                   "evaluate it with `jtbd span label` first or pass --quality-run")
        run = load_run_manifest(settings, found[0])
    expected = getattr(run.settings, "model_sha256", None)
    if expected != sha:
        raise ValidationFailed(f"model.safetensors ({sha[:12]}) differs from the files of the "
                               f"quality run {run.run_id} ({str(expected)[:12]})")
    return run


def perf_span(settings: Settings, model_dir: Path, hardware: str | None,
              text_file: Path | None = None, quality_run: str | None = None,
              repeats: int = LATENCY_REPEATS) -> dict[str, Any]:
    """Speed and peak memory of a span model in a child process (research R13, FR-014)."""
    import json
    import subprocess
    import sys
    import tempfile

    from mobility_model_zoo.productdev.jtbd.span.evaluate import model_sha256

    sha = model_sha256(model_dir)
    run = _student_run(settings, sha, quality_run)
    text_path = Path(text_file) if text_file else settings.base / DEFAULT_PERF_TEXT
    if not text_path.exists():
        raise ValidationFailed(f"perf text not found: {text_path}")
    text = text_path.read_text(encoding="utf-8")
    chunks = [c.text for c in load_chunks(settings, "main")]
    threads = os.cpu_count() or 1
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump({"model_dir": str(model_dir), "text": text, "chunks": chunks,
                   "threads": threads, "repeats": repeats}, f)
        job = f.name
    child = subprocess.Popen([sys.executable, "-m",
                              "mobility_model_zoo.productdev.jtbd.span.perfworker", job],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    sampled: float | None = None
    while child.poll() is None:
        value = process_rss_mb(child.pid)
        if value is not None:
            sampled = value if sampled is None else max(sampled, value)
        time.sleep(0.05)
    out, err = child.communicate()
    Path(job).unlink(missing_ok=True)
    if child.returncode != 0:
        raise ValidationFailed(f"perf worker failed: {err.strip()[-500:]}")
    measured = json.loads(out.strip().splitlines()[-1])
    peak = max(v for v in (sampled, measured["ru_maxrss_mb"]) if v is not None)
    result = {
        "model_id": run.model_id,
        "backend": "span",
        "model_sha256": sha,
        "quality_run": run.run_id,
        "hardware": hardware_info(hardware),
        "text_file": str(text_path),
        **measured,
        "peak_rss_mb": round(peak, 1),
        "peak_rss_sampled_mb": None if sampled is None else round(sampled, 1),
        "measured_at": datetime.now(UTC).isoformat(),
    }
    write_json(settings.analysis_dir / "perf" / f"{run.model_id}-{sha[:12]}.json", result)
    return result
