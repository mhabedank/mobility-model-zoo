"""Coverage report (FR-026, SC-004) and language report (FR-027, research R9)."""

from __future__ import annotations

import datetime as dt
from collections import Counter, defaultdict
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from mobility_model_zoo.catalog.model import VOCAB_DIR, Catalog, vocab
from mobility_model_zoo.catalog.query import permitted_use

MODALITIES = ("text", "audio", "video", "image", "graphic", "structured_data")
USABLE = ("cleared", "fetched")
DERIVED = ("machine_translated", "ai_generated")
UNITS = ("items", "hours", "bytes")


def _usable(entry: dict[str, Any]) -> bool:
    return (entry.get("status") or {}).get("value") in USABLE or permitted_use(
        entry
    ) == "training_allowed"


def _volume(entries: list[dict[str, Any]]) -> dict[str, float]:
    total: dict[str, float] = {}
    for e in entries:
        for unit in UNITS:
            value = ((e.get("content") or {}).get("volume") or {}).get(unit)
            if value is not None:
                total[unit] = total.get(unit, 0) + value
    return total


def _active(cat: Catalog) -> list[dict[str, Any]]:
    gone = ("rejected", "retired", "withdrawn")
    return [e for e in cat.entries.values() if (e.get("status") or {}).get("value") not in gone]


def coverage(cat: Catalog) -> dict[str, Any]:
    entries = _active(cat)
    by_cell: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    derived: dict[tuple[str, str], int] = Counter()
    for e in entries:
        modality = e["resource_type"]["modality"]
        for lang in e.get("languages") or []:
            if lang.get("origin") in DERIVED:
                derived[(lang["code"], lang["origin"])] += 1
            else:
                by_cell[(lang["code"], modality)].append(e)
    cells = [
        {
            "language": lang,
            "modality": mod,
            "entries": len(es),
            "usable": sum(_usable(e) for e in es),
            "volume": _volume(es),
        }
        for (lang, mod), es in sorted(by_cell.items())
    ]
    usable_langs = {c["language"] for c in cells if c["usable"]}
    usable_mods = {c["modality"] for c in cells if c["usable"]}
    determined = sum((e.get("licence") or {}).get("id") != "unknown" for e in entries)
    return {
        "date": dt.date.today().isoformat(),
        **cat.version(),
        "entries": len(entries),
        "by_language_modality": cells,
        "by_area": dict(sorted(Counter(str(e["origin_area"]) for e in entries).items())),
        "by_kind": dict(sorted(Counter(e["publisher"]["kind"] for e in entries).items())),
        "by_permitted_use": dict(sorted(Counter(permitted_use(e) for e in entries).items())),
        "by_status": dict(sorted(Counter(e["status"]["value"] for e in entries).items())),
        "licence_determined": {
            "entries": determined,
            "share": round(determined / len(entries), 4) if entries else 0.0,
        },
        "derived_languages": [
            {"language": lang, "origin": origin, "entries": n}
            for (lang, origin), n in sorted(derived.items())
        ],
        "gaps": {
            "languages": [code for code in vocab().targets if code not in usable_langs],
            "modalities": [m for m in MODALITIES if m not in usable_mods],
        },
    }


def _short(commit: str | None) -> str:
    return (commit or "uncommitted")[:12]


def _fmt_volume(volume: dict[str, float]) -> str:
    return ", ".join(f"{v:g} {unit}" for unit, v in volume.items()) or "-"


