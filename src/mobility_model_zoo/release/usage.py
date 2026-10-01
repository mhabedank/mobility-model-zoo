"""Run a model card's `how_to_run` in a clean virtual environment on CPU (gate rules 12 and 13).

The environment gets this repository's package installed from the checkout (the repository is
private during feature 003, so the card's git install line cannot be used yet) with CPU-only torch.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from mobility_model_zoo.release.errors import UsageError

TIMEOUT_SECONDS = 600


class VenvRunner:
    def __init__(self, root: Path, hf_token: str | None, timeout: int = TIMEOUT_SECONDS):
        self.root = root
        self.hf_token = hf_token
        self.timeout = timeout
        self._dir: Path | None = None

    def _python(self) -> Path:
        if self._dir is None:
            if shutil.which("uv") is None:
                raise UsageError("the usage check needs `uv` on PATH")
            self._dir = Path(tempfile.mkdtemp(prefix="zoo-usage-"))
            venv = self._dir / "venv"
            env = {**os.environ, "UV_TORCH_BACKEND": "cpu"}
            subprocess.run(["uv", "venv", "-q", "--python", "3.12", str(venv)], check=True, env=env)
            subprocess.run(
                ["uv", "pip", "install", "-q", "--python", str(venv / "bin" / "python"), str(self.root)],
                check=True,
                env=env,
            )
        return self._dir / "venv" / "bin" / "python"

    def run(self, code: str) -> tuple[int, str, str]:
        python = self._python()
        work = Path(tempfile.mkdtemp(prefix="zoo-run-", dir=self._dir))
        script = work / "how_to_run.py"
        script.write_text(code, encoding="utf-8")
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(work),
            "HF_HOME": str(self._dir / "hf-home"),
            "HF_HUB_DISABLE_TELEMETRY": "1",
        }
        if self.hf_token:
            env["HF_TOKEN"] = self.hf_token
        try:
            done = subprocess.run(
                [str(python), str(script)],
                cwd=work,
                env=env,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return 124, "", f"timed out after {self.timeout} s"
        err = done.stderr.replace(self.hf_token, "***") if self.hf_token else done.stderr
        return done.returncode, done.stdout, err
