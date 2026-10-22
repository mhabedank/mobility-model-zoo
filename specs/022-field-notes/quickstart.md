# Quickstart: adding a field note and proving it works

This is the validation guide for feature 022. It shows the loop an author runs, and the commands
that decide whether the feature is done.

## Prerequisites

The repository's usual environment. The browser checks and the preview screenshots need the
`site-check` dependency group, which brings Playwright.

## Add a note

1. Write `zoo/notes/<NN>-<slug>.md` with a front matter block. The required fields are in
   [data-model.md](./data-model.md); the shortest useful header is a title, a description, a date,
   an author and the three licence fields.
2. Put each drawing the note uses in `zoo/notes/diagrams/<name>.svg` and place it in the body with a
   line `[diagram:<name>]`.
3. List every work the note cites under `references`, and cite it in the text with `[ref:<id>]`.
4. If the note should have a lead image, add `note:<slug>` to the `placements` of a library record
   in `zoo/site/images/<id>/image.yaml` and name the same placement in the note's front matter.
5. If the note belongs to a series, add its slug to the matching part in `zoo/notes/series.yaml`.

No file under `src/` is touched by any of this. If one has to be, the feature has failed SC-002.

## Build and look at it

```bash
uv run zoo site build --offline
uv run zoo site serve --port 8787
```

The note is at `http://localhost:8787/mobility-model-zoo/notes/<slug>/`, the index at
`/notes/`. The path prefix matches GitHub Pages, so a wrong relative link shows up here.

## The gate

```bash
uv run --group site-check zoo site check --a11y
```

The feature is done when this passes with the notes in the build. That covers the accessibility
checks, the internal and external links, the image rules, the byte budgets and the rule that
numbers on the site come from data. The checks added by this feature are listed in
[contracts/checks.md](./contracts/checks.md).

## The failure cases worth seeing once

These prove the guards actually guard. Each should stop the build with a message naming the note
and the thing that is wrong.

1. Cite `[ref:nothing]` in a note whose `references` has no such id.
2. Add a reference entry and never cite it.
3. Place `[diagram:missing]` with no file of that name.
4. Make a note page exceed its byte budget, for example by pasting the body three times.

## Reading it the way a reader will

Check the note on a phone and on a desktop, in light and in dark mode. The reading column holds
title, lead image, body, diagrams and references at one width. The diagrams must follow the palette
in both modes without a second file; if a drawing stays light in dark mode, it is referencing a
colour literally instead of through a token, which check N3 should have caught.

Known limitation, recorded in research R7 and out of scope here: the diagrams are laid out for a
desktop column and their labels become too small on a phone.

## What this feature publishes

Part one of the series *Mapping the mobility experience*. Parts two to five are ordinary content
commits against this page type afterwards and need no further specification.
