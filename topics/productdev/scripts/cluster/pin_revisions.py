"""Pin the Hugging Face revisions of the cluster task's third-party models (feature 009, T008).

    uv run python topics/productdev/scripts/cluster/pin_revisions.py           # show what would change
    uv run python topics/productdev/scripts/cluster/pin_revisions.py --write   # write the commits

For every `revision: null` that belongs to a `model_id` in the cluster settings files, looks up the
current commit of that model on the Hub and writes it in place, keeping comments. A
`code_revision: null` (models with `trust_remote_code`) gets the current commit of the repository
that the model's `auto_map` names at the pinned revision, which may be another repository than the
model's own. Needs network access to huggingface.co. Licences are not touched: `licence_basis` is
recorded by hand after reading the model card and its licence file.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from huggingface_hub import hf_hub_download, model_info

ROOT = Path(__file__).resolve().parents[4]
FILES = [ROOT / "configs/productdev/jtbd" / name for name in (
    "cluster-baseline.yaml", "cluster-e5-small.yaml", "cluster-gte-base.yaml", "cluster-v1.yaml")]
MODEL_ID = re.compile(r"model_id:\s*([\w.-]+/[\w.-]+)")
NULL_REVISION = re.compile(r"(?<!\w)revision:\s*null")
NULL_CODE_REVISION = re.compile(r"\bcode_revision:\s*null")


def pin(text: str, lookup, code_lookup=None) -> tuple[str, list[tuple[str, str]]]:
    """Replace `revision: null` after (or on the same line as) a model_id with its commit, and
    `code_revision: null` with the commit of the model's remote code (`code_lookup` gives
    `(repository, commit)`)."""
    out, changes, current, model = [], [], None, None
    for line in text.splitlines(keepends=True):
        found = MODEL_ID.search(line)
        if found:
            current = model = found.group(1)
        if model and code_lookup and NULL_CODE_REVISION.search(line):
            repo, sha = code_lookup(model)
            line = NULL_CODE_REVISION.sub(f"code_revision: {sha}", line, count=1)
            changes.append((repo, sha))
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

    def code_lookup(model_id: str) -> tuple[str, str]:
        config = json.loads(Path(hf_hub_download(model_id, "config.json",
                                                 revision=lookup(model_id))).read_text())
        repos = {ref.split("--")[0] if "--" in ref else model_id
                 for ref in (config.get("auto_map") or {}).values()}
        if len(repos) != 1:
            raise SystemExit(f"{model_id}: expected one remote code repository, found {sorted(repos)}")
        repo = repos.pop()
        return repo, lookup(repo)

    for path in FILES:
        text, changes = pin(path.read_text(encoding="utf-8"), lookup, code_lookup)
        for model_id, sha in changes:
            print(f"{path.relative_to(ROOT)}: {model_id} -> {sha}")
        if args.write and changes:
            path.write_text(text, encoding="utf-8")
    if not args.write:
        print("dry run; pass --write to change the files", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
