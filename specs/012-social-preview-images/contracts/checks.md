# Contract: checks for preview images

These checks add to [specs/008-zoo-website/contracts/checks.md](../../008-zoo-website/contracts/checks.md). Each finding is printed as `<id> <page> <detail>` and blocks the deploy.

| Id | Check | Requirement |
|---|---|---|
| B6 | Share line rules ([data-model.md](../data-model.md)) for every published model, the zoo and every format. Also run by gate rule 17 for the model being released | FR-004, FR-006 |
| B7 | At render time: the title fits on one line in its 630 px box at 48 px or larger; the share line needs at most 3 lines | FR-011, edge cases |
| O1 | Every shareable page (start, published model pages, format pages) carries `og:image`, `og:image:type`, `og:image:width` = 1200, `og:image:height` = 630, `og:image:alt`, `twitter:card` = `summary_large_image`, `twitter:image`, `twitter:image:alt`. `og:image` is an absolute URL under `canonical_url`, and the file it names exists in `_site/`, is a PNG (signature and IHDR) of 1200 × 630, and is ≤ 300 KB. `404.html` points at the start image | FR-001, FR-008, FR-009, SC-001 |
| O2 | From the manifest `layout`: no element overflows its box, all text lies inside 48 px margins, and the mark and title boxes lie inside the centre square x ∈ [285, 915] | FR-008, FR-011 |
| O3 | axe-core `color-contrast` reports zero violations on each card HTML (`--a11y` only) | FR-011 |
| O4 | For each card: `title`, `line` and `labels` equal the values the registry gives for that page (model name; effective share line; release status, deprecation and usage class as on the page); `og:image:alt` and `twitter:image:alt` equal the manifest `alt` | FR-003, FR-012 |
| O5 | The hash in each file name equals SHA-256 recomputed from the card HTML, the asset bytes and the renderer id; `_site/assets/og/` contains no file that no page references | FR-010, FR-014 |

Changes to existing checks:
- **P1** and **P3** also run over the card pages `_site/_build/og/*.html`, which `pages()` skips because they live under `_build`. Findings name the card, e.g. `P1 _build/og/scout-large.html …`. This covers FR-007 (no third-party resource) and FR-015 (no branding or advertising) for the images.
- **S1** excludes `assets/og/` from the total site weight: visitors never load these files, only link-preview scrapers do, and O1 limits each one to 300 KB. The old `og.png` exemption goes away with the file.
- P2 is unchanged; rendering itself aborts every request that is not a `file:` URL (FR-007).
- C1 (`reuse lint`) covers the template and any new static files.
