"""The Claude CLI must not see this package's `security` script (it shadows macOS security)."""

import sys
from pathlib import Path

from mobility_model_zoo.productdev.jtbd.labeling.claude_cli import child_env


def test_venv_bin_is_left_out_of_path():
    venv_bin = str(Path(sys.prefix) / "bin")
    other_venv = "/x/.venv"
    env = child_env({"PATH": f"{venv_bin}:{other_venv}/bin/:/usr/bin:/bin", "VIRTUAL_ENV": other_venv,
                     "HOME": "/h"})
    assert env["PATH"] == "/usr/bin:/bin"
    assert env["HOME"] == "/h"
