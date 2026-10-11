# Quickstart: validate the preview images

Prerequisites: `uv sync --extra release --group site-check` and `uv run playwright install chromium`.

## 1. Build and check

```sh
uv run zoo site build --offline
uv run zoo site check --a11y
```

Expected:
- The summary reports one image per shareable page: `site: 4 pages, 3 images in 0.5 s, 1 models (4 in progress)` for start, scout-large and jtbd-span-v1; 404 is not a share target.
- The check prints no findings.

## 2. Look at the images

```sh
open _site/assets/og/*.png
```

Expected:
- scout-large: mark and wordmark, "scout-large", its share line, and the chips `experimental` and `non-commercial` if the release says so.
- Start image: the zoo mark, the title and the tagline.
- Format image: "jtbd-span-v1" and its title.

## 3. Metadata

```sh
uv run zoo site serve &
curl -s localhost:8000/mobility-model-zoo/models/scout-large/ | grep -E 'og:image|twitter:'
```

Expected: the eight tags of [contracts/share-card.md](contracts/share-card.md), with `og:image` under `https://mhabedank.github.io/mobility-model-zoo/assets/og/scout-large-<hash>.png`.

## 4. A new model gets its image automatically

```sh
uv run pytest tests/website -k "og and new_model" -m slow
```

The test adds a second published model with a `site.yaml` to the fixture registry, builds, and finds its image and metadata with no other change.

## 5. Rules block bad input

```sh
uv run pytest tests/website -k "share_line or og_checks"
uv run pytest tests/release/test_gate_site_text.py
```

These cover a tagline that is too long without a share line, a share line with a number, an unsupported character, a name that is too long (B7), a wrong image size (O1) and a stale hash (O5). Each fails with the documented message.

## 6. Stable addresses

Build twice without changes and compare `_site/_build/og.json`: the `file` entries are identical (SC-006).

## 7. After the deploy (manual, SC-003/SC-004)

- Paste the scout-large URL into LinkedIn Post Inspector, a Mastodon post preview and Slack. Each shows the large image with the name, mark and share line visible.
- Ask three people from the target group what the preview says.
