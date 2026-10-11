"""Independent re-check of the usage decision (SC-005) and duplicate audit (SC-008), research R8.

Two readers classify the licence evidence page of each sampled entry independently of the stored
decision: a deterministic matcher over licence names, URLs and badges, and a local model of a
different family than the discovery agent (DGX Spark, OpenAI-compatible endpoint at $OLLAMA_HOST).
Page text is held in memory only. Results are reported as agreement, not accuracy (constitution III).
"""

from __future__ import annotations

import copy
import datetime as dt
import json
import os
import random
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from mobility_model_zoo.catalog import rules
from mobility_model_zoo.catalog.checks import Throttle, make_client
from mobility_model_zoo.catalog.model import Catalog, licence_allowlist
from mobility_model_zoo.catalog.validate import DedupeIndex

MIN_AGREEMENT = 0.90
MAX_DUPLICATE_RATE = 0.02
USABLE = ("training_allowed", "benchmark_only")
TEXT_LIMIT = 6000

CC_URL = re.compile(r"creativecommons\.org/(licenses|publicdomain)/([a-z-]+)/(\d\.\d)", re.I)
CC_TEXT = re.compile(r"\bCC[\s-]?(BY(?:[\s-](?:NC|SA|ND)){0,2})[\s-]?(\d\.\d)\b", re.I)
PATTERNS = [
    (re.compile(r"\bCC0\b|creativecommons\.org/publicdomain/zero", re.I), "CC0-1.0"),
    (re.compile(r"open government licence", re.I), "LicenseRef-OGL-UK-3.0"),
    (re.compile(r"licence ouverte|etalab", re.I), "etalab-2.0"),
    (re.compile(r"datenlizenz deutschland.{0,20}namensnennung", re.I), "DL-DE-BY-2.0"),
    (re.compile(r"open data commons attribution|odc-by", re.I), "ODC-By-1.0"),
    (re.compile(r"\bODbL\b|open database license", re.I), "ODbL-1.0"),
    (
        re.compile(
            r"all rights reserved|todos los derechos reservados|wszelkie prawa zastrzeżone|無断転載",
            re.I,
        ),
        "LicenseRef-proprietary",
    ),
]


def match_licence(text: str) -> str:
    """Deterministic reading of a licence page: an SPDX id, LicenseRef-proprietary or unknown."""
    m = CC_URL.search(text)
    if m and m.group(1).lower() == "licenses":
        return f"CC-{m.group(2).upper()}-{m.group(3)}"
    m = CC_TEXT.search(text)
    if m:
        parts = re.split(r"[\s-]+", m.group(1).upper())
        return f"CC-{'-'.join(parts)}-{m.group(2)}"
    for pattern, lid in PATTERNS:
        if pattern.search(text):
            return lid
    return "unknown"


