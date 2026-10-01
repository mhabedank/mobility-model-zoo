"""Offline teacher ensemble (FR-019b) and quote repair for teacher scoring (FR-026a).

The ensemble is computed from the stored outputs of the member runs, without model calls:
- relevance: majority vote (ties count as relevant),
- items: members are processed in alphabetical order of their model IDs; each item joins the
  group it overlaps most (IoU >= min_iou, at most one item per member and group), otherwise it
  opens a new group; a group is kept when at least `min_votes` members found it,
- attributes: majority vote inside the group; ties go to the alphabetically first member,
- quote, actor and statement: from the alphabetically first member in the group.
The rule has no configurable order, so no spike measurement can enter it (spec session
2026-10-01). Near-miss quotes are repaired to the verbatim source passage before grouping;
unrepairable items are dropped.
"""

from __future__ import annotations

import shutil
from collections import Counter
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from mobility_model_zoo.productdev.jtbd.config import Settings
from mobility_model_zoo.productdev.jtbd.corpus.store import chunk_map
from mobility_model_zoo.productdev.jtbd.errors import ValidationFailed
from mobility_model_zoo.productdev.jtbd.freeze import verify_frozen
from mobility_model_zoo.productdev.jtbd.jsonio import write_json
from mobility_model_zoo.productdev.jtbd.labeling.runner import run_id_for
from mobility_model_zoo.productdev.jtbd.matching import iou
from mobility_model_zoo.productdev.jtbd.quotes import repair
from mobility_model_zoo.productdev.jtbd.runs import (
    ChunkOutput,
    LocatedItem,
    load_outputs,
    load_run_manifest,
)
from mobility_model_zoo.productdev.jtbd.schema import (
    ATTRIBUTE_DIMENSIONS,
    ExtractionOutput,
    LabelRunManifest,
    QuoteRepair,
    RunSettings,
)


def with_repair(out: ChunkOutput, text: str, rule: QuoteRepair | None = None,
                stats: Counter | None = None) -> list[LocatedItem]:
    """The output's items with near-miss quotes repaired; unrepairable items are dropped.

    Every kept item's quote is its source passage with whitespace collapsed. `stats` counts
    `invalid_quotes`, `repaired` and `dropped`.
    """
    params = rule.model_dump() if rule else {}
    stats = stats if stats is not None else Counter()
    items = []
    for it in out.items:
        span = it.span
        if span is None:
            stats["invalid_quotes"] += 1
            span = repair(it.quote, text, **params)
            stats["repaired" if span else "dropped"] += 1
            if span is None:
                continue
        items.append(LocatedItem(it.index, it.kind, " ".join(text[span[0]:span[1]].split()),
                                 it.actor, it.actor_type, it.statement, it.evidence_type,
                                 it.evidence_scope, span))
    return items


def vote(values: dict[str, str], priority: list[str]) -> str:
    counts = Counter(values.values())
    best = max(counts.values())
    tied = {v for v, n in counts.items() if n == best}
    for member in priority:
        if member in values and values[member] in tied:
            return values[member]
    return next(iter(tied))


def combine(outputs: Mapping[str, Mapping[str, ChunkOutput]], members: list[str], min_votes: int,
            chunks: Mapping, min_iou: float, tie_break: Mapping[str, list[str]] | None = None,
            quote_priority: list[str] | None = None, rule: QuoteRepair | None = None
            ) -> dict[str, ChunkOutput]:
    """Ensemble output per chunk. A chunk without a valid output from any member is excluded.

    Members are processed in the given order. Without `tie_break` and `quote_priority` (the
    pilot) ties and the quote source follow the alphabetical order of the members; the spike
    script passes its own orders.
    """
    alphabetical = sorted(members)
    tie_break = tie_break or {a: alphabetical for a in ATTRIBUTE_DIMENSIONS}
    quote_priority = quote_priority or alphabetical
    result = {}
    for chunk_id, chunk in chunks.items():
        present = {m: outputs[m][chunk_id] for m in members if chunk_id in outputs[m]}
        if not present:
            continue
        votes = [o.relevant for o in present.values() if o.relevant is not None]
        relevant = sum(votes) * 2 >= len(votes) if votes else None
        if not relevant:
            result[chunk_id] = ChunkOutput(chunk_id, relevant)
            continue
        groups: list[dict[str, LocatedItem]] = []
        for m, o in present.items():
            for it in with_repair(o, chunk.text, rule) if o.relevant else []:
                best, best_iou = None, min_iou
                for g in groups:
                    if m in g:
                        continue
                    score = max(iou(it.span, x.span) for x in g.values())
                    if score >= best_iou:
                        best, best_iou = g, score
                if best is None:
                    groups.append({m: it})
                else:
                    best[m] = it
        items = []
        for n, g in enumerate(groups):
            if len(g) < min_votes:
                continue
            rep = g[next(m for m in [*quote_priority, *members] if m in g)]
            attrs = {a: vote({m: getattr(x, a) for m, x in g.items()}, tie_break[a])
                     for a in ATTRIBUTE_DIMENSIONS}
            items.append(LocatedItem(n, attrs["kind"], rep.quote, rep.actor, attrs["actor_type"],
                                     rep.statement, attrs["evidence_type"],
                                     attrs["evidence_scope"], rep.span))
        result[chunk_id] = ChunkOutput(chunk_id, True, items)
    return result


