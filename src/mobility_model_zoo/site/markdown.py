"""Markdown fields of `model.yaml` and release records as HTML (research R12): CommonMark with raw
HTML disabled, so metadata can never inject markup into the site."""

from __future__ import annotations

from markdown_it import MarkdownIt
from markupsafe import Markup

_MD = MarkdownIt("commonmark", {"html": False})


def md(text: str | None) -> Markup:
    return Markup(_MD.render(text or ""))  # noqa: S704 - markdown-it escapes raw HTML (html=False)
