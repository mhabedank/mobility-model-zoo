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
    detector: str = typer.Argument(..., help="picket-forest, a control, a baseline, or all"),
    benchmark: str = typer.Option(BENCHMARK, help="frozen benchmark id"),
    sets: list[str] = typer.Option(None, "--sets", help="only these sets (partial run)"),
    report: bool = typer.Option(False, help="write report, metrics and quality results"),
    data: Path = typer.Option(None, help="folder with can-train-and-test/ and road/ ($MMZ_DATA)"),
    from_run: bool = typer.Option(
        False, "--from-run", help="recompute metrics and outcome from the stored run (no training)"
    ),
) -> None:
    """Score detectors on the frozen benchmark (same harness and protocol for all)."""
    import json

    from mobility_model_zoo.edge.paths import REPO_ROOT, derived_dir
    from mobility_model_zoo.security.can_ids import benchmark as bm
    from mobility_model_zoo.security.can_ids import evaluate as ev
    from mobility_model_zoo.security.can_ids.detectors import registry

    manifest_path = benchmark_dir(benchmark) / "manifest.json"
    if not manifest_path.exists():
        say(f"benchmark {benchmark} is not frozen yet: run `security can-ids freeze` first")
        raise typer.Exit(NOT_FROZEN)
    names = list(registry()) if detector == "all" else [detector]
    unknown = [n for n in names if n not in registry()]
    if unknown:
        say(f"unknown detector {unknown[0]}; choose from {', '.join(registry())} or all")
        raise typer.Exit(2)
    manifest = json.loads(manifest_path.read_text())
    sources = benchmark_sources(data)
    cache = derived_dir("picket-forest") / "features"
    runs = derived_dir("can-ids-v1") / "runs"
    if from_run:
        stored = runs / f"{detector}.json"
        if not stored.exists():
            say(f"no stored run {stored}")
            raise typer.Exit(2)
        result = ev.rejudge(json.loads(stored.read_text()))
    else:
        try:
            result = ev.run(names, manifest, sources, sets=sets or None, cache=cache)
            if "picket-forest" in names and not sets:
                result["road"] = ev.evaluate_road(manifest, sources, cache)
        except bm.CaptureChanged as e:
            say(str(e))
            raise typer.Exit(1) from None
    runs.mkdir(parents=True, exist_ok=True)
    (runs / f"{detector}.json").write_text(json.dumps(result, indent=1, default=float) + "\n")
    o = result["outcome"]
    say(f"outcome: {o['verdict']} - {' '.join(o['reasons'])}")
    if report:
        out = REPO_ROOT / "topics" / "security" / "reports" / "picket-forest" / benchmark
        ev.write_report(result, out)
        say(f"report: {out / 'report.md'}")
        if result["partial"]:
            say("partial run: quality results not written")
        elif "picket-forest" in names:
            q = REPO_ROOT / "zoo" / "models" / "picket-forest" / "results" / "0.1.0" / "quality.json"
            ev.write_quality(result, q, "picket-forest", "0.1.0")
            say(f"quality results: {q}")


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


@can_ids.command()
def measure(
    target: str = typer.Option("host", help="host, esp32-qemu, esp8266, esp32 or mkrzero"),
    board: str = typer.Option(None, "-b", "--board", help="board id in hil/boards.yaml (esp8266)"),
    export: Path = typer.Option(None, help="exported model ($MMZ_DATA/derived/picket-forest/export)"),
    out: Path = typer.Option(None, help="performance results file to merge into"),
) -> None:
    """Measure the whole detection chain and merge the metrics into a results file."""
    from mobility_model_zoo.edge.paths import REPO_ROOT, derived_dir
    from mobility_model_zoo.security.can_ids import measure as m

    export = export or derived_dir("picket-forest") / "export"
    if not (export / "picket_forest_model.h").exists():
        say(f"no exported model in {export}: run `security can-ids forest export` first")
        raise typer.Exit(5)
    out = out or REPO_ROOT / "zoo/models/picket-forest/results/0.1.0/performance.json"
    if target == "host":
        run = m.run_host(export)
    elif target == "esp32-qemu":
        run = m.run_qemu(export)
    elif target == "esp8266":
        if not board:
            say("esp8266 needs -b BOARD (see `uv run edge list`)")
            raise typer.Exit(2)
        run = m.run_board(export, board)
    elif target == "esp32":
        if not board:
            say("esp32 needs -b BOARD (see `uv run edge list`)")
            raise typer.Exit(2)
        run = m.run_board(export, board, env="esp32")
    elif target == "mkrzero":
        if not board:
            say("mkrzero needs -b BOARD (see `uv run edge list`)")
            raise typer.Exit(2)
        run = m.run_mkrzero(export, board)
    else:
        say(f"unknown target {target}")
        raise typer.Exit(2)
    try:
        new = m.metrics(target, run)
    except ValueError as e:
        say(str(e))
        raise typer.Exit(1) from None
    # results/<version>/performance.json; other paths keep the version given in the file name or 0.2.0
    version = out.parent.name if out.parent.name[:1].isdigit() else "0.2.0"
    m.merge(out, new, "picket-forest", version)
    for metric in new:
        where = f"{metric['origin']}, {metric['hardware']}"
        say(f"{metric['name']}: {metric['value']} {metric['unit']} ({where})")


