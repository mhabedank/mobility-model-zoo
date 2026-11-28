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


# ---- data overview (feature 017, specs/017-mlflow-data-transparency/contracts/cli.md) ----------


@app.command("stats")
def stats_cmd(
    topic: list[str] = typer.Option(None, "--topic", help="only these topics"),
    kind: list[str] = typer.Option(
        None, "--kind", help="dataset, source-collection, training-set or benchmark"
    ),
    use: str | None = typer.Option(None, "--use", help="training_allowed or benchmark_only"),
    include_rejected: bool = typer.Option(False, "--include-rejected", help="list rejected datasets"),
    verify: bool = typer.Option(False, "--verify", help="also re-hash benchmark data where present"),
    as_json: bool = typer.Option(False, "--json", help="rows as JSON"),
    wide: bool = typer.Option(False, "--wide", help="licence, hash, lineage and users too"),
) -> None:
    """Every dataset, training set and benchmark version: size, counts, use, freeze date, changes.

    Exit 7 when a frozen benchmark changed (constitution IX)."""

    def fn() -> None:
        from mobility_model_zoo.datasets.inventory import IntegrityFailed, collect
        from mobility_model_zoo.datasets.inventory.render import stats_table

        inv = collect(
            kinds=kind or None,
            topics=topic or None,
            use=use,
            include_rejected=include_rejected,
            verify=verify,
        )
        if as_json:
            print(json.dumps([r.to_dict() for r in inv.rows], indent=2, ensure_ascii=False))
        else:
            print(stats_table(inv.rows, inv.hidden, inv.notes, wide=wide))
        if inv.failed:
            raise IntegrityFailed(
                "frozen benchmark changed: " + ", ".join(r.name for r in inv.failed)
            )

    _run(fn)


@app.command("history")
def history_cmd(
    ref: str = typer.Argument(..., help="dataset id, family (can-ids), or version (can-ids-v2)"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Registration, register changes, freezes and lineage of a dataset or benchmark family."""

    def fn() -> None:
        from mobility_model_zoo.datasets.inventory import collect, find, history
        from mobility_model_zoo.datasets.inventory.render import history_table
        from mobility_model_zoo.edge.paths import repo_root

        root = repo_root()
        inv = collect(include_rejected=True, integrity=False)
        rows = find(inv, ref)
        if not rows:
            raise UsageError(f"unknown dataset, training set or benchmark: {ref}")
        events = []
        for row in rows:
            subject = f"{row.kind}:{row.name}"
            if row.kind == "dataset" and history.in_git(root):
                events += history.register_events(root, row.source, "datasets", subject, row.id)
                if row.version != "register":
                    events.append(history.HistoryEvent(row.version, None, subject, "retrieved"))
            elif row.kind == "source-collection" and history.in_git(root):
                for sha, date in history.file_log(root, row.source):
                    events.append(history.HistoryEvent(date, sha, subject, "revised"))
            elif row.kind == "benchmark":
                events += history.manifest_events(root, row)
            elif row.kind == "training-set" and row.frozen_at:
                events.append(history.HistoryEvent(row.frozen_at, None, subject, "frozen"))
        events.sort(key=lambda e: (e.date or "", e.subject))
        lineage = [r.name for r in sorted(rows, key=lambda r: r.version)] if len(rows) > 1 else []
        if as_json:
            print(json.dumps([e.to_dict() for e in events], indent=2, ensure_ascii=False, default=str))
        else:
            incomplete = not history.in_git(root) or history.is_shallow(root)
            print(history_table(events, lineage, incomplete))

    _run(fn)


@app.command("diff")
def diff_cmd(
    a: str = typer.Argument(..., help="first version, e.g. can-ids-v2"),
    b: str = typer.Argument(..., help="second version, e.g. can-ids-v3"),
    members: bool = typer.Option(False, "--members", help="list added, removed and changed members"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """What changed between two versions of a training set or benchmark: counts, members, settings."""

    def fn() -> None:
        from mobility_model_zoo.datasets.inventory import collect, find
        from mobility_model_zoo.datasets.inventory.diff import diff
        from mobility_model_zoo.datasets.inventory.render import diff_table
        from mobility_model_zoo.edge.paths import repo_root

        inv = collect(include_rejected=True, integrity=False)
        pair = []
        for ref in (a, b):
            found = find(inv, ref)
            if len(found) != 1:
                raise UsageError(f"{ref}: name exactly one version ({len(found)} match)")
            pair.append(found[0])
        d = diff(repo_root(), pair[0], pair[1], members=members)
        print(json.dumps(d.to_dict(), indent=2, ensure_ascii=False) if as_json else diff_table(d))

    _run(fn)


@app.command("publish")
def publish_cmd(
    topic: list[str] = typer.Option(None, "--topic", help="only these topics"),
    kind: list[str] = typer.Option(None, "--kind", help="only these kinds"),
    dry_run: bool = typer.Option(False, "--dry-run", help="show create/update/supersede, write nothing"),
    profile: bool = typer.Option(False, "--profile", help="attach profile.json (aggregates only)"),
) -> None:
    """The overview as the `datasets` experiment of the tracking server (exit 8 without one)."""

    def fn() -> None:
        from mobility_model_zoo.datasets.inventory import collect
        from mobility_model_zoo.tracking.publish import publish

        inv = collect(kinds=kind or None, topics=topic or None)
        actions = publish(inv.rows, dry_run=dry_run, profile=profile)
        for a in actions:
            print(f"{a.action:9s} {a.row}" + (f"  ({a.note})" if a.note else ""))
        kinds = ("create", "update", "supersede", "skip")
        counts = {k: sum(1 for a in actions if a.action == k) for k in kinds}
        summary = ", ".join(f"{n} {k}" for k, n in counts.items() if n)
        say(("dry run: " if dry_run else "published: ") + summary)

    _run(fn)
