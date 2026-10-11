"""The discovery pilot (spec: Riskiest Assumption and Pilot; constitution IV).

pilot/pilot-v1.yaml names the languages, modalities, runs and criteria. The criteria are fixed
before the first pilot run: `evaluate` refuses when they differ from the version committed before
the first run unless `criteria_changes` records a dated rationale.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import yaml

from mobility_model_zoo.catalog.model import Catalog, read_yaml
from mobility_model_zoo.datasets import UsageRefused


def _runs(cat: Catalog, ids: list[str]) -> list[dict[str, Any]]:
    headers = [read_yaml(p) for p in sorted((cat.root / "runs").glob("*.yaml"))]
    return [h for h in headers if not ids or h["id"] in ids]


def _criteria_at_commits(path: Path) -> list[tuple[str, dict[str, Any]]]:
    """[(commit date, criteria)] for every commit that touched the pilot file, oldest first."""
    rel = path.name
    try:
        log = subprocess.run(
            ["git", "-C", str(path.parent), "log", "--reverse", "--format=%H %cs", "--", rel],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split("\n")
    except (OSError, subprocess.CalledProcessError):
        return []
    out = []
    for line in filter(None, log):
        sha, date = line.split()
        try:
            text = subprocess.run(
                ["git", "-C", str(path.parent), "show", f"{sha}:./{rel}"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout
        except subprocess.CalledProcessError:
            continue
        out.append((date, (yaml.safe_load(text) or {}).get("criteria")))
    return out


def check_frozen(path: Path, pilot: dict[str, Any], first_run: str | None) -> None:
    history = _criteria_at_commits(path)
    if not history or first_run is None:
        return
    before = [c for d, c in history if d <= first_run]
    baseline = before[-1] if before else history[0][1]
    if pilot.get("criteria") != baseline and not pilot.get("criteria_changes"):
        raise UsageRefused(
            f"{path.name}: criteria changed after the first pilot run ({first_run}) without a "
            "criteria_changes entry (date, change, rationale); constitution IV"
        )


def evaluate(cat: Catalog, path: Path) -> dict[str, Any]:
    pilot = read_yaml(path)
    crit = pilot["criteria"]
    runs = _runs(cat, list(pilot.get("runs") or []))
    first_run = min((r["date"] for r in runs), default=None)
    check_frozen(path, pilot, first_run)
    run_ids = {f"run:{r['id']}" for r in runs}
    rows = []
    for lang in pilot["languages"]:
        accepted = [
            e
            for e in cat.entries.values()
            if e["provenance"]["added_by"] in run_ids
            and any(
                x["code"] == lang and x["origin"] not in ("machine_translated", "ai_generated")
                for x in e["languages"]
            )
            and (e.get("status") or {}).get("value") != "rejected"
        ]
        determined = sum(e["licence"]["id"] != "unknown" for e in accepted)
        training = sum(
            (e.get("usage") or {}).get("permitted_use") == "training_allowed" for e in accepted
        )
        share = determined / len(accepted) if accepted else 0.0
        rows.append(
            {
                "language": lang,
                "accepted": len(accepted),
                "determined_share": share,
                "training_allowed": training,
                "passed": share >= crit["min_determined_licence_share"]
                and training >= crit["min_training_allowed"],
            }
        )
    passing = sum(r["passed"] for r in rows)
    return {
        "runs": sorted(r["id"] for r in runs),
        "languages": rows,
        "passed": passing >= crit["min_languages_passing"],
    }
