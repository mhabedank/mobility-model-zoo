"""Findings and the fail-closed stage runner (specs/006-compliance-harness, FR-006).

A stage is a function that returns findings. The runner stops at the first stage with findings, so
data that should never have been collected is not processed by later stages. Missing evidence is a
finding: checks never treat an absent value as a pass.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from mobility_model_zoo.release.errors import GateFailed

UNKNOWN = "unknown"


@dataclass(frozen=True)
class Finding:
    check_id: str
    stage: str
    record: str
    field: str
    reason: str

    def line(self) -> str:
        return f"{self.stage} / {self.record} / {self.field} / {self.reason} [{self.check_id}]"


class StageFailed(GateFailed):
    """A compliance stage produced findings; later stages did not run."""

    def __init__(self, findings: list[Finding]):
        self.findings = findings
        super().__init__([f.line() for f in findings])


Stage = tuple[str, Callable[[Any], list[Finding]]]


def run_stages(stages: Iterable[Stage], ctx: Any, say: Callable[[str], None] | None = None) -> list[str]:
    """Run stages in order; raise StageFailed at the first stage with findings. Returns passed stages."""
    passed: list[str] = []
    for name, fn in stages:
        findings = fn(ctx)
        if findings:
            raise StageFailed(findings)
        passed.append(name)
        if say:
            say(f"ok: {name}")
    return passed


def is_unknown(value: Any) -> bool:
    return value == UNKNOWN


def parse_date(value: Any) -> dt.date | None:
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        try:
            return dt.date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def require(
    record: dict[str, Any],
    field: str,
    *,
    check_id: str,
    stage: str,
    record_id: str,
    waiver_ok: Callable[[str, str], bool],
) -> Finding | None:
    """A value the check needs. Missing or empty fails; `unknown` needs a dated attempt and a waiver."""
    value = record.get(field)
    if value is None or value == "" or value == []:
        return Finding(check_id, stage, record_id, field, "missing")
    if is_unknown(value):
        if not parse_date(record.get("unknown_checked_at")):
            return Finding(check_id, stage, record_id, field, "unknown without unknown_checked_at")
        if not waiver_ok(check_id, record_id):
            return Finding(check_id, stage, record_id, field, "unknown and no valid waiver")
    return None
