# Contract: `zoo site` changes

Extends [specs/008-zoo-website/contracts/cli.md](../../008-zoo-website/contracts/cli.md). Only the changes are listed here.

## `zoo site build`

```
zoo site build [--out _site] [--offline] [--refresh-examples] [--images/--no-images]
```

- `--images` is the default. The build renders one preview image per shareable page into `_site/assets/og/` and writes `_site/_build/og.json` and `_site/_build/og/<slug>.html` (see [data-model.md](../data-model.md)).
- If `--images` is set and Playwright or its Chromium is not installed, the build exits with code 2 and prints: `images need the site-check group: uv sync --group site-check && uv run playwright install chromium (or pass --no-images)`.
- `--no-images` writes the pages and the manifest with the same image addresses, but no PNG files. Check O1 fails on such a build, so it cannot be deployed. It is meant for template work and for tests without a browser.
- New build errors (exit 1):
  - `B6 …`: a share line breaks a rule ([data-model.md](../data-model.md)).
  - `B7 <page>: title does not fit at 48 px` or `B7 <page>: share line needs <n> lines, at most 3`.
- The summary line becomes `site: <n> pages, <i> images, <m> models (<k> in progress)`.

## `zoo site check`

New check ids `O1`–`O5`; see [checks.md](checks.md). `--only O1,O4` works as for the other ids. O3 needs `--a11y`.

## `zoo check` (release gate)

Rule 17 "site text" also reports `B6` findings for the model being released. It makes no change to other rules.

## Workflow `.github/workflows/site.yml`

No step change: Chromium is already installed before `zoo site build`. The paths filter stays the same, because the card template lives under `src/mobility_model_zoo/site/**`.
