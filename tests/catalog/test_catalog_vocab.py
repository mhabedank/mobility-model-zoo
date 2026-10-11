"""Vocabularies of the catalog (feature 009, FR-006, FR-023, T013)."""

from __future__ import annotations

from pathlib import Path

import yaml

from mobility_model_zoo.catalog.model import VOCAB_DIR, vocab

REPO = Path(__file__).resolve().parents[2]


def test_every_vocabulary_is_versioned_with_a_changelog():
    for path in VOCAB_DIR.glob("*.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(data.get("version"), int), path.name
        assert data.get("changelog"), path.name
        for change in data["changelog"]:
            assert {"date", "change", "reason"} <= change.keys(), path.name


def test_targets_are_the_34_languages_of_fr_023():
    v = vocab()
    assert len(v.targets) == 34 == len(set(v.targets))
    assert set(v.targets) <= set(v.languages)
    assert {"zxx", "und"} <= set(v.languages)
    assert all(isinstance(code, str) for code in v.languages)
    assert "NO" in v.countries and "001" in v.regions and "EU" in v.regions


def test_topics_mirror_zoo_topics_without_sandbox():
    topics = yaml.safe_load((REPO / "zoo" / "topics.yaml").read_text(encoding="utf-8"))["topics"]
    assert vocab().topics == [t["id"] for t in topics if t["id"] != "sandbox"]


def test_every_genre_belongs_to_exactly_one_modality():
    seen: dict[str, str] = {}
    for modality, spec in vocab().modalities.items():
        assert spec["dcmi"]
        for genre in spec["genres"]:
            assert genre not in seen, f"{genre} in {seen.get(genre)} and {modality}"
            seen[genre] = modality
    assert set(vocab().modalities) == {"text", "audio", "video", "image", "graphic", "structured_data"}


def test_base_model_list_misses_maltese_only():
    from mobility_model_zoo.catalog.reports import base_models

    xlmr = base_models()["FacebookAI/xlm-roberta-large"]
    assert [t for t in vocab().targets if t not in xlmr] == ["mt"]
