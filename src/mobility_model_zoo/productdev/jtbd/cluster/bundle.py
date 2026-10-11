"""Input bundles of the cluster stage (`jtbd-cluster-input-v1`, research R2-R4).

One JSON line per source: source metadata plus the unchanged scout output. Items get stable ids,
an exact-copy key and an independence key. Quotes are copied, never changed (spec FR-002).
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from mobility_model_zoo.productdev.jtbd.errors import ValidationFailed

INPUT_FORMAT_VERSION = "jtbd-cluster-input-v1"
SPAN_FORMAT_VERSION = "jtbd-span-v1"
ATTRIBUTES = ("actor_type", "evidence_type", "evidence_scope")
HERE = Path(__file__).resolve().parent
SPAN_SCHEMA = HERE.parent / "span" / "jtbd-span-v1.schema.json"
INPUT_SCHEMA = HERE / "jtbd-cluster-input-v1.schema.json"
# Quotation marks and punctuation stripped from both ends of a quote before hashing (research R4).
EDGE_CHARS = " \t\n\r.,;:!?…-–—\"'„“”‚‘’«»‹›()[]"
WHITESPACE = re.compile(r"\s+")


@cache
def _validator(path: Path) -> Draft202012Validator:
    return Draft202012Validator(json.loads(path.read_text(encoding="utf-8")),
                                format_checker=FormatChecker())


@dataclass(frozen=True)
class Source:
    source_id: str
    source_class: str
    date: str | None
    origin: str | None
    text_sha256: str | None
    output: dict[str, Any]


@dataclass(frozen=True)
class Item:
    item_id: str
    source_id: str
    start: int
    end: int
    kind: str
    quote: str
    score: float
    date: str | None
    independence_key: str
    origin_based: bool  # the independence key comes from an origin (thread), not a source id
    exact_copy_key: str
    attributes: dict[str, str] = field(default_factory=dict)

    def as_dict(self, group_id: str) -> dict[str, Any]:
        out: dict[str, Any] = {
            "item_id": self.item_id, "source_id": self.source_id, "start": self.start,
            "end": self.end, "kind": self.kind, "quote": self.quote, "score": self.score,
        }
        out.update(self.attributes)
        out.update({"date": self.date, "independence_key": self.independence_key,
                    "exact_copy_key": self.exact_copy_key, "group_id": group_id})
        return out


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def item_id(source_id: str, start: int, end: int, kind: str) -> str:
    return "it-" + sha256_hex("\x00".join((source_id, str(start), str(end), kind)))[:12]


def normalise_quote(quote: str) -> str:
    text = unicodedata.normalize("NFKC", quote).casefold()
    return WHITESPACE.sub(" ", text).strip(EDGE_CHARS)


def exact_copy_key(kind: str, quote: str) -> str:
    return sha256_hex(f"{kind}\x00{normalise_quote(quote)}")


def file_sha256(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_bundle(path: Path | str) -> list[Source]:
    """Read and validate one bundle. Refuses other format versions and duplicate source ids."""
    path = Path(path)
    lines = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        where = f"{path}:{lineno}"
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValidationFailed(f"{where}: not JSON ({exc.msg})") from exc
        lines.append((where, raw))
    return _sources(lines)


def read_bundle_lines(lines: Iterable[dict[str, Any]], name: str = "bundle") -> list[Source]:
    """Validate bundle lines already in memory (benchmark pool, tests)."""
    return _sources([(f"{name}:{n}", raw) for n, raw in enumerate(lines, start=1)])


def _sources(lines: list[tuple[str, Any]]) -> list[Source]:
    sources: list[Source] = []
    seen: set[str] = set()
    for where, raw in lines:
        if not isinstance(raw, dict):
            raise ValidationFailed(f"{where}: a source line must be a JSON object")
        version = (raw.get("output") or {}).get("output_format_version")
        if version != SPAN_FORMAT_VERSION:
            raise ValidationFailed(f"{where}: output format {version!r} is not {SPAN_FORMAT_VERSION}")
        _raise_first(_validator(INPUT_SCHEMA), raw, where)
        _raise_first(_validator(SPAN_SCHEMA), raw["output"], f"{where} (output)")
        if raw["source_id"] in seen:
            raise ValidationFailed(f"{where}: duplicate source_id {raw['source_id']!r}")
        seen.add(raw["source_id"])
        sources.append(Source(raw["source_id"], raw["source_class"], raw.get("date"),
                              raw.get("origin"), raw.get("text_sha256"), raw["output"]))
    return sources


def read_bundles(paths: Iterable[Path | str]) -> list[Source]:
    sources: list[Source] = []
    seen: set[str] = set()
    for path in paths:
        for source in read_bundle(path):
            if source.source_id in seen:
                raise ValidationFailed(f"{path}: source_id {source.source_id!r} is in two bundles")
            seen.add(source.source_id)
            sources.append(source)
    return sources


def _raise_first(validator: Draft202012Validator, data: Any, where: str) -> None:
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    if errors:
        loc = "/".join(str(p) for p in errors[0].absolute_path) or "(root)"
        raise ValidationFailed(f"{where}: {loc}: {errors[0].message}")


def independence_keys(sources: Iterable[Source]) -> dict[str, tuple[str, bool]]:
    """source_id -> (independence key, key comes from an origin). Sources with the same text hash
    share the key of the first of them in source_id order (research R3)."""
    by_hash: dict[str, tuple[str, bool]] = {}
    keys: dict[str, tuple[str, bool]] = {}
    for source in sorted(sources, key=lambda s: s.source_id):
        own = (source.origin, True) if source.origin else (source.source_id, False)
        if source.text_sha256:
            own = by_hash.setdefault(source.text_sha256, own)
        keys[source.source_id] = own
    return keys


def items_from(sources: Iterable[Source]) -> list[Item]:
    """All items of all sources, sorted by item id."""
    sources = list(sources)
    keys = independence_keys(sources)
    items: dict[str, Item] = {}
    for source in sources:
        dimensions = source.output.get("dimensions", [])
        key, origin_based = keys[source.source_id]
        for raw in source.output["items"]:
            iid = item_id(source.source_id, raw["start"], raw["end"], raw["kind"])
            if iid in items:
                raise ValidationFailed(f"{source.source_id}: two items share span "
                                       f"{raw['start']}-{raw['end']} and kind {raw['kind']}")
            items[iid] = Item(
                item_id=iid, source_id=source.source_id, start=raw["start"], end=raw["end"],
                kind=raw["kind"], quote=raw["quote"], score=raw["score"], date=source.date,
                independence_key=key, origin_based=origin_based,
                exact_copy_key=exact_copy_key(raw["kind"], raw["quote"]),
                attributes={d: raw[d] for d in ATTRIBUTES if d in dimensions and d in raw},
            )
    return [items[k] for k in sorted(items)]
