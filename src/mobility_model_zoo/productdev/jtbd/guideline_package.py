"""Owner-approved guideline packages (constitution 3.2.0, Principle XI; scout-large roadmap phase 2).

A package is assembled by code from an owner-approved brief (`brief.yaml`) and its worked examples
(`examples.yaml`) with a fixed template. Nothing is reworded: the template prints the brief's own
text under its machine keys and leaves out what the brief's `assembly.rule` keeps out of print (the
owner's German originals, review-only keys and keys that steer code rather than labelers).

    <package>/guideline.md          the labeler-facing guideline
    <package>/examples/NN-<id>.yaml one worked example per file, review keys stripped
    <package>/package.json          sha256 of every package file and of the two sources
    <package>/approval.json         written by `approve`: who, when, and the approved hashes

A package that contains Claude drafts may only be used by a labeling run, teacher runs included,
when `approval.json` exists, its hashes match the files, and the files still match their sources.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from mobility_model_zoo.productdev.jtbd.errors import ClaudeGateError, FrozenHashMismatch, UsageError
from mobility_model_zoo.productdev.jtbd.freeze import sha256_bytes

TEMPLATE_VERSION = 1
MANIFEST = "package.json"
APPROVAL = "approval.json"
GUIDELINE = "guideline.md"

# Keys of the brief that steer code, sampling or the pilot, not the labeler.
NOT_PRINTED_TOP = {
    "teacher_task", "reader", "language", "examples", "assembly", "link_connectives",
    "pilot_thresholds", "drop_order",
}
# Sub-keys that are review-only or the owner's untranslated originals (assembly.rule).
NOT_PRINTED_SUB = {"drafted_by", "approval", "previous_approval", "owner", "cases_owner"}
EXAMPLE_REVIEW_KEYS = {"shows", "language"}


def _printable(key: str) -> bool:
    return key not in NOT_PRINTED_SUB and not key.endswith("_choice")


def _has_claude_draft(node: Any) -> bool:
    if isinstance(node, dict):
        return node.get("drafted_by") == "claude" or any(_has_claude_draft(v) for v in node.values())
    if isinstance(node, list):
        return any(_has_claude_draft(v) for v in node)
    return False


def _render_value(value: Any) -> list[str]:
    if isinstance(value, list):
        if all(not isinstance(v, (dict, list)) for v in value):
            return [", ".join(f"`{v}`" for v in value)]
        lines: list[str] = []
        for item in value:
            if isinstance(item, dict):
                lines.append("- " + "; ".join(f"{k}: {v}" for k, v in item.items() if v is not None))
            else:
                lines.append(f"- {item}")
        return lines
    if isinstance(value, dict):
        lines = []
        for key, sub in value.items():
            if not _printable(key):
                continue
            rendered = _render_value(sub)
            lines.append(f"- **{key}**: {rendered[0]}" if len(rendered) == 1 else f"- **{key}**:")
            if len(rendered) > 1:
                lines += [f"  {line}" for line in rendered]
        return lines
    return [str(value).strip()]


def render_guideline(brief: dict[str, Any]) -> str:
    lines = ["# Labeling guideline", ""]
    for key, value in brief.items():
        if key in NOT_PRINTED_TOP or not _printable(key):
            continue
        lines += [f"## {key}", ""]
        if isinstance(value, dict):
            for sub, text in value.items():
                if not _printable(sub):
                    continue
                rendered = _render_value(text)
                if len(rendered) == 1:
                    lines += [f"**{sub}**: {rendered[0]}", ""]
                else:
                    lines += [f"**{sub}**:", "", *rendered, ""]
        else:
            lines += [*_render_value(value), ""]
    return "\n".join(lines).rstrip() + "\n"


def _example_doc(example: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in example.items() if k not in EXAMPLE_REVIEW_KEYS}


def _dump(doc: Any) -> bytes:
    return yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=100).encode("utf-8")


def _read_yaml(path: Path) -> Any:
    if not path.exists():
        raise UsageError(f"not found: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def assemble(brief_path: Path, examples_path: Path, out_dir: Path) -> dict[str, Any]:
    """Write the package; deterministic for the same sources. Removes an approval of older files."""
    brief = _read_yaml(brief_path) or {}
    examples = (_read_yaml(examples_path) or {}).get("examples") or []
    if not brief or not examples:
        raise UsageError("brief and examples must both be non-empty")
    files: dict[str, bytes] = {GUIDELINE: render_guideline(brief).encode("utf-8")}
    for n, example in enumerate(examples, start=1):
        files[f"examples/{n:02d}-{example['id']}.yaml"] = _dump(_example_doc(example))
    out_dir.mkdir(parents=True, exist_ok=True)
    old_examples = out_dir / "examples"
    if old_examples.exists():
        for stale in old_examples.glob("*.yaml"):
            stale.unlink()
    for rel, data in files.items():
        target = out_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    manifest = {
        "template_version": TEMPLATE_VERSION,
        "contains_claude_drafts": _has_claude_draft(brief) or _has_claude_draft(examples),
        "sources": {
            "brief": {"path": _rel(brief_path, out_dir),
                      "sha256": sha256_bytes(brief_path.read_bytes())},
            "examples": {"path": _rel(examples_path, out_dir),
                         "sha256": sha256_bytes(examples_path.read_bytes())},
        },
        "files": {rel: sha256_bytes(data) for rel, data in files.items()},
    }
    (out_dir / MANIFEST).write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                                    encoding="utf-8")
    approval = out_dir / APPROVAL
    if approval.exists():
        recorded = json.loads(approval.read_text(encoding="utf-8")).get("files")
        if recorded != manifest["files"]:
            approval.unlink()
    return manifest


def _rel(path: Path, package: Path) -> str:
    return os.path.relpath(path.resolve(), package.resolve())


def _manifest(package: Path) -> dict[str, Any]:
    path = package / MANIFEST
    if not path.exists():
        raise UsageError(f"{path} not found: assemble the package first")
    return json.loads(path.read_text(encoding="utf-8"))


def _current_hashes(package: Path, manifest: dict[str, Any]) -> dict[str, str]:
    hashes = {}
    for rel in manifest["files"]:
        path = package / rel
        if not path.exists():
            raise FrozenHashMismatch(f"package file missing: {path}")
        hashes[rel] = sha256_bytes(path.read_bytes())
    present = {f"examples/{p.name}" for p in (package / "examples").glob("*.yaml")}
    extra = present - set(manifest["files"])
    if extra:
        raise FrozenHashMismatch(f"files not in the package manifest: {sorted(extra)}")
    return hashes


def approve(package: Path, approved_by: str) -> dict[str, Any]:
    """Record the owner's approval of the package as it is now (constitution XI, 3.1.0/3.2.0)."""
    if not approved_by.strip():
        raise UsageError("--by must name the person who approves")
    manifest = _manifest(package)
    if _current_hashes(package, manifest) != manifest["files"]:
        raise FrozenHashMismatch("package files differ from package.json: assemble again first")
    _check_sources(package, manifest)
    record = {
        "approved_by": approved_by.strip(),
        "approved_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "template_version": manifest["template_version"],
        "sources": manifest["sources"],
        "files": manifest["files"],
        "manifest_sha256": sha256_bytes((package / MANIFEST).read_bytes()),
    }
    (package / APPROVAL).write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                                    encoding="utf-8")
    return record


