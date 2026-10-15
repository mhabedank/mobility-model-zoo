"""`zoo tracking audit`: scan the store for anything that is not an allowed number, hash or
metadata value (SC-007, research R8).

Re-applies the guard to every param, tag and metric key, and runs the release publication scan's
detectors over params, tags and text artifacts: personal identifiers (`compliance.scan.pii`) and,
where the snapshot corpus is on this machine, verbatim source text (`compliance.scan.overlap_spans`).
It also flags any value that names Claude as labeler, teacher, judge or model (constitution XI).
Findings print experiment, run and key; a value only as its first 12 characters, and never for
personal data or source text.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from . import guard

TEXT_ARTIFACTS = (".json", ".yaml", ".yml", ".md")
CLAUDE_KEYS = ("label", "teacher", "judge", "model", "reference", "backend")


@dataclass
class Finding:
    experiment: str
    run_id: str
    key: str
    problem: str
    value: str = ""

    def line(self) -> str:
        shown = f" ({self.value[:12]}…)" if self.value else ""
        return f"{self.experiment}  {self.run_id[:12]}  {self.key}: {self.problem}{shown}"


def _pii_allowlist() -> list[str]:
    try:
        from mobility_model_zoo.compliance.register import Register
        from mobility_model_zoo.compliance.release_checks import contact_allowlist
        from mobility_model_zoo.edge.paths import repo_root

        return contact_allowlist(Register.load(repo_root()).controller())
    except Exception:  # noqa: BLE001 - an allow-list only removes false positives
        return []


def _corpus_index():
    """The corpus index `zoo compliance scan-publish` saved (data/compliance/corpus-index/), the
    newest one, when it is on this machine."""
    try:
        from mobility_model_zoo.compliance.scan import CorpusIndex
        from mobility_model_zoo.edge.paths import repo_root

        saved = sorted(
            (repo_root() / "data" / "compliance" / "corpus-index").glob("*/index.json"),
            key=lambda p: p.stat().st_mtime,
        )
        return CorpusIndex.load(saved[-1].parent) if saved else None
    except Exception:  # noqa: BLE001
        return None


def scan_text(text: str, allow: list[str], index) -> list[str]:
    from mobility_model_zoo.compliance.scan import overlap_spans, pii

    problems = []
    hits = pii(text, allow)
    if hits:
        problems.append(f"{len(hits)} personal identifier(s)")
    if index is not None:
        from mobility_model_zoo.compliance.release_checks import VERBATIM_MAX_WORDS

        if overlap_spans(text, index, VERBATIM_MAX_WORDS):
            problems.append("verbatim source text")
    return problems


def audit(experiments: list[str] | None = None) -> tuple[list[Finding], list[str]]:
    from . import client as tc

    cl = tc.new_client()
    allow = _pii_allowlist()
    index = _corpus_index()
    notes = [] if index is not None else ["verbatim check skipped (no corpus here)"]
    findings: list[Finding] = []
    exps = [e for e in cl.search_experiments() if not experiments or e.name in experiments]
    for exp in exps:
        token = None
        while True:
            page = cl.search_runs([exp.experiment_id], max_results=500, page_token=token)
            for run in page:
                findings += _audit_run(cl, exp.name, run, allow, index)
            token = page.token
            if not token:
                break
    return findings, notes


def _audit_run(cl, exp: str, run, allow, index) -> list[Finding]:
    rid = run.info.run_id
    out: list[Finding] = []
    for key, value in run.data.params.items():
        try:
            guard.check_param(key, value)
        except guard.GuardRefused as e:
            out.append(Finding(exp, rid, f"param {key}", str(e), value))
        out += _text_findings(exp, rid, f"param {key}", value, allow, index)
        out += _claude(exp, rid, f"param {key}", key, value)
    for key, value in run.data.tags.items():
        if key.startswith("mlflow.") and key not in guard.SYSTEM_TAGS:
            continue  # MLflow's own bookkeeping (log-model history, parent run, …)
        try:
            guard.check_tag(key, value)
        except guard.GuardRefused as e:
            out.append(Finding(exp, rid, f"tag {key}", str(e), value))
        out += _text_findings(exp, rid, f"tag {key}", value, allow, index)
        out += _claude(exp, rid, f"tag {key}", key, value)
    for key in run.data.metrics:
        try:
            guard.check_key(key)
        except guard.GuardRefused as e:
            out.append(Finding(exp, rid, f"metric {key}", str(e)))
    out += _artifacts(cl, exp, rid, allow, index)
    return out


def _text_findings(exp, rid, where, value, allow, index) -> list[Finding]:
    # personal data and source text are never echoed, not even in part
    return [Finding(exp, rid, where, p) for p in scan_text(str(value), allow, index)]


def _claude(exp, rid, where, key, value) -> list[Finding]:
    if "claude" in str(value).lower() and any(k in key.lower() for k in CLAUDE_KEYS):
        return [
            Finding(
                exp, rid, where, "names Claude in a labeling, teacher or judge role (XI)", str(value)
            )
        ]
    return []


def _artifacts(cl, exp, rid, allow, index) -> list[Finding]:
    out = []
    stack = [None]
    while stack:
        folder = stack.pop()
        for item in cl.list_artifacts(rid, folder):
            if item.is_dir:
                stack.append(item.path)
                continue
            name = item.path
            if not name.startswith("config/") and Path(name).name not in guard.ARTIFACTS:
                if not name.startswith("system_metrics"):
                    out.append(Finding(exp, rid, f"artifact {name}", "not on the allow-list"))
                continue
            if Path(name).suffix.lower() not in TEXT_ARTIFACTS:
                continue
            with tempfile.TemporaryDirectory() as tmp:
                local = Path(cl.download_artifacts(rid, name, tmp))
                text = local.read_text(encoding="utf-8", errors="replace")
            out += [Finding(exp, rid, f"artifact {name}", p) for p in scan_text(text, allow, index)]
    return out
