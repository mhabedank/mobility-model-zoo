"""The release gate: rules 1-17 (contracts/cli.md; rule 15 from feature 005, 16 from 006, 17 from 008).

Every rule returns a list of failure messages (empty = PASS) or raises `Skip`. `run_gate` runs all
of them, prints one line per rule and raises `GateFailed` (exit 1) or, if the only problem is that
the version already exists, `ImmutabilityRefused` (exit 3).
"""

from __future__ import annotations

import json
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

IGNORED_STAGING_FILES = {".gitattributes"}
MIN_EXAMPLES = 3
MAX_OUTPUT_CHARS = 4000
AGREEMENT = "they are not measured against human ground truth"
GROUND_TRUTH = cards.GROUND_TRUTH
DEVICE_METRICS = ("flash_kb", "ram_kb", "latency_us")
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
    15: "device evidence",
    16: "compliance",
    17: "site text",
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
        if not self._blocked:
            failures += self._runtime_failures()
        return failures

    @property
    def mcu(self) -> bool:
        return Registry.runtime(self.model) == "mcu"

    def _runtime_failures(self) -> list[str]:
        """Rule 1, conditional part: what each runtime needs (contracts/release-format.md)."""
        m, failures = self.model, []
        budget = (self.record.get("performance") or {}).get("budget") or {}
        if self.mcu:
            if not m["card"].get("device_usage"):
                failures.append("model.yaml card.device_usage is required for runtime mcu")
            if "ram_kb" not in budget:
                failures.append("performance.budget must be {ram_kb, flash_kb, target} for runtime mcu")
        else:
            if not m.get("languages"):
                failures.append("model.yaml languages must not be empty for runtime python")
            if "{text}" not in m["card"]["how_to_run"]:
                failures.append("card.how_to_run must contain {text} for runtime python")
            if "ram_gb" not in budget:
                failures.append("performance.budget must be {ram_gb, gpu: false} for runtime python")
        return failures

    def rule_2(self) -> list[str]:
        m, r, name = self.model, self.record, self.name
        failures = []
        if m.get("name") != name:
            failures.append(f"model.yaml name {m.get('name')!r} differs from directory {name!r}")
        if self.reg.topic(m.get("topic", "")) is None:
            failures.append(f"unknown topic {m.get('topic')!r} (not in zoo/topics.yaml)")
        # <name>-<variant> (constitution 1.4.0): topic and task are fields and tags, not segments;
        # non-commercial models end in -nc (constitution 2.1.0).
        variant = m.get("variant") or ""
        nc = m.get("usage_class", "").startswith("non-commercial")
        base = name.removesuffix("-nc") if nc else name
        if not variant or not base.endswith(f"-{variant}") or base == f"-{variant}":
            failures.append("name must be <name>-<variant> ending with the model's variant")
        failures += self._name_suffix_failures(name, variant)
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
        """Licences and the usage class (constitution 2.1.0, VI and IX; feature 011)."""
        m, failures = self.model, []
        if m["license"] != "Apache-2.0" and not m.get("license_exception"):
            failures.append("license is not Apache-2.0 and license_exception is empty")
        if m.get("base_model") and m.get("base_model_license") is None:
            failures.append("base_model is set but base_model_license is null")
        for t in self.record["provenance"]["teachers"]:
            if not t["training_on_outputs_permitted"]:
                failures.append(f"teacher {t['model_id']} does not permit training on its outputs")
        failures += self._dataset_failures()
        creg = self._compliance()
        if creg is not None and creg.release(self.name, self.version) is not None:
            for t in self.record["provenance"]["teachers"]:
                if creg.output_training_terms(t["model_id"]) in ("no", "unclear"):
                    failures.append(f"teacher {t['model_id']}: a provider route does not permit "
                                    "training on outputs (compliance/providers.yaml) and no decision "
                                    "covers it")
        return failures + self._usage_failures(creg)

    def _usage_failures(self, creg) -> list[str]:
        """The declared usage class covers the class derived from every input, the licence marks it,
        and a release record not yet published stores it (FR-009 to FR-013)."""
        from mobility_model_zoo.compliance.usage import (
            LicenceList,
            UsageClass,
            derive_release,
            release_findings,
            usage_block,
        )

        m, r = self.model, self.record
        try:
            declared = UsageClass.parse(m.get("usage_class"))
        except ValueError as e:
            return [str(e)]
        root = self.reg.zoo.parent
        licences = LicenceList.load(root)
        derivation = derive_release(root, m, r, register=creg, licences=licences)
        found = derivation.findings + release_findings(declared, m["license"], derivation, licences)
        failures = [f"{f.check_id}: {f.reason} [{f.record}]" for f in found]
        expected = usage_block(declared, m["license"], derivation)
        usage = r.get("usage")
        if usage is None and not r.get("published"):
            failures.append("C-K5: the release record lacks `usage`; expected "
                            + json.dumps(expected, sort_keys=True))
        elif usage is not None and usage != expected:
            failures.append("C-K5: `usage` of the release record differs from the derivation; "
                            "expected " + json.dumps(expected, sort_keys=True))
        for v in self.reg.versions(self.name):
            if parse_version(v) >= parse_version(self.version):
                continue
            earlier = (self.reg.record_raw(self.name, v).get("usage") or {}).get("class")
            if earlier and earlier != str(declared):
                failures.append(f"C-K5: version {v} is {earlier}; a model's usage class never "
                                "changes, a new class needs a new model name")
        return failures

    def _name_suffix_failures(self, name: str, variant: str) -> list[str]:
        from mobility_model_zoo.compliance.usage import UsageClass, name_findings

        try:
            declared = UsageClass.parse(self.model.get("usage_class"))
        except ValueError:
            return []  # rule 1 reports the schema error
        return [f"{f.check_id}: {f.reason}" for f in name_findings(name, variant, declared)]

    def _datasets(self) -> dict[str, Any]:
        from mobility_model_zoo.datasets.registry import load

        return load(self.reg.zoo.parent)

    def _dataset_failures(self) -> list[str]:
        """Rule 6 for declared datasets: declaration, licence, permitted use and status."""
        failures = []
        sources = self.record["provenance"]["sources"]
        declared = self._datasets() if any(s.get("dataset") for s in sources) else {}
        # Non-commercial and share-alike terms are checked by the usage class (_usage_failures).
        for s in sources:
            licence = s["license"]
            ds = s.get("dataset")
            if not ds:
                continue
            d = declared.get(ds)
            if d is None:
                failures.append(f"dataset {ds} is not declared in topics/*/compliance/datasets.yaml")
                continue
            if d.license != licence:
                failures.append(f"dataset {ds}: declared license {d.license} differs from {licence}")
            if d.permitted_use != "training_allowed" or d.status != "active":
                failures.append(f"dataset {ds} is {d.permitted_use}, status {d.status}")
        return failures

    def _compliance(self):
        from mobility_model_zoo.compliance.register import Register

        root = self.reg.zoo.parent
        if not (root / "compliance" / "controller.yaml").exists():
            return None
        return Register.load(root)

    def rule_16(self) -> list[str]:
        """Compliance harness (feature 006): the release stages of contracts/checks.md."""
        from mobility_model_zoo.compliance import checks
        from mobility_model_zoo.compliance.findings import StageFailed, run_stages

        creg = self._compliance()
        if creg is None:
            # Repositories without a register (test fixtures) skip; in the zoo repository a missing
            # register fails `zoo validate --all` (C-M1), so this cannot pass silently in CI.
            raise Skip("no compliance register (compliance/controller.yaml)")
        names = (["meta", "licence", "repository"] if self.model["topic"] == "sandbox"
                 else list(checks.RELEASE_STAGES))
        ctx = checks.Context(creg, model=self.name, version=self.version, extra={
            "card": self.publication_card(), "topic": self.model["topic"],
            "hub": self.hub, "model_yaml": self.model})
        try:
            run_stages(checks.stages_named(names), ctx)
        except StageFailed as e:
            return e.failures
        return []

    def rule_17(self) -> list[str]:
        """Website text (feature 008): `site.yaml` is valid and every number in it resolves against
        this version's results, so publishing can never break the site build (spec FR-005)."""
        if self.model["topic"] == "sandbox" or self.record.get("sandbox"):
            raise Skip("sandbox models have no website page")
        from mobility_model_zoo.site.context import pitch_errors

        return pitch_errors(self.reg, self.name, self.version)

    def publication_card(self) -> str:
        """The card as scanned for publication: without model outputs (they are spans of the
        fictional example inputs), so the scan and the gate hash the same text."""
        return cards.render(cards.CardInput(self.reg, self.name, self.version, record=self.record))

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
            elif (
                p.parts[0] == "data"
                or p.name == ".env"
                or p.suffix == ".jsonl"
                or p.name.endswith(".eval.npz")
            ):
                failures.append(f"{p} may not be uploaded (data, secrets or labeling output)")
            elif str(p) in {"README.md", "build.json"}:
                failures.append(f"{p} is generated by the pipeline and may not be staged")
        return failures

    def rule_12(self) -> list[str]:
        if self.mcu:
            if self.offline:
                raise Skip("loads the staged int8 model; needs the Hub")
            examples = self.reg.device_examples(self.name)
            return self._device_example(*examples[0]) if examples else ["no examples/*.json"]
        if self.runner is None:
            raise Skip("runs the model; needs the Hub and a clean environment")
        examples = self.reg.examples(self.name)
        name, text = examples[0] if examples else ("(none)", "")
        return self._run_example(name, text)

    def rule_13(self) -> list[str]:
        if self.mcu:
            return self._device_examples_rule()
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

    def _device_examples_rule(self) -> list[str]:
        examples = self.reg.device_examples(self.name)
        failures = []
        if len(examples) < MIN_EXAMPLES:
            failures.append(f"{len(examples)} examples/*.json; at least {MIN_EXAMPLES} are required")
        declared = None
        for name, ex in examples:
            missing = [k for k in ("input", "expected", "source") if k not in ex]
            if missing:
                failures.append(f"{name} lacks {', '.join(missing)}")
                continue
            if ex["source"] != "synthetic":
                declared = declared if declared is not None else self._datasets()
                d = declared.get(ex["source"])
                if d is None or d.redistribution != "allowed":
                    state = "undeclared" if d is None else f"redistribution {d.redistribution}"
                    failures.append(
                        f"{name}: source {ex['source']} is {state}; examples must be synthetic or "
                        "from a dataset whose declaration allows redistribution"
                    )
        if self.offline or failures:
            return failures
        for name, ex in examples:
            if name not in self.example_outputs:
                failures += self._device_example(name, ex)
        return failures

    def _staged_qmodel(self):
        """The staged int8 model (the `.npz` in files[]), loaded once."""
        import tempfile

        from mobility_model_zoo.edge.int8.model import QModel

        if getattr(self, "_qmodel", None) is None:
            npz = [f["path"] for f in self.record["files"] if f["path"].endswith(".npz")]
            if not npz:
                raise ZooError("files[] has no .npz int8 model")
            r = self.record["staging"]
            with tempfile.TemporaryDirectory() as tmp:
                path = self.hub.download(r["repo"], npz[0], r["revision"], Path(tmp))
                self._qmodel = QModel.load(path)
        return self._qmodel

    def _device_example(self, name: str, ex: dict[str, Any]) -> list[str]:
        """Rules 12/13 for mcu: the example must match bit-exactly on the host reference."""
        import json

        import numpy as np

        from mobility_model_zoo.edge.int8.reference import run_model

        qm = self._staged_qmodel()
        got = run_model(qm, np.asarray(ex["input"], dtype=np.int8)).reshape(-1)
        expected = np.asarray(ex["expected"], dtype=np.int64).reshape(-1)
        if got.shape != expected.shape or not np.array_equal(got.astype(np.int64), expected):
            return [f"{name}: host reference output differs from expected"]
        self.example_outputs[name] = json.dumps({"output": got.astype(int).tolist()})
        return []

    def rule_15(self) -> list[str]:
        """Device evidence for mcu models (contracts/release-format.md)."""
        if not self.mcu:
            raise Skip("only for runtime mcu")
        try:
            metrics = self.reg.results(self.name, self.version, "performance")["metrics"]
        except UsageError as e:
            return [str(e)]
        failures = []
        names = {m["name"] for m in metrics}
        failures += [f"performance metric {n} is missing" for n in DEVICE_METRICS if n not in names]
        for m in metrics:
            if m["name"] in DEVICE_METRICS and not (m.get("origin") and m.get("hardware")):
                failures.append(f"performance metric {m['name']} needs origin and hardware")
        if self.record["status"] != "experimental" and not any(
            m["name"] == "latency_us" and m.get("origin") == "real_board" for m in metrics
        ):
            failures.append("no real-board latency: only status experimental may rely on emulators")
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
        failures = card_structure(card, self.record["evaluation"].get("reference_kind"))
        usage = cards.usage_line(self.model, self.record)
        if f"**Usage:** {usage}" not in card:
            failures.append(f"the card must state its usage below the version line: {usage}")
        root = self.reg.zoo.parent
        failures += [f"figure {f['path']} is not in the repository"
                     for f in self.model["card"].get("figures", []) if not (root / f["path"]).is_file()]
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
    ORDER = (1, 2, 3, 4, 5, 6, 7, 8, 11, 14, 12, 13, 9, 15, 10, 16, 17)

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
        error = GateFailed(messages)
        error.gate = self  # per-rule results for callers that report them
        raise error


# ---- card checks shared by rules 9 and 10 ------------------------------------------------------
def card_structure(card: str, reference_kind: str | None = None) -> list[str]:
    failures = []
    front, body = cards.split_card(card)
    found = cards.sections(body)
    required = cards.COMPLIANCE_SECTIONS if "Training data and attribution" in found else cards.SECTIONS
    for title in required:
        if title not in found:
            failures.append(f"card section '{title}' is missing")
        elif not found[title].strip():
            failures.append(f"card section '{title}' is empty")
    if not body.lstrip().startswith("# "):
        failures.append("card has no title")
    if (reference_kind or "model_consensus") == "ground_truth":
        if GROUND_TRUTH not in " ".join(found.get("Quality", "").split()):
            failures.append(f"the Quality section must say: {GROUND_TRUTH}")
    else:
        if AGREEMENT not in found.get("Quality", ""):
            failures.append("the Quality section must say the numbers are agreement, not ground truth")
        # agreement with reference models is not accuracy (constitution 2.0.0, III metric naming)
        if "accuracy" in card.lower():
            failures.append("the card must not use the word 'accuracy' for model-consensus quality")
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
