# Contract: `zoo site` commands

This is a Typer sub-app, mounted in `src/mobility_model_zoo/release/cli.py` the same way as `compliance` and `data`. Like every `zoo` command, it runs from the repository root. Exit codes follow the existing CLI: `0` means success, `1` means a check failed (`GateFailed`), and `2` means a usage or configuration error (`UsageError`/`ZooError`).

## `zoo site build`

```
zoo site build [--out _site] [--offline] [--refresh-examples]
```

- Renders every page listed in `site-tree.md` into `--out`, which defaults to `_site/`. The output directory is emptied first.
- Fetches the example outputs of each published model from its HF card at the latest release's `public_revision`, unless they are cached in `.cache/site/`.
  - `--offline` uses the cache only and fails if an entry is missing.
  - `--refresh-examples` ignores the cache.
- Writes `_site/_build/facts.json`. This file maps every rendered model fact (CSS selector or page + key) to its source file and key path. The deploy step removes it.
- Stops with exit code 1 on any of these build errors:
  - a `site.yaml` that fails its schema,
  - a placeholder that does not resolve,
  - a metric without a reference or hardware,
  - an example whose output does not parse or validate, or has a quote that does not match its offsets,
  - a schema path without a meaning entry, or the reverse,
  - a published model without a `site.yaml`.
- Prints one line per page written and a final summary: `site: <n> pages, <m> models (<k> in progress)`.

## `zoo site check`

```
zoo site check [--out _site] [--a11y/--no-a11y] [--only F1,L1,...]
```

Runs the checks from `checks.md` against a built site. `--a11y` is on in CI; it needs the `site-check` dependency group and Playwright's Chromium. Every finding is printed as `<check id> <page> <detail>`. The command exits with 1 if there is any finding.

## `zoo site serve`

```
zoo site serve [--out _site] [--port 8000]
```

A local static server for preview, used by the a11y check. It serves under the sub-path `/mobility-model-zoo/` to mimic GitHub Pages, so relative-link mistakes show up locally.

## Workflow `.github/workflows/site.yml`

| Job | Steps |
|---|---|
| `build` | checkout, `uv sync --extra release --group site-check`, `playwright install --with-deps chromium`, `zoo site build`, `zoo site check --a11y`, remove `_site/_build`, `actions/upload-pages-artifact` |
| `deploy` | runs only on `main`; `needs: build`; environment `github-pages`; `actions/deploy-pages` |

Triggers:
- `push` to `main` on the paths `zoo/**`, `src/mobility_model_zoo/site/**`, `PRIVACY.md`, `COPYRIGHT_POLICY.md` and `.github/workflows/site.yml`;
- `workflow_run` of `release-publish` with `conclusion == success`;
- `workflow_dispatch`.

Pull requests run `build` and the checks, but not `deploy`.
