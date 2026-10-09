# Research: Zoo website (008)

Each entry: decision, rationale, alternatives considered. Facts checked on 2026-10-09 against the repository and the delivered design.

## R1 Site generator

- **Decision**: A small generator inside the package (`mobility_model_zoo.site`), built on Jinja2 and the existing `Registry`, and exposed as `zoo site build|check|serve`.
- **Rationale**: The card renderer (`release/card.py`) already loads every fact the site needs through `Registry`: `model()`, `record()`, `published_versions()`, `results()`, `examples()`, `topic()`. Reusing it keeps the site and the card on one source (FR-004, SC-004), with no second toolchain to maintain. Jinja2 is already a dependency of the `release` extra.
- **Alternatives**:
  - MkDocs Material: markdown-centred, and it pulls in Google Fonts and its own JS by default.
  - Hugo or Eleventy: they need a Go or Node toolchain and would reimplement data loading.
  - Astro or Next static export: a framework is far too heavy for two page types.

## R2 Hosting and deployment

- **Decision**: GitHub Pages with "Source: GitHub Actions". The workflow `.github/workflows/site.yml` uses `actions/upload-pages-artifact` and `actions/deploy-pages`. Triggers:
  - push to `main` on paths `zoo/**`, `src/mobility_model_zoo/site/**`, `PRIVACY.md` and `COPYRIGHT_POLICY.md`,
  - `workflow_run` after `release-publish` completes successfully,
  - `workflow_dispatch`.

  Permissions are `pages: write` and `id-token: write`, used only in the deploy job.
- **Rationale**: This was the owner's decision. Deploying an artifact avoids a `gh-pages` branch full of generated files, and the triggers cover FR-022.
- **Alternatives**: deploying from a `gh-pages` branch (keeps generated files in git history); an HF static Space (rejected by the owner).
- **Owner action, once**: under Settings → Pages, set the source to "GitHub Actions". This is a repository setting and cannot be done from code.

## R3 Base URL

- **Decision**: All internal links and assets are relative. The canonical URL `https://mhabedank.github.io/mobility-model-zoo/` is configured once in `site.yaml`-level config (`zoo/site.yaml`) and used only for `<link rel="canonical">` and Open Graph tags.
- **Rationale**: The site then works under the project path, in local preview and under a later custom domain without a rebuild of the logic.
- **Alternatives**: absolute paths with a prefix, which break `file://` previews and need a prefix setting per environment.

## R4 Example outputs

- **Decision**: Example outputs are taken from the published HF card of the latest release, downloaded at `published.repo_commit` of its release record and verified against `published.card_sha256` (a mismatch is a build error). They are parsed with the same logic as `publish._examples_from_hub()`, which is moved to a shared helper that takes a revision. They are cached in `.cache/site/<model>/<version>.json`, keyed by `repo_commit`. The build then:
  - parses each output as JSON,
  - validates it against the model's output schema,
  - checks `text[start:end] == quote` for every item.

  A failure stops the build.
- **Rationale**: These are exactly the outputs users see on Hugging Face, produced by the gate (`Gate._run_example`) with the released files. FR-009 asks for output from the released model, and this is it. Nothing new is stored in git, and no published version is touched. Checked on 2026-10-09: the scout-large 0.1.2 card has three complete JSON examples, well under the gate's 4,000-character cap.
- **Alternatives**:
  - Running the 2.2 GB model in the site workflow: slow, and it duplicates the gate.
  - Committing outputs to `results/<ver>/examples.json`: a new artifact type that the existing three releases lack. Kept as a later improvement if HF access becomes a problem.
- **Edge**: if an output was truncated by the gate's cap, it no longer parses as JSON. The build then fails with a message naming the example; the fix is a shorter example in the next release.

## R5 Value proposition without unsourced numbers

