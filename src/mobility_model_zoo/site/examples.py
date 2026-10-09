"""Worked examples on the website: inputs from `examples/`, outputs from the published card
(research R4, checks B3 and B4).

The outputs are the ones the release gate produced with the released files and wrote into the
model card. They are read from the card at `published.repo_commit` and only used if the card hashes
to `published.card_sha256`, so the site shows exactly what was published. Every quote is checked
against its offsets in the input before it is shown.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import jsonschema

from mobility_model_zoo.release.card import parse_card_examples
from mobility_model_zoo.release.errors import GateFailed, UsageError
from mobility_model_zoo.release.registry import Registry, load_yaml

CACHE = Path(".cache") / "site"
# Frequent function words, to mark the language of an example text for screen readers (WCAG 3.1.2).
FUNCTION_WORDS = {
    "de": {"und", "ich", "nicht", "der", "die", "das", "ist", "mit", "wir", "es", "ein", "eine", "zu"},
    "en": {"and", "the", "is", "not", "with", "we", "it", "a", "an", "to", "of", "our", "my"},
}
SHAREABLE_SOURCES = {"synthetic"}


def _download_card(repo: str, revision: str) -> bytes:
    from huggingface_hub import hf_hub_download

    path = hf_hub_download(repo, "README.md", revision=revision)
    return Path(path).read_bytes()


def card_outputs(
    reg: Registry, name: str, version: str, offline: bool = False, refresh: bool = False
) -> dict[str, str]:
    """File name -> output text, from the published card of this version (cached)."""
    record = reg.record_raw(name, version)
    published = record.get("published") or {}
    commit, sha = published.get("repo_commit"), published.get("card_sha256")
    if not commit or not sha:
        raise GateFailed([f"B3 {name} {version}: not published (no repo_commit or card_sha256)"])
    cache = reg.root / CACHE / name / f"{version}.json"
    if cache.exists() and not refresh:
        data = json.loads(cache.read_text(encoding="utf-8"))
        if data.get("repo_commit") == commit and data.get("card_sha256") == sha:
            return data["outputs"]
    if offline:
        raise UsageError(f"{name} {version}: example outputs not cached ({cache}); build once online")
    repo = reg.model_raw(name)["repos"]["public"]
    card = _download_card(repo, commit)
    got = hashlib.sha256(card).hexdigest()
    if got != sha:
        raise GateFailed([f"B3 {name} {version}: card hash {got} is not card_sha256 {sha}"])
    outputs = parse_card_examples(card.decode("utf-8"))
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(
        json.dumps({"repo_commit": commit, "card_sha256": sha, "outputs": outputs}, indent=1) + "\n",
        encoding="utf-8",
    )
    return outputs


# ---- spans ------------------------------------------------------------------------------------
def language(text: str, languages: list[str]) -> str:
    """The model language whose function words occur most often in `text` (first on a tie)."""
    words = [w.strip(".,;:!?\"'()").lower() for w in text.split()]
    scores = {lang: sum(w in FUNCTION_WORDS.get(lang, set()) for w in words) for lang in languages}
    return max(languages, key=lambda lang: scores[lang]) if languages else "en"


def is_span_format(schema: dict[str, Any] | None) -> bool:
    """True when the output has items with `quote`, `start` and `end` (the viewer applies)."""
    if not schema:
        return False
    item = schema.get("properties", {}).get("items", {}).get("items", {})
    return {"quote", "start", "end"} <= set(item.get("properties", {}))


def spans(name: str, file: str, text: str, output: dict[str, Any]) -> list[dict[str, Any]]:
    """Ordered segments of `text`: plain text and marked quotes. B3 if a quote does not equal the
    text at its offsets or two quotes overlap."""
    items = sorted(
        enumerate(output.get("items", [])), key=lambda pair: (pair[1]["start"], pair[1]["end"])
    )
    segments, pos = [], 0
    for index, item in items:
        start, end = item["start"], item["end"]
        if text[start:end] != item["quote"]:
            raise GateFailed(
                [f"B3 {name} {file}: item {index} quote does not equal text[{start}:{end}]"]
            )
        if start < pos:
            raise GateFailed([f"B3 {name} {file}: item {index} overlaps the previous quote"])
        if start > pos:
            segments.append({"marked": False, "text": text[pos:start]})
        segments.append(
            {
                "marked": True,
                "text": item["quote"],
                "kind": item["kind"],
                "item": index,
                "start": start,
                "end": end,
            }
        )
        pos = end
    if pos < len(text):
        segments.append({"marked": False, "text": text[pos:]})
    return segments


def source_failures(reg: Registry, name: str) -> list[str]:
    """B4: examples shown on the site must be shareable (synthetic)."""
    path = reg.model_dir(name) / "examples" / "SOURCES.yaml"
    if not path.exists():
        return [f"B4 {name}: examples/SOURCES.yaml is missing"]
    declared = {e["file"]: e.get("source") for e in (load_yaml(path) or {}).get("examples", [])}
    failures = []
    for file, _ in reg.examples(name):
        source = declared.get(file)
        if source not in SHAREABLE_SOURCES:
            failures.append(f"B4 {name} {file}: source {source!r} may not be shown (only synthetic)")
    return failures


def load(
    reg: Registry,
    name: str,
    version: str,
    schema: dict[str, Any] | None,
    offline: bool = False,
    refresh: bool = False,
) -> list[dict[str, Any]]:
    """Every example of the model with its published output, validated (B3, B4)."""
    failures = source_failures(reg, name)
    if failures:
        raise GateFailed(failures)
    outputs = card_outputs(reg, name, version, offline, refresh)
    span_format = is_span_format(schema)
    out = []
    for n, (file, raw_text) in enumerate(reg.examples(name), 1):
        text = raw_text.strip()
        if file not in outputs:
            raise GateFailed([f"B3 {name} {file}: no output in the published card"])
        try:
            output = json.loads(outputs[file])
        except json.JSONDecodeError as e:
            raise GateFailed([f"B3 {name} {file}: output is not JSON ({e}); truncated?"]) from None
        if schema is not None:
            errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(output), key=str)
            if errors:
                raise GateFailed([f"B3 {name} {file}: {errors[0].message}"])
        items = output.get("items", []) if span_format else []
        out.append(
            {
                "n": n,
                "file": file,
                "text": text,
                "lang": language(text, reg.model_raw(name).get("languages", ["en"])),
                "output": output,
                "json": json.dumps(output, ensure_ascii=False, indent=2),
                "found": [
                    {
                        "index": i,
                        "kind": it.get("kind", ""),
                        "json": json.dumps(it, ensure_ascii=False, indent=2),
                    }
                    for i, it in enumerate(items)
                ],
                "segments": spans(name, file, text, output) if span_format else [],
                "span_format": span_format,
            }
        )
    return out
