"""`zoo site images`: import, check, list and remove website images (feature 016, contracts/cli.md).

`add` turns one generator output into a record directory `zoo/site/images/<id>/` with the source
PNG and three WebP derivatives, after the recipe, face, text and byte checks pass; nothing is
written on failure. `check` validates the records (I1, I2); `--deep` re-runs the detectors (I4);
`--regenerate` re-renders on a GPU machine and compares perceptual hashes (I5).
"""

from __future__ import annotations

import datetime as dt
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import typer

from mobility_model_zoo.release.errors import GateFailed, UsageError
from mobility_model_zoo.release.registry import dump_yaml
from mobility_model_zoo.site import images

app = typer.Typer(
    no_args_is_help=True, add_completion=False, help="Website images: add, check, list, remove."
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
    raise GateFailed([f"{png.name} is not in {manifest}"], exit_code=2)


def _default_id(placement: str, seed: int) -> str:
    base = placement.replace(":", "-")
    return f"{base}-{seed}"[:40]


@app.command("add")
def add_cmd(
    png: Path = typer.Argument(..., help="The source PNG the generator wrote."),
    manifest: Path = typer.Option(..., "--manifest", help="The generator's manifest.json."),
    placement: list[str] = typer.Option(
        ..., "--placement", help="start-hero, topic:<id> or model:<name>."
    ),
    focal: str = typer.Option(..., "--focal", help="X,Y fractions that stay visible in every crop."),
    scene: str = typer.Option(..., "--scene", help="One line for the credits page (20-120 characters)."),
    alt: str = typer.Option(..., "--alt", help="One sentence; '(AI-generated image)' is appended."),
    record_id: str = typer.Option("", "--id", help="Record id (default: from placement and seed)."),
    series: str = typer.Option("", "--series", help="Series name (default: the manifest's)."),
    hardware: str = typer.Option(
        "", "--hardware", help="dgx-spark or dev-machine (default: the manifest's)."
    ),
    image_digest: str = typer.Option(
        "", "--image-digest", help="Container image digest sha256:… (default: the manifest's)."
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run every check, write nothing."),
) -> None:
    """Import one generated image as a record with three WebP derivatives."""

    def fn() -> None:
        from mobility_model_zoo.site import images_process as proc

        reg = _reg()
        entry = _manifest_entry(manifest, png)
        series_name = series or entry.get("series") or json.loads(manifest.read_text())["series"]
        spec = images.load_series(reg, series_name)
        if spec is None:
            raise GateFailed([f"I2 series {series_name} has no file under {images.SERIES_DIR}"])
        model = next((m for m in spec["models"].values() if m["id"] == entry["model"]), None)
        if model is None:
            raise GateFailed([f"I2 model {entry['model']} is not in series {series_name}"])
        generator = entry.get("generator") or {}
        fx, fy = (float(v) for v in focal.split(","))
        aspect = "16:9" if "start-hero" in placement else "3:2"
        rid = record_id or _default_id(placement[0], entry["seed"])
        rec: dict[str, Any] = {
            "id": rid,
            "series": series_name,
            "generation": {
                "model": entry["model"],
                "revision": entry["revision"],
                "model_licence": entry.get("model_licence") or model["licence"],
                "model_card": entry.get("model_card") or model["card"],
                "pipeline": entry.get("pipeline") or model["pipeline"],
                "prompt": entry["prompt"],
                "negative_prompt": entry.get(
                    "negative_prompt", spec["negative"] if "true_cfg_scale" in model else ""
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
            "placements": list(placement),
            "scene": scene.strip(),
            "alt": f"{alt.strip().rstrip('.')} {images.ALT_SUFFIX}",
            "focal_point": [fx, fy],
            "aspect": aspect,
        }
        failures: list[str] = []
        say("checking faces …")
        f = proc.faces(png)
        if not f["pass"]:
            failures.append(f"I4 {rid}: {len(f['hits'])} face(s) of identifiable size {f['hits']}")
        say("checking text …")
        t = proc.text(png)
        if not t["pass"]:
            failures.append(f"I4 {rid}: readable text {[x['text'] for x in t['tokens']]}")
        say("encoding derivatives …")
        try:
            ders = proc.derivatives(png, aspect, (fx, fy), entry["model"], series_name)
        except UsageError as e:
            failures.append(f"I1 {rid}: {e}")
            ders = {}
        if failures:
            raise GateFailed(failures)
        rec["checks"] = {
            "tools": proc.tool_versions(),
            "ran": dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat(),
            "faces": "pass",
            "faces_below_threshold": f["below_threshold"],
            "text": "pass",
            "bytes": "pass",
        }
        target = images.records_dir(reg) / rid
        src_name = f"{rid}.png"
        rec["source"] = {
            "file": src_name,
            "width": entry["width"],
            "height": entry["height"],
            "sha256": images.sha256(png),
        }
        rec["derivatives"] = {
            str(w): {
                "file": f"{rid}-{w}.webp",
                "bytes": len(data),
                "sha256": __import__("hashlib").sha256(data).hexdigest(),
            }
            for w, data in ders.items()
        }
        # validate before writing anything
        import jsonschema

        validator = jsonschema.Draft202012Validator(
            images.schema(), format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER
        )
        errors = [
            f"I1 {rid}: {'/'.join(str(p) for p in e.absolute_path) or '(root)'}: {e.message}"
            for e in validator.iter_errors(rec)
        ]
        if errors:
            raise GateFailed(errors)
        for pl in rec["placements"]:
            kind, _, name = pl.partition(":")
            if kind == "topic" and name not in {x["id"] for x in reg.topics()}:
                raise GateFailed([f"I1 {rid}: unknown topic {name}"])
        if dry_run:
            say(
                f"dry run: {rid} passes every check "
                f"(faces, text, bytes {[len(d) for d in ders.values()]})"
            )
            return
        if target.exists():
            raise GateFailed([f"{target} exists; remove it first"])
        target.mkdir(parents=True)
        shutil.copyfile(png, target / src_name)
        for w, data in ders.items():
            (target / rec["derivatives"][str(w)]["file"]).write_bytes(data)
        (target / "image.yaml").write_text(dump_yaml(rec), encoding="utf-8")
        say(
            f"wrote {target.relative_to(reg.root)} "
            f"({', '.join(f'{w}:{len(d)}' for w, d in ders.items())} bytes)"
        )

    _run(fn)


@app.command("check")
def check_cmd(
    deep: bool = typer.Option(
        False, "--deep", help="Re-run the face and text detectors on the sources (I4)."
    ),
    regenerate: bool = typer.Option(
        False, "--regenerate", help="Re-render each record and compare perceptual hashes (I5)."
    ),
) -> None:
    """Validate every image record (I1, I2); --deep and --regenerate need the images extra."""

    def fn() -> None:
        reg = _reg()
        records, findings = images.load_records(reg)
        findings += images.series_findings(reg, records)
        if deep or regenerate:
            from mobility_model_zoo.site import images_process as proc

            for rec in records:
                src = rec["_dir"] / rec["source"]["file"]
                if deep:
                    f, t = proc.faces(src), proc.text(src)
                    if not f["pass"]:
                        findings.append(f"I4 {rec['id']}: {len(f['hits'])} face(s) {f['hits']}")
                    if not t["pass"]:
                        findings.append(
                            f"I4 {rec['id']}: readable text {[x['text'] for x in t['tokens']]}"
                        )
                    say(
                        f"I4 {rec['id']}: faces {'pass' if f['pass'] else 'FAIL'}, "
                        f"text {'pass' if t['pass'] else 'FAIL'}"
                    )
                if regenerate:
                    findings += _regenerate(rec, src, proc)
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
def list_cmd() -> None:
    """One line per image: id, series, placements, model, date, bytes of the 960 px derivative."""

    def fn() -> None:
        records, _ = images.load_records(_reg())
        if not records:
            print("no image records")
        for r in records:
            g = r.get("generation", {})
            placements = ",".join(r.get("placements", []))
            size = r.get("derivatives", {}).get("960", {}).get("bytes", "?")
            print(
                f"{r['id']:<34} {r.get('series', '?'):<10} {placements:<40} "
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
            raise GateFailed([f"{record_id}: no record under {images.IMAGES_DIR}"], exit_code=2)
        from mobility_model_zoo.release.registry import load_yaml

        placements = (load_yaml(target / "image.yaml") or {}).get("placements", [])
        shutil.rmtree(target)
        say(f"removed {record_id}; placements that now fall back: {', '.join(placements) or 'none'}")

    _run(fn)
