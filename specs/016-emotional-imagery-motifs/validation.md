# Validation: Emotional mobility imagery and prominent model motifs

Date: 2026-10-14 · Branch `claude/zoo-website-emotional-imagery-6d19f5` · [quickstart.md](quickstart.md)

## Build and checks (quickstart steps 1, 3, 6, 7)

- `uv run zoo site build`: 9 pages (start, quickstart, roadmap, 2 models, 2 formats, 404, **credits**), 6 preview images, 12 "Coming next" cards.
- `uv run zoo site check --a11y --offline`: every check passes, including the new ones:
  - static: M (M1 coverage, M2 grammar), I (I1 records, I2 series), I3 markup and files, C1 credits, X1 no text on images, S1 split;
  - browser: A (axe light and dark, no-JS, keyboard, A5 reflow, S2 LCP, **S3 CLS ≤ 0.1, S4 bytes per page**, D6 placement, **M3 ink distance, M4 sizes, M5 contrast**), O3 card contrast;
  - preview cards O1, O2, O4, O5 with the motif centred on its plate.
- `uv run zoo compliance render && uv run reuse lint`: compliant (1380 files); REUSE gains one `CC0-1.0` annotation per image, the notices a "Website imagery" section, the record of processing a synthetic-imagery note.
- `uv run pytest tests/website tests/imagery -m "not slow"`: 277 passed, 2 skipped (the three `test_motifs_*` and four `test_images_*` files are new).

## Images (quickstart steps 2 and 4)

Imported with `zoo site images add` from the Qwen-Image-2512 renders on the Spark (see [selection.md](selection.md)). Derivative sizes (480 / 960 / 1600 px, in bytes):

| Record | 480 | 960 | 1600 |
|---|---|---|---|
| hero-train-dawn | 12 754 | 29 320 | 50 078 |
| topic-productdev-interior | 17 636 | 37 904 | 59 922 |
| topic-security-workshop | 17 260 | 39 922 | 65 072 |
| topic-condmon-wheelset | 21 890 | 50 334 | 81 980 |
| model-scout-large-window | 10 184 | 22 212 | 36 508 |
| model-picket-forest-bench | 15 852 | 36 568 | 57 972 |

All far below the caps (60 / 140 / 300 KB); the flat poster style compresses well. Repository growth: 6.4 MB (`zoo/site/images/`, source PNGs included).

Rejections seen at import, each by the rules without override:
- `start-hero` seed 1021 (the owner's pick Q6): YuNet found a 22 px face at score 0.58 (the distant platform silhouette). Replaced by seed 1022.
- `topic:security` dashboard seeds 1011 and 1013 (picks Q50, Q52): RapidOCR read the dial digits (`400`, `30`, `00` …). The dashboard subject is not viable under FR-009; the topic uses the workshop subject.

Fallback (step 4) tested in `tests/website/test_images_placement.py`: removing a model's record makes its page use the topic image; a missing topic image prints a warning and leaves the motif alone.

## Motifs

Shown names covered by M1 on the real registry and roadmap: scout-large, picket-forest (tiles and pages); picket-forest-board, scout-large-reader-test, pace-cnn, hum-fan, hum-bearing, picket-mlp, mode-cnn, cell-soh, gnss-guard, scout-large-languages, jtbd-cluster, rough-road, v2x-guard, picket-signal, cairn-base (roadmap). Nine motifs were added; `cell-soh` was redrawn upright after M3 found its ink too close to `mode-cnn`.

M3 uses the Jaccard distance of the ink masks (≥ 0.5) rather than a raw pixel difference: two of the five pre-existing motifs sit at only 10–11 % pixel difference although they are clearly different, so the pixel measure could not separate "different" from "near-duplicate".

## Roadmap side effect

`cairn-base` was registered by PR #27 without a roadmap entry, which fails RM2 and therefore every site build (also on `main`). With the owner's consent an entry was added (first release, in progress). Q4 2026 and H1 2027 were full (RM4, six open entries), so it sits in H2 2027; moving it is a recorded roadmap edit.

## Reproducibility (step 5)

`zoo site images check --regenerate` needs the GPU container and was not run in this session. The records carry revision, container digest (`sha256:3732…`) and sampling parameters; the renders predate the generator's move into the repository, so `generator.commit` is `unversioned` for this first set.

## Open

- **User test** (SC-001, SC-003), five people:
  1. Show the start page for five seconds. Ask: "What did you see? One or two words." Count answers that name a mobility scene or a feeling ("morning", "departure", "calm"); "gloomy" or "cheap" counts against.
  2. Show the start page once more, then three motifs on plates (scout-large, picket-forest, hum-fan) without names and ask which model each belongs to, from the tile list.
  3. Record the answers here. Pass: ≥ 4 of 5 on both questions. Can share the session with the pending 008 SC-001 test.
- GitHub environment `site-images` (owner, one-time; docs/website.md "Image approval").
- `generator.commit` becomes a real commit once a render runs from the repository's `scripts/imagery/gen.py`.
