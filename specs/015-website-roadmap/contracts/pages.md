# Contract: roadmap page and start page changes

Extends [specs/008-zoo-website/contracts/site-tree.md](../../008-zoo-website/contracts/site-tree.md). Design decisions: [research.md](../research.md) R7, R8.

## Every page

The header navigation gains "Roadmap" between "Models" and "Topics", linking `roadmap/` (FR-012).

## `/roadmap/` roadmap page (new)

In this order:

1. **Head**: eyebrow "Roadmap", `h1` "What comes next", one line "A plan, not a commitment. As of <as_of, e.g. 12 October 2026>." (FR-010).
2. **Timeline band** (decorative, `aria-hidden`): a line with one marker per horizon and a "now" marker at today's position inside the first horizon. The same information is in the column headings, so the band carries none of its own.
3. **Horizons**: three `section` elements in time order, each with `h2` = horizon label and a muted line with its months. Columns side by side from 960 px, stacked below. Each holds an ordered list (`ol`) of its open entries in record order, or the line "Nothing planned yet."
4. **Entry card** (`li` with `id="<entry id>"`):
   - **Name**: an `h3` with the model motif at 28 px when there is one; the suffix "(working name)" in muted text when `working_name`.
   - **Topic**: the topic title as eyebrow.
   - **Sentence**: `text`.
   - **Chips**: the kind as words ("New model", "First release", "Update of <model>"); the stage ("Planned" with a hollow dot, "In progress" with a half-filled dot); the usage label when derived ("share-alike", "non-commercial").
   - **Precondition**: the line "Waits for: <precondition>", when present.
   - **Link**: for `update` entries the name links the model page (FR-011); other entries have no link.
5. **Legend**: one muted line under the columns: "New models and first releases are framed; updates of published models are outlined."

Visual weight (FR-009, FR-016):

- **New models and first releases**: `card` surface with a mint accent bar on the left (4 px).
- **Updates**: transparent background, dashed `border-strong` outline, no accent bar.
- **Chips**: the existing `.chip` component. `.chip.planned i` is hollow; `.chip.progress i` is half-filled by a linear gradient. The words always carry the meaning.

No JavaScript is required; `site.js` is not changed.

## `/` start page (changed)

Models section:

1. **Heading**: "<n> published · <m> coming next." (FR-017).
2. **Published tiles**: one tile per published or deprecated model, as today. Unpublished models no longer get a tile.
3. **"Coming next"**: an `h3` followed by a grid of small cards (`auto-fill, minmax(180px, 1fr)`: six per row at 1200 px, two at 390 px), one per open `new-model` or `first-release` entry. Order: by horizon, then record order. Each card shows:
   - name, with "(working name)" when it applies;
   - topic eyebrow;
   - the horizon label as a chip.

   The sentence stays on the roadmap page, so a card is three short lines.

   The whole card is a link to `roadmap/#<id>`. There is no version, no number and no metric (FR-015).
4. **Roadmap link**: "See the roadmap →" linking to `roadmap/`.

Size budget: the "Coming next" grid stays below half the height of the models section at 1440 × 900 (SC-003); the initial roadmap has 11 upcoming models, which is 2 rows of 6 small cards against one row of full tiles.

## Preview image

`roadmap/` gets a preview card (feature 012 pipeline):
- **Eyebrow**: "Roadmap".
- **Title**: "What comes next".
- **Line**: `zoo/site.yaml` → `roadmap.share_line`, else "What the zoo plans to release next."
