# Implementation Plan: Model pages in progressive depth

**Branch**: `014-model-page-layout` | **Date**: 2026-10-11 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/014-model-page-layout/spec.md`

## Summary

Rebuild the generated model page of the zoo website into six layers of increasing depth: overview → quality and speed → limits and status → quickstart → reference → details and documents. Short forms for the first layers (`not_for`, `limits_short`, structured `unmet_criteria`) are added to the `card` block of `model.yaml`, so the website and the model card share them; the release status comes from the release record. Word and item budgets are enforced on the input by the release gate (rule 17 extended, new rule 18) and on the rendered page by new site checks D1–D6. The field-level interface reference moves to the existing format pages. The model card adopts the same order from each model's next release. Research: [research.md](research.md).

A finding that raises the priority: every published release, scout-large included, is `experimental`, and the scout-large page does not say so where readers look (Constitution IX). The new overview fixes this from the record.

## Technical Context

**Language/Version**: Python 3.12 (project standard, `uv`)

**Primary Dependencies**: Jinja2 templates, jsonschema, the existing `mobility_model_zoo.site` and `mobility_model_zoo.release` packages; Playwright with axe-core for browser checks (existing `site-check` group). No new dependency.

**Storage**: files in the repository (`zoo/models/<name>/model.yaml`, `site.yaml`, release records, results JSON); output is the static `_site/` directory

**Testing**: pytest (`tests/website`, `tests/release`), slow browser tests with `-m slow`; `zoo site check --a11y`, `zoo check`

**Target Platform**: static pages on GitHub Pages; model card Markdown on Hugging Face

**Project Type**: CLI and library generating a static website (single project)

**Performance Goals**: unchanged from 008: main HTML ≤ 150 KB, total ≤ 300 KB without fonts, LCP ≤ 2 s on Fast 3G with 4× CPU slowdown; new: first quality figure ≤ 2 screens, limits ≤ 4 screens at 1440 × 900 (SC-001, SC-003)

**Constraints**: complete without JavaScript (A2); no request to another host (P1, P2); WCAG 2.1 AA in both colour schemes (A1); numbers only from registry sources (F1–F4); published cards and release records unchanged

**Scale/Scope**: 2 published model pages today (scout-large, picket-forest), 3 more models in progress (hum-fan, pace-cnn, picket-mlp); 1 page template with 10 partials; 1 card template

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Touched? | How the plan complies |
|---|---|---|
| I, II, VII, X (JTBD task rules) | No | No change to extraction, prompts, data or outputs |
| III Measure before optimizing: metric naming | Yes | Every headline figure and every unmet criterion keeps its "measured against" note; numbers come only from results or the task's success criteria and are checked by F1–F4; no metric is renamed; F3 ("accuracy" wording) unchanged |
| IV Riskiest assumption | Yes (light) | Riskiest assumption: readers find the status, quality and limits faster in the new order. Tested by SC-005 (reader test, at least four of five); budgets and placement are checked automatically (D2, D6) |
| V Small and local, budgets | Yes | Headline figures keep their hardware and origin (emulator vs board) in the `against` line; the note field of `unmet_criteria` states emulator-only evidence; nothing presents emulator results as hardware results |
| VI Provenance, restrictions carry over | Yes | Usage class and licence move into the first screen; "Non-commercial" is checked in layer 1 (D4); training-data summary, attribution and compliance records stay linked (L3, SC-006) |
| VIII Fair comparison | No | Comparisons are shown as they are in the results; no new comparison is computed |
| IX Reproducible, dated releases | Yes | Release status shown from the record at the top (fixes the scout-large gap); `experimental` releases name every unmet criterion with its measured value (gate rule 18, D1); published versions, records and cards stay immutable (card order applies only to new releases; audit compares hashes); "Non-commercial" on the website at the top |
| Tasks and Releases: one release gate | Yes | New rule 18 and extended rule 17 live in the shared gate `zoo check`, the same for every task |
| Resources & cost | No | No cash cost; local build and CI only |
| Workflow: spec and plan list touched principles | Yes | This table |

Result before Phase 0: **PASS**, no violation.

Re-check after Phase 1 (data model, contracts): **PASS**. The design adds structured short forms whose numbers resolve from existing sources (III, IX), keeps every required document reachable (VI, SC-006), and changes no published artefact (IX). The A2 contract change moves the field table to the format page; it removes no required content from the site.

## Project Structure

### Documentation (this feature)

```text
specs/014-model-page-layout/
├── plan.md              # This file
├── research.md          # Phase 0: decisions R1–R11
├── data-model.md        # Phase 1: new fields, layers, budgets
├── quickstart.md        # Phase 1: validation guide
├── contracts/
│   ├── page-layers.md   # order, content and anchors of the six layers
│   ├── checks.md        # D1–D6, changed A2/F1/F2/F4, gate rules 17 and 18
│   └── card-order.md    # new card.SECTIONS
├── checklists/
│   └── requirements.md  # spec quality checklist
└── tasks.md             # Phase 2 (/speckit-tasks, not created here)
```

### Source Code (repository root)

```text
src/mobility_model_zoo/
├── site/
│   ├── budgets.py                     # new: budget constants and word counting (shared by gate and checks)
│   ├── context.py                     # release status, short forms, layer data
│   ├── build.py                       # page context for the new layers
│   ├── charts.py                      # comparison bar pair for headline figures
│   ├── check.py                       # D1–D5; F1/F2/F4 scope
│   ├── a11y.py                        # D6 placement; A2 changed
│   ├── schemas/site.schema.json       # differentiators ≤ 4, metric_cards ≤ 4
│   ├── static/css/site.css            # layer navigation, short-form and bar styles
│   └── templates/
│       ├── model.html.j2              # new layer order
│       └── partials/                  # hero (overview), quality, limits, quickstart,
│                                      # reference (interface + viewer), details (provenance,
│                                      # metrics, versions, cite, notes)
└── release/
    ├── card.py                        # SECTIONS, short-form rendering, status sentence
    ├── gate.py                        # rule 17 extended, rule 18
    ├── schemas/model.schema.json      # card.not_for, card.limits_short, card.unmet_criteria
    └── templates/model_card.md.j2     # new order

