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
import yaml

from mobility_model_zoo.release.card import REPO_URL, usage_line
from mobility_model_zoo.release.errors import GateFailed
from mobility_model_zoo.release.registry import Registry, load_yaml, parse_version
from mobility_model_zoo.site import budgets, facts, og

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


def release_status(reg: Registry, name: str, version: str) -> str:
    """`experimental` or `released` (feature 013). `zoo release deprecate` overwrites the record's
    status with `deprecated`; the status the version was published with is in the record at its tag."""
    status = reg.record_raw(name, version).get("status", "")
    if status != "deprecated":
        return status
    at_tag = file_at_tag(reg, f"zoo/models/{name}/releases/{version}.yaml", f"{name}/v{version}")
    old = (yaml.safe_load(at_tag) or {}).get("status") if at_tag else None
    return old if old in ("experimental", "released") else "experimental"


def short_forms(model: dict[str, Any]) -> dict[str, list[Any]]:
    card = model.get("card") or {}
    return {k: list(card.get(k) or []) for k in ("not_for", "limits_short", "unmet_criteria")}


def _resolves(reg: Registry, name: str, version: str, text: str, where: str) -> list[str]:
    errors = []
    for kind, metric_name in facts.placeholders(text):
        try:
            facts.metric(reg, name, version, kind, metric_name)
        except GateFailed as e:
            errors += [f"{where}: {f}" for f in e.failures]
    return errors


def short_form_errors(
    reg: Registry, name: str, version: str, status: str, model: dict[str, Any]
) -> list[str]:
    """Short forms of the card that a published model needs (site check D1, gate rule 18): `not_for`
    and `limits_short` exist and fit their budgets; an `experimental` release names its unmet
    criteria, a `released` one has none; every measured value resolves, every target has a source."""
    b = budgets
    short = short_forms(model)
    not_for, limits, unmet = short["not_for"], short["limits_short"], short["unmet_criteria"]
    errors = []
    if not b.NOT_FOR_ITEMS[0] <= len(not_for) <= b.NOT_FOR_ITEMS[1]:
        errors.append(
            f"card.not_for has {len(not_for)} items, needs {b.NOT_FOR_ITEMS[0]} to {b.NOT_FOR_ITEMS[1]}"
        )
    for i, text in enumerate(not_for):
        if b.words(text) > b.NOT_FOR_ITEM_WORDS:
            errors.append(f"card.not_for[{i}] has {b.words(text)} words, limit {b.NOT_FOR_ITEM_WORDS}")
    if sum(b.words(t) for t in not_for) > b.NOT_FOR_WORDS:
        errors.append(
            f"card.not_for has {sum(b.words(t) for t in not_for)} words, limit {b.NOT_FOR_WORDS}"
        )
    if not limits:
        errors.append("card.limits_short is missing")
    for i, text in enumerate(limits):
        if b.words(text) > b.LIMITS_SHORT_ITEM_WORDS:
            errors.append(
                f"card.limits_short[{i}] has {b.words(text)} words, limit {b.LIMITS_SHORT_ITEM_WORDS}"
            )
    if len(unmet) + len(limits) > b.LIMITS_SHORT_ITEMS:
        errors.append(
            f"card.unmet_criteria and card.limits_short have {len(unmet) + len(limits)} items, "
            f"limit {b.LIMITS_SHORT_ITEMS}"
        )
    if status == "experimental" and not unmet:
        errors.append("status experimental: card.unmet_criteria must name every unmet criterion")
    if status == "released" and unmet:
        errors.append("status released: card.unmet_criteria must be empty")
    for i, item in enumerate(unmet):
        where = f"card.unmet_criteria[{i}]"
        if b.words(item.get("criterion", "")) > b.UNMET_CRITERION_WORDS:
            errors.append(f"{where}.criterion is longer than {b.UNMET_CRITERION_WORDS} words")
        if b.words(item.get("note", "")) > b.UNMET_NOTE_WORDS:
            errors.append(f"{where}.note is longer than {b.UNMET_NOTE_WORDS} words")
        if not (item.get("measured") or item.get("note")):
            errors.append(f"{where} has neither measured nor note")
        errors += _resolves(reg, name, version, item.get("measured", ""), f"{where}.measured")
        source = (item.get("target") or {}).get("source")
        if source and not (reg.root / source).exists():
            errors.append(f"{where}.target.source {source} does not exist")
    for key in ("not_for", "limits_short"):
        for i, text in enumerate(short[key]):
            errors += _resolves(reg, name, version, text, f"card.{key}[{i}]")
    return errors


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
        rec = reg.record_raw(name, latest) if latest else {}
        usage = rec.get("usage") or {
            "class": model.get("usage_class", "commercial"),
            "licence": model["license"],
        }
        out.append(
            {
                "name": name,
                "m": model,
                "status": state,
                "latest": latest,
                # constitution 2.1.0: every model states what users may do with it (feature 011)
                "usage": {
                    "class": usage["class"],
                    "licence": usage["licence"],
                    "text": usage_line(model, rec),
                },
                "releases": releases,
                # feature 013: release status from the record, short forms from the card block
                "release_status": release_status(reg, name, latest) if latest else None,
                "short": short_forms(model),
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


def budget_errors(name: str, pitch: dict[str, Any]) -> list[str]:
    """Depth budgets of the hand-written website text (feature 013, gate rule 17, site check D2)."""
    b = budgets
    errors = []
    diffs = pitch.get("differentiators", [])
    lo, hi = b.DIFFERENTIATORS
    if not lo <= len(diffs) <= hi:
        errors.append(f"D2 {name}: {len(diffs)} differentiators, needs {lo} to {hi}")
    for i, d in enumerate(diffs):
        if b.words(d["title"]) > b.DIFFERENTIATOR_TITLE_WORDS:
            errors.append(
                f"D2 {name}: differentiators[{i}].title has {b.words(d['title'])} words, "
                f"limit {b.DIFFERENTIATOR_TITLE_WORDS}"
            )
        if b.words(d["text"]) > b.DIFFERENTIATOR_TEXT_WORDS:
            errors.append(
                f"D2 {name}: differentiators[{i}].text has {b.words(d['text'])} words, "
                f"limit {b.DIFFERENTIATOR_TEXT_WORDS}"
            )
    audience = pitch.get("audience", "")
    if b.words(audience) > b.AUDIENCE_WORDS:
        errors.append(f"D2 {name}: audience has {b.words(audience)} words, limit {b.AUDIENCE_WORDS}")
    texts = [("tagline", pitch.get("tagline", "")), ("audience", audience)]
    texts += [(f"differentiators[{i}]", f"{d['title']} {d['text']}") for i, d in enumerate(diffs)]
    for key, text in texts:
        if m := b.STATUS_WORDS.search(text or ""):
            errors.append(f"D4 {name}: site.yaml {key} states a release status ({m.group(0)!r})")
    return errors


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
    errors += og.share_line_errors(name, *og.share_line(pitch))
    errors += budget_errors(name, pitch)
    fmt = reg.record_raw(name, version).get("output_format_version")
    if fmt and not (reg.zoo / "formats" / f"{fmt}.yaml").exists():
        errors.append(f"B5 {name}: output format {fmt} has no zoo/formats/{fmt}.yaml")
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
