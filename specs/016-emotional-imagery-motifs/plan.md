# Implementation Plan: Emotional mobility imagery and prominent model motifs

**Branch**: `claude/zoo-website-emotional-imagery-6d19f5` | **Date**: 2026-10-13 (revised the same day) | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/016-emotional-imagery-motifs/spec.md`

## Summary

The zoo website gets two things:

1. **Generated illustrated scenes** of mobility as an emotional stage: one on the start hero, one per topic, one behind each published model's hero. They are rendered on the project's own DGX Spark with open-weights models under Apache-2.0 (FLUX.2-klein-4B for drafts, Qwen-Image-2512 for finals) in the house style SIEBDRUCK (1970s modernist poster look, identity palette, one warm accent on the vehicle; research R13). Every image has a full recipe (model, revision, prompt, seed, steps, size), is checked automatically for faces and readable text, is cropped around a focal point into three WebP derivatives carrying the IPTC "trained algorithmic media" marker, and is disclosed as AI-generated on a credits page, in the footer, in the alt text and in the file. Images are published under CC0. The owner approves a changed image set once, as a GitHub environment approval on the site deployment.
2. **Motifs as the main figure**: one resolver for all motif uses, a motif for every model the site shows (eight roadmap names lack one today), a dark plate under every motif so strokes meet 3:1 in both colour schemes, larger sizes on tiles, roadmap and cards, a motif in the hero at phone width, and the motif centred and opaque on preview cards.

Research with decisions and rejected alternatives: [research.md](research.md). Entities: [data-model.md](data-model.md). Checks and commands: [contracts/](contracts/).

## Technical Context

**Language/Version**: Python 3.12 (project standard, `uv`)

**Primary Dependencies**:
- the existing `mobility_model_zoo.site`, `release` and `compliance` packages; Jinja2, jsonschema, PyYAML, Typer (all present);
- Playwright with axe-core for browser checks (existing `site-check` group);
- **new optional extra `images`**: Pillow, opencv-python-headless with the pinned YuNet model (MIT), rapidocr-onnxruntime (Apache-2.0). Only `zoo site images add` and `check --deep` import them (research R4, R5, R12);
- **generator (container only, never in the package)**: NGC PyTorch 25.09 + diffusers ≥ 0.41 on the Spark; models `black-forest-labs/FLUX.2-klein-4B` and `Qwen/Qwen-Image-2512`, both Apache-2.0 and not gated (R1).

**Storage**: files in the repository (images are website content like fonts and motifs, not datasets in the sense of Principle VI; at most 12 of them): `zoo/site/images/<id>/image.yaml` with the source PNG and three WebP derivatives, `zoo/site/images/series/siebdruck.yaml`, new motif SVGs under `site/static/img/motifs/`. Model weights stay in the Spark's Hugging Face cache. Output is the static `_site/`.

**Testing**: pytest (`tests/website`, new `test_images_*.py`, `test_motifs_*.py`, `test_credits.py`), slow browser tests with `-m slow`; `zoo site check --a11y`; `zoo site images check --deep`; `reuse lint`. Generator smoke test with a tiny step count in `tests/imagery` (skipped without GPU).

**Target Platform**: static pages on GitHub Pages; CLI on Linux and macOS developer machines and in CI; generator on the DGX Spark (arm64, CUDA 13).

**Project Type**: CLI and library generating a static website (single project), plus a standalone generator script.

**Performance Goals**:
- unchanged from 008: HTML ≤ 150 KB per page; LCP ≤ 2 s on Fast 3G with 4× CPU slowdown;
- changed: site total without fonts, preview cards and images ≤ 300 KB (S1); per-page transfer at 390 px, DPR 2, without fonts ≤ 600 KB with images and ≤ 300 KB without (S4); CLS ≤ 0.1 (S3);
- derivative caps 60 / 140 / 300 KB at 480 / 960 / 1600 px;
- at most 12 images; sources and derivatives under about 25 MB in git;
- generation: about 4 s per draft (klein) and about 60 s per final (Qwen) on the Spark.

**Constraints**:
- no third-party requests, cookies or scripts at run time (008 P1, P2); no hosted image API (Principle V);
- no branding, advertising or funding (P3, compliance C-G2); prompts name no real places, operators or brands (FR-010);
- no text on images (FR-004); images never on quickstart, format, roadmap or 404 pages (FR-007);
- people only if not identifiable; no readable text (FR-008, FR-009);
- AI-generated disclosure in four places (FR-013);
- everything works without JavaScript (A2); reduced-motion and data-saver visitors see no motion effects;
- no cash cost; local compute and GitHub runners only.

**Scale/Scope**: 4 to 12 images; 13 motifs (5 existing, 8 new); 1 new page (`/credits/`); generator script + container; 4 new commands; 14 new or changed checks; 2 changed templates and 3 changed partials; 1 CI job; 1 GitHub environment.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Principles I, II, VII and X concern the JTBD extraction task and are not touched. The feature changes no model, benchmark or release record.

| Principle or section | Touched | How the plan complies |
|---|---|---|
| III Measure before optimizing | no | No model result changes. The site's own budgets are measured by checks S1 to S4 before and after. |
| IV Riskiest assumption first | yes | Riskiest assumption: the illustrated house style reads as deliberate design rather than as AI cliché, and the final model keeps the accent-on-vehicle rule and the no-text rule reliably enough that 4 seeds per subject yield a usable image. Tested first: the full series was rendered (60 images) and the owner picked all six placements before any template work, so the assumption held for this set. Remaining kill criterion: if the five-person test (SC-001) returns "gloomy" or "cheap" from two or more people, the series is re-rendered with an adjusted style text and the owner is asked. |
| V Small and local | yes | Generation and detection run locally on the Spark and CPU; no hosted API. The heavy extra is optional and never loaded by `zoo site build`. |
| VI Clean provenance | yes | Every image records the generating model, revision and licence, the full prompt and sampling parameters (data model). Only Apache-2.0 or MIT models whose terms place no restriction on outputs are used; the images are published under CC0, so no restriction carries over and the zoo's usage class is untouched. Personal data: identifiable faces and readable text are rejected automatically; no real person or place is depicted. Synthetic origin is disclosed (R6). |
| IX Reproducible, dated releases | yes (website only) | Image records carry date, recipe, tool versions and hashes; regeneration is checked (I5). Model releases are unchanged. |
| Roadmap and delivery pace | no | The roadmap record is read, not changed. Motifs for roadmap names are resolved by entry id so renames keep them (R10). |
| Resources and cost discipline | yes | No cash cost. Cost order: local first. Model weights are downloaded once and cached; the Spark is the named local compute. |
| Development workflow and quality gates | yes | This plan lists touched principles. New checks run in `zoo site check` and CI; `reuse lint` covers images and models through generated blocks (C2). |
| Compliance first-class (project memory) | yes | Disclosure, provenance and content checks are automated; the owner's only manual step is the deployment approval (FR-017). |
| Zoo private, no branding (project memory) | yes | Prompts forbid brands; OCR rejects any readable text (I4); P3 unchanged. |

**Gate result before research**: pass. **After design**: pass. No deviation to justify.

## Project Structure

### Documentation (this feature)

```text
specs/016-emotional-imagery-motifs/
├── plan.md                 # This file
├── spec.md
├── research.md             # R1–R13: generation, licences, processing, detection, disclosure, composition, approval, art direction
├── data-model.md           # image record, series, motif, credits entry, generated compliance blocks
├── quickstart.md           # validation guide
├── contracts/
│   ├── image-record.schema.json
│   ├── checks.md           # M1–M5, I1–I5, C1–C2, S3–S4, X1; changed S1, S2, O2/O3
│   └── cli.md              # generator; zoo site images add/check/list/remove; changed build and compliance render
├── checklists/requirements.md
└── tasks.md                # /speckit-tasks output (not created here)
```

### Source Code (repository root)

```text
scripts/imagery/
├── gen.py                  # NEW: generator (series file → PNGs + manifest), runs in the container
├── Dockerfile              # NEW: zoo-flux from NGC PyTorch + diffusers
└── README.md               # NEW: build, cache, render in three commands

