# Phase 1 data model: field notes

Everything here is a content file in the repository. There is no database and no runtime state.

## Note

One long-form post. File: `zoo/notes/<NN>-<slug>.md`, where `NN` orders the files on disk and the
slug becomes the address `/notes/<slug>/`. The file is a YAML front matter block, then CommonMark.

| Field | Required | Meaning |
|-------|----------|---------|
| `title` | yes | The headline of the note |
| `description` | yes | One or two sentences, used as the page description, the share text and the entry in the index |
| `date` | yes | Publication date, ISO, used for ordering |
| `author` | yes | The person the licence names |
| `licence` | yes | SPDX identifier of the prose and the diagrams |
| `licence_label` | yes | How the licence is written on the page; carries the version so no version number lives in a template |
| `licence_url` | yes | Where the licence text is |
| `series` | no | Title of the series the note belongs to |
| `part`, `parts` | no | Position in that series, and how many parts it has |
| `lead_image` | no | A placement name, resolved against the image library |
| `lead_caption` | no | One line under the lead image, written to carry the argument rather than describe the picture |
| `diagrams` | no | Caption per diagram name used in the body |
| `references` | no | The works the body cites (see below) |

**Validation**

- The file begins with a front matter block, or loading fails naming the file.
- Every id cited in the body has an entry in `references`, and every entry is cited at least once.
  Either failure stops the build and names the id.
- A diagram placed in the body has a file of that name, or the build fails.
- `lead_image` resolves to a placed library record, or the page renders without a lead image and
  the build reports it as a warning, as every other unresolved placement does.

**Body markers**

- A line consisting only of `[diagram:<name>]` is replaced by the drawing of that name, embedded.
- `[ref:<id>]` anywhere in the text becomes a numbered marker linking to the reference list, and
  the entry links back. Numbers follow the order of first use, not the order of the list.

## Series

File: `zoo/notes/series.yaml`. Describes one series and the parts it promises, so the index can show
what exists and what does not.

| Field | Required | Meaning |
|-------|----------|---------|
| `id` | yes | Stable identifier |
| `title` | yes | Title shown above the list |
| `intro` | yes | What the series is for |
| `parts[].part` | yes | Position, from one |
| `parts[].title` | yes | Title of that part |
| `parts[].text` | yes | One sentence on where that part goes |
| `parts[].slug` | no | Set once the part is published; links the entry to the note of that slug |

**Derived at build time**: whether a part is published, its address and its date, from the note of
the matching slug. A part with no matching note is shown as planned and never produces a link.

## Reference

One entry in a note's `references` list.

| Field | Required | Meaning |
|-------|----------|---------|
| `id` | yes | Used in the body to cite it |
| `text` | yes | The full citation, including a DOI where one exists |
| `url` | no | A link, used only where it is stable enough to pass the external link check |
| `link_label` | only with `url` | The short label shown for the link |

**Note on links**: DOI resolvers answer the site's link check with 403 because they block automated
requests. A DOI therefore travels in `text` as plain text, and `url` is used only where the target
answers.

## Diagram

File: `zoo/notes/diagrams/<name>.svg`. An explanatory drawing belonging to the notes.

- Drawn only in the site's colour custom properties, never in literal colours, so one file serves
  light and dark mode.
- Carries a title and a description for screen readers.
- Contains no text that the page already says; the caption lives in the note's front matter.
- Follows the motif language of the site. That language is being reworked, so this feature fixes
  only the two rules above and leaves the style to the rework.

## Note placement

A value in a library image record's `placements`, the way `start-hero`, `topic:<id>` and
`model:<name>` already are.

| Form | Means |
|------|-------|
| `note:<slug>` | The lead image of the note at that slug |
| `note:series` | The lead image of the notes index |

The credits page names the use: a note's title for the first form, the index for the second.
