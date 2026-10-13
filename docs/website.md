# The zoo website

The website at https://mhabedank.github.io/mobility-model-zoo/ is a set of static pages generated from the registry (feature 008, [spec](../specs/008-zoo-website/spec.md)). Nobody edits a page by hand: every model fact comes from the same files as the model card, and the build fails when something does not add up.

## Pages and where their content comes from

| Page | Content | Source |
|---|---|---|
| Start page `/` | purpose, topics, tiles of published models, "Coming next" cards of upcoming models, principles | `zoo/site.yaml`, `zoo/topics.yaml`, every `model.yaml` and release record, `zoo/roadmap/roadmap.yaml` |
| Roadmap `/roadmap/` | what the zoo plans to release in the next quarter and the two half-years after it (feature 015) | `zoo/roadmap/roadmap.yaml`, release records |
| Quickstart `/quickstart/` | the five-minute walk-through: environment, install line, program and printed output of picket-forest and scout-large, and the common mistakes | [docs/quickstart.md](quickstart.md); `{install:<model>}`, `{snippet:<model>}` and `{output:<model>}` are filled from the latest published version of that model, so the page cannot drift from the cards |
| Model page `/models/<name>/` | six layers of increasing depth (feature 014): overview, quality and speed, limits and status, quickstart, reference (interface and worked examples), details and documents (all metrics, provenance, versions, citation) | `model.yaml` (including the card short forms), `zoo/models/<name>/site.yaml`, release records, `results/<version>/*.json`, `examples/`, the published model card |
| Output format `/formats/<id>/` | every field with type, allowed values and meaning | the format's JSON schema and `zoo/formats/<id>.yaml` |

The layers and what each may contain are in [page-layers.md](../specs/014-model-page-layout/contracts/page-layers.md). The overview shows the release status from the release record (with "Experimental: not ready for production use." for experimental releases), the usage class, the licence and the `card.not_for` points; the limits layer opens with the unmet criteria and `card.limits_short` before any code. The depth budgets (words and items per layer) are one table in `src/mobility_model_zoo/site/budgets.py`, shared by the release gate and the site checks.

Only published models get a page; unpublished models appear on the start page as "Coming next" cards from the roadmap. Format pages are never removed, so the documentation of an old format stays reachable. The data model is in [data-model.md](../specs/008-zoo-website/data-model.md).

## Roadmap and pace review (feature 015)

The roadmap is one record, [zoo/roadmap/roadmap.yaml](../zoo/roadmap/roadmap.yaml) ([schema](../src/mobility_model_zoo/site/schemas/roadmap.schema.json), [data model](../specs/015-website-roadmap/data-model.md)), and the constitution's section "Roadmap and Delivery Pace" says how it is kept.

- **Horizons**: three, the next quarter and two half-years: `2026-Q4`, `2027-Q1..Q2`, `2027-Q3..Q4` (a half-year that does not start in January or July is written like `2027-Q2..Q3` or `2027-Q4..2028-Q1`).
- **Entries**:
  - **Kind**: `new-model` (working name until registered), `first-release` of a registered model, or `update` of a published one. The order inside a horizon is the priority order.
  - **Stage**: `in-progress` only while someone works on it; otherwise `planned`.
  - **Text**: `text` (at most 20 words) and `precondition` (at most 8 words) carry no numbers.
- **Moving and dropping**:
  - `planned` never changes.
  - To move an entry, append `{date, to, reason}` to `moves` and set `horizon` to the new id.
  - To drop it, add `dropped: {date, reason}`. A dropped entry stays in the record.
- **Delivery** comes from the release records:
  - A `new-model` or `first-release` entry is delivered by the first published version of its `model`.
  - An `update` entry is delivered by the release named in `delivered_by: {model, version}`.
  - Delivered entries leave the pages and stay in the record.

**Every quarter**, after it ends:

1. `uv run zoo roadmap pace 2026-Q4 --write` writes `zoo/roadmap/reviews/2026-Q4.md`. It covers delivered early, on time or late, due and not delivered, moved, dropped, unplanned releases, delivery rate and trend.
2. Fill in the "Re-planning" section of that file: how the next horizons use the measured pace.
3. Roll the horizons forward, record the moves, set `as_of`, and run `uv run zoo roadmap check`.

Checks (RM1–RM8 in `zoo roadmap check`, CI and `zoo site build`; RM9 in `zoo site check`, [contract](../specs/015-website-roadmap/contracts/checks.md)):

| Check | What it guarantees |
|---|---|
| RM1 | schema, unique ids |
| RM2 | agreement with the model registry; every registered unpublished model has an entry |
| RM3 | text rules |
| RM4 | horizons, moves, at most six open entries per horizon |
| RM5 | `planned` unchanged since the entry was added (git history) |
| RM6 | `as_of` at most 100 days old, no open entry in an ended horizon; a warning in the last 14 days of the first horizon |
| RM7 | a filled review for every closed quarter before the horizons roll forward |
| RM8 | `delivered_by` names a published release |
| RM9 | pages show exactly the open entries, in order, with correct counts |

`ZOO_TODAY=YYYY-MM-DD` sets "today" for rehearsals. A stale or unreviewed roadmap stops the site build and CI, but never a release: `zoo check` and the release pipeline do not read the roadmap.

## Website text of a model (`site.yaml`)

The only hand-written text per model ([schema](../src/mobility_model_zoo/site/schemas/site.schema.json)):

