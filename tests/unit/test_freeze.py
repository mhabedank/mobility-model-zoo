import shutil

import pytest

from jtbd_pilot.config import load_settings
from jtbd_pilot.errors import FrozenHashMismatch, UsageError
from jtbd_pilot.freeze import freeze_criteria, sha256_canonical, verify_frozen


def test_canonical_hash_ignores_line_endings(tmp_path):
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    a.write_bytes(b"line one\nline two\n")
    b.write_bytes(b"line one\r\nline two\r\n")
    assert sha256_canonical(a) == sha256_canonical(b)


def test_canonical_hash_ignores_yaml_key_order(tmp_path):
    a, b = tmp_path / "a.yaml", tmp_path / "b.yaml"
    a.write_text("x: 1\ny: [1, 2]\n")
    b.write_text("y: [1, 2]\nx: 1\n")
    assert sha256_canonical(a) == sha256_canonical(b)


@pytest.fixture
def settings(tmp_path, fixture_dir):
    work = tmp_path / "mini"
    shutil.copytree(fixture_dir, work)
    return load_settings(work / "pilot.yaml")


def test_changed_criteria_is_detected(settings):
    freeze_criteria(settings)
    verify_frozen(settings)
    criteria = settings.paths["criteria"]
    text = criteria.read_text()
    criteria.write_text(text.replace("relevance_kappa: 0.8", "relevance_kappa: 0.7"))
    with pytest.raises(FrozenHashMismatch):
        verify_frozen(settings)
    with pytest.raises(FrozenHashMismatch):
        freeze_criteria(settings)


def test_new_version_requires_rationale(settings):
    freeze_criteria(settings)
    with pytest.raises(UsageError):
        freeze_criteria(settings, new_version="pilot-v2")
    manifest = freeze_criteria(settings, new_version="pilot-v2", rationale="test")
    assert manifest["supersedes"] == "mini-v1"
    assert verify_frozen(settings)["version"] == "pilot-v2"
