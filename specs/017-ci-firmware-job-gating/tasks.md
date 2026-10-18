---

description: "Task list for feature 017: firmware jobs only for firmware-relevant changes"
---

# Tasks: Firmware jobs only for firmware-relevant changes

**Input**: Design documents from `specs/017-ci-firmware-job-gating/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/selection.md](contracts/selection.md), [quickstart.md](quickstart.md)

**Tests**: Included. The spec requires a regression test for the pull request #35 case (FR-009) and the contract lists tested invariants; the selector's tests are a guard every pull request runs.

**Organization**: Tasks are grouped by user story. Almost all code lives in one file,
`scripts/ci/select_tests.py`, and one test module, `tests/unit/test_ci_select.py`; tasks touching
them are sequential. Fixtures and docs are parallel.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)

---

## Phase 1: Setup

**Purpose**: Coordinate with the open pull request that edits the same script, and prepare fixtures.

- [X] T001 Check whether pull request #35 (`claude/zoo-website-emotional-imagery-6d19f5`) is merged (`gh pr view 35 --json state`). If merged, bring this branch up to date with `main` (desktop tool `sync_with_base_branch`) and confirm area `images` exists in `scripts/ci/select_tests.py`. If not merged, continue; `EXTRA_AREAS` maps `images` to `site` (research R2, plan "Risks and coordination") and the conflict is resolved when #35 lands
- [X] T002 [P] Create folder `tests/fixtures/ci-select/` with a short `README.md` stating that the files are minimal revisions of `uv.lock`, `pyproject.toml` and `ci.yml` for `tests/unit/test_ci_select.py`
- [X] T003 [P] Check that `REUSE.toml` covers `tests/fixtures/**` (licence annotation for files that cannot carry headers: `.lock`, `.toml`, `.yml`); extend the annotation in `REUSE.toml` if it does not

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: The content-sensitive mechanism with fail-safe fallback, the reason-carrying selection, and the workflow block splitter. US1 and US2 plug their classifiers into it.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 In `scripts/ci/select_tests.py` add a frozen dataclass `Finding(area: str, file: str, reason: str)` and `rule_of(path) -> tuple[str, str] | None` returning the area and the matching pattern; keep `area_of(path)` as a thin wrapper (existing tests use it). Change `Selection.areas` to `dict[str, list[Finding]]` (area → findings; for ordinary rules `reason` is the matched pattern, for unmatched files `reason="no rule matches"` with area `all`). Adapt `report()` and the `--all` path so stdout keeps exactly the three lines `tests=`, `torch=`, `edge=` (contract "Output")
- [X] T005 In `scripts/ci/select_tests.py` add the reader type `Reader = Callable[[str, str], str | None]` and `git_reader(rev, path)` that returns `git show REV:PATH` output or `None` when the path does not exist at that revision; extend `select(files, base=None, head=None, read=None)`; `--diff BASE HEAD` passes `git_reader` and both revisions, `--files` passes none (research R9). A git error other than a missing path must raise (contract: exit non-zero)
- [X] T006 In `scripts/ci/select_tests.py` add `CONTENT_SENSITIVE: dict[str, Classifier]` checked before `RULES` in `select()`. For a content-sensitive path: if `read`, `base` or `head` is missing, or the classifier raises, produce `Finding("all", path, "cannot compare: <why>")` (data-model "ContentSensitivePath": fail-safe area `all`). Register `uv.lock`, `pyproject.toml` and `.github/workflows/ci.yml` with a placeholder classifier that returns the fail-safe finding, so behaviour is unchanged until US1/US2
- [X] T007 In `scripts/ci/select_tests.py` add `workflow_blocks(text) -> dict[str, str]`: key `"<header>"` for everything before the line `jobs:`, then one entry per job keyed by the job name, where a job starts at a line matching two-space indent + key + `:` under `jobs:` (research R3). Raise `ValueError` if `jobs:` is missing or no job is found
- [X] T008 In `scripts/ci/select_tests.py` add area `"ci-select": Area(())` with a comment that the selector's tests run as a guard in every pull request, and a rule `("ci-select", ("tests/fixtures/ci-select/*",))` placed before the `docs` rule
- [X] T009 In `tests/unit/test_ci_select.py`: change `test_every_tracked_file_has_a_rule` to accept paths in `sel.CONTENT_SENSITIVE`; add `test_content_sensitive_without_revisions_fails_safe` (`select(["uv.lock"])`, `select(["pyproject.toml"])`, `select([".github/workflows/ci.yml"])` each give `edge` true and tests `("tests",)`); add `test_workflow_blocks_splits_real_ci_yml` (the real `ci.yml` yields `<header>`, `changes`, `checks`, `test`, `edge-sim`, `edge-qemu`). Run `uv run pytest -q tests/unit/test_ci_select.py`: all existing tests still pass

**Checkpoint**: Selection carries reasons; content-sensitive files still fail safe; nothing changed for CI yet.

---

## Phase 3: User Story 1 – Website change with a new website-only dependency (Priority: P1) 🎯 MVP

**Goal**: Dependency changes run the firmware jobs only when the firmware install set changes (FR-001, FR-002, FR-009).

**Independent Test**: Replay pull request #35 (`quickstart.md` §2): `edge=false`, website tests selected.

### Tests for User Story 1 (write first, they must fail)

- [X] T010 [P] [US1] Create lock fixtures in `tests/fixtures/ci-select/`: `uv-base.lock` (root `mobility-model-zoo` with base `dependencies`, `optional-dependencies` `edge`, `edge-hw`, `jtbd`, and `dev-dependencies.dev`; a package reached through a dependency with `extra = [...]`; `torch` reachable from the root; a shared package `numpy`), `uv-website-extra.lock` (adds extra `images` with a new package `opencv-python-headless` only), `uv-shared-bump.lock` (changes the `numpy` version), `uv-torch-bump.lock` (changes only the `torch` version), `uv-extra-of-dep.lock` (changes a package reached only via a requested `extra`)
- [X] T011 [P] [US1] Create manifest fixtures in `tests/fixtures/ci-select/`: `pyproject-base.toml` and variants `pyproject-images-extra.toml` (new extra `images`), `pyproject-edge-extra.toml` (changed `edge` extra), `pyproject-scripts.toml` (changed `[project.scripts]`), `pyproject-requires-python.toml` (changed `requires-python`), `pyproject-site-check.toml` (changed `[dependency-groups] site-check`), `pyproject-ruff.toml` (changed `[tool.ruff]`), `pyproject-unknown-key.toml` (new top-level table), `pyproject-broken.toml` (invalid TOML)
- [X] T012 [US1] In `tests/unit/test_ci_select.py` add a dict-backed reader helper and tests: website extra lock → no `edge` finding; shared bump → `edge` with reason `numpy <old> → <new> (firmware install set)`; torch-only bump → no `edge`; extra-of-dependency change → `edge`; every lock change adds `core`. Manifest: `images` extra → `images` (or `site`, see T001), not `edge`; `edge` extra → `edge`; `project.scripts` and `requires-python` → `all` (shared runtime); `site-check` group → `images` (or `site`); `tool.ruff` → `docs`; unknown table → `core`; broken TOML → `all`
- [X] T013 [US1] In `tests/unit/test_ci_select.py` add `test_pr35_website_extra_runs_no_firmware` (FR-009, contract invariant 5): files = website files (`zoo/site.yaml`, `src/mobility_model_zoo/site/build.py`), `pyproject.toml`, `uv.lock`, `scripts/ci/select_tests.py`; reader serves base/website-extra fixtures → `edge` is false and `tests/website` is selected. Split the case: `test_pr35_dependencies_run_no_firmware` (all files except `scripts/ci/select_tests.py`) is added here and must pass after T016; the full case including the selector file is added in T020

### Implementation for User Story 1

- [X] T014 [US1] In `scripts/ci/select_tests.py` add `FIRMWARE_EXTRAS = ("edge", "edge-hw")`, `FIRMWARE_GROUPS = ("dev",)`, `FIRMWARE_SKIP = ("torch",)` next to `AREAS`, and `firmware_install_set(lock_text) -> set[tuple[str, str, str]]` per data-model "FirmwareInstallSet": members keyed by `(name, version, source)`; start from the root package's `dependencies`, its `optional-dependencies` for `FIRMWARE_EXTRAS` and its `dev-dependencies` for `FIRMWARE_GROUPS`; follow `dependencies`, and for a dependency with `extra = [...]` the target's `optional-dependencies` of those extras; skip names in `FIRMWARE_SKIP`; ignore markers; parse with `tomllib`
- [X] T015 [US1] In `scripts/ci/select_tests.py` implement the lock classifier and register it for `uv.lock` in `CONTENT_SENSITIVE`: always `Finding("core", "uv.lock", "lock changed")`; if the install sets of base and head differ, add `Finding("edge", "uv.lock", ...)` naming up to 5 changed packages as `name old → new`, `+name version` or `-name version`, then `and N more`. Remove `uv.lock` from the `all` rule
- [X] T016 [US1] In `scripts/ci/select_tests.py` add `EXTRA_AREAS` (data-model "ExtraArea mapping": `edge`, `edge-hw` → `edge`; `catalog` → `catalog`; `jtbd`, `text`, `cluster`, `labeling-api` → `productdev`; `images` → `images` if that area exists else `site`; `release`, `edge-train` → `core`; unmapped → `core`) and `SHARED_MANIFEST_KEYS` (`project.dependencies`, `project.requires-python`, `project.scripts`, `dependency-groups.dev`, `build-system`, `tool.uv`, `tool.hatch`, `tool.pytest`; data-model "ManifestKey mapping": shared runtime → `all`); implement the manifest classifier (compare `project.optional-dependencies` per extra via `EXTRA_AREAS`, the shared keys as whole values → `all`, `dependency-groups.site-check` → `images` (or `site`), `tool.ruff` → `docs`, every other changed key → `core`; reason names the key path, for example `project.optional-dependencies.images`) and register it for `pyproject.toml`. Remove `pyproject.toml` from the `all` rule
- [X] T017 [US1] In `tests/unit/test_ci_select.py` add `test_firmware_install_set_matches_ci_jobs` (research R8, contract invariant 3): from `workflow_blocks` of the real `ci.yml`, collect the `--extra` values and `--no-install-package` values of the `uv sync` lines in jobs `edge-sim` and `edge-qemu`; assert their union equals `set(FIRMWARE_EXTRAS)` and `set(FIRMWARE_SKIP)`
- [X] T018 [US1] Run `uv run pytest -q tests/unit/test_ci_select.py` and the replay of `quickstart.md` §2 (pull request #35): expect `edge=false`. If #35 is merged, replay its merge commit with `--diff M^1 M`

**Checkpoint**: The reported defect is fixed for dependency files; US1 is shippable on its own.

---

## Phase 4: User Story 2 – Changes to the CI configuration and the selection rules (Priority: P2)

**Goal**: A selector change or a non-firmware CI edit no longer runs the firmware jobs (FR-003, FR-004).

**Independent Test**: A pull request that only adds a selection rule selects no firmware job; one that edits the `edge-qemu` job selects both.

### Tests for User Story 2 (write first, they must fail)

- [X] T019 [P] [US2] Create workflow fixtures in `tests/fixtures/ci-select/`: `ci-base.yml` (header, jobs `changes`, `checks`, `test`, `edge-sim`, `edge-qemu`) and variants `ci-test-job.yml` (edit in `test`), `ci-edge-qemu.yml` (edit in `edge-qemu`), `ci-header.yml` (edit in `on:`), `ci-changes-job.yml` (edit in `changes`), `ci-new-job.yml` (added job), `ci-no-jobs.yml` (no `jobs:` key)
- [X] T020 [US2] In `tests/unit/test_ci_select.py` add tests: `test` job edit → `core`, no `edge`; `edge-qemu` edit → `edge`; header, `changes` job, added job → `all`; no `jobs:` → `all` (fail safe); `select(["scripts/ci/select_tests.py"])` → tests `()` and `edge` false; selector plus `firmware/bench/src/main.cpp` → `edge` true; add `test_pr35_website_extra_runs_no_firmware`, the full pull request #35 case from T013 including `scripts/ci/select_tests.py` → `edge` false (FR-009)

### Implementation for User Story 2

- [X] T021 [US2] In `scripts/ci/select_tests.py` add `WORKFLOW_JOB_AREAS` (data-model "WorkflowBlock mapping": `<header>` and `changes` → `all`; `checks`, `test` → `core`; `edge-sim`, `edge-qemu` → `edge`; added, removed or unknown job → `all`), implement the workflow classifier on `workflow_blocks` of base and head (reason `ci.yml: job <name>` or `ci.yml: header`), register it for `.github/workflows/ci.yml`, and remove that path from the `all` rule
- [X] T022 [US2] In `scripts/ci/select_tests.py` move `scripts/ci/*` from the `all` rule to the `ci-select` rule and add `tests/unit/test_ci_select.py` to it (before the `productdev` rule, which matches `tests/unit/*`). Check `test_dependencies_and_unknown_files_run_everything` in `tests/unit/test_ci_select.py`: it uses `select()` without revisions, so `uv.lock` and `ci.yml` still fail safe to everything; keep it and add a comment saying why
- [X] T023 [US2] Run `uv run pytest -q tests/unit/test_ci_select.py`: all pass, including the full pull request #35 regression case

**Checkpoint**: US1 and US2 both work; pull requests are selected correctly.

---

## Phase 5: User Story 3 – Merging to main does not re-run unrelated firmware jobs (Priority: P2)

**Goal**: Pushes to main use the same selection, diffed against the previous main head; weekly and manual runs run everything (FR-005, FR-006, FR-007).

**Independent Test**: After merging a website-only change, the main run skips both firmware jobs; a manual run and the Monday run include them (`quickstart.md` §5).

### Tests for User Story 3

- [X] T024 [US3] In `tests/unit/test_ci_select.py` add `test_ci_events_are_selected` reading the real `.github/workflows/ci.yml`: `on.schedule` has cron `17 3 * * 1`; the `changes` job's select step handles `pull_request`, `push`, `schedule` and `workflow_dispatch`; the push branch reads the previous head from an environment variable fed by `github.event.before` (not an inline expression in the script) and falls back to `--all`

### Implementation for User Story 3

- [X] T025 [US3] In `.github/workflows/ci.yml` add `schedule: - cron: '17 3 * * 1'` under `on:` (Monday 03:17 UTC, research R6) and update the header comment (lines 3–5) to: pull requests and pushes to main run what their changes need; the weekly schedule and manual runs run everything
- [X] T026 [US3] In `.github/workflows/ci.yml`, `changes` job: pass `EVENT: ${{ github.event_name }}` and `BEFORE: ${{ github.event.before }}` through `env:`; rewrite the select step as a `case "$EVENT"`: `pull_request` keeps today's merge-commit logic; `push` runs `--diff "$BEFORE" HEAD` only if `BEFORE` is non-empty and not all zeros, `git fetch -q --depth=1 origin "$BEFORE"` succeeds and `git cat-file -e "$BEFORE^{commit}"` succeeds, otherwise `--all` (research R5, FR-007); `schedule`, `workflow_dispatch` and anything else run `--all`. Leave the job conditions of `test`, `edge-sim`, `edge-qemu` unchanged (contract "Workflow events")
- [X] T027 [US3] Run `uv run pytest -q tests/unit/test_ci_select.py tests/unit/test_workflow_secrets.py` and simulate the push branch locally: `BEFORE=$(git rev-parse HEAD~3)` and `python3 scripts/ci/select_tests.py --diff "$BEFORE" HEAD` give the union of those commits' changes

**Checkpoint**: Pull requests and main are selected; the safety net runs weekly.

---

## Phase 6: User Story 4 – The reason for each firmware run is visible (Priority: P3)

**Goal**: The step summary names the trigger of every firmware run (FR-008).

**Independent Test**: Run the selection for a firmware change and for a dependency change; the summary names the file or package.

- [X] T028 [US4] In `tests/unit/test_ci_select.py` add tests on `report()` output (write summary to a temporary `GITHUB_STEP_SUMMARY`): firmware change → line `Firmware jobs: run — firmware/bench/src/main.cpp: firmware/*`; seven firmware findings → five listed, then `and 2 more`; website change → `Firmware jobs: not needed`; stdout still has exactly the three output lines
- [X] T029 [US4] In `scripts/ci/select_tests.py` rewrite `report()` per `contracts/selection.md` "Step summary": first line `Firmware jobs: run — <file>: <reason>[; …]` (up to 5, then `and N more`) or `Firmware jobs: not needed`; then one bullet per area `- **<area>**: <n> file(s), e.g. \`<file>\` (<reason>)`; then the tests line. The `--all` summary says `Firmware jobs: run — full run (<event or --all>)`

**Checkpoint**: All four stories work.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T030 [P] Update `docs/edge/ci.md` (FR-011): how the selection decides (rules, content-sensitive files, firmware install set from `uv.lock`, fail-safe cases; every `uv.lock` change still runs all Python tests, only the firmware jobs depend on the install-set comparison), pushes to main diffed against the previous head, weekly full run on Monday 03:17 UTC and manual run, how to read the summary's firmware line, and that GitHub disables scheduled workflows after 60 days without repository activity (how to re-enable). English only (guard `tests/unit/test_docs_english.py`)
- [X] T031 Update the module docstring of `scripts/ci/select_tests.py`: content-sensitive files, the firmware install set and where it must match `ci.yml`, the `ci-select` area, and usage of `--diff` with contents
- [X] T032 Run the checks of every pull request locally: `uv run ruff check`, `uv run pytest -q $(python3 scripts/ci/select_tests.py --guards)`, `uv run zoo compliance check --ci` (REUSE coverage of the new fixtures)
- [X] T033 Run `quickstart.md` §3 (replay the last 20 merges on main) and §4 (fail-safe checks); record per merge the `edge=` result and the changed areas in the pull request description; SC-003: no firmware run for merges without firmware, edge or shared-runtime changes; SC-004: every merge that changed such files still has `edge=true`. Investigate and fix any mismatch before opening the pull request
- [ ] T034 After merge, verify in CI (`quickstart.md` §5) with `gh`: the next website-only pull request and its main push skip `edge-sim` and `edge-qemu` (SC-002); `gh workflow run ci.yml` runs both; the `changes` job stays under 1 minute (plan Performance Goals; read its duration with `gh run view`); after the next Monday 03:17 UTC a `schedule` run exists with both firmware jobs (SC-006). Update the memory note on CI path gating with the outcome

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies; T001 first (it may rebase the branch).
- **Foundational (Phase 2)**: after Setup; blocks all stories. T004 → T005 → T006 → T007 → T008 → T009 (same file).
- **US1 (Phase 3)**: after Phase 2. MVP.
- **US2 (Phase 4)**: after Phase 2; touches the same file as US1, so run after US1 in practice. T020 adds the full regression case after T013's dependency part.
- **US3 (Phase 5)**: after Phase 2; touches `ci.yml` and the test module only, independent of US1/US2 logic. Run after US2 to avoid test-module conflicts.
- **US4 (Phase 6)**: after Phase 2 (needs `Finding`); best after US1–US2 so the reasons it prints exist.
- **Polish (Phase 7)**: after all stories; T034 after merge.

### Within Each Story

- Fixtures ([P]) → tests (fail) → implementation → run tests.

### Parallel Opportunities

- T002 ∥ T003 (Setup).
- T010 ∥ T011 (US1 fixtures); T019 (US2 fixtures) can be written at the same time.
- T030 (docs) ∥ T031 once the behaviour is final.

## Parallel Example: User Story 1

```text
Task: "T010 [P] [US1] Create lock fixtures in tests/fixtures/ci-select/"
Task: "T011 [P] [US1] Create manifest fixtures in tests/fixtures/ci-select/"
Task: "T019 [P] [US2] Create workflow fixtures in tests/fixtures/ci-select/"
```

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 and Phase 2.
2. Phase 3 (US1): dependency files are judged by content.
3. Validate with the pull request #35 replay (T018). This alone removes the firmware run for pull requests like #35, except for the selector edit.

### Incremental Delivery

1. US1 → dependency changes fixed.
2. US2 → selector and CI edits fixed; the #35 case is fully green.
3. US3 → main pushes stop re-running firmware jobs; weekly safety net.
4. US4 → reasons visible.
5. Polish → docs, replay over 20 merges, post-merge check.

All stories ship in one pull request; the order above is the order of work and of commits.

## Notes

- Every fallback runs more jobs, never fewer (FR-007); a test exists for each fallback.
- The pull request implementing 017 changes the `changes` job of `ci.yml` and therefore runs everything once; that is expected.
- Commit after each phase; keep `tests/unit/test_ci_select.py` green at every commit.

## Implementation notes (2026-10-14)

- T001: pull request #35 was merged (c776981); the branch was fast-forwarded to it, so `images` is
  a real area and no conflict arose.
- T003: `REUSE.toml` already annotates `**`; no change needed.
- T010, T011, T019: instead of one file per variant, `tests/fixtures/ci-select/` holds one base
  revision each (`uv-base.lock`, `pyproject-base.toml`, `ci-base.yml`); the tests derive every
  variant with a visible one-line replacement (`changed()` fails if the text is not found).
- T029 addition: `--all` takes `--reason`, so a fail-safe full run names its cause in the summary
  (`full run (push without a comparable previous head)`); contract and quickstart updated.
- T033 result: last 20 merges replayed (`git log --merges`, not `--first-parent`, which reaches only
  3). 14 merges without firmware, edge or shared-runtime changes: firmware jobs 0 (old selector: 6,
  among them #35, #30, #26, #14). 6 merges with such changes: firmware jobs still selected in all 6.
- T034 stays open until after the merge.
