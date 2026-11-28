"""`zoo tracking audit` and the import boundary (feature 017 T036, T037; SC-007, FR-025, XI)."""

import subprocess
import sys

from tracking_helpers import store  # noqa: F401 - pytest fixture

from mobility_model_zoo import tracking
from mobility_model_zoo.tracking.audit import audit


def test_clean_store_has_no_findings(store, tmp_path):  # noqa: F811
    with tracking.run("spikes", "clean", "spike") as r:
        r.log_step(0, {"loss": 1.0})
    findings, _notes = audit()
    assert findings == []


def test_personal_data_and_claude_roles_are_found(store):  # noqa: F811
    exp = store.create_experiment("spikes")
    rid = store.create_run(exp).info.run_id
    store.set_tag(rid, "mmz.model", "+49 171 2345678")  # written around the guard
    store.log_param(rid, "teacher.model", "claude-opus")
    findings, _ = audit()
    problems = {(f.key, f.problem) for f in findings}
    assert any(k == "tag mmz.model" and "personal identifier" in p for k, p in problems)
    assert any(k == "param teacher.model" and "Claude" in p for k, p in problems)
    assert all("2345678" not in f.line() for f in findings)  # never the full value


def test_no_gate_reads_the_store():
    """FR-025: release and compliance code never import the tracking client or MLflow."""
    code = (
        "import pkgutil, importlib, sys\n"
        "import mobility_model_zoo.release as r, mobility_model_zoo.compliance as c\n"
        "for pkg in (r, c):\n"
        "    for m in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + '.'):\n"
        "        importlib.import_module(m.name)\n"
        "client = 'mobility_model_zoo.tracking.client'\n"
        "bad = [m for m in sys.modules if m == 'mlflow' or m.startswith(client)]\n"
        "assert not bad, bad\n"
    )
    subprocess.run([sys.executable, "-c", code], check=True)
