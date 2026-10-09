"""`zoo site`: build, check and preview the website (specs/008-zoo-website/contracts/cli.md)."""

from __future__ import annotations

import sys
from pathlib import Path

import typer

app = typer.Typer(
    no_args_is_help=True, add_completion=False, help="The zoo website: build, check, serve."
)

OUT = typer.Option(Path("_site"), "--out", help="Output directory of the site.")


def say(message: str) -> None:
    print(message, file=sys.stderr)


def _run(fn) -> None:
    from mobility_model_zoo.release.cli import _run as run

    run(fn)


@app.command("build")
def build_cmd(
    out: Path = OUT,
    offline: bool = typer.Option(False, "--offline", help="Use cached example outputs only."),
    refresh: bool = typer.Option(False, "--refresh-examples", help="Ignore the example cache."),
) -> None:
    """Render every page from the registry into the output directory."""

    def fn() -> None:
        from mobility_model_zoo.release.cli import _registry
        from mobility_model_zoo.site.build import build

        build(_registry(), out, offline=offline, refresh=refresh, say=say)

    _run(fn)


@app.command("check")
def check_cmd(
    out: Path = OUT,
    a11y: bool = typer.Option(False, "--a11y/--no-a11y", help="Browser checks (needs Playwright)."),
    only: str = typer.Option("", "--only", help="Comma-separated check ids, e.g. L1,P1."),
    offline: bool = typer.Option(False, "--offline", help="Skip external link checks (L2)."),
) -> None:
    """Run the checks of contracts/checks.md against a built site."""

    def fn() -> None:
        from mobility_model_zoo.release.cli import _registry
        from mobility_model_zoo.site.check import run_checks

        ids = {i.strip() for i in only.split(",") if i.strip()} or None
        run_checks(_registry(), out, a11y=a11y, only=ids, offline=offline, say=say)

    _run(fn)


@app.command("serve")
def serve_cmd(out: Path = OUT, port: int = typer.Option(8000, "--port")) -> None:
    """Serve the built site locally under /mobility-model-zoo/, like GitHub Pages."""
    from mobility_model_zoo.site.serve import serve

    say(f"http://localhost:{port}/mobility-model-zoo/  (Ctrl+C to stop)")
    serve(out, port)
