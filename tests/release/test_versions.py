"""Version rules, version history, deprecation and audit (T053)."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil

import pytest
from conftest import FakeRunner

from mobility_model_zoo.release import audit
from mobility_model_zoo.release import publish as ops
from mobility_model_zoo.release.errors import GateFailed, ImmutabilityRefused
from mobility_model_zoo.release.gate import Gate

PUBLIC = "mobility-model-zoo/sandbox-pipeline-tiny"
STAGING = "mobility-model-zoo/sandbox-pipeline-tiny-staging"


def quiet(line: str) -> None:
    pass


def release(env, tmp_path, version: str) -> str:
    out = tmp_path / f"build-{version}"
    ops.build(env.reg, env.model, version, out, env.hub, FakeRunner(), quiet)
    ops.preview(env.reg, env.model, version, out, env.hub, quiet)
    return ops.publish(env.reg, env.model, version, f"{env.model}/v{version}", env.hub, quiet)


def new_version(
    env,
    version: str,
    change_type: str,
    weights: bytes | None = b"fake-weights-v2\n",
    item_f1: float = 0.6,
    output_format: str = "sandbox-v1",
) -> None:
    """Record, results and staged files for a new version, derived from 0.1.0."""
    record = copy.deepcopy(env.record("0.1.0"))
    record.update(
        version=version,
        change_type=change_type,
        changes=f"Version {version}.",
        output_format_version=output_format,
        published=None,
        status="experimental",
    )
    record["evaluation"]["results"] = f"results/{version}/quality.json"
    record["performance"]["results"] = f"results/{version}/performance.json"
    if weights is not None:
        revision = env.hub.seed(STAGING, {"model.safetensors": weights})
        record["staging"]["revision"] = revision
        for f in record["files"]:
            if f["path"] == "model.safetensors":
                f.update(sha256=hashlib.sha256(weights).hexdigest(), size_bytes=len(weights))
    env.set_record(record, version)
    src = env.reg.model_dir(env.model) / "results" / "0.1.0"
    dst = env.reg.model_dir(env.model) / "results" / version
    shutil.copytree(src, dst)
    for kind in ("quality", "performance"):
        path = dst / f"{kind}.json"
        data = json.loads(path.read_text())
        data["version"] = version
        if kind == "quality":
            data["metrics"][0]["value"] = item_f1
        path.write_text(json.dumps(data, indent=2))


def gate_failures(env, version: str) -> list[str]:
    try:
        Gate(env.reg, env.model, version, only={3}).run(quiet)
    except GateFailed as e:
        return e.failures
    return []


def test_change_type_rules(zoo_env, tmp_path):
    release(zoo_env, tmp_path, "0.1.0")
    new_version(zoo_env, "0.1.1", "patch")  # new weights in a patch
    assert any("must not change the model files" in f for f in gate_failures(zoo_env, "0.1.1"))
    new_version(zoo_env, "0.2.0", "initial")
    assert any("initial only for the first version" in f for f in gate_failures(zoo_env, "0.2.0"))
    new_version(zoo_env, "0.3.0", "major")
    assert any("is minor" in f for f in gate_failures(zoo_env, "0.3.0"))
    new_version(zoo_env, "0.1.2", "patch", weights=None, item_f1=0.5, output_format="sandbox-v2")
    assert any("at least a minor version" in f for f in gate_failures(zoo_env, "0.1.2"))
    new_version(zoo_env, "0.4.0", "minor")
    assert gate_failures(zoo_env, "0.4.0") == []


def test_second_version_keeps_the_first_and_shows_history(zoo_env, tmp_path):
    first = release(zoo_env, tmp_path, "0.1.0")
    new_version(zoo_env, "0.2.0", "minor")
    second = release(zoo_env, tmp_path, "0.2.0")
    repo = zoo_env.hub.repos[PUBLIC]
    assert repo.tags == {"v0.1.0": first, "v0.2.0": second}
    assert repo.branches["main"] == second
    assert zoo_env.hub.files_at(PUBLIC, "v0.1.0")["model.safetensors"] == b"fake-weights-v1\n"
    assert zoo_env.hub.files_at(PUBLIC, "main")["model.safetensors"] == b"fake-weights-v2\n"
    card = zoo_env.hub.files_at(PUBLIC, "main")["README.md"].decode()
    history = card.split("## Version history", 1)[1].split("## License", 1)[0]
    assert "| 0.2.0 | 2026-10-01 | experimental | minor | Version 0.2.0. | 0.6 |" in history
    assert "| 0.1.0 | 2026-10-01 | experimental | initial | First test release. | 0.5 |" in history


def test_older_version_after_newer_is_refused(zoo_env, tmp_path):
    release(zoo_env, tmp_path, "0.1.0")
    new_version(zoo_env, "0.3.0", "minor")
    release(zoo_env, tmp_path, "0.3.0")
    new_version(zoo_env, "0.2.0", "minor")
    with pytest.raises(ImmutabilityRefused):
        Gate(zoo_env.reg, zoo_env.model, "0.2.0", hub=zoo_env.hub, only={4}).run(quiet)


def test_deprecate_older_version_changes_only_its_history_row(zoo_env, tmp_path):
    release(zoo_env, tmp_path, "0.1.0")
    new_version(zoo_env, "0.2.0", "minor")
    release(zoo_env, tmp_path, "0.2.0")
    tags_before = dict(zoo_env.hub.repos[PUBLIC].tags)
    ops.deprecate(zoo_env.reg, zoo_env.model, "0.1.0", "Wrong thresholds.", "0.2.0", zoo_env.hub, quiet)
    record = zoo_env.record("0.1.0")
    assert record["status"] == "deprecated" and record["deprecated"]["successor"] == "0.2.0"
    assert zoo_env.hub.repos[PUBLIC].tags == tags_before
    files_main = zoo_env.hub.files_at(PUBLIC, "main")
    assert files_main["model.safetensors"] == b"fake-weights-v2\n"
    card = files_main["README.md"].decode()
    assert "Deprecated." not in card
    assert "| 0.1.0 | 2026-10-01 | deprecated |" in card
    assert '"run":' in card  # example outputs kept


def test_deprecate_latest_version_shows_the_banner(zoo_env, tmp_path):
    release(zoo_env, tmp_path, "0.1.0")
    ops.deprecate(zoo_env.reg, zoo_env.model, "0.1.0", "Broken.", None, zoo_env.hub, quiet)
    card = zoo_env.hub.files_at(PUBLIC, "main")["README.md"].decode()
    assert "> **Pipeline test model.**" in card  # sandbox banner wins; deprecation is in the history
    assert "| 0.1.0 | 2026-10-01 | deprecated |" in card


def test_audit_detects_moved_tags_and_public_staging(zoo_env, tmp_path):
    release(zoo_env, tmp_path, "0.1.0")
    audit.run(zoo_env.reg, None, zoo_env.hub, quiet)
    zoo_env.hub.repos[PUBLIC].tags["v0.1.0"] = "9" * 40
    with pytest.raises(GateFailed, match="points to"):
        audit.run(zoo_env.reg, None, zoo_env.hub, quiet)
    zoo_env.hub.repos[PUBLIC].tags["v0.1.0"] = zoo_env.record()["published"]["repo_commit"]
    zoo_env.hub.repos[STAGING].private = False
    with pytest.raises(GateFailed, match="staging repos must be private"):
        audit.run(zoo_env.reg, None, zoo_env.hub, quiet)
