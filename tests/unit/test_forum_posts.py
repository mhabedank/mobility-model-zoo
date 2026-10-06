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
