"""`zoo roadmap`: check the roadmap record and write the pace review of a quarter (feature 015,
specs/015-website-roadmap/contracts/cli.md)."""

from __future__ import annotations

import sys

import typer

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="The zoo roadmap: check the record, measure the pace of a quarter.",
)


def say(message: str) -> None:
    print(message, file=sys.stderr)


def _run(fn) -> None:
    from mobility_model_zoo.release.cli import _run as run

    run(fn)


@app.command("check")
def check_cmd() -> None:
    """Run the record checks RM1-RM8 without building the site."""

    def fn() -> None:
        from mobility_model_zoo.release.cli import _registry
        from mobility_model_zoo.site import roadmap

        record = roadmap.load_and_check(_registry())
        for warning in roadmap.warnings(record):
            say(warning)
        say(f"roadmap: ok ({len(roadmap.open_entries(_registry(), record))} open entries)")

    _run(fn)


@app.command("pace")
def pace_cmd(
    quarter: str = typer.Argument(..., help="A closed quarter, e.g. 2026-Q4."),
    write: bool = typer.Option(False, "--write", help="Write zoo/roadmap/reviews/QUARTER.md."),
    draft: bool = typer.Option(False, "--draft", help="Preview a quarter that has not ended yet."),
) -> None:
    """Plan against actual for one quarter: delivered early, on time or late, moved, dropped."""

    def fn() -> None:
        from mobility_model_zoo.release.cli import _registry
        from mobility_model_zoo.release.errors import UsageError
        from mobility_model_zoo.site import pace, roadmap

        try:
            roadmap.parse_quarter(quarter)
        except ValueError as e:
            raise UsageError(str(e)) from None
        reg = _registry()
        report = pace.report(reg, roadmap.load(reg), quarter, draft=draft)
        text = pace.render_markdown(report)
        if write:
            if report["draft"]:
                raise UsageError("a draft report is never written; wait until the quarter has ended")
            say(f"wrote {pace.write(reg, quarter, text).relative_to(reg.root)}")
        else:
            print(text, end="")

    _run(fn)
