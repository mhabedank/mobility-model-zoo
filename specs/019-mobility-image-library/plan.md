# Implementation Plan: Mobility image library in the house style

**Branch**: `claude/mobility-image-library-019` | **Date**: 2026-10-14 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/019-mobility-image-library/spec.md`

## Summary

A pool of at least 100 AI-generated images in the house style SIEBDRUCK, covering ten themes of mobility (rail, public and private road, active, water, air, infrastructure, workshops, IoT, AI at work), built on the feature 016 records, checks and generator. What is new:

1. **Series by theme**: the series file lists subjects per theme with ids, aspect, scene and alt text ([subjects.md](subjects.md), about 105 subjects); the generator renders from it with collision-free seeds.
2. **Automated rejection, manual pick**: `zoo site images triage` runs faces, text, a new palette-and-accent style check (I6), a near-duplicate check (I7) and the byte caps over a round of renders, and writes a static contact sheet of the passing candidates, numbered per subject. The owner picks one per subject or "none"; `zoo site images pick` imports the picks as records with no placement. "None" subjects go into the next round.
3. **Pool, not gallery**: records without a placement are validated but produce nothing in the site build; the credits page and `set.json` list placed records only, so the pool never triggers the deployment approval. A local `overview` page is the owner's tool for placing. No template or page changes.
4. **Light repository**: library records carry no source PNG (hash only); three WebP derivatives per image, measured at about 110 KB per image, so the pool adds about 12 MB; check L1 enforces 40 MB.

Research with decisions and rejected alternatives: [research.md](research.md). Entities: [data-model.md](data-model.md). Commands and checks: [contracts/](contracts/).

## Technical Context

**Language/Version**: Python 3.12 (project standard, `uv`)

**Primary Dependencies**: the existing `mobility_model_zoo.site` package (016 `images`, `images_process`, `images_cli`), the `images` extra (Pillow, opencv-python-headless, rapidocr-onnxruntime, NumPy) for I4, I6, I7; the `zoo-flux` container (NGC PyTorch 25.09 + diffusers) with FLUX.2-klein-4B (drafts) and Qwen-Image-2512 (finals), both Apache-2.0 and cached on the Spark. **No new package.**

**Storage**: files in the repository: `zoo/site/images/<id>/` (record + three derivatives, no PNG for library images), `zoo/site/images/series/siebdruck.yaml` (themes, palette, thresholds), `specs/019-mobility-image-library/rounds/<n>/` (triage and picks as audit trail). Round PNGs, sheets and thumbnails stay outside git (`~/zoo-imagery/rounds/` on the Spark and the developer machine). Pool overview under `.cache/site/`.

**Testing**: pytest (`tests/website/test_images_*.py` extended; new `test_images_style.py`, `test_images_triage.py`, `test_images_pick.py`, `test_images_overview.py`, `test_images_coverage.py` with synthetic flat-colour fixtures), `tests/imagery/test_gen_manifest.py` extended (themes, seeds); `zoo site check --a11y`; `zoo site images check --deep --require-coverage`; `reuse lint`. Calibration on the 016 renders is a recorded step, not a unit test.

**Target Platform**: static pages on GitHub Pages (unchanged); CLI on macOS and Linux and in CI; generator on the DGX Spark (arm64, CUDA 13).

**Project Type**: CLI and library generating a static website (single project) plus the standalone generator script.

**Performance Goals**: triage about 2 s per candidate on CPU (a 420-candidate round in about 15 minutes); `zoo site build` validates about 110 records in under 5 s (no image decoding: hashes and stored pHash); `site-images` CI job under 10 minutes (deep check on 1600 px derivatives); site budgets unchanged (S1 to S4, LCP ≤ 2 s).

**Constraints**: no new page, no template change, no change to the start page beyond placements (FR-021, FR-022); no third-party resources; no hosted image API; no model judging images (the project's rule against model judgement in the loop; I6 and I7 are deterministic measurements); the six 016 records keep their files and approval; derivatives ≤ 40 MB (L1); no cash cost.

**Scale/Scope**: about 105 subjects, 4 seeds each, about 420 final renders per full round (22 GPU hours), 1 to 2 further rounds for "none" picks; ≥ 100 records; 3 new commands (`triage`, `pick`, `overview`), 4 changed (`gen.py`, `add`, `check`, `list`); 5 new or changed checks (I6, I7, I8, L1, L2) and 6 changed (I1 to I5, C1); 1 schema change; 1 series-file migration; 6 record migrations; CI job unchanged in shape.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Principles I, II, VII and X concern the JTBD extraction task and are not touched. No model, benchmark, dataset or release record changes.

| Principle or section | Touched | How the plan complies |
|---|---|---|
| III Measure before optimizing | no | No model result changes. Site budgets are measured by the existing checks; the pool's weight by L1. |
| IV Riskiest assumption first | yes | Riskiest assumption: the automated rejection (I6, I7) rejects what the owner would reject and little else. Tested first, before any new rendering, by calibrating on the 016 renders and the two rejected series (research R4, R5, R11). Kill criteria: if the six approved images or more than 30% of the 016 shortlist fail I6 at any setting that still rejects the rejected series, I6 becomes a sheet warning and FR-006 is reported as not met; if I7 cannot separate same-composition from different-composition seeds with at most one false rejection in twenty, it is set conservatively and only marks suspected twins. Second risk: subjects the generator misreads; caught in the draft pass before the 22-hour final pass. |
| V Small and local | yes | Generation, triage and checks run on the project's own machines; no hosted API; the `images` extra stays optional and `zoo site build` never imports it (I7 at build time uses stored hashes). |
| VI Clean provenance | yes | Every record keeps the full 016 recipe plus theme, subject, round and the I6 measures; models Apache-2.0, outputs CC0; faces and readable text rejected automatically; prompts name no place, operator or brand. Every candidate's outcome and reason is kept in `triage.json` (FR-007), so the pool's provenance includes what was rejected. |
| IX Reproducible, dated releases | yes (website only) | Records carry date, recipe, container digest and generator commit (now versioned); I5 regeneration works against the 1600 px derivative when the source is absent. Model releases unchanged. |
| Roadmap and delivery pace | no | Not touched. |
| Resources and cost discipline | yes | No cash; about one Spark GPU day per full round; the VPN copy. Cost order local first. |
| Development workflow and quality gates | yes | New checks run in `zoo site check` and the `site-images` job; `reuse lint` covers every record through the existing C2 blocks. |
| No model judgement in the loop (project memory, Principle XI where present) | yes | Candidate ranking is not done by a model: I6 and I7 are deterministic measurements with thresholds calibrated on the owner's approved set; the owner picks. The agent's only judgement is on drafts (subject wording), as in 016. |
| Compliance first-class, zoo private, no branding (project memory) | yes | Disclosure unchanged; compliance blocks cover every record; OCR rejects any readable text; no new page. |

**Gate result before research**: pass. **After design**: pass. No deviation to justify.

## Project Structure

### Documentation (this feature)

```text
specs/019-mobility-image-library/
├── plan.md                 # This file
├── spec.md
├── research.md             # R1–R11: storage and weight, themes, triage, I6, I7, sheet and picks, overview, site, compute, migration, risk order
├── data-model.md           # record changes, series changes, round, sheet, overview, coverage
├── subjects.md             # the planned subjects per theme (105 + 10 reserves)
├── quickstart.md           # validation guide
├── contracts/
│   ├── image-record.schema.json   # 016 schema extended (theme, subject, round, optional source.file, style/duplicate checks, measures)
│   ├── checks.md           # I6, I7, I8, L1, L2 new; I1–I5, C1 changed
│   └── cli.md              # gen.py changes; triage, pick, overview new; check, list, add, build changed
├── rounds/<n>/             # audit trail written during implementation: manifest.json, triage.json, picks.yaml, next.txt
├── checklists/requirements.md
└── tasks.md                # /speckit-tasks output (not created here)
```

### Source Code (repository root)

```text
scripts/imagery/
├── gen.py                  # CHANGED: themes, seed scheme, --only theme/subject, --reserve, next.txt, manifest fields
└── README.md               # CHANGED: rounds workflow (draft pass, final pass, rsync, triage, picks)

