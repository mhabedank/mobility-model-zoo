"""Redaction recall on the synthetic set (D9) and Art. 9 lexicon flags."""

from mobility_model_zoo.compliance import recall
from mobility_model_zoo.compliance.scan import art9_flags, pii


def test_combined_recall_meets_d9():
    result = recall.measure(recall.load())
    assert result["items"] == 300
    assert result["recall"]["combined"] >= 0.95


def test_issn_is_not_a_phone_number():
    assert not pii("Bundesanzeiger Verlag, ISSN 0722-8333")


def test_art9_flags_count_terms_not_party_names():
    lexicon = {"religion": ["religiös", "moschee"], "health": ["rollstuhl"]}
    assert art9_flags("Die Christlich Demokratische Union stimmt zu.", lexicon) == {}
    assert art9_flags("Als Rollstuhlfahrerin komme ich nicht in den Bus.", lexicon) == {"health": 1}
