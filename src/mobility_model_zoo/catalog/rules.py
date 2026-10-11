"""K8: the provisional usage decision of an entry from its licence, signals and terms (research R5)."""

from __future__ import annotations

import datetime as dt
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from mobility_model_zoo.catalog.validate import Finding

RULES_FILE = Path(__file__).resolve().parent / "rules.yaml"
SIGNALS = ("robots", "tdmrep", "x_robots", "meta_noai", "ai_txt", "content_signal", "content_usage")


@cache
def table() -> dict[str, Any]:
    return yaml.safe_load(RULES_FILE.read_text(encoding="utf-8"))


def _usage(
    use: str,
    redistribution: str,
    rule: str,
    rationale: str,
    today: str,
    evidence: str | None,
    share_alike: bool = False,
) -> dict[str, Any]:
    out = {
        "permitted_use": use,
        "redistribution": redistribution,
        "rule": rule,
        "rules_version": int(table()["version"]),
        "rationale": rationale,
        "evidence_url": evidence,
        "decided_at": today,
    }
    if share_alike:
        out["share_alike"] = True
    return out


def opt_out(entry: dict[str, Any]) -> list[str]:
    signals = entry.get("signals") or {}
    return [name for name in SIGNALS if signals.get(name) == "deny"]


def apply(
    entry: dict[str, Any], allowlist: list[dict[str, Any]], today: str | None = None
) -> tuple[dict[str, Any], list[str]]:
    """(usage, flags) for the entry. First matching rule wins (U1 overrides an owner decision)."""
    today = today or dt.date.today().isoformat()
    lic = entry.get("licence") or {}
    lid = str(lic.get("id", "unknown"))
    evidence = lic.get("evidence_url")
    terms = entry.get("platform_terms") or {}
    status = (entry.get("status") or {}).get("value")

    denied = opt_out(entry)
    if status == "withdrawn" or denied or terms.get("ml_use") == "not_allowed":
        why = (
            "withdrawn after an objection"
            if status == "withdrawn"
            else f"opt-out signal: {', '.join(denied)}"
            if denied
            else "platform terms forbid machine-learning use"
        )
        return _usage("not_usable", "not_allowed", "U1", why, today, evidence), []
    old = entry.get("usage") or {}
    if old.get("rule") == "U0":
        return old, []
    if lid in ("unknown", "mixed"):
        return _usage("undetermined", "unclear", "U2", f"licence is {lid}", today, evidence), []
    # the list also holds non-commercial licences (U4 decides them) and licences that never train
    allowed = {
        item["id"]: item
        for item in allowlist
        if item.get("trains", True) and not item.get("non_commercial")
    }
    if lid in allowed:
        sa = bool(allowed[lid].get("share_alike"))
        why = f"{lid} is on the licence allow-list" + (" (share-alike)" if sa else "")
        return _usage("training_allowed", "allowed", "U3", why, today, evidence, sa), []
    parts = lid.upper().split("-")
    if "NC" in parts or "ND" in parts:
        return _usage(
            "benchmark_only",
            "not_allowed",
            "U4",
            f"{lid} is non-commercial or no-derivatives",
            today,
            evidence,
        ), []
    kind = (entry.get("publisher") or {}).get("kind")
    mapping = table().get("source_class_map", {}).get(kind)
    if lid in table().get("proprietary_ids", []) and mapping:
        why = (
            f"proprietary; source class {mapping['topic']}/{mapping['class']} "
            f"decides {mapping['permitted_use']}"
        )
        return _usage(mapping["permitted_use"], "not_allowed", "U5", why, today, evidence), []
    return (
        _usage(
            "undetermined",
            "unclear",
            "U6",
            f"no rule decides {lid} from a {kind} source",
            today,
            evidence,
        ),
        ["owner_decision_needed"],
    )


def k8(entry: dict[str, Any], allowlist: list[dict[str, Any]]) -> list[Finding]:
    """The stored usage must equal what the rules decide today (rule and outcome, not the date)."""
    stored = entry.get("usage")
    if not stored:
        return []
    expected, _ = apply(entry, allowlist, stored.get("decided_at"))
    keys = ("permitted_use", "redistribution", "rule")
    if any(stored.get(k) != expected.get(k) for k in keys):
        got = "/".join(str(stored.get(k)) for k in keys)
        want = "/".join(str(expected.get(k)) for k in keys)
        return [
            Finding(
                str(entry.get("id")),
                "K8",
                "fail",
                "usage",
                f"stored {got}, rules decide {want}; run `zoo catalog check`",
            )
        ]
    return []
