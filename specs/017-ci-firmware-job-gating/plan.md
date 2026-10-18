# Implementation Plan: Firmware jobs only for firmware-relevant changes

**Branch**: `017-ci-firmware-job-gating` (worktree branch `claude/speckit-specify-die-pipeline-c0136f`) | **Date**: 2026-10-14 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/017-ci-firmware-job-gating/spec.md`

## Summary

Pull request #35 (website imagery) ran both firmware jobs because any change to `pyproject.toml`,
`uv.lock`, `ci.yml` or the selector itself counts as "everything", and every push to main runs
everything anyway. The selector learns to look inside those files: it compares the firmware
install set computed from `uv.lock` at base and head, compares `pyproject.toml` per key, and
compares `ci.yml` per job. A selector change becomes its own area, covered by the guard tests.
Pushes to main are selected from the diff since the previous main head; a weekly scheduled run
and the manual start run everything. The step summary names the reason for every firmware run.
A prototype on the real files of pull request #35 found identical install sets (77 packages), so
the change would have skipped both firmware jobs there.

## Technical Context

**Language/Version**: Python 3.12 (runner `python3`, standard library only in the `changes` job); GitHub Actions YAML

**Primary Dependencies**: none new; `tomllib`, `fnmatch`, `subprocess` (stdlib), `git`

**Storage**: N/A (reads `uv.lock`, `pyproject.toml`, `ci.yml` at two revisions via `git show`)

**Testing**: pytest, `tests/unit/test_ci_select.py` (a guard: runs in the `checks` job of every pull request); fixtures under `tests/fixtures/ci-select/`

**Target Platform**: GitHub-hosted `ubuntu-latest` runner, local macOS/Linux for `--files`/`--diff`

**Project Type**: CI tooling inside the single-project repository

**Performance Goals**: `changes` job stays under 1 minute (today about 10 s; parsing two lock files of ~150 packages is milliseconds)

**Constraints**: no third-party packages in the `changes` job; every uncertainty fails safe (runs the jobs); existing tests and guarantees keep passing (FR-010)

**Scale/Scope**: one script (~300 → ~500 lines), one workflow, one test module, one doc page; 8 workflows total, only `ci.yml` changes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution 3.0.0. The feature changes CI tooling only; no model, data, label or release content.

| Principle / section | Touched? | How the plan complies |
|---|---|---|
| I, II, VII, VIII (task-specific modelling) | no | no model or data work |
| III Measure Before Optimizing | yes, lightly | the optimisation is backed by a measured defect (run 38504807495) and a replay check over 20 merged pull requests (SC-003, SC-004) before claiming success |
| IV Riskiest assumption first | yes | the riskiest assumption (lock comparison leaves the firmware set unchanged for a website extra) was prototyped on real files before design |
| V Small and local by default | yes | stdlib only, no new dependency, no new service |
| VI Provenance, IX Releases | no | release workflows and gates unchanged; `release-verify` filters its own paths |
| X Scope Discipline | yes | other workflows stay out of scope (spec Assumptions) |
| XI No Claude in learning or extraction | no | no learning, labeling or extraction; Claude Code only develops tooling (allowed) |
| Resources & Cost Discipline | yes | fewer runs of the 45-minute emulated-board job; no cash costs, no budget needed |
| Development Workflow & Quality Gates | yes | this table lists the touched principles; re-checked below |

**Gate result (pre-design)**: PASS, no deviations.

## Project Structure

### Documentation (this feature)

```text
specs/017-ci-firmware-job-gating/
├── plan.md              # this file
├── research.md          # Phase 0: decisions R1–R10
├── data-model.md        # Phase 1: selection entities
├── quickstart.md        # Phase 1: validation runs
├── contracts/
│   └── selection.md     # Phase 1: selector CLI, outputs, events, summary
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks (not created here)
```

### Source Code (repository root)

```text
scripts/ci/select_tests.py        # rules, areas, content-sensitive classifiers, reasons, summary
.github/workflows/ci.yml          # schedule trigger; changes job: push base, event handling
tests/unit/test_ci_select.py      # regression cases (PR #35), dependency/ci/rule cases, install-set guard
tests/fixtures/ci-select/         # small uv.lock / pyproject / ci.yml revisions for the tests
docs/edge/ci.md                   # how the selection decides, main-branch and weekly runs
```

**Structure Decision**: Keep the selector a single stdlib-only script. The `changes` job runs it
with plain `python3` before any environment exists; splitting it into a package would need an
install step. The new fixture folder gets a rule (area `ci-select`) so the "every tracked file has
a rule" guard holds.

## Design overview

1. **Rules stay first-match**, with two changes: `scripts/ci/*` and `tests/unit/test_ci_select.py`
   move from `all` to the new area `ci-select` (no extra tests, R4); `pyproject.toml`, `uv.lock` and
   `.github/workflows/ci.yml` become *content-sensitive*: their area comes from a classifier, not a
   fixed rule (R1–R3).
2. **Classifiers** get a reader `(rev, path) -> text | None` and return a list of
   `(area, reason)` pairs. Missing reader, missing revision or unparsable content → `all` (R9).
3. **Firmware install set** (R1): closure over the lock graph from the root's base deps + extras
   `FIRMWARE_EXTRAS = ("edge", "edge-hw")` + group `dev`, minus `FIRMWARE_SKIP = ("torch",)`;
   a difference adds area `edge` with the changed packages as reason. A lock change also adds
   `core` (all Python tests).
4. **Selection** keeps its outputs (`tests`, `torch`, `edge`) and adds per-area reasons; the
   summary leads with the firmware decision (R7).
5. **Workflow** (R5, R6): `on.schedule` weekly; the `changes` job picks `--diff` for
   `pull_request` (HEAD^1..HEAD) and `push` (before..HEAD, with fetch and fallback), `--all` for
   `schedule` and `workflow_dispatch`.
6. **Guard** (R8): a test asserts the firmware jobs' `uv sync` flags equal `FIRMWARE_EXTRAS` and
   `FIRMWARE_SKIP`.

## Risks and coordination

- **Pull request #35 edits the same script** (adds area `images` and its rule). Whichever merges
  second resolves the conflict. `EXTRA_AREAS` maps the `images` extra to `images` if that area
  exists at merge time, else to `site`. Recommended order: merge #35 first (it already passes with
  firmware jobs), then rebase 017.
- **Narrower main runs** can miss a defect the rules do not foresee; the weekly full run bounds the
  delay to 7 days (spec Assumption). The fail-safe defaults keep unknown cases on the full path.
- **Self-test of the workflow change**: the pull request implementing 017 changes the `changes`
  job's header area, so it runs everything once, as intended.

## Constitution Check (post-design)

Re-checked after Phase 1: the design adds no dependency, no service and no data handling; every
fallback runs more jobs, never fewer; validation is by replay against real history. **PASS**, no
deviations, Complexity Tracking not needed.
