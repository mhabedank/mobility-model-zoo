"""Technical spike helpers (spec 002): SFT export from teacher labels and the spike report.

Spike results are labeled "spike" and are never benchmark results (constitution v1.2.0).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

from mobility_model_zoo.productdev.jtbd.config import Settings
from mobility_model_zoo.productdev.jtbd.corpus.store import chunk_map
from mobility_model_zoo.productdev.jtbd.errors import ValidationFailed
from mobility_model_zoo.productdev.jtbd.freeze import load_manifest
from mobility_model_zoo.productdev.jtbd.jsonio import read_json, write_json, write_jsonl
from mobility_model_zoo.productdev.jtbd.labeling.prompt import build_system_prompt
from mobility_model_zoo.productdev.jtbd.quotes import repair
from mobility_model_zoo.productdev.jtbd.runs import load_outputs, load_run_manifest, run_dir

DIMS = ("relevance", "item_matching", "kind", "actor_type", "evidence_type", "evidence_scope")


def chatml(system: str, user: str) -> str:
    """Qwen chat template for the prompt part (the assistant answer is the `output` field)."""
    return (f"<|im_start|>system\n{system}<|im_end|>\n<|im_start|>user\n{user}<|im_end|>\n"
            "<|im_start|>assistant\n")


def export_sft(settings: Settings, run_id: str, out: Path, repair_quotes: bool = True
               ) -> dict[str, Any]:
    run = load_run_manifest(settings, run_id)
    if run.role != "teacher_candidate":
        raise ValidationFailed("training data may only come from a teacher_candidate run (FR-S03)")
    if run.split != "train":
        raise ValidationFailed("SFT export uses the train split only")
    chunks = chunk_map(settings, "train")
    system = build_system_prompt(settings)
    rows, skipped, emptied = [], [], []
    repaired = dropped_items = 0
    fields = ("kind", "quote", "actor", "actor_type", "statement", "evidence_type",
              "evidence_scope")
    for chunk_id, out_ in sorted(load_outputs(settings, run_id).items()):
        if out_.relevant is None:
            skipped.append(chunk_id)
            continue
        text = chunks[chunk_id].text
        items = []
        for item in out_.items if out_.relevant else []:
            entry = {k: getattr(item, k) for k in fields}
            if not item.valid:
                # Training data only: replace a near-miss quote with the verbatim source passage.
                span = repair(item.quote, text) if repair_quotes else None
                if span is None:
                    dropped_items += 1
                    continue
                # Verbatim passage with whitespace runs collapsed (still passes the quote check),
                # so training targets never contain PDF line breaks.
                entry["quote"] = " ".join(text[span[0]:span[1]].split())
                repaired += 1
            items.append(entry)
        if out_.relevant and out_.items and not items:
            # Every teacher item was dropped: "relevant but empty" would teach finding nothing.
            emptied.append(chunk_id)
            continue
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
    stats = {"run_id": run_id, "examples": len(rows), "repaired_quotes": repaired,
             "dropped_unverified_items": dropped_items,
             "skipped_examples_all_items_dropped": emptied,
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
