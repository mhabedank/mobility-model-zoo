"""Checks before texts leave the machine and after a hosted answer comes back (C-P1 … C-P6).

Pure functions on plain data, so the labeling runner can call them without the compliance module
depending on the jtbd package.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from mobility_model_zoo.compliance.findings import Finding
from mobility_model_zoo.compliance.register import Register
from mobility_model_zoo.compliance.scan import pii

# Test doubles and the vote ensemble: nothing leaves the process.
TEST_BACKENDS = {"mock", "ensemble"}
LOCAL_BACKENDS = {"ollama", "openai_compat"}


def quarantined(root: Path) -> set[str]:
    path = root / "data" / "compliance" / "quarantine.jsonl"
    if not path.exists():
        return set()
    return {json.loads(line)["chunk_id"] for line in path.read_text().splitlines() if line.strip()}


def route_allows(route: dict[str, Any], role: str) -> tuple[bool, str]:
    """Allow rule of decisions D-routing and D-routing-scc."""
    if route.get("access_path") == "consumer_cli":
        return False, "consumer subscription routes are not allowed for new runs (D-claude-api)"
    if role not in route.get("allowed_for", []):
        return False, f"route {route['id']} is not allowed for role {role}"
    if route.get("access_path") == "local":
        return True, ""
    region_ok = str(route.get("region", "")).upper().startswith(("DE", "EU", "IE", "FR", "NL", "AT"))
    transfer_ok = region_ok or route.get("dpf_listed") is True or (
        route.get("dpa") is True and route.get("scc") is True)
    if not transfer_ok:
        return False, f"route {route['id']}: no EU region, DPF listing or DPA with SCCs"
    if route.get("zero_data_retention") is not True or route.get("training_on_inputs") is not False:
        return False, f"route {route['id']}: needs zero data retention and no training on inputs"
    if not route.get("signoff"):
        return False, f"route {route['id']}: no owner sign-off"
    return True, ""


def check_batch(reg: Register, *, model_id: str, backend: str, role: str, route_id: str | None,
                provider_order: list[str] | None, items: Iterable[tuple[str, str, str | None]],
                current_patterns: str) -> list[Finding]:
    """items: (chunk id, text to be sent, redaction patterns version of the chunk)."""
    findings: list[Finding] = []
    blocked = quarantined(reg.root)
    for chunk_id, text, version in items:
        # Older pattern versions are allowed (frozen benchmarks cannot be re-redacted); the re-scan
        # below (C-P2) is what guards the text that is actually sent.
        if not version:
            findings.append(Finding("C-P1", "pre-send", chunk_id, "redaction", "never redacted"))
        hits = pii(text)
        if hits:
            kinds = ",".join(sorted({h.kind for h in hits}))
            findings.append(
                Finding("C-P2", "pre-send", chunk_id, kinds, f"{len(hits)} identifier(s) left"))
        if chunk_id in blocked:
            findings.append(Finding("C-P3", "pre-send", chunk_id, "-", "quarantined (special category)"))
    if backend in TEST_BACKENDS:
        return findings
    if not route_id:
        findings.append(Finding("C-P4", "pre-send", model_id, "route",
                                "no route in models.yaml; every labeling model needs one"))
        return findings
    route = reg.route(route_id)
    if route is None:
        findings.append(Finding("C-P4", "pre-send", model_id, "route", f"unknown route {route_id}"))
        return findings
    ok, why = route_allows(route, role)
    if not ok:
        findings.append(Finding("C-P4", "pre-send", route_id, "allowed_for", why))
    if backend == "openrouter":
        pinned = route.get("openrouter_provider")
        norm = lambda v: str(v).lower().replace(" ", "")  # noqa: E731 - slug vs display name
        if not provider_order or not pinned or [norm(v) for v in provider_order] != [norm(pinned)]:
            findings.append(Finding("C-P5", "pre-send", route_id, "provider_order",
                                    f"OpenRouter must be pinned to exactly [{pinned}]"))
    return findings


def check_answer(route: dict[str, Any] | None, backend: str, meta: dict[str, Any]) -> Finding | None:
    """C-P6: the provider that answered must be the route's provider."""
    if backend != "openrouter" or route is None:
        return None
    answered = (meta or {}).get("provider")
    if str(answered).lower() != str(route.get("openrouter_provider")).lower():
        return Finding("C-P6", "post-receive", route["id"], "provider",
                       f"answered by {answered!r}, route pins {route.get('openrouter_provider')!r}")
    return None
