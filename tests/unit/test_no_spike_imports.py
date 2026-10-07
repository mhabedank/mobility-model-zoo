"""Production code never depends on the spike (T055, spec FR-012, constitution: Technical Spikes)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IMPORT = re.compile(r"^\s*(?:from|import)\s+spike\b", re.MULTILINE)
SYS_PATH = re.compile(r"sys\.path\.\w+\([^)]*spike", re.MULTILINE)


def test_src_never_imports_spike_code():
    offenders = [str(p.relative_to(ROOT)) for p in (ROOT / "src").rglob("*.py")
                 if IMPORT.search(p.read_text()) or SYS_PATH.search(p.read_text())]
    assert offenders == []


def test_span_configs_never_point_at_spike_data():
    configs = sorted((ROOT / "configs/productdev/jtbd").glob("span-*.yaml"))
    assert configs, "the span configs exist"
    assert [str(c) for c in configs if "data/spike" in c.read_text()] == []


def test_the_check_would_catch_an_import(tmp_path):
    assert IMPORT.search("import json\nfrom spike.span_model import units\n")
    assert SYS_PATH.search("sys.path.insert(0, str(ROOT / 'spike'))")
