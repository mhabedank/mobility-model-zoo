"""Withdraw an entry after an objection (FR-021, research R11).

The request must already be logged with `zoo compliance request add`. The entry becomes
`withdrawn`, and the keyed hashes of its addresses join compliance/suppression.yaml, so the
fetch-time signal check (C-F5) refuses the resource too.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from mobility_model_zoo.catalog import states
from mobility_model_zoo.catalog.model import Catalog
from mobility_model_zoo.compliance.signals import canonical
from mobility_model_zoo.datasets import UsageRefused
from mobility_model_zoo.release.errors import CredentialError, UsageError

REQUEST_TYPES = ("objection", "takedown", "opt_out")
HEADER = "# Suppressed URLs and identifiers (keyed hashes); fetch and train skip them.\n"


def withdraw(cat: Catalog, entry_id: str, request_id: str, zoo_root: Path, today: str) -> int:
    from mobility_model_zoo.compliance.hashing import keyed_hash

    if entry_id not in cat.entries:
        raise UsageError(f"unknown entry {entry_id}")
    req_path = zoo_root / "compliance" / "requests.yaml"
    requests = (
        (yaml.safe_load(req_path.read_text(encoding="utf-8")) or {}).get("requests", [])
        if req_path.exists()
        else []
    )
    request = next((r for r in requests if r.get("id") == request_id), None)
    if request is None or request.get("type") not in REQUEST_TYPES:
        raise UsageRefused(
            f"{request_id}: no {'/'.join(REQUEST_TYPES)} request in compliance/requests.yaml "
            "(log it with `zoo compliance request add` first)"
        )
    e = cat.entries[entry_id]
    urls = [e["landing_url"], *(a["url"] for a in e.get("access") or [])]
    urls += [a["download_url"] for a in e.get("access") or [] if a.get("download_url")]
    try:
        hashes = sorted({keyed_hash(canonical(u)) for u in urls})
    except RuntimeError as err:
        raise CredentialError(str(err)) from None
    sup_path = zoo_root / "compliance" / "suppression.yaml"
    entries = (
        (yaml.safe_load(sup_path.read_text(encoding="utf-8")) or {}).get("entries", [])
        if sup_path.exists()
        else []
    )
    known = {x["hash"] for x in entries}
    added = [h for h in hashes if h not in known]
    entries += [{"hash": h, "kind": "url", "request_id": request_id, "added_at": today} for h in added]
    sup_path.write_text(
        HEADER + yaml.safe_dump({"entries": entries}, sort_keys=False, width=110), encoding="utf-8"
    )
    states.set_status(e, "withdrawn", today, f"{request['type']} {request_id}", request_id=request_id)
    states.set_flag(e, "owner_decision_needed", False)
    cat.write_entry(e)
    return len(added)