src/mobility_model_zoo/site/
├── images.py               # CHANGED: THEMES/minimums/cap, theme+subject in records, I2 via themes + negative_history, I7/I8/L1/L2 over records, placed-only asset/credits/set, overview context
├── images_process.py       # CHANGED: style() (I6, Lab, anchors, connected components, centroid), duplicate helpers, detectors on derivative fallback
├── images_triage.py        # NEW: triage of a round (outcomes, numbers, triage.json), sheet.html and overview rendering (Jinja2 templates below)
├── images_cli.py           # CHANGED: triage, pick, overview; add --theme/--subject/--no-source; check --require-coverage; list --theme
├── build.py                # CHANGED: placed-only copy, credits, set.json; validates all records
├── check.py                # CHANGED: I3 placed-only assertion; I7/I8/L1 registered via images
├── schemas/image-record.schema.json   # copied from contracts/
└── templates/
    ├── local/sheet.html.j2        # NEW: contact sheet (not deployed)
    └── local/pool.html.j2         # NEW: pool overview (not deployed)

zoo/site/images/
├── series/siebdruck.yaml   # CHANGED: themes (ids, prompts, aspect, scene, alt, reserve), negative + negative_history, palette, duplicate_max_bits
├── <six 016 ids>/image.yaml       # CHANGED: theme, subject, checks.style/duplicate/measures
└── <theme>-<subject>/      # NEW: about 100 record directories, image.yaml + three .webp, no PNG

