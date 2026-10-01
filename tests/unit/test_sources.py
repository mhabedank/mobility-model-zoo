import shutil

import pytest
import yaml

from mobility_model_zoo.productdev.jtbd.config import load_settings
from mobility_model_zoo.productdev.jtbd.errors import CrawlOnceRefused, UsageError, ValidationFailed
from mobility_model_zoo.productdev.jtbd.sources import registry
from mobility_model_zoo.productdev.jtbd.sources.snapshot import create_snapshot as _create

BODY = b" Lorem mobility text." * 120


def create_snapshot(settings, raw, *args, **kwargs):
    return _create(settings, raw + BODY, *args, **kwargs)

META = {
    "source_type": "paper",
    "license": "CC-BY-4.0",
    "legal_basis": "CC BY 4.0",
    "access_terms_checked": "ok 2026-09-26",
    "permitted_uses": "training_allowed",
    "retention_until": "2027-12-31",
}


@pytest.fixture
def settings(tmp_path, fixture_dir):
    work = tmp_path / "mini"
    shutil.copytree(fixture_dir, work)
    return load_settings(work / "pilot.yaml")


def test_canonicalize_drops_tracking_and_fragment():
    a = registry.canonicalize_url("HTTPS://Example.org/a/b/?utm_source=x&b=2&a=1#frag")
    assert a == "https://example.org/a/b?a=1&b=2"


def test_second_fetch_is_refused(settings):
    rec = create_snapshot(settings, b"paper text one", "txt", "https://example.org/p1", META)
    assert rec["snapshot_id"].startswith("snap-") and len(rec["snapshot_id"]) == 17
    with pytest.raises(CrawlOnceRefused) as info:
        create_snapshot(settings, b"paper text two", "txt", "https://example.org/p1/?utm_x=1", META)
    assert info.value.exit_code == 5


def test_update_requires_reason_and_supersedes(settings):
    first = create_snapshot(settings, b"v1", "txt", "https://example.org/p2", META)
    with pytest.raises(UsageError):
        create_snapshot(settings, b"v2", "txt", "https://example.org/p2", META, update=True)
    second = create_snapshot(settings, b"v2", "txt", "https://example.org/p2", META, update=True,
                             reason="publisher corrected table 3")
    assert second["supersedes"] == first["snapshot_id"]
    assert second["update_reason"] == "publisher corrected table 3"


def test_reddit_is_forced_benchmark_only(settings):
    meta = {**META, "source_type": "reddit"}
    with pytest.raises(ValidationFailed):
        create_snapshot(settings, b"thread", "json", "https://www.reddit.com/comments/x1", meta)
    ok = create_snapshot(settings, b"thread", "json", "https://www.reddit.com/comments/x1",
                         {**meta, "permitted_uses": "benchmark_only"})
    assert ok["permitted_uses"] == "benchmark_only"


def test_retention_is_required(settings):
    meta = {k: v for k, v in META.items() if k != "retention_until"}
    with pytest.raises(ValueError):
        create_snapshot(settings, b"x", "txt", "https://example.org/p3", meta)


def test_snapshot_files_written(settings):
    rec = create_snapshot(settings, b"raw bytes", "txt", "https://example.org/p4", META)
    d = settings.snapshots_dir / rec["snapshot_id"]
    assert (d / "raw.txt").read_bytes() == b"raw bytes" + BODY
    assert yaml.safe_load((d / "source.yaml").read_text())["permitted_uses"] == "training_allowed"


def test_block_pages_and_empty_text_are_refused(settings):
    before = sorted(settings.snapshots_dir.glob("snap-*"))
    with pytest.raises(ValidationFailed, match="unusable"):
        _create(settings, b"Checking your browser before accessing ... " * 50, "txt",
                "https://example.org/blocked", META)
    with pytest.raises(ValidationFailed, match="only"):
        _create(settings, b"too short", "txt", "https://example.org/short", META)
    assert sorted(settings.snapshots_dir.glob("snap-*")) == before
    assert registry.latest_for(settings, "https://example.org/blocked") is None
