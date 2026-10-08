"""Repository stage (C-G1, C-G2, C-G4, C-G5) on a temporary git repository."""

import subprocess

from compliance_helpers import load, write

from mobility_model_zoo.compliance.checks import Context
from mobility_model_zoo.compliance.release_checks import REQUIRED_FILES, stage_repository


def _repo(root):
    for name in REQUIRED_FILES:
        (root / name).write_text("text\n")
    (root / "README.md").write_text("Questions: privacy@example.org\n")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


def ids(root):
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    return {f.check_id for f in stage_repository(Context(load(root)))}


def test_clean_repo_passes(register_tree):
    assert ids(_repo(register_tree)) == set()


def test_missing_security_policy(register_tree):
    root = _repo(register_tree)
    (root / "SECURITY.md").unlink()
    assert ids(root) == {"C-G1"}


def test_funding_and_branding(register_tree):
    root = _repo(register_tree)
    write(root, ".github/FUNDING.yml", {"github": ["someone"]})
    assert "C-G2" in ids(root)
    (root / ".github/FUNDING.yml").unlink()
    (root / "docs.md").write_text("We offer consulting services.\n")
    assert ids(root) == {"C-G2"}
    (root / "docs.md").write_text("A project by Miskatonic Analytics.\n")
    assert ids(root) == {"C-G2"}


def test_personal_data_in_committed_file(register_tree):
    root = _repo(register_tree)
    (root / "notes.md").write_text("Write to erika.mustermann@posteo.de or call 030 12345678.\n")
    assert ids(root) == {"C-G5"}


def test_mcu_release_without_sbom(register_tree):
    root = _repo(register_tree)
    write(root, "zoo/models/m/releases/0.1.0.compliance.yaml", {"runtime": "mcu"})
    reg = load(root)
    reg.stems["zoo/models/m/releases/0.1.0.compliance.yaml"] = "release-compliance"
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    assert "C-G4" in {f.check_id for f in stage_repository(Context(reg))}
