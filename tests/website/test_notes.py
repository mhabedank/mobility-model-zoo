"""Field notes (feature 022): the content loader and the two guards that stop the build.

The guards are the point of the format. A reference list that drifts away from the text it claims
to support is worse than none, because it looks sourced, so a citation without an entry and an
entry without a citation both have to fail loudly (contracts N1), and a drawing that is not there
has to say so rather than raise a file-not-found traceback (N2).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mobility_model_zoo.site import notes

FRONT = """---
title: A note
description: One line about it.
date: 2026-10-22
author: Someone
licence: CC-BY-4.0
licence_label: CC BY 4.0
licence_url: https://example.invalid/licence
{extra}---

{body}
"""


def write(root: Path, body: str, extra: str = "", name: str = "01-a-note.md") -> Path:
    folder = root / notes.DIR
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_text(FRONT.format(extra=extra, body=body), encoding="utf-8")
    return path


def diagram(root: Path, name: str = "sketch") -> None:
    folder = root / notes.DIR / notes.DIAGRAMS
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10" role="img" '
        'aria-labelledby="t"><title id="t">A sketch</title><desc>A sketch.</desc>'
        '<rect width="10" height="10" fill="var(--bg)"/></svg>',
        encoding="utf-8",
    )


REFS = """references:
- id: one
  text: 'First, A. (2020). A work.'
- id: two
  text: 'Second, B. (2021). Another work.'
"""


def test_a_citation_without_an_entry_names_the_note_and_the_id(tmp_path: Path) -> None:
    write(tmp_path, "A claim.[ref:missing]")
    with pytest.raises(ValueError) as e:
        notes.posts(tmp_path)
    assert "missing" in str(e.value)
    assert "01-a-note.md" in str(e.value)


def test_an_entry_that_is_never_cited_names_the_unused_id(tmp_path: Path) -> None:
    write(tmp_path, "A claim with no citation.", extra=REFS)
    with pytest.raises(ValueError) as e:
        notes.posts(tmp_path)
    assert "one" in str(e.value)
    assert "two" in str(e.value)


def test_numbers_follow_first_use_and_a_repeat_keeps_its_number(tmp_path: Path) -> None:
    # `two` is cited first, so it is reference one, and the second mention of it reuses the number.
    write(tmp_path, "Second claim.[ref:two] First claim.[ref:one] Again.[ref:two]", extra=REFS)
    note = notes.posts(tmp_path)[0]
    assert [(r["id"], r["number"]) for r in note["references"]] == [("two", 1), ("one", 2)]
    assert note["body"].count('href="#ref-two"') == 2
    assert ">1</a>" in note["body"]


def test_a_missing_drawing_is_a_named_failure_not_a_traceback(tmp_path: Path) -> None:
    write(tmp_path, "Before.\n\n[diagram:nowhere]\n\nAfter.")
    with pytest.raises(ValueError) as e:
        notes.posts(tmp_path)
    assert "nowhere" in str(e.value)
    assert "01-a-note.md" in str(e.value)


def test_a_file_without_front_matter_names_the_file(tmp_path: Path) -> None:
    folder = tmp_path / notes.DIR
    folder.mkdir(parents=True)
    (folder / "01-bare.md").write_text("Just prose.\n", encoding="utf-8")
    with pytest.raises(ValueError) as e:
        notes.posts(tmp_path)
    assert "01-bare.md" in str(e.value)


def test_a_note_without_a_lead_image_renders_without_an_empty_figure(tmp_path: Path) -> None:
    write(tmp_path, "Body text.")
    note = notes.posts(tmp_path)[0]
    assert note.get("lead_image") is None
    html = render(note, lead=None)
    assert "<figure" not in html


def test_a_note_without_references_renders_without_an_empty_section(tmp_path: Path) -> None:
    write(tmp_path, "Body text with no citation.")
    note = notes.posts(tmp_path)[0]
    assert note["references"] == []
    html = render(note, lead=None)
    assert "References" not in html


def test_a_diagram_is_written_into_the_page_rather_than_linked(tmp_path: Path) -> None:
    diagram(tmp_path)
    write(tmp_path, "Before.\n\n[diagram:sketch]\n\nAfter.")
    note = notes.posts(tmp_path)[0]
    assert "<svg" in note["body"]
    assert "sketch.svg" not in note["body"]


def render(note: dict, lead: dict | None) -> str:
    """The note page as the site would render it, without building the whole site."""
    from mobility_model_zoo.site.build import environment

    site = {
        "title": "Zoo",
        "tagline": "t",
        "canonical_url": "https://example.invalid/",
        "repo": "https://example.invalid/repo",
        "hf_org": "https://example.invalid/hf",
        "legal": {"imprint": "https://example.invalid/i", "privacy": "https://example.invalid/p",
                  "copyright": "https://example.invalid/c"},
    }
    card = {"file": "x.png", "alt": "x", "labels": []}
    return environment().get_template("note.html.j2").render(
        site=site, root="../../", path="notes/a-note/", card=card,
        has_images=False, has_notes=True, page_images=[], post=note, lead=lead,
    )


def test_a_planned_part_has_no_address_and_a_published_one_is_linked(tmp_path: Path) -> None:
    write(tmp_path, "Body.", name="01-a-note.md")
    (tmp_path / notes.DIR / notes.SERIES).write_text(
        "id: s\ntitle: A series\nintro: What it is for.\n"
        "parts:\n"
        "- part: 1\n  slug: a-note\n  title: First\n  text: One line.\n"
        "- part: 2\n  title: Second\n  text: Another line.\n",
        encoding="utf-8",
    )
    found = notes.posts(tmp_path)
    parts = notes.series(tmp_path, found)["parts"]
    assert parts[0]["published"] is True
    assert parts[0]["href"] == "notes/a-note/"
    assert parts[0]["date"] == "2026-10-22"
    assert parts[1]["published"] is False
    assert parts[1]["href"] is None
