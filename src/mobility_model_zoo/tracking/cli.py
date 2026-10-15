"""`zoo tracking`: the experiment tracking server on the Spark (feature 017, contracts/cli.md)."""

from __future__ import annotations

import json
import sys

import typer

from mobility_model_zoo.release.errors import ZooError

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Experiment tracking (MLflow on the Spark): status, import of past results, audit.",
)


def say(message: str) -> None:
    print(message, file=sys.stderr)


def _run(fn) -> None:
    try:
        fn()
    except ZooError as e:
        say(f"error: {e}")
        raise typer.Exit(e.exit_code) from None


def _require():
    from . import config
    from .publish import TrackingUnavailable

    if not config.tracking_uri():
        raise TrackingUnavailable("no MLFLOW_TRACKING_URI; set it in .env (docs/tracking.md)")
    if not config.client_installed():
        raise TrackingUnavailable("the tracking client is not installed: uv sync --extra tracking")


@app.command("status")
def status_cmd(as_json: bool = typer.Option(False, "--json")) -> None:
    """Configured server, its version, and the experiments with their run counts (exit 8 if none)."""

    def fn() -> None:
        from . import client as tc
        from . import config
        from .publish import TrackingUnavailable

        _require()
        try:
            base = config.tracking_uri().rstrip("/")
            if base.startswith(("http://", "https://")):
                import requests

                version = requests.get(f"{base}/version", timeout=10).text.strip()
            else:
                version = "local store"
            cl = tc.new_client()
            experiments = {}
            for exp in cl.search_experiments():
                runs = cl.search_runs([exp.experiment_id], max_results=1000)
                experiments[exp.name] = len(runs)
        except Exception as e:  # noqa: BLE001
            raise TrackingUnavailable(
                f"server at {config.uri_host()} unreachable ({e.__class__.__name__}); "
                "is the tunnel open? scripts/spark/mlflow/mlflow.sh tunnel"
            ) from None
        out = {"server": config.uri_host(), "version": version, "experiments": experiments}
        if as_json:
            print(json.dumps(out, indent=2))
            return
        print(f"server      {out['server']} (mlflow {version})")
        for name, n in sorted(experiments.items()):
            print(f"  {name:38s} {n:>6} run(s)")

    _run(fn)


@app.command("audit")
def audit_cmd(
    experiment: list[str] = typer.Option(None, "--experiment", help="only these experiments"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Scan the store for anything but numbers, hashes and metadata (exit 7 on findings)."""

    def fn() -> None:
        from .audit import audit
        from .guard import GuardRefused
        from .publish import TrackingUnavailable

        _require()
        try:
            findings, notes = audit(experiment or None)
        except Exception as e:  # noqa: BLE001
            raise TrackingUnavailable(f"tracking server: {e.__class__.__name__}") from None
        if as_json:
            print(json.dumps([f.__dict__ | {"value": f.value[:12]} for f in findings], indent=2))
        else:
            for f in findings:
                print(f.line())
            for n in notes:
                say(n)
            say(f"audit: {len(findings)} finding(s)")
        if findings:
            raise GuardRefused(f"{len(findings)} finding(s) in the tracking store")

    _run(fn)
