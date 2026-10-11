"""Harvester search terms (feature 009 research R6): every target language searches in its own words."""

from __future__ import annotations

from mobility_model_zoo.catalog.harvest import base
from mobility_model_zoo.catalog.model import vocab


def test_every_target_language_has_its_own_terms_for_every_subdomain():
    """Batch 1 (2026-10-11) searched 20 languages with English terms because terms were missing."""
    terms = base.terms()
    assert set(terms) == set(vocab().subdomains)
    missing = [
        f"{subdomain}/{lang}"
        for subdomain, by_lang in terms.items()
        for lang in vocab().targets
        if not by_lang.get(lang)
    ]
    assert missing == []


def test_terms_are_short_non_empty_phrases():
    # up to 6 words: Vietnamese writes every syllable as a word
    for subdomain, by_lang in base.terms().items():
        for lang, phrases in by_lang.items():
            assert 1 <= len(phrases) <= 4, f"{subdomain}/{lang}"
            assert all(isinstance(p, str) and p.strip() and len(p.split()) <= 6 for p in phrases), (
                f"{subdomain}/{lang}"
            )
