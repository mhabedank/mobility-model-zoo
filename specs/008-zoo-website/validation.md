# Validation record: zoo website (008)

Date: 2026-10-09. Branch `008-zoo-website` (renumbered from 007, because `007-picket-forest-release` already uses that number), working tree on top of 6e2ef4a. Machine: MacBook (macOS), Chromium headless shell 153 via Playwright 1.63.

## quickstart.md section 1: build and check

| Step | Result |
|---|---|
| `uv run zoo site build` | pass: `site: 4 pages, 1 models (4 in progress)` (start page, scout-large, format jtbd-span-v1, 404) |
| `uv run zoo site check --a11y` | pass: F1, F2, F3, F4, L1, L2, L3, P1, P3, S1, E1 and the browser checks A1-A5, P2, S2 without findings (A5, reflow at 390 px, was added after a 2 px sideways scroll caused by long metric names in the notes was found and fixed) |
| `uv run reuse --root . lint` | pass |

## quickstart.md section 2: scenarios

| # | Result | How |
|---|---|---|
| 1 | pass | start page screenshot at 1280 and 390 px; `tests/website/test_start_page.py` |
| 2 | pass | sections in order, install line pinned to `scout-large/v0.1.2`, composite 0.7234 with reference and `pilot-v2` (`test_model_page.py`) |
| 3 | pass, with a deviation | the quickstart code taken from the built page ran against `mobility-model-zoo/scout-large` at `v0.1.2` (model downloaded from Hugging Face, 125 s including the download) and returned exactly the JSON shown on the page. It ran in the repository's virtual environment, not in a fresh one installed from the git tag |
| 4 | pass | the three example outputs validate against the schema behind the field table; every quote equals `text[start:end]` (check B3 during the build) |
| 5 | pass | check A2 (JavaScript disabled) |
| 6 | pass | axe-core in light and dark (A1); screenshots in both schemes |
| 7 | pass | check P2: no request to another host, no cookie; `site.js` stores nothing |
| 8 | pass | check L3 plus L2 (all external links answer) |

## quickstart.md section 3: negative tests

Each is an automated test in `tests/website/` (fast) or `tests/website/test_browser.py` (slow):

| Change | Fails with | Test |
|---|---|---|
| `0.72` written into `site.yaml` | F2 | `test_literal_number_in_site_yaml_is_f2` |
| `{metric:quality.does_not_exist}` | B2 | `test_pitch_errors_name_unknown_metrics_and_examples` |
| wrong offset / overlapping quotes | B3 | `test_quote_not_at_its_offsets_is_b3`, `test_overlapping_quotes_are_b3` |
| Google Fonts link | P1, P2 | `test_third_party_font_is_p1`, `test_injected_faults_are_found` |
| imprint link removed | L3 | `test_missing_imprint_link_is_l3` |
| `--muted` text on a job highlight | A1 (dark) | `test_injected_faults_are_found` |
| `site.yaml` deleted | B1 and gate rule 17 | `test_missing_site_yaml_is_b1`, `test_missing_site_text_fails` |
| schema field without a meaning | B5 | `test_schema_field_without_meaning_is_b5` |

## Test suites

- `uv run pytest -q`: 718 passed, 13 skipped (whole repository).
- `uv run pytest -q -m slow tests/website`: 2 passed (browser checks and injected faults).
- `uv run zoo validate --all`: ok.
- `uv run zoo compliance check --ci`: ok. The repository stage first reported a false positive of the PII scan in `topics/security/research/notes/competition-open-models.md` (pattern `licence_plate_de` on a dataset name followed by its year, from commit 4b3e768); the text now reads "CAN-FD (2021)" (separate commit).

## Open

- SC-001 (three people from the target group, T066) runs after the first deploy.
- The first deploy needs the owner's one-time setting GitHub → Settings → Pages → Source: GitHub Actions, and a merge to `main`.
- `docs/hf-org/README.md` has the website link; the Hugging Face org card Space is updated by uploading that file, which is not done by this feature.
