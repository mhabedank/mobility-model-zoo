"""`zoo` command line: the release tool (specs/003-model-zoo-hf-release/contracts/cli.md).

Human-readable messages go to stderr. Tokens are read from the environment only and never printed.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import typer

from mobility_model_zoo.release import publish as ops
from mobility_model_zoo.release.errors import GateFailed, UsageError, ZooError
from mobility_model_zoo.release.registry import Registry, parse_version

OFFLINE_RULES = {1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 13, 14, 16}

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Release tool of the mobility model zoo: validate, stage, check, build, preview, publish.",
)


def say(message: str) -> None:
    print(message, file=sys.stderr)


def _run(fn: Callable[[], Any]) -> None:
    """Run a command and map release errors to the exit codes of contracts/cli.md."""
    try:
        fn()
    except GateFailed as e:
        for failure in e.failures:
            say(f"FAIL: {failure}")
        raise typer.Exit(e.exit_code) from None
    except ZooError as e:
        say(f"error: {e}")
        raise typer.Exit(e.exit_code) from None


def _registry() -> Registry:
    root = Path.cwd()
    if not (root / "zoo" / "topics.yaml").exists():
        raise UsageError("run zoo from the repository root (zoo/topics.yaml not found)")
    return Registry(root)


def _hub(token_env: str) -> Any:
    from mobility_model_zoo.release.hub import Hub, token_from_env

    return Hub(token_from_env(token_env))


def _runner() -> Any:
    import os

    from mobility_model_zoo.release.hub import RELEASE_TOKEN
    from mobility_model_zoo.release.usage import VenvRunner

    return VenvRunner(Path.cwd(), os.environ.get(RELEASE_TOKEN))


def topic_folder_failures(reg: Registry) -> list[str]:
    """Every public topic has topics/<id>/README.md and its dataset declarations (feature 005)."""
    failures = []
    for topic in reg.topics():
        if topic["id"] == "sandbox":
            continue
        base = reg.root / "topics" / topic["id"]
        for rel in ("README.md", "compliance/datasets.yaml"):
            if not (base / rel).is_file():
                failures.append(f"topic {topic['id']}: topics/{topic['id']}/{rel} is missing")
    return failures


def _mount_compliance() -> None:
    from mobility_model_zoo.compliance.cli import app as compliance_app

    app.add_typer(compliance_app, name="compliance")


def _mount_data() -> None:
    from mobility_model_zoo.datasets.cli import app as data_app

    app.add_typer(data_app, name="data")


_mount_compliance()
_mount_data()


@app.command("validate")
def validate_cmd(
    model: str | None = typer.Argument(None), all_models: bool = typer.Option(False, "--all")
) -> None:
    """Offline checks of the registry (no network) for every release record."""

    def fn() -> None:
        from mobility_model_zoo.release.gate import Gate

        reg = _registry()
        reg.topics()
        if not all_models and model is None:
            raise UsageError("name a model or pass --all")
        names = reg.model_names() if all_models else [model]
        failures: list[str] = []
        for name in names:
            versions = reg.versions(name)
            if not versions:
                reg.model(name)
                say(f"{name}: no release records")
            for version in versions:
                raw = reg.record_raw(name, version)
                if raw.get("published"):
                    say(f"{name} {version}: published, skipped")
                    continue
                if not (raw.get("staging") or {}).get("revision"):
                    say(f"{name} {version}: draft (not staged yet), skipped; use `zoo check --offline`")
                    continue
                say(f"{name} {version}:")
                try:
                    Gate(reg, name, version, only=OFFLINE_RULES).run(say)
                except GateFailed as e:
                    failures += [f"{name} {version}: {f}" for f in e.failures]
        if all_models:
            failures += topic_folder_failures(reg)
            from mobility_model_zoo.compliance.checks import Context, stage_meta
            from mobility_model_zoo.compliance.register import Register

            findings = stage_meta(Context(Register.load(reg.root)))
            failures += [f"compliance: {f.line()}" for f in findings]
            if not findings:
                say("compliance register: ok")
            from mobility_model_zoo.datasets.registry import validate as validate_datasets

            data_problems = validate_datasets(reg.root)
            failures += [f"datasets: {p}" for p in data_problems]
            if not data_problems:
                say("datasets: ok")
        if failures:
            raise GateFailed(failures)

    _run(fn)


@app.command("init-model")
def init_model_cmd(model: str) -> None:
    """Create the model's private staging repo (HF_RELEASE_TOKEN)."""
    _run(lambda: ops.init_model(_registry(), model, _hub("HF_RELEASE_TOKEN"), say))


@app.command("stage")
def stage_cmd(model: str, version: str, src: Path = typer.Option(..., "--from")) -> None:
    """Upload trained model files to the private staging repo (HF_STAGING_TOKEN)."""
    _run(lambda: ops.stage(_registry(), model, version, src, _hub("HF_STAGING_TOKEN"), say))


@app.command("check")
def check_cmd(model: str, version: str, offline: bool = typer.Option(False, "--offline")) -> None:
    """Run the release gate (all 14 rules; --offline skips the rules that need the Hub)."""

    def fn() -> None:
        parse_version(version)
        hub = None if offline else _hub("HF_RELEASE_TOKEN")
        runner = None if offline else _runner()
        ops.check(_registry(), model, version, hub, runner, say)

    _run(fn)


@app.command("build")
def build_cmd(model: str, version: str, out: Path = typer.Option(..., "--out")) -> None:
    """Gate, download the staged files and render the model card into --out."""
    _run(lambda: ops.build(_registry(), model, version, out, _hub("HF_RELEASE_TOKEN"), _runner(), say))


@app.command("preview")
def preview_cmd(model: str, version: str, build: Path = typer.Option(..., "--build")) -> None:
    """Upload the build to the staging branch rc-v<version> for review (the dry run)."""
    _run(lambda: ops.preview(_registry(), model, version, build, _hub("HF_RELEASE_TOKEN"), say))


@app.command("publish")
def publish_cmd(model: str, version: str, confirm: str = typer.Option(..., "--confirm")) -> None:
    """Publish the reviewed preview. Starting this is the owner's approval."""
    _run(lambda: ops.publish(_registry(), model, version, confirm, _hub("HF_RELEASE_TOKEN"), say))


@app.command("deprecate")
def deprecate_cmd(
    model: str,
    version: str,
    reason: str = typer.Option(..., "--reason"),
    successor: str | None = typer.Option(None, "--successor"),
) -> None:
    """Mark a published version as deprecated (card-only commit; files and tags unchanged)."""
    _run(
        lambda: ops.deprecate(
            _registry(), model, version, reason, successor, _hub("HF_RELEASE_TOKEN"), say
        )
    )


@app.command("index")
def index_cmd() -> None:
    """Regenerate zoo/MODELS.md."""
    from mobility_model_zoo.release import index

    _run(lambda: index.write(_registry()))


@app.command("audit")
def audit_cmd(model: str | None = typer.Argument(None)) -> None:
    """Compare published tags and cards with the release records; check repo visibility."""
    from mobility_model_zoo.release import audit

    _run(lambda: audit.run(_registry(), model, _hub("HF_RELEASE_TOKEN"), say))


@app.command("history-check")
def history_check_cmd() -> None:
    """Scan the whole git history for data files and secrets."""
    from mobility_model_zoo.release import history

    _run(lambda: history.run(Path.cwd(), say))
