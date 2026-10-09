"""`condmon` command line: task tools of the condition-monitoring topic (specs/005-…/contracts/cli.md).

    condmon sound-anomaly train|evaluate|freeze     hum-fan on MIMII 6 dB fan (mimii-fan-v1)
    condmon activity train|evaluate|freeze          pace-cnn on UCI HAR (uci-har-v1)

`train` takes `--epochs N --seed S --out DIR --download`. Data and outputs live in $MMZ_DATA, never
in the repository. Training needs the `edge-train` extra.
"""

from __future__ import annotations

import sys

import typer

NOT_FROZEN = 5  # exit code: missing input (contracts/cli.md)
PASSTHROUGH = {"allow_extra_args": True, "ignore_unknown_options": True}

app = typer.Typer(
    no_args_is_help=True, add_completion=False, help="Task tools of the condition-monitoring topic."
)


def say(message: str) -> None:
    print(message, file=sys.stderr)


def _task(name: str, benchmark: str, module: str, help_text: str) -> None:
    sub = typer.Typer(no_args_is_help=True, add_completion=False, help=help_text)

    @sub.command(context_settings=PASSTHROUGH)
    def train(ctx: typer.Context) -> None:
        """Train, export to int8 and report (`--epochs N --seed S --out DIR --download`)."""
        import importlib

        importlib.import_module(module).main(ctx.args)

    @sub.command()
    def evaluate(model: str = typer.Argument(None)) -> None:
        """Score a model on the frozen benchmark."""
        say(f"benchmark {benchmark} is not frozen yet: run `condmon {name} freeze` first")
        raise typer.Exit(NOT_FROZEN)

    @sub.command()
    def freeze() -> None:
        """Freeze the benchmark (split manifest with hashes)."""
        say(f"benchmark {benchmark}: freezing needs the dataset declarations of feature 005 US3")
        raise typer.Exit(NOT_FROZEN)

    app.add_typer(sub, name=name)


_task(
    "sound-anomaly",
    "mimii-fan-v1",
    "mobility_model_zoo.condition_monitoring.sound_anomaly.train",
    "hum-fan: machine-sound anomaly detection.",
)
_task(
    "activity",
    "uci-har-v1",
    "mobility_model_zoo.condition_monitoring.activity.train",
    "pace-cnn: human activity recognition.",
)
