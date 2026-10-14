"""Test selection of the CI (scripts/ci/select_tests.py)."""

import importlib.util
import re
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
    # pyproject.toml, uv.lock and ci.yml are judged by their content (feature 017)
    unmatched = [f for f in files if sel.area_of(f) is None and f not in sel.CONTENT_SENSITIVE]
    assert not unmatched, f"add these to RULES in scripts/ci/select_tests.py: {unmatched[:20]}"


def test_every_area_test_path_exists():
    for area in sel.AREAS.values():
        for p in area.tests:
            assert (ROOT / p).exists(), p
    for p in sel.GUARDS:
        assert (ROOT / p).is_file(), p


def test_website_change_runs_website_tests_only():
    s = sel.select(["zoo/site.yaml", "src/mobility_model_zoo/site/templates/start.html.j2"])
    # rules 17 and 18 of the release gate use the site checks (features 008 and 014)
    assert s.tests == (
        "tests/release/test_gate_site_text.py",
        "tests/release/test_rule18.py",
        "tests/website",
    )
    assert not s.torch and not s.edge


def test_release_schema_contract_runs_the_release_tests():
    """The packaged schemas must equal the contract copy (tests/release/test_schemas.py)."""
    s = sel.select(["specs/014-model-page-layout/contracts/release/model.schema.json"])
    assert s.tests == ("tests/release",)


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
    # Without revisions (--files) the content-sensitive files cannot be compared and fail safe.
    for f in ("uv.lock", "pyproject.toml", ".github/workflows/ci.yml", "something/new.txt"):
        s = sel.select([f])
        assert s.tests == ("tests",) and s.torch and s.edge, f


def test_topic_compliance_records_are_core():
    assert sel.area_of("topics/productdev/compliance/sources.yaml") == "core"
    assert sel.area_of("topics/productdev/compliance/README.md") == "core"


# --- Feature 017: content-sensitive files, firmware install set, reasons -------------------------

FIX = ROOT / "tests/fixtures/ci-select"
LOCK = (FIX / "uv-base.lock").read_text(encoding="utf-8")
MANIFEST = (FIX / "pyproject-base.toml").read_text(encoding="utf-8")
WORKFLOW = (FIX / "ci-base.yml").read_text(encoding="utf-8")
CI = ".github/workflows/ci.yml"


def changed(base, old, new):
    """`base` with one replacement; a fixture typo fails loudly instead of passing silently."""
    assert old in base, old
    return base.replace(old, new, 1)


def reader(changes):
    """Base revision B holds the fixtures, head revision H the fixtures with `changes` applied."""
    base = {"uv.lock": LOCK, "pyproject.toml": MANIFEST, CI: WORKFLOW}
    head = {**base, **changes}

    def read(rev, path):
        return (base if rev == "B" else head).get(path)

    return read


def run(files, read):
    return sel.select(files, base="B", head="H", read=read)


def areas(s):
    return set(s.areas)


def test_content_sensitive_without_revisions_fails_safe():
    for f in ("uv.lock", "pyproject.toml", CI):
        s = sel.select([f])
        assert s.edge and s.tests == ("tests",), f
        assert "cannot compare" in s.areas["all"][0].reason


def test_content_sensitive_file_added_or_removed_fails_safe():
    s = sel.select(["uv.lock"], base="B", head="H", read=lambda rev, path: None)
    assert s.edge and areas(s) == {"all"}


# lock file (US1) -----------------------------------------------------------------------------------

WEBSITE_EXTRA_LOCK = changed(
    LOCK,
    'jtbd = [\n',
    'images = [\n    { name = "opencv-python-headless" },\n]\njtbd = [\n',
) + """
[[package]]
name = "opencv-python-headless"
version = "4.10.0"
source = { registry = "https://pypi.org/simple" }
dependencies = [
    { name = "numpy" },
]
"""


def test_firmware_install_set_follows_extras_groups_and_requested_extras():
    names = {n for n, _, _ in sel.firmware_install_set(LOCK)}
    assert names == {"numpy", "esptool", "esp-pylib", "click", "platformio", "pytest"}


def test_lock_website_extra_runs_no_firmware():
    s = run(["uv.lock"], reader({"uv.lock": WEBSITE_EXTRA_LOCK}))
    assert not s.edge and areas(s) == {"core"}


def test_lock_shared_package_bump_runs_firmware_with_reason():
    head = changed(LOCK, 'name = "numpy"\nversion = "2.1.0"', 'name = "numpy"\nversion = "2.1.3"')
    s = run(["uv.lock"], reader({"uv.lock": head}))
    assert s.edge and areas(s) == {"core", "edge"}
    assert s.areas["edge"][0].reason == "numpy 2.1.0 → 2.1.3 (firmware install set)"


