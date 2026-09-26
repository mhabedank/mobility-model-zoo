import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from jtbd_pilot.cli import app
from jtbd_pilot.config import load_settings

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "mini-corpus"

def copy_fixture(tmp_path: Path) -> Path:
    work = tmp_path / "mini"
    shutil.copytree(FIXTURE, work)
    return work / "pilot.yaml"


def pilot(config: Path, *args: str, expect: int = 0):
    result = CliRunner().invoke(app, ["--config", str(config), *args])
    assert result.exit_code == expect, (result.exit_code, result.output)
    out = result.stdout.strip()
    return json.loads(out) if out.startswith(("{", "[")) else out


def run_ids(config: Path) -> dict[str, str]:
    settings = load_settings(config)
    ids = {}
    for path in sorted(settings.runs_dir.glob("run-*")):
        model = json.loads((path / "manifest.json").read_text())["model_id"]
        ids[model] = path.name
    return ids


def reference_chain(config: Path) -> dict[str, str]:
    pilot(config, "freeze")
    pilot(config, "label", "--role", "reference", "--backend", "mock", "--model", "mock-a")
    pilot(config, "label", "--role", "reference", "--backend", "mock", "--model", "mock-b")
    ids = run_ids(config)
    for run in ids.values():
        pilot(config, "check", "--run", run)
    pilot(config, "consensus", "--reference", ids["mock-a"], ids["mock-b"])
    pilot(config, "freeze", "--benchmark")
    return ids
