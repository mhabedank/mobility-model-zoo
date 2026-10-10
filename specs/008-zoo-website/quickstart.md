# Quickstart: validating the zoo website (008)

This guide shows how to prove the feature works end to end. The commands, checks and page contents are defined in [contracts/cli.md](contracts/cli.md), [contracts/checks.md](contracts/checks.md) and [contracts/site-tree.md](contracts/site-tree.md).

## Prerequisites

- Repository root, Python ≥ 3.12, `uv`.
- `uv sync --extra release --group site-check`, then `uv run playwright install chromium`, needed for the accessibility check only.
- Network access to huggingface.co for the first build, which fills `.cache/site/`. Later builds can use `--offline`.

## 1. Build and check locally

```bash
uv run zoo site build
uv run zoo site check --a11y
uv run zoo site serve        # http://localhost:8000/mobility-model-zoo/
```

Expected:
- `site: 3 pages, 1 models (4 in progress)` plus the format page and the 404 page.
- The check passes with no findings.

## 2. Scenarios

| # | Do | Expect | Proves |
|---|---|---|---|
| 1 | Open the start page | Topics productdev, security, condition-monitoring; scout-large tile "published" with 0.1.2 and a link; four tiles "in progress" without links | US3, FR-002, FR-003 |
| 2 | Open `/models/scout-large/` | Sections 1–10 in the order of site-tree.md; install line pinned to `scout-large/v0.1.2`; the composite shows 0.72 with "agreement with frontier reference models, pilot-v2" | US1, FR-006–FR-014 |
| 3 | Copy the quickstart into a fresh venv and run it | Output equal to the JSON shown under the quickstart example | SC-002, FR-007 |
| 4 | Validate every example JSON on the page against `formats/jtbd-span-v1/` using only that page's field table | All three validate; every quote equals `text[start:end]` | SC-003, US2 |
| 5 | Disable JavaScript and reload the model page | All content is present; only the copy buttons are gone | FR-021, A2 |
| 6 | Switch the OS to dark mode | Dark tokens apply; the axe run in step 1 already covered both themes | FR-020 |
| 7 | Open DevTools → Network and Application on every page | Only same-origin requests; no cookies; no localStorage entries | SC-005 |
| 8 | Click every footer link | Imprint, privacy notice (with its new "Website" section), copyright policy and licence open | FR-016, SC-009 |

## 3. Negative tests (each must fail the build or check)

Run these on a scratch branch or against the fixture registry in `tests/website/fixtures/`:

| Change | Fails with |
|---|---|
| Write `0.72` into `zoo/models/scout-large/site.yaml` instead of `{metric:quality.comparison_composite}` | F2 |
| Reference `{metric:quality.does_not_exist}` | B2 |
| Change one `start` offset in the cached example output | B3 |
| Add `<link href="https://fonts.googleapis.com/...">` to the base template | P1 |
| Remove the imprint link from the footer | L3 |
| Set `--muted` as text colour on a job highlight | A1 (dark) |
| Delete `zoo/models/scout-large/site.yaml` | B1 |
| Add a field to the output schema without a meaning in `zoo/formats/jtbd-span-v1.yaml` | B5 |

## 4. Publication

1. Owner, once: under GitHub → Settings → Pages, set the source to "GitHub Actions".
2. Merge to `main`. The `site` workflow builds, checks and deploys. Expect the site at `https://mhabedank.github.io/mobility-model-zoo/`.
3. After the next `release-publish` run, the site workflow starts on its own (`workflow_run`), and the model page shows the new version without any hand edits (SC-008).
4. The HF org card (`docs/hf-org/README.md`, uploaded to the Space) and the repository README link to the site (FR-025).

## 5. Automated tests

```bash
uv run pytest tests/website                 # unit, golden, property tests (offline, fixture registry)
uv run pytest tests/website -m slow         # browser: axe light/dark, no-JS, network/cookie capture
```
