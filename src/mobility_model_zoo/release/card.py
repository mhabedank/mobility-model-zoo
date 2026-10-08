"""Model card rendering (contracts/model-card.md).

The card is generated from `model.yaml`, the release records of the model, the results files and
the example outputs. Nobody edits it by hand. Rendering is deterministic: the same inputs always
give the same bytes.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from importlib import resources
from typing import Any

import jinja2
import yaml

from mobility_model_zoo.release.registry import ORG, Registry, parse_version

REPO_URL = "https://github.com/mhabedank/mobility-model-zoo"
SECTIONS = (
    "Summary",
    "Intended use",
    "Out-of-scope use",
    "Input and output",
    "How to run it",
    "Examples",
    "Quality",
    "Speed and memory",
    "Limitations and risks",
    "Training data provenance",
    "Training recipe",
    "Version history",
    "License",
    "Citation",
    "About the zoo",
)
# Releases with a compliance record (feature 006) replace "Training data provenance" with these.
COMPLIANCE_SECTIONS = tuple(t for t in SECTIONS if t != "Training data provenance") + (
    "Training data and attribution",
    "Teacher and labeling models",
    "Privacy and personal data",
)
HISTORY_METRICS = 3
NO_OUTPUT = "(produced by the release gate from the staged model)"

BANNERS = {
    "experimental": (
        "Experimental.",
        "The output format may change in a minor version before 1.0.0.",
    ),
    "released": ("Released.", "The output format is stable within this major version."),
}


def num(value: Any) -> str:
    """The one way numbers are printed on a card (rule 9 compares against this)."""
    if isinstance(value, bool) or value is None:
        return str(value)
    value = float(value)
    if value.is_integer():
        return str(int(value))
    return f"{value:.4g}"


def literal(text: str) -> str:
    """A Python string literal for `{text}` in `how_to_run`."""
    return json.dumps(text.strip(), ensure_ascii=False)


def fill(code: str, repo_id: str, revision: str, text: str) -> str:
    return (
        code.replace("{repo_id}", repo_id)
        .replace("{revision}", revision)
        .replace("{text}", literal(text))
    )


def install_line(model: dict[str, Any], version: str) -> str:
    return model["card"]["install"].replace("<tag>", f"{model['name']}/v{version}")


def figure_urls(model: dict[str, Any], version: str) -> list[dict[str, str]]:
    """Figures linked at the release tag on GitHub, so a published card's images never change."""
    raw = REPO_URL.replace("https://github.com/", "https://raw.githubusercontent.com/")
    tag = f"{model['name']}/v{version}"
    return [{"alt": f["alt"], "url": f"{raw}/refs/tags/{tag}/{f['path']}"}
            for f in model["card"].get("figures", [])]


def topic_url(topic: dict[str, Any]) -> str:
    if topic.get("hf_collection"):
        return f"https://huggingface.co/collections/{topic['hf_collection']}"
    return f"https://huggingface.co/{ORG}"


def _banner(model: dict[str, Any], record: dict[str, Any], deprecated_banner: bool) -> dict[str, str]:
    if record.get("sandbox"):
        return {"title": "Pipeline test model.", "text": "Not for use. Never public."}
    if deprecated_banner and record.get("deprecated"):
        dep = record["deprecated"]
        successor = f" Use version {dep['successor']} instead." if dep.get("successor") else ""
        return {"title": "Deprecated.", "text": f"{dep['reason']}{successor}"}
    title, text = BANNERS["released" if record["status"] != "experimental" else "experimental"]
    return {"title": title, "text": text}


def front_matter(model: dict[str, Any], record: dict[str, Any], quality: dict[str, Any]) -> str:
    tags = ["mobility", "mobility-model-zoo", model["topic"], model["task"], record["status"]]
    for tag in model.get("tags", []):
        if tag not in tags:
            tags.append(tag)
    data: dict[str, Any] = {
        "license": model["license"].lower(),
        "language": list(model["languages"]),
        "library_name": model["library_name"],
        "pipeline_tag": model["pipeline_tag"],
    }
    if model.get("base_model"):
        data["base_model"] = model["base_model"]
    data["tags"] = tags
    benchmark = record["evaluation"]["benchmark"]
    data["model-index"] = [
        {
            "name": model["name"],
            "results": [
                {
                    "task": {"type": model["pipeline_tag"], "name": model["title"]},
                    "dataset": {"type": benchmark, "name": f"{benchmark} (frozen)"},
                    "metrics": [
                        {"type": q["name"], "value": q["value"], "name": q["description"]}
                        for q in quality["metrics"]
                    ],
                }
            ],
        }
    ]
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100)


def _history(reg: Registry, name: str, version: str, record: dict[str, Any], quality: dict[str, Any]):
    metric_names = [q["name"] for q in quality["metrics"][:HISTORY_METRICS]]
    versions = {v for v in reg.published_versions(name)} | {version}
    rows = []
    for v in sorted(versions, key=parse_version, reverse=True):
        rec = record if v == version else reg.record_raw(name, v)
        try:
            metrics = {q["name"]: q["value"] for q in reg.results(name, v, "quality")["metrics"]}
        except Exception:
            metrics = {}
        rows.append(
            {
                "version": v,
                "date": rec["date"],
                "status": rec["status"],
                "change_type": rec["change_type"],
                "changes": " ".join(str(rec["changes"]).split()),
                "cells": [num(metrics[n]) if n in metrics else "–" for n in metric_names],
            }
        )
    return {"metric_names": metric_names, "rows": rows}


