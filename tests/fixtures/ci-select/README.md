# CI selection fixtures

Minimal base revisions of `uv.lock`, `pyproject.toml` and `.github/workflows/ci.yml` for
`tests/unit/test_ci_select.py` (feature 017). The tests derive each changed revision from these
files with a visible string replacement, so every test states what it changes.