src/mobility_model_zoo/site/
├── motifs.py               # NEW: resolve(reg, name), lint (M2), coverage (M1)
├── images.py               # NEW: records, series, placements, fallbacks, credits context, set.json (I1–I3, C1, X1)
├── images_process.py       # NEW: crop, encode with IPTC marker, byte caps, detectors (R3–R5); imports the `images` extra lazily
├── images_cli.py           # NEW: `zoo site images` commands (contracts/cli.md)
├── build.py                # CHANGED: image copy, credits page, M1 gate, warnings, set.json
├── check.py                # CHANGED: S1 split, new static checks registered
├── a11y.py                 # CHANGED: M3–M5, S3, S4 in the browser run
├── og.py                   # CHANGED: motif via motifs.resolve, centred opaque motif, optional backdrop
├── roadmap.py              # CHANGED: motif_name delegates to motifs.resolve
├── schemas/image-record.schema.json   # copied from contracts/
├── static/css/site.css     # CHANGED: .plate, stage, hero, topic card, credits block, sizes
├── static/css/og.css       # CHANGED: centred motif
├── static/img/motifs/      # 8 NEW motifs; scout-large-hero.svg kept for the reference layer
└── templates/
    ├── start.html.j2       # CHANGED: hero image, topic cards with images, plates on tiles
    ├── credits.html.j2     # NEW
    ├── roadmap.html.j2     # CHANGED: plate size
    ├── base.html.j2        # CHANGED: footer disclosure + link, per-page credits block
    ├── partials/hero.html.j2      # CHANGED: stage + plate, visible at phone width
    ├── partials/upcoming.html.j2  # CHANGED: motif plate on mini cards
    └── og/card.html.j2     # CHANGED

