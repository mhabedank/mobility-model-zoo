import shutil
from datetime import date

import pytest

from mobility_model_zoo.productdev.jtbd.config import load_settings
from mobility_model_zoo.productdev.jtbd.corpus.build import build_from_selection
from mobility_model_zoo.productdev.jtbd.corpus.redact import redact_check, redact_text
from mobility_model_zoo.productdev.jtbd.corpus.split import balance_flag, stratified_holdout
from mobility_model_zoo.productdev.jtbd.corpus.store import load_chunks, save_chunk
from mobility_model_zoo.productdev.jtbd.corpus.validate import check_targets
from mobility_model_zoo.productdev.jtbd.errors import ValidationFailed
from mobility_model_zoo.productdev.jtbd.schema import ChunkRecord


@pytest.fixture
def settings(tmp_path, fixture_dir):
    work = tmp_path / "mini"
    shutil.copytree(fixture_dir, work)
    return load_settings(work / "pilot.yaml")


def test_redaction_removes_identifiers():
    text = ("Danke u/Bahnfahrer_92 und @mobil_blog! Schreib an max.muster@example.de oder "
            "Tel.: 0171 1234567, +49 30 1234 5678. Profil: https://www.reddit.com/user/abc123 "
            "In 2023 stieg die Nutzung um 12,5 %.")
    out, counts = redact_text(text)
    for leaked in ("Bahnfahrer_92", "mobil_blog", "max.muster", "1234567", "5678", "abc123"):
        assert leaked not in out
    assert "In 2023 stieg die Nutzung um 12,5 %." in out
    assert counts["email"] == 1
    out, _ = redact_text("Corresponding Author: Dr . J. Gruber , johannes.gruber@dlr .de   discussed")
    assert "gruber@" not in out and "[EMAIL]" in out


def test_redact_check_fails_on_residual_and_missing_review(settings):
    chunk = load_chunks(settings)[0]
    chunk.text += " Frag u/someuser dazu."
    save_chunk(settings, chunk)
    with pytest.raises(ValidationFailed, match="reddit_user"):
        redact_check(settings)
    chunk.text = chunk.text.replace(" Frag u/someuser dazu.", "")
    chunk.redaction.manual_review_at = None
    save_chunk(settings, chunk)
    with pytest.raises(ValidationFailed, match="no_manual_review"):
        redact_check(settings)


def test_split_is_reproducible_and_stratified():
    keys = {f"ch-{i:03d}": ("a" if i < 60 else "b", "paper", "de") for i in range(100)}
    first = stratified_holdout(keys, 10, seed=1)
    assert first == stratified_holdout(keys, 10, seed=1)
    assert len(first) == 10
    assert sum(1 for k in first if int(k[3:]) < 60) == 6


def _chunk(i, **kw):
    base = dict(chunk_id=f"ch-{i:03d}", snapshot_id="snap-000000000000", ranges=[(0, 10)],
                text="x" * 2000, token_count=500, split="main", sub_area="logistics_delivery",
                source_type="paper", region="DACH", country="DE", language="de",
                date=date(2025, 1, 1), license="CC-BY-4.0", relevance_intent="relevant",
                redaction={"patterns_version": "v", "manual_review_at": None,
                           "check_passed": False})
    base.update(kw)
    return ChunkRecord.model_validate(base)


TARGETS = {
    "main_size": [10, 10], "holdout_size": [0, 0], "sub_area_share_of_relevant": [0.15, 0.25],
    "source_type_share": [0.18, 0.32], "irrelevant_or_near_miss_share": [0.15, 0.25],
    "non_eu_share": [0.10, 0.15], "dach_largest_region": True, "language_min_share": 0.35,
    "token_range": [300, 1500],
}


def test_validate_reports_each_target():
    chunks = [_chunk(i) for i in range(9)] + [_chunk(9, token_count=2000)]
    _, failures = check_targets(chunks, TARGETS, "main", [])
    joined = " | ".join(failures)
    for fragment in ("sub_area public_transport_rural", "source_type reddit",
                     "irrelevant/near-miss", "non-EU", "language en", "ch-009 has 2000 tokens"):
        assert fragment in joined


def test_substitution_needs_explanation():
    chunks = [_chunk(i) for i in range(10)]
    _, failures = check_targets(chunks, TARGETS, "main",
                                [{"source_type": "reddit", "replaced_by": "forum_review"}])
    assert any("lacks an explanation" in f for f in failures)


def test_build_cuts_ranges_from_snapshot(settings, tmp_path):
    snap = load_chunks(settings)[3].snapshot_id
    sel = tmp_path / "selection.yaml"
    sel.write_text(
        f"chunks:\n  - chunk_id: ch-099\n    snapshot_id: {snap}\n    ranges: [[0, 10], [20, 40]]\n"
        "    sub_area: car_ownership_use\n    region: DACH\n    country: DE\n    language: de\n"
        "    date: 2026-01-01\n    relevance_intent: relevant\n"
    )
    result = build_from_selection(settings, sel)
    assert result["built"] == 1
    chunk = {c.chunk_id: c for c in load_chunks(settings)}["ch-099"]
    assert chunk.source_type == "reddit" and "\n\n" in chunk.text
    assert chunk.redaction.check_passed is False


def test_balance_flag_swaps_within_a_stratum_only():
    keys = {f"c{i}": ("a",) for i in range(6)} | {f"d{i}": ("b",) for i in range(4)}
    flagged = {"c4", "c5", "d3", "d2"}  # 4 of 10 -> 2 of a holdout of 5
    picked = balance_flag({"c0", "c1", "c2", "d0", "d1"}, keys, flagged, 5)
    assert len(picked) == 5 and len(picked & flagged) == 2
    assert sum(keys[c] == ("a",) for c in picked) == 3  # strata sizes unchanged
