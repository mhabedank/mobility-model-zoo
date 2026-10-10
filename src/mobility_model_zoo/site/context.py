"""What the website shows, read from the registry (specs/008-zoo-website/data-model.md).

Models, their status and releases come from the same files as the model card. The only
hand-written text per model is `zoo/models/<name>/site.yaml` (the value proposition); its numbers
are `{metric:…}` placeholders that resolve against the latest release (checks B1, B2).
"""

from __future__ import annotations

import json
import subprocess
from functools import cache
from importlib import resources
from typing import Any

import jsonschema

from mobility_model_zoo.release.card import REPO_URL
from mobility_model_zoo.release.errors import GateFailed
from mobility_model_zoo.release.registry import Registry, load_yaml, parse_version
from mobility_model_zoo.site import facts

HF = "https://huggingface.co"


@cache
def site_schema(name: str) -> dict[str, Any]:
    text = resources.files("mobility_model_zoo.site").joinpath(f"schemas/{name}.schema.json")
    return json.loads(text.read_text(encoding="utf-8"))


def _schema_errors(name: str, data: Any) -> list[str]:
    validator = jsonschema.Draft202012Validator(
        site_schema(name), format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER
    )
    return [
        f"{'/'.join(str(p) for p in e.absolute_path) or '(root)'}: {e.message}"
        for e in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    ]


def load_site_config(reg: Registry) -> dict[str, Any]:
    path = reg.zoo / "site.yaml"
    if not path.exists():
        raise GateFailed(["B1 zoo/site.yaml is missing"])
    data = load_yaml(path) or {}
    errors = _schema_errors("site-config", data)
    if errors:
        raise GateFailed([f"B1 zoo/site.yaml {e}" for e in errors])
    return data


# ---- models and releases ---------------------------------------------------------------------
def is_sandbox(reg: Registry, name: str) -> bool:
    model = reg.model_raw(name)
    if model.get("topic") == "sandbox":
        return True
    return any(reg.record_raw(name, v).get("sandbox") for v in reg.versions(name))


def status(reg: Registry, name: str) -> tuple[str, str | None]:
    """(`published` | `deprecated` | `in_progress`, latest published version or None)."""
    published = reg.published_versions(name)
    if not published:
        return "in_progress", None
    latest = max(published, key=parse_version)
    if reg.record_raw(name, latest).get("deprecated"):
        return "deprecated", latest
    return "published", latest


def gh_blob(path: str, ref: str = "main") -> str:
    return f"{REPO_URL}/blob/{ref}/{path}"


def site_release(reg: Registry, name: str, version: str) -> dict[str, Any]:
    rec = reg.record_raw(name, version)
    model = reg.model_raw(name)
    tag = f"{name}/v{version}"
    rel = f"zoo/models/{name}/releases"
    links = {}
    for key, suffix in (
        ("training_data_summary", "training-data-summary.md"),
        ("ai_act", "ai-act.md"),
        ("compliance", "compliance.yaml"),
    ):
        if (reg.model_dir(name) / "releases" / f"{version}.{suffix}").exists():
            links[key] = gh_blob(f"{rel}/{version}.{suffix}", tag)
    published = rec.get("published") or {}
    if published.get("repo_commit"):
        links["hf_tree"] = f"{HF}/{model['repos']['public']}/tree/{published['repo_commit']}"
    return {
        "version": version,
        "date": str(rec["date"]),
        "status": rec["status"],
        "deprecated": rec.get("deprecated"),
        "change_type": rec.get("change_type", ""),
        "changes": " ".join(str(rec.get("changes", "")).split()),
        "output_format_version": rec.get("output_format_version"),
        "published": published,
        "tag": tag,
        "links": links,
    }


def site_models(reg: Registry) -> list[dict[str, Any]]:
    """Every non-sandbox model with its status; published ones with their releases."""
    out = []
    for name in reg.model_names():
        if is_sandbox(reg, name):
            continue
        model = reg.model_raw(name)
        state, latest = status(reg, name)
        releases = [
            site_release(reg, name, v)
            for v in sorted(reg.published_versions(name), key=parse_version, reverse=True)
        ]
        out.append(
            {
                "name": name,
                "m": model,
                "status": state,
                "latest": latest,
                "releases": releases,
                "pitch": load_pitch(reg, name) if latest else optional_pitch(reg, name),
            }
        )
    return out


# ---- the value proposition (site.yaml) --------------------------------------------------------
def pitch_path(reg: Registry, name: str):
    return reg.model_dir(name) / "site.yaml"


def optional_pitch(reg: Registry, name: str) -> dict[str, Any] | None:
    path = pitch_path(reg, name)
    return (load_yaml(path) or {}) if path.exists() else None


def load_pitch(reg: Registry, name: str) -> dict[str, Any]:
    """`site.yaml` of a published model; B1 if it is missing or invalid."""
    path = pitch_path(reg, name)
    if not path.exists():
        raise GateFailed([f"B1 {name}: zoo/models/{name}/site.yaml is missing"])
    data = load_yaml(path) or {}
    errors = _schema_errors("site", data)
    if errors:
        raise GateFailed([f"B1 {name}: site.yaml {e}" for e in errors])
    return data


def pitch_errors(reg: Registry, name: str, version: str) -> list[str]:
    """Everything that would stop the site build for this model at this version. The release gate
    (rule 17) runs it before a publish, so a published release always builds (FR-005)."""
    try:
        pitch = load_pitch(reg, name)
    except GateFailed as e:
        return e.failures
    errors = []
    texts = [pitch.get("tagline", ""), pitch.get("audience", ""), pitch.get("hardware_note", "")]
    texts += [d["title"] + " " + d["text"] for d in pitch.get("differentiators", [])]
    for text in texts:
        for kind, metric_name in facts.placeholders(text):
            try:
                facts.metric(reg, name, version, kind, metric_name)
            except GateFailed as e:
                errors += e.failures
    example = pitch.get("quickstart_example")
    if example and not (reg.model_dir(name) / "examples" / example).exists():
        errors.append(f"B1 {name}: quickstart_example {example} is not in examples/")
    for chart in pitch.get("charts", []):
        if chart.get("labels") and not (reg.root / chart["labels"]).exists():
            errors.append(f"B1 {name}: chart label file {chart['labels']} does not exist")
        names = [
            m["name"]
            for kind in ("quality", "performance")
            if reg.results_path(name, version, kind).exists()
            for m in reg.results(name, version, kind)["metrics"]
        ]
        if not any(n.startswith(chart["metrics"]) for n in names):
            errors.append(f"B1 {name}: no metric starts with {chart['metrics']} (chart {chart['type']})")
    return errors


def file_at_tag(reg: Registry, path: str, tag: str) -> str | None:
    """A repository file as committed at `tag`, else the working-tree file (layout changes)."""
    out = subprocess.run(
        ["git", "-C", str(reg.root), "show", f"{tag}:{path}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode == 0:
        return out.stdout
    local = reg.root / path
    return local.read_text(encoding="utf-8") if local.exists() else None
