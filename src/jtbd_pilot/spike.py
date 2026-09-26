"""Technical spike helpers (spec 002): SFT export from teacher labels and the spike report.

Spike results are labeled "spike" and are never benchmark results (constitution v1.2.0).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

from jtbd_pilot.config import Settings
from jtbd_pilot.corpus.store import chunk_map
from jtbd_pilot.errors import ValidationFailed
from jtbd_pilot.freeze import load_manifest
from jtbd_pilot.jsonio import read_json, write_json, write_jsonl
from jtbd_pilot.labeling.prompt import build_system_prompt
from jtbd_pilot.runs import load_outputs, load_run_manifest, run_dir

DIMS = ("relevance", "item_matching", "kind", "actor_type", "evidence_type", "evidence_scope")


def chatml(system: str, user: str) -> str:
    """Qwen chat template for the prompt part (the assistant answer is the `output` field)."""
    return (f"<|im_start|>system\n{system}<|im_end|>\n<|im_start|>user\n{user}<|im_end|>\n"
            "<|im_start|>assistant\n")


def export_sft(settings: Settings, run_id: str, out: Path) -> dict[str, Any]:
    run = load_run_manifest(settings, run_id)
    if run.role != "teacher_candidate":
        raise ValidationFailed("training data may only come from a teacher_candidate run (FR-S03)")
    if run.split != "train":
        raise ValidationFailed("SFT export uses the train split only")
    chunks = chunk_map(settings, "train")
    system = build_system_prompt(settings)
    rows, dropped_items, skipped = [], 0, []
    for chunk_id, out_ in sorted(load_outputs(settings, run_id).items()):
        if out_.relevant is None:
            skipped.append(chunk_id)
            continue
        items = [] if not out_.relevant else [
            {k: getattr(i, k) for k in ("kind", "quote", "actor", "actor_type", "statement",
                                        "evidence_type", "evidence_scope")}
            for i in out_.valid_items]
        dropped_items += len(out_.items) - (len(items) if out_.relevant else 0)
        answer = json.dumps({"relevant": out_.relevant, "items": items}, ensure_ascii=False)
        user = chunks[chunk_id].text
        rows.append({
            "chunk_id": chunk_id,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user},
                         {"role": "assistant", "content": answer}],
            "prompt": chatml(system, user),
            "output": answer,
        })
    write_jsonl(out, rows)
    stats = {"run_id": run_id, "examples": len(rows), "dropped_unverified_items": dropped_items,
             "skipped_chunks_without_valid_output": skipped, "path": str(out),
             "exported_at": datetime.now(UTC).isoformat()}
    write_json(out.with_suffix(".stats.json"), stats)
    return stats


def _throughput(settings: Settings, run_id: str) -> dict[str, Any]:
    latencies = []
    for path in (run_dir(settings, run_id) / "raw").glob("*.a*.json"):
        data = read_json(path)
        if data.get("latency_ms"):
            latencies.append(data["latency_ms"])
    if not latencies:
        return {"calls": 0}
    avg = mean(latencies)
    return {"calls": len(latencies), "mean_latency_s": round(avg / 1000, 1),
            "chunks_per_min_sequential": round(60000 / avg, 2)}


def _fmt(x: Any) -> str:
    return "n/a" if x is None else (f"{x:.3f}" if isinstance(x, float) else str(x))


def spike_report(settings: Settings, sft_stats: Path | None = None) -> dict[str, Any]:
    manifest = load_manifest(settings)
    if not manifest or not settings.pilot.get("spike"):
        raise ValidationFailed("spike report needs a spike config with a frozen manifest")
    scores = [read_json(p) for p in sorted((settings.analysis_dir / "scores").glob("*.json"))]
    runs = [read_json(p) for p in sorted(settings.runs_dir.glob("run-*/manifest.json"))]
    lines = [f"# Spike report: {manifest['version']}", "",
             "> **Technical spike** (constitution v1.2.0). These are spike results, not benchmark "
             "results. The reference is a single model (Claude via subscription); there is no "
             "consensus between reference models and no contested set.", "",
             "## Scores on the evaluation chunks (agreement with the Claude reference)", ""]
    header = ["Model", "Role", *DIMS, "Composite", "schema_valid", "quote_verbatim"]
    lines += ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    for s in scores:
        rates = s.get("check_pass_rates") or {}
        lines.append("| " + " | ".join([
            s["model_id"], s["role"], *[_fmt(s["dimensions"][d]["score"]) for d in DIMS],
            _fmt(s["composite"]), _fmt((rates.get("schema_valid") or {}).get("rate")),
            _fmt((rates.get("quote_verbatim") or {}).get("rate"))]) + " |")
    n_eval = scores[0]["dimensions"]["relevance"]["n"] if scores else 0
    lines += ["", f"Evaluation chunks with a reference label: {n_eval}. All scores are "
              "underpowered by design (spike size).", "",
              "## Runs and throughput (DGX Spark = development hardware, not target hardware)", ""]
    lines += ["| Run | Model | Split | Status | Excluded | Calls | Mean latency s | Chunks/min |",
              "|---|---|---|---|---|---|---|---|"]
    for r in runs:
        t = _throughput(settings, r["run_id"])
        lines.append(f"| `{r['run_id']}` | {r['model_id']} | {r['split']} | {r['status']} | "
                     f"{len(r['excluded_chunks'])} | {t.get('calls', 0)} | "
                     f"{_fmt(t.get('mean_latency_s'))} | {_fmt(t.get('chunks_per_min_sequential'))} |")
    if sft_stats and sft_stats.exists():
        st = read_json(sft_stats)
        lines += ["", "## Training data", "",
                  f"- {st['examples']} SFT examples from `{st['run_id']}`",
                  f"- {st['dropped_unverified_items']} teacher items dropped (quote not verbatim)",
                  f"- {len(st['skipped_chunks_without_valid_output'])} chunks skipped (no valid "
                  "teacher output)"]
    deviations = sorted({d for r in runs for d in r.get("deviations", [])})
    lines += ["", "## Deviations", ""] + [f"- {d}" for d in deviations or ["none recorded"]]
    findings = settings.data_dir / "findings.md"
    lines += ["", "## Findings", "",
              findings.read_text(encoding="utf-8").strip() if findings.exists()
              else "No findings file yet."]
    out = settings.reports_dir / manifest["version"] / "spike-report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"report": str(out), "models": [s["model_id"] for s in scores]}
