"""`zoo site images`: import, check, list, remove, and the rounds of the library (features 016
and 019, contracts/cli.md).

`add` turns one generator output into a record directory `zoo/site/images/<id>/` with three WebP
derivatives (and, unless `--no-source`, the source PNG) after the recipe, face, text, style,
duplicate and byte checks pass; nothing is written on failure. `triage` runs the same checks over
a round and writes the contact sheet; `pick` imports the owner's picks; `overview` writes the
local pool page. `check` validates the records (I1, I2, I7, I8, L1, coverage); `--deep` re-runs
the detectors (I4); `--regenerate` re-renders on a GPU machine and compares perceptual hashes (I5).
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

import typer

from mobility_model_zoo.release.errors import GateFailed, UsageError
from mobility_model_zoo.site import images

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Website images: add, check, list, remove, triage, pick, overview.",
)


def say(message: str) -> None:
    print(message, file=sys.stderr)


def _run(fn) -> None:
    from mobility_model_zoo.release.cli import _run as run

    run(fn)


def _reg():
    from mobility_model_zoo.release.cli import _registry

    return _registry()


def _manifest_entry(manifest: Path, png: Path) -> dict[str, Any]:
    data = json.loads(manifest.read_text(encoding="utf-8"))
    for im in data.get("images", []):
        if im["file"] == png.name:
            return im
    raise UsageError(f"{png.name} is not in {manifest}")


def _default_id(placements: list[str], theme: str, subject: str, seed: int) -> str:
    base = placements[0].replace(":", "-") if placements else f"{theme}-{subject}"
    return f"{base}-{seed}"[:40].rstrip("-")


@app.command("add")
def add_cmd(
    png: Path = typer.Argument(..., help="The source PNG the generator wrote."),
    manifest: Path = typer.Option(..., "--manifest", help="The generator's manifest.json."),
    theme: str = typer.Option("", "--theme", help="Theme id (default: the manifest entry's)."),
    subject: str = typer.Option("", "--subject", help="Subject id (default: the manifest entry's)."),
    placement: list[str] = typer.Option(
        [], "--placement", help="start-hero, topic:<id> or model:<name>; may be omitted (pool)."
    ),
    focal: str = typer.Option(
        "", "--focal", help="X,Y fractions that stay visible in every crop (default: I6 centroid)."
    ),
    scene: str = typer.Option("", "--scene", help="One line for the credits page (default: series)."),
    alt: str = typer.Option("", "--alt", help="One sentence (default: series); suffix is appended."),
    record_id: str = typer.Option("", "--id", help="Record id (default: from placement and seed)."),
    series: str = typer.Option("", "--series", help="Series name (default: the manifest's)."),
    hardware: str = typer.Option(
        "", "--hardware", help="dgx-spark or dev-machine (default: the manifest's)."
    ),
    image_digest: str = typer.Option(
        "", "--image-digest", help="Container image digest sha256:… (default: the manifest's)."
    ),
    no_source: bool = typer.Option(
        False, "--no-source", help="Do not copy the PNG into the record (library records)."
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run every check, write nothing."),
) -> None:
    """Import one generated image as a record with three WebP derivatives."""

    def fn() -> None:
        from mobility_model_zoo.site import images_triage as rounds

        reg = _reg()
        entry = _manifest_entry(manifest, png)
        series_name = series or entry.get("series") or json.loads(manifest.read_text())["series"]
        spec = images.load_series(reg, series_name)
        if spec is None:
            raise GateFailed([f"I2 series {series_name} has no file under {images.SERIES_DIR}"])
        t, s = theme or entry.get("theme", ""), subject or entry.get("subject", "")
        sub = images.subjects(spec).get(f"{t}/{s}", {})
        if not (scene or sub.get("scene")) or not (alt or sub.get("alt")):
            raise GateFailed([f"I8 {t}/{s}: no scene and alt in the series; pass --scene and --alt"])
        fx_fy = tuple(float(v) for v in focal.split(",")) if focal else None
        rid = record_id or _default_id(placement, t, s, entry["seed"])
        records, _ = images.load_records(reg)
        rec, ders = rounds.build_record(
            reg,
            entry,
            png,
            theme=t,
            subject=s,
            placements=list(placement),
            scene=scene or sub["scene"],
            alt=alt or sub["alt"],
            record_id=rid,
            focal=fx_fy,  # type: ignore[arg-type]
            series_name=series_name,
            hardware=hardware,
            image_digest=image_digest,
            others=rounds.record_hashes(records),
            say=say,
        )
        if dry_run:
            say(
                f"dry run: {rid} passes every check "
                f"(faces, text, style, duplicate, bytes {[len(d) for d in ders.values()]})"
            )
            return
        target = rounds.write_record(reg, rec, ders, None if no_source else png)
        say(
            f"wrote {target.relative_to(reg.root)} "
            f"({', '.join(f'{w}:{len(d)}' for w, d in ders.items())} bytes)"
        )

    _run(fn)


def _source_for(reg, rec: dict[str, Any]) -> tuple[Path, str]:
    """The file the deep checks run on: the source next to the record, the cached source, else
    the 1600 px derivative scaled back to the source's pixel size, so the detectors see the same
    scale the import saw (feature 019, research R1; a 1600 px upscale of a 1200 px source would
    otherwise push silhouettes and trace marks over the face and text thresholds)."""
    d = rec["_dir"]
    if "file" in rec["source"] and (d / rec["source"]["file"]).exists():
        return d / rec["source"]["file"], "source"
    cached = reg.root / images.SOURCES_CACHE / f"{rec['id']}.png"
    if cached.exists():
        return cached, "cached source"
    return _at_source_scale(reg, rec), "1600 px derivative at source scale"


def _at_source_scale(reg, rec: dict[str, Any]) -> Path:
    """The 1600 px derivative resized by source_width / 1600 into `.cache/site/deep/<id>.png`."""
    from PIL import Image

    der = rec["_dir"] / rec["derivatives"]["1600"]["file"]
    out = reg.root / ".cache" / "site" / "deep" / f"{rec['id']}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and out.stat().st_mtime >= der.stat().st_mtime:
        return out
    with Image.open(der) as img:
        scale = rec["source"]["width"] / img.width
        size = (round(img.width * scale), round(img.height * scale))
        img.convert("RGB").resize(size, Image.Resampling.LANCZOS).save(out)
    return out


@app.command("check")
def check_cmd(
    deep: bool = typer.Option(
        False, "--deep", help="Re-run the face and text detectors on the sources (I4)."
    ),
    regenerate: bool = typer.Option(
        False, "--regenerate", help="Re-render each record and compare perceptual hashes (I5)."
    ),
    require_coverage: bool = typer.Option(
        False, "--require-coverage", help="Fail when the coverage table is not met (L2)."
    ),
    only: str = typer.Option("", "--only", help="Comma-separated record ids for --deep/--regenerate."),
) -> None:
    """Validate every image record (I1, I2, I7, I8, L1); --deep and --regenerate need the extra."""

    def fn() -> None:
        reg = _reg()
        records, findings = images.load_records(reg)
        findings += images.series_findings(reg, records)
        findings += images.library_findings(reg, records)
        chosen = {x.strip() for x in only.split(",") if x.strip()}
        if deep or regenerate:
            from mobility_model_zoo.site import images_process as proc

            for rec in records:
                if chosen and rec["id"] not in chosen:
                    continue
                src, kind = _source_for(reg, rec)
                if deep:
                    f, t = proc.faces(src), proc.text(src)
                    hits = []
                    if not f["pass"]:
                        hits.append(f"I4 {rec['id']}: {len(f['hits'])} face(s) {f['hits']}")
                    if not t["pass"]:
                        hits.append(f"I4 {rec['id']}: readable text {[x['text'] for x in t['tokens']]}")
                    # A lossy derivative is not the picture the import checked: its detector
                    # output is reported, the record's own checks stay the enforced evidence.
                    if kind.startswith("1600 px derivative"):
                        for h in hits:
                            say(f"note: {h} (on the derivative; the import checked the source)")
                    else:
                        findings += hits
                    say(
                        f"I4 {rec['id']} ({kind}): faces {'pass' if f['pass'] else 'FAIL'}, "
                        f"text {'pass' if t['pass'] else 'FAIL'}"
                    )
                if regenerate:
                    findings += _regenerate(rec, src, proc)
        for theme, c in images.coverage(records).items():
            say(f"coverage {theme}: {c['count']} of minimum {c['minimum']} ({c['share']:.0%})")
        l2 = images.coverage_findings(records)
        if require_coverage:
            findings += l2
        else:
            for line in l2:
                say(f"note: {line}")
        for line in findings:
            say(line)
        if findings:
            raise GateFailed(findings)
        say(f"{len(records)} image record(s) pass")

    _run(fn)


def _regenerate(rec: dict[str, Any], src: Path, proc: Any) -> list[str]:
    """I5: render the record's recipe again and compare by pHash; reported, not required."""
    import tempfile

    try:
        import diffusers  # noqa: F401
        import torch
    except ImportError:
        say(f"I5 {rec['id']}: skipped, no GPU toolchain here (needs the zoo-flux container)")
        return []
    g = rec["generation"]
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts" / "imagery"))
    from gen import build_pipeline  # type: ignore

    pipe, revision = build_pipeline({"id": g["model"], "pipeline": g["pipeline"]})
    kw = dict(
        prompt=g["prompt"],
        num_inference_steps=g["steps"],
        width=g["width"],
        height=g["height"],
        generator=torch.Generator("cuda").manual_seed(g["seed"]),
    )
    if g["negative_prompt"]:
        kw.update(true_cfg_scale=g["guidance"], negative_prompt=g["negative_prompt"])
    else:
        kw["guidance_scale"] = g["guidance"]
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "regen.png"
        pipe(**kw).images[0].save(out)
        identical = images.sha256(out) == rec["source"]["sha256"]
        dist = proc.phash_distance(proc.phash(out), proc.phash(src))
    say(
        f"I5 {rec['id']}: revision {revision}, pHash distance {dist}, "
        f"{'bit-identical' if identical else 'not bit-identical'}"
    )
    return (
        []
        if dist <= proc.PHASH_MAX_BITS
        else [f"I5 {rec['id']}: pHash distance {dist}, more than {proc.PHASH_MAX_BITS}"]
    )


