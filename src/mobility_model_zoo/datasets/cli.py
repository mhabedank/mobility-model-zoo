"""`zoo data`: dataset declarations, licence check and download (specs/005-…/contracts/cli.md).

Data goes to $MMZ_DATA (default ~/.cache/mobility-model-zoo/datasets), never into the repository.
"""

from __future__ import annotations

import json
import sys

import typer

from mobility_model_zoo.release.errors import GateFailed, UsageError, ZooError

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Dataset declarations (topics/*/compliance/datasets.yaml): list, verify, download.",
)


def say(message: str) -> None:
    print(message, file=sys.stderr)


def _run(fn) -> None:
    from mobility_model_zoo.datasets.download import DataError

    try:
        fn()
    except GateFailed as e:
        for failure in e.failures:
            say(f"FAIL: {failure}")
        raise typer.Exit(e.exit_code) from None
    except ZooError as e:
        say(f"error: {e}")
        raise typer.Exit(e.exit_code) from None
    except DataError as e:
        say(f"error: {e}")
        raise typer.Exit(6) from None


def _source(ds_id: str):
    from mobility_model_zoo.datasets.registry import load

    sources = load()
    if ds_id not in sources:
        raise UsageError(f"unknown dataset {ds_id} (known: {', '.join(sorted(sources))})")
    return sources[ds_id]


@app.command("list")
def list_cmd(
    topic: str | None = typer.Option(None, help="only this topic"),
    status: str | None = typer.Option(None, help="active, broken_at_source or rejected"),
) -> None:
    """Table of the declarations with their local state."""

    def fn() -> None:
        from mobility_model_zoo.datasets import download as dl
        from mobility_model_zoo.datasets.registry import load

        print(f"data directory: {dl.data_root()}")
        for s in load().values():
            if (topic and s.topic != topic) or (status and s.status != status):
                continue
            local = "downloaded" if (dl.dataset_dir(s.id) / "SOURCE.json").exists() else "-"
            commercial = "commercial" if s.commercial_use else "non-commercial"
            print(
                f"{s.id:28s} {s.topic:20s} {s.license:18s} {s.permitted_use:16s} {commercial:14s} "
                f"~{s.approx_size_mb:>6.0f} MB  {s.status:16s} {local}"
            )

    _run(fn)


@app.command("info")
def info_cmd(ds_id: str) -> None:
    """The full declaration plus the local SOURCE.json, if downloaded."""

    def fn() -> None:
        from mobility_model_zoo.datasets import download as dl

        src = _source(ds_id)
        for k, v in src.__dict__.items():
            print(f"{k:16s} {v}")
        marker = dl.dataset_dir(ds_id) / "SOURCE.json"
        if marker.exists():
            print("SOURCE.json:")
            print(json.dumps(json.loads(marker.read_text()), indent=2))

    _run(fn)


@app.command("verify")
def verify_cmd(ids: list[str] = typer.Argument(None)) -> None:
    """Compare the licence the publisher declares today with the declaration (exit 1 on mismatch)."""

    def fn() -> None:
        from mobility_model_zoo.datasets import download as dl
        from mobility_model_zoo.datasets.registry import load

        sources = load()
        failures = []
        for ds in ids or [k for k, s in sources.items() if s.status != "rejected"]:
            src = _source(ds)
            if src.license_check == "manual":
                print(f"[manual] {ds}: {src.license}, checked by hand on {src.license_checked}")
                continue
            ok, declared = dl.verify(src)
            if declared is None:  # the API states no licence: never report this as ok
                print(
                    f"[unstated] {ds}: the {src.provider} API states no licence; declaration "
                    f"{src.license} last checked {src.license_checked}"
                )
                continue
            print(f"[{'ok' if ok else 'FAIL'}] {ds}: declared {src.license}, publisher {declared}")
            if not ok:
                failures.append(f"{ds}: publisher declares {declared}, declaration says {src.license}")
        if failures:
            raise GateFailed(failures)

    _run(fn)


@app.command("download")
def download_cmd(
    ds_id: str,
    force: bool = typer.Option(False, help="download again, also a dataset broken at source"),
) -> None:
    """Download into $MMZ_DATA/<id>/ after the licence check; writes SOURCE.json."""

    def fn() -> None:
        from mobility_model_zoo.datasets import download as dl

        _source(ds_id)
        print(dl.download(ds_id, force=force))

    _run(fn)


@app.command("path")
def path_cmd(ds_id: str) -> None:
    """Local directory of a dataset."""

    def fn() -> None:
        from mobility_model_zoo.datasets import download as dl

        _source(ds_id)
        print(dl.dataset_dir(ds_id))

    _run(fn)


@app.command("tree")
def tree_cmd(ds_id: str, max_entries: int = typer.Option(80, "--max")) -> None:
    """What a download unpacked (useful for new parsers)."""

    def fn() -> None:
        from mobility_model_zoo.datasets import download as dl

        _source(ds_id)
        print(dl.tree(ds_id, max_entries))

    _run(fn)


@app.command("validate")
def validate_cmd() -> None:
    """Validate every topic declaration file (schema rules, unique ids)."""

    def fn() -> None:
        from mobility_model_zoo.datasets.registry import validate

        problems = validate()
        if problems:
            raise GateFailed(problems)
        say("datasets: ok")

    _run(fn)
