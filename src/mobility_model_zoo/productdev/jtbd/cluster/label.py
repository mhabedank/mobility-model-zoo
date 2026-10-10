"""Reference labeling of benchmark pairs and sets (research R11, task T029).

Units are pair batches (`batch_size` pairs, by pair id) and sets. Each unit goes through the
existing safeguards: frozen hashes (exit 3), budget guard (exit 4), pre-send check of every batch
(C-P1 … C-P5), post-receive check of hosted answers (C-P6), write-once raw responses, resumable
runs, and a stop on a model-version change (exit 6). An answer that misses, repeats or invents an id
is invalid and retried up to `max_retries`, then the unit is excluded and counted.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mobility_model_zoo.productdev.jtbd import budget
from mobility_model_zoo.productdev.jtbd.cluster import bench
from mobility_model_zoo.productdev.jtbd.cluster.prompt import (
    PAIR_SCHEMA,
    SET_SCHEMA,
    pair_answer_errors,
    pair_message,
    prompt_sha256,
    set_answer_errors,
    set_message,
    system_prompt,
)
from mobility_model_zoo.productdev.jtbd.config import Settings
from mobility_model_zoo.productdev.jtbd.errors import BackendFailure, UsageError, ValidationFailed
from mobility_model_zoo.productdev.jtbd.jsonio import read_json, write_json, write_jsonl
from mobility_model_zoo.productdev.jtbd.labeling.base import make_backend
from mobility_model_zoo.productdev.jtbd.labeling.runner import check_roles

LABEL_SPLITS = ("dev", "test", "holdout")
ASSUMED_OUTPUT_TOKENS = {"pairs": 600, "sets": 1500}


def run_id_for(model_id: str, split: str, guideline_sha: str) -> str:
    slug = re.sub(r"[^a-z0-9.]+", "-", model_id.lower()).strip("-")
    return f"cluster-reference-{slug}-{split}-{guideline_sha[:8]}"


def runs_dir(settings: Settings) -> Path:
    return settings.runs_dir


def units_for(settings: Settings, split: str) -> list[dict[str, Any]]:
    """Pair batches first, then sets; ids are stable for a frozen benchmark."""
    size = int(bench.cfg(settings).get("batch_size", 20))
    pairs = sorted(bench.load_pairs(settings, split), key=lambda p: p["pair_id"])
    units = [{"unit": f"pairs-{split}-{n // size + 1:03d}", "type": "pairs",
              "pairs": pairs[n:n + size]} for n in range(0, len(pairs), size)]
    units += [{"unit": s["set_id"], "type": "sets", "items": s["items"]}
              for s in bench.load_sets(settings, split)]
    return units


def unit_items(unit: dict[str, Any]) -> list[str]:
    if unit["type"] == "pairs":
        return sorted({i for p in unit["pairs"] for i in (p["a"], p["b"])})
    return list(unit["items"])


def _presend(settings: Settings, entry, units: list[dict[str, Any]], pool: dict[str, dict]
             ) -> dict | None:
    """Fail-closed pre-send checks of every quote that will be sent (feature 006)."""
    from mobility_model_zoo.compliance.findings import StageFailed
    from mobility_model_zoo.compliance.presend import check_batch
    from mobility_model_zoo.compliance.register import Register
    from mobility_model_zoo.productdev.jtbd.corpus.redact import PATTERNS_VERSION

    reg = Register.load(settings.base)
    route_id = entry.extra.get("route")
    items = sorted({i for u in units for i in unit_items(u)})
    findings = check_batch(
        reg, model_id=entry.model_id, backend=entry.backend, role="reference", route_id=route_id,
        provider_order=entry.extra.get("provider_order"),
        items=[(i, pool[i]["quote"], pool[i].get("patterns_version")) for i in items],
        current_patterns=PATTERNS_VERSION)
    if findings:
        raise ValidationFailed("compliance pre-send check failed: "
                               + "; ".join(StageFailed(findings).failures[:10]))
    return reg.route(route_id) if route_id else None


def _estimate(settings: Settings, entry, units: list[dict[str, Any]], system: str,
              pool: dict[str, dict]) -> float:
    if not units:
        return 0.0
    prompt_tokens = len(system) // 4
    avg_in = sum(len(_message(u, pool)) // 4 for u in units) / len(units) + prompt_tokens
    avg_out = sum(ASSUMED_OUTPUT_TOKENS[u["type"]] for u in units) / len(units)
    return budget.estimate_run(settings, entry, len(units), avg_in, prompt_tokens, avg_out)


def _message(unit: dict[str, Any], pool: dict[str, dict]) -> str:
    if unit["type"] == "pairs":
        return pair_message(unit["pairs"], pool)
    return set_message(unit["items"], pool)


def _errors(unit: dict[str, Any], answer: Any) -> list[str]:
    if unit["type"] == "pairs":
        return pair_answer_errors(answer, [p["pair_id"] for p in unit["pairs"]])
    return set_answer_errors(answer, unit["items"])


def _label_unit(model, system: str, unit: dict[str, Any], pool: dict[str, dict], raw_dir: Path,
                parsed_dir: Path, retries: int) -> tuple[str, float, list[str]]:
    """All attempts of one unit: ("" or the last error, cost, model versions seen)."""
    from mobility_model_zoo.compliance.presend import check_answer

    schema = PAIR_SCHEMA if unit["type"] == "pairs" else SET_SCHEMA
    message = _message(unit, pool)
    last_error, spent, versions = "no attempt", 0.0, []
    for _ in range(retries + 1):
        attempt = len(list(raw_dir.glob(f"{unit['unit']}.a*.json"))) + 1
        record: dict[str, Any] = {"unit": unit["unit"], "attempt": attempt,
                                  "request_ts": datetime.now(UTC).isoformat()}
        raw_path = raw_dir / f"{unit['unit']}.a{attempt}.json"
        try:
            result = model.call(system, message, schema, unit["unit"])
        except BackendFailure as exc:
            last_error = str(exc)
            write_json(raw_path, {**record, "error": last_error}, exclusive=True)
            continue
        spent += result.cost_eur
        finding = check_answer(getattr(model, "compliance_route", None),
                               getattr(model, "compliance_backend", ""), result.meta)
        if finding:
            write_json(raw_path, {**record, "error": "provider_mismatch: " + finding.reason,
                                  "backend_meta": result.meta}, exclusive=True)
            raise ValidationFailed(f"compliance post-receive check failed (C-P6): {finding.reason}")
        versions.append(result.model_version)
        write_json(raw_path, {**record, "model_version": result.model_version,
                              "usage": result.usage, "backend_meta": result.meta,
                              "cost_eur": result.cost_eur, "raw_body": result.raw_body,
                              "parsed_candidate": result.parsed_candidate}, exclusive=True)
        errors = _errors(unit, result.parsed_candidate)
        if errors:
            last_error = "invalid answer: " + "; ".join(errors)[:300]
            continue
        write_json(parsed_dir / f"{unit['unit']}.json",
                   {"unit": unit["unit"], "type": unit["type"], "answer": result.parsed_candidate},
                   exclusive=True)
        return "", spent, versions
    return last_error, spent, versions


def label(settings: Settings, model_id: str, split: str, limit: int | None = None) -> dict[str, Any]:
    """`jtbd cluster label --model … --split …`."""
    cluster = bench.cfg(settings)
    if split not in LABEL_SPLITS:
        raise UsageError(f"--split must be one of {', '.join(LABEL_SPLITS)}")
    if model_id not in cluster.get("reference_models", []):
        raise UsageError(f"{model_id} is not a reference model of {settings.benchmark_version}")
    entry = settings.model(model_id)
    check_roles(settings, "reference", entry)
    manifest_b = bench.verify(settings)
    if split == "holdout" and int(manifest_b.get("reruns", 0)) < 1:
        raise ValidationFailed("holdout units are locked until a decision says `revise`")
    pool = bench.load_pool(settings)
    units = units_for(settings, split)
    if not units:
        raise ValidationFailed(f"no {split} units in the benchmark")
    route = _presend(settings, entry, units, pool)
    system = system_prompt(settings)
    run_id = run_id_for(model_id, split, manifest_b["hashes"]["guideline"])
    run_path = runs_dir(settings) / run_id
    raw_dir, parsed_dir = run_path / "raw", run_path / "parsed"
    manifest_file = run_path / "manifest.json"
    manifest = read_json(manifest_file) if manifest_file.exists() else None
    if manifest and manifest["status"] == "invalid_version_change":
        raise ValidationFailed(f"{run_id} is invalid (model version changed mid-run); move "
                               f"{run_path} aside and repeat the run")
    excluded = {e["unit"] for e in manifest["excluded_units"]} if manifest else set()
    todo = [u for u in units
            if u["unit"] not in excluded and not (parsed_dir / f"{u['unit']}.json").exists()]
    if limit is not None:
        todo = todo[:limit]
    estimate = _estimate(settings, entry, todo, system, pool)
    budget.guard(settings, estimate, entry.backend)
    model = make_backend(settings, entry, entry.backend, None)
    model.compliance_route, model.compliance_backend = route, entry.backend
    retries = int(cluster.get("max_retries", 2))
    if manifest is None:
        manifest = {
            "run_id": run_id, "role": "reference", "backend": entry.backend, "model_id": model_id,
            "model_version": "pending", "family": entry.family, "split": split,
            "benchmark_version": settings.benchmark_version,
            "settings": {"temperature": model.temperature,
                         "structured_output": model.structured_output, "max_retries": retries,
                         "batch_size": int(cluster.get("batch_size", 20))},
            "hashes": manifest_b["hashes"], "prompt_sha256": prompt_sha256(settings),
            "started_at": datetime.now(UTC).isoformat(), "finished_at": None, "cost_eur": 0.0,
            "excluded_units": [], "status": "running", "deviations": list(model.deviations),
            "license_basis": entry.license_basis,
        }
        write_json(manifest_file, manifest)
    spent, done = 0.0, 0
    try:
        for unit in todo:
            error, cost, versions = _label_unit(model, system, unit, pool, raw_dir, parsed_dir,
                                                retries)
            spent += cost
            for version in versions:
                if manifest["model_version"] == "pending":
                    manifest["model_version"] = version
                elif manifest["model_version"] != version:
                    manifest["status"] = "invalid_version_change"
                    raise BackendFailure(f"model version changed from {manifest['model_version']} "
                                         f"to {version} during {run_id}; the run must be repeated")
            if error:
                manifest["excluded_units"].append({"unit": unit["unit"], "reason": error})
            done += 1
            write_json(manifest_file, manifest)
    finally:
        manifest["cost_eur"] = round(manifest["cost_eur"] + spent, 6)
        excluded_now = {e["unit"] for e in manifest["excluded_units"]}
        remaining = [u for u in units if u["unit"] not in excluded_now
                     and not (parsed_dir / f"{u['unit']}.json").exists()]
        if not remaining and manifest["status"] == "running":
            manifest["status"] = "complete"
            manifest["finished_at"] = datetime.now(UTC).isoformat()
            _assemble(run_path)
        write_json(manifest_file, manifest)
        if estimate or spent:
            budget.record(settings, run_id, entry.backend, estimate, spent)
    return {"run_id": run_id, "status": manifest["status"], "processed_now": done,
            "units": len(units), "excluded": len(manifest["excluded_units"]),
            "model_version": manifest["model_version"], "cost_eur": manifest["cost_eur"]}


def _assemble(run_path: Path) -> None:
    """parsed/<unit>.json -> pairs.jsonl (`pair_id`, `label`) and sets.jsonl (`set_id`, `clusters`,
    `coarse`)."""
    pairs, sets = [], []
    for path in sorted((run_path / "parsed").glob("*.json")):
        data = read_json(path)
        if data["type"] == "pairs":
            pairs += [{"pair_id": p["pair_id"], "label": p["label"]} for p in data["answer"]["pairs"]]
        else:
            sets.append({"set_id": data["unit"], "clusters": data["answer"]["clusters"],
                         "coarse": data["answer"].get("coarse")})
    write_jsonl(run_path / "pairs.jsonl", sorted(pairs, key=lambda p: p["pair_id"]))
    write_jsonl(run_path / "sets.jsonl", sets)


def reference_runs(settings: Settings, split: str) -> dict[str, Path]:
    """Complete reference runs of a split by model id (both references must have one)."""
    manifest_b = bench.verify(settings)
    out = {}
    for model_id in bench.cfg(settings)["reference_models"]:
        path = runs_dir(settings) / run_id_for(model_id, split, manifest_b["hashes"]["guideline"])
        manifest_file = path / "manifest.json"
        if not manifest_file.exists() or read_json(manifest_file)["status"] != "complete":
            raise ValidationFailed(f"no complete {split} run of {model_id} ({path.name})")
        out[model_id] = path
    return out
