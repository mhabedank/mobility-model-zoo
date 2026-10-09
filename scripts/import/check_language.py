"""Flag Markdown files that are still German (feature 005, SC-007).

    uv run python scripts/import/check_language.py topics docs README.md

A stopword heuristic: a file fails if more than 3 % of its words are common German function
words. German titles in citations stay well below that. Exit 1 if any file is flagged.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

STOPWORDS = {"und", "der", "die", "das", "nicht", "mit", "für", "ist", "auf", "wir"}
LIMIT = 0.03
WORD = re.compile(r"[A-Za-zÄÖÜäöüß]+")


def german_share(text: str) -> float:
    words = [w.lower() for w in WORD.findall(text)]
    return sum(w in STOPWORDS for w in words) / len(words) if words else 0.0


def markdown_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for p in map(Path, paths):
        files += sorted(p.rglob("*.md")) if p.is_dir() else [p]
    return files


def flagged(paths: list[str]) -> list[tuple[Path, float]]:
    out = []
    for f in markdown_files(paths):
        share = german_share(f.read_text(encoding="utf-8"))
        if share > LIMIT:
            out.append((f, share))
    return out


def main(argv: list[str] | None = None) -> int:
    paths = (argv if argv is not None else sys.argv[1:]) or ["topics", "docs", "README.md"]
    bad = flagged(paths)
    for f, share in bad:
        print(f"{f}: {share:.1%} German function words", file=sys.stderr)
    print(f"{len(markdown_files(paths))} files checked, {len(bad)} flagged")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
