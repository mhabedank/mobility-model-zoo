"""Depth budgets of a model page (feature 013, research R5) and the one way they are counted.

The release gate (rules 17 and 18) counts the hand-written input, the site checks (D1-D6) count
the rendered page; both use the constants and `words()` below, so they cannot disagree.

Counting rule: words are whitespace-separated tokens of visible text. Text inside an element with
`data-budget="skip"` (chips, buttons, the layer navigation) and inside a closed `<details>` (except
its `<summary>`) does not count. A `{metric:…}` placeholder counts as one word.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from html.parser import HTMLParser

# ---- budgets (starting values; tune here, nowhere else) ----------------------------------------
OVERVIEW_WORDS = 150
NOT_FOR_ITEMS = (2, 3)
NOT_FOR_WORDS = 40
NOT_FOR_ITEM_WORDS = 15
DIFFERENTIATORS = (3, 4)
DIFFERENTIATOR_TITLE_WORDS = 5
DIFFERENTIATOR_TEXT_WORDS = 20
AUDIENCE_WORDS = 25
HEADLINE_FIGURES_MAX = 4
QUALITY_LEAD_SENTENCES = 1
LIMITS_SHORT_ITEMS = 5
LIMITS_SHORT_ITEM_WORDS = 25
LIMITS_SHORT_WORDS = 120
WORDS_BEFORE_QUALITY = 200
UNMET_CRITERION_WORDS = 12
UNMET_NOTE_WORDS = 15

# The six layers in page order (contracts/page-layers.md).
LAYERS = ("overview", "quality", "limits", "quickstart", "reference", "details")
LAYER_IDS = {
    "overview": "top",
    "quality": "quality",
    "limits": "limits",
    "quickstart": "quickstart",
    "reference": "reference",
    "details": "details",
}
# Anchors of the page before feature 013 that must keep resolving (FR-019).
ANCHORS = (
    "top", "why", "quickstart", "interface", "examples", "quality", "limits",
    "metrics", "provenance", "versions", "cite", "notes",
)  # fmt: skip
# Hand-written website text states no release status; the page generates it (research R4).
STATUS_WORDS = re.compile(r"\b(experimental|released|production[- ]ready)\b", re.I)

PLACEHOLDER = re.compile(r"\{metric:[^}]+\}")


def words(text: str) -> int:
    """Whitespace tokens; a placeholder is one token."""
    return len(PLACEHOLDER.sub("X", text).split())


def sentences(text: str) -> int:
    """Sentences of plain prose: runs ending in . ! or ? followed by space or the end."""
    text = " ".join(text.split())
    if not text:
        return 0
    return max(1, len(re.findall(r"[.!?](?=\s|$)", text)))


# ---- a small element tree over the standard library parser --------------------------------------
VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr",
}  # fmt: skip


class Node:
    def __init__(self, tag: str, attrs: dict[str, str | None], parent: Node | None) -> None:
        self.tag = tag
        self.attrs = attrs
        self.parent = parent
        self.children: list[Node | str] = []

    def get(self, key: str) -> str | None:
        return self.attrs.get(key)

    @property
    def classes(self) -> set[str]:
        return set((self.attrs.get("class") or "").split())

    def iter(self) -> Iterator[Node]:
        yield self
        for c in self.children:
            if isinstance(c, Node):
                yield from c.iter()

    def find_all(self, pred: Callable[[Node], bool]) -> list[Node]:
        return [n for n in self.iter() if n is not self and pred(n)]

    def find(self, pred: Callable[[Node], bool]) -> Node | None:
        return next(iter(self.find_all(pred)), None)

    def by_id(self, ident: str) -> Node | None:
        return self.find(lambda n: n.get("id") == ident)

    def text(self, visible: bool = False) -> str:
        """All text below this node; with `visible`, without skipped and collapsed text."""
        out: list[str] = []
        self._text(out, visible)
        return " ".join(" ".join(out).split())

    def _text(self, out: list[str], visible: bool) -> None:
        if self.tag in ("script", "style"):
            return
        if visible and self.get("data-budget") == "skip":
            return
        if visible and self.tag == "details" and "open" not in self.attrs:
            for c in self.children:  # a closed <details> shows its summary only
                if isinstance(c, Node) and c.tag == "summary":
                    c._text(out, visible)
            return
        for c in self.children:
            if isinstance(c, str):
                out.append(c)
            else:
                c._text(out, visible)


class _Builder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", {}, None)
        self.cur = self.root

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = Node(tag, {k: (v if v is not None else "") for k, v in attrs}, self.cur)
        self.cur.children.append(node)
        if tag not in VOID:
            self.cur = node

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.cur.children.append(Node(tag, {k: (v or "") for k, v in attrs}, self.cur))

    def handle_endtag(self, tag: str) -> None:
        node = self.cur
        while node is not None and node.tag != tag:
            node = node.parent
        if node is not None and node.parent is not None:
            self.cur = node.parent

    def handle_data(self, data: str) -> None:
        self.cur.children.append(data)


def tree(html: str) -> Node:
    b = _Builder()
    b.feed(html)
    return b.root


def visible_words(node: Node) -> int:
    return words(node.text(visible=True))


def layers(root: Node) -> list[Node]:
    """The `data-layer` sections in document order."""
    return root.find_all(lambda n: n.tag == "section" and n.get("data-layer") is not None)
