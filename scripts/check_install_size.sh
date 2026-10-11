#!/bin/sh
# The install of an edge model stays small: no deep-learning framework, under 300 MB (feature 013, SC-002).
# Builds a fresh environment from the checkout with the `edge` extra, as a user's install line does.
set -eu

LIMIT_MB="${LIMIT_MB:-300}"  # macOS about 150 MB, Linux about 240 MB; torch alone is more
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

uv venv -q --python 3.12 "$WORK/venv"
uv pip install -q --python "$WORK/venv/bin/python" "$ROOT[edge]"

SITE="$("$WORK/venv/bin/python" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
MB="$(du -sm "$SITE" | cut -f1)"
echo "edge install: ${MB} MB (limit ${LIMIT_MB} MB)"

if "$WORK/venv/bin/python" -c "import torch" 2>/dev/null; then
    echo "error: the edge install contains torch" >&2
    exit 1
fi
if [ "$MB" -gt "$LIMIT_MB" ]; then
    echo "error: the edge install is larger than ${LIMIT_MB} MB" >&2
    exit 1
fi
