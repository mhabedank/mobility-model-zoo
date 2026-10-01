"""`jtbd label`: runs one model over one split.

Preconditions: frozen hashes (exit 3), budget guard (exit 4), role and family rules, holdout lock,
passed redaction. Raw responses are written once and never overwritten; runs are resumable; a
model-version change mid-run stops the run (exit 6).
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from statistics import mean
from typing import Any

from mobility_model_zoo.productdev.jtbd import budget
from mobility_model_zoo.productdev.jtbd.config import ModelEntry, Settings
from mobility_model_zoo.productdev.jtbd.corpus.store import load_chunks
from mobility_model_zoo.productdev.jtbd.errors import BackendFailure, ValidationFailed
from mobility_model_zoo.productdev.jtbd.freeze import schema_sha256, set_pilot_state, verify_frozen
from mobility_model_zoo.productdev.jtbd.jsonio import read_json, write_json
from mobility_model_zoo.productdev.jtbd.labeling.base import make_backend
from mobility_model_zoo.productdev.jtbd.labeling.prompt import (
    approx_prompt_tokens,
    build_system_prompt,
    prompt_sha256,
)
from mobility_model_zoo.productdev.jtbd.schema import (
    ExcludedChunk,
    ExtractionOutput,
    LabelRunManifest,
    RunSettings,
    wire_schema,
)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9.]+", "-", text.lower()).strip("-")


def run_id_for(role: str, model_id: str, split: str, guideline_sha: str) -> str:
    return f"run-{role}-{_slug(model_id)}-{split}-{guideline_sha[:8]}"


def check_roles(settings: Settings, role: str, entry: ModelEntry) -> None:
    if entry.role != role:
        raise ValidationFailed(f"{entry.model_id} is configured with role {entry.role}, not {role}")
    models = settings.models()
    if role == "reference" and not entry.benchmark_labeler:
        raise ValidationFailed(f"reference model {entry.model_id} must be benchmark_labeler: true")
    if role == "teacher_candidate":
        if entry.benchmark_labeler:
            raise ValidationFailed(
                f"{entry.model_id} is a benchmark labeler and can never be a teacher (FR-019)")
        reference_families = {m.family for m in models.values() if m.role == "reference"}
        if entry.family in reference_families:
            raise ValidationFailed(
                f"teacher family {entry.family} equals a reference family (FR-019a)")
        if not entry.license_basis:
            raise ValidationFailed(f"record license_basis for teacher {entry.model_id} (T071)")


def estimate_for(settings: Settings, entry: ModelEntry, n_chunks: int | None = None,
                 split: str = "main") -> float:
    chunks = load_chunks(settings, split)
    n = n_chunks if n_chunks is not None else len(chunks)
    if n == 0:
        return 0.0
    prompt_tokens = approx_prompt_tokens(build_system_prompt(settings))
    avg_chunk = mean(c.token_count or len(c.text) // 4 for c in chunks) if chunks else 0
    avg_out = float(settings.pilot.get("assumed_output_tokens", 1500))
    return budget.estimate_run(settings, entry, n, prompt_tokens + avg_chunk, prompt_tokens,
                               avg_out)


def _next_attempt(raw_dir, chunk_id: str) -> int:
    return len(list(raw_dir.glob(f"{chunk_id}.a*.json"))) + 1



def _label_chunk(model, system: str, schema: dict, chunk, raw_dir, parsed_dir,
                 retries: int) -> tuple[str, float, list[str]]:
    """All attempts for one chunk. Returns the last error ("" on success), cost, model versions."""
    last_error, spent, versions = "no attempt", 0.0, []
    for _ in range(retries + 1):
        attempt = _next_attempt(raw_dir, chunk.chunk_id)
        record: dict[str, Any] = {"chunk_id": chunk.chunk_id, "attempt": attempt,
                                  "request_ts": datetime.now(UTC).isoformat()}
        try:
            result = model.call(system, chunk.text, schema, chunk.chunk_id)
        except BackendFailure as exc:
            last_error = str(exc)
            write_json(raw_dir / f"{chunk.chunk_id}.a{attempt}.json",
                       {**record, "error": last_error, "parsed_candidate": None}, exclusive=True)
            continue
        spent += result.cost_eur
        versions.append(result.model_version)
        write_json(raw_dir / f"{chunk.chunk_id}.a{attempt}.json", {
            **record, "latency_ms": round(result.latency_ms, 1),
            "model_version": result.model_version, "usage": result.usage,
            "backend_meta": result.meta, "cost_eur": result.cost_eur,
            "raw_body": result.raw_body, "parsed_candidate": result.parsed_candidate,
        }, exclusive=True)
        try:
            output = ExtractionOutput.model_validate(result.parsed_candidate)
        except Exception as exc:  # noqa: BLE001 - schema failure of the model answer
            last_error = f"schema invalid: {str(exc)[:200]}"
            continue
        write_json(parsed_dir / f"{chunk.chunk_id}.json", output.model_dump(mode="json"))
        return "", spent, versions
    return last_error, spent, versions

def label(
    settings: Settings,
    role: str,
    backend: str,
    model_id: str,
    host: str | None = None,
    split: str = "main",
    limit: int | None = None,
    retry_failed: bool = False,
    workers: int = 1,
) -> dict[str, Any]:
    entry = settings.model(model_id)
    check_roles(settings, role, entry)
    frozen = verify_frozen(settings)
    if split == "holdout" and frozen.get("pilot_state") not in ("revise", "rerun_holdout"):
        raise ValidationFailed("holdout chunks are locked until the pilot state is `revise`")
    chunks = load_chunks(settings, split)
    unreviewed = [c.chunk_id for c in chunks if not c.redaction.check_passed]
    if unreviewed:
        raise ValidationFailed(f"chunks without passed redact-check: {unreviewed[:10]}")

    system = build_system_prompt(settings)
    schema = wire_schema()
    run_id = run_id_for(role, model_id, split, frozen["hashes"]["guideline"])
    run_path = settings.runs_dir / run_id
    raw_dir, parsed_dir = run_path / "raw", run_path / "parsed"
    manifest_file = run_path / "manifest.json"
    manifest = (LabelRunManifest.model_validate(read_json(manifest_file))
                if manifest_file.exists() else None)
    if manifest and manifest.status == "invalid_version_change":
        raise ValidationFailed(
            f"{run_id} is invalid (model version changed mid-run); move {run_path} aside and "
            "repeat the run")
    if manifest and retry_failed:
        # Backend failures (timeouts, connection errors) are retried; schema failures of the model
        # answer stay excluded so they keep counting against the model. Raw attempts are kept.
        kept = [e for e in manifest.excluded_chunks if e.reason.startswith("schema invalid")]
        manifest.deviations = sorted(set(manifest.deviations) | {
            f"retried {len(manifest.excluded_chunks) - len(kept)} chunks after backend failures"})
        manifest.excluded_chunks = kept
        manifest.status = "running"
    excluded = {e.chunk_id for e in manifest.excluded_chunks} if manifest else set()
    todo = [c for c in chunks
            if c.chunk_id not in excluded and not (parsed_dir / f"{c.chunk_id}.json").exists()]
    if limit is not None:
        todo = todo[:limit]
    estimate = estimate_for(settings, entry, len(todo), split)
    if settings.pilot.get("dry_run"):
        return {"run_id": run_id, "todo": len(todo), "estimated_eur": estimate, "dry_run": True}
    budget.guard(settings, estimate, entry.backend)

    model = make_backend(settings, entry, backend, host)
    if manifest is None:
        manifest = LabelRunManifest(
            run_id=run_id,
            role=role,
            backend=backend,
            model_id=model_id,
            model_version="pending",
            family=entry.family,
            host=host or entry.host,
            quantization=getattr(model, "quantization", None) or entry.quantization,
            settings=RunSettings(
                temperature=model.temperature,
                structured_output=model.structured_output,
                max_output_tokens=int(settings.pilot.get("max_output_tokens", 4096)),
                max_retries=int(settings.pilot.get("max_retries", 2)),
            ),
            guideline_sha256=frozen["hashes"]["guideline"],
            schema_sha256=schema_sha256(),
            criteria_sha256=frozen["hashes"]["criteria"],
            prompt_sha256=prompt_sha256(system),
            split=split,
            started_at=datetime.now(UTC),
            license_basis=entry.license_basis,
            deviations=list(model.deviations),
        )
        write_json(manifest_file, manifest.model_dump(mode="json"))
    if split == "holdout" and frozen.get("pilot_state") == "revise":
        set_pilot_state(settings, "rerun_holdout", f"holdout labeling started by {run_id}")

    retries = manifest.settings.max_retries
    spent = 0.0
    done = 0
    try:
        # Model calls may run in parallel (slow reasoning models); manifest, budget and the
        # version check stay in this thread.
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            futures = {pool.submit(_label_chunk, model, system, schema, chunk, raw_dir,
                                   parsed_dir, retries): chunk for chunk in todo}
            for future in as_completed(futures):
                chunk = futures[future]
                last_error, cost, versions = future.result()
                spent += cost
                for version in versions:
                    if manifest.model_version == "pending":
                        manifest.model_version = version
                    elif manifest.model_version != version:
                        manifest.status = "invalid_version_change"
                        for other in futures:
                            other.cancel()
                        raise BackendFailure(
                            f"model version changed from {manifest.model_version} to "
                            f"{version} during {run_id}; the run must be repeated")
                if last_error:
                    manifest.excluded_chunks.append(
                        ExcludedChunk(chunk_id=chunk.chunk_id, reason=last_error))
                done += 1
                manifest.deviations = sorted(set(manifest.deviations) | set(model.deviations))
                write_json(manifest_file, manifest.model_dump(mode="json"))
    finally:
        manifest.cost_eur = round(manifest.cost_eur + spent, 6)
        excluded_now = {e.chunk_id for e in manifest.excluded_chunks}
        remaining = [c for c in chunks if c.chunk_id not in excluded_now
                     and not (parsed_dir / f"{c.chunk_id}.json").exists()]
        if not remaining and manifest.status == "running":
            manifest.status = "complete"
            manifest.finished_at = datetime.now(UTC)
        write_json(manifest_file, manifest.model_dump(mode="json"))
        if estimate or spent:
            budget.record(settings, run_id, entry.backend, estimate, spent)
    total = len(chunks)
    return {
        "run_id": run_id,
        "status": manifest.status,
        "processed_now": done,
        "excluded": len(manifest.excluded_chunks),
        "excluded_share": round(len(manifest.excluded_chunks) / total, 4) if total else 0.0,
        "model_version": manifest.model_version,
        "cost_eur": manifest.cost_eur,
        "deviations": manifest.deviations,
    }
