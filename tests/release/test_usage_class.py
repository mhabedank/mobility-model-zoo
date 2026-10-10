"""Usage class in the release gate: non-commercial releases and hidden restrictions (feature 011,
T018 and T024). The NC fixture is the mcu fixture renamed to `edge-fixture-tiny-nc`, declared
non-commercial and trained on a CC-BY-NC-4.0 dataset."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
from pathlib import Path

import pytest
import yaml
from conftest import VERSION, ZooEnv, git, make_mcu_env
from edge_fixture import NAME, npz_bytes
from test_edge_rules import failures, run_gate, source

from mobility_model_zoo.datasets.registry import declarations
from mobility_model_zoo.release import card as cards
from mobility_model_zoo.release.registry import dump_yaml

ROOT = Path(__file__).resolve().parents[2]
NC_NAME = f"{NAME}-nc"
NC_DATASET = "tue-can-v2"
NC_USAGE = {
    "class": "non-commercial",
    "licence": "CC-BY-NC-4.0",
    "restricting_inputs": [{"kind": "dataset", "id": NC_DATASET, "licence": "CC-BY-NC-4.0",
                            "restriction": "non-commercial"}],
}


def declare(root: Path, records: list[dict]) -> None:
    d = root / "topics" / "sandbox" / "compliance"
    d.mkdir(parents=True, exist_ok=True)
    (d / "datasets.yaml").write_text(yaml.safe_dump({"datasets": records}), encoding="utf-8")


def nc_dataset(**changes) -> dict:
    """The real TU Eindhoven CAN declaration, made usable for training a non-commercial model."""
    rec = copy.deepcopy(next(r for _, r in declarations(ROOT) if r["id"] == NC_DATASET))
    rec.update(permitted_use="training_allowed", status="active", commercial_use=False)
    rec.pop("reason", None)
    rec.update(changes)
    return rec


def write_model(env: ZooEnv, name: str, data: dict) -> None:
    (env.reg.model_dir(name) / "model.yaml").write_text(dump_yaml(data), encoding="utf-8")


def make_nc_env(root: Path) -> ZooEnv:
    env = make_mcu_env(root)
    shutil.move(env.reg.model_dir(NAME), env.reg.model_dir(NC_NAME))
    model = env.reg.model_raw(NC_NAME)
    model.update(
        name=NC_NAME,
        usage_class="non-commercial",
        license="CC-BY-NC-4.0",
        license_exception=f"trained on {NC_DATASET} (CC BY-NC 4.0); non-commercial use only",
        repos={"public": f"mobility-model-zoo/{NC_NAME}",
               "staging": f"mobility-model-zoo/{NC_NAME}-staging"},
    )
    write_model(env, NC_NAME, model)
    for path in (env.reg.model_dir(NC_NAME) / "results").rglob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        data["model"] = NC_NAME
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    declare(env.root, [nc_dataset()])
    staged = {"model.npz": npz_bytes(env.qmodel)}
    record = env.reg.record_raw(NC_NAME, VERSION)
    record["model"] = NC_NAME
    record["staging"] = {"repo": model["repos"]["staging"],
                         "revision": env.hub.seed(model["repos"]["staging"], staged, private=True)}
    record["files"] = [{"path": p, "sha256": hashlib.sha256(b).hexdigest(), "size_bytes": len(b)}
                       for p, b in sorted(staged.items())]
    record["provenance"]["sources"] = [source(NC_DATASET, "CC-BY-NC-4.0")]
    record["usage"] = copy.deepcopy(NC_USAGE)
    env.reg.write_record(NC_NAME, VERSION, record)
    git(root, "-c", "user.email=t@example.org", "-c", "user.name=t", "add", "-A")
    git(root, "-c", "user.email=t@example.org", "-c", "user.name=t", "commit", "-qm", "nc fixture")
    record["recipe"]["git_commit"] = git(root, "rev-parse", "HEAD")
    env.reg.write_record(NC_NAME, VERSION, record)
    env.model = NC_NAME
    return env


@pytest.fixture
def nc_env(tmp_path: Path) -> ZooEnv:
    return make_nc_env(tmp_path)


def edit(env: ZooEnv, model=None, record=None) -> None:
    if model:
        data = env.reg.model_raw(env.model)
        model(data)
        write_model(env, env.model, data)
    if record:
        data = env.reg.record_raw(env.model, VERSION)
        record(data)
        env.reg.write_record(env.model, VERSION, data)


def bad_rules(gate) -> dict[int, str]:
    return {n: r for n, (s, r) in gate.results.items() if s == "FAIL"}


# ---- US1: an NC model passes and is marked everywhere (SC-001) ---------------------------------


def test_nc_fixture_passes_the_offline_gate(nc_env):
    gate = run_gate(nc_env)
    assert bad_rules(gate) == {}, gate.results


def test_nc_fixture_is_marked_on_card_hub_tag_and_record(nc_env):
    gate = run_gate(nc_env)
    card = gate.card
    front, body = cards.split_card(card)
    assert front["license"] == "cc-by-nc-4.0"
    top = body.split("## Summary")[0]
    assert "**Usage:** Non-commercial use only · licence CC-BY-NC-4.0 · because of dataset " \
           f"{NC_DATASET} (CC-BY-NC-4.0)." in top
    license_section = cards.sections(body)["License"]
    assert "Non-commercial use only" in license_section and NC_DATASET in license_section
    assert nc_env.reg.record_raw(NC_NAME, VERSION)["usage"] == NC_USAGE


def test_nc_share_alike_needs_the_nc_sa_licence(nc_env):
    declare(nc_env.root, [nc_dataset(licence="CC-BY-NC-SA-4.0")])
    usage = {"class": "non-commercial-share-alike", "licence": "CC-BY-NC-SA-4.0", "restricting_inputs": [
        {"kind": "dataset", "id": NC_DATASET, "licence": "CC-BY-NC-SA-4.0",
         "restriction": "non-commercial-share-alike"}]}
    edit(nc_env,
         model=lambda m: m.update(usage_class="non-commercial-share-alike", license="CC-BY-NC-SA-4.0"),
         record=lambda r: (r["provenance"].update(sources=[source(NC_DATASET, "CC-BY-NC-SA-4.0")]),
                           r.update(usage=usage)))
    assert failures(run_gate(nc_env), 6) == ""
    # CC-BY-NC-4.0 drops the share-alike term
    edit(nc_env, model=lambda m: m.update(usage_class="non-commercial", license="CC-BY-NC-4.0"))
    assert "makes the model non-commercial-share-alike" in failures(run_gate(nc_env), 6)


# ---- US2: hidden restrictions are refused (SC-002, SC-003) -------------------------------------


def as_commercial(env: ZooEnv) -> None:
    """Declare the NC fixture commercial (name without -nc is checked separately)."""
    edit(env, model=lambda m: m.update(usage_class="commercial", license="Apache-2.0",
                                       license_exception=None))


def test_name_suffix_rules(nc_env):
    as_commercial(nc_env)
    assert "C-K4: name ends in -nc but the model is declared commercial" in failures(
        run_gate(nc_env), 2)


def test_refused_nc_dataset_on_commercial_model(nc_env):
    as_commercial(nc_env)
    reason = failures(run_gate(nc_env), 6)
    assert f"C-K2: dataset {NC_DATASET} (CC-BY-NC-4.0) makes the model non-commercial" in reason


def test_refused_nc_base_model(nc_env):
    as_commercial(nc_env)
    edit(nc_env,
         model=lambda m: m.update(base_model="org/nc-base", base_model_license="CC-BY-NC-4.0"),
         record=lambda r: r["provenance"].update(sources=[]))
    assert "C-K2: base model org/nc-base (CC-BY-NC-4.0)" in failures(run_gate(nc_env), 6)


def test_refused_teacher_with_nc_only_outputs(nc_env):
    as_commercial(nc_env)
    teacher = {"model_id": "org/teacher", "license_basis": "terms: non-commercial training only",
               "training_on_outputs_permitted": True, "outputs_non_commercial": True}
    edit(nc_env, record=lambda r: (r["provenance"].update(sources=[], teachers=[teacher])))
    assert "C-K2: teacher org/teacher" in failures(run_gate(nc_env), 6)


def test_refused_third_party_runtime_model(nc_env):
    as_commercial(nc_env)
    register = {"models": [{
        "id": "org/encoder", "revision": "a" * 40, "remote_code": None, "weights_licence": "MIT",
        "training_data_named": True,
        "training_data": [{"name": "MS MARCO", "url": "https://microsoft.github.io/msmarco/",
                           "licence": "LicenseRef-MSMARCO-terms"}],
        "used_by": [], "owner": "o", "last_reviewed": "2026-10-10", "next_review": "2027-04-10"}]}
    (nc_env.root / "compliance" / "third-party-models.yaml").write_text(yaml.safe_dump(register))
    edit(nc_env, model=lambda m: m.update(runtime_models=["org/encoder"]),
         record=lambda r: r["provenance"].update(sources=[]))
    reason = failures(run_gate(nc_env), 6)
    assert "C-K2: third-party model org/encoder" in reason and "MS MARCO" in reason


def test_refused_output_of_nc_zoo_model(nc_env):
    as_commercial(nc_env)
    teacher_dir = nc_env.reg.model_dir("labeler-small-nc")
    teacher_dir.mkdir(parents=True)
    (teacher_dir / "model.yaml").write_text("usage_class: non-commercial\n")
    declare(nc_env.root, [nc_dataset(id="labels-v1", licence="CC-BY-4.0", commercial_use=False,
                                     produced_by="labeler-small-nc")])
    edit(nc_env, record=lambda r: r["provenance"].update(sources=[source("labels-v1", "CC-BY-4.0")]))
    reason = failures(run_gate(nc_env), 6)
    assert "C-K2: data produced by labeler-small-nc" in reason


@pytest.mark.parametrize("licence", ["CC-BY-NC-ND-4.0", "unknown", "LicenseRef-all-rights-reserved"])
@pytest.mark.parametrize("usage_class", ["commercial", "non-commercial"])
def test_inputs_that_forbid_training_are_refused_for_every_class(nc_env, licence, usage_class):
    edit(nc_env, record=lambda r: r["provenance"].update(sources=[
        {"origin": "https://example.org/data", "license": licence, "permitted_use": "training_allowed",
         "count": 3}]))
    if usage_class == "commercial":
        as_commercial(nc_env)
    assert "C-K1" in failures(run_gate(nc_env), 6)


def test_benchmark_only_source_is_refused(nc_env):
    edit(nc_env, record=lambda r: r["provenance"].update(sources=[
        source(NC_DATASET, "CC-BY-NC-4.0", use="benchmark_only")]))
    assert "benchmark_only" in failures(run_gate(nc_env), 7)


def test_missing_nc_suffix_is_refused(mcu_env):
    data = mcu_env.reg.model_raw(mcu_env.model)
    data.update(usage_class="non-commercial", license="CC-BY-NC-4.0", license_exception="owner's choice")
    write_model(mcu_env, mcu_env.model, data)
    assert "C-K4: name must be <name>-<variant>-nc" in failures(run_gate(mcu_env), 2)


def test_usage_class_never_changes_between_versions(nc_env):
    old = nc_env.reg.record_raw(NC_NAME, VERSION)
    old["usage"] = {**NC_USAGE, "class": "commercial"}
    nc_env.reg.write_record(NC_NAME, "0.0.9", {**old, "version": "0.0.9"})
    assert "C-K5: version 0.0.9 is commercial" in failures(run_gate(nc_env), 6)


def test_draft_record_without_usage_is_refused(nc_env):
    edit(nc_env, record=lambda r: r.pop("usage"))
    assert "C-K5: the release record lacks `usage`" in failures(run_gate(nc_env), 6)
