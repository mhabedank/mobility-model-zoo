from helpers import copy_fixture, pilot, reference_chain, run_ids

from jtbd_pilot.config import load_settings
from jtbd_pilot.jsonio import write_json

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
    run = run_ids(config)["mock-small"]
    pilot(config, "check", "--run", run)
    pilot(config, "score", "--run", run)
    settings = load_settings(config)
    write_json(settings.analysis_dir / "perf" / "mock-small.json",
               {"model_id": "mock-small", "chunks_per_min": 12.0, "latency_p95_ms": 900.0,
                "peak_rss_mb": 2400.0})
    write_json(settings.analysis_dir / "perf" / "frontier.json",
               {"model_id": "mock-b", "chunks_per_min": 2.0, "note": "test"})
    decision = pilot(config, "decide")
    assert decision["decision"] == "go"
    assert decision["finetuning"]["status"] == "required"  # ratio a 0.735 < 0.85
    result = pilot(config, "report")
    text = (settings.reports_dir / "mini-v1" / "report.md").read_text()
    for section in SECTIONS:
        assert section in text
    assert "Test-only benchmark" in text
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
