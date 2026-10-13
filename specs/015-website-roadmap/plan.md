# Implementation Plan: Roadmap and upcoming models on the zoo website

**Branch**: `claude/015-website-roadmap` | **Date**: 2026-10-12 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/015-website-roadmap/spec.md`

## Summary

A hand-kept roadmap record, `zoo/roadmap/roadmap.yaml`, becomes the one source for:
- a new roadmap page `/roadmap/`: three horizons in columns under a timeline band, with compact cards; updates of published models are visually quieter;
- a "Coming next" row of small cards on the start page, which replaces the tiles of unpublished models;
- a pace review per quarter, `zoo roadmap pace`, that measures plan against actual as constitution 2.3.0 requires.

Each entry keeps the horizon it was first planned in, guarded by the git history. Moves and drops are recorded with reasons. Delivery is read from the release records, so publishing a first release needs no second edit. Eight record checks (RM1–RM8) run in `zoo site build` and `zoo roadmap check`; a ninth (RM9) checks the rendered pages. The build fails when the roadmap goes stale or a closed quarter has no review. Research: [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.12 (project standard, `uv`)

**Primary Dependencies**:
- the existing `mobility_model_zoo.site` and `mobility_model_zoo.release` packages;
- Jinja2, jsonschema, PyYAML and Typer, all already dependencies;
- git, for the history check RM5;
- Playwright with axe-core, for the browser checks (existing `site-check` group).

No new dependency.

**Storage**: files in the repository: `zoo/roadmap/roadmap.yaml`, `zoo/roadmap/reviews/<quarter>.md`, `zoo/site.yaml` (new optional `roadmap.share_line`). Release records are read unchanged. Output is the static `_site/`.

**Testing**: pytest (`tests/website`, new `test_roadmap_*.py`), slow browser tests with `-m slow`; `zoo roadmap check`, `zoo site check --a11y`

**Target Platform**: static pages on GitHub Pages; CLI on Linux and macOS developer machines and in CI

**Project Type**: CLI and library generating a static website (single project)

**Performance Goals**:
- **Unchanged from feature 008**:
  - main HTML at most 150 KB per page;
  - at most 300 KB in total without fonts;
  - LCP at most 2 s on Fast 3G with 4× CPU slowdown.
- **Roadmap page** at 1440 × 900: all three horizons side by side, at most two screen heights (SC-002).
- **Start page**: the "Coming next" grid is less than half of the models section (SC-003).
- **Pace report**: under a minute (SC-007).

**Constraints**:
- complete without JavaScript (A2);
- no request to another host (P1, P2);
- WCAG 2.1 AA in both colour schemes (A1), reflow at 390 px (A5);
- no literal numbers in templates (F2) or entry texts (RM3);
- release records and published cards untouched;
- `zoo check` and the release pipeline do not read the roadmap, so a release is never blocked by it.

**Scale/Scope**:
- **Initial roadmap**: 15 entries, of which 11 are upcoming models and 4 are updates.
- **Pages**: 1 new page, 1 changed page, header navigation on every page.
- **Code**: 2 new modules, 1 new CLI sub-app, 2 new templates (the page and a start-page partial), about 60 lines of CSS.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle or section | Touched? | How the plan complies |
|---|---|---|
| I, II, VII, X (JTBD task rules) | No | No change to extraction, data or outputs |
| III Measure before optimizing | Yes | Roadmap and cards carry no metrics and no numbers (RM3, F2). The pace report measures delivery, not model quality, and names what each number counts (research R6) |
| IV Riskiest assumption | Yes (light) | Riskiest assumption: visitors read the plan correctly at a glance. Tested by the reader test (SC-001); layout budgets are checked in the browser (A5, SC-002) |
| V Small and local | No | No model or budget changes |
| VI Provenance, restrictions carry over | Yes | The usage label is derived from the model registration, never typed (research R9, FR-007). Open licence questions stay visible as preconditions (FR-023). New models still need their dataset declarations before training |
| VIII Fair comparison | No | — |
| IX Reproducible, dated releases | Yes | Delivery is read from published release records only (R3). Release records and cards are never written by this feature. The page is dated and says it is a plan (FR-010) |
| Project scope: naming | Yes | Working names are marked. A registered name is used once `model` is set, and RM2 requires `working_name: false` then |
| Tasks and releases: one gate, one pipeline | Yes | The release gate and pipeline are unchanged; the roadmap follows releases, it does not gate them |
| **Roadmap and Delivery Pace (2.3.0)** | Yes | `planned` is fixed and checked against git history (RM5). Moves and drops are kept with date and reason (data model). Delivered means published (R3, RM8). The pace review has the required numbers (R6) and is required before roll-over (RM7). The first plan uses the observed pace (spec, Proposed roadmap) |
| Resources & cost | No | No cash cost; local build and CI only |
| Workflow: gates | Yes | The new gate before rolling the roadmap forward is implemented as RM7 |

Result before Phase 0: **PASS**, no violation.

Re-check after Phase 1 (data model, contracts): **PASS**.
- The design adds no hand-written number to the site and no second copy of a release fact; delivery dates come from release records.
- It keeps the first planned horizon immutable through a git check, not by convention.
- The one trade-off is that RM6 and RM7 can stop a site deploy after a quarter ends until the roadmap is reviewed. This is intended (owner direction, constitution gate) and does not touch releases (research R5).

## Project Structure

### Documentation (this feature)

```text
specs/015-website-roadmap/
├── spec.md                  # feature spec (owner decisions 2026-10-12)
├── model-ideas-research.md  # research of 2026-10-11 behind the proposed roadmap
├── plan.md                  # this file
├── research.md              # Phase 0: decisions R1–R12
├── data-model.md            # Phase 1: record, horizon ids, entry, derived values, page context
├── quickstart.md            # Phase 1: validation guide
├── contracts/
│   ├── roadmap.schema.json  # structure of zoo/roadmap/roadmap.yaml
│   ├── checks.md            # RM1–RM9 and changes to existing checks
│   ├── cli.md               # zoo roadmap check | pace
│   ├── pace-report.md       # sections and rules of reviews/<quarter>.md
│   └── pages.md             # roadmap page, start page changes, navigation, preview image
├── checklists/
│   └── requirements.md      # spec quality checklist
└── tasks.md                 # Phase 2 (/speckit-tasks, not created here)
```

### Source Code (repository root)

```text
zoo/
├── roadmap/
│   ├── roadmap.yaml                       # new: the record (initial content from the spec)
│   └── reviews/                           # new: pace reviews, first one for 2026-Q4
└── site.yaml                              # + roadmap.share_line

