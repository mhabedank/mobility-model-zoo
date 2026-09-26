"""Pilot report (FR-032, FR-033). Quality is always described as agreement with frontier models."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jtbd_pilot import budget
from jtbd_pilot.categorize import summarize as categories_summary
from jtbd_pilot.config import Settings
from jtbd_pilot.consensus import load_consensus
from jtbd_pilot.decision import load_perf, load_scores
from jtbd_pilot.errors import ValidationFailed
from jtbd_pilot.freeze import load_manifest
from jtbd_pilot.jsonio import read_json
from jtbd_pilot.report.pareto import draw

DISCLAIMER = (
    "All quality numbers in this report measure **agreement with frontier reference models** "
    "(Claude and a GPT mini-tier model). They are not a comparison against human ground truth."
)
DIM_NAMES = {
    "relevance": "Relevance",
    "item_matching": "Item matching",
    "kind": "Kind",
    "actor_type": "Actor type",
    "evidence_type": "Evidence type",
    "evidence_scope": "Evidence scope",
}
TEACHER_FITNESS = ("A teacher candidate is marked fit when quality_ratio_a >= 0.85 (the FR-031 "
                   "quality bar), quote_verbatim >= 0.95, schema_valid >= 0.98 and a license basis "
                   "is recorded. This is an indicative statement, not part of the go/revise/rethink "
                   "decision.")


def _fmt(x: Any, digits: int = 3) -> str:
    if x is None:
        return "n/a"
    if isinstance(x, float):
        return f"{x:.{digits}f}"
    return str(x)


def _table(header: list[str], rows: list[list[Any]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(_fmt(c) for c in row) + " |" for row in rows]
    return lines


def _read(path: Path) -> Any | None:
    return read_json(path) if path.exists() else None


def _teacher_fit(score: dict) -> str:
    rates = score.get("check_pass_rates") or {}
    quote = (rates.get("quote_verbatim") or {}).get("rate")
    schema = (rates.get("schema_valid") or {}).get("rate")
    fit = (score.get("quality_ratio_a") is not None and score["quality_ratio_a"] >= 0.85
           and quote is not None and quote >= 0.95 and schema is not None and schema >= 0.98
           and bool(score.get("license_basis")))
    return "fit" if fit else "not fit"


def render_report(settings: Settings) -> dict[str, Any]:
    manifest = load_manifest(settings)
    decision = _read(settings.analysis_dir / "decision.json")
    agreement = _read(settings.analysis_dir / "agreement.json")
    if not manifest or not decision or not agreement:
        raise ValidationFailed("run `pilot agreement` and `pilot decide` before `pilot report`")
    version = manifest["version"]
    out_dir = settings.reports_dir / version
    lines: list[str] = [f"# Pilot report: {version}", ""]
    if manifest.get("test_only"):
        lines += ["> **Test-only benchmark** built from mock runs. Not a real result.", ""]
    lines += [DISCLAIMER, ""]

    # Summary
    lines += ["## 1. Decision", "",
              f"**{decision['decision'].upper()}** (criteria {decision['criteria_version']}, "
              f"decided on the {decision['decision_split']} split, reruns so far: "
              f"{decision['reruns']}).", "", "Path through the decision table (FR-030):", ""]
    lines += [f"- {step}" for step in decision["path"]]
    lines += ["", *_table(["Dimension", "Score", "Threshold", "Decision"], [
        [DIM_NAMES[d], v["score"], v["threshold"], v["decision"]]
        for d, v in decision["per_dimension"].items()]), ""]
    ft = decision["finetuning"]
    lines += [f"Fine-tuning (FR-031): **{ft['status']}**. Rule: {ft['rule']}.", ""]
    if decision.get("main_split_agreement_optimistic"):
        lines += ["Main-split agreement after the rerun (optimistic, because the revisions were "
                  "derived from these chunks): " + ", ".join(
                      f"{DIM_NAMES[d]} {_fmt(s)}"
                      for d, s in decision["main_split_agreement_optimistic"].items()), ""]

    # Versions
    lines += ["## 2. Versions", "",
              f"- Benchmark version: `{version}` (state {manifest['state']}, frozen "
              f"{manifest['frozen_at']})",
              f"- Guideline sha256: `{manifest['hashes']['guideline'][:16]}`",
              f"- Criteria sha256: `{manifest['hashes']['criteria'][:16]}`",
              f"- Reference runs: {', '.join(f'`{r}`' for r in agreement['reference_runs'])}",
              ""]

    # Corpus
    lines += ["## 3. Corpus composition", ""]
    for split in ("main", "holdout"):
        comp = _read(settings.analysis_dir / f"composition-{split}.json")
        if not comp:
            lines += [f"- {split}: composition not validated in this benchmark version", ""]
            continue
        c = comp["composition"]
        lines += [f"**{split}**: {c['n']} chunks, {c['n_relevant']} relevant.", ""]
        for key in ("sub_area", "source_type", "language", "region", "relevance_intent"):
            lines.append(f"- {key}: " + ", ".join(f"{k} {v}" for k, v in sorted(c[key].items())))
        if comp.get("substitutions"):
            lines.append("- substitutions: " + "; ".join(
                f"{s['source_type']} -> {s['replaced_by']} ({s['explanation']})"
                for s in comp["substitutions"]))
        lines.append("")

    # Agreement
    lines += ["## 4. Agreement between reference models", "",
              f"{agreement['chunks']} chunks, excluded: {len(agreement['excluded_chunks'])}, "
              f"invalid quotes per run: {agreement['invalid_quotes']}.", ""]
    rows = []
    for d, v in agreement["dimensions"].items():
        rows.append([DIM_NAMES[d], v["metric"], v["score"], f"{_fmt(v['ci_low'])} to "
                     f"{_fmt(v['ci_high'])}", v["n"], "yes" if v["underpowered"] else "no"])
    lines += _table(["Dimension", "Metric", "Score", "95% CI", "n", "Underpowered"], rows)
    lin = agreement["dimensions"]["evidence_type"]["linear"]
    lines += ["", f"Evidence type, linear weighting: {_fmt(lin['score'])}. Composite (all units): "
              f"{_fmt(agreement['composite_all_units'])}.", ""]
    ev = agreement["evidence_levels"]
    lines += ["Evidence levels in the consensus: " + ", ".join(
        f"{k} {v}" for k, v in ev["counts"].items()) + "."]
    if ev["underpowered_levels"]:
        lines.append(f"Observation and measurement together have {ev['observation_plus_measurement']}"
                     " consensus items (< 30): these levels are **underpowered** (FR-008).")
    lines += ["", "Breakdowns (score / n):", ""]
    for name, groups in agreement["breakdowns"].items():
        header = [name] + [DIM_NAMES[d] for d in DIM_NAMES]
        brows = [[g] + [f"{_fmt(v[d]['score'])} / {v[d]['n']}" for d in DIM_NAMES]
                 for g, v in groups.items()]
        lines += _table(header, brows) + [""]

    # Checks
    lines += ["## 5. Deterministic checks", ""]
    check_rows = []
    for path in sorted((settings.analysis_dir / "checks").glob("*.summary.json")):
        data = read_json(path)
        for check, v in data["pass_rates"].items():
            check_rows.append([data["run_id"], check, v["rate"], v["n"]])
    lines += (_table(["Run", "Check", "Pass rate", "n"], check_rows) if check_rows
              else ["No check results."]) + [""]

    # Contested and categories
    _, contested, _ = load_consensus(settings, "main")
    by_dim: dict[str, int] = {}
    for c in contested:
        for d in c["dimensions"]:
            by_dim[d] = by_dim.get(d, 0) + 1
    lines += ["## 6. Contested items", "",
              f"{len(contested)} contested entries, kept separately from the consensus: " + ", ".join(
                  f"{d} {n}" for d, n in sorted(by_dim.items())) + ".", ""]
    cats = categories_summary(settings)
    lines += ["## 7. Disagreement categories", ""]
    if cats["counts"]:
        lines += _table(["Category", "Count", "Examples", "Description"], [
            [k, n, ", ".join(cats["examples"].get(k, [])), cats["descriptions"].get(k, "")]
            for k, n in cats["counts"].items()])
    if cats["uncategorized"]:
        lines += ["", f"**{len(cats['uncategorized'])} contested entries are not categorized "
                  "yet** (SC-004)."]
    lines.append("")

    # Revisions
    lines += ["## 8. Proposed guideline revisions", ""]
    revisions = settings.analysis_dir / "revisions.md"
    lines += [revisions.read_text(encoding="utf-8").strip() if revisions.exists()
              else "No revisions file (`revisions.md`) yet.", ""]

    # Baselines and teachers
    scores = load_scores(settings)
    perf, frontier = load_perf(settings)
    lines += ["## 9. Teacher candidates and zero-shot baselines", ""]
    if scores:
        rows = []
        for s in scores:
            p = perf.get(s["model_id"], {})
            rows.append([s["model_id"], s["role"], *[s["dimensions"][d]["score"] for d in DIM_NAMES],
                         s["composite"], s["quality_ratio_a"], s["quality_ratio_b"],
                         p.get("chunks_per_min"), p.get("latency_p95_ms"), p.get("peak_rss_mb")])
        lines += _table(["Model", "Role", *DIM_NAMES.values(), "Composite", "Ratio a", "Ratio b",
                         "Chunks/min (VM)", "p95 ms", "Peak RSS MB"], rows)
        teachers = [s for s in scores if s["role"] == "teacher_candidate"]
        if teachers:
            lines += ["", TEACHER_FITNESS, ""]
            lines += [f"- `{t['model_id']}` ({t['family']}, {t.get('license_basis') or 'no license'}"
                      f"): **{_teacher_fit(t)}**" for t in teachers]
        lines += ["", "Contested reference items matched by a model are scored neutrally "
                  "(FR-028); counts per model: " + "; ".join(
                      f"{s['model_id']} {s['neutral_contested_hits']}" for s in scores) + "."]
    else:
        lines.append("No teacher-candidate or baseline scores yet.")
    if frontier:
        lines += ["", f"Frontier reference throughput (GPT mini tier, concurrency 1): "
                  f"{_fmt(frontier['chunks_per_min'])} chunks/min. {frontier['note']}."]
    lines.append("")

    # Chart
    points = [(s["model_id"], perf[s["model_id"]]["chunks_per_min"], s["composite"])
              for s in scores if s["role"] == "baseline" and s["model_id"] in perf
              and s["composite"] is not None and perf[s["model_id"]].get("chunks_per_min")]
    quality_bar = (0.85 * agreement["composite_consensus_units"]
                   if agreement.get("composite_consensus_units") else None)
    throughput_bar = 10 * frontier["chunks_per_min"] if frontier else None
    figure = draw(points, out_dir / "figures" / "pareto.png", version=version,
                  quality_bar=quality_bar, throughput_bar=throughput_bar)
    lines += ["## 10. Quality vs throughput", ""]
    lines += (["![Quality vs throughput](figures/pareto.png)", "",
               "The table in section 9 holds the same values."] if figure
              else ["No baseline has both a score and a performance measurement yet."])
    lines.append("")

    # Deviations and budget
    deviations = list(decision.get("deviations", []))
    deviations.insert(0, "GPT reference is the mini tier of the current generation, not the "
                         "flagship (budget; plan.md Complexity Tracking, FR-017)")
    lines += ["## 11. Deviations", ""] + [f"- {d}" for d in deviations] + [""]
    money = budget.summary(settings)
    lines += ["## 12. Budget", "",
              f"Spent EUR {money['spent_eur']:.2f} of EUR {money['budget_eur']} (OpenRouter EUR "
              f"{money['spent_openrouter_eur']:.2f} of the EUR {money['key_cap_eur']} key cap).",
              ""]

    out_dir.mkdir(parents=True, exist_ok=True)
    report = out_dir / "report.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    return {"report": str(report), "figure": str(figure) if figure else None,
            "decision": decision["decision"]}
