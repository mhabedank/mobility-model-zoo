"""Release stages of the compliance harness (gate rule 16): model, publication, card, licence,
repository and sign-off (contracts/checks.md, C-D*, C-U*, C-C*, C-L*, C-G*, C-S1).
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import yaml

from mobility_model_zoo.compliance.findings import Finding, is_unknown
from mobility_model_zoo.compliance.scan import CorpusIndex, overlap_spans, pii

VERBATIM_MAX_WORDS = 30  # decision D7
GPAI_FLOP = 1e23
REQUIRED_FILES = ("LICENSE", "NOTICE", "SECURITY.md", "PRIVACY.md", "COPYRIGHT_POLICY.md")
FUNDING = re.compile(
    r"(?i)(github\.com/sponsors|patreon\.com|ko-fi\.com|buymeacoffee|opencollective\.com|"
    r"liberapay|\bhire me\b|consulting services|paid support|\bpricing\b)"
)
BRAND = re.compile(r"(?i)miskatonic")
TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".py",
    ".j2",
    ".cfg",
    ".ini",
    ".sh",
    ".csv",
    ".html",
    "",
}
# Files that may name the website: the register itself and the specs that record the decisions.
BRAND_ALLOWED_PREFIXES = ("compliance/", "specs/", ".specify/")
# Test data is synthetic by policy and deliberately contains identifiers (redaction tests); code is
# not text. Both are excluded from the repository-wide personal data scan (C-G5).
PII_SKIP_PREFIXES = ("tests/",)
PII_SUFFIXES = {".md", ".txt", ".yaml", ".yml", ".json", ".toml", ".csv", ".html"}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def tracked_text_files(root: Path) -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(root), "ls-files"], capture_output=True, text=True, check=True
    )
    return [
        p for p in out.stdout.splitlines() if Path(p).suffix in TEXT_SUFFIXES and (root / p).is_file()
    ]


def contact_allowlist(controller: dict[str, Any]) -> list[str]:
    return [
        controller.get(k, "")
        for k in ("privacy_contact", "general_contact", "imprint_url", "website_privacy_url")
        if controller.get(k)
    ]


# ---- model (C-D1, C-D2) -----------------------------------------------------------------------


def stage_model(ctx) -> list[Finding]:
    rc, rel = _release(ctx)
    if rc is None:
        return [Finding("C-S1", "model", rel, "-", "release compliance record missing")]
    findings = []
    mem = (rc.get("scans") or {}).get("memorisation")
    gpai = rc.get("gpai") or {}
    if not mem:
        findings.append(Finding("C-D1", "model", rel, "scans.memorisation", "missing"))
    elif mem.get("status") == "not_applicable" and gpai.get("generative"):
        findings.append(
            Finding(
                "C-D1",
                "model",
                rel,
                "scans.memorisation",
                "a generative model needs a memorisation probe (D8)",
            )
        )
    elif mem.get("status") == "failed":
        findings.append(Finding("C-D1", "model", rel, "scans.memorisation", "probe failed (D8)"))
    flop = gpai.get("training_compute_flop")
    if flop is None or (is_unknown(flop) and not ctx.reg.waiver_ok("C-D2", rel)):
        findings.append(Finding("C-D2", "model", rel, "gpai.training_compute_flop", "estimate missing"))
    elif isinstance(flop, (int, float)) and flop >= GPAI_FLOP and not gpai.get("is_gpai"):
        findings.append(
            Finding("C-D2", "model", rel, "gpai", "compute above 10^23 FLOP needs a GPAI review")
        )
    if (
        gpai.get("generative")
        and not gpai.get("is_gpai")
        and "GPAI review" not in gpai.get("rationale", "")
    ):
        findings.append(Finding("C-D2", "model", rel, "gpai", "generative model without a GPAI review"))
    return findings


def _release(ctx) -> tuple[dict[str, Any] | None, str]:
    rel = f"zoo/models/{ctx.model}/releases/{ctx.version}.compliance.yaml"
    return ctx.reg.release(ctx.model, ctx.version), rel


# ---- publication (C-U1 … C-U4) ----------------------------------------------------------------


def publication_files(ctx) -> dict[str, str]:
    """{logical path: text} of everything that is published with this release."""
    root, model, version = ctx.root, ctx.model, ctx.version
    files: dict[str, str] = {}
    if ctx.extra.get("card") is not None:
        files["README.md (model card)"] = ctx.extra["card"]
    base = root / "zoo" / "models" / model
    for path in sorted((base / "examples").glob("*")):
        if path.is_file() and path.name != "SOURCES.yaml":
            files[path.relative_to(root).as_posix()] = path.read_text(encoding="utf-8")
    for path in sorted((base / "results" / version).glob("*.json")):
        files[path.relative_to(root).as_posix()] = path.read_text(encoding="utf-8")
    for suffix in ("ai-act.md", "training-data-summary.md"):
        path = base / "releases" / f"{version}.{suffix}"
        if path.exists():
            files[path.relative_to(root).as_posix()] = path.read_text(encoding="utf-8")
    return files


def scan_publication(ctx, full: CorpusIndex, restricted: CorpusIndex) -> dict[str, Any]:
    allow = contact_allowlist(ctx.reg.controller())
    out = []
    for name, text in publication_files(ctx).items():
        spans = overlap_spans(text, restricted, VERBATIM_MAX_WORDS)
        all_spans = overlap_spans(text, full, VERBATIM_MAX_WORDS)
        out.append(
            {
                "path": name,
                "sha256": sha256_text(text),
                "overlap_max_words": max((e - s for s, e in spans), default=0),
                "allowed_quote_words": max((e - s for s, e in all_spans), default=0),
                "pii_hits": len(pii(text, allow)),
            }
        )
    return {
        "model": ctx.model,
        "version": ctx.version,
        "threshold_words": VERBATIM_MAX_WORDS,
        "index_fingerprint": full.fingerprint,
        "restricted_fingerprint": restricted.fingerprint,
        "files": out,
    }


def report_path(root: Path, model: str, version: str) -> Path:
    return root / "zoo" / "models" / model / "releases" / f"{version}.publication-scan.json"


def stage_publication(ctx) -> list[Finding]:
    rel = report_path(ctx.root, ctx.model, ctx.version).relative_to(ctx.root).as_posix()
    path = ctx.root / rel
    findings: list[Finding] = []
    if not path.exists():
        return [
            Finding(
                "C-U1",
                "publication",
                rel,
                "-",
                "publication scan report missing; run `zoo compliance scan-publish`",
            )
        ]
    report = json.loads(path.read_text(encoding="utf-8"))
    by_path = {f["path"]: f for f in report["files"]}
    for name, text in publication_files(ctx).items():
        entry = by_path.get(name)
        if entry is None or entry["sha256"] != sha256_text(text):
            findings.append(Finding("C-U1", "publication", rel, name, "file changed since the scan"))
            continue
        if entry["overlap_max_words"] >= VERBATIM_MAX_WORDS:
            findings.append(
                Finding(
                    "C-U2",
                    "publication",
                    rel,
                    name,
                    f"{entry['overlap_max_words']} consecutive corpus words (max "
                    f"{VERBATIM_MAX_WORDS - 1}, D7)",
                )
            )
        if entry["pii_hits"]:
            findings.append(Finding("C-U3", "publication", rel, name, f"{entry['pii_hits']} PII hit(s)"))
    findings += example_sources(ctx)
    return findings


def example_sources(ctx) -> list[Finding]:
    base = ctx.root / "zoo" / "models" / ctx.model / "examples"
    examples = [p for p in sorted(base.glob("*")) if p.is_file() and p.name != "SOURCES.yaml"]
    if not examples:
        return []
    rel = (base / "SOURCES.yaml").relative_to(ctx.root).as_posix()
    if not (base / "SOURCES.yaml").exists():
        return [Finding("C-U4", "publication", rel, "-", "examples without SOURCES.yaml")]
    entries = {
        e["file"]: e
        for e in (yaml.safe_load((base / "SOURCES.yaml").read_text()) or {}).get("examples", [])
    }
    findings = []
    for p in examples:
        e = entries.get(p.name)
        if e is None:
            findings.append(Finding("C-U4", "publication", rel, p.name, "example has no source entry"))
            continue
        if e.get("source") == "synthetic":
            continue
        src = ctx.reg.source(e.get("source", ""))
        if src is None or src.get("redistribution") != "allowed":
            findings.append(
                Finding(
                    "C-U4", "publication", rel, p.name, "source is neither synthetic nor redistributable"
                )
            )
    return findings


# ---- card lint (C-C1, C-C2) ------------------------------------------------------------------


def card_lint(card: str, topic: str, lint: dict[str, Any]) -> list[tuple[str, str, str]]:
    """[(check id, field, reason)] for a rendered card."""
    from mobility_model_zoo.release.card import sections, split_card

    _, body = split_card(card)
    found = sections(body)
    problems = []
    required = list(lint.get("required_sections", {}).get("all", []))
    if topic in lint.get("security_topics", []):
        required += lint.get("required_sections", {}).get("security", [])
    for title in required:
        heading = next((h for h in found if h == title or h.startswith(title)), None)
        if heading is None or not found[heading].strip():
            problems.append(("C-C1", title, "required section missing or empty"))
    for link in lint.get("required_links", []):
        if link not in card:
            problems.append(("C-C1", link, "required link missing"))
    disclaimer = lint.get("automotive_disclaimer") or {}
    if topic in disclaimer.get("topics", []) and not re.search(disclaimer["text_pattern"], card):
        problems.append(("C-C1", "automotive disclaimer", "missing"))
    negated_sections = set(lint.get("allow_negated_in_sections", []))
    for heading, text in found.items():
        for line in text.splitlines():
            negated = heading in negated_sections and re.match(
                r"\s*[-*]?\s*(not|do not|never)\b", line, re.I
            )
            for rule in lint.get("forbidden", []):
                if re.search(rule["pattern"], line) and not negated:
                    problems.append(("C-C2", heading, f"{rule['reason']}: {line.strip()[:80]}"))
    return problems


def stage_card(ctx) -> list[Finding]:
    card = ctx.extra.get("card")
    rel = f"zoo/models/{ctx.model}/model card"
    if card is None:
        return [Finding("C-C1", "card", rel, "-", "no rendered card to lint")]
    topic = ctx.extra.get("topic", "")
    lint = ctx.reg.lists("card-lint") or {}
    return [Finding(c, "card", rel, f, r) for c, f, r in card_lint(card, topic, lint)]


# ---- licence (C-L1 … C-L3) --------------------------------------------------------------------


def reuse_lint(root: Path) -> list[Finding]:
    try:
        out = subprocess.run(
            ["reuse", "--root", str(root), "lint", "--quiet"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return [Finding("C-L1", "licence", "REUSE.toml", "-", "reuse is not installed (dev group)")]
    if out.returncode != 0:
        lines = (out.stdout + out.stderr).strip().splitlines()[-3:]
        return [Finding("C-L1", "licence", "REUSE.toml", "-", "reuse lint failed: " + " | ".join(lines))]
    return []


def stage_licence(ctx) -> list[Finding]:
    from mobility_model_zoo.compliance.render import drift

    findings = reuse_lint(ctx.root)
    for f in drift(ctx.reg):
        if f.record in ("NOTICE", "THIRD_PARTY_NOTICES.md", "REUSE.toml"):
            findings.append(Finding("C-L2", "licence", f.record, f.field, f.reason))
    hub = ctx.extra.get("hub")
    rc, rel = _release(ctx) if ctx.model else (None, "")
    if hub is not None and rc is not None:
        model = ctx.extra.get("model_yaml") or {}
        info = hub.card_data(model.get("repos", {}).get("public", ""))
        if info is not None:
            if str(info.get("license", "")).lower() != str(model.get("license", "")).lower():
                findings.append(Finding("C-L3", "licence", rel, "license", "Hub licence differs"))
            if model.get("base_model") and info.get("base_model") != model.get("base_model"):
                findings.append(Finding("C-L3", "licence", rel, "base_model", "Hub base model differs"))
            if "-SA-" in model.get("license", "").upper() and info.get("gated"):
                findings.append(Finding("C-L3", "licence", rel, "gated", "share-alike repo is gated"))
    return findings


# ---- repository (C-G1 … C-G5) -----------------------------------------------------------------


def stage_repository(ctx) -> list[Finding]:
    root = ctx.root
    findings = [
        Finding("C-G1", "repository", f, "-", "missing")
        for f in REQUIRED_FILES
        if not (root / f).exists()
    ]
    if (root / ".github" / "FUNDING.yml").exists():
        findings.append(Finding("C-G2", "repository", ".github/FUNDING.yml", "-", "funding file"))
    controller = ctx.reg.controller()
    allow = contact_allowlist(controller)
    for rel in tracked_text_files(root):
        text = (root / rel).read_text(encoding="utf-8", errors="replace")
        public = not rel.startswith(BRAND_ALLOWED_PREFIXES) and not rel.startswith("tests/")
        if public:
            for m in FUNDING.finditer(text):
                findings.append(
                    Finding("C-G2", "repository", rel, "-", f"monetisation marker '{m.group(0)}'")
                )
            for line in text.splitlines():
                if BRAND.search(line) and not any(a in line for a in allow):
                    findings.append(
                        Finding("C-G2", "repository", rel, "-", "branding outside contact lines")
                    )
                    break
        if not rel.startswith(PII_SKIP_PREFIXES) and Path(rel).suffix in PII_SUFFIXES:
            hits = pii(text, allow + EXAMPLE_ADDRESSES)
            if hits:
                kinds = sorted({h.kind for h in hits})
                findings.append(
                    Finding("C-G5", "repository", rel, ",".join(kinds), f"{len(hits)} PII hit(s)")
                )
    for rel, data in ctx.reg.files.items():
        if (
            ctx.reg.stems[rel] == "release-compliance"
            and data.get("runtime") == "mcu"
            and not data.get("sbom")
        ):
            findings.append(
                Finding("C-G4", "repository", rel, "sbom", "mcu release without firmware SBOM")
            )
    return findings


EXAMPLE_ADDRESSES: list[str] = []


# ---- sign-off (C-S1) -------------------------------------------------------------------------


def stage_signoff(ctx) -> list[Finding]:
    rc, rel = _release(ctx)
    if rc is None:
        return [Finding("C-S1", "sign-off", rel, "-", "release compliance record missing")]
    if rc.get("state") not in ("signed_off", "published") or not rc.get("signed_off_by"):
        return [Finding("C-S1", "sign-off", rel, "state", "not signed off by the owner")]
    return []
