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


@app.command("art9-scan")
def art9_scan_cmd(
    config: list[Path] = typer.Option(..., "--config", help="jtbd config(s) whose chunks to scan."),
    out: Path | None = typer.Option(None, "--out", help="Write counts as JSON (no text, no chunk ids)."),
) -> None:
    """Count special-category flags (Art. 9 GDPR) per source class and split; counts only."""

    def fn() -> None:
        import json

        import yaml

        from mobility_model_zoo.compliance.scan import art9_flags
        from mobility_model_zoo.productdev.jtbd.config import load_settings

        reg = load_register()
        lexicon = (reg.lists("special-categories") or {}).get("categories", {})
        origin_class = {s["origin_url"]: s["class"] for s in reg.records("sources")}
        snap_origin = {}
        for meta_path in (reg.root / "data" / "snapshots").glob("*/source.yaml"):
            meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
            snap_origin[meta["snapshot_id"]] = meta["origin_url"]
        counts: dict = {}
        for cfg in config:
            settings = load_settings(cfg)
            for path in sorted(settings.chunks_dir.glob("*.json")):
                chunk = json.loads(path.read_text(encoding="utf-8"))
                cls = origin_class.get(snap_origin.get(chunk.get("snapshot_id"), ""), "unregistered")
                key = f"{chunk.get('split', '?')}/{cls}"
                bucket = counts.setdefault(key, {"chunks": 0, "flagged_chunks": 0, "categories": {}})
                bucket["chunks"] += 1
                flags = art9_flags(chunk.get("text", ""), lexicon)
                if flags:
                    bucket["flagged_chunks"] += 1
                    for cat in flags:
                        bucket["categories"][cat] = bucket["categories"].get(cat, 0) + 1
        result = {k: counts[k] for k in sorted(counts)}
        if out:
            out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        for key, b in result.items():
            say(f"{key}: {b['flagged_chunks']}/{b['chunks']} chunks flagged {b['categories']}")

    _run(fn)


@app.command("redaction-recall")
def redaction_recall_cmd(
    items: Path | None = typer.Option(None, "--items", help="JSONL test set (default: synthetic set)."),
    minimum: float = typer.Option(0.95, "--min", help="Required combined recall (decision D9)."),
) -> None:
    """Measure redaction and scan recall on the synthetic test set (D9)."""

    def fn() -> None:
        import json

        from mobility_model_zoo.compliance import recall
        from mobility_model_zoo.compliance.findings import Finding, StageFailed

        result = recall.measure(recall.load(items) if items else recall.load())
        say(json.dumps(result, indent=2))
        if (result["recall"]["combined"] or 0) < minimum:
            raise StageFailed(
                [
                    Finding(
                        "C-T5",
                        "train",
                        "redaction-set",
                        "combined",
                        f"recall {result['recall']['combined']} below {minimum} (D9)",
                    )
                ]
            )

    _run(fn)


@app.command("retention")
def retention_cmd(
    fail: bool = typer.Option(False, "--fail", help="Exit with an error on findings."),
) -> None:
    """List snapshots past their retention date or without one (C-R1)."""

    def fn() -> None:
        from mobility_model_zoo.compliance.findings import StageFailed
        from mobility_model_zoo.compliance.train import retention_findings

        findings = retention_findings(load_register().root)
        for f in findings:
            say(f.line())
        say(f"retention: {len(findings)} finding(s)")
        if findings and fail:
            raise StageFailed(findings)

    _run(fn)


@app.command("delete")
def delete_cmd(
    snapshot: str = typer.Option(..., "--snapshot"), reason: str = typer.Option(..., "--reason")
) -> None:
    """Delete a snapshot's raw and text files, log hashes and URL, mark the source record."""

    def fn() -> None:
        import datetime as dt

        import yaml

        from mobility_model_zoo.compliance.train import delete_snapshot

        reg = load_register()
        entry = delete_snapshot(reg.root, snapshot, reason)
        for rel, data in reg.files.items():
            if reg.stems[rel] not in ("sources", "datasets"):
                continue
            key = "sources" if reg.stems[rel] == "sources" else "datasets"
            changed = False
            for rec in data.get(key, []):
                if rec.get("origin_url") == entry["origin_url"]:
                    rec["deleted_at"] = dt.date.today().isoformat()
                    changed = True
            if changed:
                path = reg.root / rel
                head = path.read_text(encoding="utf-8").split("\n", 1)[0]
                body = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=110)
                path.write_text((head + "\n" if head.startswith("#") else "") + body, encoding="utf-8")
        say(
            f"deleted {len(entry['files'])} file(s) of {snapshot}; "
            "logged in data/compliance/deletions.jsonl"
        )

    _run(fn)


