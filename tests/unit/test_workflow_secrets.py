"""Every secret and variable a workflow uses is documented in docs/credentials.md (FR-022)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_workflow_secrets_are_documented():
    table = (ROOT / "docs" / "credentials.md").read_text(encoding="utf-8")
    documented = set(re.findall(r"^\| `([A-Z0-9_]+)` \|", table, flags=re.M))
    used = set()
    for wf in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        used |= set(re.findall(r"\b(?:secrets|vars)\.([A-Z0-9_]+)", wf.read_text(encoding="utf-8")))
    used.discard("GITHUB_TOKEN")  # provided by GitHub
    assert used, "no workflow uses a secret: the pattern is wrong"
    assert used <= documented, f"undocumented: {sorted(used - documented)}"
