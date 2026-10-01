"""The release gate: 14 rules (contracts/cli.md, "Release gate rules").

Every rule returns a list of failure messages (empty = PASS) or raises `Skip`. `run_gate` runs all
of them, prints one line per rule and raises `GateFailed` (exit 1) or, if the only problem is that
the version already exists, `ImmutabilityRefused` (exit 3).
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Protocol

from mobility_model_zoo.release import card as cards
from mobility_model_zoo.release.errors import (
    CredentialError,
    GateFailed,
    HubError,
    ImmutabilityRefused,
    UsageError,
    ZooError,
)
from mobility_model_zoo.release.registry import (
    ORG,
    RESULT_KINDS,
    VERSION,
    Registry,
    parse_version,
    schema_errors,
)

PERMISSIVE = {"Apache-2.0", "MIT", "BSD-2-Clause", "BSD-3-Clause", "CC-BY-4.0"}
IGNORED_STAGING_FILES = {".gitattributes"}
MIN_EXAMPLES = 3
MAX_OUTPUT_CHARS = 4000
AGREEMENT = "they are not measured against human ground truth"
TITLES = {
    1: "schemas",
    2: "names",
    3: "version and status",
    4: "not yet published",
    5: "staged files",
    6: "licenses",
    7: "provenance",
    8: "recipe in git",
    9: "results and traceability",
    10: "model card",
    11: "upload allow-list",
    12: "usage example",
    13: "examples",
    14: "sandbox",
}


class Skip(Exception):
    pass


class Runner(Protocol):
    def run(self, code: str) -> tuple[int, str, str]:
        """Run Python code in a clean environment: (returncode, stdout, stderr)."""


@dataclass
class GitRepo:
    root: Path

    def _ok(self, *args: str) -> bool:
        result = subprocess.run(
            ["git", "-C", str(self.root), *args], capture_output=True, text=True, check=False
        )
        return result.returncode == 0

    def has_commit(self, sha: str) -> bool:
        return self._ok("cat-file", "-e", f"{sha}^{{commit}}")

    def has_file(self, sha: str, path: str) -> bool:
        return self._ok("cat-file", "-e", f"{sha}:{path}")

    def head(self) -> str:
        out = subprocess.run(
            ["git", "-C", str(self.root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()


@dataclass
class Gate:
    reg: Registry
    name: str
    version: str
    hub: Any = None  # Hub or FakeHub; None = offline
    runner: Runner | None = None  # None = rules 12 and 13 skip running the model
    card: str | None = None  # a card to check (publish: the reviewed preview); None = render one
    only: set[int] | None = None  # run only these rules (publish: 1-11 and 14)
    git: GitRepo | None = None
    results: dict[int, tuple[str, str]] = field(default_factory=dict)
    example_outputs: dict[str, str] = field(default_factory=dict)
    model: dict[str, Any] = field(default_factory=dict)
    record: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.git is None:
            self.git = GitRepo(self.reg.root)

    @property
    def offline(self) -> bool:
        return self.hub is None

    # ---- rules ---------------------------------------------------------------------------------
    _blocked: bool = False

    def rule_1(self) -> list[str]:
        """Schema validity. Invalid topics or model files block every other rule; an invalid release
        record does not, so that a draft record shows every gap at once."""
        failures = [f"zoo/topics.yaml {e}" for e in schema_errors("topics", self.reg.topics_raw())]
        failures += [f"model.yaml {e}" for e in schema_errors("model", self.model)]
        self._blocked = bool(failures)
        failures += [
            f"releases/{self.version}.yaml {e}" for e in schema_errors("release-record", self.record)
        ]
        return failures

    def rule_2(self) -> list[str]:
        m, r, name = self.model, self.record, self.name
        failures = []
        parts = name.split("-")
        if m.get("name") != name:
            failures.append(f"model.yaml name {m.get('name')!r} differs from directory {name!r}")
        if m.get("topic") != parts[0]:
            failures.append(f"topic {m.get('topic')!r} must be the first name segment {parts[0]!r}")
        if self.reg.topic(m.get("topic", "")) is None:
            failures.append(f"unknown topic {m.get('topic')!r} (not in zoo/topics.yaml)")
        if len(parts) < 3 or m.get("task") != parts[1] or m.get("variant") != "-".join(parts[2:]):
            failures.append("name must be <topic>-<task>-<variant> matching topic, task and variant")
        if r.get("model") != name:
            failures.append(f"release record model {r.get('model')!r} differs from {name!r}")
        if m["repos"]["public"] != f"{ORG}/{name}":
            failures.append(f"repos.public must be {ORG}/{name}")
        if m["repos"]["staging"] != f"{ORG}/{name}-staging":
            failures.append(f"repos.staging must be {ORG}/{name}-staging")
        if r["staging"]["repo"] != m["repos"]["staging"]:
            failures.append("staging.repo differs from the model's repos.staging")
        return failures

    def _previous(self) -> str | None:
        current = parse_version(self.version)
        older = [v for v in self.reg.published_versions(self.name) if parse_version(v) < current]
        return older[-1] if older else None

    def rule_3(self) -> list[str]:
        r, failures = self.record, []
        if r["version"] != self.version:
            failures.append(f"record version {r['version']} differs from {self.version}")
        major, minor, _ = parse_version(self.version)
        status = r["status"]
        if major == 0 and status != "experimental" and not (status == "deprecated" and r["deprecated"]):
            failures.append("a version below 1.0.0 must have status experimental")
        if major >= 1 and status == "experimental":
            failures.append("a version from 1.0.0 on cannot be experimental")
        if (status == "deprecated") != bool(r.get("deprecated")):
            failures.append("status deprecated and the deprecated block must go together")
        previous = self._previous()
        if previous is None:
            if r["change_type"] != "initial":
                failures.append("the first version must have change_type initial")
            return failures
        prev = self.reg.record_raw(self.name, previous)
        pmaj, pmin, _ = parse_version(previous)
        bump = "major" if major > pmaj else "minor" if minor > pmin else "patch"
        if r["change_type"] == "initial":
            failures.append(f"change_type initial only for the first version (previous: {previous})")
        elif r["change_type"] != bump:
            failures.append(f"change_type {r['change_type']} but {previous} -> {self.version} is {bump}")
        if prev.get("output_format_version") != r["output_format_version"]:
            if pmaj >= 1 and bump != "major":
                failures.append("a changed output format needs a major version from 1.0.0 on")
            if pmaj == 0 and bump == "patch":
                failures.append("a changed output format needs at least a minor version")
        if bump == "patch":
            same_files = {f["sha256"] for f in prev["files"]} == {f["sha256"] for f in r["files"]}
            if not same_files:
                failures.append("a patch version must not change the model files")
            for kind in RESULT_KINDS:
                try:
                    a = self.reg.results(self.name, previous, kind)["metrics"]
                    b = self.reg.results(self.name, self.version, kind)["metrics"]
                except UsageError:
                    continue
                if [(m["name"], m["value"]) for m in a] != [(m["name"], m["value"]) for m in b]:
                    failures.append(f"a patch version must not change the {kind} results")
        return failures

    def rule_4(self) -> list[str]:
        failures = []
        if self.record.get("published"):
            failures.append(f"version {self.version} is already published")
        current = parse_version(self.version)
        newer = [v for v in self.reg.published_versions(self.name) if parse_version(v) >= current]
        if newer and not self.record.get("published"):
            failures.append(f"version {self.version} is not newer than published {newer[-1]}")
        if not self.offline:
            repo = self.model["repos"]["public"]
            if self.hub.visibility(repo) is not None:
                tags = self.hub.refs(repo)["tags"]
                if f"v{self.version}" in tags:
                    failures.append(f"tag v{self.version} already exists in {repo}")
                hub_versions = [t[1:] for t in tags if t.startswith("v") and VERSION.match(t[1:])]
                if any(parse_version(v) > current for v in hub_versions):
                    failures.append(f"{repo} already has a newer version than {self.version}")
        return failures

    def rule_5(self) -> list[str]:
        if self.offline:
            raise Skip("needs the Hub")
        repo, revision = self.record["staging"]["repo"], self.record["staging"]["revision"]
        visibility = self.hub.visibility(repo)
        if visibility is None:
            return [f"staging repo {repo} does not exist"]
        if visibility != "private":
            return [f"staging repo {repo} is public; it must be private"]
        failures = []
        expected = {f["path"]: f for f in self.record["files"]}
        present = set(self.hub.list_files(repo, revision)) - IGNORED_STAGING_FILES
        for extra in sorted(present - set(expected)):
            failures.append(f"staged file {extra} is not listed in files[]")
        for path, f in sorted(expected.items()):
            info = self.hub.file_info(repo, path, revision)
            if info is None:
                failures.append(f"{path} is missing at staging revision {revision}")
            elif info != (f["sha256"], f["size_bytes"]):
                failures.append(f"{path} does not match its sha256 or size at {revision}")
        return failures

    def rule_6(self) -> list[str]:
        m, failures = self.model, []
        if m["license"] != "Apache-2.0" and not m.get("license_exception"):
            failures.append("license is not Apache-2.0 and license_exception is empty")
        if m.get("base_model_license") is None:
            if m["topic"] != "sandbox":
                failures.append("base_model_license may be null only in the sandbox topic")
        elif m["base_model_license"] not in PERMISSIVE:
            failures.append(
                f"base model license {m['base_model_license']} is not known to permit publication"
            )
        for t in self.record["provenance"]["teachers"]:
            if not t["training_on_outputs_permitted"]:
                failures.append(f"teacher {t['model_id']} does not permit training on its outputs")
        return failures

    def rule_7(self) -> list[str]:
        r, failures = self.record, []
        sandbox = self.model["topic"] == "sandbox"
        if r["provenance"]["spike_data"]:
            failures.append("spike_data is true: spike models and spike data are never released")
        for s in r["provenance"]["sources"]:
            if s["permitted_use"] != "training_allowed":
                failures.append(f"source {s['origin']} is {s['permitted_use']}, not training_allowed")
        for kind in RESULT_KINDS:
            try:
                synthetic = self.reg.results(self.name, self.version, kind).get("synthetic")
            except UsageError:
                continue
            if synthetic and not sandbox:
                failures.append(f"{kind} results are synthetic outside the sandbox topic")
        return failures

    def rule_8(self) -> list[str]:
        recipe = self.record["recipe"]
        if not self.git.has_commit(recipe["git_commit"]):
            return [f"recipe commit {recipe['git_commit']} is not in this repository"]
        return [
            f"{recipe[key]} does not exist at commit {recipe['git_commit'][:12]}"
            for key in ("config", "doc")
            if not self.git.has_file(recipe["git_commit"], recipe[key])
        ]

    def rule_11(self) -> list[str]:
        failures = []
        for f in self.record["files"]:
            p = PurePosixPath(f["path"])
            if p.is_absolute() or ".." in p.parts:
                failures.append(f"{p} is not a relative path inside the repo")
            elif p.parts[0] == "data" or p.name == ".env" or p.suffix == ".jsonl":
                failures.append(f"{p} may not be uploaded (data, secrets or labeling output)")
            elif str(p) in {"README.md", "build.json"}:
                failures.append(f"{p} is generated by the pipeline and may not be staged")
        return failures

    def rule_12(self) -> list[str]:
        if self.runner is None:
            raise Skip("runs the model; needs the Hub and a clean environment")
        examples = self.reg.examples(self.name)
        name, text = examples[0] if examples else ("(none)", "")
        return self._run_example(name, text)

    def rule_13(self) -> list[str]:
        examples = self.reg.examples(self.name)
        failures = []
        if len(examples) < MIN_EXAMPLES:
            failures.append(f"{len(examples)} example texts; at least {MIN_EXAMPLES} are required")
        if self.runner is None:
            return failures
        for name, text in examples:
            if name not in self.example_outputs:
                failures += self._run_example(name, text)
        return failures

    def _run_example(self, name: str, text: str) -> list[str]:
        r = self.record
        code = cards.fill(
            self.model["card"]["how_to_run"], r["staging"]["repo"], r["staging"]["revision"], text
        )
        rc, out, err = self.runner.run(code)
        if rc != 0:
            tail = "\n".join(err.strip().splitlines()[-5:])
            return [f"how_to_run failed on {name} (exit {rc}): {tail}"]
        self.example_outputs[name] = out.strip()[:MAX_OUTPUT_CHARS]
        return []

    def rule_9(self) -> list[str]:
        failures = []
        r = self.record
        for kind, key in (("quality", "evaluation"), ("performance", "performance")):
            expected = f"results/{self.version}/{kind}.json"
            if r[key]["results"] != expected:
                failures.append(f"{key}.results must be {expected}")
            try:
                data = self.reg.results(self.name, self.version, kind)
            except UsageError as e:
                failures.append(str(e))
                continue
            failures += [f"{kind}.json {e}" for e in schema_errors("results", data)]
            if (
                data.get("kind") != kind
                or data.get("model") != self.name
                or data.get("version") != self.version
            ):
                failures.append(f"{kind}.json kind, model or version does not match")
        if failures:
            return failures
        return failures + traceability(self.reg, self.name, self.version, self._card())

    def rule_10(self) -> list[str]:
        card = self._card()
        failures = card_structure(card)
        if self.offline:
            return failures
        verdict = self.hub.validate_yaml(card)
        failures += [f"Hub validation error: {e}" for e in verdict["errors"]]
        failures += [f"Hub validation warning: {w}" for w in verdict["warnings"]]
        return failures

    def rule_14(self) -> list[str]:
        sandbox_topic = self.model["topic"] == "sandbox"
        failures = []
        if bool(self.record["sandbox"]) != sandbox_topic:
            failures.append("sandbox must be true exactly for models in the sandbox topic")
        if not self.offline:
            visibility = self.hub.visibility(self.model["repos"]["public"])
            if sandbox_topic and visibility == "public":
                failures.append("the sandbox model's repo is public; it must stay private")
            if not sandbox_topic and visibility == "private":
                failures.append("the model's public repo exists but is private")
        return failures

    # ---- card ----------------------------------------------------------------------------------
    def _card(self) -> str:
        if self.card is None:
            self.card = cards.render(
                cards.CardInput(
                    self.reg,
                    self.name,
                    self.version,
                    record=self.record,
                    example_outputs=self.example_outputs,
                )
            )
        return self.card

    # ---- running -------------------------------------------------------------------------------
    ORDER = (1, 2, 3, 4, 5, 6, 7, 8, 11, 14, 12, 13, 9, 10)

    def run(self, say: Callable[[str], None] | None = None) -> None:
        say = say or (lambda line: print(line, file=sys.stderr))
        failures: dict[int, list[str]] = {}
        self.model = self.reg.model_raw(self.name)
        self.record = self.reg.record_raw(self.name, self.version)
        for number in self.ORDER:
            if self.only is not None and number not in self.only:
                self.results[number] = ("SKIP", "not part of this step")
                continue
            if number != 1 and self._blocked:
                self.results[number] = ("SKIP", "needs a valid model.yaml and topics.yaml (rule 1)")
                continue
            try:
                found = getattr(self, f"rule_{number}")()
            except Skip as e:
                self.results[number] = ("SKIP", str(e))
                continue
            except (CredentialError, HubError):
                raise  # the Hub, not the release, is the problem: exit 5 or 6
            except ZooError as e:
                found = [str(e)]
            except Exception as e:  # a rule must never crash the gate silently
                found = [f"rule crashed: {type(e).__name__}: {e}"]
            failures[number] = found
            self.results[number] = ("FAIL", "; ".join(found)) if found else ("PASS", "")
        for number in sorted(self.results):
            status, reason = self.results[number]
            say(f"rule {number:>2} {TITLES[number]:<26} {status}{': ' + reason if reason else ''}")
        failing = {n: f for n, f in failures.items() if f}
        if not failing:
            return
        messages = [f"rule {n}: {m}" for n, found in sorted(failing.items()) for m in found]
        if set(failing) == {4}:
            raise ImmutabilityRefused("; ".join(messages))
        raise GateFailed(messages)


# ---- card checks shared by rules 9 and 10 ------------------------------------------------------
def card_structure(card: str) -> list[str]:
    failures = []
    front, body = cards.split_card(card)
    found = cards.sections(body)
    for title in cards.SECTIONS:
        if title not in found:
            failures.append(f"card section '{title}' is missing")
        elif not found[title].strip():
            failures.append(f"card section '{title}' is empty")
    if not body.lstrip().startswith("# "):
        failures.append("card has no title")
    if AGREEMENT not in found.get("Quality", ""):
        failures.append("the Quality section must say the numbers are agreement, not ground truth")
    if "accuracy" in card.lower():
        failures.append("the card must not use the word 'accuracy' (spec FR-014)")
    for key in ("license", "language", "library_name", "pipeline_tag", "tags", "model-index"):
        if key not in front:
            failures.append(f"card metadata lacks {key}")
    return failures


def traceability(reg: Registry, name: str, version: str, card: str) -> list[str]:
    """Every number in the quality, speed and history tables and in model-index comes from a
    results file of the version it belongs to (FR-016)."""
    failures = []
    front, body = cards.split_card(card)
    found = cards.sections(body)

    def metrics(v: str, kind: str) -> dict[str, str]:
        try:
            return {m["name"]: cards.num(m["value"]) for m in reg.results(name, v, kind)["metrics"]}
        except UsageError:
            return {}

    for section, kind in (("Quality", "quality"), ("Speed and memory", "performance")):
        known = metrics(version, kind)
        for table in cards.tables(found.get(section, "")):
            for row in table:
                metric = row.get("Metric", "").strip("`")
                if known.get(metric) != row.get("Value"):
                    failures.append(f"{section}: {metric} = {row.get('Value')} is not in {kind}.json")
    for table in cards.tables(found.get("Version history", "")):
        for row in table:
            v = row.get("Version", "")
            known = metrics(v, "quality")
            for column, cell in row.items():
                if column.startswith("`") and cell != "–" and known.get(column.strip("`")) != cell:
                    failures.append(f"Version history: {v} {column} = {cell} is not in {v} quality.json")
    known = metrics(version, "quality")
    for entry in front.get("model-index", []):
        for result in entry.get("results", []):
            for m in result.get("metrics", []):
                if known.get(m.get("type")) != cards.num(m.get("value")):
                    failures.append(
                        f"model-index: {m.get('type')} = {m.get('value')} is not in quality.json"
                    )
    return failures
