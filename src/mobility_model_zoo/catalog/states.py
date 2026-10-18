"""State machine of an entry (data-model.md "Entity: Status"). The only module that sets `status`."""

from __future__ import annotations

import datetime as dt
from typing import Any

TERMINAL = ("rejected", "retired", "withdrawn")
CLEARABLE_METHODS = ("direct_download", "bulk_dump", "api", "feed", "page_by_page")
BLOCKING_FLAGS = (
    "unreachable",
    "personal_data_in_metadata",
    "owner_decision_needed",
    "licence_conflict",
    "licence_unconfirmed",
)
RETIRE_AFTER = 3  # 404/410 answers …
RETIRE_SPAN_DAYS = 7  # … at least this many days apart


def set_status(
    entry: dict[str, Any],
    value: str,
    today: str,
    reason: str | None = None,
    request_id: str | None = None,
) -> None:
    status = entry.setdefault("status", {})
    flags = status.get("flags") or []
    if status.get("value") != value:
        status["since"] = today
    status["value"] = value
    status["reason"] = reason
    if request_id is not None:
        status["request_id"] = request_id
    elif "request_id" in status and value != "withdrawn":
        status.pop("request_id")
    status["flags"] = flags
    if not flags:
        status.pop("flags")


def flags(entry: dict[str, Any]) -> list[str]:
    return list((entry.get("status") or {}).get("flags") or [])


def set_flag(entry: dict[str, Any], flag: str, on: bool = True) -> None:
    status = entry.setdefault("status", {})
    current = [f for f in status.get("flags") or [] if f != flag]
    if on:
        current.append(flag)
    if current:
        status["flags"] = sorted(current)
    else:
        status.pop("flags", None)


def clearable_route(entry: dict[str, Any]) -> dict[str, Any] | None:
    for route in entry.get("access") or []:
        if (
            route.get("method") in CLEARABLE_METHODS
            and route.get("cost") == "free"
            and route.get("auth") in ("none", "api_key")
        ):
            return route
    return None


def clear_blockers(entry: dict[str, Any]) -> list[str]:
    """Why an entry cannot be cleared (empty = clearable). FR-018, data-model.md."""
    out = []
    usage = entry.get("usage") or {}
    if usage.get("permitted_use") not in ("training_allowed", "benchmark_only"):
        out.append(f"permitted use is {usage.get('permitted_use', 'undetermined')}")
    signals = entry.get("signals") or {}
    if not signals:
        out.append("opt-out signals not checked")
    denied = [k for k, v in signals.items() if k != "checked_at" and v == "deny"]
    if denied:
        out.append(f"opt-out signal: {', '.join(denied)}")
    terms = entry.get("platform_terms") or {}
    for key in ("ml_use", "automated_access"):
        if terms.get(key) == "not_allowed":
            out.append(f"platform terms: {key} not allowed")
    blocking = [f for f in flags(entry) if f in BLOCKING_FLAGS]
    if blocking:
        out.append(f"flags: {', '.join(blocking)}")
    if clearable_route(entry) is None:
        out.append("no free access route usable without payment, request or per-resource account")
    return out


def _gone(entry: dict[str, Any], today: str) -> bool:
    """Three 404/410 answers of K4 at least 7 days apart (kept in checks[K4].previous)."""
    k4 = next((c for c in entry.get("checks") or [] if c.get("check") == "K4"), None)
    if not k4:
        return False
    history = list((k4.get("previous") or {}).get("gone_dates") or [])
    if len(history) < RETIRE_AFTER:
        return False
    dates = sorted(dt.date.fromisoformat(d) for d in history)
    picked = [dates[0]]
    for d in dates[1:]:
        if (d - picked[-1]).days >= RETIRE_SPAN_DAYS:
            picked.append(d)
    return len(picked) >= RETIRE_AFTER


def transition(entry: dict[str, Any], today: str, changed: list[str] | None = None) -> str:
    """Apply the state machine after checks and rules ran. Returns the new status value.

    `changed` names what a re-check found different (licence, evidence, signals); a cleared entry
    then falls back to verified.
    """
    current = (entry.get("status") or {}).get("value", "candidate")
    if current in TERMINAL or current == "fetched":
        return current
    results = {c["check"]: c["result"] for c in entry.get("checks") or []}
    if _gone(entry, today):
        set_status(entry, "retired", today, "landing page gone (404/410 on three checks ≥ 7 days apart)")
        return "retired"
    if any(r == "fail" for r in results.values()):
        if current == "cleared":
            set_status(
                entry,
                "verified",
                today,
                "a re-check failed: " + ", ".join(sorted(k for k, r in results.items() if r == "fail")),
            )
            return "verified"
        return current
    if current == "candidate":
        if not {"K4", "K6"} <= results.keys():  # network checks have not run yet
            return current
        set_status(entry, "verified", today)
        current = "verified"
    if current == "cleared" and changed:
        set_status(entry, "verified", today, "re-check changed: " + ", ".join(changed))
        set_flag(entry, "licence_changed", "licence" in changed or "evidence" in changed)
        return "verified"
    blockers = clear_blockers(entry)
    if current == "verified" and not blockers:
        set_status(entry, "cleared", today)
        return "cleared"
    if current == "cleared" and blockers:
        set_status(entry, "verified", today, "; ".join(blockers))
        return "verified"
    return current
