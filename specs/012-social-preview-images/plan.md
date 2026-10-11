# Implementation Plan: Social preview images for every zoo page

**Branch**: `012-social-preview-images` | **Date**: 2026-10-11 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/012-social-preview-images/spec.md`

## Summary

Every shareable page of the zoo website (start, each published model, each output format) gets its own preview image, 1200 × 630. The image shows:

- the zoo mark and wordmark;
- the page title (the model name, for model pages);
- a one-line share text with no numbers;
- for models, the labels `experimental`, `deprecated` and `non-commercial`, where the page shows them.

`zoo site build` renders the images in the same run that renders the pages, from the same context. It fills one HTML card template and screenshots it in headless Chromium through Playwright, which the site workflow already installs. Image addresses are content hashes of the inputs, so platforms re-fetch an image when it changes and see the same address when it does not.

The rules for the share line run in the release gate (rule 17) and in the build. New checks O1–O5 cover size, format, layout, contrast, text parity with the registry, and stable addresses, and block the deploy. The hand-made `og.png` and its script are removed.

## Technical Context

**Language/Version**: Python 3.11 (existing package `mobility_model_zoo`).

**Primary Dependencies**:
- Existing: Jinja2, Playwright with Chromium (`site-check` group), vendored axe-core 4.14.0.
- No new runtime dependency. fontTools is used only by an optional unit test when it is installed.

**Storage**: Files only.
- Input: `zoo/site.yaml` and `zoo/models/<name>/site.yaml`, each with an optional `share_line`.
- Output: `_site/assets/og/*.png` and `_site/_build/og.json`.

**Testing**: pytest.
- Fast tests: share line rules, metadata and manifest, built with `--no-images`.
- Slow, browser-marked tests: rendering, layout, O1–O5, and a new fixture model.

**Target Platform**:
- GitHub Pages: a static site.
- Link-preview scrapers of LinkedIn, Facebook, X, Mastodon, Bluesky, Slack, Discord, WhatsApp and Signal.

**Project Type**: Static site generator inside the existing CLI package.

**Performance Goals**: All images in under 60 s per build with five published models (SC-005). Expected about 0.3 s per card.

**Constraints**:
- 1200 × 630 PNG, ≤ 300 KB.
- No network during rendering.
- No third-party resources.
- Deterministic addresses.
- WCAG AA contrast.

**Scale/Scope**:
- Today 3 images: zoo, scout-large and jtbd-span-v1.
- Grows by one per published model or format.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Constitution 2.1.0.

| Principle / section | Check | Result |
|---|---|---|
| III. Metric naming: every number states its reference | No numbers on the image (B6) | Pass |
| V. Small and local | Rendering runs locally and in CI; no hosted service | Pass |
| VI. Clean provenance | Only zoo-owned mark and motifs and OFL fonts already shipped; no source text | Pass |
| IX. Releases only through the pipeline; "Non-commercial" on the website | Images come only from published releases; the NC, experimental and deprecated labels are on the image (FR-003, O4) | Pass |
| X / Project scope | No change needed for a new model or topic (FR-016) | Pass |
| Tasks and releases: one release gate | Rule 17 reports B6 (FR-006) | Pass |
| Resources & cost | Runs in the existing free CI; no cash budget | Pass |
| Compliance (owner direction 2026-10-08) | No third-party resource, no tracking, no branding (P1–P3 cover the cards) | Pass |

No violations. Post-design re-check: the design in research R1–R11 keeps all rows at Pass, and Complexity Tracking stays empty.

## Project Structure

### Documentation (this feature)

```text
specs/012-social-preview-images/
├── plan.md
├── research.md            # R1–R11
├── data-model.md          # share line, share card, manifest
├── quickstart.md
├── contracts/
│   ├── cli.md             # build --images/--no-images, B6/B7, gate rule 17
│   ├── checks.md          # B6, B7, O1–O5
│   ├── share-card.md      # layout, safe area, metadata tags
│   └── site-yaml-share-line.md
├── checklists/requirements.md
└── tasks.md               # /speckit-tasks
```

### Source Code (repository root)

```text
src/mobility_model_zoo/site/
├── og.py                      # NEW: share cards (context → card dict), share line rules (B6),
│                              #      input hash, render with Playwright (B7, layout), manifest
├── build.py                   # build(images=True): card per page, og meta into the page context
├── context.py                 # pitch_errors adds B6 → gate rule 17
├── check.py                   # O1, O2, O4, O5; P1/P3 also over _build/og/*.html; S1 excludes assets/og/
├── a11y.py                    # O3: axe color-contrast on each card HTML
├── facts.py                   # NUMBER (F2 pattern) moves here from check.py
├── templates/partials/hero.html.j2   # release-status chips (experimental, non-commercial) as on the image
├── cli.py                     # --images/--no-images, exit 2 without Playwright
├── schemas/site.schema.json          # share_line
├── schemas/site-config.schema.json   # share_line
├── templates/base.html.j2            # og:image*, twitter:* tags from the page's card
├── templates/og/card.html.j2         # NEW: card template (zoo, model, format)
└── static/
    ├── css/og.css                    # NEW: card styles on top of tokens.css
    └── img/og.png                    # REMOVED

zoo/models/scout-large/site.yaml      # share_line
scripts/site_og_image.py              # REMOVED
scripts/ci/select_tests.py            # site entry: drop the script, add og files
docs/website.md, docs/adding-a-model.md

tests/website/
├── test_share_line.py         # B6 cases, tagline fallback
├── test_og_meta.py            # meta tags, alt text, manifest, addresses stable (--no-images)
├── test_og_render.py          # slow: render, sizes, layout, O1–O5, new fixture model
└── fixtures/registry/…        # second published model with site.yaml for the "new model" test
tests/release/test_gate_site_text.py  # rule 17 reports B6
```

**Structure Decision**:
- All logic lives in one new module, `site/og.py`, next to the 008 site modules.
- The build calls it per page.
- Checks and the gate reuse its rule function and hash function, so there is one definition of each.

## Implementation Notes

1. **Card per page.**
   - `og.cards(reg, site, models, formats)` returns card dicts as in the data model.
   - The build puts `card` into the context of each shareable page. `base.html.j2` writes the metadata from it, and `404` gets the zoo card.
2. **Hash before rendering.**
   - The card HTML is rendered with relative asset URLs into `_site/_build/og/<slug>.html`.
   - The hash covers that HTML, the bytes of the files it loads and `renderer_id()`. It is computed before the PNG exists, so `--no-images` yields the same addresses.
   - `renderer_id()` is `playwright <version>`, read from the installed package metadata or, without Playwright, from `uv.lock`. The Playwright version pins the Chromium revision, and the address does not depend on whether a browser is installed (research R5).
3. **Render.**
   - One Chromium launch per build.
   - `page.route("**", abort unless file:)` blocks network access.
   - Wait for `document.fonts.ready`, then step the title size and measure. B7 fires if the title still does not fit or the line runs to more than 3 lines.
   - Record the boxes and overflow in `layout`, then take the screenshot.
4. **Checks.**
   - O1 parses the PNG header with `struct`; Pillow is not needed.
   - O5 recomputes the hash with `og.input_hash`.
   - O3 runs in the existing a11y browser session.
5. **Gate.** `context.pitch_errors` calls `og.share_line_errors(name, pitch)`. The zoo-level line is checked in the build only, because the zoo is not released.
6. **Removal.**
   - Remove `og.png`, the script and its `select_tests` entry.
   - Update `docs/website.md`. Document `share_line` in `docs/adding-a-model.md`.
7. **REUSE.** The new template and CSS fall under the catch-all `**` annotation in `REUSE.toml`. Nothing new needs annotating. Generated PNGs are not tracked.

## Complexity Tracking

No constitution violations; nothing to justify.
