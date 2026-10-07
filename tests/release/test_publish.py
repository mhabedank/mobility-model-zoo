"""init-model, stage, preview and publish against FakeHub (T023, T029, T030, T034)."""

from __future__ import annotations

import pytest
from conftest import FakeRunner, git
from typer.testing import CliRunner

from mobility_model_zoo.release import publish as ops
from mobility_model_zoo.release.cli import app
from mobility_model_zoo.release.errors import (
    ApprovalRefused,
    GateFailed,
    HubError,
    ImmutabilityRefused,
    UsageError,
)

PUBLIC = "mobility-model-zoo/sandbox-pipeline-tiny"
STAGING = "mobility-model-zoo/sandbox-pipeline-tiny-staging"
CONFIRM = "sandbox-pipeline-tiny/v0.1.0"


def quiet(line: str) -> None:
    pass


def verified(env, tmp_path):
    """Build and preview, as release-verify does."""
    out = tmp_path / "build"
    ops.build(env.reg, env.model, env.version, out, env.hub, FakeRunner(), quiet)
    ops.preview(env.reg, env.model, env.version, out, env.hub, quiet)
    env.hub.writes.clear()
    return out


def test_publish_creates_one_tagged_commit_in_a_private_sandbox_repo(zoo_env, tmp_path):
    verified(zoo_env, tmp_path)
    commit = ops.publish(zoo_env.reg, zoo_env.model, zoo_env.version, CONFIRM, zoo_env.hub, quiet)
    repo = zoo_env.hub.repos[PUBLIC]
    assert repo.private is True
    assert repo.tags == {"v0.1.0": commit}
    assert set(repo.commits[commit]) == {"README.md", "config.json", "model.safetensors"}
    assert [w for w in zoo_env.hub.writes if w.startswith("commit")] == [
        f"commit {PUBLIC}@main ['README.md', 'config.json', 'model.safetensors']"
    ]
    assert zoo_env.record()["published"]["repo_commit"] == commit
    assert zoo_env.hub.collections == {}  # sandbox models are never in a collection
    assert "sandbox-pipeline-tiny" not in (zoo_env.root / "zoo/MODELS.md").read_text()


def test_second_publish_is_refused_and_changes_nothing(zoo_env, tmp_path):
    verified(zoo_env, tmp_path)
    ops.publish(zoo_env.reg, zoo_env.model, zoo_env.version, CONFIRM, zoo_env.hub, quiet)
    before = {k: dict(v.commits) for k, v in zoo_env.hub.repos.items()}
    zoo_env.hub.writes.clear()
    with pytest.raises(ImmutabilityRefused):
        ops.publish(zoo_env.reg, zoo_env.model, zoo_env.version, CONFIRM, zoo_env.hub, quiet)
    assert zoo_env.hub.writes == []
    assert {k: dict(v.commits) for k, v in zoo_env.hub.repos.items()} == before


def test_wrong_confirm_is_refused_before_any_write(zoo_env, tmp_path):
    verified(zoo_env, tmp_path)
    with pytest.raises(ApprovalRefused):
        ops.publish(
            zoo_env.reg,
            zoo_env.model,
            zoo_env.version,
            "sandbox-pipeline-tiny/v9.9.9",
            zoo_env.hub,
            quiet,
        )
    assert zoo_env.hub.writes == []


def test_missing_preview_is_refused(zoo_env):
    with pytest.raises(ApprovalRefused, match="no reviewed preview"):
        ops.publish(zoo_env.reg, zoo_env.model, zoo_env.version, CONFIRM, zoo_env.hub, quiet)
    assert zoo_env.hub.writes == []


def test_preview_from_another_commit_is_refused(zoo_env, tmp_path):
    verified(zoo_env, tmp_path)
    (zoo_env.root / "other.txt").write_text("x")
    git(zoo_env.root, "-c", "user.email=t@example.org", "-c", "user.name=t", "add", "-A")
    git(zoo_env.root, "-c", "user.email=t@example.org", "-c", "user.name=t", "commit", "-qm", "later")
    with pytest.raises(ApprovalRefused, match="tag commit"):
        ops.publish(zoo_env.reg, zoo_env.model, zoo_env.version, CONFIRM, zoo_env.hub, quiet)
    assert zoo_env.hub.writes == []


