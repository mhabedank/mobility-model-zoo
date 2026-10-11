# Contract: share card layout and metadata

## Canvas

- 1200 × 630 CSS px, device scale factor 1, PNG.
- Full-bleed background in the dark-scheme `--bg` colour. Text and mark use colours from `tokens.css` that pass WCAG AA against it (O3).
- Margins of 48 px on every side. No text outside them.
- Safe square x ∈ [285, 915]: the mark and the title must lie inside it (O2).

## Blocks (top to bottom, centred)

| Block | zoo | model | format |
|---|---|---|---|
| Brand row | mark 88 px + wordmark | mark 56 px + wordmark | mark 56 px + wordmark |
| Eyebrow | none | topic title | "Output format" |
| Title | zoo title, 76 px | model name, 76 → 60 → 48 px | format id, 76 → 60 → 48 px |
| Line | zoo share line | effective share line | format title |
| Labels | none | chips: `experimental`, `deprecated`, `non-commercial` | none |
| Decoration | none | model motif at both side edges, outside the safe square, not meaningful (`aria-hidden`) | none |

- Title: Figtree 700, in a box of `max-width: 630px` centred on the safe square; it must fit on one line (B7). Line: Figtree 500, 34 px, max width 960 px, at most 3 lines.
- All text is set in Figtree, as the `h-display` hero title on the site; JetBrains Mono is not used on cards.
- Colours: the dark-scheme tokens of `tokens.css` (background `--bg` #0A0F2E, accent `--accent` #6FFFC8), so the card matches the site in dark mode and stands out on light feeds.
- No numbers and no URLs on the card.

## Page metadata (in `base.html.j2`)

```html
<meta property="og:image" content="{canonical_url}{file}">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{alt}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{canonical_url}{file}">
<meta name="twitter:image:alt" content="{alt}">
```

`og:title`, `og:description` and `og:url` stay as in feature 008.
