"""`zoo catalog`: the mobility resource index (specs/009-mobility-dataset-index/contracts/cli.md).

Entries live in the private repository mobility-model-zoo-catalog (--catalog, $MMZ_CATALOG or
../mobility-model-zoo-catalog). Commands write only inside that repository and never commit;
`withdraw` additionally adds suppression hashes to the zoo repository's compliance register.
"""

from __future__ import annotations

import datetime as dt
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import typer

from mobility_model_zoo.release.errors import GateFailed, UsageError

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Mobility resource index (metadata only): validate, check, query, report, fetch lists.",
)
report_app = typer.Typer(
    no_args_is_help=True, add_completion=False, help="Coverage and language reports."
)
pilot_app = typer.Typer(
    no_args_is_help=True, add_completion=False, help="The discovery pilot (riskiest assumption)."
)
app.add_typer(report_app, name="report")
app.add_typer(pilot_app, name="pilot")

_STATE: dict[str, Any] = {"catalog": None}


def say(message: str) -> None:
    print(message, file=sys.stderr)


def _run(fn) -> None:
    from mobility_model_zoo.release.cli import _run as run

    run(fn)


@app.callback()
def main(
    catalog: Path | None = typer.Option(
        None,
        "--catalog",
        help="Catalog repository (default $MMZ_CATALOG, then ../mobility-model-zoo-catalog).",
    ),
) -> None:
    _STATE["catalog"] = catalog


def _cat():
    from mobility_model_zoo.catalog.model import load

    return load(_STATE["catalog"])


def _today() -> str:
    return dt.date.today().isoformat()


def _zoo_root(zoo_root: Path | None) -> Path | None:
    if zoo_root is not None:
        return zoo_root
    return Path.cwd() if (Path.cwd() / "zoo" / "topics.yaml").is_file() else None


ZOO_ROOT = typer.Option(
    None, "--zoo-root", help="Checkout of mobility-model-zoo (default: current directory if it is one)."
)


def _entry(cat, entry_id: str) -> dict[str, Any]:
    if entry_id not in cat.entries:
        raise UsageError(f"unknown entry {entry_id}")
    return cat.entries[entry_id]


# ---- maintenance -------------------------------------------------------------------------------


