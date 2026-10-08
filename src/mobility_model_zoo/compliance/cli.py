"""`zoo compliance …`: the compliance harness commands (specs/006-compliance-harness/contracts/cli.md).

Failures print `stage / record / field / reason [check id]` and exit like a failed gate.
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from mobility_model_zoo.compliance import checks
from mobility_model_zoo.compliance.findings import run_stages
from mobility_model_zoo.compliance.register import Register
from mobility_model_zoo.release.errors import UsageError

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Compliance register, fail-closed checks and generated notices.",
)


def say(message: str) -> None:
    print(message, file=sys.stderr)


def _run(fn) -> None:
    from mobility_model_zoo.release.cli import _run as release_run

    release_run(fn)


def _root() -> Path:
    root = Path.cwd()
    if not (root / "zoo" / "topics.yaml").exists():
        raise UsageError("run zoo from the repository root (zoo/topics.yaml not found)")
    return root


def load_register() -> Register:
    return Register.load(_root())


@app.command("check")
def check_cmd(
    ci: bool = typer.Option(False, "--ci", help="Only stages that need no data outside git."),
    stage: list[str] = typer.Option([], "--stage", help="Run only these stages (repeatable)."),
    model: str | None = typer.Option(None, "--model"),
    version: str | None = typer.Option(None, "--version"),
) -> None:
    """Run the compliance stages in order; stop at the first failing stage."""

    def fn() -> None:
        if ci and stage:
            raise UsageError("--ci and --stage are exclusive")
        names = checks.CI_STAGES if ci else (stage or list(checks.STAGES))
        try:
            selected = checks.stages_named(names)
        except KeyError as e:
            raise UsageError(str(e)) from None
        ctx = checks.Context(load_register(), model=model, version=version)
        run_stages(selected, ctx, say)
        say("compliance: ok")

    _run(fn)


def _not_implemented(name: str):
    def cmd() -> None:
        say(f"zoo compliance {name}: not implemented yet")
        raise typer.Exit(1)

    cmd.__doc__ = f"{name} (not implemented yet)"
    return cmd


@app.command("recipients")
def recipients_cmd(
    runs: list[Path] = typer.Option(..., "--runs", help="Run folders (repeatable)."),
) -> None:
    """Aggregate labeling logs into compliance/recipients.yaml (no text, no chunk ids)."""

    def fn() -> None:
        from mobility_model_zoo.compliance import recipients

        reg = load_register()
        missing = [str(r) for r in runs if not r.is_dir()]
        if missing:
            raise UsageError(f"not a folder: {', '.join(missing)}")
        recs = recipients.collect(runs)
        recipients.assign_routes(recs, reg.records("providers"))
        recipients.write(reg.root / "compliance" / "recipients.yaml", recs, runs, reg.root)
        say(
            f"recipients: {len(recs)} routes from "
            f"{sum(r['calls_ok'] + r['calls_error'] for r in recs)} calls"
        )

    _run(fn)


@app.command("bootstrap-sources")
def bootstrap_sources_cmd(
    topic: str = typer.Option(..., "--topic"),
    model: str = typer.Option(..., "--model"),
    version: str = typer.Option(..., "--version"),
    benchmark_config: Path | None = typer.Option(None, "--benchmark-config"),
    benchmark: str | None = typer.Option(None, "--benchmark", help="Benchmark name for used_by tags."),
    also_versions: list[str] = typer.Option(
        [], "--also-version", help="More versions using the same sources."
    ),
    offline: bool = typer.Option(False, "--offline", help="Skip the retrospective signal check."),
) -> None:
    """Propose source records from local metadata (writes topics/<topic>/compliance/sources.yaml)."""

    def fn() -> None:
        import datetime as dt

        import httpx
        import yaml

        from mobility_model_zoo.compliance import bootstrap, signals

        reg = load_register()
        record_path = reg.root / "zoo" / "models" / model / "releases" / f"{version}.yaml"
        if not record_path.exists():
            raise UsageError(f"no release record {record_path}")
        record = yaml.safe_load(record_path.read_text(encoding="utf-8"))
        bench_ids = (
            bootstrap.benchmark_snapshot_ids(reg.root, benchmark_config) if benchmark_config else set()
        )
        if benchmark_config and not benchmark:
            raise UsageError("--benchmark-config needs --benchmark (the benchmark name)")
        lists = signals.Lists(
            ai_agents=(reg.lists("ai-user-agents") or {}).get("agents", []),
            denylist=(reg.lists("denylist") or {}).get("domains", []),
            piracy=(reg.lists("piracy-domains") or {}).get("domains", []),
        )
        client = httpx.Client(timeout=30)
        check = None if offline else (lambda url: signals.check_url(url, lists, client)[0])
        records, items = bootstrap.build(
            reg.root,
            model=model,
            version=version,
            release_record=record,
            benchmark=benchmark,
            benchmark_ids=bench_ids,
            meta=bootstrap.Metadata(),
            check=check,
            today=dt.date.today(),
            used_by_versions=[version, *also_versions],
        )
        out = reg.root / "topics" / topic / "compliance" / "sources.yaml"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            "# Proposed by `zoo compliance bootstrap-sources`; reviewed and maintained by hand.\n"
            + yaml.safe_dump({"sources": records}, sort_keys=False, allow_unicode=True, width=110),
            encoding="utf-8",
        )
        say(f"sources: {len(records)} records written to {out.relative_to(reg.root)}")
        for item in items:
            say(f"owner decision item: {item}")

    _run(fn)


@app.command("render")
def render_cmd(
    check: bool = typer.Option(False, "--check", help="Compare only; write nothing."),
) -> None:
    """Render the public compliance documents from the register."""

    def fn() -> None:
        from mobility_model_zoo.compliance import render
        from mobility_model_zoo.compliance.findings import StageFailed

        reg = load_register()
        rendered = render.render_all(reg)
        if check:
            findings = render.drift(reg, rendered)
            if findings:
                raise StageFailed(findings)
            say(f"render: {len(rendered)} documents up to date")
            return
        for rel in render.write_all(reg, rendered):
            say(f"wrote {rel}")

    _run(fn)


def _corpus_texts(reg, sources) -> tuple[list[str], list[str]]:
    """(all texts, texts of sources whose record does not allow quotes) from local snapshots."""
    import yaml

    by_origin: dict[str, list] = {}
    for meta_path in sorted((reg.root / "data" / "snapshots").glob("*/source.yaml")):
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
        text_path = meta_path.parent / "text.txt"
        if text_path.exists():
            by_origin.setdefault(meta["origin_url"], []).append(text_path)
    full, restricted = [], []
    missing = []
    for s in sources:
        paths = by_origin.get(s["origin_url"], [])
        if not paths and not s.get("deleted_at"):
            missing.append(s["id"])
        for path in paths:
            text = path.read_text(encoding="utf-8")
            full.append(text)
            if not s.get("quote_allowed"):
                restricted.append(text)
    if missing:
        raise UsageError(
            f"no local text for {len(missing)} source(s), e.g. {missing[0]}; "
            "the scan needs the snapshots under data/snapshots"
        )
    return full, restricted


@app.command("scan-publish")
def scan_publish_cmd(
    model: str = typer.Option(..., "--model"), version: str = typer.Option(..., "--version")
) -> None:
    """Scan every file published with a release for corpus overlap and personal data."""

    def fn() -> None:
        import json

        from mobility_model_zoo.compliance import checks, release_checks
        from mobility_model_zoo.compliance.scan import CorpusIndex
        from mobility_model_zoo.release import card as cards
        from mobility_model_zoo.release.registry import Registry

        reg = load_register()
        zreg = Registry(reg.root)
        sources = [
            s
            for s in reg.records("sources") + reg.records("datasets")
            if f"{model}@{version}" in s.get("used_by", [])
            or any(u.startswith("benchmark:") for u in s.get("used_by", []))
        ]
        full_texts, restricted_texts = _corpus_texts(reg, sources)
        full, restricted = CorpusIndex.build(full_texts), CorpusIndex.build(restricted_texts)
        full.save(reg.root / "data" / "compliance" / "corpus-index")
        card = cards.render(
            cards.CardInput(zreg, model, version, record=zreg.record_raw(model, version))
        )
        ctx = checks.Context(reg, model=model, version=version, extra={"card": card})
        report = release_checks.scan_publication(ctx, full, restricted)
        path = release_checks.report_path(reg.root, model, version)
        path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        worst = max((f["overlap_max_words"] for f in report["files"]), default=0)
        pii_hits = sum(f["pii_hits"] for f in report["files"])
        say(
            f"scan: {len(report['files'])} files, {len(sources)} sources; longest restricted overlap "
            f"{worst} words, PII hits {pii_hits}; report {path.relative_to(reg.root)}"
        )

    _run(fn)


@app.command("signoff")
def signoff_cmd(
    model: str = typer.Option(..., "--model"), version: str = typer.Option(..., "--version")
) -> None:
    """Record the owner's sign-off in the release compliance record (all other stages must pass)."""

    def fn() -> None:
        import datetime as dt
        import subprocess

        import yaml

        from mobility_model_zoo.compliance import checks
        from mobility_model_zoo.release import card as cards
        from mobility_model_zoo.release.registry import Registry

        reg = load_register()
        zreg = Registry(reg.root)
        path = reg.root / "zoo" / "models" / model / "releases" / f"{version}.compliance.yaml"
        if not path.exists():
            raise UsageError(f"no compliance record {path.relative_to(reg.root)}")
        card = cards.render(
            cards.CardInput(zreg, model, version, record=zreg.record_raw(model, version))
        )
        stages = [n for n in checks.RELEASE_STAGES if n != "signoff"]
        ctx = checks.Context(
            reg,
            model=model,
            version=version,
            extra={
                "card": card,
                "topic": zreg.model_raw(model)["topic"],
                "model_yaml": zreg.model_raw(model),
            },
        )
        run_stages(checks.stages_named(stages), ctx, say)
        name = subprocess.run(
            ["git", "config", "user.name"], capture_output=True, text=True
        ).stdout.strip()
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data.update(
            state="signed_off", signed_off_by=name or "owner", signed_off_at=dt.date.today().isoformat()
        )
        path.write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100), encoding="utf-8"
        )
        say(f"signed off {model} {version} as {data['signed_off_by']}")

    _run(fn)


for _name in (
    "retention",
    "delete",
    "art9-scan",
    "redaction-recall",
    "request",
    "watch",
):
    app.command(_name)(_not_implemented(_name))