request_app = typer.Typer(no_args_is_help=True, help="Rights and takedown requests (FR-026).")
watch_app = typer.Typer(no_args_is_help=True, help="Legal watch list (FR-028).")
app.add_typer(request_app, name="request")
app.add_typer(watch_app, name="watch")
DEADLINE_DAYS = {"objection": 30, "erasure": 30, "access": 30, "takedown": 14, "opt_out": 14}


def _write_records(path: Path, key: str, records: list, header: str) -> None:
    import yaml

    path.write_text(
        header + yaml.safe_dump({key: records}, sort_keys=False, allow_unicode=True, width=110),
        encoding="utf-8",
    )


@request_app.command("add")
def request_add_cmd(
    kind: str = typer.Option(..., "--type", help="objection|erasure|access|takedown|opt_out"),
    identifier: str = typer.Option(
        ..., "--identifier", help="URL, name or handle; only its keyed hash is stored"
    ),
    received: str = typer.Option(..., "--received", help="YYYY-MM-DD"),
    suppress: str = typer.Option("url", "--suppress", help="url|identifier|none"),
) -> None:
    """Log a request with its deadline; add a suppression entry (keyed hash, no personal data)."""

    def fn() -> None:
        import datetime as dt

        from mobility_model_zoo.compliance.hashing import keyed_hash

        if kind not in DEADLINE_DAYS:
            raise UsageError(f"--type must be one of {', '.join(DEADLINE_DAYS)}")
        from mobility_model_zoo.compliance.signals import canonical

        try:
            # URLs are hashed in the canonical form the fetch stage uses (C-F5).
            digest = keyed_hash(canonical(identifier) if suppress == "url" else identifier)
        except RuntimeError as e:
            raise UsageError(str(e)) from None
        reg = load_register()
        day = dt.date.fromisoformat(received)
        requests = reg.records("requests")
        rid = f"r-{day.isoformat()}-{len(requests) + 1:03d}"
        requests.append(
            {
                "id": rid,
                "type": kind,
                "received_at": day.isoformat(),
                "deadline": (day + dt.timedelta(days=DEADLINE_DAYS[kind])).isoformat(),
                "identifier_hash": digest,
                "stores_searched": [],
                "action": "",
                "suppression_added": suppress != "none",
                "answered_at": None,
            }
        )
        _write_records(
            reg.root / "compliance" / "requests.yaml",
            "requests",
            requests,
            "# Rights and takedown requests; identifiers are keyed hashes (MMZ_SUPPRESSION_KEY).\n",
        )
        if suppress != "none":
            entries = reg.records("suppression")
            entries.append(
                {"hash": digest, "kind": suppress, "request_id": rid, "added_at": day.isoformat()}
            )
            _write_records(
                reg.root / "compliance" / "suppression.yaml",
                "entries",
                entries,
                "# Suppressed URLs and identifiers (keyed hashes); fetch and train skip them.\n",
            )
        say(f"logged {rid}, deadline {requests[-1]['deadline']}")

    _run(fn)


@request_app.command("close")
def request_close_cmd(
    request_id: str,
    action: str = typer.Option(..., "--action", help="What was done (no personal data)."),
    stores: list[str] = typer.Option(..., "--searched", help="Stores searched (repeatable)."),
    answered: str = typer.Option(..., "--answered", help="YYYY-MM-DD"),
) -> None:
    """Record the answer to a request."""

    def fn() -> None:
        reg = load_register()
        requests = reg.records("requests")
        match = next((r for r in requests if r["id"] == request_id), None)
        if match is None:
            raise UsageError(f"unknown request {request_id}")
        match.update(action=action, stores_searched=list(stores), answered_at=answered)
        _write_records(
            reg.root / "compliance" / "requests.yaml",
            "requests",
            requests,
            "# Rights and takedown requests; identifiers are keyed hashes (MMZ_SUPPRESSION_KEY).\n",
        )
        say(f"closed {request_id}")

    _run(fn)


@watch_app.command("review")
def watch_review_cmd(
    item_id: str,
    outcome: str = typer.Option(..., "--outcome"),
    next_review: str = typer.Option(None, "--next-review", help="Keep watching until this date."),
) -> None:
    """Record the review of a legal watch item (clears C-M2)."""

    def fn() -> None:
        import datetime as dt

        reg = load_register()
        items = reg.records("legal-watch")
        match = next((i for i in items if i["id"] == item_id), None)
        if match is None:
            raise UsageError(f"unknown legal watch item {item_id}")
        match.update(reviewed_at=dt.date.today().isoformat(), outcome=outcome)
        if next_review:
            match.update(review_by=next_review, reviewed_at=None)
        _write_records(
            reg.root / "compliance" / "legal-watch.yaml",
            "items",
            items,
            "# Pending decisions and legal dates that can change the rules (FR-028).\n",
        )
        say(f"reviewed {item_id}")

    _run(fn)