def test_lock_torch_bump_runs_no_firmware():
    head = changed(LOCK, 'version = "2.5.0"', 'version = "2.5.1"')
    s = run(["uv.lock"], reader({"uv.lock": head}))
    assert not s.edge


def test_lock_change_reached_only_through_a_requested_extra_runs_firmware():
    head = changed(LOCK, 'version = "8.1.7"', 'version = "8.1.8"')
    s = run(["uv.lock"], reader({"uv.lock": head}))
    assert s.edge and "click 8.1.7 → 8.1.8" in s.areas["edge"][0].reason


def test_lock_unparsable_fails_safe():
    s = run(["uv.lock"], reader({"uv.lock": "not = [toml"}))
    assert s.edge and areas(s) == {"all"}


# manifest (US1) ------------------------------------------------------------------------------------


def manifest_case(old, new):
    return run(["pyproject.toml"], reader({"pyproject.toml": changed(MANIFEST, old, new)}))


def test_manifest_website_extra_is_images_not_firmware():
    s = manifest_case('catalog = ["pyyaml>=6.0"]', 'catalog = ["pyyaml>=6.0"]\nimages = ["pillow>=10"]')
    assert areas(s) == {"images"} and not s.edge
    assert s.areas["images"][0].reason == "project.optional-dependencies.images changed"


def test_manifest_edge_extra_runs_firmware():
    s = manifest_case('edge = ["esptool>=4.8"]', 'edge = ["esptool>=4.9"]')
    assert areas(s) == {"edge"} and s.edge


def test_manifest_shared_runtime_runs_everything():
    for old, new in (
        ('edge = "mobility_model_zoo.edge.cli:main"', 'edge = "mobility_model_zoo.edge.main:run"'),
        ('requires-python = ">=3.12"', 'requires-python = ">=3.13"'),
        ('dependencies = ["numpy>=2.0"]', 'dependencies = ["numpy>=2.1"]'),
        ('dev = ["pytest>=8.3"]', 'dev = ["pytest>=8.4"]'),
    ):
        s = manifest_case(old, new)
        assert areas(s) == {"all"} and s.edge, old


def test_manifest_site_check_group_is_images():
    s = manifest_case('site-check = ["playwright>=1.47"]', 'site-check = ["playwright>=1.48"]')
    assert areas(s) == {"images"} and not s.edge


def test_manifest_lint_settings_are_docs_and_unknown_tables_core():
    assert areas(manifest_case("line-length = 100", "line-length = 110")) == {"docs"}
    s = manifest_case("[tool.ruff]", "[tool.mypy]\nstrict = true\n\n[tool.ruff]")
    assert areas(s) == {"core"} and not s.edge


def test_manifest_unparsable_fails_safe():
    s = run(["pyproject.toml"], reader({"pyproject.toml": "[project\n"}))
    assert s.edge and areas(s) == {"all"}


def test_pr35_dependencies_run_no_firmware():
    """Pull request #35 without its selector edit: website files, an `images` extra, a lock change."""
    manifest = changed(MANIFEST, 'catalog = ["pyyaml>=6.0"]',
                       'catalog = ["pyyaml>=6.0"]\nimages = ["opencv-python-headless>=4.10"]')
    files = ["zoo/site.yaml", "src/mobility_model_zoo/site/build.py", "pyproject.toml", "uv.lock"]
    s = run(files, reader({"pyproject.toml": manifest, "uv.lock": WEBSITE_EXTRA_LOCK}))
    # every lock change runs all Python tests (research R2); only the firmware jobs stay off
    assert not s.edge and s.tests == ("tests",)


def test_firmware_install_set_matches_ci_jobs():
    """The firmware jobs' `uv sync` flags equal FIRMWARE_EXTRAS and FIRMWARE_SKIP (research R8)."""
    blocks = sel.workflow_blocks((ROOT / CI).read_text(encoding="utf-8"))
    extras, skip = set(), set()
    for job in ("edge-sim", "edge-qemu"):
        for line in blocks[job].splitlines():
            if "uv sync" in line:
                extras |= set(re.findall(r"--extra\s+(\S+)", line))
                skip |= set(re.findall(r"--no-install-package\s+(\S+)", line))
    assert extras == set(sel.FIRMWARE_EXTRAS)
    assert skip == set(sel.FIRMWARE_SKIP)


# workflow and selector (US2) -----------------------------------------------------------------------


def test_workflow_blocks_splits_real_ci_yml():
    blocks = sel.workflow_blocks((ROOT / CI).read_text(encoding="utf-8"))
    assert set(blocks) == {"<header>", "changes", "checks", "test", "edge-sim", "edge-qemu"}