def render_coverage(rep: dict[str, Any]) -> str:
    lines = [
        f"# Coverage report {rep['date']}",
        "",
        f"Index `{_short(rep['catalog_commit'])}` · sha256 `{rep['catalog_sha256'][:12]}`"
        f" · vocab v{rep['vocab_version']} · {rep['entries']} active entries",
        "",
        "Usable = cleared or fetched, or permitted use training_allowed.",
        "",
        "## By language × modality",
        "",
        "| Language | Modality | Entries | Usable | Estimated volume |",
        "|---|---|---|---|---|",
    ]
    lines += [
        f"| {c['language']} | {c['modality']} | {c['entries']} | {c['usable']} "
        f"| {_fmt_volume(c['volume'])} |"
        for c in rep["by_language_modality"]
    ]
    for title, key in (
        ("By area", "by_area"),
        ("By kind of source", "by_kind"),
        ("By permitted use", "by_permitted_use"),
        ("By status", "by_status"),
    ):
        lines += ["", f"## {title}", "", "| Value | Entries |", "|---|---|"]
        lines += [f"| {k} | {v} |" for k, v in rep[key].items()]
    ld = rep["licence_determined"]
    lines += [
        "",
        "## Licence determined",
        "",
        f"{ld['entries']} of {rep['entries']} entries ({ld['share']:.1%}) have a licence other "
        "than `unknown` (SC-004 target: 80%).",
    ]
    lines += ["", "## Machine-translated and AI-generated", ""]
    if rep["derived_languages"]:
        lines += ["| Language | Origin | Entries |", "|---|---|---|"]
        lines += [
            f"| {d['language']} | {d['origin']} | {d['entries']} |" for d in rep["derived_languages"]
        ]
    else:
        lines.append("None.")
    gaps = rep["gaps"]
    lines += [
        "",
        "## Gaps",
        "",
        "Target languages without a usable entry: " + (", ".join(gaps["languages"]) or "none"),
        "",
        "Modalities without a usable entry: " + (", ".join(gaps["modalities"]) or "none"),
        "",
    ]
    return "\n".join(lines)


# ---- language report (R9) ---------------------------------------------------------------------


@cache
def base_models() -> dict[str, list[str]]:
    data = yaml.safe_load((VOCAB_DIR / "base-models.yaml").read_text(encoding="utf-8"))
    return {name: list(m["languages"]) for name, m in data["models"].items()}


def _base_covers(base: str | None, code: str) -> str:
    if not base:
        return "unknown"
    langs = base_models().get(base) or base_models().get(base.split("/")[-1])
    if langs is None:
        return "unknown"
    primary = code.split("-")[0]
    return "yes" if code in langs or primary in langs else "no"


def zoo_models(zoo_root: Path) -> list[dict[str, Any]]:
    out = []
    for path in sorted((zoo_root / "zoo" / "models").glob("*/model.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if data.get("languages") or data.get("base_model"):
            out.append({"name": path.parent.name, "base_model": data.get("base_model")})
    return out


def languages(cat: Catalog, zoo_root: Path) -> dict[str, Any]:
    entries = _active(cat)
    models = zoo_models(zoo_root)
    shares = {
        name: (m or {}).get("language_shares") or {}
        for name, m in (cat.config.get("models") or {}).items()
    }
    by_lang: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in entries:
        for lang in e.get("languages") or []:
            if lang["code"] not in ("zxx", "und"):
                by_lang[lang["code"]].append(e)
    rows = []
    for code in sorted(set(by_lang) | set(vocab().targets)):
        es = by_lang.get(code, [])
        rows.append(
            {
                "language": code,
                "target": code in vocab().targets,
                "entries": len(es),
                "cleared": sum((e.get("status") or {}).get("value") in USABLE for e in es),
                "volume": _volume(es),
                "models": {
                    m["name"]: {
                        "base_model": m["base_model"],
                        "base_covers": _base_covers(m["base_model"], code),
                        "training_share": float(shares.get(m["name"], {}).get(code, 0)),
                    }
                    for m in models
                },
            }
        )
    return {"date": dt.date.today().isoformat(), **cat.version(), "languages": rows}


def render_languages(rep: dict[str, Any]) -> str:
    names = sorted({n for row in rep["languages"] for n in row["models"]})
    head = (
        "| Language | Target | Entries | Cleared | Volume | "
        + " | ".join(f"{n}: base covers / training share" for n in names)
        + " |"
    )
    lines = [
        f"# Language report {rep['date']}",
        "",
        f"Index `{_short(rep['catalog_commit'])}` · sha256 `{rep['catalog_sha256'][:12]}`",
        "",
        head,
        "|" + "---|" * (5 + len(names)),
    ]
    for row in rep["languages"]:
        cells = [
            f"{row['models'][n]['base_covers']} / {row['models'][n]['training_share']:.0%}"
            for n in names
        ]
        lines.append(
            f"| {row['language']} | {'yes' if row['target'] else ''} | {row['entries']} "
            f"| {row['cleared']} | "
            f"{_fmt_volume(row['volume'])} | " + " | ".join(cells) + " |"
        )
    not_covered = [
        row["language"]
        for row in rep["languages"]
        if any(m["base_covers"] == "no" for m in row["models"].values())
    ]
    lines += [
        "",
        "Languages a current base model does not cover: " + (", ".join(not_covered) or "none"),
        "",
    ]
    return "\n".join(lines)
