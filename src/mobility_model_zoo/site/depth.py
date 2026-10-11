"""Depth checks of the model pages (feature 013, specs/013-model-page-layout/contracts/checks.md).

- D1: every published model's card has the short forms its release status requires.
- D2: word and item budgets of the layers, counted on the rendered page (`budgets.py`).
- D3: what each layer may and may not contain.
- D4: release status, its sentence and the usage class in the first layer.
- D5: the six layers in order and the anchors of the old page.

D6 (placement on screen) needs a browser and is in `a11y.py`.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from mobility_model_zoo.release.card import status_sentence
from mobility_model_zoo.release.registry import Registry
from mobility_model_zoo.site import budgets as b
from mobility_model_zoo.site.check import Finding


def _published(reg: Registry) -> list[dict[str, Any]]:
    from mobility_model_zoo.site import context

    return [sm for sm in context.site_models(reg) if sm["status"] != "in_progress"]


def _page(out: Path, name: str) -> tuple[str, b.Node | None]:
    rel = f"models/{name}/index.html"
    path = out / rel
    return rel, (b.tree(path.read_text(encoding="utf-8")) if path.exists() else None)


def _layer(root: b.Node, layer: str) -> b.Node | None:
    return root.find(lambda n: n.tag == "section" and n.get("data-layer") == layer)


def _hand_text(pitch: dict[str, Any]) -> Iterable[tuple[str, str]]:
    for key in ("tagline", "audience"):
        if pitch.get(key):
            yield key, pitch[key]
    for i, d in enumerate(pitch.get("differentiators", [])):
        yield f"differentiators[{i}]", f"{d['title']} {d['text']}"


# ---- D4 and the first layer of D2/D3 ---------------------------------------------------------
def overview_findings(rel: str, root: b.Node, sm: dict[str, Any]) -> list[Finding]:
    layer = _layer(root, "overview")
    if layer is None:
        return [Finding("D5", rel, "no overview layer")]
    out: list[Finding] = []
    status = sm["release_status"]
    chip = layer.find(lambda n: n.get("data-status") is not None)
    if chip is None or chip.get("data-status") != status:
        found = chip.get("data-status") if chip else "none"
        out.append(Finding("D4", rel, f"status chip says {found}, the release record says {status}"))
    sentence = status_sentence(status)
    line = layer.find(lambda n: "status-line" in n.classes)
    if status == "experimental":
        if line is None or sentence not in line.text():
            out.append(Finding("D4", rel, f"overview lacks the status sentence {sentence!r}"))
        elif not line.find(lambda n: n.tag == "a" and n.get("href") == "#limits"):
            out.append(Finding("D4", rel, "status sentence does not link #limits"))
    if sm["usage"]["class"].startswith("non-commercial") and "Non-commercial" not in layer.text():
        out.append(Finding("D4", rel, "non-commercial model: 'Non-commercial' is not in the overview"))
    for key, text in _hand_text(sm.get("pitch") or {}):
        if m := b.STATUS_WORDS.search(text):
            out.append(Finding("D4", rel, f"site.yaml {key} states a release status ({m.group(0)!r})"))

    not_for = layer.find(lambda n: n.get("data-short") == "not-for")
    nf_words = b.visible_words(not_for) if not_for else 0
    running = b.visible_words(layer) - nf_words
    if running > b.OVERVIEW_WORDS:
        out.append(
            Finding("D2", rel, f"overview: {running} words of running text, limit {b.OVERVIEW_WORDS}")
        )
    if not_for is None:
        out.append(Finding("D2", rel, "overview: no 'Not for' list"))
    else:
        items = not_for.find_all(lambda n: n.tag == "li")
        lo, hi = b.NOT_FOR_ITEMS
        if not lo <= len(items) <= hi:
            out.append(
                Finding("D2", rel, f"overview: {len(items)} 'Not for' points, needs {lo} to {hi}")
            )
        list_words = sum(b.words(i.text(visible=True)) for i in items)
        if list_words > b.NOT_FOR_WORDS:
            out.append(
                Finding(
                    "D2", rel, f"overview: 'Not for' has {list_words} words, limit {b.NOT_FOR_WORDS}"
                )
            )
    diffs = [n for n in layer.find_all(lambda n: n.tag == "li" and "card" in n.classes)]
    lo, hi = b.DIFFERENTIATORS
    if not lo <= len(diffs) <= hi:
        out.append(Finding("D2", rel, f"overview: {len(diffs)} reasons to use it, needs {lo} to {hi}"))
    for i, d in enumerate(diffs):
        title = d.find(lambda n: n.tag == "h3")
        text = d.find(lambda n: n.tag == "p")
        if title and b.words(title.text(visible=True)) > b.DIFFERENTIATOR_TITLE_WORDS:
            out.append(
                Finding("D2", rel, f"reason {i + 1}: title over {b.DIFFERENTIATOR_TITLE_WORDS} words")
            )
        if text and b.words(text.text(visible=True)) > b.DIFFERENTIATOR_TEXT_WORDS:
            n = b.words(text.text(visible=True))
            out.append(
                Finding("D2", rel, f"reason {i + 1}: {n} words, limit {b.DIFFERENTIATOR_TEXT_WORDS}")
            )
    for tag in ("pre", "table"):
        if layer.find(lambda n, t=tag: n.tag == t):
            out.append(Finding("D3", rel, f"overview contains <{tag}>"))
    if layer.find(lambda n: "metric" in n.classes):
        out.append(Finding("D3", rel, "overview contains a headline figure"))
    return out


def check_overview(reg: Registry, out: Path) -> Iterable[Finding]:
    for sm in _published(reg):
        rel, root = _page(out, sm["name"])
        if root is None:
            yield Finding("D5", rel, "model page is missing")
            continue
        yield from overview_findings(rel, root, sm)


# ---- the second layer of D3 --------------------------------------------------------------------
def _inside(node: b.Node, tag: str) -> bool:
    p = node.parent
    while p is not None:
        if p.tag == tag:
            return True
        p = p.parent
    return False


def quality_findings(rel: str, root: b.Node) -> list[Finding]:
    layer = _layer(root, "quality")
    if layer is None:
        return [Finding("D5", rel, "no quality layer")]
    out: list[Finding] = []
    figures = layer.find_all(lambda n: "metric" in n.classes)
    if not 1 <= len(figures) <= b.HEADLINE_FIGURES_MAX:
        out.append(
            Finding(
                "D3",
                rel,
                f"quality: {len(figures)} headline figures, needs 1 to {b.HEADLINE_FIGURES_MAX}",
            )
        )
    for t in layer.find_all(lambda n: n.tag == "table"):
        if not _inside(t, "details"):
            out.append(Finding("D3", rel, "quality: a table outside a chart's value list"))
    lead = []
    for n in layer.iter():
        if "metric" in n.classes or n.tag == "figure":
            break
        if n.tag == "p":
            lead.append(n.text(visible=True))
    if b.sentences(" ".join(lead)) > b.QUALITY_LEAD_SENTENCES:
        out.append(
            Finding(
                "D3",
                rel,
                f"quality: more than {b.QUALITY_LEAD_SENTENCES} sentence before the first figure",
            )
        )
    if not layer.find(lambda n: n.tag == "a" and n.get("href") == "#metrics"):
        out.append(Finding("D3", rel, "quality: no link to #metrics"))
    return out


def check_quality(reg: Registry, out: Path) -> Iterable[Finding]:
    for sm in _published(reg):
        rel, root = _page(out, sm["name"])
        if root is not None:
            yield from quality_findings(rel, root)
