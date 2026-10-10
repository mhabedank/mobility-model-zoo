# The zoo website

The website at https://mhabedank.github.io/mobility-model-zoo/ is a set of static pages generated from the registry (feature 008, [spec](../specs/008-zoo-website/spec.md)). Nobody edits a page by hand: every model fact comes from the same files as the model card, and the build fails when something does not add up.

## Pages and where their content comes from

| Page | Content | Source |
|---|---|---|
| Start page `/` | purpose, topics, model tiles, principles | `zoo/site.yaml`, `zoo/topics.yaml`, every `model.yaml` and release record |
| Model page `/models/<name>/` | value proposition, quickstart, interface, worked examples, quality and speed, use and limits, provenance, versions, citation | `model.yaml`, `zoo/models/<name>/site.yaml`, release records, `results/<version>/*.json`, `examples/`, the published model card |
| Output format `/formats/<id>/` | every field with type, allowed values and meaning | the format's JSON schema and `zoo/formats/<id>.yaml` |

Only published models get a page; unpublished models appear on the start page as "in progress". Format pages are never removed, so the documentation of an old format stays reachable. The data model is in [data-model.md](../specs/008-zoo-website/data-model.md).

## Website text of a model (`site.yaml`)

The only hand-written text per model ([schema](../src/mobility_model_zoo/site/schemas/site.schema.json)):

- `tagline`, `audience`, `differentiators` (three to five), `hardware_note`: prose. Numbers appear only as placeholders such as `{metric:quality.comparison_composite}` or `{metric:performance.latency_9k_chars_s}`. They resolve against the results of the latest release and each one links to a note that says what it is measured against.
- `quickstart_example`: the example whose output the quickstart shows.
- `metric_cards`: the headline numbers of the quality section, optionally with a comparison.
- `charts`: `quality_vs_speed` and `latency_per_machine`, each with a metric-name prefix and a label file. Without charts the section shows the metric cards and the full metric table.
- `motif`: a picture in `src/mobility_model_zoo/site/static/img/motifs/`, in the grammar of the identity sheet (round caps, 8° lean, one mint element, ink brackets).

Gate rule 17 validates `site.yaml` against the release candidate, so a published release always builds. Example outputs are read from the published model card at `published.repo_commit` and used only if the card hashes to `published.card_sha256`.

## Commands

```bash
uv run zoo site build                 # render into _site/ (fetches example outputs once, cached in .cache/site/)
uv run zoo site check --a11y          # every check below; --offline skips external links
uv run zoo site serve                 # http://localhost:8000/mobility-model-zoo/
uv run pytest tests/website           # offline tests on a frozen registry; -m slow for the browser tests
```

The browser checks need `uv sync --extra release --group site-check` and `uv run playwright install chromium` once.

## Checks that block publication

All checks are listed in [checks.md](../specs/008-zoo-website/contracts/checks.md). In short:

- Facts: every number equals its source and is printed on the model card too (F1, F4); hand-written text contains no numbers (F2); nothing is called accuracy (F3).
- Examples: outputs parse, validate and quote the text at their offsets (B3); only synthetic example texts (B4).
- Links: internal links and anchors resolve (L1), external links answer (L2), legal links on every page (L3).
- Privacy: no resource from another host (P1), no request to another host and no cookie in the browser (P2), no branding or advertising (P3).
- Accessibility: axe-core WCAG 2.1 AA in light and dark mode (A1), complete without JavaScript (A2), text alternatives (A3), keyboard (A4).
- Weight: page size and deferred scripts (S1), Largest Contentful Paint at most 2 s on a slow mobile connection (S2).

## Publishing

`.github/workflows/site.yml` builds and checks the site for pull requests and deploys it from `main` on changes to `zoo/`, the site code or the legal pages, after every successful `release-publish` run and on demand. One-time setup by the owner: GitHub → Settings → Pages → Source: **GitHub Actions**.

## Identity

The design tokens (`static/css/tokens.css`) and components come from the Claude Design identity sheet in [specs/008-zoo-website/design/source/](../specs/008-zoo-website/design/source/). Changing the identity means changing `tokens.css` and `site.css`, not the templates. The Open Graph image is rendered by `scripts/site_og_image.py`. Fonts are Figtree and JetBrains Mono under the SIL Open Font License, served from the site itself.
