from helpers import copy_fixture, pilot, reference_chain, run_ids

from mobility_model_zoo.productdev.jtbd.config import load_settings
from mobility_model_zoo.productdev.jtbd.jsonio import write_json

SECTIONS = ["## 1. Decision", "## 2. Versions", "## 3. Corpus composition",
            "## 4. Agreement between reference models", "## 5. Deterministic checks",
            "## 6. Contested items", "## 7. Disagreement categories",
            "## 8. Proposed guideline revisions", "## 9. Teacher candidates and zero-shot baselines",
            "## 10. Quality vs throughput", "## 11. Deviations", "## 12. Budget"]


def test_full_mock_chain_report(tmp_path):
    config = copy_fixture(tmp_path)
    reference_chain(config)
    pilot(config, "corpus", "validate", "--split", "main")
    pilot(config, "agreement")
    pilot(config, "label", "--role", "baseline", "--backend", "mock", "--model", "mock-small")
    for teacher in ("mock-teacher-x", "mock-teacher-y"):
        pilot(config, "label", "--role", "teacher_candidate", "--backend", "mock",
              "--model", teacher)
    pilot(config, "ensemble")
    ids = run_ids(config)
    scores = {}
    for model in ("mock-small", "mock-teacher-x", "mock-teacher-y", "mock-ensemble"):
        pilot(config, "check", "--run", ids[model])
        scores[model] = pilot(config, "score", "--run", ids[model])
    settings = load_settings(config)
    write_json(settings.analysis_dir / "perf" / "mock-small.json",
               {"model_id": "mock-small", "chunks_per_min": 12.0, "latency_p95_ms": 900.0,
                "peak_rss_mb": 2400.0})
    write_json(settings.analysis_dir / "perf" / "frontier.json",
               {"model_id": "mock-b", "chunks_per_min": 2.0, "note": "test"})
    decision = pilot(config, "decide")
    assert decision["decision"] == "go"
    assert decision["finetuning"]["status"] == "required"  # ratio a 0.735 < 0.85
    # mock-teacher-y copies a reference with one near-miss quote; mock-teacher-x copies mock-small.
    assert scores["mock-teacher-y"]["repaired"]["composite"] > scores["mock-teacher-y"]["composite"]
    assert scores["mock-teacher-y"]["repaired"]["repair_stats"]["repaired"] == 1
    fitness = decision["teacher_fitness"]
    assert {r["model_id"]: r["fit"] for r in fitness["candidates"]} == {
        "mock-teacher-x": False, "mock-teacher-y": True, "mock-ensemble": False}
    assert fitness["recommended"] == "mock-teacher-y"
    result = pilot(config, "report")
    text = (settings.reports_dir / "mini-v1" / "report.md").read_text()
    for section in SECTIONS:
        assert section in text
    assert "Test-only benchmark" in text
    assert "### Teacher fitness (FR-031a)" in text
    assert "Recommended teacher: **mock-teacher-y**." in text
    assert "- `mock-teacher-x` misses: " in text and "schema_valid 0.800 < 0.98" in text
    assert "`mock-ensemble` is the offline ensemble (FR-019b)" in text
    assert "| mock-teacher-y | 0.985 | 1.000 | 1.000 | 1.000 | 0.857 | 1 / 0 | 0.000 | fit |" in text
    assert "accuracy" not in text.lower()
    assert result["figure"] and (settings.reports_dir / "mini-v1" / "figures" / "pareto.png").exists()


def test_decide_sets_revise_and_unlocks_holdout(tmp_path):
    config = copy_fixture(tmp_path)
    crit = config.parent / "decision-criteria.yaml"
    crit.write_text(crit.read_text().replace("kind_kappa: 0.6", "kind_kappa: 0.9"))
    reference_chain(config)
    pilot(config, "agreement")
    assert pilot(config, "decide")["decision"] == "revise"
    manifest = pilot(config, "freeze", "--new-version", "mini-v2", "--rationale", "revise kind")
    assert manifest["reruns"] == 1 and manifest["pilot_state"] == "revise"
