# Contract: model card section order

The model card on Hugging Face follows the page layers from the first release published after this feature (FR-024). Cards already published are not changed; `zoo release audit` compares hashes only.

## `card.SECTIONS` (new)

| # | Section | Layer | Content change |
|---|---|---|---|
| – | (top, before the first section) | overview | title, status banner, usage class line as today |
| 1 | Summary | overview | summary and figures as today; then "Not for:" with the `not_for` items |
| 2 | Quality | quality | unchanged |
| 3 | Speed and memory | quality | unchanged |
| 4 | Limitations and risks | limits | opens with the status sentence, the `unmet_criteria` (criterion, measured value, target) and `limits_short`; then the full `limitations` text as today |
| 5 | Intended use | limits | unchanged |
| 6 | Out-of-scope use | limits | unchanged |
| 7 | How to run it | quickstart | unchanged |
| 8 | Input and output | reference | unchanged |
| 9 | Examples | reference | unchanged |
| 10 | Training data provenance | details | unchanged (replaced by the three compliance sections when a compliance record exists, as today) |
| 11 | Training recipe | details | unchanged |
| 12 | Version history | details | unchanged |
| 13 | License | details | unchanged |
| 14 | Citation | details | unchanged |
| 15 | About the zoo | details | unchanged |

`COMPLIANCE_SECTIONS` keeps its rule: it replaces "Training data provenance" with "Training data and attribution", "Teacher and labeling models", "Privacy and personal data" at the same position.

## Rules

- No number on the card changes because of the reorder; the golden-file diff shows moved blocks and the new short-form blocks only.
- The short-form blocks are rendered only when `model.yaml` (at the release tag) has the fields; a card rendered for an older tag (for example by `zoo release deprecate`) uses the new order without them.
- The Hugging Face card renders the "Not for" list and the unmet criteria as plain Markdown lists; no HTML.
