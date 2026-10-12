"""RM5 (feature 015): the first planned horizon of an entry cannot change, checked against the git
history of the record (research R4)."""

from __future__ import annotations

import subprocess

from mobility_model_zoo.site import roadmap

RECORD = "zoo/roadmap/roadmap.yaml"


def git(root, *args):
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@example.org", *args],
        check=True,
        capture_output=True,
    )


def commit_all(root, message):
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)


def hum_bearing(r):
    return next(e for e in r["entries"] if e["id"] == "hum-bearing")


def test_changed_planned_is_rm5(site_env):
    git(site_env.root, "init", "-q")
    commit_all(site_env.root, "fixture")
    site_env.edit_yaml(RECORD, lambda r: hum_bearing(r).update(planned="2026-Q4", horizon="2026-Q4"))
    commit_all(site_env.root, "re-date hum-bearing")
    record = roadmap.load(site_env.reg)
    assert roadmap.check_first_planned(site_env.reg, record) == [
        "RM5 hum-bearing: planned was 2027-Q1..Q2 when the entry was added, now 2026-Q4"
    ]


def test_uncommitted_change_is_rm5(site_env):
    git(site_env.root, "init", "-q")
    commit_all(site_env.root, "fixture")
    site_env.edit_yaml(RECORD, lambda r: hum_bearing(r).update(planned="2026-Q4", horizon="2026-Q4"))
    record = roadmap.load(site_env.reg)
    assert len(roadmap.check_first_planned(site_env.reg, record)) == 1


def test_recorded_move_passes(site_env):
    git(site_env.root, "init", "-q")
    commit_all(site_env.root, "fixture")

    def move(r):
        hum_bearing(r).update(
            horizon="2027-Q3..Q4",
            moves=[{"date": "2026-10-12", "to": "2027-Q3..Q4", "reason": "Waiting for data."}],
        )

    site_env.edit_yaml(RECORD, move)
    commit_all(site_env.root, "move hum-bearing")
    record = roadmap.load(site_env.reg)
    assert roadmap.validate(site_env.reg, record) == []


def test_new_entry_and_no_git_pass(site_env):
    record = roadmap.load(site_env.reg)  # the fixture copy is not a git repository
    assert roadmap.check_first_planned(site_env.reg, record) == []
