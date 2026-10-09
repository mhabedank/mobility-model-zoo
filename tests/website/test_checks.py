"""Static checks of the built site: links, third-party resources, size, language (checks.md)."""

from __future__ import annotations

from mobility_model_zoo.site import check


def test_built_site_passes_the_static_checks(built):
    assert list(check.check_links(built.out)) == []
    assert list(check.check_resources(built.out)) == []
    assert list(check.check_size(built.out)) == []
    assert list(check.check_language(built.out)) == []
    assert list(check.check_wording(built.out)) == []


def test_third_party_font_is_p1(built):
    path = built.out / "index.html"
    path.write_text(
        path.read_text().replace(
            "</head>",
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter"></head>',
        )
    )
    css = built.out / "assets" / "css" / "site.css"
    css.write_text(css.read_text() + '\n@import "https://cdn.example.org/x.css";\n')
    found = {f[2] for f in check.check_resources(built.out)}
    assert any("fonts.googleapis.com" in f for f in found) and any("cdn.example.org" in f for f in found)


def test_broken_internal_link_and_anchor_are_l1(built):
    path = built.out / "index.html"
    path.write_text(
        path.read_text().replace(
            "</main>", '<a href="models/nope/">x</a><a href="#nowhere">y</a></main>'
        )
    )
    details = [f[2] for f in check.check_links(built.out)]
    assert any("models/nope/" in d for d in details) and any("nowhere" in d for d in details)


def test_accuracy_wording_is_f3(built):
    path = built.out / "index.html"
    path.write_text(path.read_text().replace("</main>", "<p>It reaches an accuracy of 0.72.</p></main>"))
    assert [f[0] for f in check.check_wording(built.out)] == ["F3"]


def test_undeferred_script_is_s1(built):
    path = built.out / "index.html"
    path.write_text(path.read_text().replace(" defer>", ">"))
    assert any(f[0] == "S1" and "deferred" in f[2] for f in check.check_size(built.out))
