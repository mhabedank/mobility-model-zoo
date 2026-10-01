import json
from collections import Counter
from types import SimpleNamespace

import jsonschema
import yaml
from helpers import copy_fixture, pilot, reference_chain, run_ids

from jtbd_pilot.config import load_settings
from jtbd_pilot.ensemble import combine, with_repair
from jtbd_pilot.runs import ChunkOutput, LocatedItem

TEXT = ("Der Bus kommt am Abend nur noch\nalle zwei Stunden. "
        "Viele Pendler nehmen deshalb das Auto. "
        "Die Ladesäule am Bahnhof ist oft defekt.")
BUS = "Der Bus kommt am Abend nur noch\nalle zwei Stunden."
CAR = "Viele Pendler nehmen deshalb das Auto."
CHARGER = "Die Ladesäule am Bahnhof ist oft defekt."
CHUNKS = {"c1": SimpleNamespace(text=TEXT)}
MEMBERS = ["m1", "m2", "m3"]
TIE_BREAK = {"kind": ["m3", "m2", "m1"], "actor_type": ["m1", "m2", "m3"],
             "evidence_type": ["m1", "m2", "m3"], "evidence_scope": ["m1", "m2", "m3"]}


def item(passage, kind="pain", actor="pendler", n=0, quote=None, verbatim=True, **attrs):
    start = TEXT.index(passage)
    values = {"actor_type": "individual", "evidence_type": "anecdote", "evidence_scope": "single",
              **attrs}
    return LocatedItem(n, kind, quote or passage, actor, values["actor_type"], f"{actor} says",
                       values["evidence_type"], values["evidence_scope"],
                       (start, start + len(passage)) if verbatim else None)


def run(outputs, min_votes=2, quote_priority=("m1", "m2", "m3"), members=MEMBERS):
    wrapped = {m: {"c1": ChunkOutput("c1", rel, items)} for m, (rel, items) in outputs.items()}
    return combine(wrapped, list(members), min_votes, CHUNKS, 0.3, TIE_BREAK,
                   list(quote_priority))["c1"]


def test_item_needs_min_votes():
    out = run({"m1": (True, [item(BUS), item(CHARGER, n=1)]),
               "m2": (True, [item(BUS)]),
               "m3": (True, [item(CAR)])})
    assert [i.quote for i in out.items] == [" ".join(BUS.split())]


def test_at_most_one_item_per_member_and_group():
    first = item(BUS)
    second = item("Der Bus kommt am Abend nur noch", n=1)
    out = run({"m1": (True, [first, second]), "m2": (False, []), "m3": (True, [])},
              min_votes=1)
    assert len(out.items) == 2


def test_relevance_majority_and_tie_counts_as_relevant():
    assert run({"m1": (False, []), "m2": (False, []), "m3": (True, [item(BUS)])},
               min_votes=1).relevant is False
    tie = run({"m1": (True, [item(BUS)]), "m2": (False, []), "m3": (None, [])}, min_votes=1)
    assert tie.relevant is True
    assert len(tie.items) == 1
    excluded = run({"m1": (None, []), "m2": (None, []), "m3": (None, [])})
    assert excluded.relevant is None


def test_attribute_tie_break_and_quote_priority():
    out = run({"m1": (True, [item(BUS, kind="pain", actor="from m1", evidence_type="routine")]),
               "m2": (True, [item(BUS, kind="job", actor="from m2", evidence_type="opinion")]),
               "m3": (True, [])}, quote_priority=("m2", "m1", "m3"))
    [result] = out.items
    assert result.kind == "job"  # tie: m3 is first in the kind order but has no item, then m2
    assert result.evidence_type == "routine"  # tie: m1 first
    assert result.actor == "from m2" and result.statement == "from m2 says"


def test_majority_beats_tie_break():
    out = run({"m1": (True, [item(BUS, kind="pain")]),
               "m2": (True, [item(BUS, kind="pain")]),
               "m3": (True, [item(BUS, kind="job")])})
    assert out.items[0].kind == "pain"