src/mobility_model_zoo/
├── site/
│   ├── roadmap.py                         # new: load, RM1–RM8, horizon ids, delivery, page context
│   ├── pace.py                            # new: pace report (research R6, contracts/pace-report.md)
│   ├── roadmap_cli.py                     # new: `zoo roadmap check | pace`
│   ├── build.py                           # run RM1–RM8, render roadmap/, pass upcoming to start page
│   ├── check.py                           # + RM9 (rendered parity)
│   ├── og.py                              # + preview card for roadmap/
│   ├── schemas/roadmap.schema.json        # new (copy of contracts/roadmap.schema.json)
│   ├── schemas/site-config.schema.json    # + optional roadmap.share_line
│   ├── templates/roadmap.html.j2          # new: the roadmap page
│   ├── templates/partials/upcoming.html.j2 # new: "Coming next" cards
│   ├── templates/start.html.j2            # tiles for published models only, upcoming partial, counts
│   ├── templates/base.html.j2             # + "Roadmap" in the navigation
│   └── static/css/site.css                # timeline band, horizon columns, entry and mini cards, chips
└── release/cli.py                         # register the `roadmap` sub-app

tests/website/
├── fixtures/registry/zoo/roadmap/roadmap.yaml   # new fixture record
├── test_roadmap_record.py                 # RM1–RM8, each with a deliberate fault
├── test_roadmap_page.py                   # page content, order, anchors, quieter updates, no-JS
├── test_roadmap_pace.py                   # report on a constructed git history
└── test_start_page.py                     # updated: no tiles for unpublished models, cards, counts

docs/website.md                            # + roadmap page, record and pace review
.github/workflows/ci.yml                   # + `zoo roadmap check` in the checks job
```

**Structure Decision**: single project, following the existing site package (features 008, 012, 014). The roadmap code lives in `site/` because both the build and the CLI use it (research R11).

## Phases after this plan

- **Phase 2** (`/speckit-tasks`): tasks in story order. The order is:
  1. US1 (roadmap page) and US2 (start-page cards) on the record and checks RM1–RM4.
  2. US3 (consistency and staleness, RM5–RM9).
  3. US4 (pace report and review gate).
  4. US5 (preview image).
- **First review**: at the end of Q4 2026, `zoo roadmap pace 2026-Q4 --write`, then the owner fills in "Re-planning" and rolls the horizons forward (SC-008).

## Complexity Tracking

No constitution violations to justify.
