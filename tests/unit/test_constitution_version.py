"""The constitution in force is 2.1.0 (amended 2026-10-10: usage class, non-commercial models)."""

from pathlib import Path

CONSTITUTION = Path(__file__).resolve().parents[2] / ".specify" / "memory" / "constitution.md"


def test_constitution_version():
    text = CONSTITUTION.read_text(encoding="utf-8")
    assert "**Version**: 2.1.0" in text
    assert "2.0.0 → 2.1.0" in text