def _member_runs(settings: Settings, members: list[str], split: str,
                 frozen: dict[str, Any]) -> dict[str, LabelRunManifest]:
    hashes = frozen["hashes"]
    runs = {}
    for member in members:
        run_id = run_id_for("teacher_candidate", member, split, hashes["guideline"])
        if not (settings.runs_dir / run_id / "manifest.json").exists():
            raise ValidationFailed(f"ensemble member {member}: no run {run_id}")
        run = load_run_manifest(settings, run_id)
        if run.status != "complete":
            raise ValidationFailed(f"ensemble member {member}: {run_id} is not complete "
                                   f"(status {run.status})")
        if (run.guideline_sha256, run.schema_sha256, run.criteria_sha256) != (
                hashes["guideline"], hashes["schema"], hashes["criteria"]):
            raise ValidationFailed(f"ensemble member {member}: {run_id} was labeled with other "
                                   "frozen hashes")
        runs[member] = run
    return runs


def build_ensemble(settings: Settings, split: str = "main") -> dict[str, Any]:
    """Write the derived ensemble run from the frozen `teacher_ensemble` rule (FR-019b)."""
    frozen = verify_frozen(settings)
    scoring = settings.teacher_scoring()
    rule = scoring.teacher_ensemble
    members = sorted(rule.members)
    entry = settings.model(rule.model_id)
    if entry.backend != "ensemble" or entry.role != "teacher_candidate":
        raise ValidationFailed(f"{rule.model_id} must be configured with backend ensemble and "
                               "role teacher_candidate")
    runs = _member_runs(settings, members, split, frozen)
    min_iou = float(settings.pilot.get("min_iou", 0.3))
    chunks = chunk_map(settings, split)
    outputs = {m: load_outputs(settings, run.run_id) for m, run in runs.items()}
    combined = combine(outputs, members, rule.min_votes, chunks, min_iou,
                       rule=scoring.quote_repair)

    run_id = run_id_for("teacher_candidate", rule.model_id, split, frozen["hashes"]["guideline"])
    run_path = settings.runs_dir / run_id
    if run_path.exists():
        shutil.rmtree(run_path)  # derived and deterministic: rebuilt from the members
    now = datetime.now(UTC)
    manifest = LabelRunManifest(
        run_id=run_id,
        role="teacher_candidate",
        backend="ensemble",
        model_id=rule.model_id,
        model_version=" + ".join(f"{m}={runs[m].model_version}" for m in members),
        family=entry.family,
        host=entry.host,
        settings=RunSettings(temperature="not_settable", structured_output="post_validation",
                             max_retries=0, min_votes=rule.min_votes, min_iou=min_iou),
        guideline_sha256=frozen["hashes"]["guideline"],
        schema_sha256=frozen["hashes"]["schema"],
        criteria_sha256=frozen["hashes"]["criteria"],
        split=split,
        started_at=now,
        finished_at=now,
        cost_eur=round(sum(r.cost_eur for r in runs.values()), 6),
        excluded_chunks=[{"chunk_id": c, "reason": "no valid output from any member"}
                         for c, o in sorted(combined.items()) if o.relevant is None],
        license_basis="; ".join(f"{m}: {runs[m].license_basis}" for m in members),
        deviations=sorted({d for r in runs.values() for d in r.deviations}),
        status="complete",
        derived_from=[runs[m].run_id for m in members],
    )
    for chunk_id, out in sorted(combined.items()):
        if out.relevant is None:
            continue
        doc = ExtractionOutput.model_validate({
            "relevant": out.relevant,
            "items": [{"kind": it.kind, "quote": it.quote, "actor": it.actor,
                       "actor_type": it.actor_type, "statement": it.statement,
                       "evidence_type": it.evidence_type, "evidence_scope": it.evidence_scope}
                      for it in out.items]})
        write_json(run_path / "parsed" / f"{chunk_id}.json", doc.model_dump(mode="json"))
    data = manifest.model_dump(mode="json")
    # No model is called: token limit and seed do not apply (the contract allows no null here).
    data["settings"] = {k: v for k, v in data["settings"].items() if v is not None}
    write_json(run_path / "manifest.json", data)
    return {
        "run_id": run_id,
        "status": manifest.status,
        "derived_from": manifest.derived_from,
        "chunks": len(combined),
        "excluded": len(manifest.excluded_chunks),
        "items": sum(len(o.items) for o in combined.values()),
        "cost_eur": manifest.cost_eur,
    }
