# Data model: Zoo website (008)

The site has no database. Every entity is a view over files that already exist, plus three small new source files (marked **new**). The `Registry` methods named below are in `src/mobility_model_zoo/release/registry.py`.

## Sources

| File | Status | Read through |
|---|---|---|
| `zoo/topics.yaml` | existing | `Registry.topics()` |
| `zoo/models/<name>/model.yaml` | existing | `Registry.model(name)` |
| `zoo/models/<name>/releases/<ver>.yaml` | existing | `Registry.record(name, ver)`, `published_versions(name)` |
| `zoo/models/<name>/results/<ver>/{quality,performance}.json` | existing | `Registry.results(name, ver, kind)` |
| `zoo/models/<name>/examples/*.txt` + `SOURCES.yaml` | existing | `Registry.examples(name)` |
| Output schema, e.g. `.../span/jtbd-span-v1.schema.json` | existing | by `output_format_version` |
| Published HF card `README.md` at `published.repo_commit` of the release record | existing (remote) | `site.examples` (cached, verified against `published.card_sha256`) |
| Chart label file named in `site.yaml` `charts[].labels`, e.g. `topics/productdev/recipes/figures/scout-large-comparison.json` | existing | display labels for comparison models, read at the release tag `<name>/v<ver>` |
| `zoo/site.yaml` | **new** | site-wide settings |
| `zoo/models/<name>/site.yaml` | **new** | per-model value proposition |
| `zoo/formats/<format>.yaml` | **new** | per-format field meanings |

## Entities

### SiteConfig (`zoo/site.yaml`, new)

| Field | Type | Rule |
|---|---|---|
| `title` | str | "Mobility Model Zoo" |
| `canonical_url` | URL | `https://mhabedank.github.io/mobility-model-zoo/` |
| `tagline` | str | no digits |
| `principles` | list of `{title, text}` | same four principles as the HF org card |
| `legal.imprint` | URL | `https://miskatonic-analytics.com/imprint.html` |
| `legal.privacy` | URL | `PRIVACY.md` on GitHub (main) |
| `legal.copyright` | URL | `COPYRIGHT_POLICY.md` on GitHub (main) |
| `repo` | URL | GitHub repository |
| `hf_org` | URL | Hugging Face org |

### Topic (from `topics.yaml`)

`id`, `title`, `description`, `collection` (HF collection URL). This entity has no rules of its own.

### SiteModel (from `model.yaml`, `site.yaml` and the release list)

| Field | Source | Rule |
|---|---|---|
| `name`, `topic`, `task`, `variant`, `title`, `summary` | model.yaml | — |
| `license`, `base_model`, `base_model_license`, `languages`, `pipeline_tag` | model.yaml | — |
| `intended_use`, `out_of_scope`, `limitations`, `input_output` | model.yaml `card.*` | rendered as markdown, HTML disabled |
| `install`, `how_to_run`, `citation` | model.yaml `card.*` | `{repo_id}`, `{revision}`, `<tag>` and `{text}` are filled the same way as in the card |
| `repos.public` | model.yaml | HF link |
| `status` | derived | `published`: at least one published version (record has `published` set) whose `deprecated` is null. `deprecated`: the latest published version has a `deprecated` object. `in_progress`: no published version. Sandbox models (`sandbox: true`) are excluded. |
| `latest` | derived | the highest published version (`parse_version`) |
| `releases` | list of SiteRelease | newest first |
| `pitch` | `site.yaml` | required when `status ≠ in_progress`; schema in `contracts/site-yaml.schema.json`; checked by the release gate (`zoo check`) before the first and every later publish, so the site build can rely on it |
| `output_format` | OutputFormat | from `latest.output_format_version` |

State transitions follow the release pipeline and are never set by hand:

```
in_progress --(zoo publish v1)--> published --(zoo deprecate latest)--> deprecated
published --(zoo publish next)--> published (latest moves)
```

### Pitch (`zoo/models/<name>/site.yaml`, new)

| Field | Type | Rule |
|---|---|---|
| `tagline` | str ≤ 120 chars | no digits outside placeholders |
| `audience` | str | who it is for |
| `differentiators` | list of 3–5 `{title, text}` | placeholders `{metric:<kind>.<metric_name>}` only; each placeholder must resolve in the latest release's results |
| `motif` | str (optional) | file name in `static/img/motifs/` |
| `quickstart_example` | str | file name in `examples/`; must exist and have an output |
| `charts` | list (optional) | each `{type: quality_vs_speed \| latency_per_machine, metrics: <metric-name prefix>, labels: <repo path of a label file>}`; no `charts` → no chart section, metric cards only |
| `hardware_note` | str (optional) | placeholders only for numbers |

### SiteRelease (from the release record)

`version`, `date`, `status` (schema enum: `experimental` / `released` / `deprecated`), `deprecated` (`null` or `{reason, successor}`), `change_type`, `changes` (markdown), `output_format_version`, `published` (`repo_commit` = HF commit of the publication, `tag` = HF tag such as `v0.1.2`, `published_at`, `card_sha256`), `links`. The links are:

- the HF tree at `published.repo_commit`,
- the training-data summary (`releases/<ver>.training-data-summary.md` on GitHub at the tag),
- the AI Act note (`<ver>.ai-act.md`),
- the compliance record.

A link is included only when its file exists.

### Metric (from the results JSON)

`kind` (quality/performance), `name`, `value`, `unit`, `description`, plus `reference` and `benchmark` for quality or `hardware` for performance, plus `n_items` and `date`.

Rules:
- A quality metric without `reference` or `benchmark`, or a performance metric without `hardware`, cannot be rendered. Referencing it is a build error.
- Display rounding uses `card.num()` so the site and the card show identical strings (SC-004).
- For model-labeled tasks the rendered label never contains "accuracy" (Principle III).

### Example (from `examples/` + the HF card)

| Field | Rule |
|---|---|
| `file`, `text` | from `examples/` |
| `source` | from `SOURCES.yaml`; must be `synthetic` (or a declared redistributable source) |
| `output` | parsed JSON from the card at `published.repo_commit` (card bytes must hash to `published.card_sha256`); must validate against the output schema |
| `spans` | derived, only for span formats (the format schema has `items[].quote`, `items[].start`, `items[].end`): for each item `(start, end, kind)`; build error if `text[start:end] != quote` or spans overlap. Other formats (e.g. MCU outputs `{"output": [...]}` from `device_examples`) are shown as input and output code blocks without spans |

### OutputFormat (schema + `zoo/formats/<id>.yaml`, new)

| Field | Source |
|---|---|
| `id` | e.g. `jtbd-span-v1` |
| `fields` | flattened from the JSON schema: `path` (`items[].quote`), `type`, `enum`, `required`, `nullable` |
| `meaning`, `empty_case`, `notes` per path | `zoo/formats/<id>.yaml` |
| `produced_by` | release versions whose record names this format |

Rule: every schema path has a meaning entry and every meaning entry matches a schema path. A mismatch fails the build.

### Page (build output)

| Page | Path | Built from |
|---|---|---|
| Start | `index.html` | SiteConfig, Topics, SiteModels |
| Model | `models/<name>/index.html` | SiteModel with `status ≠ in_progress` |
| Output format | `formats/<id>/index.html` | OutputFormat (kept for every format ever produced) |
| Not found | `404.html` | SiteConfig |
| Assets | `assets/**` | `static/` |
| Provenance map | `_build/facts.json` | every rendered fact with its source path; used by `zoo site check`, not deployed |
