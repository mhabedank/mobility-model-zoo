"""Deterministic checks, independent of any model judgment (FR-026, Principle III)."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any

from mobility_model_zoo.productdev.jtbd.config import Settings
from mobility_model_zoo.productdev.jtbd.corpus.store import chunk_map
from mobility_model_zoo.productdev.jtbd.jsonio import read_json, write_json, write_jsonl
from mobility_model_zoo.productdev.jtbd.quotes import locate
from mobility_model_zoo.productdev.jtbd.runs import load_run_manifest, produced_dimensions, run_dir
from mobility_model_zoo.productdev.jtbd.schema import (
    ACTOR_TYPES,
    EVIDENCE_ORDER,
    EVIDENCE_SCOPES,
    KINDS,
    ExtractionOutput,
)

NUMBER_WORDS = {
    # English
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven",
    "twelve", "twenty", "thirty", "forty", "fifty", "hundred", "thousand", "million", "billion",
    "percent", "half", "quarter", "third", "dozen", "twice", "double", "triple", "once",
    # German
    "eins", "ein", "eine", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun",
    "zehn", "elf", "zwölf", "zwanzig", "dreißig", "vierzig", "fünfzig", "hundert", "tausend",
    "millionen", "milliarde", "milliarden", "prozent", "hälfte", "halb", "viertel",
    "drittel", "dutzend", "doppelt", "zweimal", "dreimal", "einmal",
}
ENUMS = {
    "kind": KINDS,
    "actor_type": ACTOR_TYPES,
    "evidence_type": EVIDENCE_ORDER,
    "evidence_scope": EVIDENCE_SCOPES,
}


def has_quantity(text: str) -> bool:
    if re.search(r"\d", text) or "%" in text:
        return True
    words = re.findall(r"[a-zäöüß]+", text.lower())
    return any(w in NUMBER_WORDS for w in words)


def _last_raw(directory, chunk_id: str) -> tuple[bool, Any]:
    """(attempted, parsed candidate of the last attempt or None if it was not JSON)."""
    attempts = sorted((directory / "raw").glob(f"{chunk_id}.a*.json"))
    if not attempts:
        return False, None
    return True, read_json(attempts[-1]).get("parsed_candidate")


def check_output(chunk_id: str, candidate: Any, text: str, rules: list[str]) -> list[dict]:
    rows: list[dict] = []
    try:
        output = ExtractionOutput.model_validate(candidate)
        rows.append({"chunk_id": chunk_id, "check": "schema_valid", "passed": True})
    except Exception as exc:  # noqa: BLE001 - any failure counts as schema failure
        rows.append({"chunk_id": chunk_id, "check": "schema_valid", "passed": False,
                     "detail": str(exc)[:300]})
        output = None
    items = candidate.get("items", []) if isinstance(candidate, dict) else []
    items = items if isinstance(items, list) else []
    if "enum_values" in rules:
        for n, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            bad = [k for k, allowed in ENUMS.items() if item.get(k) not in allowed]
            rows.append({"chunk_id": chunk_id, "item_index": n, "check": "consistency.enum_values",
                         "passed": not bad, "detail": ",".join(bad) or None})
    if output is None:
        return rows
    used: list[tuple[int, int]] = []
    for n, item in enumerate(output.items):
        span = locate(item.quote, text, used)
        if span:
            used.append(span)
        rows.append({"chunk_id": chunk_id, "item_index": n, "check": "quote_verbatim",
                     "passed": span is not None})
        if "quantified_has_quantity" in rules and item.evidence_scope == "quantified":
            rows.append({"chunk_id": chunk_id, "item_index": n,
                         "check": "consistency.quantified_has_quantity",
                         "passed": has_quantity(item.quote)})
    if "irrelevant_no_items" in rules:
        rows.append({"chunk_id": chunk_id, "check": "consistency.irrelevant_no_items",
                     "passed": output.relevant or not output.items})
    return rows


def check_span_output(chunk_id: str, candidate: Any, text: str,
                      dimensions: list[str]) -> list[dict]:
    """Checks of a jtbd-span-v1 output (feature 004): schema, verbatim spans, consistency."""
    import jsonschema

    from mobility_model_zoo.productdev.jtbd.span.extractor import SCHEMA_PATH

    rows: list[dict] = []
    errors = sorted(jsonschema.Draft202012Validator(json.loads(SCHEMA_PATH.read_text()))
                    .iter_errors(candidate), key=str)
    rows.append({"chunk_id": chunk_id, "check": "schema_valid", "passed": not errors,
                 "detail": str(errors[0].message)[:300] if errors else None})
    if errors or not isinstance(candidate, dict):
        return rows
    items = candidate["items"]
    for n, item in enumerate(items):
        start, end = item["start"], item["end"]
        rows.append({"chunk_id": chunk_id, "item_index": n, "check": "quote_verbatim",
                     "passed": start < end <= len(text) and text[start:end] == item["quote"]})
        attrs = sorted(k for k in item if k in ENUMS and k != "kind")
        rows.append({"chunk_id": chunk_id, "item_index": n, "check": "consistency.span_dimensions",
                     "passed": attrs == sorted(dimensions), "detail": ",".join(attrs) or None})
    ordered = all(a["end"] <= b["start"] for a, b in zip(items, items[1:], strict=False))
    rows.append({"chunk_id": chunk_id, "check": "consistency.span_order", "passed": ordered})
    rows.append({"chunk_id": chunk_id, "check": "consistency.span_dimensions_declared",
                 "passed": sorted(candidate["dimensions"]) == sorted(dimensions)})
    rows.append({"chunk_id": chunk_id, "check": "consistency.irrelevant_no_items",
                 "passed": candidate["relevant"] or not items})
    return rows


def consistency_rate(rates: dict[str, dict[str, Any]]) -> float | None:
    """Share of passed rows over every `consistency.*` check."""
    rows = [v for k, v in rates.items() if k.startswith("consistency.")]
    n = sum(v["n"] for v in rows)
    return round(sum(v["passed"] for v in rows) / n, 6) if n else None


def pass_rates(rows: list[dict]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[bool]] = defaultdict(list)
    for row in rows:
        grouped[row["check"]].append(bool(row["passed"]))
    return {
        check: {"n": len(v), "passed": sum(v), "rate": round(sum(v) / len(v), 6) if v else None}
        for check, v in sorted(grouped.items())
    }


def check_run(settings: Settings, run_id: str) -> dict[str, Any]:
    manifest = load_run_manifest(settings, run_id)
    directory = run_dir(settings, run_id)
    chunks = chunk_map(settings, manifest.split)
    rules = settings.pilot.get("consistency_rules", [])
    span_dims = produced_dimensions(manifest)
    rows: list[dict] = []
    for chunk_id, chunk in sorted(chunks.items()):
        parsed = directory / "parsed" / f"{chunk_id}.json"
        if parsed.exists():
            candidate = read_json(parsed)
        else:
            attempted, candidate = _last_raw(directory, chunk_id)
            if not attempted:
                continue  # chunk not labeled (yet)
        if span_dims is not None:
            rows.extend(check_span_output(chunk_id, candidate, chunk.text, span_dims))
        else:
            rows.extend(check_output(chunk_id, candidate, chunk.text, rules))
    for row in rows:
        row["run_id"] = run_id
    out_dir = settings.analysis_dir / "checks"
    write_jsonl(out_dir / f"{run_id}.jsonl", rows)
    rates = pass_rates(rows)
    write_json(out_dir / f"{run_id}.summary.json", {"run_id": run_id, "pass_rates": rates})
    return {"run_id": run_id, "pass_rates": rates}


def load_pass_rates(settings: Settings, run_id: str) -> dict[str, Any] | None:
    path = settings.analysis_dir / "checks" / f"{run_id}.summary.json"
    return read_json(path)["pass_rates"] if path.exists() else None


def dumps(candidate: Any) -> str:
    return json.dumps(candidate, ensure_ascii=False)
