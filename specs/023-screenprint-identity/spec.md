# Feature Specification: One identity, taken from the website imagery

**Feature Branch**: `023-screenprint-identity`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: the site's "M." mark no longer fits the screenprint style of the imagery.

## Context

The website carried two complete visual identities. The interface came from the feature 008
identity sheet: electric blue `#1B3BD8`, neon mint `#6FFFC8`, monoline motifs with round caps, a
soft geometric typeface. The imagery came from features 016 and 019: a 1970s West German poster
style with flat colour fields, crisp cut edges, deep navy, pale mint, warm cream and exactly one
warm orange reserved for the vehicle or machine.

The mark is the only place both are in view at the same time, which is why it was the thing that
looked wrong. The complaint was about the logo; the defect was the seam.

The first attempt proved the point the wrong way round. Moving only the mark and the motifs into
the poster world made the remaining interface colours read as foreign bodies, and the result was
worse than either whole. A half step is not available here: either the interface joins the
imagery or it stays deliberately separate.

This specification is written from an implementation that exists and passes every check, not
ahead of it. Its job is to record the decisions the implementation made and the reasons behind
them, because most of those reasons are not recoverable from the diff.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A reader sees one thing, not two (Priority: P1)

A visitor opens a model page. The illustration, the motif on it, the page around it and the mark
in the header belong to one visual world: the same inks, the same cut edges, the same single warm
accent.

**Acceptance**: On every page, interface colours come from the same palette as the imagery. No
interface element uses a colour absent from the illustrations.

### User Story 2 - The page is legible in both schemes (Priority: P1)

A visitor with a light system reads on paper; a visitor with a dark system reads a night print.
Neither is an afterthought, and body copy is comfortable in both.

**Acceptance**: Every colour pair that carries meaning reaches its WCAG threshold, measured in the
browser on the rendered page, not only in the palette table.

### User Story 3 - A shared link earns a look (Priority: P2)

The owner posts a model link on LinkedIn. The preview shows an illustration from the zoo's own
library rather than a text tile, so the post stops a scroll on its own terms.

**Acceptance**: Every shareable page whose placement resolves to an image gets an illustrated
card; a page without one keeps a typographic card rather than breaking.

### User Story 4 - The identity stays swappable (Priority: P3)

A later change of identity touches the design tokens, not the page content.

**Acceptance**: No interface colour is written outside `tokens.css`, including the sections that
are dark in both schemes.

### Edge Cases

- A page with no image placement: the card stays typographic, the page is not broken.
- A motif whose strokes were only visible through their round caps: zero-length runs still draw.
- A future model image with more detail than today's: the card budget keeps headroom for it.
- A messenger cropping a preview to a square: mark and title stay inside the centre square.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Interface colours MUST come from the palette of the website imagery. The page takes
  its light tone from the sky of the illustrations, not from paper.
- **FR-002**: The same light tone MUST serve as the page in the light scheme and as the ink in the
  dark one, so the two schemes are one pair turned over rather than two inventions.
- **FR-003**: The warm accent MUST stay rare. Links MUST NOT use it; a colour used for everything
  signals nothing.
- **FR-004**: The mark MUST be cut rather than drawn: filled fields with flat cuts, no round caps.
  It MUST turn over with the colour scheme from a single file.
- **FR-005**: Motifs MUST keep their geometry and their lean and MUST be cut with
  `stroke-linecap="square"`, which covers exactly what the round cap covered. The grammar, its
  lint and contract M2 move with them.
- **FR-006**: The single accent element each motif carries MUST be the one warm accent the art
  direction reserves, so motif and illustration follow the same rule.
- **FR-007**: Headline type MUST be set narrow over a width axis, as the poster headlines of the
  period were. Body copy MUST stay at full width.
- **FR-008**: The shipped typeface MUST be self-hosted, openly licensed, and subset to the code
  points the site draws, so the drawable character set does not change with the swap.
- **FR-009**: Information graphics MAY use a documented data-ink extension beyond the brand
  palette. Categorical encoding needs hue separation that a poster palette deliberately refuses.
- **FR-010**: Share cards MUST be illustrated where a placement resolves, using the placements the
  pages already carry rather than a second mapping.
- **FR-011**: Share card text MUST sit on a solid panel, not over the illustration, so contrast
  does not depend on what a picture happens to show.
- **FR-012**: The card hash MUST cover the illustration, so a changed picture yields a changed
  file name.

### Key Entities

- **Poster inks**: navy, cream, pale mint and one warm orange, shared by both schemes. They
  describe printed surfaces — the mark's ground, the motif plates — and do not turn over.
- **Page tones**: the paper and ink pair that does turn over with the colour scheme.
- **Data inks**: the additional hues reserved for categorical encoding in information graphics.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every meaning-carrying colour pair meets its threshold: 36 pairs checked before
  implementation, all passing, verified afterwards in the browser.
- **SC-002**: No interface colour literal survives outside `tokens.css`.
- **SC-003**: The motif grammar lint and contract agree, and every shipped motif passes.
- **SC-004**: The typeface ships under 60 KB with both axes intact and unchanged character
  coverage.
- **SC-005**: Every page keeps its Largest Contentful Paint under 2,000 ms under Fast 3G
  throttling, which is the promise SC-007 of feature 008 actually makes.
- **SC-006**: Every share card stays inside its budget and its layout checks, overlap included.

## Constitution Compliance

- **VI, Clean Provenance**: The typeface is OFL-1.1 and self-hosted. Its copyright line, its
  licence and the fact that it was subset and its axes trimmed are recorded in the font licence
  file, the third-party notices and the REUSE records. "Unmodified apart from subsetting" would
  have been false once the axes were trimmed, so the wording changed with the fact.
- **XI, No Claude in Model Learning or Extraction**: Nothing here is model input. Visual design is
  not learning material, and no artefact of this feature may become one.
- **IX, Reproducible Releases**: The subsetting is a one-off build step whose output is committed,
  as the previous typeface was handled. No new project dependency was added for it.

## Assumptions

- Dark mode stays. A print identity has no dark mode, but removing it would be a regression for
  readers, so the dark scheme is treated as a night print rather than dropped.
- The local image-triage templates under `templates/local/` are out of scope: they are tools for
  the owner, never built and never published.

## Out of Scope

- The model pages' HTML weight, which is the largest part of the site total and a separate
  investigation.
- Parts of the identity sheet of feature 008 that no longer describe the site; superseding that
  document is a documentation task, not this change.
- Any change to the illustrations themselves. Their palette is calibrated and anchored in check
  I6; the interface moved to them, not the other way round.
