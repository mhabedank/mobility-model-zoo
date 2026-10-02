"""`jtbd span label`: a span-model candidate on the benchmark's main split (feature 004, T030).

Writes a regular run directory (role `student`, backend `span`), so `jtbd check` and `jtbd score`
measure the model with the same harness as every other JTBD model (Principle VIII). Each evaluated
candidate is recorded in the training dataset's `analysis/candidates.json`; at most
`selection.benchmark_candidate_cap` candidates are evaluated, all of them are reported, and the
holdout split stays unused (research R8).
"""

from __future__ import annotations

import hashlib
import platform
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mobility_model_zoo.productdev.jtbd.config import Settings, load_settings
from mobility_model_zoo.productdev.jtbd.corpus.store import chunk_map
from mobility_model_zoo.productdev.jtbd.errors import ValidationFailed
from mobility_model_zoo.productdev.jtbd.freeze import schema_sha256, verify_benchmark_frozen
from mobility_model_zoo.productdev.jtbd.jsonio import read_json, write_json
from mobility_model_zoo.productdev.jtbd.labeling.runner import run_id_for
from mobility_model_zoo.productdev.jtbd.schema import LabelRunManifest, RunSettings
from mobility_model_zoo.productdev.jtbd.span.extractor import WEIGHTS_FILE
from mobility_model_zoo.productdev.jtbd.span.recipe import (
    head_commit,
    load_recipe,
    require_clean_tree,
)

MODEL_ID = "productdev-jtbd-span-xlmr"


def model_sha256(model_dir: Path) -> str:
    digest = hashlib.sha256()
    with (Path(model_dir) / WEIGHTS_FILE).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def dataset_settings(settings: Settings, recipe: dict[str, Any]) -> Settings:
    path = Path(recipe["dataset_config"])
    return load_settings(path if path.is_absolute() else settings.base / path)


def candidates_path(dataset: Settings) -> Path:
    return dataset.data_dir / "analysis" / "candidates.json"


def load_candidates(dataset: Settings) -> list[dict[str, Any]]:
    path = candidates_path(dataset)
    return read_json(path)["candidates"] if path.exists() else []


def save_candidates(dataset: Settings, candidates: list[dict[str, Any]]) -> None:
    write_json(candidates_path(dataset), {"candidates": candidates})


def label_span(settings: Settings, model_dir: Path, split: str, change: str,
               recipe_file: str | None = None) -> dict[str, Any]:
    if split != "main":
        raise ValidationFailed("span label evaluates on the main split only; the holdout stays "
                               "unused (spec Assumptions)")
    if not (change and change.strip()):
        raise ValidationFailed("--candidate-change must say what this candidate changes and why")
    frozen = verify_benchmark_frozen(settings)
    recipe = load_recipe(settings, recipe_file)
    dataset = dataset_settings(settings, recipe)
    require_clean_tree(settings)
    sha = model_sha256(model_dir)
    candidates = load_candidates(dataset)
    if any(c["model_sha256"] == sha for c in candidates):
        raise ValidationFailed(f"this model ({sha[:12]}) was already evaluated on the benchmark")
    cap = int(recipe["selection"]["benchmark_candidate_cap"])
    if len(candidates) >= cap:
        raise ValidationFailed(f"the cap of {cap} benchmark-evaluated candidates is reached "
                               "(research R8)")

    from mobility_model_zoo.productdev.jtbd.span.extractor import SpanExtractor

    extractor = SpanExtractor.from_pretrained(model_dir)
    candidate_id = f"c{len(candidates) + 1}"
    run_id = run_id_for("student", f"{MODEL_ID}-{candidate_id}-{sha[:12]}", split,
                        frozen["hashes"]["guideline"])
    run_path = settings.runs_dir / run_id
    if run_path.exists():
        raise ValidationFailed(f"{run_id} already exists")
    started = datetime.now(UTC)
    chunks = chunk_map(settings, split)
    for chunk_id, chunk in sorted(chunks.items()):
        write_json(run_path / "parsed" / f"{chunk_id}.json", extractor.extract(chunk.text))
    manifest = LabelRunManifest(
        run_id=run_id, role="student", backend="span", model_id=MODEL_ID,
        model_version=sha[:12], family="xlm-roberta", host=platform.node() or "local",
        settings=RunSettings(temperature=0.0, structured_output="post_validation",
                             max_retries=0, dimensions=extractor.dimensions, model_sha256=sha,
                             thresholds=extractor.thresholds, git_commit=head_commit(settings),
                             candidate_id=candidate_id),
        guideline_sha256=frozen["hashes"]["guideline"], schema_sha256=schema_sha256(),
        criteria_sha256=frozen["hashes"]["criteria"], split=split, started_at=started,
        finished_at=datetime.now(UTC), status="complete",
        deviations=["span model: no free-text actor or English statement (not scored)"])
    data = manifest.model_dump(mode="json")
    data["settings"] = {k: v for k, v in data["settings"].items() if v is not None}
    write_json(run_path / "manifest.json", data)
    candidates.append({
        "candidate_id": candidate_id, "model_sha256": sha, "model_dir": str(model_dir),
        "change": change.strip(), "run_id": run_id,
        "scores": str(settings.analysis_dir / "scores" / f"{run_id}.json"),
        "benchmark_version": frozen["version"], "evaluated_at": started.isoformat(),
        "selected": False})
    save_candidates(dataset, candidates)
    return {"run_id": run_id, "candidate_id": candidate_id, "chunks": len(chunks),
            "dimensions": extractor.dimensions, "model_sha256": sha}
