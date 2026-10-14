# Research: Firmware jobs only for firmware-relevant changes

Feature: [spec.md](spec.md) · Date: 2026-10-14

## Diagnosis (input)

CI run 38504807495 of pull request #35 (feature 016) ran `edge-sim` and `edge-qemu`. Replaying the
selection on its 100 changed files:

| Area | Files | Firmware? | Cause |
|------|-------|-----------|-------|
| `all` | `pyproject.toml`, `uv.lock`, `scripts/ci/select_tests.py` | yes | any change to these is "everything" |
| `core`, `site`, `registry`, `docs`, `compliance-tests` | 93 | no | as intended |
| (PR's own `images` rule) | `scripts/imagery/*`, `tests/imagery/*` | no | the PR adds a rule; CI runs the PR's version of the selector |

The only trigger is the `all` rule for dependency and CI files. Second symptom: every push to main
runs `--all`, so the firmware jobs would run again after the merge.

## R1. Deciding whether a dependency change matters to the firmware jobs

**Decision**: Compute the firmware install set from `uv.lock` at the base and at the head
revision, and compare. The set is the transitive closure, in the lock's dependency graph, of the
project's base dependencies, the extras `edge` and `edge-hw`, and the default dependency group
`dev` (`uv sync` installs it), with `torch` excluded (`--no-install-package torch`). Each member
is keyed by name, version and source. Requested extras of dependencies (`extra = [...]` in the
lock) are followed. Environment markers are ignored, which over-approximates the set (fail safe).
Parsing uses `tomllib` (standard library, Python ≥ 3.11; the runner has 3.12).

**Rationale**: The lock file records the exact resolution, so a change to a package shared with
the firmware jobs (for example `numpy` moving because a website extra was added) is detected,
while a change confined to other extras is not. A prototype on the real files of pull request #35
gave 77 members at base and 77 identical members at head: no firmware run, as the spec requires
(SC-001).

**Alternatives considered**:
- `uv export --extra edge --extra edge-hw` at both revisions and diff: exact, including markers,
  but needs `uv` and a second checkout in the `changes` job, which today runs plain `python3` in
  seconds. Rejected for the added setup and moving parts; the over-approximation of R1 only errs
  towards running the jobs.
- Any lock change runs the firmware jobs (status quo): the reported defect.
- Compare only the `pyproject.toml` extras: misses transitive version shifts of shared packages.

## R2. Classifying a `pyproject.toml` change

**Decision**: Parse both revisions with `tomllib` and compare per key. Keys every job shares are
the shared runtime and map to `all` (spec edge case "shared runtime change still runs
everything"): `project.dependencies`, `project.requires-python`, `project.scripts`,
`dependency-groups.dev`, `build-system`, `tool.uv`, `tool.hatch`, `tool.pytest`. A changed extra
maps to the area that uses it (`EXTRA_AREAS`: `edge` and `edge-hw` → `edge`; `catalog` →
`catalog`; `jtbd`, `text`, `cluster`, `labeling-api` → `productdev`; `images` → the website area;
`release` and `edge-train` → `core`). The dependency group `site-check` (browser checks of the
website) maps to the website area. An extra, group or top-level key without a mapping maps to
`core` (all Python tests, no firmware). Tool settings checked by the `checks` job (`tool.ruff`)
map to `docs`. A file that does not parse at either revision is `all`.

**Rationale**: Keeps a website extra (pull request #35) away from the firmware jobs, while any
change to what the firmware jobs install or run still triggers them. The lock comparison (R1)
runs as well, so a manifest edit that shifts resolved versions is caught there too.

**Alternatives considered**: Treat every manifest change as `core` and rely on R1 alone. Rejected:
a change to `project.scripts` or `tool.pytest` alters the firmware jobs without touching the lock.
Mapping the shared keys to `edge` only (first draft) was rejected by `/speckit-analyze` (finding
I1): they affect every job, not just the firmware jobs.

**Consequence noted for the docs**: every `uv.lock` change still runs all Python tests (area
`core`, with torch), also for pull request #35; only the firmware jobs depend on the install-set
comparison.

## R3. Classifying a `ci.yml` change

**Decision**: Split both revisions of `.github/workflows/ci.yml` into the header (everything
before `jobs:`) and one text block per job (a line with two-space indent and a key under
`jobs:`), and compare block by block. Effects: header or `changes` job → `all`; `checks` or `test`
job → `core`; `edge-sim` or `edge-qemu` job → `edge`; an added, removed or unknown job → `all`. If
the split fails at either revision → `all`.

**Rationale**: The `changes` job runs plain `python3` without PyYAML, and the workflow's layout is
regular. Text blocks are enough to tell which job changed; a mis-split only errs towards `all`.

**Alternatives considered**: Parse YAML (needs PyYAML in the `changes` job); keep `ci.yml` as
`all` (this spec's FR-004 forbids it for non-firmware edits).

## R4. Changes to the selection rules

**Decision**: `scripts/ci/select_tests.py` and `tests/unit/test_ci_select.py` get their own area
`ci-select` with no extra tests: the selector's tests are already a guard that every pull request
runs in the `checks` job. The files the pull request changes are classified by the pull request's
own version of the selector, as today.

**Rationale**: The guard tests prove the rules (every tracked file has a rule, every test path
exists, the regression cases). Running everything to "test" a rule change only proved that the
full suite passes, not that the rules are right.

## R5. Selection for pushes to main

**Decision**: On `push`, the `changes` job diffs `github.event.before` against `HEAD`. It fetches
the `before` commit (`git fetch --depth=1 origin <sha>`). If `before` is all zeros, cannot be
fetched (force push, rewritten history) or `git cat-file -e` fails, the job runs `--all`. A push
with several commits is covered because the diff is between the two heads.

**Alternatives considered**: `HEAD^1..HEAD` (misses earlier commits of a multi-commit push);
diffing against the merged pull request's base (needs the API, same result for merge commits).

## R6. Weekly full run

**Decision**: Add `schedule` with cron `17 3 * * 1` (Monday 03:17 UTC, off the full hour to avoid
GitHub's scheduling peaks). `schedule` and `workflow_dispatch` run `--all`. Failure notices go
through GitHub's standard notification for scheduled runs.

**Note**: GitHub disables scheduled workflows of public repositories after 60 days without
repository activity. The project is active; `docs/edge/ci.md` states how to re-enable it.

## R7. Showing the reason

**Decision**: The selection records, per area, each file and the pattern that matched it, and,
for content-sensitive files, the deciding detail (`uv.lock: numpy 2.1.0 → 2.1.3`,
`pyproject.toml: project.optional-dependencies.images`, `ci.yml: job edge-qemu`). The step summary
gets a first line `Firmware jobs: run — <reason>` or `Firmware jobs: not needed`, then the areas.

## R8. Keeping the firmware install set current

**Decision**: The install set's extras live as one constant next to `AREAS`. A guard test reads
the `uv sync` lines of the `edge-sim` and `edge-qemu` jobs in `ci.yml` and asserts that their
`--extra` and `--no-install-package` flags equal the constant. Changing a firmware job's installs
without updating the selector fails the pull request.

**Rationale**: The spec's assumption ("keeping it current is part of changing a firmware job")
becomes an automated check instead of a reminder (owner wants automation, no manual review).

## R9. Local and test use without git

**Decision**: Content-sensitive classification reads files through an injectable reader
`(revision, path) -> text | None`. `--diff` uses `git show`. `--files` has no revisions, so
content-sensitive files fall back to their fail-safe area (`all`), matching today's behaviour.
Tests pass fixture contents through the reader.

## R10. Validation by replay

**Decision**: SC-003 and SC-004 are checked by replaying `--diff M^1 M` for the last 20 merge
commits on main (quickstart). No new CLI mode: merge commits carry both sides locally.
