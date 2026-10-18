# Contract: CI selection (`scripts/ci/select_tests.py` and the `changes` job)

Feature: [../spec.md](../spec.md) · Model: [../data-model.md](../data-model.md)

## CLI

| Invocation | Behaviour | Change |
|---|---|---|
| `select_tests.py --diff BASE HEAD` | changed files from `git diff --name-only --no-renames BASE HEAD`; content-sensitive files read with `git show REV:PATH` | extended: reads contents at both revisions |
| `select_tests.py --all [--reason R]` | full run; `R` (default `--all`) is shown as `full run (R)` in the summary | extended |
| `select_tests.py --files A B ...` | given paths, no revisions: content-sensitive files fall back to `all` | unchanged result for those files |
| `select_tests.py --guards` | guard test paths | unchanged |

Exit code 0 on success. A git error in `--diff` exits non-zero (the job fails visibly rather than
selecting too little).

## Output (stdout, appended to `GITHUB_OUTPUT`)

Exactly three lines, same keys and formats as today, consumed by the `test`, `edge-sim` and
`edge-qemu` jobs:

```text
tests=<space-separated test paths, may be empty>
torch=<true|false>
edge=<true|false>
```

## Step summary (`GITHUB_STEP_SUMMARY`, stderr when unset)

```text
### Test selection

Firmware jobs: run — <file>: <reason>[; <file>: <reason> …]      (up to 5, then "and N more")
   or
Firmware jobs: not needed

- **<area>**: <n> file(s), e.g. `<file>` (<reason>)
...

Tests: `<paths or "none (checks only)">`; torch: <bool>
```

Guarantees: when `edge=true`, the firmware line names at least one file and reason (FR-008). When
`edge=false`, the line reads `not needed`.

## Workflow events (`.github/workflows/ci.yml`)

| Event | Trigger | Selection |
|---|---|---|
| `pull_request` | any | `--diff HEAD^1 HEAD` on the merge commit; `--all --reason "pull request without merge commit"` without a second parent |
| `push` | branch `main` | `--diff ${{ github.event.before }} HEAD` after fetching `before`; `--all --reason "push without a comparable previous head"` if `before` is `0000…`, unfetchable or absent |
| `schedule` | `17 3 * * 1` (Monday 03:17 UTC) | `--all --reason schedule` |
| `workflow_dispatch` | manual | `--all --reason workflow_dispatch` |

Job conditions stay: `test` runs when `tests != ''`; `edge-sim` and `edge-qemu` run when
`edge == 'true'`; `checks` always runs.

## Invariants (tested)

1. Every tracked file matches a rule or a content-sensitive path.
2. Every area test path exists.
3. The firmware jobs' `uv sync` `--extra` and `--no-install-package` flags equal
   `FIRMWARE_EXTRAS` and `FIRMWARE_SKIP`.
4. Unknown file, unparsable content-sensitive file or missing revision → `edge=true`.
5. Regression: the pull request #35 case (website files + `images` extra + lock change without
   firmware set change + selector change) → `edge=false`.
