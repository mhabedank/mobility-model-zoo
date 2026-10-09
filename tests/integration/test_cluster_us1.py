"""User story 1 end to end: bundle -> `jtbd cluster run` -> `jtbd cluster check` (feature 009, T017).

Stub vectors from tests/fixtures/cluster/vectors.json; nothing is downloaded.
"""

import json
from pathlib import Path

from typer.testing import CliRunner

from mobility_model_zoo.productdev.jtbd.cli import app

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "cluster"
BUNDLE = FIXTURE / "bundles" / "basic.jsonl"
SETTINGS = FIXTURE / "settings.yaml"


def jtbd(*args, expect=0):
    result = CliRunner().invoke(app, list(args))
    assert result.exit_code == expect, (result.exit_code, result.output)
    return result


def run(tmp_path, *bundles):
    out = tmp_path / "map"
    args = ["cluster", "run", "--map", str(out), "--settings", str(SETTINGS)]
    for b in bundles:
        args += ["--input", str(b)]
    jtbd(*args)
    return out, json.loads((out / "result.json").read_text())


def test_run_then_check(tmp_path):
    out, result = run(tmp_path, BUNDLE)
    jtbd("cluster", "check", "--map", str(out))
    items = {i["item_id"]: i for i in result["items"]}
    assert result["inputs"]["sources"] == 23  # the irrelevant source without items is processed too
    assert len(items) == 23
    by_sources = {frozenset(items[m]["source_id"] for m in g["members"]): g for g in result["groups"]}
    # German and English paraphrase in one group, counted as two independent threads
    assert by_sources[frozenset({"s01", "s02"})]["counts"]["independent_sources"] == 2
    # the same text collected twice: one independent source, two mentions
    copies = by_sources[frozenset({"s11", "s12"})]["counts"]
    assert copies == {"mentions": 2, "independent_sources": 1, "independence_rule": "source_id"}
    # a quoting reply in the same thread: one independent source
    assert by_sources[frozenset({"s13", "s14"})]["counts"]["independent_sources"] == 1
    # the job with the same direction as the parking pain stays in its own group
    job = next(g for g in result["groups"] if g["kind"] == "job"
               and {items[m]["source_id"] for m in g["members"]} == {"s03"})
    assert job["members"] == [i for i, it in items.items() if it["source_id"] == "s03"]
    assert len(result["groups"]) == 16
    assert result["clusters"] == []


def test_quotes_are_byte_identical_to_the_bundle(tmp_path):
    _, result = run(tmp_path, BUNDLE)
    bundle_quotes = {it["quote"] for line in BUNDLE.read_text().splitlines()
                     for it in json.loads(line)["output"]["items"]}
    assert {i["quote"] for i in result["items"]} == bundle_quotes


def test_check_fails_on_an_edited_result(tmp_path):
    out, result = run(tmp_path, BUNDLE)
    result["items"][0]["quote"] = result["items"][0]["quote"].upper()
    (out / "result.json").write_text(json.dumps(result))
    jtbd("cluster", "check", "--map", str(out), expect=1)


def test_other_format_version_is_refused(tmp_path):
    result = jtbd("cluster", "run", "--input", str(FIXTURE / "bundles" / "bad_version.jsonl"),
                  "--settings", str(SETTINGS), expect=1)
    assert "bad_version.jsonl:1" in result.output


def test_identical_runs_give_identical_results(tmp_path):
    out1, _ = run(tmp_path / "a", BUNDLE)
    out2, _ = run(tmp_path / "b", BUNDLE)
    assert (out1 / "result.json").read_bytes() == (out2 / "result.json").read_bytes()