@app.command("list")
def list_cmd(
    theme: str = typer.Option("", "--theme", help="Only records of this theme."),
) -> None:
    """One line per image: id, theme/subject, placements, model, date, bytes of the 960 px file."""

    def fn() -> None:
        records, _ = images.load_records(_reg())
        records = [r for r in records if not theme or r.get("theme") == theme]
        if not records:
            print("no image records")
        for r in records:
            g = r.get("generation", {})
            placements = ",".join(r.get("placements", [])) or "-"
            size = r.get("derivatives", {}).get("960", {}).get("bytes", "?")
            key = f"{r.get('theme', '?')}/{r.get('subject', '?')}"
            print(
                f"{r['id']:<34} {key:<34} {placements:<28} "
                f"{g.get('model', '?')} {g.get('generated', '?')} {size} B"
            )

    _run(fn)


@app.command("remove")
def remove_cmd(record_id: str = typer.Argument(..., help="The record id (directory name).")) -> None:
    """Delete an image record directory; the affected placements fall back on the next build."""

    def fn() -> None:
        reg = _reg()
        target = images.records_dir(reg) / record_id
        if not (target / "image.yaml").exists():
            raise UsageError(f"{record_id}: no record under {images.IMAGES_DIR}")
        from mobility_model_zoo.release.registry import load_yaml

        placements = (load_yaml(target / "image.yaml") or {}).get("placements", [])
        shutil.rmtree(target)
        say(f"removed {record_id}; placements that now fall back: {', '.join(placements) or 'none'}")

    _run(fn)


