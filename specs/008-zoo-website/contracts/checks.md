# Contract: checks that block publication

`zoo site check` runs all of these checks. Any finding means exit code 1 and no deploy. `B*` checks run during `zoo site build` already.

| ID | Check | Spec |
|---|---|---|
| B1 | `site.yaml` (each model) and `zoo/site.yaml` validate against their schemas; every published model has a `site.yaml`. The same per-model check runs in the release gate `zoo check` (rule `site-text`), so a published release always passes B1 | FR-005, SC-008 |
| B2 | Every `{metric:…}` placeholder resolves in the latest release's results; the metric has `reference` + `benchmark` (quality) or `hardware` (performance) | FR-004, FR-010 |
| B3 | Every example output parses as JSON and validates against the output schema; the fetched card hashes to `published.card_sha256`; for span formats, `text[start:end] == quote` for every item and spans do not overlap | FR-009, Principle II |
| B4 | Every example source in `SOURCES.yaml` is `synthetic` or a declared redistributable source | FR-018 |
| B5 | Schema paths and the meaning entries in `zoo/formats/<id>.yaml` match one to one | FR-008 |
| F1 | Every model fact on a page is listed in `_build/facts.json` with a source file that exists and a value equal to the source value formatted by `card.num()` | FR-004, SC-004 |
| F2 | No free-standing number (`(?<![\w.,-])\d+(?:[.,]\d+)*(?![\w-]|[.,]\d)`) in `site.yaml` prose outside placeholders, or in template text nodes (attribute values, `<style>` and SVG geometry are excluded) | FR-004 |
| F3 | Rendered text of model-labeled tasks does not contain "accuracy" (case-insensitive) | FR-010, Principle III |
| F4 | Numbers on the model page equal the numbers in the card rendered for the same release (`card.render`) | SC-004 |
| L1 | Every internal link and anchor resolves inside `_site/`; in `404.html` the root-relative prefix `/mobility-model-zoo/` is mapped to `_site/` | FR-022 |
| L2 | External links to HF, GitHub (at tag or main) and legal pages answer 200 (HEAD, with retry); release-file links point at files that exist at the tag | FR-022 |
| L3 | Every page links the imprint, privacy notice and copyright policy; every model page has links to the licence, limitations section and AI Act note | FR-016, SC-009 |
| P1 | No resource reference (`src`, `link href`, CSS `url()`, `@import`, `srcset`, `poster`) points to another host; `<a href>` navigation links are allowed | FR-015, SC-005 |
| P2 | During the browser run, all requests go to the local server and no cookie is set on any page | FR-015, SC-005 |
| P3 | No text, image or link with Miskatonic branding except the imprint URL; no funding, pricing or consulting links | FR-017 |
| A1 | axe-core (`wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`) reports zero violations for every page in the light and the dark colour scheme | FR-020, SC-006 |
| A2 | With JavaScript disabled, each model page still contains the quickstart code, the field table, every example's JSON and the limitations | FR-021 |
| A3 | Every `img` and SVG with `role="img"` has a text alternative; every chart has a data table or a text list of its values | FR-020 |
| A4 | Keyboard: tabbing through each page reaches the skip link first, then every link, button and viewer control in document order; every focused element shows the focus ring (computed `outline-width` ≥ 2px) | FR-020 |
| A5 | Reflow: at a width of 390 px no page scrolls sideways (WCAG 1.4.10); tables and code blocks scroll inside their own box | FR-020 |
| S1 | Main HTML ≤ 150 KB per page; total size without fonts ≤ 300 KB; no `<script>` without `defer` | SC-007 |
| S2 | Under Playwright network throttling (Fast 3G profile: 1.6 Mbps down, 150 ms RTT) and 4× CPU slowdown, Largest Contentful Paint of every page ≤ 2,000 ms | SC-007 |
| C1 | `reuse lint` passes, including fonts, mark and generated assets; this check comes from the existing `zoo compliance check` | FR-019 |
