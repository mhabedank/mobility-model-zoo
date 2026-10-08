"""Ingest checks before chunks are cut from snapshots (C-I1 … C-I7).

Called by `jtbd corpus autochunk`. Works on plain data (snapshot metadata), so it does not depend on
the jtbd package. Windows with special-category terms are excluded for classes that quarantine them
(C-I6, decision D12).
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from mobility_model_zoo.compliance.findings import Finding
from mobility_model_zoo.compliance.register import Register
from mobility_model_zoo.compliance.scan import art9_flags

REQUIRED = ("licence", "permitted_use", "signals", "personal_data", "retention_until", "class")


def harness_present(root: Path) -> bool:
    return (root / "compliance" / "controller.yaml").exists()


def allowlisted(reg: Register) -> set[str]:
    return {e["id"] for e in (reg.lists("licence-allowlist") or {}).get("licences", [])}


def check_snapshots(reg: Register, snapshots: Iterable[dict[str, Any]]) -> list[Finding]:
    """snapshots: dicts with snapshot_id, origin_url, source_type and use ('train' or 'eval')."""
    findings: list[Finding] = []
    allow = allowlisted(reg)
    classes = {c["id"]: c for c in reg.records("source-classes")}
    by_origin = {s["origin_url"]: s for s in reg.records("sources") + reg.records("datasets")}
    for snap in snapshots:
        sid = snap["snapshot_id"]
        rec = by_origin.get(snap["origin_url"])
        if rec is None:
            findings.append(
                Finding(
                    "C-I1",
                    "ingest",
                    sid,
                    "-",
                    f"no source record for {snap['origin_url']}; add one (`zoo compliance add-sources`)",
                )
            )
            continue
        for key in REQUIRED:
            if rec.get(key) in (None, "", []):
                findings.append(Finding("C-I1", "ingest", rec["id"], key, "missing"))
        licence = rec.get("licence", "unknown")
        if snap["use"] == "train":
            if licence not in allow:
                findings.append(
                    Finding(
                        "C-I2",
                        "ingest",
                        rec["id"],
                        "licence",
                        f"{licence} is not on the licence allowlist for training",
                    )
                )
            if rec.get("permitted_use") != "training_allowed":
                findings.append(Finding("C-I2", "ingest", rec["id"], "permitted_use", "benchmark_only"))
        if "unconfirmed" in licence:
            findings.append(
                Finding(
                    "C-I3",
                    "ingest",
                    rec["id"],
                    "licence",
                    "official-work status not confirmed (§5 UrhG decision missing)",
                )
            )
        pdata = rec.get("personal_data") or {}
        if pdata.get("human_subjects") and pdata.get("consent_or_ethics") in (None, "", "unknown"):
            findings.append(
                Finding(
                    "C-I4",
                    "ingest",
                    rec["id"],
                    "consent_or_ethics",
                    "human-subject data without consent or ethics basis",
                )
            )
        vehicle = rec.get("vehicle_data") or {}
        if any(v == "present" for v in vehicle.values()):
            findings.append(
                Finding(
                    "C-I5",
                    "ingest",
                    rec["id"],
                    "vehicle_data",
                    "VIN, GPS or absolute timestamps present and not removed",
                )
            )
        cls = classes.get(rec.get("class", ""))
        if cls is None:
            findings.append(Finding("C-I1", "ingest", rec["id"], "class", "unknown source class"))
        if snap.get("source_type") == "reddit" or "reddit.com" in snap["origin_url"]:
            terms = (cls or {}).get("platform_terms") or rec.get("platform_terms")
            if not terms or terms.get("ml_use") != "allowed":
                findings.append(
                    Finding(
                        "C-I7",
                        "ingest",
                        rec["id"],
                        "platform_terms",
                        "platform API terms not recorded as allowing ML use",
                    )
                )
        signals = rec.get("signals") or {}
        if any(
            signals.get(k) == "deny" for k in ("robots", "tdmrep", "x_robots", "meta_noai", "ai_txt")
        ) and not rec.get("licence", "").startswith(("CC-BY", "CC0", "LicenseRef-official-work")):
            findings.append(
                Finding(
                    "C-I1",
                    "ingest",
                    rec["id"],
                    "signals",
                    "an opt-out signal is recorded and no licence grants the use",
                )
            )
    return findings


def quarantine_classes(reg: Register) -> set[str]:
    return {c["id"] for c in reg.records("source-classes") if c.get("art9_handling") == "quarantine"}


def window_allowed(
    reg: Register, origin_url: str, text: str, lexicon: dict[str, list[str]] | None = None
) -> bool:
    """False if the window has special-category terms and its class quarantines them (C-I6)."""
    rec = reg.source(
        next((s["id"] for s in reg.records("sources") if s["origin_url"] == origin_url), "")
    )
    if rec is None or rec.get("class") not in quarantine_classes(reg):
        return True
    lexicon = (
        lexicon if lexicon is not None else (reg.lists("special-categories") or {}).get("categories", {})
    )
    return not art9_flags(text, lexicon)
