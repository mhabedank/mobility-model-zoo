# Contract: checks added and changed by feature 022

Extends the [019 checks](../../019-mobility-image-library/contracts/checks.md). A check not listed
stays as it is.

## New checks

N1 and N2 are raised by the content loader while the site is built, not by `zoo site check`; an
implementer looking for them in the check module will not find them. N3 to N6 are checks in the
suite.

| Id | Kind | Rule | Requirement |
|----|------|------|-------------|
| **N1** | loader (build-time) | Every reference id cited in a note's body has an entry in that note's `references`, and every entry is cited at least once. The failure names the note and the ids on both sides. | FR-007 |
| **N2** | loader (build-time) | Every `[diagram:<name>]` in a note resolves to a file in `zoo/notes/diagrams/`. The failure names the note and the drawing. | FR-005 |
| **N3** | static | Every SVG under `zoo/notes/diagrams/` draws colour only through the site's custom properties: no literal colour value, no gradient, no embedded image, no external reference. Each carries a `<title>` and a `<desc>`. | FR-005 |
| **N4** | static | Every note page is at most 40,000 bytes without fonts and images. The finding names the page and its size. | FR-014, SC-004 |
| **N5** | static | Every class name in the note stylesheet carries the page type's prefix, and no prefixed class appears in the shared stylesheet. Guards against the collision that research R3 records. | FR-015 |
| **N6** | static | Every part of a series either resolves to a published note or is marked as planned; no entry produces a link to a page that does not exist. | FR-009 |

## Changed checks

| Id | Before | After | Reason |
|----|--------|-------|--------|
| **S1** | The sum of HTML, CSS and JavaScript over the whole site is at most 300,000 bytes, and every page at most 150,000 | Note pages and the note stylesheet are excluded from the site-wide total and governed by N4 instead. The total and the per-page cap are unchanged for every other page. | FR-014, research R1 and R2 |
| **I3** | Pictures are allowed on the start page, model pages and the credits page | Also on note pages and the notes index | FR-008, FR-010 |
| **I1** | `placements` entries match `start-hero`, `topic:<id>` or `model:<name>` | Also `note:<slug>` and `note:series` | FR-008 |
| **C1** | Credits name the start page, a topic or a model as the place a picture is used | Also a note, by its title, and the notes index | FR-008, Principle VI |
| **L2** | Every external link answers | Unchanged as a rule. Recorded for the implementer: DOI resolvers answer 403 to the checker, so a DOI belongs in the citation text and not in a link. | FR-006, data model |

## Unchanged checks that must keep passing

The suite is the acceptance gate for this feature, so the following are called out because the new
page type is the most likely thing to break them: the accessibility checks on every page in light
and dark mode at phone and desktop width; the internal link check; the rule that numbers shown on
the site come from data rather than from template text, which is why the licence version lives in
the note's front matter; and the rule that no text sits inside a figure holding a picture, which is
why an image credit is a paragraph after the figure rather than a caption inside it.
