"""Quickstart of a microcontroller model: snippet output and own-data step (feature 013)."""

from __future__ import annotations

import json
from pathlib import Path

from site_fixture import MODEL, VERSION

from mobility_model_zoo.release import card as cards
from mobility_model_zoo.site import examples
from mobility_model_zoo.site.build import environment

LATEST = {"version": "0.2.1"}


def _page(**changes):
    page = {
        "hardware_note": "Needs a host with Python.",
        "usage": {"class": "commercial", "text": "Commercial use permitted."},
        "latest": LATEST,
        "python_requirement": "Python 3.12 or newer",
        "install": 'pip install "mobility-model-zoo[edge] @ git+https://x/y@picket-forest/v0.2.1"',
        "how_to_run": "print(1)",
        "run_output": None,
        "own_data": "",
        "quick": None,
    }
    return {**page, **changes}


def render(**changes) -> str:
    return (
        environment()
        .get_template("partials/quickstart.html.j2")
        .render(p=_page(**changes), root="../../")
    )


def test_snippet_output_is_shown_when_the_card_has_one():
    html = render(run_output="3000 frames, 3.00 s; 1 alarm at frame 1155")
    assert "Get this output" in html and "3000 frames, 3.00 s; 1 alarm at frame 1155" in html
    assert "recorded by the release gate in a fresh environment" in html


def test_no_output_step_without_output_or_example():
    assert "Get this output" not in render()


def test_own_data_step_only_when_declared():
    assert "Use it on your own data" not in render()
    html = render(own_data="table = pf.calibrate(benign)")
    assert "Use it on your own data" in html and "table = pf.calibrate(benign)" in html


def test_python_requirement_stays_next_to_the_install_line():
    html = render()
    assert html.index("Requires Python 3.12 or newer.") < html.index("qs-install")


# ---- run_output(): the published card, cached like the example outputs ----------------------------


def _publish_card(site_env, monkeypatch, card: str):
    import hashlib

    record = site_env.reg.record_raw(MODEL, VERSION)
    body = card.encode("utf-8")
    sha = hashlib.sha256(body).hexdigest()
    site_env.edit_yaml(
        f"zoo/models/{MODEL}/releases/{VERSION}.yaml",
        lambda r: r["published"].update(card_sha256=sha),
    )
    monkeypatch.setattr(examples, "_download_card", lambda repo, revision: body)
    return record["published"]["repo_commit"], sha


CARD = "## How to run it\n\nOutput:\n\n```text\n3 frames, 1 alarm\n```\n\n## Examples\n"


def test_run_output_is_read_from_the_published_card_and_cached(site_env, monkeypatch):
    commit, sha = _publish_card(site_env, monkeypatch, CARD)
    assert examples.run_output(site_env.reg, MODEL, VERSION) == "3 frames, 1 alarm"
    cache = Path(site_env.root) / ".cache" / "site" / MODEL / f"{VERSION}.run.json"
    assert json.loads(cache.read_text())["card_sha256"] == sha
    monkeypatch.setattr(
        examples, "_download_card", lambda *a: (_ for _ in ()).throw(AssertionError("net"))
    )
    assert examples.run_output(site_env.reg, MODEL, VERSION) == "3 frames, 1 alarm"  # from the cache


def test_run_output_offline_without_cache_is_none(site_env, monkeypatch):
    _publish_card(site_env, monkeypatch, CARD)
    assert examples.run_output(site_env.reg, MODEL, VERSION, offline=True) is None


def test_run_output_refuses_a_card_that_does_not_match_its_hash(site_env, monkeypatch):
    import pytest

    from mobility_model_zoo.release.errors import GateFailed

    _publish_card(site_env, monkeypatch, CARD)
    monkeypatch.setattr(examples, "_download_card", lambda repo, revision: b"another card")
    with pytest.raises(GateFailed, match="card hash"):
        examples.run_output(site_env.reg, MODEL, VERSION)


def test_card_without_output_gives_none(site_env, monkeypatch):
    _publish_card(site_env, monkeypatch, "## How to run it\n\nno output\n")
    assert examples.run_output(site_env.reg, MODEL, VERSION) is None
    assert cards.parse_card_run_output("## Other\n\nOutput:\n\n```text\nx\n```\n") is None