def _visible_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    # keep link targets: licence badges are often only an <a href> to creativecommons.org
    html = re.sub(r'(?i)href=["\']([^"\']+)["\']', r" \1 ", html)
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def local_model_reader(model: str, host: str | None = None) -> Callable[[str], str]:
    """A reader that asks a local OpenAI-compatible model for the licence id."""
    base = (host or os.environ.get("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")

    def read(text: str) -> str:
        prompt = (
            "Which licence does this web page state for the resource it describes? Answer with JSON "
            '{"licence": "<SPDX id, or LicenseRef-proprietary if all rights are reserved, '
            'or unknown>"}. '
            "Use unknown if the page states no licence.\n\nPAGE:\n" + text[:TEXT_LIMIT]
        )
        resp = httpx.post(
            f"{base}/v1/chat/completions",
            timeout=120,
            json={
                "model": model,
                "temperature": 0,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        m = re.search(r"\{.*\}", content, re.S)
        try:
            return str(json.loads(m.group(0))["licence"]) if m else "unknown"
        except (ValueError, KeyError):
            return "unknown"

    return read


def _use_for(entry: dict[str, Any], licence_id: str, allowlist) -> str:
    probe = copy.deepcopy(entry)
    probe["licence"]["id"] = licence_id
    probe.pop("usage", None)
    return rules.apply(probe, allowlist)[0]["permitted_use"]


def run(
    cat: Catalog,
    *,
    sample: int = 30,
    dup_sample: int = 50,
    seed: int = 9,
    model: str | None = None,
    zoo_root: Path | None = None,
    transport: httpx.BaseTransport | None = None,
    reader: Callable[[str], str] | None = None,
    throttle: Throttle | None = None,
) -> dict[str, Any]:
    allowlist = licence_allowlist(zoo_root)
    rng = random.Random(seed)
    pool = sorted(
        (
            e
            for e in cat.entries.values()
            if e.get("usage")
            and e["licence"]["id"] != "unknown"
            and e["licence"].get("evidence_url")
            and e["status"]["value"] in ("verified", "cleared", "fetched")
        ),
        key=lambda e: e["id"],
    )
    picked = rng.sample(pool, min(sample, len(pool)))
    if reader is None and model:
        reader = local_model_reader(model)
    client = make_client(transport, throttle or Throttle())
    rows = []
    try:
        for e in picked:
            row = {"id": e["id"], "stored": e["usage"]["permitted_use"], "status": e["status"]["value"]}
            try:
                page = client.get(e["licence"]["evidence_url"])
                text = _visible_text(page.text) if page.status_code < 400 else ""
            except httpx.HTTPError:
                text = ""
            matched = match_licence(text) if text else "unknown"
            row["matcher"] = {"licence": matched, "use": _use_for(e, matched, allowlist)}
            if reader is not None and text:
                try:
                    read = reader(text)
                    row["model"] = {"licence": read, "use": _use_for(e, read, allowlist)}
                except (httpx.HTTPError, KeyError, ValueError) as err:
                    row["model"] = {
                        "licence": "error",
                        "use": "undetermined",
                        "error": type(err).__name__,
                    }
            rows.append(row)
    finally:
        client.close()

    failures = []
    agreement: dict[str, float | None] = {}
    for name in ("matcher", "model"):
        judged = [r for r in rows if name in r]
        agreement[name] = (
            round(sum(r[name]["use"] == r["stored"] for r in judged) / len(judged), 4)
            if judged
            else None
        )
        if agreement[name] is not None and agreement[name] < MIN_AGREEMENT:
            failures.append(f"{name} agreement {agreement[name]:.0%} < {MIN_AGREEMENT:.0%}")
    unusable_cleared = sorted(
        {
            r["id"]
            for r in rows
            if r["status"] == "cleared"
            for name in ("matcher", "model")
            if name in r and r[name]["use"] not in USABLE
        }
    )
    if unusable_cleared:
        failures.append(f"cleared but not usable on re-check: {', '.join(unusable_cleared)}")

    all_entries = sorted(cat.entries.values(), key=lambda e: e["id"])
    dup_pick = random.Random(seed + 1).sample(all_entries, min(dup_sample, len(all_entries)))
    duplicates = []
    for e in dup_pick:
        others = DedupeIndex.build(
            x
            for x in all_entries
            if x["id"] != e["id"] and (x.get("relations") or {}).get("duplicate_of") != e["id"]
        )
        hit = others.exact(e)
        if hit and (e.get("relations") or {}).get("duplicate_of") != hit[0]:
            duplicates.append({"id": e["id"], "of": hit[0], "reason": hit[1]})
    dup_rate = round(len(duplicates) / len(dup_pick), 4) if dup_pick else 0.0
    if dup_rate >= MAX_DUPLICATE_RATE:
        failures.append(f"duplicate rate {dup_rate:.1%} ≥ {MAX_DUPLICATE_RATE:.0%}")
    return {
        "date": dt.date.today().isoformat(),
        **cat.version(),
        "seed": seed,
        "model": model,
        "sample_ids": [r["id"] for r in rows],
        "rows": rows,
        "agreement": agreement,
        "unusable_cleared": unusable_cleared,
        "duplicate_audit": {"sample": len(dup_pick), "duplicates": duplicates, "rate": dup_rate},
        "passed": not failures,
        "failures": failures,
    }


def render(rep: dict[str, Any]) -> str:
    def pct(x):
        return "not run" if x is None else f"{x:.0%}"

    lines = [
        f"# Audit {rep['date']}",
        "",
        f"Index `{(rep['catalog_commit'] or 'uncommitted')[:12]}` · seed {rep['seed']} · "
        f"model {rep['model'] or 'none'}",
        "",
        "Agreement of the stored permitted use with independent readings of the licence evidence page "
        "(constitution III: agreement, not accuracy).",
        "",
        f"- Deterministic matcher: {pct(rep['agreement']['matcher'])}",
        f"- Local model: {pct(rep['agreement']['model'])}",
        f"- Cleared entries not usable on re-check: {', '.join(rep['unusable_cleared']) or 'none'}",
        f"- Duplicates in {rep['duplicate_audit']['sample']} entries: "
        f"{len(rep['duplicate_audit']['duplicates'])} ({rep['duplicate_audit']['rate']:.1%})",
        "",
        "| Entry | Status | Stored | Matcher | Model |",
        "|---|---|---|---|---|",
    ]
    for r in rep["rows"]:
        model = r.get("model", {})
        lines.append(
            f"| {r['id']} | {r['status']} | {r['stored']} | {r['matcher']['licence']} → "
            f"{r['matcher']['use']} | {model.get('licence', '-')} → {model.get('use', '-')} |"
        )
    lines += (
        ["", f"Result: {'PASS' if rep['passed'] else 'FAIL'}"]
        + [f"- {f}" for f in rep["failures"]]
        + [""]
    )
    return "\n".join(lines)
