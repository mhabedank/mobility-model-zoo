# Research: Social preview images for every zoo page

Decisions for [plan.md](plan.md). Each entry: decision, rationale, alternatives considered.

## R1 When the images are made

- **Decision**: `zoo site build` renders the images, in the same run that writes the pages, from the same context. The `site` workflow already builds after every registry change on `main` and after every successful `release-publish`, so a new model gets its image in the deploy that brings its page.
- **Rationale**: no extra pipeline step, and no committed binary that can go stale (FR-005, SC-002). The image text comes from the same dictionaries as the page, so the two cannot disagree (FR-012).
- **Alternatives**:
  - Render at release time and commit the PNG: adds a step to `release-publish`, puts binaries in git, and leaves old images when the identity or the share line changes.
  - Render on request (an image endpoint such as Vercel OG or Cloudflare Workers): GitHub Pages is static, and a third-party service breaks the no-third-party rule (FR-007).
  - Design each image by hand, for example with Claude Design: does not scale and is the manual step the owner wants to avoid. Claude Design may still restyle the one template later.

## R2 Renderer

- **Decision**: headless Chromium through Playwright renders one HTML card per page with `page.screenshot` at 1200 × 630, device scale factor 1. The card uses `tokens.css`, the self-hosted woff2 fonts, the inline mark and the model motif SVG, the same assets as the site.
- **Rationale**:
  - Playwright and Chromium are already in the `site-check` dependency group and installed in the `site` workflow before `zoo site build` runs. No new dependency.
  - HTML layout handles line wrapping, font fallback and SVG. The same browser session can measure the layout (overflow, line count, bounding boxes) for check O2 and run axe on the card for contrast (O3).
  - The card reuses the website identity without redrawing it.
- **Alternatives**:
  - Pillow: needs hand-written line wrapping and cannot draw the SVG mark and motifs without cairo or resvg. Its text metrics differ from the browser's, so a separate fit check would be needed.
  - SVG template rendered with resvg plus fontTools for measuring: deterministic and fast, but needs two new dependencies, TTF instead of woff2 fonts, and a hand-written wrapping algorithm.
  - Satori-style JSX to SVG: a Node toolchain for one feature.

## R3 Build without a browser

- **Decision**: `zoo site build` gets `--images/--no-images`, on by default. With images on and Playwright or Chromium missing, the build stops with exit code 2 and the install hint. `--no-images` writes pages and the manifest with the same image addresses, but no PNG files. Check O1 then reports the missing files, so such a build can never be deployed.
- **Rationale**: the CI `test` job and most unit tests run without Chromium (`ci.yml` installs no browser). The image addresses are computed from the inputs, not the pixels (R5), so pages are identical with and without rendering.
- **Alternatives**: skip images silently when Playwright is missing. Rejected: a deploy could go out without images, unnoticed.

## R4 Layout and safe area

- **Decision**: one template, `og/card.html.j2`, with three kinds (`zoo`, `model`, `format`).
  - Full-bleed solid background from the identity, so the image stands on its own on light and dark platform themes.
  - Mark and wordmark at the top, centred.
  - The title in the middle, centred: the model name, format id or zoo name.
  - The share line below it, centred, at most 3 lines, maximum width 960 px.
  - Status labels as chips under the share line.
  - The model motif as decoration at the side edges, outside the safe area.
- **Fitting the title**: the title box is 630 px wide, the width of the safe square, so B7 and the safe-area check O2 measure the same thing. Font size steps 76 → 60 → 48 px for long names. If it still does not fit on one line in that box, the build fails (B7).
- **Safe area**:
  - Mark and title stay inside the centre square (x 285–915). That is what messengers keep when they crop to a square thumbnail.
  - All text stays inside 48 px margins.
- **Rationale**: LinkedIn, Facebook, X, Mastodon, Bluesky, Slack and Discord show 1.91 : 1 uncropped. WhatsApp and iMessage may crop to the centre square, and the model name must survive that crop.
- **Alternatives**: left-aligned layout like the old `og.png`. It loses the name in a centre-square crop.

## R5 Address that changes with the content

- **Decision**: the image goes to `assets/og/<slug>-<hash>.png`. `<hash>` is the first 12 hex digits of SHA-256 over:
  - the rendered card HTML,
  - the bytes of every asset the card loads (fonts, `tokens.css`, mark, motif),
  - the renderer identity: the Playwright version, read from the installed package metadata or, without Playwright, from `uv.lock`. Every Playwright release pins its Chromium revision, so the version identifies the browser too, and a build with `--no-images` yields the same addresses as one with images.

  The manifest records the inputs' digest.
