"""`zoo` command line: the release tool (specs/003-model-zoo-hf-release/contracts/cli.md).

Human-readable messages go to stderr. Tokens are read from the environment only and never printed.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import typer

from mobility_model_zoo.release.errors import GateFailed, UsageError, ZooError

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Release tool of the mobility model zoo: validate, stage, check, build, preview, publish.",
)


def _say(message: str) -> None:
    print(message, file=sys.stderr)


def _run(fn: Callable[[], Any]) -> None:
    """Run a command and map release errors to the exit codes of contracts/cli.md."""
    try:
        fn()
    except GateFailed as e:
        for failure in e.failures:
            _say(f"FAIL: {failure}")
        raise typer.Exit(e.exit_code) from None
    except ZooError as e:
        _say(f"error: {e}")
        raise typer.Exit(e.exit_code) from None


def _root() -> Path:
    return Path.cwd()


def _not_yet(name: str) -> Callable[[], None]:
    def fn() -> None:
        raise UsageError(f"`zoo {name}` is not implemented yet")

    return fn


@app.command("validate")
def validate_cmd(
    model: str | None = typer.Argument(None), all_models: bool = typer.Option(False, "--all")
) -> None:
    """Offline checks of the registry (no network)."""
    _run(_not_yet("validate"))


@app.command("init-model")
def init_model_cmd(model: str) -> None:
    """Create the model's private staging repo (release token)."""
    _run(_not_yet("init-model"))


@app.command("stage")
def stage_cmd(model: str, version: str, src: Path = typer.Option(..., "--from")) -> None:
    """Upload trained model files to the private staging repo (staging token)."""
    _run(_not_yet("stage"))


@app.command("check")
def check_cmd(model: str, version: str, offline: bool = typer.Option(False, "--offline")) -> None:
    """Run the release gate."""
    _run(_not_yet("check"))


@app.command("build")
def build_cmd(model: str, version: str, out: Path = typer.Option(..., "--out")) -> None:
    """Gate, download the staged files and render the model card."""
    _run(_not_yet("build"))


@app.command("preview")
def preview_cmd(model: str, version: str, build: Path = typer.Option(..., "--build")) -> None:
    """Upload the build to the staging branch rc-v<version> for review."""
    _run(_not_yet("preview"))


@app.command("publish")
def publish_cmd(model: str, version: str, confirm: str = typer.Option(..., "--confirm")) -> None:
    """Publish the reviewed preview (the owner's approval)."""
    _run(_not_yet("publish"))


@app.command("deprecate")
def deprecate_cmd(
    model: str,
    version: str,
    reason: str = typer.Option(..., "--reason"),
    successor: str | None = typer.Option(None, "--successor"),
) -> None:
    """Mark a published version as deprecated."""
    _run(_not_yet("deprecate"))


@app.command("index")
def index_cmd() -> None:
    """Regenerate zoo/MODELS.md."""
    _run(_not_yet("index"))


@app.command("audit")
def audit_cmd(model: str | None = typer.Argument(None)) -> None:
    """Compare published tags and cards with the release records."""
    _run(_not_yet("audit"))


@app.command("history-check")
def history_check_cmd() -> None:
    """Scan the git history for data files and secrets."""
    _run(_not_yet("history-check"))