src/mobility_model_zoo/compliance/
├── release_checks.py       # CHANGED: .svg in text suffixes for C-G2
└── templates/              # CHANGED: REUSE.toml.j2, THIRD_PARTY_NOTICES.md.j2, record-of-processing.md.j2

zoo/site/images/
├── series/siebdruck.yaml   # NEW: art direction
└── <id>/                   # NEW: image.yaml + <id>.png + three .webp per image
LICENSES/CC0-1.0.txt        # NEW
pyproject.toml              # CHANGED: extra `images`
.github/workflows/site.yml  # CHANGED: site-images job, deploy with environment site-images on digest change
scripts/ci/select_tests.py  # CHANGED: area `images` for zoo/site/images/** and scripts/imagery/**
docs/website.md             # CHANGED: imagery and motif rules
specs/008-zoo-website/contracts/checks.md  # CHANGED: S1 note, photo rule superseded

tests/website/
├── test_motifs_resolve.py, test_motifs_lint.py, test_motifs_coverage.py
├── test_images_record.py, test_images_placement.py, test_images_fallback.py, test_images_series.py
├── test_images_checks.py   # synthetic fixtures: face, text (marked slow, needs extra)
├── test_credits.py, test_start_page.py (extended), test_model_page.py (extended)
├── test_og_motif.py
└── test_browser.py (extended: M3–M5, S3, S4)
tests/imagery/test_gen_manifest.py   # manifest shape; render skipped without GPU
```

**Structure Decision**: single project, as in 008 to 015, plus a generator under `scripts/imagery/` that is deliberately outside the package: its dependencies (torch, diffusers) belong to the container on the Spark, not to the wheel. Image handling in the package is split so `build` and `check` never import the heavy extra. Images live under `zoo/` (content, triggers the site workflow, outside the wheel), motifs under the package's static files (identity, shipped with the generator).

## Phase 0 and 1 outputs

- [research.md](research.md): all unknowns resolved; no NEEDS CLARIFICATION remains.
- [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md): written.

## Risks and open points for the task phase

- **Structural errors in renders** (Principle IV): the final model is non-distilled and each subject gets 4 to 8 seeds; the kill criterion is in the Constitution Check. FLUX.2-dev stays as a stronger, gated fallback (R1).
- **Detector false positives**: resolved by rendering another seed, never by override (R4).
- **Dark plate in light mode**: a visual change beyond the owner's request; the owner sees it in the first preview build and can ask for an alternative (R9).
- **Spark availability**: generation needs the VPN link to `cst-ai-02`; imports and checks do not. The task order keeps generation in one early group.
- **User test** (SC-001, SC-003): needs five people; can share the session with the pending 008 SC-001 test.

## Complexity Tracking

No constitution violations. Not applicable.
