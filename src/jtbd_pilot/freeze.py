"""Hash-freezing of guideline, schema, criteria, teacher scoring, budget, chunks (FR-015, FR-034).

The manifest lives at benchmarks/<version>/manifest.json. benchmarks/current names the active
version. It stores hashes only, never text.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from jtbd_pilot.config import Settings
from jtbd_pilot.corpus.store import load_chunks
from jtbd_pilot.errors import FrozenHashMismatch, UsageError, ValidationFailed
from jtbd_pilot.jsonio import read_json, write_json
from jtbd_pilot.schema import wire_schema

PILOT_STATES = (
    "collecting",
    "criteria_frozen",
    "labeled",
    "evaluated",
    "revise",
    "rerun_holdout",
    "decided",
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8"))


def sha256_canonical(path: Path) -> str:
    """Stable hash: LF line endings, sorted keys for YAML/JSON, sorted entries for directories."""
    if path.is_dir():
        parts = [
            f"{p.relative_to(path).as_posix()}:{sha256_canonical(p)}"
            for p in sorted(path.rglob("*"))
            if p.is_file() and not p.name.startswith(".")
        ]
        return sha256_text("\n".join(parts))
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        return sha256_text(json.dumps(yaml.safe_load(text), sort_keys=True, default=str))
    if suffix == ".json":
        return sha256_text(json.dumps(json.loads(text), sort_keys=True))
    return sha256_text(text)


def schema_sha256() -> str:
    return sha256_text(json.dumps(wire_schema(), sort_keys=True))


def current_version(settings: Settings) -> str:
    return settings.active_version


def manifest_path(settings: Settings, version: str | None = None) -> Path:
    return settings.benchmarks_dir / (version or current_version(settings)) / "manifest.json"


def load_manifest(settings: Settings, version: str | None = None) -> dict[str, Any] | None:
    path = manifest_path(settings, version)
    return read_json(path) if path.exists() else None


def save_manifest(settings: Settings, manifest: dict[str, Any]) -> None:
    write_json(manifest_path(settings, manifest["version"]), manifest)


def compute_hashes(settings: Settings) -> dict[str, Any]:
    chunks = load_chunks(settings)
    return {
        "hashes": {
            "guideline": sha256_canonical(settings.paths["guideline"]),
            "examples": sha256_canonical(settings.paths["examples"]),
            "schema": schema_sha256(),
            "criteria": sha256_canonical(settings.paths["criteria"]),
            "teacher_scoring": sha256_canonical(settings.paths["teacher_scoring"]),
            "budget": sha256_canonical(settings.paths["budget"]),
            "domain": sha256_canonical(settings.paths["domain"]),
        },
        "chunks": {c.chunk_id: sha256_text(c.text) for c in chunks if c.split == "main"},
        "holdout_chunks": {c.chunk_id: sha256_text(c.text) for c in chunks if c.split == "holdout"},
        "train_chunks": {c.chunk_id: sha256_text(c.text) for c in chunks if c.split == "train"},
    }


def _diff(frozen: dict[str, Any], current: dict[str, Any]) -> list[str]:
    diffs = []
    for key in ("hashes", "chunks", "holdout_chunks", "train_chunks"):
        a, b = frozen.get(key, {}), current.get(key, {})
        for name in sorted(set(a) | set(b)):
            if a.get(name) != b.get(name):
                diffs.append(f"{key}.{name}")
    return diffs


def _reruns_for_new_version(existing: dict[str, Any] | None) -> int:
    """A new version created from the `revise` state is the (next) holdout rerun."""
    if not existing:
        return 0
    return existing.get("reruns", 0) + (1 if existing.get("pilot_state") == "revise" else 0)


def freeze_criteria(
    settings: Settings, new_version: str | None = None, rationale: str | None = None
) -> dict[str, Any]:
    current = compute_hashes(settings)
    if not current["chunks"] and not settings.test_fixture:
        raise ValidationFailed("no main chunks found; build and split the corpus before freezing")
    existing = load_manifest(settings)
    if existing and not new_version:
        diffs = _diff(existing, current)
        if diffs:
            raise FrozenHashMismatch(
                f"{existing['version']} is already frozen and differs in {diffs}; "
                "use --new-version <v> --rationale <text>"
            )
        return existing
    if new_version:
        if not (rationale and rationale.strip()):
            raise UsageError("--new-version requires --rationale")
        if manifest_path(settings, new_version).exists():
            raise UsageError(f"benchmark version {new_version} already exists")
    version = new_version or current_version(settings)
    manifest = {
        "version": version,
        "state": "criteria_frozen",
        "pilot_state": (existing or {}).get("pilot_state", "criteria_frozen")
        if new_version
        else "criteria_frozen",
        "test_only": settings.test_fixture,
        "frozen_at": _now(),
        **current,
        "benchmark": None,
        "supersedes": existing["version"] if (existing and new_version) else None,
        "rationale": rationale,
        "reruns": _reruns_for_new_version(existing) if new_version else 0,
        "history": [{"ts": _now(), "event": "criteria_frozen"}],
    }
    save_manifest(settings, manifest)
    (settings.benchmarks_dir / "current").write_text(version + "\n", encoding="utf-8")
    return manifest


def verify_frozen(settings: Settings) -> dict[str, Any]:
    manifest = load_manifest(settings)
    if not manifest:
        raise FrozenHashMismatch("criteria are not frozen: run `pilot freeze` before labeling")
    diffs = _diff(manifest, compute_hashes(settings))
    if diffs:
        raise FrozenHashMismatch(f"frozen hashes of {manifest['version']} differ: {diffs}")
    return manifest


def freeze_benchmark(
    settings: Settings,
    reference_runs: list[str],
    run_backends: dict[str, str],
    consensus_path: Path,
    contested_path: Path,
) -> dict[str, Any]:
    manifest = verify_frozen(settings)
    mock_runs = [r for r in reference_runs if run_backends.get(r) == "mock"]
    if mock_runs and not settings.test_fixture:
        raise ValidationFailed(
            f"runs {mock_runs} used the mock backend; only fixture configs "
            "(test_fixture: true) may freeze a benchmark from mock runs"
        )
    block = {
        "reference_runs": reference_runs,
        "consensus_sha256": sha256_canonical(consensus_path),
        "contested_sha256": sha256_canonical(contested_path),
        "frozen_at": _now(),
    }
    if manifest.get("state") == "frozen":
        if manifest["benchmark"]["consensus_sha256"] != block["consensus_sha256"] or manifest[
            "benchmark"
        ]["contested_sha256"] != block["contested_sha256"]:
            raise FrozenHashMismatch(
                f"benchmark {manifest['version']} is already frozen with a different consensus; "
                "use `pilot freeze --new-version`"
            )
        return manifest
    manifest["benchmark"] = block
    manifest["state"] = "frozen"
    manifest["test_only"] = bool(manifest.get("test_only") or mock_runs)
    manifest["history"].append({"ts": _now(), "event": "benchmark_frozen"})
    if manifest.get("pilot_state") in ("criteria_frozen", "rerun_holdout"):
        manifest["pilot_state"] = "labeled"
    save_manifest(settings, manifest)
    return manifest


def verify_benchmark_frozen(settings: Settings) -> dict[str, Any]:
    manifest = verify_frozen(settings)
    if manifest.get("state") != "frozen":
        raise ValidationFailed(
            "benchmark is not frozen: run `pilot freeze --benchmark` after `pilot consensus`"
        )
    analysis = settings.analysis_dir
    for key, name in (("consensus_sha256", "consensus.jsonl"),
                      ("contested_sha256", "contested.jsonl")):
        path = analysis / name
        if not path.exists() or sha256_canonical(path) != manifest["benchmark"][key]:
            raise FrozenHashMismatch(
                f"{name} differs from the frozen benchmark {manifest['version']}")
    return manifest


def set_pilot_state(settings: Settings, state: str, event: str | None = None) -> dict[str, Any]:
    if state not in PILOT_STATES:
        raise UsageError(f"unknown pilot state {state}")
    manifest = load_manifest(settings)
    if not manifest:
        raise FrozenHashMismatch("no manifest; run `pilot freeze` first")
    manifest["pilot_state"] = state
    manifest["history"].append({"ts": _now(), "event": event or f"state:{state}"})
    save_manifest(settings, manifest)
    return manifest
