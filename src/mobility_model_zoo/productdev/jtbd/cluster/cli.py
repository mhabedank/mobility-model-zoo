"""`jtbd cluster …`: deduplicate and cluster JTBD items (feature 009, contracts/cli.md).

Registered as a sub-app of the `jtbd` CLI. `run` and `check` work on bundles and map directories
and need no JTBD config; `collect` reads the stored corpus through the global `--config`.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import typer

from mobility_model_zoo.productdev.jtbd.errors import PilotError, ValidationFailed

DEFAULT_SETTINGS = Path("configs/productdev/jtbd/cluster-baseline.yaml")

app = typer.Typer(no_args_is_help=True,
                  help="Deduplicate and cluster JTBD items into opportunity maps (feature 009)")


def _run(ctx: typer.Context, fn) -> None:
    from mobility_model_zoo.productdev.jtbd.cli import _run as run

    run(ctx, fn)


def _plain(fn: Callable[[], Any]) -> None:
    """Run without JTBD settings; map errors to exit codes, print a JSON summary."""
    try:
        result = fn()
    except PilotError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise typer.Exit(exc.exit_code) from exc
    if result is not None:
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


@app.command("collect")
def collect_cmd(ctx: typer.Context, run: str = typer.Option(..., "--run", help="Span run id"),
                out: Path = typer.Option(..., "--out", help="Bundle file to write")) -> None:
    """Span run over stored chunks -> jtbd-cluster-input-v1 bundle."""
    from mobility_model_zoo.productdev.jtbd.cluster.collect import collect

    _run(ctx, lambda s: collect(s, run, out))


@app.command("extract")
def extract_cmd(ctx: typer.Context,
                model_dir: Path = typer.Option(..., "--model-dir", help="Released span model"),
                split: str = typer.Option("main", "--split")) -> None:
    """Span model over the stored chunks of a corpus config -> span run for the benchmark pool."""
    from mobility_model_zoo.productdev.jtbd.cluster.collect import extract

    _run(ctx, lambda s: extract(s, model_dir, split))


@app.command("run")
def run_cmd(inputs: list[Path] = typer.Option(..., "--input", help="Bundle file (repeatable)"),
            map_dir: Path = typer.Option(None, "--map", help="Map directory to write"),
            settings: Path = typer.Option(DEFAULT_SETTINGS, "--settings",
                                          help="Stage settings")) -> None:
    """Deduplicate the items of the bundles and write result.json into the map directory."""

    def go() -> dict[str, Any]:
        from mobility_model_zoo.productdev.jtbd.cluster.bundle import read_bundles
        from mobility_model_zoo.productdev.jtbd.cluster.stage import ClusterStage

        stage = ClusterStage.from_settings(settings)
        result = stage.run(read_bundles(inputs), map_dir=map_dir, bundle_paths=inputs)
        failed = [c["name"] for c in result["checks"]["results"] if not c["passed"]]
        if failed:
            raise ValidationFailed(f"deterministic checks failed: {', '.join(failed)}")
        return {"map": str(map_dir) if map_dir else None, "sources": result["inputs"]["sources"],
                "items": result["inputs"]["items"], "groups": len(result["groups"]),
                "clusters": len(result["clusters"])}

    _plain(go)


@app.command("check")
def check_cmd(map_dir: Path = typer.Option(..., "--map", help="Map directory"),
              inputs: list[Path] = typer.Option(None, "--input",
                                                help="Bundles (default: those named in the result)")
              ) -> None:
    """Deterministic checks of result.json against the format and the input bundles."""

    def go() -> dict[str, Any]:
        from mobility_model_zoo.productdev.jtbd.cluster.bundle import (
            file_sha256,
            items_from,
            read_bundles,
        )
        from mobility_model_zoo.productdev.jtbd.cluster.checks import check_result

        path = map_dir / "result.json"
        if not path.exists():
            raise ValidationFailed(f"no result in {map_dir}")
        result = json.loads(path.read_text(encoding="utf-8"))
        bundles = list(inputs or [Path(p) for p in result.get("inputs", {}).get("bundle_paths", [])])
        quotes = None
        if bundles:
            recorded = set(result.get("inputs", {}).get("bundles", []))
            changed = [str(b) for b in bundles if recorded and file_sha256(b) not in recorded]
            if changed:
                raise ValidationFailed(f"bundles changed since the run: {', '.join(changed)}")
            quotes = {i.item_id: i.quote for i in items_from(read_bundles(bundles))}
        checks = check_result(result, quotes)
        failed = [c for c in checks if not c["passed"]]
        for c in failed:
            print(f"failed: {c['name']} ({c['count']}): {', '.join(c['offending'])}", file=sys.stderr)
        if failed:
            raise ValidationFailed(f"{len(failed)} of {len(checks)} checks failed")
        return {"checks": len(checks), "passed": True,
                "skipped": [c["name"] for c in checks if c.get("skipped")]}

    _plain(go)


@app.command("report")
def report_cmd(map_dir: Path = typer.Option(..., "--map", help="Map directory with result.json"),
               out: Path = typer.Option(None, "--out", help="Directory for the views "
                                                            "(default: the map directory)")
               ) -> None:
    """tree.md (opportunity tree) and needs.csv (groups by kind), rendered from result.json."""
    from mobility_model_zoo.productdev.jtbd.cluster.report import write_report

    _plain(lambda: write_report(map_dir, out))


# ---- building and measuring (user story 2; global --config cluster-v1.yaml) ----------------------

bench_app = typer.Typer(no_args_is_help=True, help="Benchmark cluster-v1: pool, pairs and sets")
app.add_typer(bench_app, name="bench")


@bench_app.command("build")
def bench_build_cmd(ctx: typer.Context) -> None:
    """Item pool, split by snapshot, stratified pairs and neighbourhood sets (research R10)."""
    from mobility_model_zoo.productdev.jtbd.cluster.bench import build

    _run(ctx, build)


@app.command("freeze")
def freeze_cmd(ctx: typer.Context) -> None:
    """Freeze guideline, examples, prompt, wire schema, criteria, budget and benchmark lists."""
    from mobility_model_zoo.productdev.jtbd.cluster.bench import freeze

    _run(ctx, freeze)


@app.command("label")
def label_cmd(ctx: typer.Context, model: str = typer.Option(..., "--model", help="Reference model id"),
              split: str = typer.Option(..., "--split", help="dev, test or holdout"),
              limit: int = typer.Option(None, "--limit", help="Label at most this many units"),
              retry_excluded: str = typer.Option(
                  None, "--retry-excluded",
                  help="Reason for labeling the run's excluded units again (cause on our side)")
              ) -> None:
    """Label pairs and sets of one split with one reference model (research R11)."""
    from mobility_model_zoo.productdev.jtbd.cluster.label import label

    _run(ctx, lambda s: label(s, model, split, limit, retry_excluded))


@app.command("agreement")
def agreement_cmd(ctx: typer.Context,
                  split: str = typer.Option(..., "--split", help="dev, test or holdout")) -> None:
    """Reference-vs-reference agreement per level with CIs, consensus and contested pairs."""
    from mobility_model_zoo.productdev.jtbd.cluster.metrics import run_agreement

    def go(s):
        result = run_agreement(s, split)
        return {k: result[k] for k in ("split", "references", "levels", "consensus_pairs",
                                       "contested_pairs")}

    _run(ctx, go)


@app.command("decide")
def decide_cmd(ctx: typer.Context) -> None:
    """Apply the frozen criteria: go, revise or rethink per level (spec FR-024)."""
    from mobility_model_zoo.productdev.jtbd.cluster.decide import decide

    _run(ctx, decide)


@app.command("tune")
def tune_cmd(ctx: typer.Context,
             settings: Path = typer.Option(..., "--settings", help="Stage settings to tune"),
             split: str = typer.Option(..., "--split", help="Only dev is allowed"),
             out: Path = typer.Option(None, "--out", help="Tuned settings file")) -> None:
    """Grid search of t_dup on development pairs; writes a new settings file with the grid."""
    from mobility_model_zoo.productdev.jtbd.cluster.tune import tune

    _run(ctx, lambda s: tune(s, settings, split, out))


@app.command("score")
def score_cmd(ctx: typer.Context,
              settings: Path = typer.Option(..., "--settings", help="Candidate stage settings")) -> None:
    """Run one candidate on the test pool and score it per level against the consensus."""
    from mobility_model_zoo.productdev.jtbd.cluster.score import score

    _run(ctx, lambda s: score(s, settings))


# ---- corrections and annotations (user stories 4 and 5) ------------------------------------------

correct_app = typer.Typer(no_args_is_help=True,
                          help="Append one structure correction to <map>/corrections.yaml")
app.add_typer(correct_app, name="correct")
MAP = typer.Option(..., "--map", help="Map directory")
NOTE = typer.Option(None, "--note", help="Why (kept in the file)")


def _correct(map_dir: Path, op: dict[str, Any], note: str | None) -> None:
    from mobility_model_zoo.productdev.jtbd.cluster import corrections

    if note:
        op["note"] = note
    _plain(lambda: {"index": corrections.append(map_dir, op), "op": op["op"]})


@correct_app.command("merge")
def correct_merge(items: list[str] = typer.Argument(..., help="One item id per group to merge"),
                  map_dir: Path = MAP, note: str = NOTE) -> None:
    """The groups of these items become one group (refused across kinds)."""
    _correct(map_dir, {"op": "merge", "items": items}, note)


@correct_app.command("split")
def correct_split(sets: list[str] = typer.Option(..., "--set",
                                                 help="Comma-separated item ids (repeat per set)"),
                  map_dir: Path = MAP, note: str = NOTE) -> None:
    """These item sets never share a group; the other members go to the nearest set."""
    _correct(map_dir, {"op": "split", "sets": [s.split(",") for s in sets]}, note)


@correct_app.command("move")
def correct_move(item: str = typer.Argument(..., help="An item of the group to move"),
                 under: str = typer.Option(None, "--under", help="An item of the new parent"),
                 top: bool = typer.Option(False, "--top", help="Make the group top-level"),
                 into: str = typer.Option("group", "--into",
                                          help="group (specificity link) or cluster"),
                 map_dir: Path = MAP, note: str = NOTE) -> None:
    """Pin a group under the group (or, with --into cluster, the cluster) of another item."""
    if top == (under is not None):
        raise typer.BadParameter("give exactly one of --under and --top")
    op = {"op": "move", "item": item, "under": under}
    if into != "group":
        op["into"] = into
    _correct(map_dir, op, note)


@correct_app.command("representative")
def correct_representative(item: str = typer.Argument(..., help="The new representative"),
                           map_dir: Path = MAP, note: str = NOTE) -> None:
    """The item becomes its group's representative."""
    _correct(map_dir, {"op": "representative", "item": item}, note)


