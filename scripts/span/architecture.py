"""Architecture figure of scout-large for the model card and the recipe document.

Follows the inference path of `SpanExtractor.extract` (src/.../span/extractor.py): units, windows,
one encoder pass per window, token states averaged over overlaps and pooled per unit, then the unit,
attribute and relevance heads. The BIO head is used in training only.

    uv run python scripts/span/architecture.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "docs/recipes/figures/scout-large-architecture.png"
SURFACE, TEXT_PRIMARY, TEXT_SECONDARY, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
SCOUT, SCOUT_LIGHT, OTHER_LIGHT = "#eb6834", "#fbe3d8", "#dce9f8"


def box(ax, x, y, w, h, title, body, face="#ffffff", edge=GRID, title_color=TEXT_PRIMARY):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.018",
                                facecolor=face, edgecolor=edge, linewidth=1.2))
    ax.text(x + w / 2, y + h - 0.035, title, ha="center", va="top", fontsize=9.5,
            fontweight="bold", color=title_color)
    ax.text(x + w / 2, y + h - 0.085, body, ha="center", va="top", fontsize=8,
            color=TEXT_SECONDARY, linespacing=1.35)


def arrow(ax, x0, y0, x1, y1):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=12,
                                 color=TEXT_SECONDARY, linewidth=1.2))


def main() -> None:
    fig = plt.figure(figsize=(11, 5.6), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.02, 0.965, "How scout-large reads a text", fontsize=13, color=TEXT_PRIMARY,
            va="top")
    ax.text(0.02, 0.925, "One pass of an encoder per 512-token window, no text generation: "
            "quotes are always exact spans of the input.", fontsize=9, color=TEXT_SECONDARY,
            va="top")

    y, h, w = 0.47, 0.36, 0.165
    xs = [0.02, 0.215, 0.41, 0.605, 0.80]
    box(ax, xs[0], y, w, h, "1  Text", "German or English,\nany length\n\n"
        "split into units:\nsentences and clauses")
    box(ax, xs[1], y, w, h, "2  Windows", "tokens in windows of\n512, overlapping by 128\n\n"
        "long texts become\nseveral windows")
    box(ax, xs[2], y, w, h, "3  Encoder", "XLM-RoBERTa-large\n24 layers, 1,024 dims\n"
        "560M parameters\n\none forward pass\nper window", face=SCOUT_LIGHT, edge=SCOUT,
        title_color=SCOUT)
    box(ax, xs[3], y, w, h, "4  Per unit", "token states averaged\nwhere windows overlap,\n"
        "then pooled over\neach unit's tokens")
    box(ax, xs[4], y, 0.18, h, "5  Heads", "unit: job, pain, gain\nor no item (+ score)\n\n"
        "actor type\nevidence type\nevidence scope\n\nrelevance of the text",
        face=SCOUT_LIGHT, edge=SCOUT, title_color=SCOUT)
    for a, b in zip(xs[:-1], xs[1:], strict=True):
        arrow(ax, a + w + 0.005, y + h / 2, b - 0.008, y + h / 2)

    box(ax, 0.60, 0.07, 0.38, 0.30, "Output: JSON (jtbd-span-v1)",
        "relevant, relevance_probability, dimensions\n"
        "items: kind, quote, start, end, score,\nactor_type, evidence_type, evidence_scope\n\n"
        "each quote is the unit's own text with its\ncharacter offsets: verbatim by construction")
    arrow(ax, xs[4] + 0.09, y - 0.005, 0.79, 0.375)

    box(ax, 0.02, 0.07, 0.54, 0.30, "For comparison: a generative LLM",
        "reads the whole prompt (guideline + text), then writes the JSON\n"
        "token by token: about 1,000 output tokens per text on this\n"
        "benchmark (median), several thousand for reasoning models;\n"
        "quotes are retyped and can drift from the source.\n\n"
        "scout-large instead labels units it has already read:\n"
        "no output tokens to generate, so it is much faster and cannot break the format.",
        face=OTHER_LIGHT, edge="#2a78d6", title_color="#2a78d6")
    ax.text(0.98, 0.015, "Training only: a BIO head for token-level span boundaries helps the "
            "encoder learn; it is not used at inference.", ha="right", fontsize=7,
            color=TEXT_SECONDARY)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, facecolor=SURFACE)
    plt.close(fig)
    print(OUT)


if __name__ == "__main__":
    main()
