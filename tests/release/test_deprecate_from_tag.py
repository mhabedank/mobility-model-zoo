"""Re-rendering a published version reads model.yaml at its tag (feature 005, R14)."""

import subprocess

import yaml

from mobility_model_zoo.release.card import model_at_tag


class Reg:
    def __init__(self, root):
        self.root = root


def git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def test_model_at_tag_keeps_old_figure_paths(tmp_path):
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "t@example.org")
    git(tmp_path, "config", "user.name", "t")
    path = tmp_path / "zoo/models/m-x/model.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump({"name": "m-x", "card": {"figures": [{"path": "docs/f.png"}]}}))
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "v0.1.0")
    git(tmp_path, "tag", "m-x/v0.1.0")
    path.write_text(yaml.safe_dump({"name": "m-x", "card": {"figures": [{"path": "topics/t/f.png"}]}}))
    git(tmp_path, "commit", "-qam", "move")
    old = model_at_tag(Reg(tmp_path), "m-x", "0.1.0")
    assert old["card"]["figures"][0]["path"] == "docs/f.png"
    assert model_at_tag(Reg(tmp_path), "m-x", "9.9.9") is None
