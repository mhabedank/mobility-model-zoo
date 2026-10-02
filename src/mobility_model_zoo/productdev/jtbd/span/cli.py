"""`jtbd span …`: build, train, measure and release-check the span model (feature 004).

Registered as a sub-app of the `jtbd` CLI; `--config` is the global option before `span`.
"""

from __future__ import annotations

from pathlib import Path

import typer

app = typer.Typer(no_args_is_help=True,
                  help="Production span model: data check, rows, training, evaluation, results")


def _run(ctx: typer.Context, fn) -> None:
    from mobility_model_zoo.productdev.jtbd.cli import _run as run

    run(ctx, fn)


@app.command("data-check")
def data_check_cmd(ctx: typer.Context) -> None:
    """Verify provenance and report composition of the training dataset."""
    from mobility_model_zoo.productdev.jtbd.span.datacheck import data_check

    _run(ctx, data_check)


@app.command("build-rows")
def build_rows_cmd(ctx: typer.Context, run: str = typer.Option(..., "--run"),
                   recipe: str = typer.Option(None, "--recipe",
                                              help="Recipe (default span-xlmr.yaml)")) -> None:
    """Teacher run on the train split -> training rows with repaired quotes."""
    from mobility_model_zoo.productdev.jtbd.span.rows import build_rows

    _run(ctx, lambda s: build_rows(s, run, recipe))


@app.command("freeze-data")
def freeze_data_cmd(ctx: typer.Context) -> None:
    """Hash training chunks and rows; write the retention record."""
    from mobility_model_zoo.productdev.jtbd.span.rows import freeze_data

    _run(ctx, freeze_data)


@app.command("train")
def train_cmd(ctx: typer.Context,
              recipe: str = typer.Option(None, "--recipe", help="Recipe (default span-xlmr.yaml)"),
              out: Path = typer.Option(..., "--out", help="Directory for the model files"),
              device: str = typer.Option("cpu", "--device", help="cpu, cuda or mps"),
              max_epochs: int = typer.Option(
                  None, "--max-epochs", help="Override for smoke tests; recorded in the model")
              ) -> None:
    """Train one candidate on the frozen training rows (best epoch on validation rows)."""
    from mobility_model_zoo.productdev.jtbd.span.commands import train_command

    _run(ctx, lambda s: train_command(s, recipe, out, device, max_epochs))


@app.command("tune")
def tune_cmd(ctx: typer.Context, model_dir: Path = typer.Option(..., "--model-dir"),
             recipe: str = typer.Option(None, "--recipe")) -> None:
    """Tune unit and relevance thresholds on the validation rows only."""
    from mobility_model_zoo.productdev.jtbd.span.commands import tune_command

    _run(ctx, lambda s: tune_command(s, model_dir, recipe))


@app.command("label")
def label_cmd(ctx: typer.Context, model_dir: Path = typer.Option(..., "--model-dir"),
              split: str = typer.Option("main", "--split"),
              change: str = typer.Option(..., "--candidate-change",
                                         help="What this candidate changes and why"),
              recipe: str = typer.Option(None, "--recipe")) -> None:
    """Evaluate a candidate on the benchmark: a student run with backend span."""
    from mobility_model_zoo.productdev.jtbd.span.evaluate import label_span

    _run(ctx, lambda s: label_span(s, model_dir, split, change, recipe))


@app.command("select")
def select_cmd(ctx: typer.Context, recipe: str = typer.Option(None, "--recipe")) -> None:
    """Apply the recipe's selection rule to every evaluated candidate."""
    from mobility_model_zoo.productdev.jtbd.span.results import select

    _run(ctx, lambda s: select(s, recipe))


@app.command("results")
def results_cmd(ctx: typer.Context, run: str = typer.Option(..., "--run"),
                perf: Path = typer.Option(..., "--perf", help="Perf file of the same model"),
                version: str = typer.Option(..., "--version"),
                recipe: str = typer.Option(None, "--recipe")) -> None:
    """Write the zoo results files (quality.json, performance.json) for a version."""
    from mobility_model_zoo.productdev.jtbd.span.results import write_results

    _run(ctx, lambda s: write_results(s, run, perf, version, recipe))


@app.command("release-check")
def release_check_cmd(ctx: typer.Context, version: str = typer.Option(..., "--version"),
                      recipe: str = typer.Option(None, "--recipe")) -> None:
    """Evaluate the release bar from the results files (exit 1 if any condition fails)."""
    from mobility_model_zoo.productdev.jtbd.span.results import release_check

    _run(ctx, lambda s: release_check(s, version, recipe))


@app.command("pareto")
def pareto_cmd(ctx: typer.Context, recipe: str = typer.Option(None, "--recipe")) -> None:
    """Quality-vs-throughput figure with every candidate and the zero-shot baselines."""
    from mobility_model_zoo.productdev.jtbd.span.results import pareto

    _run(ctx, lambda s: pareto(s, recipe))


@app.command("record")
def record_cmd(ctx: typer.Context, version: str = typer.Option(..., "--version"),
               recipe: str = typer.Option(None, "--recipe")) -> None:
    """Fill the release record (provenance, teachers, recipe, evaluation, performance)."""
    from mobility_model_zoo.productdev.jtbd.span.results import write_record

    _run(ctx, lambda s: write_record(s, version, recipe))
