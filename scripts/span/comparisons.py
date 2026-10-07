"""Compare scout-large with the other models of the pilot on quality and speed (feature 004).

Adds comparison metrics to the release's results files and draws two figures for the model card
and the recipe document:

- quality vs speed: comparison composite on the frozen benchmark against texts per minute, one
  request at a time;
- time for 10,000 texts, per model and hardware.

Sources, all from runs on the same frozen benchmark (pilot-v2, 150 main chunks):
- scout-large: `jtbd perf --backend span` files (reference machine, Mac CPU and GPU, DGX Spark GPU);
- generative models: 60 / median latency of their benchmark labeling calls, which ran one call
  per chunk; GPT from the dedicated sample at concurrency 1 (`jtbd perf --frontier`); small models
  also on the reference machine (`jtbd perf`);
- quality: `jtbd score` files (comparison composite over the same six dimensions).

Run after `jtbd span results`, which rewrites the results files:

    uv run python scripts/span/comparisons.py --version 0.1.0
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
VERSION_DIR = ROOT / "zoo/models/scout-large/results"
FIGURES = ROOT / "docs/recipes/figures"
BENCH = "pilot-v2"
ANALYSIS = ROOT / "data/analysis" / BENCH
RUNS = ROOT / "data/runs"
SHA = "932c33e3a85a"
REFERENCE = "the consensus of claude-reference and gpt-mini-reference (frontier reference models)"

SURFACE, TEXT_PRIMARY, TEXT_SECONDARY, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
SCOUT, OTHER, REF, SIZE = "#eb6834", "#2a78d6", "#8a8984", "#7a5fc4"

# Scout on four machines: (metric suffix, perf file suffix, label, hardware text)
SCOUT_HW = [
    ("", "", "4 vCPU, 8 GB (reference)", None),
    ("mac_m3pro_cpu", "-mac-cpu", "MacBook M3 Pro, CPU", "MacBook Pro, Apple M3 Pro, 36 GB, CPU only"),
    ("mac_m3pro_gpu", "-mps", "MacBook M3 Pro, GPU", "MacBook Pro, Apple M3 Pro, 36 GB, GPU (MPS)"),
    ("dgx_spark_gpu", "-dgx-spark-gpu", "DGX Spark, GPU", "NVIDIA DGX Spark (GB10), GPU (CUDA)"),
]


def run_id(role: str, model: str) -> str:
    return f"run-{role}-{model}-main-6b5662fa"


TEACHER = "teacher_candidate"
OPENROUTER = "OpenRouter, provider chosen per request"
SPARK_OLLAMA = "NVIDIA DGX Spark (GB10), GPU, Ollama"
# Generative models: (metric id, label, run for latency, hardware text, run for quality or None)
OTHERS = [
    ("claude", "Claude Opus 5.5 (reference)", run_id("reference", "claude-reference"),
     "Anthropic, Claude Code CLI (subscription)", None),
    ("gpt_mini", "GPT-5.4 mini (reference)", None, "OpenAI via OpenRouter", None),
    ("mimo", "MiMo V2.6 Pro (teacher)", run_id(TEACHER, "teacher-or-mimo-v2.6-pro"), OPENROUTER,
     run_id(TEACHER, "teacher-or-mimo-v2.6-pro")),
    ("deepseek", "DeepSeek V4.1 Flash", run_id(TEACHER, "teacher-or-deepseek-v4.1-flash"),
     OPENROUTER, run_id(TEACHER, "teacher-or-deepseek-v4.1-flash")),
    ("qwen3_8_27b_dgx", "Qwen3.8 27B, DGX Spark", run_id(TEACHER, "teacher-qwen3.8"), SPARK_OLLAMA,
     run_id(TEACHER, "teacher-qwen3.8")),
    ("gemma4_e4b_dgx", "Gemma4 E4B, DGX Spark", run_id("baseline", "baseline-gemma4-e4b"),
     SPARK_OLLAMA, run_id("baseline", "baseline-gemma4-e4b")),
]
# Small models measured on the reference machine (perf files of the pilot)
SMALL = [
    ("qwen3_5_4b", "Qwen3.5 4B, 4 vCPU", "baseline-qwen3.5-4b"),
    ("ministral_3b", "Ministral 3B, 4 vCPU", "baseline-ministral-3b"),
    ("gemma4_e2b", "Gemma4 E2B, 4 vCPU", "baseline-gemma4-e2b"),
]
# Same size class as scout-large (0.3-1.2B), added for the 0.1.1 card: the newest model of each
# family at this size in October 2026 (Qwen3 0.6B and Llama 3.2 1B were run but left out as
# superseded). Quality from their benchmark runs, speed from their benchmark runs on the DGX Spark.
SIZE_CLASS = [
    ("qwen3_5_0_8b", "Qwen3.5 0.8B", "baseline-qwen3.5-0.8b"),
    ("gemma3_270m", "Gemma3 270M", "baseline-gemma3-270m"),
    ("gemma3_1b", "Gemma3 1B", "baseline-gemma3-1b"),
    ("lfm2_5_1_2b", "LFM2.5 1.2B", "baseline-lfm2.5-1.2b"),
    ("granite4_350m", "Granite 4 350M", "baseline-granite4-350m"),
]


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def median_latency_s(run: str) -> tuple[float, int]:
    values = []
    for f in (RUNS / run / "raw").glob("*.json"):
        d = read(f)
        if d.get("latency_ms") and not d.get("error"):
            values.append(d["latency_ms"] / 1000)
    return statistics.median(values), len(values)


def composite(run: str) -> float:
    return read(ANALYSIS / "scores" / f"{run}.json")["composite"]


def collect() -> dict:
    scout_quality = read(ANALYSIS / "scores" /
                         f"run-student-scout-large-c1-{SHA}-main-6b5662fa.json")["comparison_composite"]["value"]
    scout = []
    for key, suffix, label, hw in SCOUT_HW:
        p = read(ANALYSIS / "perf" / f"scout-large-{SHA}{suffix}.json")
        scout.append({"id": key, "label": label, "hardware": hw or p["hardware"]["label"],
                      "chunks_per_min": p["chunks_per_min"],
                      "latency_9k_chars_s": p["latency_9k_chars_s"], "quality": scout_quality})
    others = []
    for key, label, run, hw, qrun in OTHERS:
        if run is None:  # GPT: dedicated sample at concurrency 1
            f = read(ANALYSIS / "perf" / "frontier.json")
            cpm, n, how = f["chunks_per_min"], f["n_chunks"], "sample at concurrency 1"
        else:
            lat, n = median_latency_s(run)
            cpm, how = 60 / lat, "60 / median call latency while labeling the benchmark"
        others.append({"id": key, "label": label, "hardware": hw, "chunks_per_min": cpm,
                       "n": n, "how": how, "quality": composite(qrun) if qrun else None,
                       "quality_run": qrun})
    for key, label, model in SMALL:
        qrun = run_id("baseline", model)
        p = read(ANALYSIS / "perf" / f"{model}.json")
        others.append({"id": key, "label": label, "hardware": p["hardware"]["label"],
                       "chunks_per_min": p["chunks_per_min"], "n": p["n_chunks"],
                       "how": "jtbd perf on the reference machine, one chunk at a time",
                       "quality": composite(qrun), "quality_run": qrun})
    for key, label, model in SIZE_CLASS:
        qrun = run_id("baseline", model)
        if not (ANALYSIS / "scores" / f"{qrun}.json").exists():
            continue  # not scored yet
        lat, n = median_latency_s(qrun)
        others.append({"id": key, "label": f"{label}, DGX Spark", "hardware": SPARK_OLLAMA,
                       "chunks_per_min": 60 / lat, "n": n, "size_class": True,
                       "how": "60 / median call latency while labeling the benchmark, two calls "
                              "in parallel",
                       "quality": composite(qrun), "quality_run": qrun})
    return {"scout": scout, "others": others}


def add_metrics(data: dict, version: str) -> None:
    today = date.today().isoformat()
    qpath, ppath = VERSION_DIR / version / "quality.json", VERSION_DIR / version / "performance.json"
    quality, perf = read(qpath), read(ppath)
    qnames = {m["name"] for m in quality["metrics"]}
    pnames = {m["name"] for m in perf["metrics"]}
    for s in data["scout"]:
        if not s["id"]:
            continue
        for name, value, unit, desc in (
            (f"chunks_per_min_{s['id']}", s["chunks_per_min"], "chunks/min",
             "Throughput over the 150 benchmark chunks, one at a time (development hardware)"),
            (f"latency_9k_chars_s_{s['id']}", s["latency_9k_chars_s"], "s",
             "Median time to process the 9,240-character text, model loaded (development hardware)"),
        ):
            if name not in pnames:
                perf["metrics"].append({"name": name, "value": round(value, 4), "unit": unit,
                                        "description": desc, "date": today, "hardware": s["hardware"],
                                        "n_items": 150 if name.startswith("chunks") else None})
    for o in data["others"]:
        name = f"comparison_chunks_per_min_{o['id']}"
        if name not in pnames:
            perf["metrics"].append({
                "name": name, "value": round(o["chunks_per_min"], 4), "unit": "chunks/min",
                "description": f"{o['label']}: texts per minute on the benchmark chunks ({o['how']})",
                "date": today, "hardware": o["hardware"], "n_items": o["n"]})
        qname = f"comparison_composite_{o['id']}"
        if o["quality"] is not None and qname not in qnames:
            quality["metrics"].append({
                "name": qname, "value": round(o["quality"], 6), "unit": None,
                "description": f"Same composite for {o['label']} (zero-shot, from its benchmark run)",
                "date": today, "reference": REFERENCE, "benchmark": BENCH, "n_items": 150})
    ppath.write_text(json.dumps(perf, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    qpath.write_text(json.dumps(quality, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def duration(minutes: float) -> str:
    if minutes < 90:
        return f"{minutes:.0f} min"
    hours = minutes / 60
    return f"{hours:.1f} h" if hours < 48 else f"{hours / 24:.1f} days"


def style(ax) -> None:
    ax.set_facecolor(SURFACE)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(GRID)
    ax.tick_params(colors=TEXT_SECONDARY, labelsize=9, which="both")
    ax.set_axisbelow(True)


# Label positions chosen by hand where automatic placement crosses leader lines.
FIXED = {
    "Ministral 3B, 4 vCPU": ((6, -36), "left"),
    "Gemma4 E2B, 4 vCPU": ((12, -3), "left"),
    "Qwen3.5 4B, 4 vCPU": ((10, 8), "left"),
}


# Groups of the comparison, in legend order: (marker, colour, legend text).
GROUPS = {
    "frontier": ("o", REF, "frontier models (Claude, GPT): reference, = 1.0"),
    "large": ("o", OTHER, "large open LLMs (27B and up, hosted or on the DGX), zero-shot"),
    "small": ("s", "#1f9e89", "small LLMs (2-8B), zero-shot"),
    "size": ("^", SIZE, "LLMs of scout's size (0.3-1.2B), zero-shot"),
}
LARGE = {"mimo", "deepseek", "qwen3_8_27b_dgx"}


def group_of(o: dict) -> str:
    if o["quality"] is None:
        return "frontier"
    if o.get("size_class"):
        return "size"
    return "large" if o["id"] in LARGE else "small"


def place_labels(fig, ax, items: list[tuple[str, float, float, str]], boxes: list,
                 extra_points: list) -> None:
    """Labels with leader lines; each takes the first free position around its point, avoiding
    the boxes and points given; otherwise the position with the least overlap."""
    renderer = fig.canvas.get_renderer()
    points = [ax.transData.transform((x, y)) for _, x, y, _ in items] + extra_points
    offsets = [((10, 8), "left"), ((10, -16), "left"), ((-10, 8), "right"),
               ((-10, -16), "right"), ((14, 22), "left"), ((-14, 22), "right"),
               ((14, -30), "left"), ((-14, -30), "right"), ((24, 36), "left"),
               ((24, -44), "left"), ((-24, 36), "right"), ((-24, -44), "right"),
               ((36, 0), "left"), ((-36, 0), "right")]
    leader = {"arrowstyle": "-", "color": TEXT_SECONDARY, "linewidth": 0.6, "shrinkA": 0,
              "shrinkB": 5}
    def overlap(a, b) -> float:
        w = min(a.x1, b.x1) - max(a.x0, b.x0)
        h = min(a.y1, b.y1) - max(a.y0, b.y0)
        return w * h if w > 0 and h > 0 else 0.0

    inside = ax.get_window_extent(renderer)
    for name, x, y, color in sorted(items, key=lambda i: (-i[2], i[1])):
        if name in FIXED:
            (dx, dy), ha = FIXED[name]
            label = ax.annotate(name, (x, y), xytext=(dx, dy), textcoords="offset points",
                                fontsize=8.5, color=color, ha=ha, arrowprops=leader)
            boxes.append(label.get_window_extent(renderer).expanded(1.03, 1.2))
            continue
        best = None
        for (dx, dy), ha in offsets:
            label = ax.annotate(name, (x, y), xytext=(dx, dy), textcoords="offset points",
                                fontsize=8.5, color=color, ha=ha, arrowprops=leader)
            box = label.get_window_extent(renderer).expanded(1.03, 1.2)
            cost = sum(overlap(box, b) for b in boxes) + 1e4 * sum(
                box.contains(px, py) for px, py in points)
            if not (inside.contains(box.x0, box.y0) and inside.contains(box.x1, box.y1)):
                cost += 1e6
            label.remove()
            if best is None or cost < best[0]:
                best = (cost, (dx, dy), ha)
            if cost == 0:
                break
        _, (dx, dy), ha = best
        label = ax.annotate(name, (x, y), xytext=(dx, dy), textcoords="offset points",
                            fontsize=8.5, color=color, ha=ha, arrowprops=leader)
        boxes.append(label.get_window_extent(renderer).expanded(1.03, 1.2))


def figure_quality_speed(data: dict, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.6, 5.2), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    style(ax)
    ax.set_xscale("log")
    ax.grid(True, which="major", color=GRID, linewidth=0.8)
    plain = FuncFormatter(lambda v, _: f"{v:g}")
    ax.xaxis.set_major_formatter(plain)
    items = []
    # Two points only (owner's choice, 2026-10-07): the GPUs a team is likely to use. The CPU
    # measurements, including the reference machine, are in the 10,000-texts figure.
    scout = sorted((s for s in data["scout"] if s["id"] in ("mac_m3pro_gpu", "dgx_spark_gpu")),
                   key=lambda s: s["chunks_per_min"])
    ax.scatter([s["chunks_per_min"] for s in scout], [s["quality"] for s in scout], marker="D",
               s=80, color=SCOUT, edgecolors=SURFACE, linewidths=1.5, zorder=4,
               label="scout-large (this model)")
    short = {"mac_m3pro_gpu": "MacBook M3 Pro\n(GPU)", "dgx_spark_gpu": "DGX Spark\n(GPU)"}
    groups = {g: [o for o in data["others"] if group_of(o) == g] for g in GROUPS}
    for g, (marker, color, legend_text) in GROUPS.items():
        members = groups[g]
        if not members or g == "frontier":
            continue
        ax.scatter([o["chunks_per_min"] for o in members], [o["quality"] for o in members], s=56,
                   marker=marker, color=color, edgecolors=SURFACE, linewidths=1.5, zorder=3,
                   label=legend_text)
        items += [(o["label"].removesuffix(", DGX Spark") if g == "size" else o["label"],
                   o["chunks_per_min"], o["quality"], TEXT_SECONDARY) for o in members]
    refs = groups["frontier"]
    ax.scatter([o["chunks_per_min"] for o in refs], [1.0] * len(refs), s=56, facecolors="none",
               edgecolors=REF, linewidths=1.5, zorder=3, label=GROUPS["frontier"][2])
    ref_labels = [(o["label"].removesuffix(" (reference)"), o["chunks_per_min"]) for o in refs]
    ax.axhspan(0.97, 1.03, color=REF, alpha=0.08, zorder=1, linewidth=0)
    ax.annotate("frontier models (they define the benchmark: 1.0)", (0.21, 1.035),
                fontsize=8, color=TEXT_SECONDARY, va="bottom", style="italic")
    ax.set_xlim(0.2, 4000)
    ax.set_ylim(0, 1.15)
    ax.set_xlabel("Texts per minute, one at a time (log scale)", color=TEXT_SECONDARY, fontsize=9)
    ax.set_ylabel("Quality: agreement with the reference models", color=TEXT_SECONDARY, fontsize=9)
    ax.set_title("scout-large: good quality, hundreds of times faster", loc="left",
                 color=TEXT_PRIMARY, fontsize=12)
    legend = ax.legend(loc="lower right", fontsize=8, frameon=False)
    for text in legend.get_texts():
        text.set_color(TEXT_SECONDARY)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    boxes = []
    for s in scout:
        label = ax.annotate(short[s["id"]], (s["chunks_per_min"], s["quality"]), xytext=(0, -12),
                            textcoords="offset points", ha="center", va="top", fontsize=8.5,
                            color=TEXT_PRIMARY)
        boxes.append(label.get_window_extent(renderer).expanded(1.05, 1.1))
    mid = math.sqrt(scout[0]["chunks_per_min"] * scout[-1]["chunks_per_min"])
    label = ax.annotate("scout-large (this model)", (mid, scout[-1]["quality"]),
                        xytext=(0, 14), textcoords="offset points", ha="center", va="bottom",
                        fontsize=9.5, color=SCOUT, fontweight="bold")
    boxes.append(label.get_window_extent(renderer).expanded(1.05, 1.1))
    for n, (name, x) in enumerate(sorted(ref_labels, key=lambda r: r[1])):
        # left circle labelled to its left, right circle to its right
        dx, ha = (-9, "right") if n == 0 else (9, "left")
        label = ax.annotate(name, (x, 1.0), xytext=(dx, 0), textcoords="offset points",
                            ha=ha, va="center", fontsize=8.5, color=TEXT_SECONDARY)
        boxes.append(label.get_window_extent(renderer).expanded(1.05, 1.15))
    scout_points = [ax.transData.transform((s["chunks_per_min"], s["quality"])) for s in scout]
    scout_points += [ax.transData.transform((x, 1.0)) for _, x in ref_labels]
    place_labels(fig, ax, items, boxes, scout_points)
    fig.text(0.01, 0.005, f"Frozen benchmark {BENCH}, 150 texts. Quality of LLMs is zero-shot; "
             "LLM speed = 60 / median call latency.", fontsize=7, color=TEXT_SECONDARY)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor=SURFACE)
    plt.close(fig)


def figure_10k(data: dict, out: Path) -> None:
    rows = [(f"scout-large · {s['label']}", s["chunks_per_min"], True, "scout")
            for s in data["scout"]]
    rows += [(o["label"], o["chunks_per_min"], False, group_of(o)) for o in data["others"]]
    rows.sort(key=lambda r: -r[1])
    fig, ax = plt.subplots(figsize=(8.6, 7.2), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    style(ax)
    ax.set_xscale("log")
    ax.grid(True, axis="x", which="major", color=GRID, linewidth=0.8)
    minutes = [10_000 / r[1] for r in rows]
    y = range(len(rows))
    ax.barh(list(y), minutes, height=0.62,
            color=[SCOUT if r[2] else GROUPS[r[3]][1] for r in rows])
    ax.set_yticks(list(y), [r[0] for r in rows], fontsize=8.5)
    for tick, row in zip(ax.get_yticklabels(), rows, strict=True):
        tick.set_color(TEXT_PRIMARY if row[2] else TEXT_SECONDARY)
    ax.invert_yaxis()
    for i, m in enumerate(minutes):
        ax.annotate(duration(m), (m, i), xytext=(4, 0), textcoords="offset points",
                    va="center", fontsize=8.5, color=TEXT_PRIMARY)
    ticks = [1, 10, 60, 600, 1440, 10080, 43200]
    names = ["1 min", "10 min", "1 h", "10 h", "1 day", "1 week", "1 month"]
    ax.set_xticks(ticks, names)
    ax.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    ax.set_xlim(1, max(minutes) * 4)
    ax.set_xlabel("Time for 10,000 texts, one at a time (log scale)", color=TEXT_SECONDARY, fontsize=9)
    ax.set_title("Time to read 10,000 interview excerpts", loc="left", color=TEXT_PRIMARY,
                 fontsize=12)
    from matplotlib.patches import Patch

    present = {r[3] for r in rows}
    bar_names = {"frontier": "frontier models (reference)", "large": "large open LLMs",
                 "small": "small LLMs (2-8B)", "size": "LLMs of scout's size (0.3-1.2B)"}
    handles = [Patch(color=SCOUT, label="scout-large (this model)")]
    handles += [Patch(color=GROUPS[g][1], label=bar_names[g]) for g in GROUPS if g in present]
    legend = ax.legend(handles=handles, loc="upper right", fontsize=8, frameon=False)
    for text in legend.get_texts():
        text.set_color(TEXT_SECONDARY)
    fig.tight_layout()
    fig.savefig(out, facecolor=SURFACE)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="0.1.0")
    args = parser.parse_args()
    data = collect()
    add_metrics(data, args.version)
    figure_quality_speed(data, FIGURES / "scout-large-quality-speed.png")
    figure_10k(data, FIGURES / "scout-large-10k-texts.png")
    (FIGURES / "scout-large-comparison.json").write_text(json.dumps(data, indent=2) + "\n")
    for s in data["scout"]:
        print(f"scout {s['label']}: {s['chunks_per_min']:.1f}/min")
    for o in data["others"]:
        q = "-" if o["quality"] is None else f"{o['quality']:.3f}"
        print(f"{o['label']}: {o['chunks_per_min']:.2f}/min, quality {q}")


if __name__ == "__main__":
    main()
