"""Forum threads: every post's text, no author names, no duplicated quotes (snapshot extraction)."""

from mobility_model_zoo.productdev.jtbd.sources.snapshot import extract_text, forum_posts

PAGE = """<html><body>
<div id="p1"><span class="username">alice</span>
  <div class="content">Der Bus kommt abends nicht mehr.<br>Ich fahre deshalb Auto.</div></div>
<div id="p2"><span class="username">bob</span>
  <div class="content"><blockquote><cite>alice schrieb:</cite>
  Der Bus kommt abends nicht mehr.</blockquote>
  Bei uns genauso, seit 2023.</div></div>
<div id="p3"><span class="username">carol</span>
  <div class="content"><blockquote>Sehr geehrte Damen und Herren, wann kommt die Ladesäule?</blockquote>
  Das habe ich der Stadt geschrieben.</div></div>
</body></html>"""


def test_posts_are_extracted_without_names_and_duplicate_quotes():
    text = forum_posts(PAGE)
    posts = text.split("\n\n")
    assert len(posts) == 3
    assert posts[0] == "Der Bus kommt abends nicht mehr.\nIch fahre deshalb Auto."
    assert posts[1] == "Bei uns genauso, seit 2023."  # the quote of post 1 is dropped
    assert "Sehr geehrte Damen und Herren" in posts[2]  # a quote from outside the page is kept
    assert not any(name in text for name in ("alice", "bob", "carol"))


def test_non_forum_pages_fall_back():
    assert forum_posts("<html><body><p>Ein Artikel.</p></body></html>") is None
    assert extract_text(PAGE.encode(), "html").startswith("Der Bus kommt")


def test_regulations_comment_keeps_only_the_comment_text():
    import json

    from mobility_model_zoo.productdev.jtbd.sources.snapshot import regulations_comment

    doc = {"data": {"attributes": {"title": "Jane Doe - Comments", "firstName": "Jane",
                                   "comment": "I drive 11 hours a day.<br/>Parking is full by 6 pm."}}}
    text = regulations_comment(json.dumps(doc).encode())
    assert text == "I drive 11 hours a day.\nParking is full by 6 pm."
    assert regulations_comment(b'{"data": []}') is None


def test_truncated_previews_are_dropped():
    page = """<div class="comment__text">Sammeltaxis sind beliebt. In der Praxis […]
    Weiterlesen</div>
    <div class="comment__text">Sammeltaxis sind beliebt. In der Praxis sind es Taxifahrten.</div>
    <div class="comment__text">Ein zweiter Kommentar.</div>"""
    assert forum_posts(page).split("\n\n") == [
        "Sammeltaxis sind beliebt. In der Praxis sind es Taxifahrten.", "Ein zweiter Kommentar."]


def test_toggle_posts_keep_the_full_text_and_repeated_notices_go():
    page = """<div class="comment__text">Sammeltaxis sind beliebt. […]<br>Weiterlesen<br>
    Sammeltaxis sind beliebt. In der Praxis sind es Taxifahrten.<br>Einklappen</div>
    <div class="comment__text">Bitte beachten Sie die Netiquette.</div>
    <div class="comment__text">Ein zweiter Kommentar.</div>
    <div class="comment__text">Bitte beachten Sie die Netiquette.</div>"""
    assert forum_posts(page).split("\n\n") == [
        "Sammeltaxis sind beliebt. In der Praxis sind es Taxifahrten.", "Ein zweiter Kommentar."]


def test_lemmy_comment_list_without_names_quotes_or_deleted():
    import json

    from mobility_model_zoo.productdev.jtbd.sources.snapshot import extract_text

    post = {"name": "Car payments", "body": ""}
    doc = {"comments": [
        {"comment": {"content": "> quoted\nI sold my car.", "path": "0.2", "deleted": False,
                     "removed": False}, "creator": {"name": "alice"}, "post": post},
        {"comment": {"content": "The bus is fine.", "path": "0.1", "deleted": False,
                     "removed": False}, "creator": {"name": "bob"}, "post": post},
        {"comment": {"content": "gone", "path": "0.3", "deleted": True, "removed": False},
         "creator": {"name": "carol"}, "post": post}]}
    text = extract_text(json.dumps(doc).encode(), "json")
    assert text == "Car payments\n\nThe bus is fine.\n\nI sold my car."


def test_namespaced_parliament_xml_paragraphs_are_extracted():
    xml = b"""<akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">
      <debate><debateBody><speech by="#x"><from>Chair</from><p>We are in public session.</p>
      <p>The taxi licence costs too much.</p></speech></debateBody></debate></akomaNtoso>"""
    assert extract_text(xml, "xml") == "We are in public session.\n\nThe taxi licence costs too much."


def test_base64_html_inside_json_is_extracted():
    import base64
    import json

    html = ("<html><body><p>Q1 Chair: Welcome.</p><p>Paul: As a taxi driver I wait two hours "
            "at the airport rank every night before I get a fare. " * 20 + "</p></body></html>")
    doc = {"data": base64.b64encode(html.encode()).decode(), "fileName": "x.html"}
    assert "taxi driver I wait two hours" in extract_text(json.dumps(doc).encode(), "json")