def test_workflow_comment_belongs_to_the_next_job():
    blocks = sel.workflow_blocks(WORKFLOW)
    assert "# Emulated board." in blocks["edge-qemu"]
    assert "# Emulated board." not in blocks["edge-sim"]


def workflow_case(old, new):
    return run([CI], reader({CI: changed(WORKFLOW, old, new)}))


def test_workflow_test_job_edit_runs_no_firmware():
    s = workflow_case("pytest -q tests", "pytest -q -x tests")
    assert areas(s) == {"core"} and not s.edge
    assert s.areas["core"][0].reason == "job test changed"


def test_workflow_firmware_job_edit_runs_firmware():
    s = workflow_case("esp-develop-9.2.2-20250817", "esp-develop-9.2.3-20251001")
    assert areas(s) == {"edge"} and s.edge


def test_workflow_header_selector_job_and_new_job_run_everything():
    for old, new in (
        ("  pull_request:\n", "  pull_request:\n  workflow_dispatch:\n"),
        ("select_tests.py --all", "select_tests.py --all --reason x"),
        ("  # Native simulator.", "  lint:\n    runs-on: ubuntu-latest\n\n  # Native simulator."),
    ):
        s = workflow_case(old, new)
        assert "all" in areas(s) and s.edge, old


def test_workflow_without_jobs_fails_safe():
    s = run([CI], reader({CI: "name: ci\non: push\n"}))
    assert areas(s) == {"all"} and s.edge


def test_selector_change_runs_no_firmware():
    s = sel.select(["scripts/ci/select_tests.py", "tests/unit/test_ci_select.py",
                    "tests/fixtures/ci-select/uv-base.lock"])
    assert s.tests == () and not s.edge and not s.torch


def test_selector_change_with_firmware_file_runs_firmware():
    s = sel.select(["scripts/ci/select_tests.py", "firmware/bench/src/main.cpp"])
    assert s.edge


def test_pr35_website_extra_runs_no_firmware():
    """FR-009: the full pull request #35 case, including its edit of the selector."""
    manifest = changed(MANIFEST, 'catalog = ["pyyaml>=6.0"]',
                       'catalog = ["pyyaml>=6.0"]\nimages = ["opencv-python-headless>=4.10"]')
    files = ["zoo/site.yaml", "src/mobility_model_zoo/site/build.py", "scripts/imagery/gen.py",
             "pyproject.toml", "uv.lock", "scripts/ci/select_tests.py"]
    s = run(files, reader({"pyproject.toml": manifest, "uv.lock": WEBSITE_EXTRA_LOCK}))
    assert not s.edge and s.tests == ("tests",)
    assert {"site", "images", "core", "ci-select"} == set(s.areas)


# main pushes and the weekly run (US3) --------------------------------------------------------------


def test_ci_events_are_selected():
    text = (ROOT / CI).read_text(encoding="utf-8")
    assert "cron: '17 3 * * 1'" in text
    step = sel.workflow_blocks(text)["changes"]
    for event in ("pull_request)", "push)", "*)"):
        assert event in step, event
    assert "BEFORE: ${{ github.event.before }}" in step
    assert '--diff "$BEFORE" HEAD' in step
    assert "${{ github.event.before }}" not in step.split("run: |", 1)[1]  # no inline expression
    assert step.count("--all") >= 3  # fallbacks: no merge commit, no previous head, other events


# reasons in the summary (US4) ----------------------------------------------------------------------


def summary(s, tmp_path, monkeypatch, capsys):
    out = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(out))
    sel.report(s)
    stdout = capsys.readouterr().out.splitlines()
    return stdout, out.read_text(encoding="utf-8").splitlines()


def test_summary_names_the_firmware_trigger(tmp_path, monkeypatch, capsys):
    stdout, lines = summary(sel.select(["firmware/bench/src/main.cpp"]), tmp_path, monkeypatch, capsys)
    assert [line.split("=")[0] for line in stdout] == ["tests", "torch", "edge"]
    assert "Firmware jobs: run — firmware/bench/src/main.cpp: firmware/*" in lines


def test_summary_lists_five_triggers_then_counts(tmp_path, monkeypatch, capsys):
    files = [f"firmware/bench/src/f{i}.cpp" for i in range(7)]
    _, lines = summary(sel.select(files), tmp_path, monkeypatch, capsys)
    first = next(line for line in lines if line.startswith("Firmware jobs:"))
    assert first.count("firmware/bench/src/") == 5 and first.endswith("and 2 more")


def test_summary_says_when_no_firmware_job_is_needed(tmp_path, monkeypatch, capsys):
    _, lines = summary(sel.select(["zoo/site.yaml"]), tmp_path, monkeypatch, capsys)
    assert "Firmware jobs: not needed" in lines
