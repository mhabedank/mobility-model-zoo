"""Train-stage checks (C-T1 … C-T5) and retention (C-R1), on plain data.

Training data checks run in `jtbd span data-check` (and in future task tools) before a model is
trained: suppressed or opted-out sources, licences that forbid training or do not fit the declared
usage class of the model (constitution 2.1.0: non-commercial data trains non-commercial models only),
share-alike that the class does not carry, teacher routes without output rights, and redaction
recall.
"""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from mobility_model_zoo.compliance.findings import Finding, parse_date
from mobility_model_zoo.compliance.register import Register
from mobility_model_zoo.compliance.usage import LicenceList, UsageClass

SIGNALS = ("robots", "tdmrep", "x_robots", "meta_noai", "ai_txt")
LICENSED = (
    "CC-BY",
    "CC0",
    "LicenseRef-official-work",
    "LicenseRef-Open-Parliament",
    "LicenseRef-US-PD",
    "LicenseRef-OGL",
    "LicenseRef-Senedd",
    "LicenseRef-Scottish",
    "LicenseRef-EU-Reuse",
)


def check_training(
    reg: Register,
    *,
    origins: Iterable[str],
    model_licence: str | None,
    teachers: Iterable[str],
    usage_class: str = "commercial",
    url_hash=None,
    recall: float | None = None,
    min_recall: float = 0.95,
) -> list[Finding]:
    findings: list[Finding] = []
    target = UsageClass.parse(usage_class)
    licences = LicenceList.load(reg.root)
    marked = licences.licence_class(model_licence) if model_licence else None
    if marked is not None:
        target = target.combine(marked)
    by_origin = {s["origin_url"]: s for s in reg.records("sources") + reg.records("datasets")}
    suppressed = {e["hash"] for e in reg.records("suppression") if e.get("kind") == "url"}
    share_alike = False
    for origin in sorted(set(origins)):
        rec = by_origin.get(origin)
        if rec is None:
            findings.append(Finding("C-T1", "train", origin, "-", "no source record"))
            continue
        if url_hash and url_hash(origin) in suppressed:
            findings.append(Finding("C-T1", "train", rec["id"], "-", "on the suppression list"))
        signals = rec.get("signals") or {}
        if any(signals.get(k) == "deny" for k in SIGNALS) and not rec["licence"].startswith(LICENSED):
            findings.append(
                Finding(
                    "C-T1",
                    "train",
                    rec["id"],
                    "signals",
                    "opt-out signal recorded and no licence grants the use",
                )
            )
        licence = rec.get("licence", "unknown")
        entry = licences.get(licence)
        if entry is None or not entry.trains:
            # unknown, no-derivatives, all rights reserved and every licence not on the list
            findings.append(Finding("C-T2", "train", rec["id"], "licence", f"{licence} cannot train"))
        elif target.commercial and (entry.non_commercial or rec.get("commercial_use") is False):
            findings.append(Finding("C-T2", "train", rec["id"], "licence",
                                    f"{licence} is non-commercial; the model is declared {target}"))
        if rec.get("permitted_use") != "training_allowed":
            findings.append(Finding("C-T2", "train", rec["id"], "permitted_use", "benchmark_only"))
        share_alike |= bool(entry and entry.share_alike)
    if share_alike and not target.share_alike:
        findings.append(
            Finding(
                "C-T3",
                "train",
                "model",
                "licence",
                f"share-alike training data but the model is declared {target}"
                + (f" with licence {model_licence}" if model_licence else ""),
            )
        )
    for teacher in teachers:
        terms = reg.output_training_terms(teacher)
        if terms in ("no", "unclear") or (terms == "non_commercial" and target.commercial):
            findings.append(
                Finding(
                    "C-T4",
                    "train",
                    teacher,
                    "output_training_permitted",
                    "a route of this teacher does not permit training on outputs"
                    if terms != "non_commercial"
                    else f"outputs may train non-commercial models only; the model is declared {target}",
                )
            )
    if recall is not None and recall < min_recall:
        findings.append(
            Finding("C-T5", "train", "redaction-set", "recall", f"{recall} below {min_recall} (D9)")
        )
    return findings


def suppressed_identifier_findings(
    reg: Register, chunks: Iterable[tuple[str, str]], hasher
) -> list[Finding]:
    """C-T1 for suppressed names and handles: keyed hashes of every 1-3 word n-gram of each chunk
    are compared with the identifier entries of the suppression list. chunks: (chunk id, text)."""
    import re

    wanted = {e["hash"] for e in reg.records("suppression") if e.get("kind") == "identifier"}
    if not wanted:
        return []
    if hasher is None:
        return [Finding("C-T1", "train", "suppression", "-", "MMZ_SUPPRESSION_KEY not set")]
    findings = []
    for chunk_id, text in chunks:
        tokens = re.findall(r"[@/\w.-]+", text)
        grams = {" ".join(tokens[i : i + n]) for n in (1, 2, 3) for i in range(len(tokens) - n + 1)}
        if any(hasher(g) in wanted for g in grams):
            findings.append(Finding("C-T1", "train", chunk_id, "-", "contains a suppressed identifier"))
    return findings


# ---- retention (C-R1) ------------------------------------------------------------------------


def retention_findings(root: Path, today: dt.date | None = None) -> list[Finding]:
    """Snapshots past retention_until or without one; deleted snapshots are skipped."""
    import yaml

    today = today or dt.date.today()
    findings = []
    for meta_path in sorted((root / "data" / "snapshots").glob("*/source.yaml")):
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
        if not (meta_path.parent / "text.txt").exists() and not list(meta_path.parent.glob("raw.*")):
            continue  # already deleted
        until = parse_date(meta.get("retention_until"))
        sid = meta.get("snapshot_id", meta_path.parent.name)
        if until is None:
            findings.append(Finding("C-R1", "retention", sid, "retention_until", "no retention date"))
        elif until < today:
            findings.append(Finding("C-R1", "retention", sid, "retention_until", f"expired {until}"))
    return findings


def delete_snapshot(root: Path, snapshot_id: str, reason: str) -> dict[str, Any]:
    """Delete raw and text of one snapshot; log hash and URL; keep source.yaml as evidence."""
    import hashlib

    import yaml

    folder = root / "data" / "snapshots" / snapshot_id
    meta_path = folder / "source.yaml"
    if not meta_path.exists():
        raise FileNotFoundError(f"unknown snapshot {snapshot_id}")
    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    removed = []
    for path in [*folder.glob("raw.*"), folder / "text.txt"]:
        if path.exists():
            removed.append({"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
            path.unlink()
    entry = {
        "snapshot_id": snapshot_id,
        "origin_url": meta.get("origin_url"),
        "deleted_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "reason": reason,
        "files": removed,
    }
    log = root / "data" / "compliance" / "deletions.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry
