# ruff: noqa: E501  (fixture data table: long literal lines read better unwrapped)
"""Write tests/fixtures/mini-corpus-v3 (feature 025, task T005). Deterministic; run again after edits.

All texts are invented for tests. Mock answers are test data only: they are never a benchmark
reference (the fixture sets test_fixture: true, and the v3 freeze refuses mock runs otherwise).
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "mini-corpus-v3"

TEXTS = {
    "c01": ("de", "Im Dorf fährt der letzte Bus um 18 Uhr. Abends komme ich deshalb nicht mehr nach Hause. "
                  "Ich wünsche mir einen Bus bis Mitternacht."),
    "c02": ("de", "Die Stadtwerke haben zwölf neue Busse gekauft. Sie fahren ab März auf Linie 4."),
    "c03": ("de", "Zuerst bringe ich die Kinder zur Schule, danach fahre ich mit dem Auto zur Arbeit. "
                  "Ich nehme das Auto, um pünktlich zu sein. Der Stau kostet mich jeden Morgen zwanzig Minuten."),
    "c04": ("de", "Als Paketbote parke ich in zweiter Reihe, weil es keine Ladezonen gibt. "
                  "Die Radfahrer ärgern sich, weil ich den Radweg blockiere."),
    "c05": ("en", "Our depot runs night buses. Passengers complain that the app shows no live delays. "
                  "We want to give them reliable real-time information."),
    "c06": ("en", "The council approved a new timetable. It starts in March."),
    "c07": ("en", "First I cycle to the station, then I take the train to work. I cycle in order to save money. "
                  "The train is late almost every day."),
    "c08": ("en", "As a delivery driver I double-park because there are no loading bays, and cyclists get "
                  "angry because I block the bike lane."),
}


def item(kind, quote, actor, ev, scope):
    return {"kind": kind, "quote": quote, "actor_type": actor, "evidence_type": ev, "evidence_scope": scope}


def attrs(i, job_kind=None, mode=(), improve=(), sol=False, role=None, situation=None):
    return {"index": i, "job_kind": job_kind, "mode": list(mode), "improve": list(improve),
            "states_solution": sol, "executor_role": role, "situation": situation}


# Reference A: the intended reading of each text.
A = {
    "c01": ([item("pain", "der letzte Bus um 18 Uhr", "individual", "routine", "single"),
             item("pain", "Abends komme ich deshalb nicht mehr nach Hause", "individual", "routine", "single"),
             item("gain", "Ich wünsche mir einen Bus bis Mitternacht", "individual", "opinion", "single")],
            [attrs(0, mode=["bus"], improve=["access"], situation="Im Dorf"),
             attrs(1, improve=["access"], situation="Abends"),
             attrs(2, mode=["bus"], improve=["access"], sol=True)],
            []),
    "c02": ([], [], []),
    "c03": ([item("job", "bringe ich die Kinder zur Schule", "individual", "routine", "single"),
             item("job", "fahre ich mit dem Auto zur Arbeit", "individual", "routine", "single"),
             item("job", "um pünktlich zu sein", "individual", "opinion", "single"),
             item("pain", "Der Stau kostet mich jeden Morgen zwanzig Minuten", "individual", "routine", "single")],
            [attrs(0, job_kind="functional"),
             attrs(1, job_kind="functional", mode=["car"]),
             attrs(2, job_kind="functional", improve=["reliability"]),
             attrs(3, improve=["time"], situation="Morgen")],
            [{"from": 0, "to": 1, "relation": "before"}, {"from": 1, "to": 2, "relation": "in_order_to"}]),
    "c04": ([item("pain", "parke ich in zweiter Reihe, weil es keine Ladezonen gibt", "worker", "routine", "single"),
             item("pain", "Die Radfahrer ärgern sich, weil ich den Radweg blockiere", "individual", "observation",
                  "multiple")],
            [attrs(0, improve=["access"], role="Paketbote"),
             attrs(1, mode=["bicycle"], improve=["safety"], role="Radfahrer")],
            [{"from": 0, "to": 1, "relation": "causes"}]),
    "c05": ([item("pain", "Passengers complain that the app shows no live delays", "individual", "observation",
                  "multiple"),
             item("job", "We want to give them reliable real-time information", "organization", "opinion", "single")],
            [attrs(0, improve=["information"], role="Passengers"),
             attrs(1, job_kind="functional", improve=["information", "reliability"], role="depot")],
            []),
    "c06": ([], [], []),
    "c07": ([item("job", "I cycle to the station", "individual", "routine", "single"),
             item("job", "I take the train to work", "individual", "routine", "single"),
             item("job", "in order to save money", "individual", "opinion", "single"),
             item("pain", "The train is late almost every day", "individual", "routine", "single")],
            [attrs(0, job_kind="functional", mode=["bicycle"]),
             attrs(1, job_kind="functional", mode=["train"]),
             attrs(2, job_kind="functional", improve=["cost"]),
             attrs(3, mode=["train"], improve=["reliability"])],
            [{"from": 0, "to": 1, "relation": "before"}, {"from": 0, "to": 2, "relation": "in_order_to"}]),
    "c08": ([item("pain", "I double-park because there are no loading bays", "worker", "routine", "single"),
             item("pain", "cyclists get angry because I block the bike lane", "individual", "observation", "multiple")],
            [attrs(0, improve=["access"], role="delivery driver"),
             attrs(1, mode=["bicycle"], improve=["safety"], role="cyclists")],
            [{"from": 0, "to": 1, "relation": "causes"}]),
}


def variant_b():
    """Reference B: mostly A, with deliberate disagreements."""
    b = json.loads(json.dumps(A))
    b["c01"][0][1]["evidence_type"] = "anecdote"           # evidence disagreement
    b["c01"][1][2]["states_solution"] = False                # solution disagreement
    b["c03"][0][3]["quote"] = "Der Stau kostet mich jeden Morgen"  # shorter span, still matched
    b["c03"][2] = [{"from": 0, "to": 1, "relation": "before"}]     # misses the means-end link
    b["c05"][1][1]["improve"] = ["information"]              # list disagreement
    b["c07"][0].pop(2)                                       # misses one item
    b["c07"][1] = [attrs(0, job_kind="functional", mode=["bicycle"]),
                   attrs(1, job_kind="functional", mode=["train"]),
                   attrs(2, mode=["train"], improve=["reliability"])]
    b["c07"][2] = [{"from": 0, "to": 1, "relation": "before"}]
    b["c08"][1][0]["role"] = None                            # pointer disagreement
    return b


def variant_base():
    """Baseline: finds only the first item of each relevant text, no links."""
    out = {}
    for cid, (p1, p2, _p3) in A.items():
        out[cid] = (p1[:1], [dict(p2[0], index=0)] if p2 else [], [])
    return out


def write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    for cid, (lang, text) in TEXTS.items():
        for _, (p1, _p2, _p3) in (("a", A[cid]),):
            for it in p1:
                assert it["quote"] in text, (cid, it["quote"])
        write(ROOT / "store" / "chunks" / f"{cid}.json", {
            "chunk_id": cid, "snapshot_id": f"snap-v3-{cid}", "ranges": [[0, len(text)]], "text": text,
            "token_count": len(text.split()), "split": "main", "sub_area": "public_transport_rural",
            "source_type": "transcript", "region": "DACH" if lang == "de" else "UK",
            "country": "DE" if lang == "de" else "GB", "language": lang, "date": "2026-11-01",
            "license": "invented test text", "relevance_intent": "relevant" if A[cid][0] else "near_miss",
            "redaction": {"patterns_version": "redact-v2", "manual_review_at": "2026-11-28T10:00:00+00:00",
                          "check_passed": True}})
    for model, data in (("mock-a", A), ("mock-b", variant_b()), ("mock-base", variant_base())):
        for cid, (p1, p2, p3) in data.items():
            write(ROOT / "mock" / model / f"{cid}.p1.json", {"relevant": bool(p1), "items": p1})
            if p1:
                write(ROOT / "mock" / model / f"{cid}.p2.json", {"items": p2})
            if len(p1) >= 2:
                write(ROOT / "mock" / model / f"{cid}.p3.json", {"links": p3})
    index = "".join(json.dumps({"snapshot_id": f"snap-v3-{c}", "canonical_url": f"https://example.org/v3/{c}",
                                "retrieved_at": "2026-11-28T10:00:00+00:00", "supersedes": None}) + "\n"
                    for c in TEXTS)
    (ROOT / "store" / "snapshots").mkdir(parents=True, exist_ok=True)
    (ROOT / "store" / "snapshots" / "index.jsonl").write_text(index, encoding="utf-8")
    (ROOT / "models.yaml").write_text(yaml.safe_dump({"models": [
        {"model_id": "mock-a", "family": "fam-a", "backend": "mock", "host": "local", "role": "reference",
         "benchmark_labeler": True, "teacher_banned": True},
        {"model_id": "mock-b", "family": "fam-b", "backend": "mock", "host": "local", "role": "reference",
         "benchmark_labeler": True, "teacher_banned": True},
        {"model_id": "mock-base", "family": "fam-c", "backend": "mock", "host": "local", "role": "baseline"},
    ]}, sort_keys=False), encoding="utf-8")


REPO = ROOT.parents[2]


def write_configs() -> None:
    real_brief = yaml.safe_load((REPO / "topics/productdev/guideline/scout-v3/brief.yaml").read_text(encoding="utf-8"))
    brief = {
        "teacher_task_en": "Find the jobs, pains and gains in the text (fixture).",
        "kind": {"drafted_by": "claude", "approval": "fixture owner",
                 "job": "What an actor wants to get done (fixture).",
                 "pain": "What bothers the actor (fixture).", "gain": "What the actor wants (fixture)."},
        "mode": {"values": real_brief["mode"]["values"]},
        "improve": {"values": real_brief["improve"]["values"]},
        "pass_instructions": {"drafted_by": "claude", "approval": "fixture owner",
                              "pass1": "Fixture pass 1: return the items.",
                              "pass2": "Fixture pass 2: return the attributes of the given items.",
                              "pass3": "Fixture pass 3: return the links between the given items."},
        "pilot_thresholds": real_brief["pilot_thresholds"],
        "link_connectives": real_brief["link_connectives"],
    }
    (ROOT / "brief.yaml").write_text(yaml.safe_dump(brief, allow_unicode=True, sort_keys=False), encoding="utf-8")
    examples = {"examples": [{"id": "x01", "language": "en", "text": "The bus is always late.", "relevant": True,
                              "items": [{"id": "i1", "kind": "pain", "quote": "The bus is always late."}],
                              "links": {"actor_pair": [], "means_end": [], "order": []}}]}
    (ROOT / "examples.yaml").write_text(yaml.safe_dump(examples, allow_unicode=True, sort_keys=False),
                                        encoding="utf-8")
    criteria = {"pilot_thresholds": real_brief["pilot_thresholds"],
                "bootstrap": {"resamples": 200, "seed": 7},
                "role_words": {"de": ["Paketbote", "Radfahrer"], "en": ["driver", "cyclists", "passengers"]}}
    (ROOT / "criteria-pilot-v3.yaml").write_text(yaml.safe_dump(criteria, allow_unicode=True, sort_keys=False),
                                                 encoding="utf-8")
    (ROOT / "budget.yaml").write_text("budget_eur: 25\nkey_cap_eur: 25\nopenrouter_fee: 0.055\nusd_to_eur: 0.92\n"
                                      "prices: {}\n", encoding="utf-8")
    for name in ("teacher-scoring.yaml", "domain.yaml"):
        (ROOT / name).write_text((REPO / "tests/fixtures/mini-corpus" / name).read_text(encoding="utf-8"),
                                 encoding="utf-8")
    (ROOT / "pilot-v3.yaml").write_text("""# Mini corpus for pilot-v3 (feature 025): 8 invented chunks, mocked backends.
