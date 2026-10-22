# Phase 0 research: field notes

Decisions taken before design, each with the number or the constraint behind it. Measurements come
from the proof of concept in the working tree, built with `zoo site build --no-images --offline`
on 2026-10-22.

## R1: The byte budget for notes

**Measured**: Check S1 counts every published file except web fonts, link-preview images and the
image library, which is wider than HTML, CSS and JavaScript alone. On that basis the site came to
328,966 bytes against a cap of 300,000. The notes account for 30,994: the note page 19,104, the
index 7,916 and the stylesheet only they load 3,974. Without all three the site stands at 297,972,
inside the cap with 2,028 bytes of headroom.

A first draft of this note put the figure at 294,049 by counting only HTML, CSS and JavaScript.
That was the wrong basis and it flattered the result by about 4,000 bytes. The corrected number
matters, because it is what makes R2 necessary rather than tidy.

**Decision**: Note pages leave the site-wide total and get a cap of their own, 40,000 bytes per
page. The existing per-page cap of 150,000 stays for every other page.

**Rationale**: The total was chosen for a site whose size is set by the number of models, which
grows slowly and deliberately. A diary grows by design, so a shared total turns every new post into
a negotiation with pages it has nothing to do with. 40,000 is about twice the size of part one,
which leaves room for a longer post with two diagrams and still refuses a page that has quietly
become a brochure.

**Alternatives considered**: Raising the total to carry five parts was rejected because the number
would have to be raised again with the sixth. Keeping the total and shortening the posts was
rejected because length is the point of the format.

## R2: Where the styles for notes live

**Measured**: The note styles come to 3,974 bytes. Left in the shared stylesheet they count in the
site-wide total, which would stand at 301,946 against a cap of 300,000. The site would fail its own
budget.

**Decision**: The note styles move into their own stylesheet, loaded only by note pages, and count
against the note page budget rather than the site total.

**Rationale**: It would be inconsistent to take notes out of the site budget and then leave their
styles inside it. It also keeps the promise that the page type cannot make existing pages heavier.
The cost is one extra stylesheet request on note pages, which is within their own budget.

**Alternatives considered**: Leaving the styles in the shared sheet is not a choice, it is a
failure: the site would be 1,946 bytes over its cap the moment the first note is published. Even
with the split the remaining headroom is 2,028 bytes, which is thin enough that the next model page
should be measured before it is merged.

## R3: A class-name space for the page type

**Observed**: The proof of concept first gave the index the class `notes`, which already exists in
the site for the small annotation lists on model pages. The index silently inherited 13 px type and
a 900 px width, and looked broken for a reason that had nothing to do with its own styles.

**Decision**: Every class belonging to this page type carries a prefix that exists nowhere else in
the stylesheet, and the plan's check list gains a rule that the prefix is unique.

**Rationale**: A stylesheet with no component boundaries will keep doing this. A cheap naming rule
catches it at the moment it is introduced rather than in a screenshot.

## R4: Citations as data rather than markdown footnotes

**Decision**: References live in the note's front matter and are cited by id. Numbers follow the
order of first use. A citation without an entry, or an entry never cited, fails the build.

**Rationale**: CommonMark has no footnotes, so the alternative was a markdown plugin, a new
dependency for a syntax the author would still have to keep consistent by hand. Keeping references
as structured data also means a citation can be checked, which is the part that matters: a
reference list that silently drifts away from the text is worse than none, because it looks
sourced.

**Alternatives considered**: A footnote plugin for `markdown-it-py` was rejected as a dependency
added for formatting. Plain links in the text were rejected because they lose the full citation,
which is what makes a claim checkable when a link rots.

## R5: Diagrams embedded, not linked

**Decision**: A diagram is written into the page itself rather than referenced as an image file.

**Rationale**: The site's colours are CSS custom properties. An SVG referenced through `<img>` is a
separate document and cannot see them, so a linked drawing would need a second file for dark mode
and would drift from the palette the moment a token changes. Embedded, one file follows both modes
for free.

**Cost accepted**: The drawing counts against the page's bytes every time the page is served, with
no separate cache entry. At roughly 4,500 bytes per diagram this is affordable inside the budget of
R1, and it is the reason that budget is not tighter.

## R6: Where field notes sit in the navigation

**Decision**: In the main navigation, between the roadmap and the topics.

**Rationale**: The index is now a substantive page with a lead image and a visible plan, and a
reader who wants to know how the project thinks should not have to find it in a footer. The entry
is shown only when at least one note exists, so the link can never be dead.

**Reversible**: This is a positioning choice, not a technical one. Moving the entry is a one-line
change if the owner later decides the diary should not sit level with the models.

## R7: What is deliberately not solved here

- **A narrow diagram for phones.** The drawing is laid out for a 700 px column. On a phone it
  scales down until its labels sit near 7 px, which is too small to read. One SVG cannot serve both
  widths, so the answer is a second, narrower variant swapped by a media query. It is left out
  because the diagram's visual language is about to change (see below) and the second variant would
  be drawn twice.
- **The visual style of diagrams.** The owner is reworking the logo and the model motifs so they sit
  better with the Siebdruck imagery. A diagram style defined now would be redrawn within weeks. The
  rule to record instead: diagrams follow the motif language, and this feature only fixes that they
  are embedded and use the colour tokens.
- **An index of mixed content.** Series, standalone notes and short snippets will need a different
  index. One series is enough while one series exists, and the structure will be clearer when the
  second kind of entry actually exists rather than being imagined.
- **The lead image part one really wants.** None of the 92 library images shows two roles meeting,
  which is the subject of part one. The post ships with the empty platform under a canopy, whose
  caption was written to carry the argument rather than describe the picture. The missing motif is
  a subject for a later round of the image library.