- **Rationale**:
  - The address changes exactly when what is drawn can change. Platforms that cache previews by URL then fetch the new image (FR-010).
  - An unchanged registry yields the same addresses on every build (FR-014, SC-006), even if PNG encoders differ by a byte between machines.
  - Including the Playwright version makes an upgrade, which brings a new Chromium and may change antialiasing, produce new addresses.
  - Reading the Chromium revision from the installed browser was rejected: it is unknown without a browser, so `--no-images` builds would get different addresses.
- **Alternatives**:
  - Hash of the PNG bytes: not stable across machines.
  - A query string `og.png?v=…`: some scrapers drop query strings when they cache.

## R6 Share line rules (B6) and the release gate

- **Decision**: `site.yaml` gets an optional `share_line`. The text on a model image is `share_line`, or the `tagline` if no share line is given. That text must:
  - be at most 90 characters,
  - contain no `{metric:…}` placeholder,
  - contain no free-standing number (the F2 pattern; digits inside names such as "M3 Pro" stay allowed, as on the site),
  - use only characters in the Figtree latin subset (R7).

  `zoo/site.yaml` gets the same optional `share_line` for the start image, with the same rules. The format image uses the format's `title` from `zoo/formats/<id>.yaml`.

  `context.pitch_errors` checks these rules, so gate rule 17 (site text) rejects a release whose model would fail the image build (FR-006).
- **Rationale**: an image cannot carry the footnote that names what a number is measured against (Principle III). 90 characters fit in three lines at the chosen size, with margin. scout-large's tagline has 96 characters, so it gets a `share_line`.
- **Alternatives**: shorten the tagline automatically at a word boundary. Rejected: a cut sentence can say something different.

## R7 Characters the fonts cannot draw

- **Decision**: B6 rejects characters the shipped Figtree subset cannot draw. `og.LATIN_RANGES` lists the code points of the font's cmap (24 ranges: Basic Latin, Latin-1, a few Latin Extended letters and combining marks, dashes, quotes, bullet, ellipsis, euro, trade mark, arrows up and down, minus).

  `tests/website/test_og_fonts.py` reads the woff2 cmap with fontTools and brotli, if both are installed, and confirms that every drawable code point in the list is in the font.
- **Rationale**: a missing glyph would fall back to a system font or a box without any error. The first draft used the Google Fonts "latin" range list; the font test showed that the shipped subset lacks 61 of its code points (for example U+2010 hyphen, U+2030 per mille, U+FFFD), so the list now comes from the font itself.
- **Alternatives**: detect fallback in the browser. Rejected: `document.fonts.check` does not report per-glyph fallback reliably.

## R8 Metadata

- **Decision**: `base.html.j2` writes the following tags for every shareable page:
  - `og:image` (absolute URL under `canonical_url`), `og:image:type` (`image/png`), `og:image:width` (1200), `og:image:height` (630) and `og:image:alt`;
  - `twitter:card` (`summary_large_image`), `twitter:image` and `twitter:image:alt`.

  The alt text is `<title>, Mobility Model Zoo: <share line>`, plus the labels if any. The 404 page uses the start image and stays out of the manifest.
- **Rationale**: Open Graph is read by LinkedIn, Facebook, Mastodon, Slack, Discord, Bluesky and messengers. X needs `twitter:card` for the large format and falls back to `og:image` for the rest. Width and height let platforms show the image on the first share, before they download it.
- **Alternatives**: none worth keeping; the tag set is the platform standard.

## R9 File size, format and speed

- **Decision**:
  - PNG, flat colours.
  - Limit 300 KB per image (check O1). WhatsApp drops previews above roughly 300 KB; LinkedIn and X allow 5 MB.
  - One browser launch for all cards. Routing aborts every request that is not a `file:` URL (FR-007).
  - Expected time: about 0.3 s per card, under 10 s for the current site.
- **Rationale**: a stricter limit than the spec's 1 MB keeps WhatsApp working. Flat PNGs of this layout are around 60 to 150 KB.
- **Alternatives**: JPEG. Text edges get artefacts, and PNG is accepted everywhere.

## R10 Checks

- **Decision**: new checks O1–O5 in `zoo site check`, and B6/B7 in the build. Details are in [contracts/checks.md](contracts/checks.md).
  - O1: file, format, size and metadata.
  - O2: layout measurements recorded at render time.
  - O3: axe `color-contrast` on each card, run with `--a11y`.
  - O4: text parity between image, metadata and registry.
  - O5: the address hash matches the inputs, and there are no orphan images.
- **Rationale**: same pattern as feature 008. The build records what it did in `_site/_build/`, and the check verifies it independently before deploy (FR-011).

## R11 Old image and script

- **Decision**:
  - Remove `static/img/og.png` and `scripts/site_og_image.py`.
  - Drop the `og.png` exemption in `check.py`.
  - Point the `site` entry of `scripts/ci/select_tests.py` at the new files.
  - Update `docs/website.md`.
- **Rationale**: one generation path (FR-013).
