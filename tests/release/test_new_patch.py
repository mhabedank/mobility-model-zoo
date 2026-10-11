"""`zoo new-patch`: a patch release starts from a published version (feature 013)."""

from __future__ import annotations

import json

import pytest
from test_gate_rules import edit_record

from mobility_model_zoo.release import publish as ops
from mobility_model_zoo.release.errors import UsageError
from mobility_model_zoo.release.registry import dump_yaml, load_yaml

COMMIT = "c" * 40


def publish_it(env):
    edit_record(
        env,
        lambda r: r.update(
            published={"repo_commit": "a" * 40, "card_sha256": "b" * 64, "date": "2026-10-01"}
        ),
    )
    releases = env.reg.model_dir(env.model) / "releases"
    (releases / "0.1.0.ai-act.md").write_text(
        f"# {env.model} 0.1.0\n\nMinimal risk.\n", encoding="utf-8"
    )
    (releases / "0.1.0.compliance.yaml").write_text(
        dump_yaml(
            {
                "model": env.model,
                "version": "0.1.0",
                "state": "signed_off",
                "signed_off_by": "owner",
                "signed_off_at": "2026-10-01",
            }
        ),
        encoding="utf-8",
    )
    return releases


def patch(env, **kw):
    return ops.new_patch(env.reg, env.model, "0.1.0", "0.1.1", COMMIT, "Card only.", lambda line: None)


def test_new_patch_copies_the_record_and_results(zoo_env):
    publish_it(zoo_env)
    old = zoo_env.reg.record_raw(zoo_env.model, "0.1.0")
    patch(zoo_env)
    new = zoo_env.reg.record_raw(zoo_env.model, "0.1.1")
    assert new["version"] == "0.1.1" and new["change_type"] == "patch" and new["changes"] == "Card only."
    assert (
        new["recipe"]["git_commit"] == COMMIT and new["published"] is None and new["deprecated"] is None
    )
    assert (
        new["files"] == old["files"] and new["staging"] == old["staging"]
    )  # until `zoo stage` replaces them
    assert new["evaluation"]["results"] == "results/0.1.1/quality.json"
    assert new["performance"]["results"] == "results/0.1.1/performance.json"
    for kind in ("quality", "performance"):
        data = json.loads(zoo_env.reg.results_path(zoo_env.model, "0.1.1", kind).read_text())
        assert data.get("version", "0.1.1") == "0.1.1"
    assert zoo_env.reg.record_raw(zoo_env.model, "0.1.0")["published"]  # the old version is untouched


def test_new_patch_resets_the_sign_off_and_renames_the_companions(zoo_env):
    releases = publish_it(zoo_env)
    patch(zoo_env)
    compliance = load_yaml(releases / "0.1.1.compliance.yaml")
    assert compliance["version"] == "0.1.1" and compliance["state"] == "draft"
    assert compliance["signed_off_by"] is None and compliance["signed_off_at"] is None
    assert (
        "0.1.1" in (releases / "0.1.1.ai-act.md").read_text()
        and "0.1.0" not in (releases / "0.1.1.ai-act.md").read_text()
    )
    assert load_yaml(releases / "0.1.0.compliance.yaml")["state"] == "signed_off"  # the old record stays


def test_new_patch_refuses_an_unpublished_base(zoo_env):
    with pytest.raises(UsageError, match="not published"):
        patch(zoo_env)


def test_new_patch_refuses_an_older_version_and_an_existing_record(zoo_env):
    publish_it(zoo_env)
    with pytest.raises(UsageError, match="newer"):
        ops.new_patch(zoo_env.reg, zoo_env.model, "0.1.0", "0.1.0", COMMIT, "x", lambda line: None)
    patch(zoo_env)
    with pytest.raises(UsageError, match="exists already"):
        patch(zoo_env)
