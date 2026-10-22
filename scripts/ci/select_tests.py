"""Choose the CI jobs and test paths a change needs from the files it changes.

Every changed file is assigned to the first area whose pattern matches it (RULES, top to bottom).
The run then uses the union of the tests of its areas. Torch is installed only for the JTBD tests,
the firmware jobs (native simulator, QEMU) run only for areas with `edge`. A file no rule matches
runs everything. Pull requests and pushes to main are selected; the weekly schedule and manual
runs run everything (feature 017).

Three files are judged by their content at both revisions instead of by a rule (CONTENT_SENSITIVE):
- uv.lock: the firmware jobs run only if the firmware install set changes, that is the packages
  `uv sync` installs for them (base dependencies, FIRMWARE_EXTRAS, FIRMWARE_GROUPS, minus
  FIRMWARE_SKIP). tests/unit/test_ci_select.py checks these constants against the `uv sync` lines
  of the firmware jobs in ci.yml. Any lock change runs all Python tests.
- pyproject.toml: per key; an extra belongs to the area that uses it (EXTRA_AREAS), keys every job
  shares run everything (SHARED_MANIFEST_KEYS).
- .github/workflows/ci.yml: per job (WORKFLOW_JOB_AREAS).
Whenever a comparison is impossible (no revisions with --files, file added or removed, content
that does not parse), the file runs everything.

Patterns use fnmatch, where `*` also matches `/`. tests/unit/test_ci_select.py checks that every
tracked file is matched by a rule, so a new folder needs a decision here. The step summary names
the file and the rule or detail behind each area, first of all behind the firmware jobs.

Usage:
  select_tests.py --diff BASE HEAD   changed files and contents from git, write key=value lines
                                     for GITHUB_OUTPUT
  select_tests.py --all [--reason R] the full run, R names why in the summary
  select_tests.py --files A B ...    for given paths (local use, tests; content not compared)
  select_tests.py --guards           the repository-wide tests every pull request runs
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
import tomllib
from collections.abc import Callable
from dataclasses import dataclass

SRC = "src/mobility_model_zoo"


@dataclass(frozen=True)
class Area:
    tests: tuple[str, ...]
    torch: bool = False  # JTBD tests need torch; nothing else does
    edge: bool = False  # firmware jobs edge-sim and edge-qemu


AREAS: dict[str, Area] = {
    # The shared runtime and the datasets package (imported by every topic and by edge).
    "all": Area(("tests",), torch=True, edge=True),
    # Release and compliance code imports every topic; every Python test, no firmware jobs.
    "core": Area(("tests",), torch=True),
    "compliance-tests": Area(("tests/compliance",)),
    "release-tests": Area(("tests/release",)),
    "datasets-tests": Area(("tests/datasets",)),
    # The release gate imports the site checks (rules site-text and status-and-limits, features 008
    # and 013).
    "site": Area(
        ("tests/website", "tests/release/test_gate_site_text.py", "tests/release/test_rule18.py")
    ),
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
    # The resource index (feature 009) imports the compliance signal checker and PII scan.
    "catalog": Area(("tests/catalog", "tests/compliance/test_signals.py")),
    # Website imagery (feature 016): records under zoo/site/images, the generator and its tests.
    "images": Area(("tests/website", "tests/imagery")),
    # The selector and its fixtures: its tests are a guard every pull request runs (GUARDS).
    "ci-select": Area(()),
    # Covered by the checks every pull request runs (ruff, guards, zoo validate, compliance).
    "docs": Area(()),
}

RULES: list[tuple[str, tuple[str, ...]]] = [
    (
        "all",
        (
            ".python-version",
            f"{SRC}/datasets/*",
            "tests/conftest.py",
        ),
    ),
    # Before productdev, which matches tests/unit/*.
    ("ci-select", ("scripts/ci/*", "tests/unit/test_ci_select.py", "tests/fixtures/ci-select/*")),
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
    # The packaged release schemas must equal the contract copy of the feature that owns the format
    # (tests/release/test_schemas.py), so a change to that copy runs the release tests.
    ("release-tests", ("specs/*/contracts/release/*",)),
    # The same for the compliance register schemas (tests/compliance/test_register_schemas.py).
    ("compliance-tests", ("specs/*/contracts/compliance/*",)),
    ("datasets-tests", ("tests/datasets/*",)),
    (
        "catalog",
        (
            f"{SRC}/catalog/*",
            "tests/catalog/*",
            "tests/fixtures/catalog/*",
            "tests/fixtures/catalog-invalid/*",
            "tests/fixtures/catalog-http/*",
            ".claude/skills/catalog-discover/*",
        ),
    ),
    (
        "site",
        (
            f"{SRC}/site/*",
            "zoo/site.yaml",
            "tests/website/*",
            "docs/quickstart.md",  # rendered at /quickstart/ (feature 013)
        ),
    ),
    (
        "images",
        ("zoo/site/images/*", "scripts/imagery/*", "tests/website/test_images_*", "tests/imagery/*"),
    ),
    ("registry", ("zoo/*",)),
    (
        "edge",
        (
            f"{SRC}/edge/*",
            "firmware/*",
            "hil/*",
            "tests/edge/*",
            "tests/fixtures/edge-int8/*",
            "scripts/check_install_size.sh",
        ),
    ),
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
            "tests/fixtures/cluster/*",
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
            "drafts/*",  # design and post drafts, not package code
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

# Firmware install set (research R1): what `uv sync` installs in the jobs edge-sim and edge-qemu.
ROOT_PACKAGE = "mobility-model-zoo"
FIRMWARE_EXTRAS = ("edge", "edge-hw")
FIRMWARE_GROUPS = ("dev",)  # `uv sync` installs the default group
FIRMWARE_SKIP = ("torch",)  # --no-install-package

# pyproject.toml (research R2): keys every job shares run everything; extras and groups belong to
# the area that uses them; anything else runs the Python tests.
SHARED_MANIFEST_KEYS = (
    "project.dependencies",
    "project.requires-python",
    "project.scripts",
    "dependency-groups.dev",
    "build-system",
    "tool.uv",
    "tool.hatch",
    "tool.pytest",
)
EXTRA_AREAS = {
    "edge": "edge",
    "edge-hw": "edge",
    "catalog": "catalog",
    "jtbd": "productdev",
    "text": "productdev",
    "cluster": "productdev",
    "labeling-api": "productdev",
    "images": "images",
    "release": "core",
    "edge-train": "core",
}
GROUP_AREAS = {"site-check": "images"}  # browser checks of the website
MANIFEST_KEY_AREAS = {"tool.ruff": "docs"}  # checked by ruff in the checks job

# .github/workflows/ci.yml (research R3): per job; an added, removed or unknown job runs everything.
WORKFLOW_JOB_AREAS = {
    "<header>": "all",
    "changes": "all",
    "checks": "core",
    "test": "core",
    "edge-sim": "edge",
    "edge-qemu": "edge",
}

FULL_RUN = "full run"
MAX_REASONS = 5

Reader = Callable[[str, str], "str | None"]  # (revision, path) -> content, None if absent


@dataclass(frozen=True)
class Finding:
    """Why a changed file selects an area: the matching pattern or the deciding detail."""

    area: str
    file: str
    reason: str


def rule_of(path: str) -> tuple[str, str] | None:
    """The area and pattern of the first rule that matches, None if no rule does."""
    for area, patterns in RULES:
        for p in patterns:
            if fnmatch.fnmatchcase(path, p):
                return area, p
    return None


def area_of(path: str) -> str | None:
    """The area of the first rule that matches, None if no rule does."""
    rule = rule_of(path)
    return rule[0] if rule else None


# --- uv.lock -------------------------------------------------------------------------------------


def firmware_install_set(lock_text: str) -> set[tuple[str, str, str]]:
    """(name, version, source) of every package the firmware jobs install.

    The closure over the lock's dependency graph from the project's base dependencies, its
    FIRMWARE_EXTRAS and FIRMWARE_GROUPS, following the extras a dependency requests and skipping
    FIRMWARE_SKIP. Markers are ignored, so the set may be larger than an install (fail safe).
    """
    packages = tomllib.loads(lock_text)["package"]
    by_name: dict[str, list[dict]] = {}
    for p in packages:
        by_name.setdefault(p["name"], []).append(p)
    roots = [p for p in by_name.get(ROOT_PACKAGE, []) if "editable" in p["source"]]
    if len(roots) != 1:
        raise ValueError(f"no single editable package {ROOT_PACKAGE} in the lock")
    root = roots[0]
    todo = list(root.get("dependencies", []))
    for extra in FIRMWARE_EXTRAS:
        todo += root.get("optional-dependencies", {}).get(extra, [])
    for group in FIRMWARE_GROUPS:
        todo += root.get("dev-dependencies", {}).get(group, [])
    seen: dict[tuple[str, str, str], set[str]] = {}  # member -> extras already followed
    while todo:
        dep = todo.pop()
        if dep["name"] in FIRMWARE_SKIP:
            continue
        for p in by_name.get(dep["name"], []):
            key = (p["name"], p.get("version", ""), json.dumps(p.get("source", {}), sort_keys=True))
            if key not in seen:
                seen[key] = set()
                todo += p.get("dependencies", [])
            for extra in set(dep.get("extra", [])) - seen[key]:
                seen[key].add(extra)
                todo += p.get("optional-dependencies", {}).get(extra, [])
    return set(seen)


def describe_set_change(old: set[tuple[str, str, str]], new: set[tuple[str, str, str]]) -> str:
    """`numpy 2.1.0 → 2.1.3`, `+name 1.0`, `-name 1.0`; at most MAX_REASONS packages."""
    names = sorted({m[0] for m in old ^ new})
    parts = []
    for n in names:
        a = sorted(v for name, v, _ in old if name == n)
        b = sorted(v for name, v, _ in new if name == n)
        if a and b and a != b:
            parts.append(f"{n} {', '.join(a)} → {', '.join(b)}")
        elif a and b:
            parts.append(f"{n} {', '.join(a)} (source changed)")
        else:
            parts.append(f"+{n} {', '.join(b)}" if b else f"-{n} {', '.join(a)}")
    text = "; ".join(parts[:MAX_REASONS])
    return text + (f" and {len(parts) - MAX_REASONS} more" if len(parts) > MAX_REASONS else "")


def classify_lock(path: str, old: str, new: str) -> list[Finding]:
    found = [Finding("core", path, "lock changed")]
    a, b = firmware_install_set(old), firmware_install_set(new)
    if a != b:
        found.append(Finding("edge", path, describe_set_change(a, b) + " (firmware install set)"))
    return found


# --- pyproject.toml ------------------------------------------------------------------------------


def manifest_keys(text: str) -> dict[str, object]:
    """Key path -> value at the depth the selection decides on."""
    data = tomllib.loads(text)
    keys: dict[str, object] = {}
    for top, value in data.items():
        if top == "project" and isinstance(value, dict):
            for k, v in value.items():
                if k == "optional-dependencies":
                    keys |= {f"project.optional-dependencies.{e}": d for e, d in v.items()}
                else:
                    keys[f"project.{k}"] = v
        elif top in ("tool", "dependency-groups") and isinstance(value, dict):
            keys |= {f"{top}.{k}": v for k, v in value.items()}
        else:
            keys[top] = value
    return keys


def manifest_area(key: str) -> str:
    if key in SHARED_MANIFEST_KEYS:
        return "all"
    if key.startswith("project.optional-dependencies."):
        return EXTRA_AREAS.get(key.split(".", 2)[2], "core")
    if key.startswith("dependency-groups."):
        return GROUP_AREAS.get(key.split(".", 1)[1], "core")
    return MANIFEST_KEY_AREAS.get(key, "core")


def classify_manifest(path: str, old: str, new: str) -> list[Finding]:
    a, b = manifest_keys(old), manifest_keys(new)
    changed = sorted(k for k in a.keys() | b.keys() if a.get(k) != b.get(k))
    if not changed:  # comments or formatting only
        return [Finding("docs", path, "no key changed")]
    return [Finding(manifest_area(k), path, f"{k} changed") for k in changed]


# --- .github/workflows/ci.yml --------------------------------------------------------------------

JOB_LINE = re.compile(r"^  ([A-Za-z0-9_-]+):\s*$")
LOOSE_LINE = re.compile(r"^(\s{0,2}#.*)?\s*$")  # blank line or comment at job level


def workflow_blocks(text: str) -> dict[str, str]:
    """`<header>` (everything before `jobs:`) and the text of each job, keyed by job name.

    Blank lines and comments between jobs belong to the job that follows them.
    """
    lines = text.splitlines(keepends=True)
    try:
        start = next(i for i, line in enumerate(lines) if line.rstrip() == "jobs:")
    except StopIteration:
        raise ValueError("no jobs: key") from None
    blocks = {"<header>": "".join(lines[:start])}
    job, pending = None, ""
    for line in lines[start + 1 :]:
        m = JOB_LINE.match(line)
        if m:
            job = m.group(1)
            blocks[job], pending = pending + line, ""
        elif LOOSE_LINE.match(line):
            pending += line
        elif job is None:
            raise ValueError(f"content before the first job: {line.strip()}")
        else:
            blocks[job] += pending + line
            pending = ""
    if job is None:
        raise ValueError("no job under jobs:")
    blocks[job] += pending
    return blocks


def classify_workflow(path: str, old: str, new: str) -> list[Finding]:
    a, b = workflow_blocks(old), workflow_blocks(new)
    found = []
    for name in sorted(a.keys() | b.keys()):
        if a.get(name) == b.get(name):
            continue
        what = "header" if name == "<header>" else f"job {name}"
        if name not in a or name not in b:
            found.append(Finding("all", path, f"{what} {'added' if name in b else 'removed'}"))
        else:
            found.append(Finding(WORKFLOW_JOB_AREAS.get(name, "all"), path, f"{what} changed"))
    return found or [Finding("docs", path, "no job changed")]


Classifier = Callable[[str, str, str], list[Finding]]
CONTENT_SENSITIVE: dict[str, Classifier] = {
    "uv.lock": classify_lock,
    "pyproject.toml": classify_manifest,
    ".github/workflows/ci.yml": classify_workflow,
}


# --- selection -----------------------------------------------------------------------------------


def classify(
    path: str, base: str | None, head: str | None, read: Reader | None
) -> list[Finding]:
    if path in CONTENT_SENSITIVE:
        if read is None or base is None or head is None:
            return [Finding(FALLBACK, path, "cannot compare: no revisions")]
        old, new = read(base, path), read(head, path)  # a git error propagates (exit non-zero)
        if old is None or new is None:
            return [Finding(FALLBACK, path, f"cannot compare: file {'added' if new else 'removed'}")]
        try:
            return CONTENT_SENSITIVE[path](path, old, new)
        except (ValueError, KeyError, TypeError, AttributeError, tomllib.TOMLDecodeError) as e:
            return [Finding(FALLBACK, path, f"cannot compare: {type(e).__name__}: {e}")]
    rule = rule_of(path)
    if rule is None:
        return [Finding(FALLBACK, path, "no rule matches")]
    return [Finding(rule[0], path, rule[1])]


@dataclass(frozen=True)
class Selection:
    tests: tuple[str, ...]
    torch: bool
    edge: bool
    areas: dict[str, list[Finding]]  # area -> findings, for the job summary

    @property
    def firmware_findings(self) -> list[Finding]:
        return [f for a, fs in sorted(self.areas.items()) if AREAS[a].edge for f in fs]


def select(
    files: list[str],
    base: str | None = None,
    head: str | None = None,
    read: Reader | None = None,
) -> Selection:
    areas: dict[str, list[Finding]] = {}
    for f in files:
        for finding in classify(f, base, head, read):
            areas.setdefault(finding.area, []).append(finding)
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


def full_run(reason: str) -> Selection:
    a = AREAS[FALLBACK]
    return Selection(a.tests, a.torch, a.edge, {FALLBACK: [Finding(FALLBACK, FULL_RUN, reason)]})


def changed_files(base: str, head: str) -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--name-only", "--no-renames", base, head],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [line for line in out.splitlines() if line]


def git_reader(rev: str, path: str) -> str | None:
    """The file at a revision, None if it does not exist there; other git errors raise."""
    shown = subprocess.run(["git", "show", f"{rev}:{path}"], capture_output=True, text=True)
    if shown.returncode == 0:
        return shown.stdout
    exists = subprocess.run(["git", "cat-file", "-e", f"{rev}:{path}"], capture_output=True)
    commit = subprocess.run(["git", "cat-file", "-e", f"{rev}^{{commit}}"], capture_output=True)
    if commit.returncode == 0 and exists.returncode != 0:
        return None
    raise RuntimeError(f"git show {rev}:{path} failed: {shown.stderr.strip()}")


def describe(f: Finding) -> str:
    return f"{FULL_RUN} ({f.reason})" if f.file == FULL_RUN else f"{f.file}: {f.reason}"


def firmware_line(sel: Selection) -> str:
    if not sel.edge:
        return "Firmware jobs: not needed"
    reasons = [describe(f) for f in sel.firmware_findings]
    more = len(reasons) - MAX_REASONS
    return "Firmware jobs: run — " + "; ".join(reasons[:MAX_REASONS]) + (
        f" and {more} more" if more > 0 else ""
    )


def report(sel: Selection) -> None:
    print(f"tests={' '.join(sel.tests)}")
    print(f"torch={str(sel.torch).lower()}")
    print(f"edge={str(sel.edge).lower()}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    lines = ["### Test selection", "", firmware_line(sel), ""]
    for a, fs in sorted(sel.areas.items()):
        n = len({f.file for f in fs})
        lines.append(f"- **{a}**: {n} file(s), e.g. `{fs[0].file}` ({fs[0].reason})")
    lines += ["", f"Tests: `{' '.join(sel.tests) or 'none (checks only)'}`; torch: {sel.torch}"]
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
    ap.add_argument("--reason", default="--all", help="why --all runs, shown in the summary")
    args = ap.parse_args(argv)
    if args.guards:
        print(" ".join(GUARDS))
        return 0
    if args.all:
        report(full_run(args.reason))
        return 0
    if args.diff:
        base, head = args.diff
        report(select(changed_files(base, head), base, head, git_reader))
    else:
        report(select(args.files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