v2 = typer.Typer(no_args_is_help=True, add_completion=False, help="picket-forest 0.2.0 (calibrated).")
can_ids.add_typer(v2, name="v2")
V2_BENCHMARK = "can-ids-v3"


@v2.command("export")
def v2_export(
    out: Path = typer.Option(
        None, help="export folder (default $MMZ_DATA/derived/picket-forest/export-v2)"
    ),
) -> None:
    """Train the release model on can-ids-v3; write headers, joblib, C sources, SBOM; C = Python."""
    import json

    from mobility_model_zoo.datasets import require_training_allowed
    from mobility_model_zoo.edge.paths import derived_dir
    from mobility_model_zoo.security.can_ids import calibrated as cal
    from mobility_model_zoo.security.can_ids import evaluate as ev
    from mobility_model_zoo.security.can_ids import release_export_v2 as rx

    require_training_allowed("can-train-and-test", model="picket-forest")
    path = benchmark_dir(V2_BENCHMARK) / "manifest.json"
    if not path.exists():
        say(f"benchmark {V2_BENCHMARK} is not frozen")
        raise typer.Exit(NOT_FROZEN)
    manifest = json.loads(path.read_text())
    sources, cache = benchmark_sources(), derived_dir("picket-forest") / "features"
    by_id = {c["id"]: c for c in manifest["captures"]}
    table = cal.calibrate(
        [
            ev.load_capture(by_id[i], sources, cache)
            for i in manifest["calibration"]["road"]["road-vehicle"]
        ]
    )
    road_test = [
        ev.load_capture(c, sources, cache)
        for c in manifest["captures"]
        if c["dataset"] == "road" and c["role"] == "test"
    ]
    target = out or derived_dir("picket-forest") / "export-v2"
    config = rx.export(target, manifest, sources, cache, road_test, table)
    say(
        json.dumps(
            {k: config[k] for k in ("frame_threshold", "decision", "tree_nodes", "parity_c_vs_python")},
            default=float,
        )
    )
    say(f"export: {target}")


@v2.command("examples")
def v2_examples(
    export: Path = typer.Option(None, help="export folder"),
    out: Path = typer.Option(None, help="examples folder (default zoo/models/picket-forest/examples)"),
) -> None:
    """Write the synthetic release examples with expected scores and alarms from the staged C chain."""
    import shutil

    from mobility_model_zoo.edge.paths import REPO_ROOT, derived_dir
    from mobility_model_zoo.security.can_ids import release_export_v2 as rx

    src = export or derived_dir("picket-forest") / "export-v2"
    target = out or REPO_ROOT / "zoo" / "models" / "picket-forest" / "examples"
    staged = src / "examples"  # published with the release, next to the model (feature 013)
    staged.mkdir(exist_ok=True)
    for p in rx.write_examples(src, target):
        shutil.copy(p, staged / p.name)
        say(str(p))


@v2.command("table")
def v2_table(
    log: list[Path] = typer.Argument(..., help="candump logs of benign traffic of your vehicle"),
    out: Path = typer.Option(Path("picket_forest_table.h"), help="header to write"),
    minutes: float = typer.Option(None, help="use at most this many minutes"),
) -> None:
    """Calibration table of your vehicle from benign candump logs (cover driving, idle and parked).

    Writes the C header for the device and, next to it, the same table as JSON for the Python
    reference (`picket_forest.load_table`)."""
    from mobility_model_zoo.security.can_ids import picket_forest as pf
    from mobility_model_zoo.security.can_ids import release_export_v2 as rx

    caps = [pf.read_candump(p) for p in log]
    table = pf.calibrate(caps, max_seconds=None if minutes is None else minutes * 60)
    note = ", ".join(p.name for p in log)
    rx.table_header(table, out, note)
    json_out = out.with_suffix(".json")
    pf.save_table(table, json_out, note)
    say(f"{out} and {json_out}: {len(table.known)} IDs, {table.seconds / 60:.1f} min")
    if table.seconds < 3600:
        say("warning: less than 60 min of calibration; false alarms rise sharply with short calibration")


@v2.command("table-json")
def v2_table_json(
    header: Path = typer.Option(..., "--from-header", help="a picket_forest_table.h of a release"),
    out: Path = typer.Option(Path("calibration_table.json"), help="JSON file to write"),
) -> None:
    """The calibration table of an existing header as JSON (repacks a release without retraining)."""
    from mobility_model_zoo.security.can_ids import picket_forest as pf

    table = pf.table_from_header(header.read_text(encoding="utf-8"))
    pf.save_table(table, out, f"from {header.name}")
    say(f"{out}: {len(table.known)} IDs")
