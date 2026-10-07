"""Sampled manual review with an identifier scan for training datasets (T020, research R4)."""

import pytest
from helpers import copy_fixture, pilot
from span_helpers import span_train_env, write_train_chunks

from mobility_model_zoo.productdev.jtbd.config import load_settings
from mobility_model_zoo.productdev.jtbd.corpus.store import chunk_map
from mobility_model_zoo.productdev.jtbd.jsonio import read_json

SPECS = [("snap-000000000001", "de", "paper"), ("snap-000000000002", "de", "paper"),
         ("snap-000000000003", "en", "paper"), ("snap-000000000004", "en", "paper"),
         ("snap-000000000005", "en", "transcript"), ("snap-000000000006", "de", "forum_review")]


@pytest.fixture
def train(tmp_path):
    _, train = span_train_env(tmp_path)
    write_train_chunks(load_settings(train), SPECS)
    return train


def test_sample_is_stratified_plus_always_review_and_drawn_once(train):
    out = pilot(train, "corpus", "review-sample", "--seed", "3")
    sample = read_json(load_settings(train).chunks_dir / "review-sample.json")
    assert len(sample["sampled"]) == 3  # max(min 2, ceil(0.5 x 6))
    assert sample["always_review"] == ["ch-006"]
    assert set(sample["chunk_ids"]) == set(sample["sampled"]) | {"ch-006"}
    languages = {SPECS[int(c[3:]) - 1][1] for c in sample["sampled"]}
    assert languages == {"de", "en"}, "round-robin over strata covers both languages"
    assert out["to_review"] == len(sample["chunk_ids"])
    pilot(train, "corpus", "review-sample", "--seed", "4", expect=1)


def test_redact_check_needs_review_of_the_sample_only(train):
    pilot(train, "corpus", "redact-check", expect=1)  # no sample yet
    pilot(train, "corpus", "review-sample", "--seed", "3")
    pilot(train, "corpus", "redact-check", expect=1)  # sample not reviewed yet
    to_review = read_json(load_settings(train).chunks_dir / "review-sample.json")["chunk_ids"]
    pilot(train, "corpus", "mark-reviewed", *to_review)
    out = pilot(train, "corpus", "redact-check")
    assert out == {"checked": 6, "passed": 6, "reviewed_by_hand": len(to_review)}
    assert all(c.redaction.check_passed for c in chunk_map(load_settings(train)).values())


def test_identifier_scan_runs_on_every_chunk(tmp_path):
    _, train = span_train_env(tmp_path)
    settings = load_settings(train)
    write_train_chunks(settings, SPECS[:2], text="Mehr unter https://forum.example.org/members/"
                       "hans_m zum Thema Bus. " * 3)
    pilot(train, "corpus", "review-sample", "--seed", "1")
    pilot(train, "corpus", "mark-reviewed", "--all")
    pilot(train, "corpus", "redact-check", expect=1)


def test_pilot_config_still_requires_review_of_every_chunk(tmp_path):
    config = copy_fixture(tmp_path)
    pilot(config, "corpus", "review-sample", "--seed", "1", expect=2)
