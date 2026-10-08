"""Retention (C-R1), deletion log, and train checks (C-T1 … C-T5)."""

import datetime as dt
import json

import yaml
from compliance_helpers import load, route, seed, write

from mobility_model_zoo.compliance.train import check_training, delete_snapshot, retention_findings


def _snapshot(root, sid, until):
    d = root / "data/snapshots" / sid
    d.mkdir(parents=True)
    (d / "source.yaml").write_text(
        yaml.safe_dump(
            {"snapshot_id": sid, "origin_url": "https://example.org/x", "retention_until": until}
        )
    )
    (d / "text.txt").write_text("text")
    (d / "raw.html").write_text("<p>text</p>")


def test_retention_and_delete(register_tree):
    _snapshot(register_tree, "snap-a", "2026-10-07")
    _snapshot(register_tree, "snap-b", "2028-10-01")
    found = retention_findings(register_tree, dt.date(2026, 10, 8))
    assert [f.record for f in found] == ["snap-a"]
    entry = delete_snapshot(register_tree, "snap-a", "retention expired")
    assert not (register_tree / "data/snapshots/snap-a/text.txt").exists()
    log = (register_tree / "data/compliance/deletions.jsonl").read_text().splitlines()
    assert json.loads(log[0])["origin_url"] == "https://example.org/x" and len(entry["files"]) == 2
    assert retention_findings(register_tree, dt.date(2026, 10, 8)) == []


def ids(root, **kw):
    args = {"origins": ["https://example.org/paper-one"], "model_licence": "Apache-2.0", "teachers": []}
    args.update(kw)
    return {f.check_id for f in check_training(load(root), **args)}


def test_clean_training(register_tree):
    assert ids(register_tree) == set()


def test_suppressed_and_opted_out(register_tree):
    write(
        register_tree,
        "compliance/suppression.yaml",
        {"entries": [{"hash": "a" * 64, "kind": "url", "request_id": "r1", "added_at": "2026-10-08"}]},
    )
    assert ids(register_tree, url_hash=lambda u: "a" * 64) == {"C-T1"}


def test_nd_licence(register_tree):
    seed(
        register_tree,
        "topics/t/compliance/sources.yaml",
        lambda d: d["sources"][0].update(licence="CC-BY-ND-4.0", permitted_use="benchmark_only"),
    )
    assert ids(register_tree) == {"C-T2"}


def test_share_alike_needs_matching_licence(register_tree):
    seed(
        register_tree,
        "topics/t/compliance/sources.yaml",
        lambda d: d["sources"][0].update(licence="CC-BY-SA-4.0"),
    )
    assert ids(register_tree) == {"C-T3"}
    assert ids(register_tree, model_licence="CC-BY-SA-4.0") == set()


def test_teacher_without_output_rights(register_tree):
    write(
        register_tree,
        "compliance/providers.yaml",
        {
            "routes": [
                route(
                    id="t", log_matches=["teacher-x|openrouter|P"], output_training_permitted="unclear"
                )
            ]
        },
    )
    assert ids(register_tree, teachers=["teacher-x"]) == {"C-T4"}


def test_recall_below_threshold(register_tree):
    assert ids(register_tree, recall=0.9) == {"C-T5"}