def test_tampered_preview_card_is_refused(zoo_env, tmp_path):
    verified(zoo_env, tmp_path)
    bad = tmp_path / "README.md"
    bad.write_text("# tampered\n")
    zoo_env.hub.commit(STAGING, {"README.md": bad}, "tamper", branch="rc-v0.1.0")
    zoo_env.hub.writes.clear()
    with pytest.raises(ApprovalRefused, match="does not match build.json"):
        ops.publish(zoo_env.reg, zoo_env.model, zoo_env.version, CONFIRM, zoo_env.hub, quiet)
    assert zoo_env.hub.writes == []


def test_preview_model_file_differing_from_the_record_is_refused(zoo_env, tmp_path):
    verified(zoo_env, tmp_path)
    bad = tmp_path / "model.safetensors"
    bad.write_bytes(b"other weights")
    zoo_env.hub.commit(STAGING, {"model.safetensors": bad}, "tamper", branch="rc-v0.1.0")
    zoo_env.hub.writes.clear()
    with pytest.raises(ApprovalRefused, match="model.safetensors"):
        ops.publish(zoo_env.reg, zoo_env.model, zoo_env.version, CONFIRM, zoo_env.hub, quiet)
    assert zoo_env.hub.writes == []


def test_publish_never_rebuilds_or_runs_the_model(zoo_env, tmp_path, monkeypatch):
    verified(zoo_env, tmp_path)

    def boom(*args, **kwargs):
        raise AssertionError("publish must not render or run the model")

    monkeypatch.setattr(ops, "build", boom)
    monkeypatch.setattr("mobility_model_zoo.release.card.render", boom)
    ops.publish(zoo_env.reg, zoo_env.model, zoo_env.version, CONFIRM, zoo_env.hub, quiet)


def test_failure_after_commit_then_rerun_only_tags(zoo_env, tmp_path):
    verified(zoo_env, tmp_path)
    zoo_env.hub.fail["create_tag"] = HubError("network down")
    with pytest.raises(HubError):
        ops.publish(zoo_env.reg, zoo_env.model, zoo_env.version, CONFIRM, zoo_env.hub, quiet)
    assert zoo_env.record()["published"] is None
    commits_after_failure = len(zoo_env.hub.repos[PUBLIC].commits)
    commit = ops.publish(zoo_env.reg, zoo_env.model, zoo_env.version, CONFIRM, zoo_env.hub, quiet)
    assert len(zoo_env.hub.repos[PUBLIC].commits) == commits_after_failure
    assert zoo_env.hub.repos[PUBLIC].tags == {"v0.1.0": commit}


def test_sandbox_repo_that_became_public_blocks_publish(zoo_env, tmp_path):
    verified(zoo_env, tmp_path)
    zoo_env.hub.repos[PUBLIC] = type(zoo_env.hub.repos[STAGING])(private=False)
    with pytest.raises(GateFailed) as exc:
        ops.publish(zoo_env.reg, zoo_env.model, zoo_env.version, CONFIRM, zoo_env.hub, quiet)
    assert any(f.startswith("rule 14:") for f in exc.value.failures)
    assert zoo_env.hub.repos[PUBLIC].private is False  # never changed by the tool


def test_missing_token_exits_5(zoo_env, monkeypatch):
    monkeypatch.chdir(zoo_env.root)
    monkeypatch.delenv("HF_RELEASE_TOKEN", raising=False)
    result = CliRunner().invoke(app, ["publish", zoo_env.model, zoo_env.version, "--confirm", CONFIRM])
    assert result.exit_code == 5
    assert "HF_RELEASE_TOKEN" in result.output


# ---- init-model and stage ----------------------------------------------------------------------
def test_init_model_creates_a_private_staging_repo(zoo_env):
    del zoo_env.hub.repos[STAGING]
    ops.init_model(zoo_env.reg, zoo_env.model, zoo_env.hub, quiet)
    assert zoo_env.hub.repos[STAGING].private is True


