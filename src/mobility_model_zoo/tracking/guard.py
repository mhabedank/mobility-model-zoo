"""What may enter the tracking store (FR-024, research R8, contracts/tracking.md).

An allow-list: keys of a fixed form, `mmz.*` tags from a fixed set, short single-line param values,
finite metrics, and only the artifact files the zoo writes itself. A refused value raises
`GuardRefused`; the run layer drops it with a warning at run time and re-raises in tests (`STRICT`).
"""

from __future__ import annotations

import math
import re
from pathlib import Path

from mobility_model_zoo.release.errors import ZooError

KEY = re.compile(r"^[a-z0-9_./-]{1,120}$")
MAX_PARAM = 120
MAX_SPACES = 3
MAX_ARTIFACT = 1_000_000

TAGS = frozenset(
    {
        "mmz.kind",
        "mmz.topic",
        "mmz.task",
        "mmz.id",
        "mmz.version",
        "mmz.sha256",
        "mmz.frozen_at",
        "mmz.permitted_use",
        "mmz.licence",
        "mmz.superseded_by",
        "mmz.git_commit",
        "mmz.git_clean",
        "mmz.hardware",
        "mmz.benchmark",
        "mmz.training_set",
        "mmz.model",
        "mmz.model_version",
        "mmz.candidate",
        "mmz.imported",
        "mmz.import_key",
        "mmz.spike",
        "mmz.input_unresolved",
        "mmz.offline_id",
        "mmz.offline_synced",
    }
)
# MLflow's own tags the client sets; `mlflow.source.name` is reduced to a repository path.
SYSTEM_TAGS = frozenset({"mlflow.runName", "mlflow.user", "mlflow.source.type", "mlflow.source.name"})

ARTIFACTS = frozenset(
    {
        "profile.json",
        "span_config.json",
        "report.json",
        "export-config.json",
        "summary.json",
        "summary.md",
        "quality.json",
        "performance.json",
    }
)
NEVER = (".safetensors", ".bin", ".joblib", ".tflite", ".npz", ".keras", ".h5", ".jsonl", ".pt", ".onnx")


class GuardRefused(ZooError):
    exit_code = 7


def check_key(key: str) -> str:
    if not KEY.match(key):
        raise GuardRefused(f"key {key!r} does not match {KEY.pattern}")
    return key


def _repo_relative(value: str) -> str:
    """Home-directory paths become repository-relative or `$MMZ_DATA/...`; others are refused."""
    from mobility_model_zoo.edge.paths import data_root, repo_root

    if not (value.startswith("/") or value.startswith("~")):
        return value
    path = Path(value).expanduser()
    for base, prefix in ((repo_root(), ""), (data_root(), "$MMZ_DATA/")):
        try:
            return prefix + path.resolve().relative_to(base.resolve()).as_posix()
        except ValueError:
            continue
    raise GuardRefused(f"absolute path outside the repository and $MMZ_DATA: {value[:40]}…")


def check_param(key: str, value: object) -> str:
    check_key(key)
    if isinstance(value, bool) or value is None:
        return str(value).lower()
    if isinstance(value, int | float):
        return repr(value)
    text = _repo_relative(str(value))
    if len(text) > MAX_PARAM or "\n" in text or "\r" in text or text.count(" ") > MAX_SPACES:
        raise GuardRefused(f"param {key}: value is free text (only short single values are stored)")
    return text


def check_tag(key: str, value: object) -> str:
    if key not in TAGS and key not in SYSTEM_TAGS:
        raise GuardRefused(f"tag {key} is not on the allow-list (contracts/tracking.md)")
    text = str(value)
    if key == "mlflow.source.name":
        text = _repo_relative(text)
    if len(text) > MAX_PARAM or "\n" in text:
        raise GuardRefused(f"tag {key}: value too long or multi-line")
    return text


def check_metric(key: str, value: object) -> float:
    check_key(key)
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise GuardRefused(f"metric {key}: {value!r} is not a finite number")
    return float(value)


def check_artifact(path: Path, name: str | None = None) -> Path:
    """Only allow-listed files the zoo writes itself, at most 1 MB, and never under data/."""
    from mobility_model_zoo.edge.paths import data_root, repo_root

    path = Path(path)
    published = name or path.name
    is_config = _artifact_kind(path, published)
    resolved = path.resolve()
    if is_config:
        try:
            resolved.relative_to((repo_root() / "configs").resolve())
        except ValueError:
            raise GuardRefused(f"artifact {published}: only committed files under configs/") from None
    for forbidden in (repo_root() / "data", data_root()):
        try:
            resolved.relative_to(forbidden.resolve())
        except ValueError:
            continue
        if published not in {"span_config.json", "report.json", "export-config.json", "summary.json"}:
            raise GuardRefused(f"artifact {published}: files under data/ or $MMZ_DATA are not stored")
    if not path.is_file() or path.stat().st_size > MAX_ARTIFACT:
        raise GuardRefused(f"artifact {published}: missing or larger than 1 MB")
    return path


def _artifact_kind(path: Path, published: str) -> bool:
    """Name rules shared by writing and syncing; True for a `config/<name>.yaml` copy."""
    if path.suffix.lower() in NEVER or published.lower().endswith(NEVER):
        raise GuardRefused(f"artifact {published}: model and data files never go into the store")
    is_config = published.startswith("config/") and published.endswith((".yaml", ".yml"))
    if (published not in ARTIFACTS and not is_config) or ".." in published.split("/"):
        raise GuardRefused(f"artifact {published} is not on the allow-list (contracts/tracking.md)")
    return is_config


def check_synced_artifact(path: Path, published: str) -> Path:
    """An artifact copied into an offline log folder: name, kind and size (its origin was checked
    when the run wrote it, research R17)."""
    path = Path(path)
    _artifact_kind(path, published)
    if not path.is_file() or path.stat().st_size > MAX_ARTIFACT:
        raise GuardRefused(f"artifact {published}: missing or larger than 1 MB")
    return path


def sanitize_key(text: str) -> str:
    """A metric or param key part from a free value, e.g. an attack family name."""
    return re.sub(r"[^a-z0-9_./-]+", "_", str(text).lower()).strip("_")[:60] or "_"
