"""The /quickstart/ page: filled from the registry and linked from other pages (feature 013)."""

from __future__ import annotations

import html

import pytest
from site_fixture import MODEL, VERSION

from mobility_model_zoo.release.errors import GateFailed


def page(built) -> str:
    return html.unescape(built.html("quickstart/index.html"))


def test_install_line_and_program_come_from_the_registry(built):
    text = page(built)
    assert (
        f'uv pip install "mobility-model-zoo[text] @ git+https://github.com/mhabedank/mobility-model-zoo@{MODEL}/v{VERSION}"'
        in text
    )
    assert f'SpanExtractor.from_pretrained("mobility-model-zoo/{MODEL}", revision="v{VERSION}")' in text
    assert "{install:" not in text and "{snippet:" not in text


def test_the_pitfalls_are_named(built):
    text = page(built)
    for symptom in (
        "No module named pip",
        "IPython shows another Python version",
        "command not found: from",
    ):
        assert symptom in text


def test_the_page_is_linked_from_the_start_page_and_model_pages(built):
    assert 'href="quickstart/"' in built.html("index.html")
    assert 'href="../../quickstart/"' in built.html(f"models/{MODEL}/index.html")


def test_a_model_without_a_published_version_fails_the_build(site_env):
    path = site_env.root / "docs" / "quickstart.md"
    path.write_text(path.read_text() + "\n```bash\nuv {install:picket-forest}\n```\n")
    with pytest.raises(GateFailed, match="Q1.*picket-forest"):
        site_env.build()


def test_no_quickstart_document_no_page(site_env):
    (site_env.root / "docs" / "quickstart.md").unlink()
    site_env.build()
    assert not (site_env.out / "quickstart").exists()
