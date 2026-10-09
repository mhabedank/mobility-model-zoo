"""Pin the Hugging Face revisions of the cluster task's third-party models (feature 009, T008).

    uv run python topics/productdev/scripts/cluster/pin_revisions.py           # show what would change
    uv run python topics/productdev/scripts/cluster/pin_revisions.py --write   # write the commits

For every `revision: null` that belongs to a `model_id` in the cluster settings files, looks up the
current commit of that model on the Hub and writes it in place, keeping comments. Needs network
access to huggingface.co. Licences are not touched: `licence_basis` is recorded by hand after
reading the model card and its licence file.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from huggingface_hub import model_info

ROOT = Path(__file__).resolve().parents[4]
FILES = [ROOT / "configs/productdev/jtbd" / name for name in (
    "cluster-baseline.yaml", "cluster-e5-small.yaml", "cluster-gte-base.yaml", "cluster-v1.yaml")]
MODEL_ID = re.compile(r"model_id:\s*([\w.-]+/[\w.-]+)")
NULL_REVISION = re.compile(r"revision:\s*null")


def pin(text: str, lookup) -> tuple[str, list[tuple[str, str]]]:
    """Replace `revision: null` after (or on the same line as) a model_id with its commit."""
    out, changes, current = [], [], None
    for line in text.splitlines(keepends=True):
        found = MODEL_ID.search(line)
        if found:
            current = found.group(1)
        if current and NULL_REVISION.search(line):
            sha = lookup(current)
            line = NULL_REVISION.sub(f"revision: {sha}", line, count=1)
            changes.append((current, sha))
            current = None
        out.append(line)
    return "".join(out), changes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="write the commits into the files")
    args = parser.parse_args(argv)
    cache: dict[str, str] = {}

    def lookup(model_id: str) -> str:
        if model_id not in cache:
            cache[model_id] = model_info(model_id).sha
        return cache[model_id]

    for path in FILES:
        text, changes = pin(path.read_text(encoding="utf-8"), lookup)
        for model_id, sha in changes:
            print(f"{path.relative_to(ROOT)}: {model_id} -> {sha}")
        if args.write and changes:
            path.write_text(text, encoding="utf-8")
    if not args.write:
        print("dry run; pass --write to change the files", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
