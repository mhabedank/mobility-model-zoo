import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "check_merge_log", Path(__file__).resolve().parents[2] / "scripts/import/check_merge_log.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

LOG = """| Branch | Old path | New path | Reason |
|---|---|---|---|
| b | `a.md` | `topics/x/a.md` | |
| b | `raw.bin` | dropped | raw data |
| b | `c.txt` | dropped | |
"""


def test_missing_reason_and_path():
    rows = mod.parse_log(LOG)
    assert mod.missing(rows, {"b": ["a.md", "raw.bin"]}) == []
    assert mod.missing(rows, {"b": ["c.txt", "d.txt"]}) == ["b: c.txt", "b: d.txt"]