docs/website.md             # CHANGED: library section (themes, rounds, triage, picks, overview, placing)
specs/016-emotional-imagery-motifs/contracts/checks.md   # CHANGED: note that 019 changes I1–I5, C1
.github/workflows/site.yml  # CHANGED only if the deep check needs more time (timeout); job logic unchanged

tests/website/
├── test_images_record.py   # extended: optional source.file, theme/subject, empty placements, I8
├── test_images_series.py   # extended: themes, negative_history
├── test_images_placement.py, test_images_checks.py   # extended: placed-only build, detector fallback
├── test_images_style.py    # NEW: I6 on synthetic scenes (in-palette passes; orange sky, off-palette, scattered accent fail; centroid)
├── test_images_triage.py   # NEW: outcomes, numbering, twins, sheet content, subjects without shown candidate
├── test_images_pick.py     # NEW: picks → records (no PNG, scene/alt from series), none → next.txt, atomic failure
├── test_images_overview.py # NEW: grouping, counts against minimum and cap
└── test_images_coverage.py # NEW: L1, L2
tests/imagery/test_gen_manifest.py   # extended: themes, seed scheme, --only, next.txt
```

**Structure Decision**: single project as in 016. The new triage and sheet code goes into one module `images_triage.py` so `build` and `check` keep importing only `images.py` (no heavy extra at build time). The two local HTML pages use Jinja2 templates under `templates/local/` to make clear they are never part of `_site/`. Records keep the 016 layout (one directory per image) so every existing tool, the compliance blocks and the CI job work unchanged.

## Phase 0 and 1 outputs

- [research.md](research.md): all unknowns resolved; no NEEDS CLARIFICATION remains.
- [data-model.md](data-model.md), [contracts/](contracts/), [subjects.md](subjects.md), [quickstart.md](quickstart.md): written.

## Risks and open points for the task phase

- **Calibration data**: the 016 renders (`~/zoo-imagery/out6/`) and the rejected series must still be on the Spark; if they are gone, I6 is calibrated on the six approved records alone and the rejected-series test is dropped from the acceptance (noted in `validation.md`).
- **Spark availability**: a full round needs the machine for about a day; the task order puts calibration and the draft pass first so the long render starts with checked subjects.
- **Owner time**: about 300 shown candidates to look at; the sheet is one file per round. If the owner prefers smaller sittings, `--only` renders theme by theme and each theme gets its own sheet.
- **Deployment approval after migration**: the six changed records change `set.json`, so the next deploy asks for approval once (research R10); the job summary explains it.
- **Theme balance**: picks may leave a theme under its minimum; reserves and further rounds close the gap; the feature is done only when `check --require-coverage` passes.

## Complexity Tracking

No constitution violations. Not applicable.
