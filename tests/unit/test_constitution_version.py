"""The constitution in force is 3.2.0 (amended 2026-11-27: the owner-approved labeling guideline may also
be read by a dataset's teacher; 3.1.0 of 2026-10-14 let Claude draft guidelines for non-Claude
benchmark references when the owner approves them; 3.0.0 of 2026-10-13 added Principle XI,
no Claude in model learning or extraction; 2.3.0 delivery pace, 2.2.0 `experimental` releases)."""

from pathlib import Path

CONSTITUTION = Path(__file__).resolve().parents[2] / ".specify" / "memory" / "constitution.md"


def test_constitution_version():
    text = CONSTITUTION.read_text(encoding="utf-8")
    assert "**Version**: 3.2.0" in text
    assert "3.1.0 → 3.2.0" in text
    assert "3.0.0 → 3.1.0" in text
    assert "2.3.0 → 3.0.0" in text  # the previous amendment stays recorded
    assert "### XI. No Claude in Model Learning or Extraction" in text
