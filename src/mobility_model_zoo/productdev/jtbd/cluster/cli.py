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
