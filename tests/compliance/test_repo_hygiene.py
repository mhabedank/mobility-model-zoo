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


def test_mcu_release_with_sbom_passes_c_g4(register_tree):
    root = _repo(register_tree)
    write(
        root, "zoo/models/m/releases/0.1.0.compliance.yaml", {"runtime": "mcu", "sbom": "sbom.cdx.json"}
    )
    reg = load(root)
    reg.stems["zoo/models/m/releases/0.1.0.compliance.yaml"] = "release-compliance"
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    assert "C-G4" not in {f.check_id for f in stage_repository(Context(reg))}


def test_release_compliance_schema_requires_sbom_for_mcu():
    import json
    from pathlib import Path

    from jsonschema import Draft202012Validator

    schema = json.loads(
        (
            Path(__file__).resolve().parents[2]
            / "src/mobility_model_zoo/compliance/schemas/release-compliance.schema.json"
        ).read_text()
    )
    errors = [e.message for e in Draft202012Validator(schema).iter_errors({"runtime": "mcu"})]
    assert any("'sbom' is a required property" in e for e in errors)
    errors = [
        e.message for e in Draft202012Validator(schema).iter_errors({"runtime": "mcu", "sbom": "s"})
    ]
    assert not any("sbom" in e for e in errors)


def test_tree_example_numbers_are_not_scanned_as_text(tmp_path):
    import json

    from mobility_model_zoo.compliance.release_checks import scan_text

    ex = {
        "source": "synthetic",
        "frames": [[0, 291, 8, [0] * 8]],
        "expected_scores": ["00000000"],
        "expected_alarms": [3],
    }
    p = tmp_path / "01.json"
    text = scan_text(p, json.dumps(ex))
    assert "expected_scores" not in text and "synthetic" in text
    ex["expected_scores"] = ["+49 170 1234567"]  # not a bit pattern: the whole file is scanned
    assert "+49 170" in scan_text(p, json.dumps(ex))
