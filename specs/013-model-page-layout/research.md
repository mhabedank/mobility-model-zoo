# Research: Model pages in progressive depth

Phase 0 of [plan.md](plan.md). The reader-side research (standards, model pages, reading behaviour) is summarised in the spec under "Context: best practice and reader expectations"; this file records the design decisions that follow from it and from the code as of `main` 9cb9b23.

## Findings in the code and on the live site (2026-10-11)

- The model page is `templates/model.html.j2`, a fixed sequence of partials: hero, why, quickstart, interface, viewer (examples), quality, limits, provenance, versions, cite, notes. Reordering is a template change; the data already exists in the page context built by `site/context.py` and `site/build.py`.
- The hero chip shows the lifecycle from `context.status()` (`published`, `deprecated`), not the release status of the record (`experimental`, `released`).
- **Every published release is `experimental`**, scout-large included (0.1.0, 0.1.1, 0.1.2). The scout-large page says so only in the version table and in a format footnote; the picket-forest page says so because its hand-written text does. Constitution IX ("the status tells users at a glance") is therefore not met on the website today. The model cards already carry the status as a banner (`card.BANNERS`).
- The release record has `status` but no structured list of unmet criteria; the unmet criteria live in prose (`changes`, `card.limitations`).
- `card.SECTIONS` fixes the card's section order; `tests/release/test_card_build.py` asserts the order and a golden card.
- `zoo release audit` compares the card on Hugging Face with the recorded `card_sha256` and never re-renders, so a new card template does not affect published releases. `zoo release deprecate` re-renders the latest card with the current template and `model.yaml` at the release tag.
- Check A2 (`site/a11y.py`) requires a field table under `#interface` on every model page.
- Feature 012 (social preview images, branch `012-social-preview-images`, not yet merged) also changes `check.py`, `context.py`, `facts.py`, `hero.html.j2`, `site.schema.json` and both models' `site.yaml`; it uses check IDs B6, B7, O1–O5 and adds no gate rule.

## Decisions

### R1. Six layers, one page, one template order

- **Decision**: The model page keeps one URL and renders six layers in the order of FR-001: `overview` (hero), `quality`, `limits`, `quickstart`, `reference` (interface + examples), `details` (all metrics, provenance and documents, versions, citation, notes). Each layer is a `<section data-layer="…">` that the checks can find.
- **Rationale**: One page keeps every existing link and anchor working, keeps the checks that run per page (size, LCP, axe, no-JS), and matches how model cards and the Hugging Face template work. Depth comes from order and from collapsing, not from navigation.
- **Alternatives considered**: separate sub-pages for reference and details (`/models/<name>/reference/`): breaks anchors, doubles the pages each check must cover, and hides the required documents one navigation step further; tabs: need JavaScript (check A2) and hide content from search and print.

### R2. Short forms come from `model.yaml` (`card` block), not from `site.yaml`

- **Decision**: Three new optional fields in the `card` block of `model.yaml`: `not_for` (two or three short points), `limits_short` (at most five short points), and `unmet_criteria` (structured list, see R3). The website and the model card render them from the same source.
- **Rationale**: FR-024 puts the same short forms on the card from the next release; `site.yaml` is website-only text and the card never reads it. `model.yaml` already holds `out_of_scope` and `limitations`, of which these are the short form, so they are maintained side by side.
- **Alternatives considered**: `site.yaml` (card cannot use it; two sources for one fact); deriving short forms automatically from the prose (no reliable sentence selection; the prose is written as paragraphs).
- **Consequence**: the fields are optional in the model schema, so `model.yaml` at old release tags stays valid; the site build requires them for every published model (check D1), and the release gate requires them for every new release (gate rule 18).

### R3. Unmet criteria are structured, with numbers from the results

- **Decision**: `card.unmet_criteria` is a list of items `{criterion, target, measured, note}`: `criterion` is a short text without numbers; `target` is an optional structured value (`op`, `value`, `unit`) taken from the task's success criteria, with `source` naming the task document; `measured` is an optional `{metric:<kind>.<name>}` reference resolved against the release's results; `note` is an optional short text without numbers (for example "measured only in an emulator"). Each item needs `measured` or `note`.
- **Rationale**: Constitution IX requires every missed criterion "with the measured value". Free-typed numbers would bypass the fact checks (F1, F2, F4); metric references keep one source per number and print the same value on card and page.
- **Alternatives considered**: a field in the release record (records of published versions must not change, and old versions would need back-filling); prose only (cannot be checked, cannot be shortened per layer).

### R4. Release status from the record, the banner text from the card

- **Decision**: The overview shows the release status of the latest published record (`experimental`, `released`) next to the lifecycle (`deprecated` stays a banner). For `experimental`, a one-sentence statement ("Experimental: not ready for production use.") links to the limits layer. The status words come from `card.BANNERS`, extended by this sentence, so card and site share the wording.
- **Rationale**: One wording for one status; no hand-written status sentence that can drift (the picket-forest tagline currently carries it by hand).
- **Consequence**: hand-written texts no longer need to say "experimental"; the content tasks remove it from the picket-forest tagline so the overview does not say it twice.

