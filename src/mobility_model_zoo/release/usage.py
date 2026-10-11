"""Run a model card's `how_to_run` in a clean virtual environment on CPU (gate rules 12 and 13).

The environment gets this repository's package installed from the checkout (the repository is
private during feature 003, so the card's git install line cannot be used yet) with the extras the
card's own install line names, and CPU-only torch. A snippet that needs more than its install line
installs therefore fails here, as it would for a user (feature 013).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from mobility_model_zoo.release.errors import UsageError

TIMEOUT_SECONDS = 600
_EXTRAS = re.compile(r"mobility-model-zoo\[([^\]]+)\]")


def install_spec(root: Path, install_line: str) -> str:
    """What to install from the checkout so that it equals the card's install line: the package
    with the extras in square brackets (`mobility-model-zoo[edge] @ git+...` -> `<root>[edge]`)."""
    m = _EXTRAS.search(install_line or "")
    return f"{root}[{m.group(1).replace(' ', '')}]" if m else str(root)


class VenvRunner:
    def __init__(
        self,
        root: Path,
        hf_token: str | None,
        install_line: str = "",
        timeout: int = TIMEOUT_SECONDS,
    ):
        self.root = root
        self.hf_token = hf_token
        self.install_line = install_line
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
            spec = install_spec(self.root, self.install_line)
            done = subprocess.run(
                ["uv", "pip", "install", "-q", "--python", str(venv / "bin" / "python"), spec],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            if done.returncode != 0:
                tail = "\n".join(done.stderr.strip().splitlines()[-5:])
                raise UsageError(
                    f"fresh environment: installing {spec.rsplit('/', 1)[-1]} failed: {tail}"
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
