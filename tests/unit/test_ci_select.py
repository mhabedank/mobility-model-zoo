"""Test selection of the CI (scripts/ci/select_tests.py)."""

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("select_tests", ROOT / "scripts/ci/select_tests.py")
sel = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = sel  # dataclasses look the module up
spec.loader.exec_module(sel)


def test_every_tracked_file_has_a_rule():
    files = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.splitlines()
    unmatched = [f for f in files if sel.area_of(f) is None]
    assert not unmatched, f"add these to RULES in scripts/ci/select_tests.py: {unmatched[:20]}"


def test_every_area_test_path_exists():
    for area in sel.AREAS.values():
        for p in area.tests:
            assert (ROOT / p).exists(), p
    for p in sel.GUARDS:
        assert (ROOT / p).is_file(), p


def test_website_change_runs_website_tests_only():
    s = sel.select(["zoo/site.yaml", "src/mobility_model_zoo/site/templates/start.html.j2"])
    assert s.tests == ("tests/release/test_gate_site_text.py", "tests/website")
    assert not s.torch and not s.edge


def test_docs_change_runs_no_tests():
    s = sel.select(["README.md", "docs/website.md", "specs/008-zoo-website/spec.md",
                    "topics/security/research/notes.md"])
    assert s.tests == () and not s.torch and not s.edge


def test_jtbd_change_needs_torch_but_no_firmware():
    s = sel.select(["src/mobility_model_zoo/productdev/jtbd/span/model.py"])
    assert "tests/unit" in s.tests and "tests/integration" in s.tests
    assert s.torch and not s.edge


def test_edge_change_runs_firmware_jobs_and_dependents():
    s = sel.select(["firmware/bench/src/main.cpp"])
    assert s.edge and not s.torch
    assert {"tests/edge", "tests/security", "tests/release"} <= set(s.tests)


def test_security_change_runs_no_firmware_jobs():
    s = sel.select(["src/mobility_model_zoo/security/can_ids/features.py"])
    assert s.tests == ("tests/security", "tests/unit/test_task_configs.py")
    assert not s.edge and not s.torch


def test_core_change_runs_all_tests_without_firmware():
    s = sel.select(["src/mobility_model_zoo/release/gate.py"])
    assert s.tests == ("tests",) and s.torch and not s.edge


def test_dependencies_and_unknown_files_run_everything():
    for f in ("uv.lock", ".github/workflows/ci.yml", "something/new.txt"):
        s = sel.select([f])
        assert s.tests == ("tests",) and s.torch and s.edge, f


def test_topic_compliance_records_are_core():
    assert sel.area_of("topics/productdev/compliance/sources.yaml") == "core"
    assert sel.area_of("topics/productdev/compliance/README.md") == "core"
