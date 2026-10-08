"""Published Markdown is English (feature 005, SC-007)."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "import" / "check_language.py"
spec = importlib.util.spec_from_file_location("check_language", SCRIPT)
check_language = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_language)


def test_heuristic():
    assert check_language.german_share("Das ist nicht der Fall und wir sind auf dem Weg.") > 0.3
    english = "The model runs on the board and reports its latency to the host. " * 5
    assert check_language.german_share(english + "See Müller, 'Der Weg'.") < 0.03


def test_topics_docs_and_readme_are_english():
    paths = [str(ROOT / p) for p in ("topics", "docs", "README.md")]
    bad = check_language.flagged(paths)
    assert not bad, "\n".join(f"{f.relative_to(ROOT)}: {s:.1%}" for f, s in bad)
