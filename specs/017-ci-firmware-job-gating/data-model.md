# Data Model: CI selection

Feature: [spec.md](spec.md) · Decisions: [research.md](research.md)

All entities live in `scripts/ci/select_tests.py`, in memory only.

## Area (existing, extended)

| Field | Type | Meaning |
|---|---|---|
| `tests` | tuple of paths | test paths the area needs |
| `torch` | bool | install torch for the `test` job |
| `edge` | bool | run `edge-sim` and `edge-qemu` |

New area: `ci-select` = `Area(())` (the selector's tests run as a guard in every pull request).
Rules: `all`, `core`, `edge` keep their meaning; `all` no longer lists `pyproject.toml`,
`uv.lock`, `.github/workflows/ci.yml` or `scripts/ci/*`.

## Rule (existing)

`(area, patterns)`, first match wins. Validation: every tracked file matches a rule or a
content-sensitive path (guard test).

## ContentSensitivePath (new)

| Path | Classifier | Fail-safe area |
|---|---|---|
| `uv.lock` | lock classifier (R1) | `all` |
| `pyproject.toml` | manifest classifier (R2) | `all` |
| `.github/workflows/ci.yml` | workflow classifier (R3) | `all` |

Classifier input: path, base revision, head revision, reader `(rev, path) -> str | None`.
Classifier output: list of `Finding`. Parse error, missing revision or missing reader → one
finding with the fail-safe area.

## Finding (new)

The spec's "Selection reason".

| Field | Type | Example |
|---|---|---|
| `area` | area name | `edge` |
| `file` | path | `uv.lock` |
| `reason` | short text | `numpy 2.1.0 → 2.1.3 (firmware install set)` |

For a file matched by an ordinary rule, `reason` is the matching pattern (`firmware/*`).

## FirmwareInstallSet (new)

| Field | Type | Meaning |
|---|---|---|
| `extras` | `FIRMWARE_EXTRAS = ("edge", "edge-hw")` | extras the firmware jobs install |
| `groups` | `("dev",)` | default dependency group `uv sync` installs |
| `skip` | `FIRMWARE_SKIP = ("torch",)` | packages excluded by `--no-install-package` |
| members | set of `(name, version, source)` | closure over the lock graph, markers ignored |

Rules: the closure follows `dependencies`, and for a dependency with `extra = [...]` the target's
`optional-dependencies` of those extras. Added, removed or re-versioned members are the diff.
Validation (guard, R8): the `uv sync` flags of the `edge-sim` and `edge-qemu` jobs equal
`extras` and `skip`.

## ExtraArea mapping (new)

`EXTRA_AREAS: dict[str, str]`, extra name → area. `edge`, `edge-hw` → `edge`; `catalog` →
`catalog`; `jtbd`, `text`, `cluster`, `labeling-api` → `productdev`; `images` → `images` (or
`site` if that area does not exist); `release`, `edge-train` → `core`. Unmapped extra → `core`.

## ManifestKey mapping (new)

`SHARED_MANIFEST_KEYS` (shared runtime) → `all`: `project.dependencies`,
`project.requires-python`, `project.scripts`, `dependency-groups.dev`, `build-system`, `tool.uv`,
`tool.hatch`, `tool.pytest`. `project.optional-dependencies.<extra>` → `EXTRA_AREAS`.
`dependency-groups.site-check` → `images` (or `site`). `tool.ruff` → `docs`. Any other changed key
→ `core`.

## WorkflowBlock mapping (new)

Header (before `jobs:`) and job `changes` → `all`; jobs `checks`, `test` → `core`; jobs
`edge-sim`, `edge-qemu` → `edge`; added, removed or unknown job → `all`.

## Selection (existing, extended)

| Field | Type | Meaning |
|---|---|---|
| `tests` | tuple | union of area tests, nested paths dropped |
| `torch` | bool | any area needs torch |
| `edge` | bool | any area runs the firmware jobs |
| `areas` | area → list of `Finding` | was area → files; now carries the reason |

Derived: `firmware_reasons` = findings whose area has `edge=True`, for the summary's first line.

## Run mode (new, workflow level)

| Event | Mode |
|---|---|
| `pull_request` | `--diff HEAD^1 HEAD` (merge commit); `--all` if HEAD has no second parent |
| `push` (main) | `--diff <before> HEAD`; `--all` if before is zero, unfetchable or missing |
| `schedule` (weekly) | `--all` |
| `workflow_dispatch` | `--all` |