- `tagline`, `audience` (at most 25 words), `differentiators` (three or four; title at most 5 words, text at most 20), `hardware_note`: prose, without the release status (it is generated). Numbers appear only as placeholders such as `{metric:quality.comparison_composite}` or `{metric:performance.latency_9k_chars_s}`. They resolve against the results of the latest release and each one links to a note that says what it is measured against.
- `quickstart_example`: the example whose output the quickstart shows.
- `metric_cards`: at most four headline numbers of the quality layer, optionally with a comparison (drawn as a bar pair).
- `charts`: `quality_vs_speed` and `latency_per_machine`, each with a metric-name prefix and a label file. Without charts the section shows the metric cards and the full metric table.
- `motif`: a picture in `src/mobility_model_zoo/site/static/img/motifs/`, in the grammar of the identity sheet (round caps, 8° lean, one mint element, ink brackets).

Gate rule 17 validates `site.yaml` against the release candidate, including its word limits, so a published release always builds. Gate rule 18 checks the card short forms in `model.yaml` (`not_for`, `limits_short`, `unmet_criteria`; see [adding-a-model.md](adding-a-model.md)). Example outputs are read from the published model card at `published.repo_commit` and used only if the card hashes to `published.card_sha256`.

## Commands

```bash
uv run zoo site build                 # render into _site/ (fetches example outputs once, cached in .cache/site/)
uv run zoo site build --no-images     # pages only, without Chromium; such a build fails check O1
uv run zoo site check --a11y          # every check below; --offline skips external links
uv run zoo site serve                 # http://localhost:8000/mobility-model-zoo/
uv run pytest tests/website           # offline tests on a frozen registry; -m slow for the browser tests
```

The preview images and the browser checks need `uv sync --extra release --group site-check` and `uv run playwright install chromium` once.

## Checks that block publication

All checks are listed in [checks.md](../specs/008-zoo-website/contracts/checks.md). In short:

- Facts: every number equals its source and is printed on the model card too (F1, F4); hand-written text contains no numbers (F2); nothing is called accuracy (F3).
- Examples: outputs parse, validate and quote the text at their offsets (B3); only synthetic example texts (B4).
- Links: internal links and anchors resolve (L1), external links answer (L2), legal links on every page (L3).
- Privacy: no resource from another host (P1), no request to another host and no cookie in the browser (P2), no branding or advertising (P3).
- Accessibility: axe-core WCAG 2.1 AA in light and dark mode (A1), complete without JavaScript (A2; the field table is on the format page, the model page links it), text alternatives (A3), keyboard (A4).
- Depth (feature 014, [checks](../specs/014-model-page-layout/contracts/checks.md)): card short forms present (D1), word and item budgets per layer (D2), what each layer may contain and no code before the limits (D3), status and terms in the overview (D4), layer order and old anchors (D5), placement on screen in the browser (D6).
- Weight: page size and deferred scripts (S1), Largest Contentful Paint at most 2 s on a slow mobile connection (S2).
- Preview images: share line rules (B6), text fits (B7), metadata, size and format (O1), layout (O2), contrast (O3), same text as the registry and the page (O4), address matches the content (O5). Details in [specs/012-social-preview-images/contracts/checks.md](../specs/012-social-preview-images/contracts/checks.md).

## Preview images for shared links

When a page link is shared on LinkedIn, Mastodon, Slack, X, Bluesky or in a messenger, the preview shows an image made for that page. `zoo site build` draws one per shareable page (start page, every published model, every output format) from the template `templates/og/card.html.j2`, in headless Chromium, at 1200 × 630:

- the zoo mark and wordmark, the page title (the model name), a one-line share text, and for models the labels `experimental`, `deprecated` and `non-commercial` as the latest release record states them; the model page shows the same labels at its top;
- the model motif in two corners; mark and title inside the centre square, so a square crop in a messenger keeps them.

Nobody designs or uploads an image: a newly published model gets its image in the same deploy as its page. The image's file name, `assets/og/<page>-<hash>.png`, carries a hash of everything drawn, so a changed image gets a new address and platforms that cache previews fetch it; an unchanged one keeps its address.

The share text is `share_line` in the model's `site.yaml` (or in `zoo/site.yaml` for the start page), else the tagline. It has at most 90 characters, no free-standing numbers (an image cannot carry the note that says what a number is measured against), no `{metric:…}` placeholders and only characters the site font draws. Gate rule 17 checks it before every publish (B6).

To see how a platform shows a page after the deploy, paste its URL into the LinkedIn Post Inspector or a draft post on Mastodon or Slack. Platforms cache previews for days; a new image address is picked up on the next share.

## Publishing

`.github/workflows/site.yml` builds and checks the site for pull requests and deploys it from `main` on changes to `zoo/`, the site code or the legal pages, after every successful `release-publish` run and on demand. One-time setup by the owner: GitHub → Settings → Pages → Source: **GitHub Actions**.

## Identity

The design tokens (`static/css/tokens.css`) and components come from the Claude Design identity sheet in [specs/008-zoo-website/design/source/](../specs/008-zoo-website/design/source/). Changing the identity means changing `tokens.css` and `site.css`, not the templates. The preview images use the same tokens in the dark colour scheme, with their own styles in `static/css/og.css`. Fonts are Figtree and JetBrains Mono under the SIL Open Font License, served from the site itself.
