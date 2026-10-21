"""Gate check: no Claude inputs behind a release (constitution, Principle XI; feature 021, R21).

Principle XI: no Claude output may become training data, teacher output, labels, evaluation
judgments or any selection signal of a zoo model. The release gate (rule 7) confirms it for every
release from what the release records:

- every teacher in `provenance.teachers`;
- every route of the release's compliance record (`provenance.routes`), with the roles the
  recipients log records for it (labeling, reference, teacher, PII review, ...);
- the evaluation reference of the release record.

A model belongs to the Claude family if its route says `model_family: claude`, or if its model id
or hosting provider names Claude or Anthropic (a safety net for entries without the field).

The only exception is the frozen benchmark references that Principle XI keeps (pilot-v1, pilot-v2,
cluster-v1, spike-v2): a Claude route passes only if every role recorded for it is `reference` and
an owner decision in compliance/decisions.yaml names both the route and this release in its scope
(today D-claude-risk-0.1.x for scout-large 0.1.0-0.1.3). A Claude teacher never passes.
"""

from __future__ import annotations

import re
from typing import Any

CLAUDE = re.compile(r"claude|anthropic", re.IGNORECASE)
REFERENCE_ROLES = {"reference"}


def is_claude(entry: dict[str, Any]) -> bool:
    if str(entry.get("model_family", "")).lower() == "claude":
        return True
    text = " ".join(str(entry.get(k, "")) for k in ("model_id", "model_version", "hosting_provider"))
    return bool(CLAUDE.search(text))


def _covering_decision(decisions: list[dict], route_id: str, release: str) -> str | None:
    for d in decisions:
        scope = {str(s) for s in d.get("scope", [])}
        if f"compliance/providers.yaml#{route_id}" in scope and release in scope:
            return d["id"]
    return None


def claude_findings(
    *,
    model: str,
    version: str,
    teachers: list[dict[str, Any]],
    routes: list[dict[str, Any]],
    roles: dict[str, set[str]],
    decisions: list[dict[str, Any]],
    evaluation_reference: str = "",
    provider_routes: list[dict[str, Any]] | None = None,
) -> tuple[list[str], str]:
    """(failures, confirmation). `routes` are the release's routes (provider records), `roles`
    the recorded roles per route id, `provider_routes` all routes (to resolve teacher model ids)."""
    release = f"{model}@{version}"
    failures: list[str] = []
    claude_ids = {
        r.get("model_id") for r in (provider_routes or []) if is_claude(r) and r.get("model_id")
    }
    for t in teachers:
        if is_claude(t) or t.get("model_id") in claude_ids:
            failures.append(
                f"teacher {t.get('model_id')} belongs to the Claude family; Claude is never a "
                "teacher (Principle XI)"
            )
    excepted = []
    for r in routes:
        if not is_claude(r):
            continue
        used = roles.get(r["id"], set())
        decision = _covering_decision(decisions, r["id"], release)
        if used and used <= REFERENCE_ROLES and decision:
            excepted.append(f"{r['id']} as frozen benchmark reference ({decision})")
            continue
        why = (
            f"roles {', '.join(sorted(used))}"
            if used and not used <= REFERENCE_ROLES
            else "no owner decision names this route and release"
            if used
            else "no recorded role"
        )
        failures.append(f"route {r['id']} belongs to the Claude family ({why}; Principle XI)")
    if CLAUDE.search(evaluation_reference or "") and not excepted:
        failures.append(
            "the evaluation reference names a Claude model and no decision allows it (Principle XI)"
        )
    if failures:
        return failures, ""
    note = f"no Claude inputs ({len(teachers)} teachers, {len(routes)} routes checked)"
    if excepted:
        note += "; Claude only " + "; ".join(excepted)
    return [], note
