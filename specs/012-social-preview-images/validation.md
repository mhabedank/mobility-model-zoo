# Validation: Social preview images (feature 012)

Run on 2026-10-11 on branch `012-social-preview-images`, macOS, Playwright 1.63.0.

## Quickstart steps 1–6

| Step | Result |
|---|---|
| 1. `zoo site build` and `zoo site check --a11y` on the real registry | `site: 4 pages, 3 images in 0.5 s, 1 models (4 in progress)`. Every check passes: F1–F4, L1–L3, P1, P3, S1, E1, O1–O5, browser checks A, O3 |
| 2. Look at the images | Checked by eye: zoo, scout-large and jtbd-span-v1. Name, mark, wordmark, share line and the `experimental` chip are readable and centred. The scout-large motif sits in two corners, clear of the text. Sizes 28–48 KB |
| 3. Metadata | The model page carries all eight tags, with `og:image` `https://mhabedank.github.io/mobility-model-zoo/assets/og/scout-large-<hash>.png` (`test_og_meta.py::test_model_page_metadata`) |
| 4. A new model gets its image | A cloned second model gets its page metadata (fast) and its drawn image (slow) with no code change (`test_new_model_gets_card_and_meta`, `test_new_model_image_rendered`) |
| 5. Bad input is blocked | B6 (length, placeholder, number, character, tagline fallback), B7 (name of 40 characters), O1 (tag, size, bytes, format, relative URL), O2, O3 (low contrast), O4 (line, labels, alt, NC label), O5 (stale hash, orphan), P1/P3 on card pages: all reported with the documented id |
| 6. Stable addresses | Two builds without changes give identical `file` entries. A changed share line changes only the scout-large address, and deprecation changes it again (`test_address_changes_with_content`) |

## Speed (SC-005)

Seven images (zoo, five models, one format) render in well under 60 s (`test_render_time_five_models`). The full image step for the real site takes 0.5 s.

## Findings during implementation

- The Google Fonts "latin" range list from research R7 overstated what the shipped Figtree subset draws: 61 code points were missing. `og.LATIN_RANGES` now comes from the font's cmap, and `test_og_fonts.py` guards it when fontTools and brotli are installed.
- `zoo site build` with the default relative `--out _site` failed to open the card pages (`Path.as_uri` needs an absolute path). Checks O1 and O4 caught it on the first real build. Fixed, with a regression test `test_relative_output_directory`.
- A share line longer than 90 characters is already rejected by the `site.yaml` schema (B1), before B6 counts it.

## Test runs

- `uv run pytest -q`: 841 passed, 14 skipped (before the docs step; the new fast tests are included).
- `uv run pytest -q -m slow tests/website`: all passed, one existing skip.
- `uv run ruff check .`, `uv run zoo validate --all`, `uv run zoo compliance check --ci`, `reuse lint`: clean.

## Open (T039, after merge and deploy)

- Check the live scout-large URL in LinkedIn Post Inspector, a Mastodon draft and Slack (SC-003).
- Ask three people from the target group what the preview says (SC-004).
