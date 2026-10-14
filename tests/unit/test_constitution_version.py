"""The constitution in force is 3.0.0 (amended 2026-10-13: Principle XI, no Claude in model learning
or extraction; earlier 2.3.0 delivery pace measured against the roadmap, 2.2.0 `experimental`
releases for models that are not production ready)."""

from pathlib import Path

CONSTITUTION = Path(__file__).resolve().parents[2] / ".specify" / "memory" / "constitution.md"


def test_constitution_version():
    text = CONSTITUTION.read_text(encoding="utf-8")
    assert "**Version**: 3.0.0" in text
    assert "2.3.0 → 3.0.0" in text
    assert "2.2.0 → 2.3.0" in text  # the previous amendment stays recorded
    assert "### XI. No Claude in Model Learning or Extraction" in text