- **Decision**: Each published model has `zoo/models/<name>/site.yaml` (schema in `contracts/site-yaml.schema.json`) with a tagline, an audience, differentiators and an optional motif. Numbers may appear only as placeholders of the form `{metric:quality.comparison_composite}` or `{metric:performance.latency_9k_chars_s_dgx_spark_gpu}`. The renderer replaces each placeholder with the formatted value from the latest release, which carries its reference or hardware into a footnote. A check rejects any digit outside placeholders in `site.yaml` (version strings excluded) and in the templates.
- **Rationale**: The value proposition is the only prose the release records do not hold (FR-005). Tying its numbers to metrics keeps it true after the next release and enforces Principle III's naming rule.
- **Release gate**: `zoo check` validates `site.yaml` (schema, placeholders against the candidate's results, quickstart example exists, chart declarations resolve) for every non-sandbox model. A release without valid page text cannot be published, so the automatic site rebuild after `release-publish` cannot fail on it.
- **Alternatives**: a `site` block in `model.yaml`, which would change a schema-validated file that `model_at_tag` re-reads for published cards and mixes marketing text into release metadata; free prose, which goes stale silently; a fallback to `summary` when `site.yaml` is missing, which would publish pages without a value proposition.

## R6 Charts

- **Decision**: Charts are declared per model in `site.yaml` (`charts: [{type, metrics, labels}]`); a model without the declaration gets metric cards only, so models with other metrics (e.g. MCU models) need no code change. For scout-large, the two charts are rendered as inline SVG at build time from `quality.json` and `performance.json`, in the style of the design sheet:
  - Quality against texts per minute (log scale). scout-large is the only filled mark. The best zero-shot small model is a dashed reference line. The generative comparison models are a band, or labelled points from the `comparison_composite_*` and `comparison_chunks_per_min_*` metrics.
  - Latency for one 9,240-character interview per machine, drawn as HTML bars. Bars come from the `latency_9k_chars_s*` metrics; the "fourth machine" placeholder in the mockup becomes the MacBook M3 Pro CPU (1.94 s).

  Each chart has a text alternative listing all values. The existing PNG figures stay for the HF card.
- **Rationale**: Inline SVG uses the theme tokens, so dark mode works, the charts are crisp, need no JS and add no request. It follows the design (`design/source/identity-system.html`, section 06).
- **Alternatives**: reusing the PNGs (no dark mode, blurry, the colours do not follow the tokens); a JS chart library (third-party code and a JS dependency for content).
- **Labels**: the display names of the comparison models (for example "Claude Opus 5.5 (reference)") are currently only in `topics/productdev/recipes/figures/scout-large-comparison.json`. The chart reads that file as it was at the release tag (`git show <name>/v<ver>:<path>`, like `card.model_at_tag`), so labels and numbers belong to the same release. Only the labels are taken from it; every number comes from the results JSON. If a metric has no label there, its id is shown instead.

## R7 Output-format documentation

- **Decision**: The field table is generated from the model's output JSON schema (`src/mobility_model_zoo/productdev/jtbd/span/jtbd-span-v1.schema.json`): names, types, enums, required and nullable. A per-format `description` file adds meanings: `zoo/formats/jtbd-span-v1.yaml`, with meaning, empty case and notes per field path. Every version of a format gets a stable anchor and is listed with the releases that produce it (`output_format_version` in the release records).
- **Rationale**: The schema is the contract the model validates against, so the documentation cannot drift from it. The mockup's invented values (`private_user`, `self_report`) show the risk. FR-008 and US2 scenario 3 (old formats stay reachable) are covered.
- **Alternatives**: hand-written tables (they drift); schema descriptions only (the current schema has no per-field prose, and adding it would change the model package).

## R8 Fonts, licences and REUSE

- **Decision**: Self-host the two WOFF2 files delivered by Claude Design. Verified with fontTools:
  - Figtree 2.002 and JetBrains Mono 2.211.
  - Both variable, Latin subset, covering ä ö ü ß € – ’.
  - Both licensed under the SIL OFL 1.1 (name table, IDs 0 and 14).

  Add `LICENSES/OFL-1.1.txt`, and annotate `src/mobility_model_zoo/site/static/fonts/**` in `REUSE.toml.j2` with the font copyright and `OFL-1.1`. Ship the OFL text next to the fonts. Also add `LICENSES/MPL-2.0.txt` for the vendored axe-core, which is used only in checks and never deployed.
- **Rationale**: FR-015 (no third-party loading) and FR-019 (the licence check passes). OFL allows bundling with any software as long as the licence text travels with the fonts.
- **Alternatives**: system font stacks only, which lose the identity; Google Fonts, which is a third-party request with known GDPR problems in Germany.

## R9 Accessibility check

- **Decision**: `zoo site check --a11y` serves `_site/` locally and opens every page in headless Chromium through Playwright, once with `prefers-color-scheme: light` and once with `dark`. It runs the vendored axe-core with the `wcag2a`, `wcag2aa`, `wcag21a` and `wcag21aa` tags, and any violation fails the check. A JS-disabled pass checks that the quickstart, field table, example output and limitations are present in the DOM.
- **Rationale**: SC-006 and FR-021. Static token contrast was already computed: all pairs pass in light mode. Dark mode fails one pair, `--muted` on `--job-bg` at 4.02:1. The fix is to never put muted text on highlights (only `--text`). axe will catch it if that rule is broken.
- **Alternatives**: pa11y or Lighthouse CI, which need Node; a static contrast-only check, which misses structure, labels and focus.

## R10 Third-party and cookie check

- **Decision**: Two checks:
  - A static check: every `src`, `href` of `link`/`script`/`img`, `url()` in CSS and `@import` must be relative or `data:`. Outbound `<a href>` links are allowed, since they are navigation and not resource loads.
  - A dynamic check in the Playwright run: every network request must go to the local server, and `document.cookie` and the context cookies must be empty.
- **Rationale**: SC-005, checked on every page.

## R11 Privacy notice and legal links

- **Decision**: Add a section "Website" to `PRIVACY.md.j2`, rendered through `zoo compliance render`. It covers:
  - the host (GitHub, Inc., US), and that GitHub processes visitors' IP addresses in access logs for security and operation;
  - the legal basis (Art. 6(1)(f) GDPR, the legitimate interest in providing the site securely);
  - that there are no cookies, no analytics and no third-party content;
  - a link to the GitHub privacy statement and the transfer basis GitHub states.

  Every page footer links to:
  - the imprint, `https://miskatonic-analytics.com/imprint.html`, reused by link per the owner decision, without other branding;
  - `PRIVACY.md` and `COPYRIGHT_POLICY.md` on GitHub;
  - the model licence.
- **Rationale**: FR-016 and FR-017, and the owner decision of 2026-10-08 on contact and imprint.
- **Alternatives**: a separate website privacy page, which would mean two notices to keep in sync.

## R12 Markdown fields

- **Decision**: Render `intended_use`, `out_of_scope`, `limitations` and `changes` with `markdown-it-py` in commonmark mode with HTML disabled.
- **Rationale**: These fields are markdown (bullets, inline code). Disabling HTML prevents markup injection from metadata. The library is small and MIT-licensed.
- **Alternatives**: a hand-written bullet parser, which is fragile; `python-markdown`, which allows raw HTML by default.

## R13 Interactivity without dependency

- **Decision**: One vanilla JS file, around 3 KB, loaded with `defer`. It adds copy buttons (hidden without JS), links quote ↔ JSON item in the output viewer (focus and `aria-pressed`), and nothing else. The theme follows `prefers-color-scheme` only; there is no toggle, so nothing is stored.
- **Rationale**: FR-021. A theme toggle would need `localStorage`, which is not a cookie but is still client storage, for little gain.

## R14 Status of unpublished models

- **Decision**: The start page lists every model from `Registry.model_names()` except sandbox models. A model without a published version shows the chip "in progress", its topic and task, and no link and no numbers. A model whose latest version is deprecated shows "deprecated" and links to its page with a banner.
- **Rationale**: FR-003, the spec's edge cases, and the same logic as `zoo index`.
