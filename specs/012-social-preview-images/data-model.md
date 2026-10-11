# Data model: Social preview images

## Share line (input, hand-written)

Where it is written:

| File | Field | Used on |
|---|---|---|
| `zoo/models/<name>/site.yaml` | `share_line` (optional) | the model image |
| `zoo/site.yaml` | `share_line` (optional) | the start image |

The effective line is `share_line` if it is present, otherwise `tagline`.

Validation (B6, also run by gate rule 17 through `context.pitch_errors`):

| Rule | Error |
|---|---|
| length ≤ 90 characters after whitespace is collapsed | `B6 <name>: share line has <n> characters, at most 90` |
| no `{metric:…}` placeholder | `B6 <name>: share line contains a metric placeholder` |
| no free-standing number (F2 pattern) | `B6 <name>: share line contains the number "<n>"` |
| every character is drawn by the site font (`og.LATIN_RANGES`, research R7) | `B6 <name>: character U+XXXX is not in the site fonts` |

If `share_line` is absent and the tagline breaks a rule, the message ends with "; add share_line to site.yaml".

Format images use `title` from `zoo/formats/<id>.yaml` as their line, under the same rules.

## Share card (derived, one per shareable page)

| Field | Source | Notes |
|---|---|---|
| `page` | page path, e.g. `models/scout-large/` | key |
| `kind` | `zoo` · `model` · `format` | selects the template block |
| `title` | zoo `title` · model name · format id | |
| `line` | effective share line · format `title` | |
| `labels` | model only, in this order: release status if not `released` (e.g. `experimental`); `deprecated` if the site status is deprecated; `non-commercial` if the usage class starts with `non-commercial` | the same values as on the page |
| `motif` | `site.yaml` `motif` (model only) | optional |
| `alt` | `"<title>, Mobility Model Zoo: <line>"` + `" (<labels joined by ', '>)"` if there are labels | for format cards: `"Output format <id>, Mobility Model Zoo: <line>"` |
| `inputs_sha256` | SHA-256 over card HTML + asset bytes + renderer id (research R5) | |
| `file` | `assets/og/<slug>-<inputs_sha256[:12]>.png` | `<slug>` is `zoo`, the model name, or `format-<id>` |
| `layout` | measured at render time; absent with `--no-images` | see the manifest |

## Manifest `_site/_build/og.json` (build output, removed before deploy)

```json
{
  "renderer": "playwright 1.xx",
  "cards": [
    {
      "page": "models/scout-large/",
      "kind": "model",
      "title": "scout-large",
      "line": "…",
      "labels": ["experimental", "non-commercial"],
      "alt": "…",
      "file": "assets/og/scout-large-1a2b3c4d5e6f.png",
      "inputs_sha256": "…",
      "html": "_build/og/scout-large.html",
      "layout": {
        "title_px": 76,
        "line_lines": 2,
        "overflow": [],
        "boxes": {"mark": [x, y, w, h], "title": […], "line": […], "labels": […]}
      }
    }
  ]
}
```

`html` is the card page the renderer opened, kept so the check can run axe on it (O3) and recompute the hash (O5).

## Lifecycle

```
registry ──► context (site_models, formats) ──► Share card ──► card HTML (_build/og/)
                                                            ├─► address (hash of inputs)
                                                            ├─► page metadata (og:/twitter: tags)
                                                            └─► PNG (rendered, --images) + layout ──► manifest
```

The build stops when a name does not fit on one line at the smallest title size, or when the share line needs more than 3 lines (B7). Nothing is cached between builds: `_site/` is emptied first, as before.
