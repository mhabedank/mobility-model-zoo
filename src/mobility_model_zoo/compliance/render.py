"""Render the public compliance documents from the register (contracts/documents.md, FR-021).

`render_all` returns {repo-relative path: content}. `zoo compliance render` writes them;
`--check` compares them with the committed files (check C-N3). Hand edits are drift.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from mobility_model_zoo.compliance.findings import Finding
from mobility_model_zoo.compliance.register import Register

TEMPLATES = Path(__file__).parent / "templates"
REPO_URL = "https://github.com/mhabedank/mobility-model-zoo"

OUTPUTS = {
    "PRIVACY.md": "PRIVACY.md.j2",
    "COPYRIGHT_POLICY.md": "COPYRIGHT_POLICY.md.j2",
    "SECURITY.md": "SECURITY.md.j2",
    "NOTICE": "NOTICE.j2",
    "THIRD_PARTY_NOTICES.md": "THIRD_PARTY_NOTICES.md.j2",
    "REUSE.toml": "REUSE.toml.j2",
    ".github/ISSUE_TEMPLATE/rights-request.yml": "rights-request.yml.j2",
    "docs/compliance/record-of-processing.md": "record-of-processing.md.j2",
    "docs/compliance/lia-dpia.md": "lia-dpia.md.j2",
}
RELEASE_OUTPUTS = {
    "ai-act.md": "ai-act.md.j2",
    "training-data-summary.md": "training-data-summary.md.j2",
}

# Copyright notices of third-party components that published models or the repository redistribute.
BASE_MODEL_NOTICES = {
    "FacebookAI/xlm-roberta-large": {
        "name": "XLM-RoBERTa large (FacebookAI/xlm-roberta-large)",
        "licence": "MIT",
        "copyright": "Copyright (c) Facebook, Inc. and its affiliates.",
        "url": "https://huggingface.co/FacebookAI/xlm-roberta-large",
    },
}
MIT_TEXT = (
    "Permission is hereby granted, free of charge, to any person obtaining a copy of this software and "
    'associated documentation files (the "Software"), to deal in the Software without restriction, '
    "including without limitation the rights to use, copy, modify, merge, publish, distribute, "
    "sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is "
    "furnished to do so, subject to the following conditions:\n\nThe above copyright notice and this "
    "permission notice shall be included in all copies or substantial portions of the Software.\n\n"
    'THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT '
    "NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND "
    "NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, "
    "DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT "
    "OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE."
)


def _env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    env.filters["creators"] = lambda c: ", ".join(c) if isinstance(c, list) else "creators unknown"
    env.filters["licence_label"] = lambda s: s.removeprefix("LicenseRef-").replace("-", " ")
    env.filters["yn"] = lambda v: {True: "yes", False: "no", "unknown": "unknown"}.get(v, str(v))
    return env


def _published_models(root: Path) -> list[tuple[str, str, dict[str, Any]]]:
    import yaml

    out = []
    for model_dir in sorted((root / "zoo" / "models").glob("*")):
        model = (
            yaml.safe_load((model_dir / "model.yaml").read_text(encoding="utf-8"))
            if (model_dir / "model.yaml").exists()
            else {}
        )
        if model.get("topic") == "sandbox":
            continue
        for rec_path in sorted((model_dir / "releases").glob("*.yaml")):
            if rec_path.name.endswith(".compliance.yaml"):
                continue
            rec = yaml.safe_load(rec_path.read_text(encoding="utf-8"))
            staged = bool((rec.get("staging") or {}).get("revision"))
            has_compliance = rec_path.with_name(f"{rec_path.stem}.compliance.yaml").exists()
            if not (rec.get("published") or staged or has_compliance):
                continue  # a draft that was never staged has no files and no training data yet
            out.append((model_dir.name, rec["version"], {"model": model, "record": rec}))
    return out


def context(reg: Register) -> dict[str, Any]:
    classes = reg.records("source-classes")
    sources = reg.records("sources")
    datasets = reg.records("datasets")
    routes = {r["id"]: r for r in reg.records("providers")}
    recipients = reg.records("recipients")
    by_route: dict[str, dict[str, Any]] = {}
    for rec in recipients:
        g = by_route.setdefault(
            rec["route_id"],
            {
                "route": routes.get(rec["route_id"]),
                "calls": 0,
                "first": rec["first_call"],
                "last": rec["last_call"],
                "roles": set(),
                "models": set(),
            },
        )
        g["calls"] += rec["calls_ok"] + rec["calls_error"]
        g["first"] = min(filter(None, [g["first"], rec["first_call"]]), default=None)
        g["last"] = max(filter(None, [g["last"], rec["last_call"]]), default=None)
        g["roles"].update(rec["roles"])
        g["models"].add(rec["model_id"])
    class_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for s in sources:
        kind = "training" if any("@" in u for u in s["used_by"]) else "benchmark"
        class_counts[s["class"]][kind] += 1
    class_publishers: dict[str, list[str]] = defaultdict(list)
    for s in sources:
        if s["class"] != "forum-review" and s["publisher"] not in class_publishers[s["class"]]:
            class_publishers[s["class"]].append(s["publisher"])
    forum_hosts = sorted(
        {
            s["origin_url"].split("/")[2].removeprefix("www.")
            for s in sources
            if s["class"] == "forum-review"
        }
    )
    models = []
    for name, version, data in _published_models(reg.root):
        model = data["model"]
        training = [s for s in sources + datasets if f"{name}@{version}" in s.get("used_by", [])]
        models.append(
            {
                "name": name,
                "version": version,
                "model": model,
                "record": data["record"],
                "training": training,
                "base_notice": BASE_MODEL_NOTICES.get(model.get("base_model") or ""),
            }
        )
    latest: dict[str, dict[str, Any]] = {}
    for m in models:
        latest[m["name"]] = m  # releases are sorted, so the last one wins
    return {
        "controller": reg.controller(),
        "classes": classes,
        "class_counts": {k: dict(v) for k, v in class_counts.items()},
        "class_publishers": dict(class_publishers),
        "forum_hosts": forum_hosts,
        "sources": sources,
        "datasets": datasets,
        "routes": routes,
        "recipients": by_route,
        "decisions": {d["id"]: d for d in reg.records("decisions")},
        "lists": {"ai_agents": (reg.lists("ai-user-agents") or {}).get("agents", [])},
        "models": list(latest.values()),
        "repo_url": REPO_URL,
        "user_agent": __import__("mobility_model_zoo.compliance.signals", fromlist=["x"]).USER_AGENT,
        "mit_text": MIT_TEXT,
        "updated": max(
            [d.get("last_reviewed", "") for d in classes + list(routes.values())]
            + [reg.controller().get("last_reviewed", "")]
        ),
    }


def render_all(reg: Register) -> dict[str, str]:
    env = _env()
    ctx = context(reg)
    out = {path: env.get_template(tpl).render(**ctx) for path, tpl in OUTPUTS.items()}
    for rel, data in reg.files.items():
        if reg.stems[rel] != "release-compliance":
            continue
        base = rel.removesuffix(".compliance.yaml")
        model = next((m for m in ctx["models"] if m["name"] == data["model"]), None)
        rctx = {
            **ctx,
            "rc": data,
            "release_model": model,
            "release_sources": [
                s
                for s in ctx["sources"] + ctx["datasets"]
                if s["id"]
                in set(data["provenance"]["sources"] + data["provenance"].get("benchmark_sources", []))
            ],
            "release_routes": [
                ctx["routes"][r] for r in data["provenance"]["routes"] if r in ctx["routes"]
            ],
        }
        for suffix, tpl in RELEASE_OUTPUTS.items():
            out[f"{base}.{suffix}"] = env.get_template(tpl).render(**rctx)
    return out


def drift(reg: Register, rendered: dict[str, str] | None = None) -> list[Finding]:
    rendered = rendered or render_all(reg)
    findings = []
    for rel, content in rendered.items():
        path = reg.root / rel
        if not path.exists():
            findings.append(Finding("C-N3", "drift", rel, "-", "missing; run `zoo compliance render`"))
        elif path.read_text(encoding="utf-8") != content:
            findings.append(
                Finding("C-N3", "drift", rel, "-", "differs from its rendering (hand edit?)")
            )
    return findings


def write_all(reg: Register, rendered: dict[str, str] | None = None) -> list[str]:
    rendered = rendered or render_all(reg)
    for rel, content in rendered.items():
        path = reg.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return sorted(rendered)


def today() -> str:
    return dt.date.today().isoformat()
