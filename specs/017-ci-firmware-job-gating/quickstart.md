# Quickstart: validate the firmware job gating

Feature: [spec.md](spec.md) · Contract: [contracts/selection.md](contracts/selection.md)

Prerequisites: a checkout with full history of `main` (`git fetch origin main`), `python3` ≥ 3.12,
`uv` for the test run, `gh` for the CI checks.

## 1. Unit and guard tests

```bash
uv run pytest -q tests/unit/test_ci_select.py
```

Expected: all pass, including the pull request #35 regression case and the install-set guard.

## 2. SC-001: replay pull request #35

```bash
git fetch origin pull/35/head:pr-35
python3 scripts/ci/select_tests.py --diff "$(git merge-base origin/main pr-35)" pr-35
```

Expected: `edge=false`; the summary on stderr reads `Firmware jobs: not needed`. (After #35 is
merged, use its merge commit `M`: `--diff M^1 M`.)

## 3. SC-003 and SC-004: replay the last 20 merged pull requests

```bash
for m in $(git log --merges -n 20 --format=%h origin/main); do printf '%s %s\n' "$m" "$(python3 scripts/ci/select_tests.py --diff "$m^1" "$m" 2>/dev/null | grep '^edge=')"; done
```

Expected: `edge=true` exactly for merges that touched firmware, edge, `hil/` or shared runtime
files, or changed the firmware install set; `edge=false` for all others. Compare with the
changed files of each merge (`git diff --name-only M^1 M`) and record the result in the pull
request description.

## 4. Fail-safe checks

```bash
python3 scripts/ci/select_tests.py --files uv.lock
python3 scripts/ci/select_tests.py --files something/new.txt
```

Expected: both `edge=true` (no revisions to compare; unknown file).

## 5. In CI (after merge of 017)

- Open a website-only pull request: `edge-sim` and `edge-qemu` show as skipped; the step summary
  of `changes` says `Firmware jobs: not needed`.
- Merge it: the push run on main also skips both firmware jobs (SC-002).
- Start CI manually (`gh workflow run ci.yml`): both firmware jobs run.
- The next Monday after 03:17 UTC: a `schedule` run of `ci` exists with both firmware jobs (SC-006):

```bash
gh run list --workflow ci.yml --event schedule --limit 1
```