def test_near_miss_quote_is_repaired_before_grouping():
    near_miss = item(BUS, quote="Der Bus kommt am Abend nur noch alle 2 Stunden.", verbatim=False)
    out = run({"m1": (True, [near_miss]), "m2": (True, [item(BUS)]), "m3": (True, [])},
              quote_priority=("m1", "m2", "m3"))
    [result] = out.items
    assert result.quote == "Der Bus kommt am Abend nur noch alle zwei Stunden."
    assert TEXT[result.span[0]:result.span[1]] == BUS


def test_unrepairable_quote_is_dropped_and_counted():
    stats = Counter()
    bad = item(BUS, quote="Die Straßenbahn fährt nachts überhaupt nicht", verbatim=False)
    near = item(BUS, quote="Der Bus kommt am Abend nur noch alle 2 Stunden.", verbatim=False)
    kept = with_repair(ChunkOutput("c1", True, [bad, near, item(CAR)]), TEXT, stats=stats)
    assert [i.quote for i in kept] == ["Der Bus kommt am Abend nur noch alle zwei Stunden.", CAR]
    assert stats == {"invalid_quotes": 2, "repaired": 1, "dropped": 1}
    out = run({"m1": (True, [bad]), "m2": (True, [item(BUS)]), "m3": (True, [])})
    assert out.items == []


# ---- pilot ensemble ----------------------------------------------------------------------------
def _teachers(config):
    for model in ("mock-teacher-x", "mock-teacher-y"):
        pilot(config, "label", "--role", "teacher_candidate", "--backend", "mock", "--model", model)


def test_pilot_ensemble_writes_derived_run(tmp_path, contracts_dir):
    config = copy_fixture(tmp_path)
    reference_chain(config)
    _teachers(config)
    ids = run_ids(config)
    summary = pilot(config, "ensemble")
    run_dir = load_settings(config).runs_dir / summary["run_id"]
    manifest = json.loads((run_dir / "manifest.json").read_text())
    assert manifest["backend"] == "ensemble"
    assert manifest["role"] == "teacher_candidate"
    assert manifest["derived_from"] == [ids["mock-teacher-x"], ids["mock-teacher-y"]]
    assert manifest["cost_eur"] == 0
    assert manifest["status"] == "complete"
    assert not (run_dir / "raw").exists()
    contract = json.loads((contracts_dir / "label-run-manifest.schema.json").read_text())
    jsonschema.validate(manifest, contract)
    assert sorted(p.name for p in (run_dir / "parsed").iterdir())
    checks = pilot(config, "check", "--run", summary["run_id"])
    assert checks["pass_rates"]["schema_valid"]["rate"] == 1.0
    assert checks["pass_rates"]["quote_verbatim"]["rate"] == 1.0
    score = pilot(config, "score", "--run", summary["run_id"])
    assert score["repaired"]["repair_stats"] == {"invalid_quotes": 0, "repaired": 0, "dropped": 0}
    assert score["repaired"]["composite"] == score["composite"]
    # Rebuilding gives the same run.
    assert pilot(config, "ensemble") == summary


def test_pilot_ensemble_needs_complete_member_runs(tmp_path):
    config = copy_fixture(tmp_path)
    reference_chain(config)
    pilot(config, "label", "--role", "teacher_candidate", "--backend", "mock",
          "--model", "mock-teacher-x")
    pilot(config, "ensemble", expect=1)
    pilot(config, "label", "--role", "teacher_candidate", "--backend", "mock",
          "--model", "mock-teacher-y", "--limit", "2")
    pilot(config, "ensemble", expect=1)


def test_pilot_ensemble_refuses_changed_criteria(tmp_path):
    config = copy_fixture(tmp_path)
    reference_chain(config)
    _teachers(config)
    criteria = config.parent / "decision-criteria.yaml"
    doc = yaml.safe_load(criteria.read_text())
    doc["teacher_ensemble"]["min_votes"] = 1
    criteria.write_text(yaml.safe_dump(doc))
    pilot(config, "ensemble", expect=3)


def test_ensemble_model_cannot_be_labeled(tmp_path):
    config = copy_fixture(tmp_path)
    pilot(config, "freeze")
    pilot(config, "label", "--role", "teacher_candidate", "--backend", "ensemble",
          "--model", "mock-ensemble", expect=2)
