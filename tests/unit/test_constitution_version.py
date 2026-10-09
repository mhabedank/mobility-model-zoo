"""The constitution in force is 2.0.0 (amended 2026-10-08 before features 005 and 006)."""

from pathlib import Path

CONSTITUTION = Path(__file__).resolve().parents[2] / ".specify" / "memory" / "constitution.md"


def test_constitution_version():
    text = CONSTITUTION.read_text(encoding="utf-8")
    assert "**Version**: 2.0.0" in text
    assert "1.4.0 → 2.0.0" in text