def compliance_context(reg: Registry, name: str, version: str) -> dict[str, Any] | None:
    """Card data from the compliance register, or None if the release has no compliance record."""
    from mobility_model_zoo.compliance.register import Register
    from mobility_model_zoo.compliance.render import BASE_MODEL_NOTICES, MIT_TEXT

    root = reg.zoo.parent
    creg = Register.load(root)
    rc = creg.release(name, version)
    if rc is None:
        return None
    model = reg.model(name)
    sources = sorted(
        (s for s in creg.sources_for(name, version) if s["permitted_use"] == "training_allowed"),
        key=lambda s: (s["class"], s["title"]),
    )
    roles: dict[str, set[str]] = {}
    for rec in creg.records("recipients"):
        roles.setdefault(rec["route_id"], set()).update(rec["roles"])
    routes = []
    for rid in rc["provenance"]["routes"]:
        route = creg.route(rid) or {"id": rid, "hosting_provider": "unknown", "model_id": rid}
        routes.append({**route, "roles": sorted(roles.get(rid, set()))})
    lint = creg.lists("card-lint") or {}
    return {
        "rc": rc,
        "sources": sources,
        "routes": routes,
        "base_notice": BASE_MODEL_NOTICES.get(model.get("base_model") or ""),
        "mit_text": MIT_TEXT,
        "security": model["topic"] in lint.get("security_topics", []),
        "decisions": [creg.decision(d) for d in rc.get("decisions", []) if creg.decision(d)],
        "controller": creg.controller(),
    }


@dataclass
class CardInput:
    """Everything a card is rendered from. `examples` maps file name -> model output (or None)."""

    reg: Registry
    name: str
    version: str
    record: dict[str, Any] | None = None
    example_outputs: dict[str, str] | None = None
    deprecated_banner: bool = True


def render(inp: CardInput) -> str:
    reg, name, version = inp.reg, inp.name, inp.version
    model = reg.model(name)
    record = inp.record if inp.record is not None else reg.record(name, version)
    topic = reg.topic(model["topic"]) or {"id": model["topic"], "title": model["topic"]}
    quality = reg.results(name, version, "quality")
    performance = reg.results(name, version, "performance")
    examples = reg.examples(name)
    outputs = inp.example_outputs or {}
    first_text = examples[0][1] if examples else ""

    env = jinja2.Environment(
        loader=jinja2.FunctionLoader(
            lambda n: (
                resources.files("mobility_model_zoo.release")
                .joinpath(f"templates/{n}")
                .read_text(encoding="utf-8")
            )
        ),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        undefined=jinja2.StrictUndefined,
        autoescape=False,
    )
    env.filters["num"] = num
    text = env.get_template("model_card.md.j2").render(
        m=model,
        r=record,
        topic=topic,
        topic_url=topic_url(topic),
        banner=_banner(model, record, inp.deprecated_banner),
        front_matter=front_matter(model, record, quality),
        install=install_line(model, version),
        figures=figure_urls(model, version),
        how_to_run=fill(
            model["card"]["how_to_run"], model["repos"]["public"], f"v{version}", first_text
        ).strip(),
        examples=[
            {"name": n, "text": t.strip(), "output": outputs.get(n, NO_OUTPUT).strip()}
            for n, t in examples
        ],
        quality=quality,
        performance=performance,
        history=_history(reg, name, version, record, quality),
        c=compliance_context(reg, name, version),
        repo_url=REPO_URL,
        org=ORG,
    )
    return _normalize(text)


def _normalize(text: str) -> str:
    """Blank line before headings and tables (outside code fences), at most one blank line."""
    out: list[str] = []
    fenced = False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        elif not fenced and out and out[-1].strip():
            starts_block = line.startswith("#") or (line.startswith("|") and not out[-1].startswith("|"))
            if starts_block:
                out.append("")
        out.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip("\n") + "\n"


# ---- reading cards back (rules 9 and 10) -------------------------------------------------------
def split_card(card: str) -> tuple[dict[str, Any], str]:
    """(front matter, body)."""
    if not card.startswith("---\n"):
        return {}, card
    end = card.find("\n---\n", 4)
    if end < 0:
        return {}, card
    return yaml.safe_load(card[4:end]) or {}, card[end + 5 :]


def sections(body: str) -> dict[str, str]:
    """`## Heading` -> section text."""
    out: dict[str, str] = {}
    current = None
    for line in body.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            out[current] = ""
        elif current is not None:
            out[current] += line + "\n"
    return out


def tables(section: str) -> list[list[dict[str, str]]]:
    """Markdown tables in a section, as lists of {column: cell}."""
    found, rows, header = [], [], None
    for line in section.splitlines() + [""]:
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if header is None:
                header = cells
            elif set("".join(cells)) <= set("-: "):
                continue
            else:
                rows.append(dict(zip(header, cells, strict=False)))
        else:
            if header is not None:
                found.append(rows)
            rows, header = [], None
    return found