zoo/models/{scout-large,picket-forest,hum-fan,pace-cnn,picket-mlp}/model.yaml   # short forms
zoo/models/{scout-large,picket-forest}/site.yaml                                # texts within budgets

tests/
├── website/                           # D1–D6, A2, layer order, anchors; frozen registry updated
└── release/                           # rule 17/18, card order, golden card

docs/website.md, docs/adding-a-model.md                                          # new fields, layers, budgets
```

**Structure Decision**: single project; the change stays inside the existing `site` and `release` packages. One new module, `site/budgets.py`, holds the budget table and the counting rule so the gate and the site checks cannot disagree.

## Implementation order

1. Rebase on `main` after feature 012 is merged (R11).
2. Schema and data: `model.schema.json` fields, `site.schema.json` limits, `budgets.py`; gate rules 17 and 18 with tests.
3. Content: short forms for all five models' `model.yaml`; `site.yaml` of scout-large and picket-forest within budgets (R10); frozen test registry updated.
4. Page: context and templates in layer order; comparison bars; A2 change; checks D1–D5 with tests.
5. Browser check D6; measure and record positions.
6. Card: new `SECTIONS`, short-form blocks, golden card regenerated and reviewed.
7. Docs: `docs/website.md`, `docs/adding-a-model.md`; CI path filters checked for the new module (memory: CI path gating).
8. Reader test (SC-005) after deployment.

## Complexity Tracking

No constitution violation. One contract change to feature 008, justified here:

| Change | Why needed | Simpler alternative rejected because |
|---|---|---|
| Check A2 no longer requires the field table on the model page | FR-015: the interface reference is the largest block on both pages (627–798 words) and duplicates the format page | Keeping the table collapsed on the model page keeps two copies of one reference and the page weight, and contradicts the spec's "link instead of repeating" |
