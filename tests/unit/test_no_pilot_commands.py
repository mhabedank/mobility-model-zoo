"""The proof-of-concept CLI `pilot` is now `jtbd` (feature 003, T011).

README.md and the open tasks of feature 001 must not tell anyone to run `pilot ...` any more. The
benchmark name `pilot-v1` and the word "pilot" for the agreement pilot itself are fine.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMMANDS = (
    "source|corpus|freeze|label|ensemble|budget|check|match|consensus|categorize|agreement|score"
    "|perf|decide|report|spike|doctor"
)
PILOT_COMMAND = re.compile(rf"(?<![\w-])pilot (?:{COMMANDS})\b|(?<![\w-])pilot --|run pilot\b")


def _open_task_lines(path: Path) -> list[str]:
    """Lines of unchecked tasks, including their indented continuation lines."""
    lines, inside = [], False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("- ["):
            inside = line.startswith("- [ ]")
        elif not line.startswith((" ", "\t")):
            inside = False
        if inside:
            lines.append(line)
    return lines


def test_readme_has_no_pilot_commands():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert not PILOT_COMMAND.findall(text)


def test_open_001_tasks_have_no_pilot_commands():
    lines = _open_task_lines(ROOT / "specs/001-jtbd-extraction-pilot/tasks.md")
    offending = [line for line in lines if PILOT_COMMAND.search(line)]
    assert not offending, offending
