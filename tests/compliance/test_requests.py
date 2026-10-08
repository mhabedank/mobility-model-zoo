"""Requests, suppression and legal watch (FR-026 … FR-028)."""

import yaml
from compliance_helpers import TODAY, load, write
from typer.testing import CliRunner

from mobility_model_zoo.compliance.checks import Context, stage_meta
from mobility_model_zoo.compliance.hashing import keyed_hash
from mobility_model_zoo.compliance.signals import Lists, check_url
from mobility_model_zoo.release.cli import app

RUN = CliRunner()


def zoo(root, monkeypatch, *args, key="test-key"):
    monkeypatch.chdir(root)
    if key:
        monkeypatch.setenv("MMZ_SUPPRESSION_KEY", key)
    else:
        monkeypatch.delenv("MMZ_SUPPRESSION_KEY", raising=False)
    return RUN.invoke(app, ["compliance", *args])


def test_request_add_stores_only_a_keyed_hash(register_tree, monkeypatch):
    res = zoo(
        register_tree,
        monkeypatch,
        "request",
        "add",
        "--type",
        "takedown",
        "--identifier",
        "https://news.example/article",
        "--received",
        "2026-10-08",
    )
    assert res.exit_code == 0, res.output
    text = (register_tree / "compliance/requests.yaml").read_text()
    assert "news.example" not in text
    req = yaml.safe_load(text)["requests"][0]
    assert req["deadline"] == "2026-10-22"
    assert req["identifier_hash"] == keyed_hash("https://news.example/article", b"test-key")
    supp = yaml.safe_load((register_tree / "compliance/suppression.yaml").read_text())["entries"]
    assert supp[0]["hash"] == req["identifier_hash"]


def test_request_url_then_fetch_is_blocked(register_tree, monkeypatch):
    zoo(
        register_tree,
        monkeypatch,
        "request",
        "add",
        "--type",
        "opt_out",
        "--identifier",
        "https://www.News.example/a/",
        "--received",
        "2026-10-08",
    )
    entries = yaml.safe_load((register_tree / "compliance/suppression.yaml").read_text())["entries"]
    v, _ = check_url(
        "https://news.example/a",
        Lists(suppressed_url_hashes={e["hash"] for e in entries}),
        None,
        url_hash=lambda u: keyed_hash(u, b"test-key"),
    )
    assert [c for c, _ in v.reasons] == ["C-F5"]


def test_request_needs_the_key(register_tree, monkeypatch):
    res = zoo(
        register_tree,
        monkeypatch,
        "request",
        "add",
        "--type",
        "erasure",
        "--identifier",
        "x",
        "--received",
        "2026-10-08",
        key=None,
    )
    assert res.exit_code != 0


def test_gdpr_deadline_one_month(register_tree, monkeypatch):
    zoo(
        register_tree,
        monkeypatch,
        "request",
        "add",
        "--type",
        "objection",
        "--identifier",
        "Lena Beispiel",
        "--received",
        "2026-09-01",
        "--suppress",
        "identifier",
    )
    assert {f.check_id for f in stage_meta(Context(load(register_tree, TODAY)))} == {"C-M4"}


def test_suppressed_url_blocks_fetch():
    digest = keyed_hash("https://news.example/a", b"k")
    v, _ = check_url(
        "https://news.example/a",
        Lists(suppressed_url_hashes={digest}),
        None,
        url_hash=lambda u: keyed_hash(u, b"k"),
    )
    assert [c for c, _ in v.reasons] == ["C-F5"]


def test_watch_review_clears_meta(register_tree, monkeypatch):
    write(
        register_tree,
        "compliance/legal-watch.yaml",
        {
            "items": [
                {
                    "id": "bgh",
                    "title": "BGH",
                    "kind": "court",
                    "expected": None,
                    "review_by": "2026-10-01",
                    "reviewed_at": None,
                    "outcome": None,
                    "affects": [],
                }
            ]
        },
    )
    assert {f.check_id for f in stage_meta(Context(load(register_tree, TODAY)))} == {"C-M2"}
    res = zoo(register_tree, monkeypatch, "watch", "review", "bgh", "--outcome", "no change")
    assert res.exit_code == 0, res.output
    assert stage_meta(Context(load(register_tree, TODAY))) == []
