"""`security` command line: task tools of the security topic (specs/005-…/contracts/cli.md).

    security can-ids frames road|can-train-and-test [--out DIR]
    security can-ids forest evaluate|alarms|export|convert|testvectors [...]
    security can-ids mlp train [--epochs N] [--seed S] [--out DIR]
    security can-ids evaluate MODEL --benchmark can-ids-v1
    security can-ids freeze

Data and outputs live in $MMZ_DATA (default ~/.cache/mobility-model-zoo/datasets), never in the
repository. Training needs the `edge-train` extra.
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

BENCHMARK = "can-ids-v1"
NOT_FROZEN = 5  # exit code: missing input (contracts/cli.md)
PASSTHROUGH = {"allow_extra_args": True, "ignore_unknown_options": True, "help_option_names": []}

app = typer.Typer(no_args_is_help=True, add_completion=False, help="Task tools of the security topic.")
can_ids = typer.Typer(no_args_is_help=True, add_completion=False, help="CAN intrusion detection.")
app.add_typer(can_ids, name="can-ids")


def say(message: str) -> None:
    print(message, file=sys.stderr)


@can_ids.command()
def frames(
    dataset: str = typer.Argument(..., help="road or can-train-and-test"),
    out: Path = typer.Option(None, help="default $MMZ_DATA/derived/frames/<dataset>/"),
) -> None:
    """Convert a downloaded dataset into the common frame format (one Parquet file per capture)."""
    from mobility_model_zoo.datasets.download import dataset_dir
    from mobility_model_zoo.edge.paths import derived_dir
    from mobility_model_zoo.security.can_ids import frames as fmt

    readers = {"road": fmt.from_road, "can-train-and-test": fmt.from_can_train_and_test}
    if dataset not in readers:
        say(f"unknown dataset {dataset}; choose one of {', '.join(sorted(readers))}")
        raise typer.Exit(2)
    target = out or derived_dir("frames") / dataset
    n = 0
    for df in readers[dataset](dataset_dir(dataset)):
        capture = df["capture"].iat[0]
        fmt.write_parquet(df, target / f"{Path(capture).with_suffix('')}.parquet")
        n += 1
    say(f"{n} captures written to {target}")


@can_ids.command(context_settings=PASSTHROUGH)
def forest(ctx: typer.Context) -> None:
    """picket-forest pipeline: evaluate | alarms | export | convert | testvectors (see --help)."""
    from mobility_model_zoo.security.can_ids import forest as pipeline

    pipeline.main(ctx.args or ["--help"])


@can_ids.command(context_settings=PASSTHROUGH)
def mlp(ctx: typer.Context) -> None:
    """picket-mlp: `train [--epochs N] [--seed S] [--out DIR] [--download]`."""
    from mobility_model_zoo.security.can_ids import mlp as model

    if not ctx.args or ctx.args[0] != "train":
        say("usage: security can-ids mlp train [--epochs N] [--seed S] [--out DIR] [--download]")
        raise typer.Exit(2)
    model.main(ctx.args[1:])


@can_ids.command()
def evaluate(
    model: str = typer.Argument(..., help="picket-forest or picket-mlp"),
    benchmark: str = typer.Option(BENCHMARK, help="frozen benchmark id"),
) -> None:
    """Score a model on every split of the frozen benchmark (frame and event metrics)."""
    say(f"benchmark {benchmark} is not frozen yet: run `security can-ids freeze` first")
    raise typer.Exit(NOT_FROZEN)


def benchmark_sources(data: Path | None = None) -> dict[str, Path]:
    """Data roots of can-ids-v1 in the data cache (or below `data`)."""
    from mobility_model_zoo.datasets.download import dataset_dir

    root = (lambda ds: Path(data) / ds) if data else dataset_dir
    return {"can-train-and-test": root("can-train-and-test") / "extracted", "road": root("road")}


def benchmark_dir(benchmark: str = BENCHMARK) -> Path:
    from mobility_model_zoo.edge.paths import REPO_ROOT

    return REPO_ROOT / "topics" / "security" / "benchmarks" / benchmark


@can_ids.command()
def freeze(
    benchmark: str = typer.Option(BENCHMARK, help="benchmark version"),
    data: Path = typer.Option(None, help="folder with can-train-and-test/ and road/ ($MMZ_DATA)"),
) -> None:
    """Freeze the benchmark: manifest with hashes; duplicates must be resolved first."""
    from mobility_model_zoo.security.can_ids import benchmark as bm

    if benchmark != BENCHMARK:
        say(f"unknown benchmark {benchmark}; this version knows {BENCHMARK}")
        raise typer.Exit(2)
    sources = benchmark_sources(data)
    missing = [ds for ds, root in sources.items() if not root.exists()]
    if missing:
        say(f"not downloaded: {', '.join(missing)} (uv run zoo data download <id>)")
        raise typer.Exit(5)
    out = benchmark_dir(benchmark)
    try:
        manifest = bm.freeze(sources, out, out / "resolutions.yaml")
    except bm.UnresolvedDuplicates as e:
        say(str(e))
        say(f"record a resolution per group in {out / 'resolutions.yaml'} and run freeze again")
        raise typer.Exit(1) from None
    except bm.FrozenChanged as e:
        say(str(e))
        raise typer.Exit(3) from None
    roles: dict[str, int] = {}
    for c in manifest["captures"]:
        roles[c["role"]] = roles.get(c["role"], 0) + 1
    n = len(manifest["captures"])
    say(f"{benchmark}: {n} captures {roles}, frozen at {manifest['frozen_at']}")