# The package is assembled and approved into `package/` by the test helper at run time.
root: .
benchmark_version: mini-v3
test_fixture: true
budget_name: mini-v3
paths:
  guideline: package/guideline.md
  examples: package/examples
  domain: domain.yaml
  models: models.yaml
  criteria: criteria-pilot-v3.yaml
  teacher_scoring: teacher-scoring.yaml
  budget: budget.yaml
  data: store
  benchmarks: benchmarks
  reports: reports
  mock: mock
pilot:
  max_retries: 0
  max_output_tokens: 4096
  assumed_output_tokens: 500
  redaction_patterns_version: redact-v2
  redaction_review: model
v3:
  benchmark: mini-v3
  brief: brief.yaml
  package: package
  criteria: criteria-pilot-v3.yaml
  pool: store/chunks
  languages: [de, en]
  seed: 7
""", encoding="utf-8")
    (ROOT / "README.md").write_text("""# mini-corpus-v3 (feature 025)

Generated by `scripts/fixtures/make_mini_corpus_v3.py`; do not edit by hand. All texts are invented.

- 8 chunks: c01 to c04 German, c05 to c08 English; c02 and c06 contain no need (empty results).
- Mock answers per pass (`mock/<model>/<chunk>.p<n>.json`):
  - `mock-a`: the intended reading.
  - `mock-b`: `mock-a` with deliberate disagreements. c01: evidence of item 0, solution flag of item 2.
    c03: a shorter span for item 3, which is still matched at token IoU 0.5, and no means-end link.
    c05: improve list of item 1. c07: misses one item and its means-end link. c08: no role on item 0.
  - `mock-base`: only the first item of each relevant text, no links.
- `brief.yaml` copies `pilot_thresholds` and `link_connectives` from the real brief, so the criteria check
  of `jtbd v3 freeze-criteria` applies here too.
- The hand-computed agreement figures of the statistics live in `tests/fixtures/v3-agreement/` (task T021);
  this corpus tests the flow, not the arithmetic.
""", encoding="utf-8")


if __name__ == "__main__":
    main()
    write_configs()
