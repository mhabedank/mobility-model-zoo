"""`condmon` command line: task tools of the condition-monitoring topic (specs/005-…/contracts/cli.md,
specs/021-pace-cnn-first-release/contracts/cli.md).

    condmon sound-anomaly train|evaluate|freeze     hum-fan on MIMII 6 dB fan (mimii-fan-v1)
    condmon activity freeze                          pace-cnn: freeze benchmark uci-har-v1
    condmon activity train --seed N [--out DIR]      one pre-registered run
    condmon activity evaluate [--version V]          report, quality results and verdict
    condmon activity reproduce                       retrain the candidate seed and compare
    condmon activity export --version V --out DIR    the upload folder of a release

Exit codes: 0 ok, 2 usage error, 3 refused (frozen benchmark or pre-registration), 4 check failed,
5 not implemented. Data and run outputs live in $MMZ_DATA, never in the repository. Training needs
the `edge-train` extra.
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

REFUSED = 3
CHECK_FAILED = 4
NOT_FROZEN = 5  # exit code: missing input or not implemented (feature 005 contracts/cli.md)
PASSTHROUGH = {"allow_extra_args": True, "ignore_unknown_options": True}

app = typer.Typer(
    no_args_is_help=True, add_completion=False, help="Task tools of the condition-monitoring topic."
)


def say(message: str) -> None:
    print(message, file=sys.stderr)


def _stub_task(name: str, benchmark: str, module: str, help_text: str) -> None:
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


_stub_task(
    "sound-anomaly",
    "mimii-fan-v1",
    "mobility_model_zoo.condition_monitoring.sound_anomaly.train",
    "hum-fan: machine-sound anomaly detection.",
)

activity = typer.Typer(
    no_args_is_help=True, add_completion=False, help="pace-cnn: human activity recognition."
)
app.add_typer(activity, name="activity")


def _licence_check() -> None:
    """The licence of the downloaded copy equals the declaration, and training is allowed."""
    import json

    from mobility_model_zoo.condition_monitoring.activity import train as pace
    from mobility_model_zoo.datasets import require_training_allowed
    from mobility_model_zoo.datasets.download import dataset_dir
    from mobility_model_zoo.datasets.registry import load

    declared = load()
    for ds in pace.DATASETS:
        require_training_allowed(ds, model=pace.NAME)
        src = dataset_dir(ds) / "SOURCE.json"
        if not src.exists():
            raise FileNotFoundError(f"{ds} not downloaded: zoo data download {ds}")
        got = json.loads(src.read_text(encoding="utf-8"))["license"]
        if got != declared[ds].license:
            raise ValueError(f"{ds}: downloaded licence {got} differs from the declaration")


@activity.command()
def freeze() -> None:
    """Freeze benchmark uci-har-v1 (manifest with hashes, no subject numbers)."""
    from mobility_model_zoo.condition_monitoring import benchmark as bm
    from mobility_model_zoo.condition_monitoring.activity import train as pace

    try:
        _licence_check()
        manifest = pace.build_manifest()
    except SystemExit as e:  # load_har: dataset not downloaded
        say(str(e.code))
        raise typer.Exit(CHECK_FAILED) from None
    except Exception as e:  # missing download, licence mismatch, declaration refuses
        say(f"freeze refused: {e}")
        raise typer.Exit(CHECK_FAILED) from None
    path = pace.manifest_path()
    try:
        _, written = bm.freeze(path, manifest)
    except bm.FrozenChanged as e:
        say(str(e))
        raise typer.Exit(REFUSED) from None
    rel = path.relative_to(bm.repo()) if path.is_relative_to(bm.repo()) else path
    splits = manifest["splits"]
    counts = "/".join(str(splits[s]["subjects"]) for s in ("train", "validation", "test"))
    say(
        f"{'wrote' if written else 'unchanged'} {rel}: subjects {counts}, "
        f"{splits['test']['windows']} test windows"
    )


@activity.command(context_settings=PASSTHROUGH)
def train(ctx: typer.Context) -> None:
    """One pre-registered run (`--seed N --out DIR --download`); epochs come from the recipe."""
    from mobility_model_zoo.condition_monitoring.activity import train as pace

    pace.main(ctx.args)


@activity.command()
def evaluate(version: str = typer.Option("0.1.0", "--version")) -> None:
    """Evaluate the pre-registered runs on uci-har-v1 and derive the status by rule."""
    from mobility_model_zoo.condition_monitoring.activity import evaluate as ev

    try:
        verdict = ev.evaluate(version)
    except ev.EvaluationRefused as e:
        say(f"refused: {e}")
        raise typer.Exit(REFUSED) from None
    except ev.DeterministicCheckFailed as e:
        say(f"deterministic check failed, release blocked: {e}")
        raise typer.Exit(CHECK_FAILED) from None
    print(f"status: {verdict['status']}")
    for reason in verdict["reasons"]:
        print(f"  missed: {reason}")
    if verdict["kill"]["fired"]:
        print(f"  kill criteria fired: {', '.join(verdict['kill']['fired'])}")


@activity.command()
def reproduce() -> None:
    """Retrain the candidate seed in a temporary folder and compare it with the stored run."""
    from mobility_model_zoo.condition_monitoring.activity import evaluate as ev

    result = ev.reproduce()
    if result["identical"]:
        print(f"identical: seed {result['seed']} reproduces the same model parameters")
    else:
        print(f"differs: seed {result['seed']}, deviation {result['deviation']}")


@activity.command()
def export(
    version: str = typer.Option("0.1.0", "--version"),
    out: Path = typer.Option(..., "--out", help="upload folder to write"),
) -> None:
    """Write the upload folder of a release (model files, C sources, config, examples, SBOM)."""
    from mobility_model_zoo.condition_monitoring.activity import release

    try:
        result = release.export(version, out)
    except release.ExportRefused as e:
        say(f"export refused: {e}")
        raise typer.Exit(CHECK_FAILED) from None
    for name in result["files"]:
        print(name)
    say(f"wrote {len(result['files'])} files to {out}")