### R5. Word budgets measured on rendered text, enforced twice

- **Decision**: Budgets are counted on the rendered page (check D2) and, for hand-written input, before rendering in the release gate (rule 17 extended), so a release cannot publish text that breaks the page. Counting rule: words are whitespace-separated tokens of visible text; content inside closed `<details>` (except its `<summary>`), and elements marked `data-budget="skip"` (chips, buttons, the layer navigation) do not count.
- **Starting budgets** (from the spec; tunable in one constants table): overview running text ≤ 150 words plus ≤ 40 words for `not_for`; differentiators 3–4, title ≤ 5 words, text ≤ 20 words; audience ≤ 25 words; at most 4 headline figures; quality-layer prose ≤ 2 sentences before the first figure; limits short form ≤ 5 items and ≤ 120 words including unmet criteria; ≤ 200 words of running text before the quality layer.
- **Rationale**: Budgets that are only guidelines drift with the next model; counting the rendered text is what the reader sees, counting the input gives an early error at release time.
- **Alternatives considered**: character limits in the JSON schema only (do not capture the rendered total; kept as a coarse first line for `tagline`, `title`).

### R6. Quality layer: figures first, tables to the details layer

- **Decision**: Layer 2 shows at most four headline figures (`metric_cards`, schema `maxItems` 6 → 4), then the charts, then a single link "All metrics of version x" to `#metrics` in the details layer. A headline figure that has a comparison shows a small server-rendered bar pair (value and comparison, same scale, numbers as text next to the bars). The benchmark and deterministic-check line stays as one compact line.
- **Rationale**: FR-007–FR-010; picket-forest has no charts, and a bar pair gives every model a visual without new chart types. Server-rendered SVG keeps the page complete without JavaScript and passes the privacy checks.
- **Alternatives considered**: a third chart type per model (needs per-model data work; not required by the spec); keeping the full table collapsed in layer 2 (contradicts FR-010 and duplicates layer 6).

### R7. Interface in short form; the field table lives on the format page

- **Decision**: Layer 5 shows `card.input_output`, the input and guarantee lists of the format, and a prominent link to `/formats/<id>/` and the JSON schema. The field table, edge cases and versioning are shown only on the format page. Check A2 changes accordingly: a model page must contain the quickstart code, every example's JSON, the limitations, and a link to its format page; the format page must contain the field table (contract change, [contracts/checks.md](contracts/checks.md)).
- **Rationale**: FR-015; the interface section is the largest block on both pages today (627–798 words), and the format page (feature 008) already documents every field as the single full reference.
- **Alternatives considered**: keep the field table collapsed on the model page (no check change, but two copies of the same reference and more page weight).

### R8. Card order from the next release, old cards untouched

- **Decision**: `card.SECTIONS` changes to the layer order (see [contracts/card-order.md](contracts/card-order.md)). The template renders the short forms when `model.yaml` has them and omits those blocks when it does not, so `zoo release deprecate` can still re-render an old release from its tag.
- **Rationale**: FR-024 and the owner decision of 2026-10-11; audit compares hashes only, so published cards stay valid.

### R9. Placement checks in the browser run

- **Decision**: A new browser check D6 measures, at 1440 × 900 and at 390 × 844, where the first quality figure, the status chip and the limits layer start, against SC-001–SC-003. It runs with the existing Playwright accessibility run (`zoo site check --a11y`, `pytest -m slow`).
- **Rationale**: Order and word budgets (D1–D5) can be checked offline on HTML; screen position depends on layout and needs a browser. Measuring in CI keeps the success criteria from regressing with the next model.

### R10. Content of the existing models is part of this feature

- **Decision**: The feature includes rewriting `site.yaml` (scout-large, picket-forest) to the budgets and adding `not_for`, `limits_short` and `unmet_criteria` to every published model's `model.yaml`. The unmet criteria are taken from each model's published card, release record and task success criteria; for scout-large they are reconstructed from its card and the success criteria of feature 004. If a published card does not name a missed criterion with its value, the gap is reported, not invented.
- **Rationale**: Without content the new structure fails its own checks; the owner approves releases only (memory: autonomy), so the text work is automated and verified by the checks.

### R11. Order with feature 012

- **Decision**: 013 is implemented after 012 is merged and rebased onto it. Both touch the hero partial, `site.schema.json`, `check.py` and the two `site.yaml` files; 012's `share_line` and 013's budgets do not conflict.
- **Rationale**: 012 is further along (plan and contracts done); sequencing avoids a three-way merge in the check module.

## Open items

None that block the design. Budgets are starting values (R5) and may be tuned in implementation if a model cannot meet them with honest text; a change is made in the constants table and noted in the PR.