@app.command("init")
def init_cmd(path: Path) -> None:
    """Create the catalog repository layout (never inside the zoo repository; never runs git)."""

    def fn() -> None:
        from mobility_model_zoo.catalog.model import PACKAGE, inside_zoo_repo
        from mobility_model_zoo.datasets import UsageRefused

        target = path.expanduser()
        if inside_zoo_repo(target.resolve()):
            raise UsageRefused(
                f"{target}: the catalog must not live inside the public zoo repository (R1)"
            )
        if target.exists() and any(p.name != ".git" for p in target.iterdir()):
            raise UsageRefused(f"{target}: directory is not empty")
        tpl = PACKAGE / "templates"
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy(tpl / "catalog.yaml", target / "catalog.yaml")
        shutil.copy(tpl / "README.md", target / "README.md")
        shutil.copy(tpl / "gitignore", target / ".gitignore")
        (target / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
        for wf in ("check.yml", "recheck.yml"):
            shutil.copy(tpl / "workflows" / wf, target / ".github" / "workflows" / wf)
        for folder in ("entries", "runs", "fetch-lists", "reports", "pilot"):
            (target / folder).mkdir(exist_ok=True)
            (target / folder / ".gitkeep").touch()
        say(f"created catalog layout in {target}")

    _run(fn)


@app.command("validate")
def validate_cmd(zoo_root: Path | None = ZOO_ROOT) -> None:
    """Offline checks K1, K2, K3, K8 and K9 of every entry. Exit 1 on any failure."""

    def fn() -> None:
        from mobility_model_zoo.catalog.model import licence_allowlist
        from mobility_model_zoo.catalog.validate import offline

        cat = _cat()
        findings = offline(cat, allowlist=licence_allowlist(_zoo_root(zoo_root)))
        for f in findings:
            print(f.line())
        failures = [f.line() for f in findings if f.severity == "fail"]
        if failures:
            raise GateFailed([f"{len(failures)} failing finding(s)"])
        v = cat.version()
        say(
            f"ok: {len(cat.entries)} entries, index {(v['catalog_commit'] or 'uncommitted')[:12]} "
            f"{v['catalog_sha256'][:12]}, vocab v{v['vocab_version']}"
        )

    _run(fn)


@app.command("new")
def new_cmd(from_file: Path = typer.Option(..., "--from", help="YAML file with one entry.")) -> None:
    """Add one entry by hand (provenance owner, status candidate)."""

    def fn() -> None:
        from mobility_model_zoo.catalog import ingest
        from mobility_model_zoo.catalog.model import read_yaml

        cat = _cat()
        entry = read_yaml(from_file)
        new_id, findings = ingest.add_one(cat, entry, added_by="owner", today=_today())
        for f in findings:
            print(f.line())
        if new_id is None:
            raise GateFailed(["entry not added"])
        say(f"added {new_id} as candidate")

    _run(fn)


@app.command("check")
def check_cmd(
    ids: list[str] = typer.Option(None, "--id", help="Only these entries."),
    status: list[str] = typer.Option(None, "--status", help="Only entries with these statuses."),
    stale: int = typer.Option(
        180, "--stale", help="Re-check cleared entries verified more than DAYS ago."
    ),
    offline_only: bool = typer.Option(False, "--offline", help="Only the offline checks; no network."),
    zoo_root: Path | None = ZOO_ROOT,
) -> None:
    """Run the checks K1-K9, apply the rules and the state machine, write the entries."""

    def fn() -> None:
        from mobility_model_zoo.catalog import checks

        cat = _cat()
        summary = checks.run(
            cat,
            ids=ids or None,
            statuses=status or None,
            stale_days=stale,
            network=not offline_only,
            zoo_root=_zoo_root(zoo_root),
            say=say,
        )
        say("; ".join(f"{k}: {v}" for k, v in summary.items()))

    _run(fn)


@app.command("flags")
def flags_cmd(flag: str | None = typer.Option(None, "--flag")) -> None:
    """Entries with flags: the owner's decision queue."""

    def fn() -> None:
        cat = _cat()
        for eid in sorted(cat.entries):
            e = cat.entries[eid]
            for f in (e.get("status") or {}).get("flags") or []:
                if flag and f != flag:
                    continue
                usage = e.get("usage") or {}
                why = usage.get("rationale") or e["status"].get("reason") or ""
                print(f"{eid}\t{f}\t{usage.get('rule', '-')}\t{why}")

    _run(fn)


@app.command("decide")
def decide_cmd(
    entry_id: str,
    use: str = typer.Option(..., "--use", help="training_allowed, benchmark_only or not_usable"),
    reason: str = typer.Option(..., "--reason"),
) -> None:
    """Record an owner decision for a flagged entry (rule U0)."""

    def fn() -> None:
        from mobility_model_zoo.catalog import rules, states

        if use not in ("training_allowed", "benchmark_only", "not_usable"):
            raise UsageError("--use must be training_allowed, benchmark_only or not_usable")
        cat = _cat()
        e = _entry(cat, entry_id)
        lic = e.get("licence") or {}
        e["usage"] = {
            "permitted_use": use,
            "redistribution": "unclear" if use == "training_allowed" else "not_allowed",
            "rule": "U0",
            "rules_version": int(rules.table()["version"]),
            "rationale": f"owner decision: {reason}",
            "evidence_url": lic.get("evidence_url"),
            "decided_at": _today(),
        }
        states.set_flag(e, "owner_decision_needed", False)
        cat.write_entry(e)
        say(f"{entry_id}: {use} (U0)")

    _run(fn)


def _end_state(entry_id: str, value: str, reason: str) -> None:
    from mobility_model_zoo.catalog import states

    cat = _cat()
    e = _entry(cat, entry_id)
    states.set_status(e, value, _today(), reason)
    cat.write_entry(e)
    say(f"{entry_id}: {value}")


@app.command("reject")
def reject_cmd(entry_id: str, reason: str = typer.Option(..., "--reason")) -> None:
    """Set an entry to rejected (kept, so discovery does not propose it again)."""
    _run(lambda: _end_state(entry_id, "rejected", reason))


@app.command("retire")
def retire_cmd(entry_id: str, reason: str = typer.Option(..., "--reason")) -> None:
    """Set an entry to retired (the resource is gone for good)."""
    _run(lambda: _end_state(entry_id, "retired", reason))


@app.command("withdraw")
def withdraw_cmd(
    entry_id: str,
    request: str = typer.Option(..., "--request", help="Request id in compliance/requests.yaml."),
    zoo_root: Path | None = ZOO_ROOT,
) -> None:
    """Withdraw an entry after an objection and add its addresses to the suppression list (FR-021)."""

    def fn() -> None:
        from mobility_model_zoo.catalog import withdraw

        root = _zoo_root(zoo_root)
        if root is None:
            raise UsageError("run in the zoo repository or pass --zoo-root")
        cat = _cat()
        added = withdraw.withdraw(cat, entry_id, request, root, _today())
        say(f"{entry_id}: withdrawn ({request}); {added} suppression hash(es) added")

    _run(fn)


@app.command("link")
def link_cmd(entry_id: str, target: str, zoo_root: Path | None = ZOO_ROOT) -> None:
    """Link a fetched entry to its source record: REGISTER:TOPIC:RECORD (FR-029)."""

    def fn() -> None:
        from mobility_model_zoo.catalog import fetchlist

        root = _zoo_root(zoo_root)
        if root is None:
            raise UsageError("run in the zoo repository or pass --zoo-root")
        cat = _cat()
        fetchlist.link(cat, entry_id, target, root, _today())
        say(f"{entry_id}: fetched -> {target}")

    _run(fn)


# ---- discovery ---------------------------------------------------------------------------------


@app.command("ingest")
def ingest_cmd(
    candidates: Path,
    run_file: Path = typer.Option(..., "--run", help="Run header (runs/<date>-<slug>.yaml)."),
) -> None:
    """Validate, deduplicate and add the candidates of a discovery run."""

    def fn() -> None:
        from mobility_model_zoo.catalog import ingest

        cat = _cat()
        outcome = ingest.ingest(cat, candidates, run_file, _today())
        say(
            f"proposed {outcome['proposed']}, accepted {outcome['accepted']}, "
            f"merged {outcome['merged']}, "
            f"rejected {outcome['rejected']}"
        )
        if outcome["proposed"] and outcome["rejected"] / outcome["proposed"] > ingest.MAX_REJECTED_SHARE:
            raise GateFailed(
                [
                    f"{outcome['rejected']} of {outcome['proposed']} lines failed (> 20%): "
                    "check the harvester or the agent"
                ]
            )

    _run(fn)


@app.command("harvest")
def harvest_cmd(
    name: str,
    lang: list[str] = typer.Option(None, "--lang"),
    area: list[str] = typer.Option(None, "--area"),
    subdomain: list[str] = typer.Option(None, "--subdomain"),
    limit: int = typer.Option(200, "--limit", help="At most N candidates."),
    run_id: str | None = typer.Option(None, "--run-id"),
) -> None:
    """Run a harvester (catalogue API), write its run files and ingest the candidates."""

    def fn() -> None:
        from mobility_model_zoo.catalog import ingest
        from mobility_model_zoo.catalog.harvest import run_harvester

        cat = _cat()
        jsonl, header = run_harvester(
            cat.root,
            name,
            languages=lang or [],
            areas=area or [],
            subdomains=subdomain or [],
            limit=limit,
            run_id=run_id,
            say=say,
        )
        outcome = ingest.ingest(cat, jsonl, header, _today())
        say(
            f"{name}: proposed {outcome['proposed']}, accepted {outcome['accepted']}, "
            f"merged {outcome['merged']}, rejected {outcome['rejected']}"
        )

    _run(fn)


# ---- use ---------------------------------------------------------------------------------------


def _select(cat, **filters):
    from mobility_model_zoo.catalog.query import select

    return select(cat.entries.values(), **filters)


QUERY_OPTS = dict(
    lang=typer.Option(None, "--lang"),
    area=typer.Option(None, "--area"),
    modality=typer.Option(None, "--modality"),
    genre=typer.Option(None, "--genre"),
    kind=typer.Option(None, "--kind"),
    topic=typer.Option(None, "--topic"),
    subdomain=typer.Option(None, "--subdomain"),
    status=typer.Option(None, "--status"),
    use=typer.Option(None, "--use"),
    transcripts=typer.Option(None, "--transcripts", help="yes, no or unknown"),
    origin=typer.Option(None, "--origin"),
    min_quality=typer.Option(None, "--min-quality"),
    include_transcripts=typer.Option(False, "--include-transcripts"),
)


def _filters(**kw) -> dict[str, Any]:
    return {k: (list(v) if isinstance(v, (list, tuple)) else v) for k, v in kw.items()}


@app.command("query")
def query_cmd(
    lang: list[str] = QUERY_OPTS["lang"],
    area: list[str] = QUERY_OPTS["area"],
    modality: list[str] = QUERY_OPTS["modality"],
    genre: list[str] = QUERY_OPTS["genre"],
    kind: list[str] = QUERY_OPTS["kind"],
    topic: list[str] = QUERY_OPTS["topic"],
    subdomain: list[str] = QUERY_OPTS["subdomain"],
    status: list[str] = QUERY_OPTS["status"],
    use: list[str] = QUERY_OPTS["use"],
    transcripts: str | None = QUERY_OPTS["transcripts"],
    origin: list[str] = QUERY_OPTS["origin"],
    min_quality: int | None = QUERY_OPTS["min_quality"],
    include_transcripts: bool = QUERY_OPTS["include_transcripts"],
    fmt: str = typer.Option("table", "--format", help="table, json or ids"),
) -> None:
    """Filter entries: AND across options, OR within one option (FR-025)."""

    def fn() -> None:
        from mobility_model_zoo.catalog.query import permitted_use

        cat = _cat()
        found = _select(
            cat,
            **_filters(
                lang=lang,
                area=area,
                modality=modality,
                genre=genre,
                kind=kind,
                topic=topic,
                subdomain=subdomain,
                status=status,
                use=use,
                transcripts=transcripts,
                origin=origin,
                min_quality=min_quality,
                include_transcripts=include_transcripts,
            ),
        )
        if fmt == "ids":
            for e in found:
                print(e["id"])
        elif fmt == "json":
            print(json.dumps(found, ensure_ascii=False, indent=2, default=str))
        elif fmt == "table":
            for e in found:
                rtype = e["resource_type"]
                print(
                    "\t".join(
                        [
                            e["id"],
                            ",".join(lang_["code"] for lang_ in e["languages"]),
                            str(e["origin_area"]),
                            f"{rtype['modality']}/{rtype['genre']}",
                            e["publisher"]["kind"],
                            e["licence"]["id"],
                            permitted_use(e),
                            e["status"]["value"],
                            str(e["quality"]["score"]),
                        ]
                    )
                )
            say(f"{len(found)} entries")
        else:
            raise UsageError("--format must be table, json or ids")

    _run(fn)


def _write_report(cat, out: Path | None, stem: str, data: dict[str, Any], markdown: str) -> Path:
    folder = out or (cat.root / "reports")
    folder.mkdir(parents=True, exist_ok=True)
    base = folder / f"{data['date']}-{stem}"
    base.with_suffix(".json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    base.with_suffix(".md").write_text(markdown, encoding="utf-8")
    return base


@report_app.command("coverage")
def coverage_cmd(out: Path | None = typer.Option(None, "--out")) -> None:
    """Counts and volume per language, area, modality, kind and permitted use, with gaps (FR-026)."""

    def fn() -> None:
        from mobility_model_zoo.catalog import reports

        cat = _cat()
        rep = reports.coverage(cat)
        base = _write_report(cat, out, "coverage", rep, reports.render_coverage(rep))
        say(f"wrote {base}.md and .json")
        print("gaps (languages): " + (", ".join(rep["gaps"]["languages"]) or "none"))
        print("gaps (modalities): " + (", ".join(rep["gaps"]["modalities"]) or "none"))

    _run(fn)


@report_app.command("languages")
def languages_cmd(
    out: Path | None = typer.Option(None, "--out"), zoo_root: Path | None = ZOO_ROOT
) -> None:
    """Per language: index volume, base-model coverage and training share of each zoo model (FR-027)."""

    def fn() -> None:
        from mobility_model_zoo.catalog import reports

        root = _zoo_root(zoo_root)
        if root is None:
            raise UsageError("run in the zoo repository or pass --zoo-root")
        cat = _cat()
        rep = reports.languages(cat, root)
        base = _write_report(cat, out, "languages", rep, reports.render_languages(rep))
        say(f"wrote {base}.md and .json")

    _run(fn)


@app.command("fetchlist")
def fetchlist_cmd(
    name: str,
    lang: list[str] = QUERY_OPTS["lang"],
    area: list[str] = QUERY_OPTS["area"],
    modality: list[str] = QUERY_OPTS["modality"],
    genre: list[str] = QUERY_OPTS["genre"],
    kind: list[str] = QUERY_OPTS["kind"],
    topic: list[str] = QUERY_OPTS["topic"],
    subdomain: list[str] = QUERY_OPTS["subdomain"],
    status: list[str] = QUERY_OPTS["status"],
    use: list[str] = QUERY_OPTS["use"],
    transcripts: str | None = QUERY_OPTS["transcripts"],
    origin: list[str] = QUERY_OPTS["origin"],
    min_quality: int | None = QUERY_OPTS["min_quality"],
    include_transcripts: bool = QUERY_OPTS["include_transcripts"],
) -> None:
    """Write fetch-lists/<date>-<name>.yaml: cleared entries with proposed register records (FR-028)."""

    def fn() -> None:
        from mobility_model_zoo.catalog import fetchlist

        cat = _cat()
        filters = _filters(
            lang=lang,
            area=area,
            modality=modality,
            genre=genre,
            kind=kind,
            topic=topic,
            subdomain=subdomain,
            status=status,
            use=use,
            transcripts=transcripts,
            origin=origin,
            min_quality=min_quality,
            include_transcripts=include_transcripts,
        )
        selection = " ".join(
            f"--{k.replace('_', '-')} {' '.join(map(str, v)) if isinstance(v, list) else v}"
            for k, v in filters.items()
            if v not in (None, [], False)
        )
        path, doc = fetchlist.write(cat, name, _select(cat, **filters), selection or "(all)")
        say(f"wrote {path}: {len(doc['items'])} item(s), {len(doc['refused'])} refused")

    _run(fn)


@app.command("audit")
def audit_cmd(
    sample: int = typer.Option(30, "--sample", help="Entries for the usage re-check (SC-005)."),
    dup_sample: int = typer.Option(50, "--dup-sample", help="Entries for the duplicate audit (SC-008)."),
    seed: int = typer.Option(9, "--seed"),
    model: str | None = typer.Option(
        None, "--model", help="Local model (not Claude) for the second reading."
    ),
    zoo_root: Path | None = ZOO_ROOT,
) -> None:
    """Independent re-check of the usage decision and duplicate audit (research R8)."""

    def fn() -> None:
        from mobility_model_zoo.catalog import audit

        cat = _cat()
        rep = audit.run(
            cat,
            sample=sample,
            dup_sample=dup_sample,
            seed=seed,
            model=model,
            zoo_root=_zoo_root(zoo_root),
        )
        base = _write_report(cat, None, "audit", rep, audit.render(rep))
        say(f"wrote {base}.md and .json")
        if not rep["passed"]:
            raise GateFailed(rep["failures"])

    _run(fn)


@pilot_app.command("evaluate")
def pilot_evaluate_cmd(pilot_file: Path) -> None:
    """Pilot criteria per language (spec: Riskiest Assumption and Pilot)."""

    def fn() -> None:
        from mobility_model_zoo.catalog import pilot

        cat = _cat()
        path = pilot_file if pilot_file.is_absolute() else cat.root / pilot_file
        result = pilot.evaluate(cat, path)
        for row in result["languages"]:
            print(
                f"{row['language']}: {'PASS' if row['passed'] else 'FAIL'}  accepted {row['accepted']}, "
                f"licence determined {row['determined_share']:.0%}, "
                f"training_allowed {row['training_allowed']}"
            )
        print(f"overall: {'PASS' if result['passed'] else 'FAIL'}")
        if not result["passed"]:
            raise GateFailed(["pilot criteria not met"])

    _run(fn)
