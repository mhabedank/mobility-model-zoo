# Contract: checks added or changed by feature 014

Adds to [specs/008-zoo-website/contracts/checks.md](../../008-zoo-website/contracts/checks.md) (and to feature 012's B6, B7, O1–O5). Every check blocks publication like the existing ones. Budgets come from one constants table ([data-model.md](../data-model.md#budget)).

## New site checks (`zoo site check`)

| ID | Check | Covers |
|---|---|---|
| D1 | Every published model's `model.yaml` has `card.not_for` (2–3 items) and `card.limits_short` (1–5 items); when its latest release is `experimental`, `card.unmet_criteria` is non-empty, and when `released`, it is absent or empty; every `measured` placeholder resolves (B2 rules) and every `target.source` file exists | FR-005, FR-012, FR-020 |
| D2 | Rendered word budgets: layer 1 running text ≤ 150 words and its `not_for` list ≤ 40 words; running text before `#quality` ≤ 200 words; layer 3 short form ≤ 5 items and ≤ 120 words; differentiators 3–4 with text ≤ 20 words. Counting rule: whitespace tokens of visible text, excluding `data-budget="skip"` and closed `<details>` content except `<summary>`. A finding names page, layer, measured value and limit | FR-006, FR-011, SC-004 |
| D3 | Layer content: layer 1 has no `pre`, `code` block, `table` or headline figure; layer 2 has 1–4 headline figures, no `table` outside chart `<details>`, at most one sentence of prose before the first figure, and a link to `#metrics`; layer 5 has no field table and links the format page | FR-006, FR-007, FR-010, FR-015 |
| D4 | Status and terms in layer 1: a status chip equal to the latest record's status; for `experimental`, the status sentence and a link to `#limits`; for a non-commercial usage class, the text "Non-commercial"; no hand-written text in layer 1 states a release status ("experimental", "released", "production ready" outside the generated chip and sentence) | FR-004, FR-005, Constitution IX |
| D5 | Order and anchors: the six `data-layer` sections exist once each in the order of [page-layers.md](page-layers.md); every anchor in the anchor list resolves on every model page | FR-001, FR-019 |
| D6 | Placement (browser, with `--a11y`): at 1440 × 900, the first headline figure or chart starts at ≤ 2 × 900 px, `#limits` at ≤ 4 × 900 px, the status chip, usage class and licence chips lie inside the first 900 px; at 390 × 844, the chips lie inside the first 2 × 844 px. No code element appears above `#limits` | SC-001, SC-002, SC-003, FR-023 |

## Changed site checks

| ID | Before | After |
|---|---|---|
| A2 | Without JavaScript, each model page contains the quickstart code, the field table (`#interface table.tbl`), every example's JSON and the limitations | Without JavaScript, each model page contains the quickstart code, every example's JSON, the limitations (inside layer 3, also when collapsed) and a link to its format page; each format page contains its field table |
| L3 | Every model page links licence, limitations section and AI Act note | Unchanged; the limitations link target is `#limits` |
| F1, F4 | Facts from placeholders and metric cards | Also cover `unmet_criteria` (`target.value` with source `model.yaml`, `measured` with source the results file) and placeholders in `not_for` and `limits_short` |
| F2 | No free-standing numbers in `site.yaml` prose and template text | Also in `card.not_for`, `card.limits_short`, `unmet_criteria[].criterion` and `unmet_criteria[].note` of `model.yaml` |

## Release gate (`zoo check`)

| Rule | Change |
|---|---|
| 17 (site text) | Extended: the word limits of `site.yaml` (differentiators, audience) and the item and word limits of `not_for` and `limits_short` are checked on the release candidate, with the same constants as D2; `site.yaml` prose must not state a release status |
| 18 (new: status and limits) | `card.not_for` and `card.limits_short` exist; `unmet_criteria` is non-empty for `experimental` and empty for `released`; each item has `measured` or `note`; each `measured` resolves in the candidate's results; each `target.source` exists at the candidate commit. Resolves the constitution 2.2.0 follow-up ("check whether a card of an experimental release must carry a 'not production ready' statement automatically") |

## Card

| Test | Change |
|---|---|
| `test_every_section_present_and_in_order` | Expects the new `card.SECTIONS` ([card-order.md](card-order.md)) |
| `test_card_matches_golden_file` | Golden card regenerated once with `ZOO_UPDATE_GOLDEN=1`; the diff is reviewed: only order and the new short-form blocks change, no number changes |
| new: short forms optional | A card rendered from a `model.yaml` without the new fields (an old tag) renders without the short-form blocks and without error |
