# Contract: site checks added or changed by feature 016

Extends [008 checks](../../008-zoo-website/contracts/checks.md) and the preview-card checks of [012](../../012-social-preview-images/contracts/checks.md). A check that is not listed here stays as it is. Each check names the requirements it enforces.

> Feature 019 changes I1 to I5 and C1 (optional `source.file`, empty placements, placed-only credits and build, detector fallback to the 1600 px derivative) and adds I6, I7, I8, L1 and L2: see [019 checks](../../019-mobility-image-library/contracts/checks.md).

## New checks

| Id | Kind | Rule | Requirement |
|----|------|------|-------------|
| **M1** | static | Every model the site shows (start tiles, roadmap entries, "Coming next" cards, model pages, preview cards) resolves to a motif through `motifs.resolve`. The finding names the model. | FR-019, FR-021, FR-025 |
| **M2** | static | Every motif file follows the grammar: viewBox `0 0 96 96`; one group with `skewX(-8)`; cut caps (`stroke-linecap="square"`, feature 023); stroke widths only 4.5, 5, 8, 12 or 16; colours only `var(--text)`, `var(--border-strong)` and `var(--mark)`; exactly one `var(--mark)` element; no `<text>`, gradient or raster image; at most 1.5 KB. | FR-019 |
| **M3** | browser | Each motif is rasterised at 96 px on its plate. For every pair, the ink masks overlap by at most half (Jaccard distance ≥ 0.5), so near-duplicates are caught while thin, different motifs pass. | FR-020 |
| **M4** | browser | On start tiles the motif is at least 64 px tall, on roadmap entries and "Coming next" cards at least 40 px, in the model hero it is visible at 390 px width. | FR-022, FR-023 |
| **M5** | browser | Motif strokes reach at least 3:1 contrast against the plate in light and dark mode. | FR-024 |
| **I1** | static | Every `zoo/site/images/<id>/image.yaml` validates against [image-record.schema.json](image-record.schema.json); every check in `checks` is `pass`; the source PNG and each derivative exist and match their `sha256`; derivatives are within their byte caps (60, 140, 300 KB); no two records share a placement; every placement names a topic or a model the site shows. | FR-005, FR-012 |
| **I2** | static | Each record's `generation.prompt` equals a subject of its series followed by the series' style text, and `negative_prompt` equals the series' negative text; `generation.model` is one of the series' models and `model_licence` is in the accepted set. | FR-003, FR-010, FR-011 |
| **I3** | static | Every image in a built page has a matching record, `width` and `height`, an `alt` equal to the record's, `srcset`, and `loading="lazy"` unless it is the start hero. Images appear only on the start page, model pages and the credits page (FR-007). Every file in `assets/images/` is used by a record (no orphans). Every derivative carries the IPTC `DigitalSourceType = trainedAlgorithmicMedia` marker. | FR-005, FR-007, FR-013, FR-016, FR-029 |
| **I4** | deep (`zoo site images check --deep`) | On the source PNG: no face detection with score ≥ 0.5 and box height ≥ 16 px; no OCR token with confidence ≥ 0.7 and at least two alphanumeric characters. | FR-009, FR-010 |
| **I5** | deep (`--regenerate`, optional, GPU machine only) | Regenerating from the record, in the container image the record names, yields a PNG whose perceptual hash (64-bit pHash) differs from the source's by at most 4 bits; a bit-identical file is reported as such. Reported, not required in CI. | FR-018, SC-008 |
| **C1** | static | `/credits/` exists and lists every image record with scene, the AI-generated disclosure (model, licence, date, hardware class) and placements. Every page that shows an image links to it from the footer with the words "AI-generated". | FR-013 |
| **C2** | compliance | `zoo compliance render` produces the `REUSE.toml`, `THIRD_PARTY_NOTICES.md` and record-of-processing blocks for every image and generating model; `reuse lint` passes (existing C-L1). | FR-015 |
| **S3** | browser | Cumulative Layout Shift ≤ 0.1 on every page. | FR-029 |
| **S4** | browser | Bytes transferred per page at 390 px width and device pixel ratio 2, without fonts: ≤ 600 KB on pages that show images, ≤ 300 KB on others. The finding names the heaviest file. | FR-028 |
| **X1** | static | On a page with images, no text node sits inside an element positioned over an image. The stage markup is a `figure` whose only overlap is the plate (SVG). | FR-004 |

## Changed checks

| Id | Before | After | Reason |
|----|--------|-------|--------|
| **S1** | HTML ≤ 150 KB per page; site total without fonts ≤ 300 KB (preview cards excluded) | HTML ≤ 150 KB per page (unchanged); site total without fonts, preview cards **and image derivatives** ≤ 300 KB; scripts deferred (unchanged) | The total would count images that no single page loads. Per-page weight moves to S4. |
| **S2** | LCP ≤ 2 s (Fast 3G, 4× CPU) | Unchanged; now also measured on pages with the start-hero image | FR-028 |
| **A3** | Every `img` and `role="img"` SVG has a text alternative | Unchanged. Motifs on plates stay decorative unless they carry the only name of an item. | FR-005 |
| **P1** | No resource from another host | Unchanged. Images are served from `assets/images/`. | FR-014 |
| **O2, O3** (012) | Layout inside the centre safe area, contrast | Unchanged. A preview card with an image backdrop is built only if it passes both; otherwise without. | FR-026 |
| **008 FR-015, branding brief "no stock photos"** | Forbade scene photographs | Replaced for generated illustrated images meeting I1 to I4 | Owner decision of 2026-10-13 |

## Check order and exit

`zoo site check` runs the new static checks with the others. `--a11y` adds the browser checks (M3, M4, M5, S2, S3, S4). `zoo site images check --deep` runs I4 and is also run by the CI job `site-images` when `zoo/site/images/**` changes. Any failing check fails the command with exit code 1 and names the image or model.

## Approval

FR-017 is met by the GitHub environment `site-images`, whose required reviewer is the owner.
- The `deploy` job reads `assets/images/set.json` (image ids and `sha256` of each record) from the build and from the live site.
- Equal digests: no prompt. Different digests: the job uses the environment and waits for approval. The job summary lists added, changed and removed images with scene, series, model and placements.
- Rejecting the deployment leaves the live site unchanged.

## Fallbacks that warn but do not fail

A missing start-hero, topic or model image (spec Story 3, FR-016) prints one warning per placement, falls back as listed in the [data model](../data-model.md) and does not fail the build.
