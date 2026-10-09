# Implementation Plan: Zoo website with a landing page for scout-large

**Branch**: `008-zoo-website` | **Date**: 2026-10-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/008-zoo-website/spec.md`

## Summary

A static website for the Mobility Model Zoo, published on GitHub Pages: a start page and one detail page per published model, scout-large first. A new `zoo site` command group renders the site from the same sources as the Hugging Face model card. These sources are the `Registry` (`model.yaml`, release records, `results/<ver>/*.json`, `topics.yaml`), the output schema of the model, and the example outputs of the published card. The only hand-written model text is a small `site.yaml` per model. It holds the value proposition and differentiators, and every number in it is a reference to a release metric. Jinja2 templates implement the identity delivered by Claude Design (`design/source/`), using self-hosted OFL fonts, CSS tokens for light and dark mode, inline SVG charts drawn from the results, and an output viewer that is fully readable without JavaScript. A `zoo site check` command blocks publication on:

- broken links,
- numbers without a source,
- third-party requests or cookies,
- accessibility violations (axe-core in light and dark mode),
- licence findings.

A GitHub Actions workflow builds, checks and deploys the site on pushes to `main` and after every release publish.

## Technical Context

**Language/Version**: Python ≥ 3.12, the same as the package. The site output is static HTML5, CSS and one small vanilla JS file.

**Primary Dependencies**:
- Already in the `release` extra: `jinja2`, `pyyaml`, `jsonschema`, `typer`, `httpx`.
- New: `markdown-it-py` (MIT) for the limitation, intended-use and other markdown fields.
- New dev/CI group `site-check`: `playwright` (Apache-2.0) with Chromium, plus vendored `axe-core` (MPL-2.0) for the accessibility check.
- No Node toolchain and no frontend framework.

**Storage**: Files only.
- Sources: `zoo/` and `src/mobility_model_zoo/site/`.
- Build output: `_site/`, gitignored.
- Example outputs: fetched from the published HF card at the release revision and cached in `.cache/site/` (gitignored).

**Testing**:
- pytest in `tests/website/`: unit tests, golden HTML for the fixture registry, and property tests (no literal numbers in templates or `site.yaml`, links resolve, no external URLs in `src`/`href` of assets).
- A `slow`-marked browser test runs axe-core through Playwright. CI runs it in the site workflow.

**Target Platform**:
- Hosting: GitHub Pages, served at `https://mhabedank.github.io/mobility-model-zoo/`, with all links relative.
- Browsers: evergreen browsers, mobile first. Content works without JS.

**Project Type**: A static-site generator inside the existing Python package, used as a CLI (`zoo site build|check|serve`).

**Performance Goals**:
- Main content in under 2 s on a mobile connection (SC-007).
- Under 150 KB per page excluding fonts. Fonts are 60 KB WOFF2 in total, preloaded.
- No render-blocking JS.

**Constraints**:
- No third-party requests and no cookies (FR-015).
- WCAG 2.1 AA in both themes (FR-020).
- No model fact without a source (FR-004).
- English only.
- No Miskatonic branding (FR-017).
- Builds offline when the example cache is filled.

**Scale/Scope**:
- At launch: 1 start page, 1 model page (scout-large), 4 models listed as "in progress".
- Then: one page per newly published model, each needing only a `site.yaml`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / section | Touched? | How the design complies |
|---|---|---|
| I. Problem-first | No | The site describes, it does not extract. |
| II. Grounded evidence | Yes (presentation) | The output viewer shows each quote at its offsets in the input. The build checks that `text[start:end] == quote` for every shown item, so an invalid example fails the build. An empty item list is presented as a valid result. |
| III. Measure before optimizing, metric naming | Yes | Every metric is rendered with its `reference`, `benchmark` and `hardware` taken from the results JSON. The renderer refuses metrics that lack them. The word "accuracy" is blocked for model-labeled tasks by a check on the rendered text, alongside the existing card rule. |
| V. Budgets per task | Yes | Hardware and memory come from `performance.json` with their origin (hardware string). No emulator numbers exist for scout-large. For MCU models the measurement origin is printed as on the card. |
| VI. Clean provenance | Yes | Only the synthetic examples (`examples/SOURCES.yaml`, `source: synthetic`) are shown. The build refuses an example whose source is not `synthetic` or a declared redistributable source. Training-source attribution is linked from the release (training-data summary), not copied. |
| IX. Reproducible, dated releases | Yes | The site never publishes model files. Model pages only reflect published releases (`published_versions`). Deprecated versions are marked. Example outputs come from the card at the release's HF revision, so they are what was published. |
| X. Scope discipline | No | — |
| Project scope & layout | Yes | The site is shared across topics, so it is not topic code. The package lives at `src/mobility_model_zoo/site/`, and per-model text sits next to the model in `zoo/models/<name>/site.yaml`. A new topic or model needs no code change (tested like `test_new_topic_needs_no_code_change`). |
| Tasks and releases | Yes | It hooks into the one release pipeline: `release-publish.yml` triggers a site rebuild, and a new gate rule 17 ("site text") in `zoo check` validates each model's `site.yaml` before publication, so a release cannot break the site. There is no second publication path for models. |
| Resources & cost | Yes | GitHub Pages and Actions are free for public repos. No cash budget is needed. |
| Compliance (owner direction 2026-10-08) | Yes | The privacy notice is extended through `PRIVACY.md.j2` with a "Website" section naming GitHub as host and its access logs. The site links to the existing imprint and privacy pages. There are no cookies, no analytics and no third-party resources. Fonts (OFL-1.1), axe-core (MPL-2.0, CI only, not deployed) and the mark are covered in `REUSE.toml.j2` and `LICENSES/`. |

**Gate result (pre-design)**: PASS, no violations.

**Gate result (post-design)**: PASS. Three design choices were re-checked:
- Fetching example outputs from the published card keeps one source of truth (IX).
- Numeric references in `site.yaml` prevent unsourced claims (III).
- The fixture registry keeps tests offline.

No entries are needed in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/008-zoo-website/
├── spec.md
├── branding-brief.md        # prompt given to Claude Design
├── design/                  # delivered identity (raw bundle + extracted sources, fonts, mark)
├── plan.md                  # this file
├── research.md              # Phase 0
├── data-model.md            # Phase 1
├── quickstart.md            # Phase 1 validation guide
├── contracts/
│   ├── cli.md               # zoo site build | check | serve
│   ├── site-yaml.schema.json# per-model site text, numbers only by reference
│   ├── site-tree.md         # URL layout and what each page must contain
│   └── checks.md            # every check that blocks publication
└── tasks.md                 # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
src/mobility_model_zoo/site/
├── __init__.py
├── build.py           # Registry -> page contexts -> HTML into _site/
├── context.py         # SiteModel/SiteRelease/... (data-model.md), fact resolution
├── examples.py        # example outputs: HF card at release revision, cache, offset check
├── charts.py          # inline SVG charts from results JSON (quality vs speed, latency per machine)
├── schema_doc.py      # output-format JSON schema -> field table rows
├── check.py           # link, provenance, wording, third-party, licence checks; axe runner
├── cli.py             # Typer sub-app mounted as `zoo site`
├── schemas/site.schema.json
├── templates/         # base.html.j2, start.html.j2, model.html.j2, partials/*.html.j2
└── static/
    ├── css/tokens.css     # light/dark tokens from design/source/identity-system.html
    ├── css/site.css
    ├── js/site.js         # copy buttons, viewer linking; nothing required for content
    ├── fonts/             # Figtree, JetBrains Mono (OFL-1.1) + OFL.txt notices
    └── img/mark.svg, favicon.svg, motifs/*.svg

zoo/models/scout-large/site.yaml          # value proposition, differentiators, motif, chart declarations
zoo/formats/jtbd-span-v1.yaml             # field meanings of the output format
zoo/site.yaml                             # site-wide settings and legal links
src/mobility_model_zoo/release/gate.py    # + rule 17 "site text"
.github/workflows/site.yml                # build -> check -> deploy-pages
src/mobility_model_zoo/compliance/templates/PRIVACY.md.j2   # + "Website" section
src/mobility_model_zoo/compliance/templates/REUSE.toml.j2   # + fonts/axe annotations
LICENSES/OFL-1.1.txt, LICENSES/MPL-2.0.txt
tests/website/                               # unit, golden, property, slow a11y test
tests/website/fixtures/                      # fixture registry incl. site.yaml and cached card
docs/website.md                           # how the site is built, checked, published
```

**Structure Decision**: The generator lives in the shared package next to `release/`, because it reuses `Registry` and the card helpers and is not topic code. Per-model prose lives with the model. The build output is never committed. GitHub Pages deploys from an Actions artifact, not from a branch.

## Complexity Tracking

No constitution violations.
