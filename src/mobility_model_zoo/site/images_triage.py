"""Rounds of the image library (feature 019, contracts/cli.md): building a record from a
generator manifest entry (shared by `add` and `pick`), the triage of a round (I4, I6, I7, bytes;
`triage.json` and the contact sheet), the import of the owner's picks (`next.txt`) and the local
pool overview. Everything that decodes images goes through `images_process` and therefore needs
the `images` extra; `write_overview` does not.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any

import jinja2
import jsonschema

from mobility_model_zoo.release.errors import GateFailed, UsageError
from mobility_model_zoo.release.registry import Registry, dump_yaml, load_yaml
from mobility_model_zoo.site import images

PACKAGE = "mobility_model_zoo.site"
TRIAGE_FILE, SHEET_FILE, PICKS_FILE, NEXT_FILE, THUMBS = (
    "triage.json",
    "sheet.html",
    "picks.yaml",
    "next.txt",
    "thumbs",
)
CHECK_ORDER = ("faces", "text", "style", "duplicate", "bytes")


def _env() -> jinja2.Environment:
    return jinja2.Environment(
        loader=jinja2.PackageLoader(PACKAGE, "templates"), autoescape=True, trim_blocks=True
    )


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validator() -> jsonschema.Draft202012Validator:
    return jsonschema.Draft202012Validator(
        images.schema(), format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER
    )


def record_hashes(records: list[dict[str, Any]]) -> dict[str, str]:
    """id → stored pHash of every record that has one (the I7 reference set)."""
    out = {}
    for r in records:
        h = ((r.get("checks") or {}).get("measures") or {}).get("phash")
        if h:
            out[r["id"]] = h
    return out


# ---- one record from a manifest entry -----------------------------------------------------------
def candidate_checks(
    png: Path,
    series: dict[str, Any],
    others: dict[str, str],
    say=lambda _m: None,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """I4 faces, I4 text, I6 style and I7 duplicate on one PNG, in that order, stopping at the
    first failure. Returns (reasons, measures); measures always hold the pHash."""
    from mobility_model_zoo.site import images_process as proc

    measures: dict[str, Any] = {"phash": proc.phash_hex(png)}
    say("checking faces …")
    f = proc.faces(png)
    measures["faces_below_threshold"] = f["below_threshold"]
    if not f["pass"]:
        return [{"check": "I4 faces", "detail": f"{len(f['hits'])} face(s) {f['hits']}"}], measures
    say("checking text …")
    t = proc.text(png)
    if not t["pass"]:
        words = [x["text"] for x in t["tokens"]]
        return [{"check": "I4 text", "detail": f"readable text {words}"}], measures
    if series.get("palette"):
        st = proc.style(png, series["palette"])
        measures.update(st["measures"])
        if not st["pass"]:
            return [{"check": "I6 style", "detail": "; ".join(st["reasons"])}], measures
    twin = proc.duplicate_of(measures["phash"], others, int(series.get("duplicate_max_bits", 10)))
    if twin:
        return [{"check": "I7 duplicate", "detail": f"twin of {twin[0]} ({twin[1]} bits)"}], measures
    return [], measures


def build_record(
    reg: Registry,
    entry: dict[str, Any],
    png: Path,
    *,
    theme: str,
    subject: str,
    placements: list[str],
    scene: str,
    alt: str,
    record_id: str,
    focal: tuple[float, float] | None = None,
    series_name: str = "",
    hardware: str = "",
    image_digest: str = "",
    round_no: int | None = None,
    others: dict[str, str] | None = None,
    say=lambda _m: None,
) -> tuple[dict[str, Any], dict[int, bytes]]:
    """The validated record and its derivatives for one generator output. Raises GateFailed with
    every failed check; writes nothing."""
    from mobility_model_zoo.site import images_process as proc

    series_name = series_name or entry.get("series") or ""
    series = images.load_series(reg, series_name)
    if series is None:
        raise GateFailed([f"I2 series {series_name} has no file under {images.SERIES_DIR}"])
    model = next((m for m in series["models"].values() if m["id"] == entry["model"]), None)
    if model is None:
        raise GateFailed([f"I2 model {entry['model']} is not in series {series_name}"])
    generator = entry.get("generator") or {}
    rid = record_id
    reasons, measures = candidate_checks(png, series, others or {}, say)
    failures = [f"{r['check']} {rid}: {r['detail']}" for r in reasons]
    if focal is None:
        focal = tuple(measures.get("accent_centroid") or (0.5, 0.5))  # type: ignore[assignment]
    aspect = entry.get("aspect") or ("16:9" if "start-hero" in placements else "3:2")
    say("encoding derivatives …")
    try:
        ders = proc.derivatives(png, aspect, focal, entry["model"], series_name)
    except UsageError as e:
        failures.append(f"I1 {rid}: {e}")
        ders = {}
    if failures:
        raise GateFailed(failures)
    below = measures.pop("faces_below_threshold", 0)
    rec: dict[str, Any] = {
        "id": rid,
        "series": series_name,
        "theme": theme,
        "subject": subject,
        "generation": {
            "model": entry["model"],
            "revision": entry["revision"],
            "model_licence": entry.get("model_licence") or model["licence"],
            "model_card": entry.get("model_card") or model["card"],
            "pipeline": entry.get("pipeline") or model["pipeline"],
            "prompt": entry["prompt"],
            "negative_prompt": entry.get(
                "negative_prompt", series["negative"] if "true_cfg_scale" in model else ""
            ),
            "seed": entry["seed"],
            "steps": entry["steps"],
            "guidance": float(entry["guidance"]),
            "width": entry["width"],
            "height": entry["height"],
            "generated": entry.get("generated")
            or dt.date.fromtimestamp(png.stat().st_mtime).isoformat(),
            "hardware": hardware or entry.get("hardware") or "dgx-spark",
            "generator": {
                "commit": generator.get("commit")
                if generator.get("commit", "unknown") != "unknown"
                else "unversioned",
                "image_digest": image_digest or generator.get("image_digest") or "",
            },
        },
        "licence": "CC0-1.0",
        "placements": list(placements),
        "scene": scene.strip(),
        "alt": f"{alt.strip().rstrip('.')} {images.ALT_SUFFIX}",
        "focal_point": [round(float(focal[0]), 3), round(float(focal[1]), 3)],
        "aspect": aspect,
        "source": {
            "width": entry["width"],
            "height": entry["height"],
            "sha256": images.sha256(png),
        },
        "derivatives": {
            str(w): {"file": f"{rid}-{w}.webp", "bytes": len(data), "sha256": _hash(data)}
            for w, data in ders.items()
        },
        "checks": {
            "tools": proc.tool_versions(),
            "ran": dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat(),
            "faces": "pass",
            "faces_below_threshold": below,
            "text": "pass",
            "bytes": "pass",
            "style": "pass",
            "duplicate": "pass",
            "measures": measures,
        },
    }
    if round_no is not None:
        rec["round"] = round_no
    errors = [
        f"I1 {rid}: {'/'.join(str(p) for p in e.absolute_path) or '(root)'}: {e.message}"
        for e in _validator().iter_errors(rec)
    ]
    if errors:
        raise GateFailed(errors)
    topics = {x["id"] for x in reg.topics()}
    for pl in rec["placements"]:
        kind, _, name = pl.partition(":")
        if kind == "topic" and name not in topics:
            raise GateFailed([f"I1 {rid}: unknown topic {name}"])
    return rec, ders


def write_record(reg: Registry, rec: dict[str, Any], ders: dict[int, bytes], png: Path | None) -> Path:
    """Write the record directory; `png` copies the source in (016 style), None omits it."""
    target = images.records_dir(reg) / rec["id"]
    if target.exists():
        raise GateFailed([f"{target} exists; remove it first"])
    target.mkdir(parents=True)
    if png is not None:
        rec["source"]["file"] = f"{rec['id']}.png"
        shutil.copyfile(png, target / rec["source"]["file"])
    for w, data in ders.items():
        (target / rec["derivatives"][str(w)]["file"]).write_bytes(data)
    (target / "image.yaml").write_text(dump_yaml(rec), encoding="utf-8")
    return target


# ---- triage of a round --------------------------------------------------------------------------
def _manifest(round_dir: Path) -> dict[str, Any]:
    path = round_dir / "manifest.json"
    if not path.exists():
        raise UsageError(f"{path} is missing")
    return json.loads(path.read_text(encoding="utf-8"))


def triage_round(reg: Registry, round_dir: Path, round_no: int, say=lambda _m: None) -> dict[str, Any]:
    """Run the automated rejection over a round and write `triage.json` and the thumbnails.
    Candidates are taken in manifest order; the first failing check names the reason."""
    from mobility_model_zoo.site import images_process as proc

    manifest = _manifest(round_dir)
    series = images.load_series(reg, manifest["series"])
    if series is None:
        raise GateFailed([f"I2 series {manifest['series']} has no file under {images.SERIES_DIR}"])
    records, _ = images.load_records(reg)
    others = record_hashes(records)
    thumbs = round_dir / THUMBS
    thumbs.mkdir(exist_ok=True)
    numbers: dict[str, int] = {}
    candidates = []
    rejected_per_check: dict[str, int] = {}
    for entry in manifest["images"]:
        png = round_dir / entry["file"]
        key = f"{entry['theme']}/{entry['subject']}"
        cand: dict[str, Any] = {
            "file": entry["file"],
            "theme": entry["theme"],
            "subject": entry["subject"],
            "seed": entry["seed"],
            "number": None,
            "outcome": "rejected",
            "reasons": [],
            "measures": {},
            "phash": None,
            "focal_default": None,
        }
        candidates.append(cand)
        if not png.exists():
            cand["reasons"] = [{"check": "file", "detail": "PNG missing"}]
            rejected_per_check["file"] = rejected_per_check.get("file", 0) + 1
            continue
        say(f"{entry['file']}")
        reasons, measures = candidate_checks(png, series, others, say)
        cand["phash"] = measures.get("phash")
        cand["measures"] = {k: v for k, v in measures.items() if k != "phash"}
        cand["focal_default"] = measures.get("accent_centroid")
        if not reasons:
            focal = tuple(measures.get("accent_centroid") or (0.5, 0.5))
            aspect = entry.get("aspect") or "3:2"
            try:
                ders = proc.derivatives(png, aspect, focal, entry["model"], manifest["series"])
                for w, data in ders.items():
                    (thumbs / f"{Path(entry['file']).stem}-{w}.webp").write_bytes(data)
            except UsageError as e:
                reasons = [{"check": "I1 bytes", "detail": str(e)}]
        if reasons:
            cand["reasons"] = reasons
            check = reasons[0]["check"]
            rejected_per_check[check] = rejected_per_check.get(check, 0) + 1
            continue
        numbers[key] = numbers.get(key, 0) + 1
        cand["number"] = numbers[key]
        cand["outcome"] = "shown"
        others[f"{key}#{cand['number']}"] = cand["phash"]
    subjects_in_round = sorted({f"{c['theme']}/{c['subject']}" for c in candidates})
    missing = [k for k in subjects_in_round if k not in numbers]
    triage = {
        "round": round_no,
        "series": manifest["series"],
        "model": manifest.get("model"),
        "container": (manifest["images"][0].get("generator") or {}).get("image_digest")
        if manifest["images"]
        else None,
        "generator": (manifest["images"][0].get("generator") or {}).get("commit")
        if manifest["images"]
        else None,
        "tools": proc.tool_versions(),
        "ran": dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat(),
        "summary": {
            "candidates": len(candidates),
            "shown": sum(1 for c in candidates if c["outcome"] == "shown"),
            "rejected": rejected_per_check,
            "subjects": len(subjects_in_round),
            "subjects_without_candidate": missing,
        },
        "candidates": candidates,
    }
    (round_dir / TRIAGE_FILE).write_text(
        json.dumps(triage, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    write_sheet(round_dir, triage, series, taken_subjects(records))
    return triage


def _grouped(
    triage: dict[str, Any], series: dict[str, Any], taken: dict[str, str] | None = None
) -> list[dict[str, Any]]:
    """Themes in THEMES order → subjects in series order → candidates, for the sheet."""
    subs = images.subjects(series)
    by_key: dict[str, list[dict[str, Any]]] = {}
    for c in triage["candidates"]:
        by_key.setdefault(f"{c['theme']}/{c['subject']}", []).append(c)
    order = [k for k in subs if k in by_key] + sorted(k for k in by_key if k not in subs)
    order.sort(key=lambda k: k in (taken or {}))  # subjects already in the pool go last
    themes: dict[str, list[dict[str, Any]]] = {}
    for key in order:
        theme = key.split("/", 1)[0]
        cands = by_key[key]
        themes.setdefault(theme, []).append(
            {
                "key": key,
                "prompt": subs.get(key, {}).get("prompt", ""),
                "shown": [c for c in cands if c["outcome"] == "shown"],
                "rejected": [c for c in cands if c["outcome"] != "shown"],
            }
        )
    ordered = [t for t in images.THEMES if t in themes] + sorted(
        t for t in themes if t not in images.THEMES
    )
    return [{"id": t, "subjects": themes[t]} for t in ordered]


def taken_subjects(records: list[dict[str, Any]]) -> dict[str, str]:
    """`theme/subject` → record id for subjects already in the pool (shown as skipped on the sheet)."""
    return {f"{r.get('theme')}/{r.get('subject')}": r["id"] for r in records}


def write_sheet(
    round_dir: Path,
    triage: dict[str, Any],
    series: dict[str, Any],
    taken: dict[str, str] | None = None,
) -> Path:
    """The contact sheet: a local page whose only script keeps the owner's clicks in the
    browser and hands back `picks.yaml` as a download (nothing is deployed, nothing is sent)."""
    html = (
        _env()
        .get_template("local/sheet.html.j2")
        .render(
            triage=triage,
            themes=_grouped(triage, series, taken),
            thumbs=THUMBS,
            stem=lambda f: Path(f).stem,
            taken=taken or {},
        )
    )
    out = round_dir / SHEET_FILE
    out.write_text(html, encoding="utf-8")
    return out


# ---- picks --------------------------------------------------------------------------------------
def _pick_id(reg: Registry, theme: str, subject: str, taken: set[str]) -> str:
    base = f"{theme}-{subject}"[:40].rstrip("-")
    rid, n = base, 2
    while rid in taken or (images.records_dir(reg) / rid).exists():
        suffix = f"-{n}"
        rid, n = base[: 40 - len(suffix)].rstrip("-") + suffix, n + 1
    return rid


def pick_round(
    reg: Registry,
    round_dir: Path,
    picks: dict[str, Any],
    dry_run: bool = False,
    say=lambda _m: None,
) -> list[Path]:
    """Import the owner's picks of a round atomically; write `next.txt`. `picks` is the parsed
    picks.yaml: {round, picks: {"theme/subject": number | "none" | {number, focal?, id?}}}."""
    triage_path = round_dir / TRIAGE_FILE
    if not triage_path.exists():
        raise UsageError(f"{triage_path} is missing; run triage first")
    triage = json.loads(triage_path.read_text(encoding="utf-8"))
    manifest = _manifest(round_dir)
    entries = {e["file"]: e for e in manifest["images"]}
    shown = {
        (f"{c['theme']}/{c['subject']}", c["number"]): c
        for c in triage["candidates"]
        if c["outcome"] == "shown"
    }
    series = images.load_series(reg, manifest["series"])
    if series is None:
        raise GateFailed([f"I2 series {manifest['series']} has no file under {images.SERIES_DIR}"])
    subs = images.subjects(series)
    records, _ = images.load_records(reg)
    others = record_hashes(records)
    round_no = int(picks.get("round") or triage.get("round") or 0) or None
    todo, nones, usage = [], [], []
    for key, choice in (picks.get("picks") or {}).items():
        if key not in subs:
            usage.append(f"{key}: not a subject of series {manifest['series']}")
            continue
        number, focal, rid = choice, None, ""
        if isinstance(choice, dict):
            number, focal, rid = choice.get("number"), choice.get("focal"), choice.get("id", "")
        if number in (None, "none", "None"):
            nones.append(key)
            continue
        cand = shown.get((key, int(number)))
        if cand is None:
            usage.append(f"{key}: #{number} is not a shown candidate of round {triage['round']}")
            continue
        todo.append((key, cand, focal, rid))
    if usage:
        raise UsageError("; ".join(usage))
    built, taken, failures = [], set(), []
    for key, cand, focal, rid in todo:
        theme, subject = key.split("/", 1)
        rid = rid or _pick_id(reg, theme, subject, taken)
        taken.add(rid)
        sub = subs[key]
        try:
            rec, ders = build_record(
                reg,
                entries[cand["file"]],
                round_dir / cand["file"],
                theme=theme,
                subject=subject,
                placements=[],
                scene=sub["scene"],
                alt=sub["alt"],
                record_id=rid,
                focal=tuple(focal) if focal else None,
                series_name=manifest["series"],
                round_no=round_no,
                others=others,
                say=say,
            )
        except GateFailed as e:
            failures.extend(e.failures)
            continue
        others[rid] = rec["checks"]["measures"]["phash"]
        built.append((rec, ders))
        say(f"{key} #{cand['number']} → {rid}")
    if failures:
        raise GateFailed(failures)
    missing = triage["summary"].get("subjects_without_candidate", [])
    next_keys = sorted(set(nones) | set(missing))
    if dry_run:
        say(f"dry run: {len(built)} pick(s) pass; next round: {', '.join(next_keys) or 'none'}")
        return []
    written = [write_record(reg, rec, ders, None) for rec, ders in built]
    (round_dir / NEXT_FILE).write_text("".join(f"{k}\n" for k in next_keys), encoding="utf-8")
    return written


# ---- pool overview ------------------------------------------------------------------------------
def write_overview(reg: Registry, out: Path) -> Path:
    """The local pool page (data-model.md "Pool overview"); relative links into the records."""
    records, _ = images.load_records(reg)
    cov = images.coverage(records)
    base = Path(os.path.relpath(images.records_dir(reg), out.parent))
    themes = []
    for t in images.THEMES:
        recs = sorted((r for r in records if r.get("theme") == t), key=lambda r: r["id"])
        themes.append(
            {
                "id": t,
                "count": cov[t]["count"],
                "minimum": cov[t]["minimum"],
                "share": cov[t]["share"],
                "records": [
                    {
                        "id": r["id"],
                        "subject": r.get("subject"),
                        "aspect": r.get("aspect"),
                        "placements": r.get("placements", []),
                        "round": r.get("round"),
                        "scene": r.get("scene", ""),
                        "thumb": (base / r["id"] / r["derivatives"]["480"]["file"]).as_posix(),
                        "full": (base / r["id"] / r["derivatives"]["1600"]["file"]).as_posix(),
                    }
                    for r in recs
                ],
            }
        )
    html = (
        _env()
        .get_template("local/pool.html.j2")
        .render(themes=themes, total=len(records), minimum=images.LIBRARY_MIN, cap=images.THEME_CAP)
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out


def load_picks(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise UsageError(f"{path} is missing")
    return load_yaml(path) or {}
