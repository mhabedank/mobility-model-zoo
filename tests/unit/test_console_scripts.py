"""Console scripts must not shadow system tools.

`uv run` puts `.venv/bin` first on PATH. A script called `security` shadowed macOS
`/usr/bin/security`, so programs reading the keychain (the Claude Code CLI) reported
"Not logged in". The script is now `zoo-security` (2026-10-11).
"""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SYSTEM_DIRS = ("/bin", "/sbin", "/usr/bin", "/usr/sbin")
# Known system tools, checked on every OS so a Linux CI run still catches a macOS collision.
KNOWN = {"security", "codesign", "open", "say", "plutil", "defaults", "launchctl", "ditto"}


def _scripts() -> set[str]:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return set(data["project"]["scripts"])


def test_no_known_system_tool_name():
    assert not _scripts() & KNOWN


def test_no_script_in_system_dirs():
    shadowed = sorted(f"{d}/{n}" for n in _scripts() for d in SYSTEM_DIRS if Path(d, n).exists())
    assert not shadowed, shadowed
