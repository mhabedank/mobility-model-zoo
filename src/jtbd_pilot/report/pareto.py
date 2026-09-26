"""Quality-vs-throughput chart: first points of the Pareto front (FR-032, Principle III).

Static figure for the Markdown report: one series (small models on the reference VM), direct
labels, recessive grid, reference lines for the FR-031 bars. The report's baseline table is the
table view of the same data.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e4e3df"
SERIES_1 = "#2a78d6"


def pareto_front(points: list[tuple[str, float, float]]) -> list[tuple[str, float, float]]:
    """Points (name, throughput, quality) not dominated on both axes, sorted by throughput."""
    front = [
        p for p in points
        if not any(q[1] >= p[1] and q[2] >= p[2] and (q[1] > p[1] or q[2] > p[2]) for q in points)
    ]
    return sorted(front, key=lambda p: p[1])


def draw(points: list[tuple[str, float, float]], out: Path, *, version: str,
         quality_bar: float | None, throughput_bar: float | None) -> Path | None:
    if not points:
        return None
    fig, ax = plt.subplots(figsize=(7.5, 4.8), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    ax.set_xscale("log")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(GRID)
    ax.grid(True, which="major", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=TEXT_SECONDARY, labelsize=9, which="both")
    plain = FuncFormatter(lambda v, _: f"{v:g}")
    ax.xaxis.set_major_formatter(plain)
    ax.xaxis.set_minor_formatter(plain)

    if quality_bar is not None:
        ax.axhline(quality_bar, color=TEXT_SECONDARY, linewidth=1, linestyle=(0, (4, 3)))
        ax.annotate("85% of frontier quality", (0.99, quality_bar), xycoords=("axes fraction",
                    "data"), ha="right", va="bottom", fontsize=8, color=TEXT_SECONDARY)
    if throughput_bar is not None:
        ax.axvline(throughput_bar, color=TEXT_SECONDARY, linewidth=1, linestyle=(0, (4, 3)))
        ax.annotate("10x reference throughput", (throughput_bar, 0.02),
                    xycoords=("data", "axes fraction"), xytext=(-4, 0),
                    textcoords="offset points", rotation=90, ha="right", va="bottom",
                    fontsize=8, color=TEXT_SECONDARY)

    front = pareto_front(points)
    if len(front) > 1:
        ax.plot([p[1] for p in front], [p[2] for p in front], color=SERIES_1, linewidth=2,
                zorder=2)
    ax.scatter([p[1] for p in points], [p[2] for p in points], s=64, color=SERIES_1,
               edgecolors=SURFACE, linewidths=2, zorder=3)
    for name, x, y in points:
        ax.annotate(name, (x, y), xytext=(6, 6), textcoords="offset points", fontsize=9,
                    color=TEXT_PRIMARY)

    ax.set_xlabel("Throughput on reference VM (chunks per minute, log scale)",
                  color=TEXT_SECONDARY, fontsize=9)
    ax.set_ylabel("Composite agreement with consensus", color=TEXT_SECONDARY, fontsize=9)
    ax.set_title(f"Quality vs throughput, zero-shot small models ({version})", loc="left",
                 color=TEXT_PRIMARY, fontsize=11)
    ys = [p[2] for p in points] + ([quality_bar] if quality_bar is not None else [])
    ax.set_ylim(min(0.0, min(ys) - 0.05), max(1.0, max(ys) + 0.05))
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, facecolor=SURFACE)
    plt.close(fig)
    return out
