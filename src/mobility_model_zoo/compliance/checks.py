"""Compliance checks, one function per stage (contracts/checks.md). Every check fails closed."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mobility_model_zoo.compliance.findings import Finding, Stage, parse_date
from mobility_model_zoo.compliance.register import Register

MAX_WAIVER_DAYS = 183  # waivers expire at most 6 months after approval


@dataclass
class Context:
    """What a stage needs. Data-dependent stages get the paths they read; CI stages need none."""

    reg: Register
    model: str | None = None
    version: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def root(self) -> Path:
        return self.reg.root

    @property
    def today(self) -> dt.date:
        return self.reg.today


# ---- meta (C-M1 … C-M4) ---------------------------------------------------------------------


def _record_id(rec: dict[str, Any], rel: str) -> str:
    return f"{rel}#{rec.get('id', '-')}"


def stage_meta(ctx: Context) -> list[Finding]:
    reg = ctx.reg
    findings = reg.schema_findings()
    if findings:  # the other meta checks need a valid register
        return findings
    today = ctx.today
    for rel, data in reg.files.items():
        records = [data] if reg.stems[rel] in ("controller", "release-compliance") else None
        if records is None:
            records = [r for _, r in reg.located(reg.stems[rel]) if _ == rel]
        for rec in records:
            due = parse_date(rec.get("next_review"))
            if due and due < today:
                findings.append(
                    Finding(
                        "C-M2",
                        "meta",
                        _record_id(rec, rel),
                        "next_review",
                        f"review overdue since {due}",
                    )
                )
    for rel, item in reg.located("legal-watch"):
        due = parse_date(item.get("review_by"))
        if due and due < today and not item.get("reviewed_at"):
            findings.append(
                Finding(
                    "C-M2",
                    "meta",
                    _record_id(item, rel),
                    "review_by",
                    f"legal watch item not reviewed by {due}",
                )
            )
    for rel, d in reg.located("decisions"):
        due = parse_date(d.get("review_by"))
        if due and due < today:
            findings.append(
                Finding(
                    "C-M2",
                    "meta",
                    _record_id(d, rel),
                    "review_by",
                    f"decision review overdue since {due}",
                )
            )
    for rel, w in reg.located("waivers"):
        approved, expires = parse_date(w.get("approved_at")), parse_date(w.get("expires_at"))
        if not expires or expires < today:
            findings.append(Finding("C-M3", "meta", _record_id(w, rel), "expires_at", "waiver expired"))
        elif approved and (expires - approved).days > MAX_WAIVER_DAYS:
            findings.append(
                Finding(
                    "C-M3", "meta", _record_id(w, rel), "expires_at", "waiver runs longer than 6 months"
                )
            )
    for rel, r in reg.located("requests"):
        deadline = parse_date(r.get("deadline"))
        if not r.get("answered_at") and deadline and deadline < today:
            findings.append(
                Finding(
                    "C-M4",
                    "meta",
                    _record_id(r, rel),
                    "deadline",
                    f"request open past its deadline {deadline}",
                )
            )
    for rel, rc in ((rel, d) for rel, d in reg.files.items() if reg.stems[rel] == "release-compliance"):
        if rc.get("ai_system", {}).get("is_system") and rc.get("exclusion_basis") != "art2_12":
            findings.append(
                Finding(
                    "C-M1",
                    "meta",
                    rel,
                    "exclusion_basis",
                    "an AI system without monetisation relies on art2_12",
                )
            )
    return findings


STAGES: dict[str, Stage] = {
    "meta": ("meta", stage_meta),
}

# Stages that need no data outside git; run in CI by `zoo compliance check --ci`.
CI_STAGES = ["meta"]


def stages_named(names: list[str]) -> list[Stage]:
    unknown = [n for n in names if n not in STAGES]
    if unknown:
        raise KeyError(f"unknown stage(s): {', '.join(unknown)}; known: {', '.join(STAGES)}")
    return [STAGES[n] for n in names]