@app.command("annotate")
def annotate_cmd(map_dir: Path = MAP,
                 node: str = typer.Option(..., "--node", help="dg- or cl- id"),
                 statement: str = typer.Option(None, "--statement", help="Statement text"),
                 assign: list[str] = typer.Option(None, "--assign", help="scheme=value (repeat)"),
                 by: str = typer.Option(..., "--by", help="person or model:<id>")) -> None:
    """Append a statement or assignments for a node to <map>/annotations.jsonl."""
    from datetime import date

    from mobility_model_zoo.productdev.jtbd.cluster import annotation

    line: dict[str, Any] = {"node": node}
    if statement:
        line["statement"] = {"text": statement, "by": by, "at": date.today().isoformat()}
    pairs = [a.split("=", 1) for a in assign or []]
    if any(len(p) != 2 for p in pairs):
        raise typer.BadParameter("--assign takes scheme=value")
    if pairs:
        line["assignments"] = [{"scheme": s, "value": v, "origin": by} for s, v in pairs]

    def go() -> dict[str, Any]:
        annotation.append(map_dir, line)
        return {"node": node, "statement": bool(statement), "assignments": len(pairs)}

    _plain(go)


@app.command("perf")
def perf_cmd(ctx: typer.Context,
             settings: Path = typer.Option(..., "--settings", help="Stage settings to measure"),
             scale: int = typer.Option(None, "--scale", help="Scale set of at least N items"),
             hardware: str = typer.Option(None, "--hardware", help="Label of the machine")) -> None:
    """Wall time and peak memory of one stage run in a child process, offline (research R17)."""
    from mobility_model_zoo.productdev.jtbd.cluster.perf import perf

    _run(ctx, lambda s: perf(s, settings, scale, hardware))
