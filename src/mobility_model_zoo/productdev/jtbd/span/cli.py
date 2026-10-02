"""`jtbd span …`: build, train, measure and release-check the span model (feature 004).

Registered as a sub-app of the `jtbd` CLI; `--config` is the global option before `span`.
"""

from __future__ import annotations

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
