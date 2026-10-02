"""`jtbd span data-check`: provenance violations and composition report (T022)."""

import pytest
from helpers import pilot
from span_helpers import make_snapshot, prose, snapshot_map, span_train_env, write_train_chunks

from mobility_model_zoo.productdev.jtbd.config import load_settings
from mobility_model_zoo.productdev.jtbd.jsonio import read_json


def reviewed(train):
    pilot(train, "corpus", "review-sample", "--seed", "1")
    pilot(train, "corpus", "mark-reviewed", "--all")
    pilot(train, "corpus", "redact-check")


@pytest.fixture
def env(tmp_path):
    _, train = span_train_env(tmp_path, composition_targets={
        "min_share_per_language": {"en": 0.3}, "min_offtopic_share": 0.15,
        "min_source_types": 3})
    return train, load_settings(train)


def test_clean_dataset_passes_and_reports_composition(env, tmp_path):
    train, settings = env
    snaps = [make_snapshot(settings, f"https://example.net/report-{n}", prose(f"r{n}", 8000))
             for n in range(3)]
    pilot(train, "corpus", "autochunk", "--map", str(snapshot_map(tmp_path / "m.yaml", snaps)),
          "--train", "4", "--eval", "0", "--seed", "1")
    reviewed(train)
    out = pilot(train, "span", "data-check")
    assert out["violations"] == {"not_training_allowed": 0, "shared_with_benchmark": 0,
                                 "spike_data": 0, "redaction_not_passed": 0}
    assert sum(s["count"] for s in out["sources"]) == out["chunks"] == 4
    assert {s["permitted_use"] for s in out["sources"]} == {"training_allowed"}
    comp = out["composition"]
    assert comp["language_share"] == {"en": 1.0}
    assert comp["targets_met"]["language_en"] is True
    assert comp["targets_met"]["source_types"] is False  # one source type only: reported
    saved = read_json(settings.data_dir / "analysis" / "provenance.json")
    assert saved["violating_chunks"] == []


def test_violations_fail_and_are_recorded(env):
    train, settings = env
    bench_only = make_snapshot(settings, "https://example.net/bench-only", prose("b"),
                               permitted="benchmark_only")
    write_train_chunks(settings, [("snap-53d0c1790348", "en", "paper"),
                                  (bench_only, "de", "paper")])
    reviewed(train)
    pilot(train, "span", "data-check", expect=1)
    saved = read_json(settings.data_dir / "analysis" / "provenance.json")
    assert saved["violations"]["shared_with_benchmark"] == 1
    assert saved["violations"]["not_training_allowed"] == 1
    assert {c["chunk_id"] for c in saved["violating_chunks"]} == {"ch-001", "ch-002"}


def test_unredacted_chunks_fail(env):
    train, settings = env
    snap = make_snapshot(settings, "https://example.net/fresh", prose("f"))
    write_train_chunks(settings, [(snap, "en", "paper")])
    pilot(train, "span", "data-check", expect=1)
    saved = read_json(settings.data_dir / "analysis" / "provenance.json")
    assert saved["violations"]["redaction_not_passed"] == 1
