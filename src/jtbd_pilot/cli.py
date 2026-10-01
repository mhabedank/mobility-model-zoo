"""`pilot` command line (contracts/cli.md).

Human-readable messages go to stderr, a JSON summary to stdout. Errors map to the exit codes in
jtbd_pilot.errors.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import typer

from jtbd_pilot.config import Settings, load_settings
from jtbd_pilot.errors import PilotError

app = typer.Typer(no_args_is_help=True, add_completion=False, help="JTBD extraction pilot")
spike_app = typer.Typer(no_args_is_help=True, help="Technical spike helpers (spec 002)")
source_app = typer.Typer(no_args_is_help=True, help="Fetch and register sources (crawl once)")
corpus_app = typer.Typer(no_args_is_help=True, help="Build, redact, split and validate chunks")
app.add_typer(source_app, name="source")
app.add_typer(corpus_app, name="corpus")
app.add_typer(spike_app, name="spike")


def _log(message: str) -> None:
    print(message, file=sys.stderr)


def _run(ctx: typer.Context, fn: Callable[[Settings], Any]) -> None:
    try:
        settings = load_settings(ctx.obj["config"])
        settings.pilot["dry_run"] = ctx.obj["dry_run"]
        result = fn(settings)
    except PilotError as exc:
        _log(f"error: {exc}")
        raise typer.Exit(exc.exit_code) from exc
    if result is not None:
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


@app.callback()
def main(
    ctx: typer.Context,
    config: Path = typer.Option(
        None, "--config", help="Pilot config (default configs/pilot-v1.yaml)"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Estimate and validate only"),
) -> None:
    ctx.obj = {"config": config, "dry_run": dry_run}


# ---- sources ----------------------------------------------------------------------
def _meta(**kwargs: Any) -> dict[str, Any]:
    return {k: v for k, v in kwargs.items() if v is not None}


@source_app.command("fetch")
def source_fetch(
    ctx: typer.Context,
    url: str,
    source_type: str = typer.Option(..., "--type"),
    license: str = typer.Option(..., "--license"),
    legal_basis: str = typer.Option(..., "--legal-basis"),
    permitted_uses: str = typer.Option(..., "--permitted-uses"),
    retention_until: str = typer.Option(..., "--retention-until"),
    access_terms: str = typer.Option(..., "--access-terms", help="ToS/robots.txt note with date"),
    update: bool = typer.Option(False, "--update"),
    reason: str = typer.Option(None, "--reason"),
) -> None:
    from jtbd_pilot.sources.snapshot import fetch_url

    meta = _meta(source_type=source_type, license=license, legal_basis=legal_basis,
                 permitted_uses=permitted_uses, retention_until=retention_until,
                 access_terms_checked=access_terms)
    _run(ctx, lambda s: fetch_url(s, url, meta, update=update, reason=reason))


@source_app.command("reddit")
def source_reddit(
    ctx: typer.Context,
    thread_id: str,
    retention_until: str = typer.Option(..., "--retention-until"),
    update: bool = typer.Option(False, "--update"),
    reason: str = typer.Option(None, "--reason"),
) -> None:
    from jtbd_pilot.sources.reddit import fetch_thread

    _run(ctx, lambda s: fetch_thread(s, thread_id, retention_until, update=update, reason=reason))


@source_app.command("register")
def source_register(
    ctx: typer.Context,
    path: Path,
    url: str = typer.Option(..., "--url", help="Origin URL of the manually obtained file"),
    source_type: str = typer.Option(..., "--type"),
    license: str = typer.Option(..., "--license"),
    legal_basis: str = typer.Option(..., "--legal-basis"),
    permitted_uses: str = typer.Option(..., "--permitted-uses"),
    retention_until: str = typer.Option(..., "--retention-until"),
    access_terms: str = typer.Option(..., "--access-terms"),
    update: bool = typer.Option(False, "--update"),
    reason: str = typer.Option(None, "--reason"),
) -> None:
    from jtbd_pilot.sources.snapshot import register_file

    meta = _meta(source_type=source_type, license=license, legal_basis=legal_basis,
                 permitted_uses=permitted_uses, retention_until=retention_until,
                 access_terms_checked=access_terms)
    _run(ctx, lambda s: register_file(s, path, url, meta, update=update, reason=reason))


@source_app.command("list")
def source_list(
    ctx: typer.Context,
    permitted_uses: str = typer.Option(None, "--permitted-uses"),
) -> None:
    from jtbd_pilot.sources.snapshot import list_snapshots

    _run(ctx, lambda s: list_snapshots(s, permitted_uses))


# ---- corpus ----------------------------------------------------------------------
@corpus_app.command("build")
def corpus_build(ctx: typer.Context, selection: Path = typer.Option(..., "--from")) -> None:
    from jtbd_pilot.corpus.build import build_from_selection

    _run(ctx, lambda s: build_from_selection(s, selection))


@corpus_app.command("autochunk")
def corpus_autochunk(
    ctx: typer.Context,
    snapshot_map: Path = typer.Option(..., "--map"),
    train: int = typer.Option(..., "--train"),
    evaluation: int = typer.Option(..., "--eval"),
    seed: int = typer.Option(..., "--seed"),
) -> None:
    from jtbd_pilot.corpus.autochunk import autochunk

    _run(ctx, lambda s: autochunk(s, snapshot_map, train, evaluation, seed))


@corpus_app.command("redact")
def corpus_redact(ctx: typer.Context) -> None:
    from jtbd_pilot.corpus.redact import redact_all

    _run(ctx, redact_all)


@corpus_app.command("mark-reviewed")
def corpus_mark_reviewed(
    ctx: typer.Context,
    chunk_ids: list[str] = typer.Argument(None),
    all_chunks: bool = typer.Option(False, "--all"),
) -> None:
    from jtbd_pilot.corpus.redact import mark_reviewed

    _run(ctx, lambda s: mark_reviewed(s, chunk_ids or [], all_chunks))


@corpus_app.command("redact-check")
def corpus_redact_check(ctx: typer.Context) -> None:
    from jtbd_pilot.corpus.redact import redact_check

    _run(ctx, redact_check)


@corpus_app.command("split")
def corpus_split(
    ctx: typer.Context,
    holdout: int = typer.Option(30, "--holdout"),
    seed: int = typer.Option(..., "--seed"),
) -> None:
    from jtbd_pilot.corpus.split import split_corpus

    _run(ctx, lambda s: split_corpus(s, holdout, seed))


@corpus_app.command("validate")
def corpus_validate(ctx: typer.Context, split: str = typer.Option("main", "--split")) -> None:
    from jtbd_pilot.corpus.validate import validate_split

    _run(ctx, lambda s: validate_split(s, split))


# ---- freezing ----------------------------------------------------------------------
@app.command("freeze")
def freeze_cmd(
    ctx: typer.Context,
    benchmark: bool = typer.Option(False, "--benchmark", help="Freeze consensus and contested set"),
    new_version: str = typer.Option(None, "--new-version"),
    rationale: str = typer.Option(None, "--rationale"),
) -> None:
    from jtbd_pilot.consensus import freeze_benchmark_from_analysis
    from jtbd_pilot.freeze import freeze_criteria

    if benchmark:
        _run(ctx, freeze_benchmark_from_analysis)
    else:
        _run(ctx, lambda s: freeze_criteria(s, new_version, rationale))


# ---- labeling ----------------------------------------------------------------------
@app.command("label")
def label_cmd(
    ctx: typer.Context,
    role: str = typer.Option(..., "--role"),
    backend: str = typer.Option(..., "--backend"),
    model: str = typer.Option(..., "--model", help="model_id from configs/models.yaml"),
    host: str = typer.Option(None, "--host", help="Override host (e.g. spark, vm)"),
    split: str = typer.Option("main", "--split"),
    limit: int = typer.Option(None, "--limit"),
    retry_failed: bool = typer.Option(
        False, "--retry-failed", help="Retry chunks excluded after backend failures"),
    workers: int = typer.Option(1, "--workers", help="Parallel model calls (chunks at a time)"),
) -> None:
    from jtbd_pilot.labeling.runner import label

    _run(ctx, lambda s: label(s, role=role, backend=backend, model_id=model, host=host,
                              split=split, limit=limit, retry_failed=retry_failed,
                              workers=workers))


@app.command("ensemble")
def ensemble_cmd(ctx: typer.Context, split: str = typer.Option("main", "--split")) -> None:
    """Build the offline teacher ensemble from its frozen member runs (FR-019b)."""
    from jtbd_pilot.ensemble import build_ensemble

    _run(ctx, lambda s: build_ensemble(s, split))


@app.command("budget")
def budget_cmd(
    ctx: typer.Context,
    estimate: bool = typer.Option(False, "--estimate"),
    model: str = typer.Option(None, "--model"),
    chunks: int = typer.Option(None, "--chunks"),
    add: str = typer.Option(None, "--add", help="Record a manual charge, e.g. vm"),
    eur: float = typer.Option(None, "--eur"),
) -> None:
    from jtbd_pilot import budget
    from jtbd_pilot.labeling.runner import estimate_for

    def action(s: Settings) -> Any:
        if add:
            if eur is None:
                from jtbd_pilot.errors import UsageError

                raise UsageError("--add requires --eur")
            return budget.record(s, add, "manual", eur, eur)
        if estimate:
            from jtbd_pilot.errors import UsageError

            if not model:
                raise UsageError("--estimate requires --model")
            entry = s.model(model)
            est = estimate_for(s, entry, chunks)
            budget.guard(s, est, entry.backend)
            return {"model": model, "estimated_eur": est, **budget.summary(s)}
        return budget.summary(s)

    _run(ctx, action)


# ---- evaluation ----------------------------------------------------------------------
@app.command("check")
def check_cmd(ctx: typer.Context, run: str = typer.Option(..., "--run")) -> None:
    from jtbd_pilot.checks import check_run

    _run(ctx, lambda s: check_run(s, run))


@app.command("match")
def match_cmd(ctx: typer.Context, runs: tuple[str, str] = typer.Option(..., "--runs")) -> None:
    from jtbd_pilot.matching import match_runs

    _run(ctx, lambda s: match_runs(s, runs[0], runs[1]))


@app.command("consensus")
def consensus_cmd(
    ctx: typer.Context,
    reference: tuple[str, str] = typer.Option((None, None), "--reference"),
    single: str = typer.Option(None, "--single", help="Spike configs only: one reference run"),
) -> None:
    from jtbd_pilot.consensus import build_consensus, build_single_reference
    from jtbd_pilot.errors import UsageError

    def action(s: Settings) -> Any:
        if single:
            return build_single_reference(s, single)
        if not all(reference):
            raise UsageError("give --reference <run_a> <run_b> (or --single <run> in a spike)")
        return build_consensus(s, reference[0], reference[1])

    _run(ctx, action)


@app.command("categorize")
def categorize_cmd(
    ctx: typer.Context,
    export: bool = typer.Option(False, "--export", help="Write contested-review.csv"),
    import_path: Path = typer.Option(None, "--import", help="Read a filled-in review CSV"),
    check: bool = typer.Option(
        False, "--check", help="Fail if any contested entry is uncategorized"
    ),
    freetext: bool = typer.Option(False, "--freetext", help="Write the free-text sample (FR-025)"),
) -> None:
    from jtbd_pilot import categorize

    def action(s: Settings) -> Any:
        if export:
            return categorize.export_review(s)
        if import_path:
            return categorize.import_review(s, import_path)
        if freetext:
            return categorize.export_freetext_sample(s)
        if check:
            return categorize.check_categories(s)
        return categorize.summarize(s)

    _run(ctx, action)


@app.command("agreement")
def agreement_cmd(ctx: typer.Context, split: str = typer.Option("main", "--split")) -> None:
    from jtbd_pilot.metrics import compute_agreement

    _run(ctx, lambda s: compute_agreement(s, split))


@app.command("score")
def score_cmd(ctx: typer.Context, run: str = typer.Option(..., "--run")) -> None:
    from jtbd_pilot.scoring import score_run

    _run(ctx, lambda s: score_run(s, run))


@app.command("perf")
def perf_cmd(
    ctx: typer.Context,
    model: str = typer.Option(None, "--model"),
    host: str = typer.Option("vm", "--host"),
    warmup: int = typer.Option(3, "--warmup"),
    quality_run: str = typer.Option(None, "--quality-run", help="Run whose digest must match"),
    hardware: str = typer.Option(None, "--hardware", help="VM type label, e.g. hetzner-cx32"),
    frontier: bool = typer.Option(False, "--frontier"),
    run: str = typer.Option(None, "--run"),
    sample: int = typer.Option(20, "--sample"),
) -> None:
    from jtbd_pilot import perf
    from jtbd_pilot.errors import UsageError

    def action(s: Settings) -> Any:
        if frontier:
            if not run:
                raise UsageError("--frontier requires --run <gpt-run>")
            return perf.perf_frontier(s, run, sample)
        if not model:
            raise UsageError("--model is required")
        return perf.perf_local(s, model, host, warmup, quality_run, hardware)

    _run(ctx, action)


# ---- decision and report ----------------------------------------------------------------------
@app.command("decide")
def decide_cmd(ctx: typer.Context) -> None:
    from jtbd_pilot.decision import decide

    _run(ctx, decide)


@app.command("report")
def report_cmd(ctx: typer.Context) -> None:
    from jtbd_pilot.report.render import render_report

    _run(ctx, render_report)


@spike_app.command("export-sft")
def spike_export(ctx: typer.Context, run: str = typer.Option(..., "--run"),
                 out: Path = typer.Option(..., "--out"),
                 repair_quotes: bool = typer.Option(
                     True, "--repair/--no-repair",
                     help="Replace near-miss teacher quotes with the verbatim source passage")
                 ) -> None:
    from jtbd_pilot.spike import export_sft

    _run(ctx, lambda s: export_sft(s, run, out, repair_quotes))


@spike_app.command("report")
def spike_report_cmd(ctx: typer.Context,
                     sft_stats: Path = typer.Option(None, "--sft-stats")) -> None:
    from jtbd_pilot.spike import spike_report

    _run(ctx, lambda s: spike_report(s, sft_stats))


@app.command("doctor")
def doctor_cmd(ctx: typer.Context) -> None:
    from jtbd_pilot.doctor import doctor

    _run(ctx, doctor)


if __name__ == "__main__":
    app()
