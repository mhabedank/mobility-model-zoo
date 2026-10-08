"""Check that the merge log accounts for every path of both source branches (SC-001).

    uv run python scripts/import/check_merge_log.py [--log topics/security/research/merge-log.md]
        [--source /tmp/msml]

Every historic path of the two branches must appear in the log with a new path or a reason.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

BRANCHES = ("claude/clever-goldberg-ygio83", "claude/cool-volta-rqsgdx")


def parse_log(text: str) -> dict[tuple[str, str], tuple[str, str]]:
    rows = {}
    for line in text.splitlines():
        cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
        if len(cells) != 4 or cells[0] in ("Branch", "") or set(cells[0]) <= {"-", ":"}:
            continue
        branch, old, new, reason = cells
        rows[(branch, old)] = (new, reason)
    return rows


def missing(rows: dict, branch_paths: dict[str, list[str]]) -> list[str]:
    out = []
    for branch, paths in branch_paths.items():
        for path in paths:
            new, reason = rows.get((branch, path), ("", ""))
            if not (new and new != "dropped") and not reason:
                out.append(f"{branch}: {path}")
    return out


def branch_paths(source: str) -> dict[str, list[str]]:
    result = {}
    for branch in BRANCHES:
        out = subprocess.run(
            ["git", "-C", source, "log", f"origin/{branch}", "--format=", "--name-only"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        result[branch] = sorted({p for p in out.splitlines() if p.strip()})
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", type=Path, default=Path("topics/security/research/merge-log.md"))
    ap.add_argument("--source", default="/tmp/msml")
    args = ap.parse_args(argv)
    gaps = missing(parse_log(args.log.read_text(encoding="utf-8")), branch_paths(args.source))
    if gaps:
        print("paths without a new location or reason:", *gaps, sep="\n  ", file=sys.stderr)
        return 1
    print("merge log complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
