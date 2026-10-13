"""The constitution in force is 2.3.0 (amended 2026-10-12: delivery pace measured against the
roadmap; earlier 2.1.0 usage class and non-commercial models, 2.2.0 `experimental` releases for
models that are not production ready)."""

from pathlib import Path

CONSTITUTION = Path(__file__).resolve().parents[2] / ".specify" / "memory" / "constitution.md"


def test_constitution_version():
    text = CONSTITUTION.read_text(encoding="utf-8")
    assert "**Version**: 2.3.0" in text
    assert "2.2.0 → 2.3.0" in text
    assert "2.1.0 → 2.2.0" in text  # the previous amendment stays recorded
