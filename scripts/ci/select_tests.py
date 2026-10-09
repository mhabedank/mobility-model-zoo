"""Choose the CI jobs and test paths a pull request needs from the files it changes.

Every changed file is assigned to the first area whose pattern matches it (RULES, top to bottom).
The pull request then runs the union of the tests of its areas. Torch is installed only for the
JTBD tests, the firmware jobs (native simulator, QEMU) run only for the edge area. A file no rule
matches runs everything, and pushes to main always run everything.

Patterns use fnmatch, where `*` also matches `/`. tests/unit/test_ci_select.py checks that every
tracked file is matched by a rule, so a new folder needs a decision here.

Usage:
  select_tests.py --diff BASE HEAD   changed files from git, write key=value lines for GITHUB_OUTPUT
  select_tests.py --all              the full run
  select_tests.py --files A B ...    for given paths (local use, tests)
  select_tests.py --guards           the repository-wide tests every pull request runs
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import subprocess
import sys
from dataclasses import dataclass

SRC = "src/mobility_model_zoo"


@dataclass(frozen=True)
class Area:
    tests: tuple[str, ...]
    torch: bool = False  # JTBD tests need torch; nothing else does
    edge: bool = False  # firmware jobs edge-sim and edge-qemu


AREAS: dict[str, Area] = {
    # Dependencies, the CI itself and the datasets package (imported by every topic and by edge).
    "all": Area(("tests",), torch=True, edge=True),
    # Release and compliance code imports every topic; every Python test, no firmware jobs.
    "core": Area(("tests",), torch=True),
    "compliance-tests": Area(("tests/compliance",)),
    "release-tests": Area(("tests/release",)),
    "datasets-tests": Area(("tests/datasets",)),
    # The release gate imports the site checks (rule site-text).
    "site": Area(("tests/website", "tests/release/test_gate_site_text.py")),
    # Model records, formats and topics feed the release tool and the website.
    "registry": Area(("tests/release", "tests/website")),
    # Compliance imports the JTBD redaction patterns and settings.
    "productdev": Area(("tests/unit", "tests/integration", "tests/compliance"), torch=True),
    "security": Area(("tests/security", "tests/unit/test_task_configs.py")),
    "condmon": Area(("tests/condition_monitoring", "tests/unit/test_task_configs.py")),
    # Security, condition monitoring and the release gate (MCU rules) import edge.
    "edge": Area(
        (
            "tests/edge",
            "tests/security",
            "tests/condition_monitoring",
            "tests/release",
            "tests/unit/test_task_configs.py",
        ),
        edge=True,
    ),
    # Covered by the checks every pull request runs (ruff, guards, zoo validate, compliance).
    "docs": Area(()),
}

RULES: list[tuple[str, tuple[str, ...]]] = [
    (
        "all",
        (
            "pyproject.toml",
            "uv.lock",
            ".python-version",
            ".github/workflows/ci.yml",
            "scripts/ci/*",
            f"{SRC}/datasets/*",
            "tests/conftest.py",
        ),
    ),
    (
        "core",
        (
            f"{SRC}/__init__.py",
            f"{SRC}/release/*",
            f"{SRC}/compliance/*",
            f"{SRC}/sandbox/*",
            "compliance/*",
            "topics/*/compliance/*",
            "tests/compliance_helpers.py",
            "tests/fixtures/compliance/*",
        ),
    ),
    ("compliance-tests", ("tests/compliance/*",)),
    ("release-tests", ("tests/release/*",)),
    ("datasets-tests", ("tests/datasets/*",)),
    ("site", (f"{SRC}/site/*", "zoo/site.yaml", "tests/website/*", "scripts/site_og_image.py")),
    ("registry", ("zoo/*",)),
    ("edge", (f"{SRC}/edge/*", "firmware/*", "hil/*", "tests/edge/*", "tests/fixtures/edge-int8/*")),
    # Research notes, reports and task documents of a topic are prose.
    ("docs", ("topics/*.md",)),
    ("security", (f"{SRC}/security/*", "configs/security/*", "topics/security/*", "tests/security/*")),
    (
        "condmon",
        (
            f"{SRC}/condition_monitoring/*",
            "configs/condition-monitoring/*",
            "topics/condition-monitoring/*",
            "tests/condition_monitoring/*",
        ),
    ),
    (
        "productdev",
        (
            f"{SRC}/productdev/*",
            "configs/productdev/*",
            "topics/productdev/*",
            "tests/unit/*",
            "tests/integration/*",
            "tests/fixtures/mini-corpus/*",
            "tests/fixtures/rename-hashes.json",
            "tests/helpers.py",
            "tests/span_helpers.py",
        ),
    ),
    # Legal and licence files are checked by `zoo compliance check`; their tests are fast.
    (
        "compliance-tests",
        (
            "LICENSE",
            "LICENSES/*",
            "NOTICE",
            "REUSE.toml",
            "THIRD_PARTY_NOTICES.md",
            "PRIVACY.md",
            "COPYRIGHT_POLICY.md",
            "SECURITY.md",
            "docs/compliance/*",
        ),
    ),
    (
        "docs",
        (
            "*.md",
            "docs/*",
            "specs/*",
            ".specify/*",
            ".claude/*",
            ".github/*",  # the other workflows filter their own paths
            "scripts/import/*",
            "scripts/hf_org_avatar.py",
            "scripts/setup-cloud.sh",
            ".gitignore",
            ".gitattributes",
            ".gitleaksignore",  # the secret scan runs on every pull request
            ".env.example",
        ),
    ),
]

# Repository-wide tests every pull request runs (with ruff, zoo validate and the compliance check).
GUARDS = (
    "tests/unit/test_ci_select.py",
    "tests/unit/test_check_merge_log.py",
    "tests/unit/test_constitution_version.py",
    "tests/unit/test_docs_english.py",
    "tests/unit/test_import_branch.py",
    "tests/unit/test_no_pilot_commands.py",
    "tests/unit/test_no_spike_imports.py",
    "tests/unit/test_workflow_secrets.py",
)

FALLBACK = "all"


def area_of(path: str) -> str | None:
    """The area of the first rule that matches, None if no rule does."""
    for area, patterns in RULES:
        if any(fnmatch.fnmatchcase(path, p) for p in patterns):
            return area
    return None


@dataclass(frozen=True)
class Selection:
    tests: tuple[str, ...]
    torch: bool
    edge: bool
    areas: dict[str, list[str]]  # area -> changed files, for the job summary


def select(files: list[str]) -> Selection:
    areas: dict[str, list[str]] = {}
    for f in files:
        areas.setdefault(area_of(f) or FALLBACK, []).append(f)
    chosen = [AREAS[a] for a in areas]
    paths = sorted({t for a in chosen for t in a.tests})
    # drop a path that lies inside another selected path
    paths = [p for p in paths if not any(p != q and p.startswith(q + "/") for q in paths)]
    return Selection(
        tests=tuple(paths),
        torch=any(a.torch for a in chosen),
        edge=any(a.edge for a in chosen),
        areas=areas,
    )


def changed_files(base: str, head: str) -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--name-only", "--no-renames", base, head],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [line for line in out.splitlines() if line]


def report(sel: Selection) -> None:
    print(f"tests={' '.join(sel.tests)}")
    print(f"torch={str(sel.torch).lower()}")
    print(f"edge={str(sel.edge).lower()}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    lines = ["### Test selection", ""]
    lines += [f"- **{a}**: {len(fs)} file(s), e.g. `{fs[0]}`" for a, fs in sorted(sel.areas.items())]
    lines += [
        "",
        f"Tests: `{' '.join(sel.tests) or 'none (checks only)'}`; torch: {sel.torch}; "
        f"firmware jobs: {sel.edge}",
    ]
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    else:
        print("\n".join(lines), file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--diff", nargs=2, metavar=("BASE", "HEAD"))
    g.add_argument("--all", action="store_true")
    g.add_argument("--files", nargs="*")
    g.add_argument("--guards", action="store_true")
    args = ap.parse_args(argv)
    if args.guards:
        print(" ".join(GUARDS))
        return 0
    if args.all:
        report(Selection(AREAS["all"].tests, True, True, {"all": ["(full run)"]}))
        return 0
    files = changed_files(*args.diff) if args.diff else args.files
    report(select(files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