def test_init_model_refuses_a_public_staging_repo(zoo_env):
    zoo_env.hub.repos[STAGING].private = False
    with pytest.raises(GateFailed):
        ops.init_model(zoo_env.reg, zoo_env.model, zoo_env.hub, quiet)


def test_stage_uploads_and_records_checksums(zoo_env, tmp_path):
    src = tmp_path / "trained"
    src.mkdir()
    (src / "model.safetensors").write_bytes(b"weights-v2")
    (src / "config.json").write_bytes(b"{}")
    zoo_env.reg.record_path(zoo_env.model, "0.2.0").unlink(missing_ok=True)
    revision = ops.stage(zoo_env.reg, zoo_env.model, "0.2.0", src, zoo_env.hub, quiet)
    record = zoo_env.reg.record_raw(zoo_env.model, "0.2.0")
    assert record["staging"]["revision"] == revision
    assert [f["path"] for f in record["files"]] == ["config.json", "model.safetensors"]
    assert record["changes"] == ""  # left for the owner; the schema rejects it until filled in


def test_stage_never_creates_repos(zoo_env, tmp_path):
    del zoo_env.hub.repos[STAGING]
    src = tmp_path / "trained"
    src.mkdir()
    (src / "model.safetensors").write_bytes(b"w")
    with pytest.raises(UsageError, match="init-model"):
        ops.stage(zoo_env.reg, zoo_env.model, "0.2.0", src, zoo_env.hub, quiet)
    assert STAGING not in zoo_env.hub.repos


@pytest.mark.parametrize("bad", ["data/chunks.jsonl", ".env", "labels.jsonl", "README.md"])
def test_stage_refuses_forbidden_files(zoo_env, tmp_path, bad):
    src = tmp_path / "trained"
    (src / bad).parent.mkdir(parents=True, exist_ok=True)
    (src / bad).write_bytes(b"x")
    zoo_env.hub.writes.clear()
    with pytest.raises(GateFailed):
        ops.stage(zoo_env.reg, zoo_env.model, "0.2.0", src, zoo_env.hub, quiet)
    assert zoo_env.hub.writes == []


def test_failure_after_tagging_then_rerun_finishes(zoo_env, tmp_path, monkeypatch):
    """A run that fails after the tag (here: writing the record; in 0.1.0 of scout-large: adding the
    collection) is resumed: no new commit, no second tag, record and index are written."""
    verified(zoo_env, tmp_path)
    write_record = zoo_env.reg.write_record
    calls = {"n": 0}

    def flaky(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise HubError("collection refused")
        return write_record(*args, **kwargs)

    monkeypatch.setattr(zoo_env.reg, "write_record", flaky)
    with pytest.raises(HubError):
        ops.publish(zoo_env.reg, zoo_env.model, zoo_env.version, CONFIRM, zoo_env.hub, quiet)
    tags_after_failure = dict(zoo_env.hub.repos[PUBLIC].tags)
    commits_after_failure = len(zoo_env.hub.repos[PUBLIC].commits)
    commit = ops.publish(zoo_env.reg, zoo_env.model, zoo_env.version, CONFIRM, zoo_env.hub, quiet)
    assert zoo_env.hub.repos[PUBLIC].tags == tags_after_failure == {"v0.1.0": commit}
    assert len(zoo_env.hub.repos[PUBLIC].commits) == commits_after_failure
    assert zoo_env.record()["published"]["repo_commit"] == commit


def test_existing_tag_on_another_commit_still_fails(zoo_env, tmp_path):
    verified(zoo_env, tmp_path)
    zoo_env.hub.create_repo(PUBLIC, private=True)
    zoo_env.hub.repos[PUBLIC].tags["v0.1.0"] = "deadbeef"
    with pytest.raises(ImmutabilityRefused, match="tag v0.1.0 already exists"):
        ops.publish(zoo_env.reg, zoo_env.model, zoo_env.version, CONFIRM, zoo_env.hub, quiet)
