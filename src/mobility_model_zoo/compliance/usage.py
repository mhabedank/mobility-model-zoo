"""Usage class of models: restrictions of every input carry over (constitution 2.1.0, Principle VI).

One derivation for the release gate, the train checks, the dataset guard and the audit (feature 011,
FR-022). A release's inputs are its training sources and datasets, its base model, its teachers, the
third-party models it loads at run time and data produced by zoo models. Each input's licence is
resolved through the project's licence list (`compliance/lists/licence-allowlist.yaml`); an input
whose licence cannot be resolved fails closed (C-U1).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from mobility_model_zoo.compliance.findings import UNKNOWN, Finding

CLASSES = ("commercial", "commercial-share-alike", "non-commercial", "non-commercial-share-alike")
NC_SUFFIX = "-nc"
LICENCE_LIST = Path("compliance") / "lists" / "licence-allowlist.yaml"
THIRD_PARTY = Path("compliance") / "third-party-models.yaml"


@dataclass(frozen=True)
class UsageClass:
    commercial: bool = True
    share_alike: bool = False

    @classmethod
    def parse(cls, value: str | None) -> UsageClass:
        if value not in CLASSES:
            raise ValueError(f"unknown usage class {value!r}; use one of {', '.join(CLASSES)}")
        return cls(commercial=value.startswith("commercial"), share_alike=value.endswith("share-alike"))

    def __str__(self) -> str:
        return ("commercial" if self.commercial else "non-commercial") + (
            "-share-alike" if self.share_alike else ""
        )

    def combine(self, other: UsageClass) -> UsageClass:
        """The most restrictive combination of two classes."""
        return UsageClass(self.commercial and other.commercial, self.share_alike or other.share_alike)

    def covers(self, other: UsageClass) -> bool:
        """True if this class is at least as restrictive as `other`."""
        return (not self.commercial or other.commercial) and (self.share_alike or not other.share_alike)

    @property
    def restricted(self) -> bool:
        return not self.commercial or self.share_alike

    def restriction(self) -> str:
        """Short label of what an input restricts: non-commercial, share-alike or both."""
        if not self.commercial and self.share_alike:
            return "non-commercial-share-alike"
        return "non-commercial" if not self.commercial else "share-alike" if self.share_alike else "none"


COMMERCIAL = UsageClass()
NON_COMMERCIAL = UsageClass(commercial=False)


@dataclass(frozen=True)
class LicenceEntry:
    id: str
    non_commercial: bool = False
    share_alike: bool = False
    trains: bool = True
    release_licences: tuple[str, ...] = ()
    note: str = ""

    @property
    def restriction(self) -> UsageClass:
        return UsageClass(commercial=not self.non_commercial, share_alike=self.share_alike)


@dataclass
class LicenceList:
    entries: dict[str, LicenceEntry] = field(default_factory=dict)

    @classmethod
    def load(cls, root: Path) -> LicenceList:
        path = root / LICENCE_LIST
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
        return cls.from_records((raw or {}).get("licences", []))

    @classmethod
    def from_records(cls, records: list[dict[str, Any]]) -> LicenceList:
        entries = {}
        for e in records:
            entries[e["id"]] = LicenceEntry(
                id=e["id"],
                non_commercial=bool(e.get("non_commercial", False)),
                share_alike=bool(e.get("share_alike", False)),
                trains=bool(e.get("trains", True)),
                release_licences=tuple(e.get("release_licences") or ()),
                note=e.get("note", ""),
            )
        return cls(entries)

    def get(self, licence: str | None) -> LicenceEntry | None:
        return self.entries.get(licence or "")

    def errors(self) -> list[str]:
        out = []
        for e in self.entries.values():
            if e.share_alike and not e.release_licences:
                out.append(f"{e.id}: share_alike needs release_licences")
            out += [f"{e.id}: release licence {r} is not listed" for r in e.release_licences
                    if r not in self.entries]
        return out

    def licence_class(self, licence: str) -> UsageClass | None:
        """The class a release licence marks: non-commercial and share-alike attributes."""
        entry = self.get(licence)
        return entry.restriction if entry else None


@dataclass(frozen=True)
class RestrictingInput:
    kind: str  # source | dataset | base_model | teacher | third_party | zoo_model_output
    id: str
    licence: str
    restriction: UsageClass
    release_licences: tuple[str, ...] = ()  # share-alike inputs: release licences that satisfy them

    def record(self) -> dict[str, str]:
        return {"kind": self.kind, "id": self.id, "licence": self.licence,
                "restriction": self.restriction.restriction()}

    def text(self) -> str:
        label = {"source": "source", "dataset": "dataset", "base_model": "base model",
                 "teacher": "teacher", "third_party": "third-party model",
                 "zoo_model_output": "data produced by"}[self.kind]
        return f"{label} {self.id} ({self.licence})"


@dataclass
class Derivation:
    cls: UsageClass = COMMERCIAL
    inputs: list[RestrictingInput] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    @property
    def restricting(self) -> list[RestrictingInput]:
        return [i for i in self.inputs if i.restriction.restricted]

    def add(self, item: RestrictingInput) -> None:
        self.inputs.append(item)
        self.cls = self.cls.combine(item.restriction)


# ---- licence resolution (research R3) -----------------------------------------------------------


def free_text_licence(text: str) -> str | None:
    from mobility_model_zoo.compliance.bootstrap import LICENCES

    for pattern, spdx, _ in LICENCES:
        if re.search(pattern, text or ""):
            return spdx
    return None


def resolve_source_licence(
    source: dict[str, Any],
    licences: LicenceList,
    declared: dict[str, Any] | None = None,
    by_origin: dict[str, dict[str, Any]] | None = None,
) -> str:
    """Licence id of a release-record source: the dataset declaration, then the compliance record of
    the same origin, then the licence string itself, then the free-text mapping. Returns the first
    candidate that is on the licence list, otherwise the best candidate (unresolved)."""
    candidates: list[str] = []
    ds = (declared or {}).get(source.get("dataset") or "")
    if ds is not None:
        candidates.append(ds.license)
    rec = (by_origin or {}).get(source.get("origin", ""))
    if rec is not None and rec.get("licence"):
        candidates.append(rec["licence"])
    raw = source.get("license") or UNKNOWN
    candidates.append(raw)
    mapped = free_text_licence(raw)
    if mapped:
        candidates.append(mapped)
    return next((c for c in candidates if licences.get(c)), candidates[0])


# ---- zoo models and third-party models -----------------------------------------------------------


def zoo_model_class(root: Path, model_id: str) -> UsageClass | None:
    """Declared class of a zoo model named `name` or `mobility-model-zoo/name`, else None."""
    name = model_id.split("/", 1)[1] if model_id.startswith("mobility-model-zoo/") else model_id
    path = root / "zoo" / "models" / name / "model.yaml"
    if "/" in name or not path.exists():
        return None
    value = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("usage_class")
    return UsageClass.parse(value) if value in CLASSES else None


def declared_class(root: Path, model_name: str | None) -> str:
    """Declared usage class of a zoo model for train-time checks; commercial when the model is not
    named or has no declaration (the strict default, FR-006)."""
    cls = zoo_model_class(root, model_name) if model_name else None
    return str(cls) if cls is not None else "commercial"


def third_party_records(root: Path) -> dict[str, dict[str, Any]]:
    path = root / THIRD_PARTY
    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {r["id"]: r for r in raw.get("models", []) if isinstance(r, dict) and "id" in r}


def third_party_class(
    record: dict[str, Any], licences: LicenceList
) -> tuple[UsageClass, list[str], list[Finding]]:
    """Restriction of a third-party model: its weights licence combined with every licence of the
    training data its model card names (training data governs, FR-019). Returns the class, the
    reasons and findings for unresolved licences (C-U1) and unknown training-data licences (C-X2)."""
    cls, reasons, findings = COMMERCIAL, [], []
    entry = licences.get(record.get("weights_licence"))
    if entry is None:
        findings.append(Finding("C-U1", "usage", record["id"], "weights_licence",
                                f"licence {record.get('weights_licence')} is not on the licence list"))
    else:
        cls = cls.combine(entry.restriction)
        if entry.restriction.restricted:
            reasons.append(f"weights {entry.id}")
    for data in record.get("training_data") or []:
        licence = data.get("licence") or UNKNOWN
        if licence == UNKNOWN:
            findings.append(Finding("C-X2", "meta", record["id"], "training_data",
                                    f"licence of training data {data.get('name')} is unknown"))
            continue
        entry = licences.get(licence)
        if entry is None:
            findings.append(Finding("C-U1", "usage", record["id"], "training_data",
                                    f"licence {licence} of {data.get('name')} is not listed"))
            continue
        # Only the non-commercial term of third-party training data carries over: share-alike terms
        # bind the third party's weights, whose licence is checked above.
        if entry.non_commercial:
            cls = cls.combine(NON_COMMERCIAL)
            reasons.append(f"training data {data.get('name')} ({licence})")
    return cls, reasons, findings


def third_party_metadata(root: Path, ids: list[str]) -> list[dict[str, Any]]:
    """For stage outputs (FR-020): id, revision, usage class and reason of each registered model."""
    licences, records, out = LicenceList.load(root), third_party_records(root), []
    for model_id in ids:
        rec = records.get(model_id)
        if rec is None:
            raise KeyError(f"{model_id} is not in {THIRD_PARTY}")
        cls, reasons, _ = third_party_class(rec, licences)
        out.append({"id": model_id, "revision": rec.get("revision"), "usage_class": str(cls),
                    "reason": "; ".join(reasons) or "no restricting licence"})
    return out


def _release_licences(licences: LicenceList, licence: str | None) -> tuple[str, ...]:
    entry = licences.get(licence)
    return entry.release_licences if entry else ()


# ---- derivation (research R4) --------------------------------------------------------------------


def derive_release(
    root: Path,
    model: dict[str, Any],
    record: dict[str, Any],
    *,
    register: Any = None,
    declared: dict[str, Any] | None = None,
    licences: LicenceList | None = None,
) -> Derivation:
    """Derived usage class of one release from all of its inputs (FR-002).

    `register` is the compliance register (sources by origin, provider routes) or None when the
    repository has none; `declared` maps dataset ids to declarations (datasets.registry.load)."""
    licences = licences or LicenceList.load(root)
    if declared is None:
        from mobility_model_zoo.datasets.registry import load

        declared = load(root)
    by_origin = {}
    if register is not None:
        recs = register.records("sources") + register.records("datasets")
        by_origin = {s["origin_url"]: s for s in recs}
    out = Derivation()
    for source in record.get("provenance", {}).get("sources", []):
        if source.get("permitted_use") != "training_allowed":
            continue  # measured only (FR-004); rule 7 refuses benchmark_only sources in provenance
        _add_source(root, out, source, licences, declared, by_origin)
    _add_base_model(root, out, model, licences)
    for teacher in record.get("provenance", {}).get("teachers", []):
        _add_teacher(root, out, teacher, register)
    records = third_party_records(root)
    for model_id in model.get("runtime_models") or []:
        rec = records.get(model_id)
        if rec is None:
            out.findings.append(Finding("C-X1", "usage", model_id, "runtime_models",
                                        f"third-party model is not in {THIRD_PARTY}"))
            continue
        cls, reasons, findings = third_party_class(rec, licences)
        out.findings += findings
        out.add(RestrictingInput("third_party", model_id, "; ".join(reasons) or rec["weights_licence"],
                                 cls, _release_licences(licences, rec.get("weights_licence"))))
    return out


def _add_source(root, out, source, licences, declared, by_origin) -> None:
    ds_id = source.get("dataset")
    kind, ident = ("dataset", ds_id) if ds_id else ("source", source.get("origin", "?"))
    licence = resolve_source_licence(source, licences, declared, by_origin)
    entry = licences.get(licence)
    if entry is None:
        out.findings.append(Finding("C-U1", "usage", ident, "license",
                                    f"licence {source.get('license')!r} resolves to no entry of the "
                                    "licence list"))
        return
    if not entry.trains:
        out.findings.append(Finding("C-T2", "usage", ident, "license", f"{licence} cannot train"))
        return
    restriction = entry.restriction
    ds = declared.get(ds_id) if ds_id else None
    if ds is not None and not ds.commercial_use:
        restriction = restriction.combine(NON_COMMERCIAL)
    producer = getattr(ds, "produced_by", None) if ds is not None else None
    if producer:
        producer_cls = zoo_model_class(root, producer)
        if producer_cls is None:
            out.findings.append(Finding("C-U1", "usage", ident, "produced_by",
                                        f"producer {producer} is not a zoo model with a usage class"))
        elif not producer_cls.commercial:
            out.add(RestrictingInput("zoo_model_output", f"{producer} → {ident}", str(producer_cls),
                                     NON_COMMERCIAL))
    out.add(RestrictingInput(kind, ident, licence, restriction, entry.release_licences))


def _add_base_model(root, out, model, licences) -> None:
    base = model.get("base_model")
    if not base:
        return
    record = third_party_records(root).get(base)
    if record is not None:
        cls, reasons, findings = third_party_class(record, licences)
        out.findings += findings
        out.add(RestrictingInput("base_model", base, "; ".join(reasons) or record["weights_licence"],
                                 cls, _release_licences(licences, record.get("weights_licence"))))
        return
    licence = model.get("base_model_license")
    entry = licences.get(licence)
    if entry is None:
        out.findings.append(Finding("C-U1", "usage", base, "base_model_license",
                                    f"licence {licence} is not on the licence list"))
        return
    out.add(RestrictingInput("base_model", base, licence, entry.restriction, entry.release_licences))


def _add_teacher(root, out, teacher, register) -> None:
    model_id = teacher["model_id"]
    zoo_cls = zoo_model_class(root, model_id)
    if zoo_cls is not None:
        # Outputs of a non-commercial zoo model are non-commercial data (FR-008); share-alike terms
        # bind the teacher's weights, not its outputs.
        out.add(RestrictingInput("teacher", model_id, f"zoo model, {zoo_cls}",
                                 UsageClass(commercial=zoo_cls.commercial)))
        return
    terms = register.output_training_terms(model_id) if register is not None else None
    if teacher.get("outputs_non_commercial") or terms == "non_commercial":
        out.add(RestrictingInput("teacher", model_id, "outputs may train non-commercial models only",
                                 NON_COMMERCIAL))
    else:
        out.add(RestrictingInput("teacher", model_id, teacher.get("license_basis", ""), COMMERCIAL))


# ---- release licence and marking (research R5) ---------------------------------------------------


def release_findings(
    declared: UsageClass, licence: str, derivation: Derivation, licences: LicenceList
) -> list[Finding]:
    """C-U2: the declared class must cover the derived class. C-U3: the release licence must mark the
    declared class and satisfy every share-alike input; share-alike inputs that no single licence
    satisfies are a conflict."""
    findings = []
    if not declared.covers(derivation.cls):
        for item in derivation.restricting:
            if not declared.covers(item.restriction):
                findings.append(Finding(
                    "C-U2", "usage", item.id, "usage_class",
                    f"{item.text()} makes the model {item.restriction.restriction()}, but it is "
                    f"declared {declared}"))
    marked = licences.licence_class(licence)
    if marked is None:
        findings.append(Finding("C-U3", "usage", licence, "license",
                                f"release licence {licence} is not on the licence list"))
    elif marked != declared:
        findings.append(Finding("C-U3", "usage", licence, "license",
                                f"release licence {licence} marks the model {marked}, but it is "
                                f"declared {declared}"))
    share_alike = [i for i in derivation.inputs if i.restriction.share_alike]
    allowed: set[str] | None = None
    for item in share_alike:
        options = set(item.release_licences)
        allowed = options if allowed is None else allowed & options
    if allowed is not None and not allowed:
        names = ", ".join(i.text() for i in share_alike)
        findings.append(Finding("C-U3", "usage", "share-alike", "license",
                                f"no single release licence satisfies the share-alike inputs: {names}"))
    elif allowed is not None and licence not in allowed:
        findings.append(Finding("C-U3", "usage", licence, "license",
                                f"share-alike inputs require the release licence to be one of "
                                f"{', '.join(sorted(allowed))}, not {licence}"))
    return findings


def name_findings(name: str, variant: str, declared: UsageClass) -> list[Finding]:
    """C-U4: `<name>-<variant>-nc` for non-commercial classes, never `-nc` for commercial ones."""
    if declared.commercial:
        if name.endswith(NC_SUFFIX):
            return [Finding("C-U4", "usage", name, "name",
                            "name ends in -nc but the model is declared commercial")]
        return []
    if not name.endswith(f"-{variant}{NC_SUFFIX}"):
        return [Finding("C-U4", "usage", name, "name",
                        "name must be <name>-<variant>-nc for a non-commercial model")]
    return []


def usage_block(declared: UsageClass, licence: str, derivation: Derivation) -> dict[str, Any]:
    """The `usage` object of a release record (FR-013)."""
    return {"class": str(declared), "licence": licence,
            "restricting_inputs": [i.record() for i in derivation.restricting]}