@app.command("triage")
def triage_cmd(
    round_dir: Path = typer.Argument(..., help="A round copied from the Spark (PNGs + manifest)."),
    round_no: int = typer.Option(0, "--round", help="Round number (default: from the directory name)."),
) -> None:
    """Reject failing candidates (I4, I6, I7, bytes) and write triage.json and sheet.html."""

    def fn() -> None:
        from mobility_model_zoo.site import images_triage as rounds

        n = round_no or (int(round_dir.name) if round_dir.name.isdigit() else 0)
        triage = rounds.triage_round(_reg(), round_dir, n, say)
        s = triage["summary"]
        rejected = ", ".join(f"{k} {v}" for k, v in s["rejected"].items()) or "none"
        say(
            f"round {n}: {s['candidates']} candidates, {s['shown']} shown, rejected: {rejected}; "
            f"{len(s['subjects_without_candidate'])} subject(s) without a shown candidate"
        )
        for key in s["subjects_without_candidate"]:
            say(f"  needs another round: {key}")
        say(f"sheet: {round_dir / rounds.SHEET_FILE}")

    _run(fn)


@app.command("pick")
def pick_cmd(
    round_dir: Path = typer.Argument(..., help="The triaged round directory."),
    picks: Path = typer.Option(None, "--picks", help="picks.yaml (default: <round-dir>/picks.yaml)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run every check, write nothing."),
) -> None:
    """Import the owner's picks of a round as pool records; write next.txt."""

    def fn() -> None:
        from mobility_model_zoo.site import images_triage as rounds

        reg = _reg()
        data = rounds.load_picks(picks or round_dir / rounds.PICKS_FILE)
        written = rounds.pick_round(reg, round_dir, data, dry_run, say)
        for p in written:
            say(f"wrote {p.relative_to(reg.root)}")
        if written:
            say(f"next round: {round_dir / rounds.NEXT_FILE}")

    _run(fn)


@app.command("overview")
def overview_cmd(
    out: Path = typer.Option(None, "--out", help="Output file (default: .cache/site/pool.html)."),
) -> None:
    """Write the local pool overview page, grouped by theme."""

    def fn() -> None:
        from mobility_model_zoo.site import images_triage as rounds

        reg = _reg()
        path = rounds.write_overview(reg, out or reg.root / ".cache" / "site" / "pool.html")
        print(path)

    _run(fn)
