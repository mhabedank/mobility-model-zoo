"""Triage of a round, the contact sheet and the picks (feature 019, US2; contracts/cli.md).
Needs the `images` extra; the detectors load on first use, so these are slow."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

pytest.importorskip("cv2")
pytestmark = pytest.mark.slow

from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from test_images_series import SERIES, write_series  # noqa: E402

from mobility_model_zoo.release.errors import GateFailed, UsageError  # noqa: E402
from mobility_model_zoo.release.registry import load_yaml  # noqa: E402
from mobility_model_zoo.site import images  # noqa: E402
from mobility_model_zoo.site import images_triage as rounds  # noqa: E402

NAVY, MINT, CREAM, ACCENT = (17, 24, 70), (207, 245, 232), (243, 235, 216), (240, 160, 40)
STYLE = SERIES["style"]


def scene(path: Path, box=(300, 350, 900, 600), sky=MINT, text: str | None = None, size=(1200, 800)):
    img = Image.new("RGB", size, CREAM)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, size[0], size[1] // 2], fill=sky)
    d.rectangle([0, size[1] - 120, size[0], size[1]], fill=NAVY)
    if box:
        d.rectangle(list(box), fill=ACCENT)
    if text:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 140)
        except OSError:
            font = ImageFont.load_default(size=140)
        d.text((120, 120), text, fill=(255, 255, 255), font=font)
    img.save(path)
    return path


def entry(theme: str, subject: str, prompt: str, seed: int) -> dict:
    return {
        "file": f"{theme}--{subject}--{seed}.png",
        "theme": theme,
        "subject": subject,
        "aspect": "3:2",
        "seed_base": 0,
        "prompt": f"{prompt}, {STYLE}",
        "negative_prompt": SERIES["negative"],
        "seed": seed,
        "steps": 50,
        "guidance": 4.0,
        "width": 1200,
        "height": 800,
        "model": "Qwen/Qwen-Image-2512",
        "revision": "a" * 40,
        "model_licence": "Apache-2.0",
        "model_card": "https://huggingface.co/y",
        "pipeline": "QwenImagePipeline",
        "series": "siebdruck",
        "generated": "2026-10-14",
        "hardware": "dgx-spark",
        "generator": {"commit": "abc1234", "image_digest": "sha256:" + "b" * 64},
    }


@pytest.fixture
def round_dir(site_env, tmp_path) -> Path:
    """Three subjects: rail/tram has two good seeds, one with text, one twin of the first;
    private-road/dashboard only has orange-sky renders; private-road/workshop has one good seed."""
    write_series(site_env.root)
    rd = tmp_path / "1"
    rd.mkdir()
    entries = [
        entry("rail", "tram", "an orange-yellow tram", 101),
        entry("rail", "tram", "an orange-yellow tram", 102),
        entry("rail", "tram", "an orange-yellow tram", 103),
        entry("rail", "tram", "an orange-yellow tram", 104),
        entry("private-road", "dashboard", "a dashboard", 201),
        entry("private-road", "dashboard", "a dashboard", 202),
        entry("private-road", "workshop", "a workshop bay", 301),
    ]
    scene(rd / entries[0]["file"])
    scene(rd / entries[1]["file"], box=(100, 420, 500, 640))
    scene(rd / entries[2]["file"], text="ROUTE 400")
    shutil.copyfile(rd / entries[0]["file"], rd / entries[3]["file"])
    scene(rd / entries[4]["file"], box=None, sky=ACCENT)
    scene(rd / entries[5]["file"], box=None, sky=ACCENT)
    scene(rd / entries[6]["file"], box=(500, 300, 800, 560))
    (rd / "manifest.json").write_text(
        json.dumps({"series": "siebdruck", "model": "Qwen/Qwen-Image-2512", "images": entries})
    )
    return rd


def test_triage_outcomes_numbers_sheet_and_summary(site_env, round_dir):
    triage = rounds.triage_round(site_env.reg, round_dir, 1)
    by_file = {c["file"]: c for c in triage["candidates"]}
    tram = [by_file[f"rail--tram--{s}.png"] for s in (101, 102, 103, 104)]
    assert [c["outcome"] for c in tram] == ["shown", "shown", "rejected", "rejected"]
    assert [c["number"] for c in tram] == [1, 2, None, None]
    assert tram[2]["reasons"][0]["check"] == "I4 text" and "400" in tram[2]["reasons"][0]["detail"]
    assert tram[3]["reasons"][0]["check"] == "I7 duplicate"
    assert "rail/tram#1 (0 bits)" in tram[3]["reasons"][0]["detail"]
    dash = [by_file[f"private-road--dashboard--{s}.png"] for s in (201, 202)]
    assert all(c["outcome"] == "rejected" and c["reasons"][0]["check"] == "I6 style" for c in dash)
    assert by_file["private-road--workshop--301.png"]["number"] == 1
    assert tram[0]["focal_default"] and 0.4 < tram[0]["focal_default"][0] < 0.6
    assert len(tram[0]["phash"]) == 16 and "accent_share" in tram[0]["measures"]
    s = triage["summary"]
    assert s["candidates"] == 7 and s["shown"] == 3 and s["subjects"] == 3
    assert s["rejected"] == {"I4 text": 1, "I7 duplicate": 1, "I6 style": 2}
    assert s["subjects_without_candidate"] == ["private-road/dashboard"]
    assert triage["container"] == "sha256:" + "b" * 64 and triage["round"] == 1
    assert json.loads((round_dir / "triage.json").read_text())["summary"] == s
    assert (round_dir / "thumbs" / "rail--tram--101-480.webp").exists()
    assert not (round_dir / "thumbs" / "rail--tram--103-480.webp").exists()
    html = (round_dir / "sheet.html").read_text()
    assert "Needs another round" in html and "private-road/dashboard" in html
    assert html.count("<figure data-number=") == 3 and "#2</b> seed 102" in html
    assert "thumbs/rail--tram--103-480.webp" not in html  # rejected: text only
    assert "I4 text readable text" in html and "<script src" not in html
    assert 'id="dl"' in html and '"picks-round-" + round' in html  # clickable picks → picks.yaml
    assert html.index('id="rail"') < html.index('id="private-road"')


def test_picks_import_records_and_write_next(site_env, round_dir):
    rounds.triage_round(site_env.reg, round_dir, 1)
    picks = {
        "round": 1,
        "picks": {
            "rail/tram": {"number": 2, "focal": [0.3, 0.6]},
            "private-road/workshop": 1,
            "private-road/dashboard": "none",
        },
    }
    assert rounds.pick_round(site_env.reg, round_dir, picks, dry_run=True) == []
    assert not (images.records_dir(site_env.reg) / "rail-tram").exists()
    written = rounds.pick_round(site_env.reg, round_dir, picks)
    assert sorted(p.name for p in written) == ["private-road-workshop", "rail-tram"]
    rec = load_yaml(images.records_dir(site_env.reg) / "rail-tram" / "image.yaml")
    assert rec["theme"] == "rail" and rec["subject"] == "tram" and rec["round"] == 1
    assert rec["placements"] == [] and "file" not in rec["source"]
    assert rec["scene"] == "A tram at a stop at sunrise on a boulevard"
    assert rec["alt"].endswith("(AI-generated image)") and rec["focal_point"] == [0.3, 0.6]
    assert rec["checks"]["style"] == "pass" and len(rec["checks"]["measures"]["phash"]) == 16
    d = images.records_dir(site_env.reg) / "rail-tram"
    assert sorted(p.suffix for p in d.iterdir()) == [".webp", ".webp", ".webp", ".yaml"]
    ws = load_yaml(images.records_dir(site_env.reg) / "private-road-workshop" / "image.yaml")
    assert 0.2 <= ws["focal_point"][0] <= 0.8  # the I6 centroid is the default focal point
    assert (round_dir / "next.txt").read_text().splitlines() == ["private-road/dashboard"]
    records, findings = images.load_records(site_env.reg)
    assert findings == [] and len(records) == 2
    assert images.series_findings(site_env.reg, records) == []
    assert images.library_findings(site_env.reg, records) == []


def test_unknown_or_rejected_pick_is_refused_and_writes_nothing(site_env, round_dir):
    rounds.triage_round(site_env.reg, round_dir, 1)
    with pytest.raises(UsageError) as e:
        rounds.pick_round(site_env.reg, round_dir, {"picks": {"rail/tram": 3}})
    assert e.value.exit_code == 2 and "not a shown candidate" in str(e.value)
    with pytest.raises(UsageError):
        rounds.pick_round(site_env.reg, round_dir, {"picks": {"water/ferry": 1}})
    assert not any(images.records_dir(site_env.reg).glob("*/image.yaml"))
    assert not (round_dir / "next.txt").exists()


def test_a_pick_that_duplicates_a_library_record_fails_atomically(site_env, round_dir):
    rounds.triage_round(site_env.reg, round_dir, 1)
    rounds.pick_round(site_env.reg, round_dir, {"picks": {"rail/tram": 1}})
    # the same candidate under another subject would be a twin of the record just written
    (round_dir / "private-road--workshop--301.png").unlink()
    shutil.copyfile(round_dir / "rail--tram--101.png", round_dir / "private-road--workshop--301.png")
    with pytest.raises(GateFailed) as e:
        rounds.pick_round(
            site_env.reg, round_dir, {"picks": {"private-road/workshop": 1, "rail/tram": 2}}
        )
    assert any("I7 duplicate" in f and "rail-tram" in f for f in e.value.failures)
    assert not (images.records_dir(site_env.reg) / "rail-tram-2").exists()
