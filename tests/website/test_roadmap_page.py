"""The roadmap page (feature 015, US1, contracts/pages.md)."""

from __future__ import annotations

import re

RECORD = "zoo/roadmap/roadmap.yaml"


def entries(html: str) -> list[tuple[str, str]]:
    """(entry id, class) of every roadmap card, in page order."""
    return re.findall(r'<li class="entry (entry-\w+)" id="([^"]+)"', html)[::1]


def test_roadmap_page(built):
    html = built.html("roadmap/index.html")
    assert html.count("<h1") == 1 and '<html lang="en">' in html
    assert "A plan, not a commitment. As of 12 October 2026." in html
    labels = [m for m in re.findall(r'<h2 class="h3" id="h-[^"]+">([^<]+)</h2>', html)]
    assert labels == ["Q4 2026", "H1 2027", "H2 2027"]
    assert [i for _, i in entries(html)] == [
        "picket-forest",
        "scout-large-reader-test",
        "hum-bearing",
        "picket-signal",
    ]


def test_cards(built):
    html = built.html("roadmap/index.html")
    classes = dict((i, c) for c, i in entries(html))
    assert classes["scout-large-reader-test"] == "entry-update"
    assert classes["picket-forest"] == classes["hum-bearing"] == "entry-new"
    update = html[html.index('id="scout-large-reader-test"') :]
    update = update[: update.index("</li>")]
    assert 'href="../models/scout-large/"' in update and "Update of scout-large" in update
    first = html[html.index('id="picket-forest"') :]
    first = first[: first.index("</li>")]
    assert "<a " not in first and "First release" in first and "In progress" in first
    working = html[html.index('id="hum-bearing"') :]
    working = working[: working.index("</li>")]
    assert "(working name)" in working and "Waits for: Data licence to be confirmed" in working
    assert "New model" in working and "Planned" in working


def test_empty_horizon(site_env):
    site_env.edit_yaml(
        RECORD,
        lambda r: r.update(entries=[e for e in r["entries"] if e["horizon"] != "2027-Q3..Q4"]),
    )
    site_env.build()
    html = site_env.html("roadmap/index.html")
    assert html.count("Nothing planned yet.") == 1


def test_no_extra_scripts(built):
    html = built.html("roadmap/index.html")
    assert re.findall(r"<script[^>]*>", html) == ['<script src="../assets/js/site.js" defer>']


def test_navigation_links_roadmap(built):
    for page in ("index.html", "roadmap/index.html", "quickstart/index.html"):
        if (built.out / page).exists():
            assert ">Roadmap</a>" in built.html(page)


def test_moved_entry_changes_column_only(site_env):
    def move(r):
        e = next(e for e in r["entries"] if e["id"] == "hum-bearing")
        e["horizon"] = "2027-Q3..Q4"
        e["moves"] = [{"date": "2026-10-12", "to": "2027-Q3..Q4", "reason": "Waiting for data."}]

    site_env.edit_yaml(RECORD, move)
    site_env.build()
    html = site_env.html("roadmap/index.html")
    h2 = html[html.index('id="h-2027-Q3..Q4"') :]
    assert 'id="hum-bearing"' in h2
    assert [i for _, i in entries(html)][-2:] == ["hum-bearing", "picket-signal"]
