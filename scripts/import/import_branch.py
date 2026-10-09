"""Rewrite one branch of mobility-security-ml to zoo paths, keeping its history (feature 005, R1).

    uv run python scripts/import/import_branch.py --source /tmp/msml \
        --branch claude/clever-goldberg-ygio83 --map scripts/import/path-map-goldberg.yaml \
        --out /tmp/import-goldberg

Steps: clone the branch fresh; list every path that ever existed; fail (exit 2) if a path is matched
by no rename, strip or drop entry; remove stripped and dropped paths from every commit; rename the
rest; write `<out>.merge-log.csv`. The result is merged into the zoo with
`git merge --allow-unrelated-histories`.
"""

from __future__ import annotations

import argparse
import csv
import fnmatch
import shutil
import subprocess
import sys
from pathlib import Path

import yaml


def git(*args: str, cwd: Path | None = None) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def all_paths(repo: Path) -> list[str]:
    out = git("log", "--all", "--format=", "--name-only", cwd=repo)
    return sorted({line for line in out.splitlines() if line.strip()})


def classify(path: str, mapping: dict) -> tuple[str, str, str]:
    """(status, new path or '', reason) for one historic path."""
    for kind in ("strip", "drop"):
        for entry in mapping.get(kind, []):
            if fnmatch.fnmatch(path, entry["glob"]):
                return kind, "", entry["reason"]
    for entry in mapping.get("renames", []):
        src, dst = entry["from"], entry["to"]
        if src.endswith("/") and path.startswith(src):
            return "renamed", dst + path[len(src) :], ""
        if path == src:
            return "renamed", dst, ""
    return "unmapped", "", ""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--branch", required=True)
    ap.add_argument("--map", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)
    mapping = yaml.safe_load(args.map.read_text(encoding="utf-8"))
    out: Path = args.out
    if out.exists():
        shutil.rmtree(out)
    subprocess.run(
        [
            "git",
            "clone",
            "--quiet",
            "--no-local",
            "--single-branch",
            "--branch",
            args.branch,
            args.source,
            str(out),
        ],
        check=True,
    )
    rows = [(p, *classify(p, mapping)) for p in all_paths(out)]
    unmapped = [p for p, status, _, _ in rows if status == "unmapped"]
    if unmapped:
        print("unmapped paths (add them to the map):", *unmapped, sep="\n  ", file=sys.stderr)
        return 2
    removed = [p for p, status, _, _ in rows if status in ("strip", "drop")]
    if removed:
        paths_file = out.parent / f"{out.name}.remove.txt"
        paths_file.write_text("".join(f"literal:{p}\n" for p in removed), encoding="utf-8")
        subprocess.run(
            [
                "git",
                "filter-repo",
                "--force",
                "--quiet",
                "--invert-paths",
                "--paths-from-file",
                str(paths_file),
            ],
            cwd=out,
            check=True,
        )
    renames = []
    for entry in mapping.get("renames", []):
        if entry["from"] != entry["to"]:
            renames += ["--path-rename", f"{entry['from']}:{entry['to']}"]
    if renames:
        subprocess.run(["git", "filter-repo", "--force", "--quiet", *renames], cwd=out, check=True)
    log = out.parent / f"{out.name}.merge-log.csv"
    with log.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["branch", "old_path", "new_path", "status", "reason"])
        for path, status, new, reason in rows:
            writer.writerow([args.branch, path, new, status, reason])
    left = set(all_paths(out))
    leaked = [p for p in removed if p in left]
    if leaked:
        print("removed paths still in history:", *leaked, sep="\n  ", file=sys.stderr)
        return 3
    print(
        f"imported {args.branch}: {len(rows) - len(removed)} paths renamed, {len(removed)} removed; "
        f"log {log}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
