# Contract: model page layers

The rendered model page `/models/<name>/` after this feature. Checks in [checks.md](checks.md) verify every MUST below.

## Order

The page `<main>` contains, in this order and nothing between them except whitespace:

1. `<section id="top" data-layer="overview">`
2. `<section id="quality" data-layer="quality">`
3. `<section id="limits" data-layer="limits">`
4. `<section id="quickstart" data-layer="quickstart">`
5. `<section id="reference" data-layer="reference">` with `<div id="interface">` and `<div id="examples">` inside
6. `<section id="details" data-layer="details">` with `#metrics`, `#notes`, `#provenance`, `#versions`, `#cite` inside

The deprecation banner, when present, stays above `<main>` (unchanged).

## Layer 1: overview (`#top`)

MUST contain: eyebrow (topic, task); `h1` name; tagline; audience; chips for release status, usage class, licence, languages or target, output format; for `experimental`, the status sentence with a link to `#limits`; for non-commercial, a chip reading "Non-commercial"; 3–4 differentiators (title + one short text); the `not_for` list with a link to `#limits`; jump links to `#quickstart`, `#limits`, `#details` and the model card on Hugging Face; a layer navigation listing the six layers.

MUST NOT contain: `<pre>`, `<code>` blocks, `<table>`, headline figures.

Budget: running text ≤ 150 words + `not_for` ≤ 40 words. Chips, buttons and the layer navigation carry `data-budget="skip"`.

## Layer 2: quality and speed (`#quality`)

MUST contain, in this order: heading; at most one lead sentence; the benchmark and deterministic-check line; 1–4 headline figures; the charts (when the model has any), each with its value table in a `<details>`; a link "All metrics of version x" to `#metrics`.

A headline figure with a comparison MUST show a bar pair as inline SVG with `role="img"` and a text alternative giving both values; the numbers also appear as text.

MUST NOT contain: the full quality or performance tables.

## Layer 3: limits and status (`#limits`)

MUST start with the short form in an element `data-short="limits"`: the status sentence; the `unmet_criteria` items as "criterion: measured value (target op value unit)" or "criterion: note"; the `limits_short` items. Then links to the evidence: recipe document, results of the release at its tag, release notes (record `changes`), compliance record. Then the full texts: intended use, out of scope, limitations, each in a `<details>` element that is closed by default.

Budget of the short form: ≤ 5 items, ≤ 120 words.

## Layer 4: quickstart (`#quickstart`)

Content as today (hardware note, NC notice, install, run, expected output). No interface or format detail.

## Layer 5: reference (`#reference`)

`#interface`: `card.input_output`, the input and guarantee lists of the format, links to `/formats/<id>/` and the JSON schema. No field table, edge-case table or versioning text (they are on the format page).

`#examples`: worked examples as today.

## Layer 6: details and documents (`#details`)

`#metrics`: the quality table and the speed-and-memory table (open, not collapsed). `#notes`: the notes `fn-<N>`. `#provenance`: the licence and provenance table as today, including training data summary, AI Act note, compliance record, model files, recipe, code, privacy. `#versions` and `#cite` as today.

## Anchors

Every anchor of the old page resolves: `#top`, `#why` (alias on layer 1), `#quickstart`, `#interface`, `#examples`, `#ex<N>`, `#quality`, `#limits`, `#provenance`, `#versions`, `#cite`, `#notes`, `#fn-<N>`.
