"""Pre-registration is enforced by `train` (feature 021, T010; FR-007, research R2).

Training itself is stubbed out: these tests only check the refusals and the recorded fields.
"""

import subprocess
from pathlib import Path

import pytest

from mobility_model_zoo.edge.int8 import keras_export as ke

CRITERIA = """version: 1
date: 2026-10-20
benchmark: uci-har-v1
seeds: {candidate: 0, spread: [1, 2, 3, 4]}
"""


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def prereg(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.org")
    _git(repo, "config", "user.name", "t")
    (repo / "README").write_text("x")
    _git(repo, "add", "README")
    _git(repo, "commit", "-qm", "init")
    manifest = repo / "manifest.json"
    manifest.write_text("{}")
    return ke.Prereg(criteria=repo / "criteria.yaml", manifest=manifest, benchmark="uci-har-v1")


def _commit(p: ke.Prereg) -> None:
    _git(p.criteria.parent, "add", p.criteria.name)
    _git(p.criteria.parent, "commit", "-qm", "criteria")


def _refused(p, seed=0):
    with pytest.raises(SystemExit) as e:
        ke.check_prereg(p, seed)
    assert e.value.code == ke.REFUSED


def test_missing_manifest_is_refused(prereg):
    prereg.criteria.write_text(CRITERIA)
    _commit(prereg)
    prereg.manifest.unlink()
    _refused(prereg)


def test_untracked_criteria_are_refused(prereg):
    prereg.criteria.write_text(CRITERIA)
    _refused(prereg)


def test_modified_criteria_are_refused(prereg):
    prereg.criteria.write_text(CRITERIA)
    _commit(prereg)
    prereg.criteria.write_text(CRITERIA.replace("version: 1", "version: 2"))
    _refused(prereg)


def test_seed_outside_the_criteria_is_refused(prereg):
    prereg.criteria.write_text(CRITERIA)
    _commit(prereg)
    _refused(prereg, seed=5)


def test_committed_criteria_are_recorded(prereg):
    prereg.criteria.write_text(CRITERIA)
    _commit(prereg)
    rec = ke.check_prereg(prereg, 3)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=prereg.criteria.parent, capture_output=True, text=True
    ).stdout.strip()
    assert rec["criteria_version"] == 1
    assert rec["criteria_commit"] == head
    assert rec["criteria_sha256"] == ke.file_sha256(prereg.criteria)
    assert rec["manifest_sha256"] == ke.file_sha256(prereg.manifest)
    assert rec["benchmark"] == "uci-har-v1"


def test_activity_has_no_epochs_option(monkeypatch):
    from mobility_model_zoo.condition_monitoring.activity import train as pace

    with pytest.raises(SystemExit) as e:
        pace.main(["--epochs", "1"])
    assert e.value.code == 2  # argparse: unknown option


def test_sound_anomaly_keeps_epochs(monkeypatch):
    from mobility_model_zoo.condition_monitoring.sound_anomaly import train as hum

    seen = {}
    monkeypatch.setattr(ke, "train", lambda *a, **k: seen.setdefault("epochs", a[3]) or {})
    hum.main(["--epochs", "1"])
    assert seen["epochs"] == 1


def test_default_out_is_a_seed_folder(monkeypatch, tmp_path):
    from mobility_model_zoo.condition_monitoring.activity import train as pace

    monkeypatch.setenv("MMZ_DATA", str(tmp_path))
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}")
    monkeypatch.setattr(pace, "manifest_path", lambda: manifest)
    monkeypatch.setattr(ke, "check_prereg", lambda p, seed: {})
    seen = {}
    monkeypatch.setattr(ke, "train", lambda *a, **k: seen.setdefault("out", a[6]) or {})
    pace.main(["--seed", "2"])
    assert Path(seen["out"]) == tmp_path / "derived" / "pace-cnn" / "seed-2"