def _check_sources(package: Path, manifest: dict[str, Any]) -> None:
    for name, source in manifest["sources"].items():
        path = (package / source["path"]).resolve()
        if not path.exists():
            raise FrozenHashMismatch(f"package source {name} not found: {path}")
        if sha256_bytes(path.read_bytes()) != source["sha256"]:
            raise FrozenHashMismatch(
                f"package source {name} changed after assembly ({path}): assemble and approve again")


def check(package: Path) -> dict[str, Any]:
    """Raise unless the package may be used by a labeling run; return a short status."""
    manifest = _manifest(package)
    hashes = _current_hashes(package, manifest)
    if hashes != manifest["files"]:
        changed = sorted(rel for rel in hashes if hashes[rel] != manifest["files"].get(rel))
        raise FrozenHashMismatch(f"package files changed after assembly: {changed}")
    _check_sources(package, manifest)
    status = {"package": str(package), "contains_claude_drafts": manifest["contains_claude_drafts"],
              "approved": False}
    approval_path = package / APPROVAL
    if approval_path.exists():
        approval = json.loads(approval_path.read_text(encoding="utf-8"))
        if approval.get("files") != hashes:
            raise FrozenHashMismatch("package changed after its approval: approve again")
        status |= {"approved": True, "approved_by": approval["approved_by"],
                   "approved_at": approval["approved_at"]}
    elif manifest["contains_claude_drafts"]:
        raise ClaudeGateError(
            f"guideline package {package} contains Claude drafts and has no owner approval "
            "(constitution XI): run `jtbd guide approve` after the owner's review")
    return status


def require_for_run(guideline_path: Path, examples_path: Path) -> None:
    """Called by every labeling run. A guideline inside a package must pass `check`.

    A guideline file outside a package (the frozen guidelines of 0.1.x) is not affected.
    """
    package = guideline_path.parent
    if not (package / MANIFEST).exists():
        return
    if examples_path.resolve() != (package / "examples").resolve():
        raise UsageError(f"examples path {examples_path} is not the package's examples directory")
    check(package)
