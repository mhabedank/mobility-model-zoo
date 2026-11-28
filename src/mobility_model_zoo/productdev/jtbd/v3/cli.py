"""`jtbd v3 …`: benchmark steps of pilot-v3 (contracts/cli.md of feature 025)."""

from __future__ import annotations

import typer

app = typer.Typer(
    no_args_is_help=True,
    help="Benchmark pilot-v3: separation, samples, freeze, agreement, decision.",
)
