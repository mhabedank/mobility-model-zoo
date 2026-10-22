# Implementation Plan: Field notes, a long-form page type for the website

**Branch**: `022-field-notes` | **Date**: 2026-10-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/022-field-notes/spec.md`

## Summary

A new page type in the existing site generator: one page per note at `/notes/<slug>/` and an index
at `/notes/`, both built from content files under `zoo/notes/`. A note is CommonMark with a YAML
front matter block. Two markers in the body are resolved at build time: a diagram line embeds an
SVG from `zoo/notes/diagrams/` directly into the page so it inherits the site's colour tokens, and a
citation marker becomes a numbered link into a reference list built from the front matter. The
build fails on a dangling citation in either direction.

Four changes reach outside the new code: the image record schema learns a `note:` placement kind,
the image-markup check learns that notes may show pictures, the credits builder learns to name a
note as a place of use, and the byte budget stops counting notes in the site-wide total and gives
them a budget of their own.

An unreviewed proof of concept of all of this is already in the working tree and passes every site
check except the byte budget. The plan's job is to turn it into the real thing, justify the four
outside changes, and record the numbers the spec deliberately left out.

## Technical Context

**Language/Version**: Python 3.13 (the repository's existing toolchain)

**Primary Dependencies**: Jinja2 templates, `markdown-it-py` in CommonMark mode with raw HTML
disabled, PyYAML, all already used by the site generator. No new dependency.

**Storage**: Content files in the repository: `zoo/notes/*.md`, `zoo/notes/series.yaml`,
`zoo/notes/diagrams/*.svg`. No database, no runtime state.

**Testing**: `pytest` for the loader, and the site's own check suite (`zoo site check`, with
`--a11y` for the browser checks) as the acceptance gate.

**Target Platform**: A static site on GitHub Pages, read on phone and desktop, light and dark.

**Project Type**: Static site generator inside an existing Python package.

**Performance Goals**: No measurable change to build time; the site build stays in the same order
of seconds it takes today.

**Constraints**: A note page stays within its own byte budget without fonts and images, and the
pages still covered by the site-wide budget stay under it. No third-party request, no script, no
web font beyond the two the site already ships. Everything renders without JavaScript.

**Scale/Scope**: One series of five parts, one of them published by this feature. The design should
carry a few dozen notes without a change; it is not built for hundreds.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Touched? | How this feature complies |
|-----------|----------|---------------------------|
| **II. Grounded Evidence over Plausibility** | Indirectly | The principle governs items a model extracts, not prose, so it does not bind a note. The local analogue is built anyway: a citation with no entry, or an entry never cited, fails the build, so a reference list cannot drift away from the text it supports. Where part one makes a claim the author has not sourced, it is written as the author's own observation rather than dressed as literature. |
| **VI. Clean Provenance, Restrictions Carry Over** | Yes | Prose and diagrams are the author's own work and are licensed CC-BY-4.0 through a new entry in `REUSE.toml`; every other path keeps Apache-2.0. Library images keep their CC0 records, and the credits page gains the note as a named place of use, so a picture's origin and its use stay recorded together. |
| **IX. Reproducible, Dated Releases** | No | Notes are not model releases. They carry an author and a date, and nothing in them claims a measured result. |
| **X. Scope Discipline** | No | The principle concerns the extraction model's task boundary. |
| **XI. No Claude in Model Learning or Extraction** | Yes, and it is the sharpest edge | Notes are documentation written with a development assistant, which the principle's carve-out permits. The hard line is that nothing written here may become model input. The ontology that part two and three develop will, if it becomes a labelling guideline, need its own provenance from the literature; it is therefore explicitly out of scope for this feature and must not be published as a definitions page under this page type. |
| **Development Workflow & Quality Gates** | Yes | The gates listed in the constitution cover labelling runs, data generation, experiments, reporting and releases. None of them is triggered by publishing prose. The gate this feature does have to pass is the site's own check suite, which is treated as the acceptance criterion in `quickstart.md`. |

**Result**: Pass, with one standing condition recorded above: the ontology that the series describes
must not be published as a reference page for models under this page type without its own
provenance.

**Re-check after Phase 1 design**: Still a pass, and the design strengthened two of the entries.
Provenance (VI) gained a mechanism rather than an intention: check C1 now has to name the note a
picture is used on, and the licence version travels in the note's own data so no version number
lives in a template. The condition under XI is unchanged and now has a place to live: the data
model describes notes only, and nothing in it can carry a labelling guideline. No new violation
appeared, and the Complexity Tracking table covers every change that reaches outside the feature.

## Project Structure

### Documentation (this feature)

```text
specs/022-field-notes/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0: decisions and the numbers behind them
├── data-model.md        # Phase 1: the content entities
├── quickstart.md        # Phase 1: how to add a note and prove it works
├── contracts/
│   └── checks.md        # Phase 1: checks added and changed
├── checklists/
│   └── requirements.md  # Specification quality checklist
└── tasks.md             # Phase 2 output (/speckit-tasks, not created here)
```

### Source Code (repository root)

```text
src/mobility_model_zoo/site/
├── notes.py                    # NEW: load notes and the series, resolve markers
├── build.py                    # CHANGED: render the note pages and the index
├── check.py                    # CHANGED: image pages allowlist, byte budget
├── images.py                   # CHANGED: credits label for a note placement
├── schemas/
│   └── image-record.schema.json # CHANGED: note placement kind
├── static/css/
│   └── notes.css               # NEW: styles for the page type, loaded only there
└── templates/
    ├── base.html.j2            # CHANGED: navigation entry, conditional stylesheet
    ├── note.html.j2            # NEW
    └── notes.html.j2           # NEW

zoo/notes/
├── 01-whose-journey.md         # NEW: part one
├── series.yaml                 # NEW: the series and its planned parts
└── diagrams/
    └── three-lanes.svg         # NEW

tests/website/
└── test_notes.py                # NEW: loader behaviour, including the failure cases

REUSE.toml                      # CHANGED (generated): CC-BY-4.0 for note prose
docs/website.md                 # CHANGED: the page type documented
```

**Structure Decision**: The page type lives inside the existing site package rather than beside it.
Notes are pages of the same site, built by the same command, checked by the same suite; a second
generator would duplicate the checks that make this site trustworthy. The one piece that is
deliberately separate is the stylesheet, for the budget reason set out in research R2.

## Complexity Tracking

> Four changes touch code that belongs to other features. Each is recorded here with the simpler
> alternative that was rejected, because none of them is strictly about field notes.

| Change | Why needed | Simpler alternative rejected because |
|--------|-----------|--------------------------------------|
| `note:` placement kind in the image record schema (feature 019) | A note needs a lead image from the library, and placements are a closed, validated vocabulary | Reusing `topic:` or `model:` would file a note's picture under a model that does not own it, and the credits page would name the wrong place of use |
| Notes added to the image-page allowlist in the image markup check (feature 016) | The check limits pictures to the start, model and credits pages; notes now have pictures | Dropping the allowlist would remove a real guard that keeps pictures off pages where they only add weight |
| Credits label for a note placement (feature 019) | Every placed picture must name where it is used, and the existing branches produce no label for a note | Leaving the branch out makes the picture appear in the credits with no use named, which breaks the point of the credits page |
| Notes leave the site-wide byte budget and gain their own (feature 008) | The total was set for a site of fixed size; a growing series of long posts breaks that premise by construction | Raising the total would hide the question and need raising again with every post; shortening the posts would remove the reason to write them |
