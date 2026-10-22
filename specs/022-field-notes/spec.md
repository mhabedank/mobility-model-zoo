# Feature Specification: Field notes, a long-form page type for the website

**Feature Branch**: `022-field-notes`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: a long-form page type for the zoo website. Long-form working notes about how the models are built, published at `/notes/` with an index and one page per post, written as a developer diary rather than documentation.

## Context

The website today explains finished models: what they achieve, against what, and where they fail. It says nothing about how the decisions behind them were reached. The thinking that produces a model is often further along than the model itself, and today it lives in chat logs and specs that nobody outside the project reads.

Field notes are opinion pieces about the way to a model. They sit outside the compliance chain that governs models, datasets and releases, and what they need instead is their own licence and their own byte budget.

The first series, *Mapping the mobility experience*, has five parts. This feature carries the page type and part one. Parts two to five are ordinary content commits afterwards and need no further specification.

A working proof of concept exists in the tree and passes every site check except the byte budget. The specification is written from it, not ahead of it, and its job is to record the decisions that the proof of concept made silently.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A reader follows the thinking behind a model (Priority: P1)

A reader arrives from a link, reads a long note from start to finish, follows a claim to the model page it refers to, checks a citation, and understands that this is an opinion about work in progress rather than a product statement.

**Why this priority**: Without a readable post page the feature has no value at all. Everything else is navigation around it.

**Independent Test**: Publish one post and read it on a phone and on a desktop, in light and in dark mode, without touching any other page of the site.

**Acceptance Scenarios**:

1. **Given** a published note, **When** it is opened on a desktop, **Then** title, lead image, body, diagrams and reference list share one reading column of the same width, and that column is centred.
2. **Given** a published note, **When** the reader's system is set to dark mode, **Then** text, lead image and every diagram follow the dark palette without a second set of files.
3. **Given** a published note, **When** the reader follows a claim about a model, **Then** the link leads to that model's page, its output format page, or the roadmap entry if the model is not published yet.
4. **Given** a published note, **When** the reader meets a superscript number, **Then** it leads to the full reference, and the reference leads back to the place it was cited.
5. **Given** a published note, **When** the reader looks for its origin, **Then** the page names the author and the date.

---

### User Story 2 - A reader finds the series and sees where it is going (Priority: P2)

A reader lands on the index, sees what field notes are, which parts exist, and which are still to come.

**Why this priority**: One post is reachable by link alone. The index earns its place as soon as a series is announced, and an honest "not written yet" is worth more than a hidden plan.

**Independent Test**: Open the index with exactly one of five parts published.

**Acceptance Scenarios**:

1. **Given** a series with one published part, **When** the index is opened, **Then** all five parts appear in order, the published one links to its page and carries its date, and the others are marked as planned.
2. **Given** the index, **When** it is opened, **Then** it carries its own lead image, and each published part shows a thumbnail of its own image.
3. **Given** any page of the site, **When** the reader looks at the main navigation, **Then** field notes are reachable from it.

---

### User Story 3 - The author publishes a note without touching the generator (Priority: P2)

The author writes a file, puts its references and its lead image in the file's own header, and builds the site.

**Why this priority**: If publishing needs a code change, the diary dies after three posts.

**Independent Test**: Add a second markdown file with a front matter block and build the site; a new page appears with no change to any template or module.

**Acceptance Scenarios**:

1. **Given** a markdown file with a front matter block in the content folder, **When** the site is built, **Then** a page exists at its own address, and the index lists it when the note is named as a part of the series.
2. **Given** a post that cites a reference with no entry in its header, **When** the site is built, **Then** the build fails and names the missing entry.
3. **Given** a post that lists a reference it never cites, **When** the site is built, **Then** the build fails and names the unused entry.
4. **Given** a post that places a diagram, **When** the site is built, **Then** the drawing is embedded in the page itself rather than linked as an image file, so it follows the site's colours.

---

### User Story 4 - Reuse of a note carries the author's name (Priority: P3)

Someone republishes a passage or a diagram elsewhere.

**Why this priority**: Attribution is the whole return on writing the notes in public. It must be stated on the page and recorded in the repository, not left to courtesy.

**Independent Test**: Read the licence statement on a post and check the repository's licence records for the same path.

**Acceptance Scenarios**:

1. **Given** a published note, **When** the reader reaches the end, **Then** the page names the author, the year and a licence that requires attribution for text and diagrams.
2. **Given** the repository, **When** its licence records are checked, **Then** note prose and diagrams carry that licence and every other path is unchanged.
3. **Given** a note with a lead image, **When** the reader follows the credit, **Then** the credits page names the image, how it was generated, and the note it is used on.

---

### Edge Cases

- A post with no lead image still renders, without an empty frame.
- A post with no references renders without an empty reference section.
- A series part that has no note yet never produces a dead link.
- A note that belongs to no series builds its page but has no entry on the index, because an index of mixed content is out of scope. Until that changes, a standalone note is reachable by link alone.
- An image placed on a note and nowhere else still appears in the credits with the note named as its use.
- A note must not appear in the model listings or the roadmap, which are generated from release records.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The site MUST publish long-form notes as their own page type, one page per note, at an address separate from models, formats and the roadmap.
- **FR-002**: A note's text and metadata MUST live in a content file outside the code, and adding a note MUST NOT require changing a template or a module.
- **FR-003**: A note's header MUST carry at least its title, a one-line description, its date, its author and its licence with the version and the link that are shown on the page, and optionally its series, its part number, its lead image and its references.
- **FR-004**: A note page MUST present title, lead image, body, diagrams and references in one reading column of a single width, centred, using the fonts of the rest of the site.
- **FR-005**: A note MUST be able to place an explanatory drawing in its body by name, and the drawing MUST be embedded in the page so that it follows the site's colour tokens in light and dark mode without a second file.
- **FR-006**: A note MUST be able to cite a reference by id; the citation MUST render as a numbered marker that leads to the reference, and the reference MUST lead back to the citation. Numbers follow the order of first use.
- **FR-007**: The build MUST fail when a note cites a reference that its header does not list, or lists a reference it never cites.
- **FR-008**: A note MUST be able to carry a lead image from the existing image library through a placement reserved for notes, and the credits page MUST name the note a picture is used on.
- **FR-009**: The site MUST publish an index of notes that shows, for each series, every part in order, with published parts linked and dated and unpublished parts marked as planned.
- **FR-010**: The index MUST carry its own lead image, and each published part MUST show a thumbnail of its own image.
- **FR-011**: Field notes MUST be reachable from the main navigation of every page.
- **FR-012**: A note page MUST state its author, its date and its licence.
- **FR-013**: Note prose and diagrams MUST be licensed under CC-BY-4.0 in the repository's licence records; every other path MUST keep the licence it has today.
- **FR-014**: Note pages and the styles that only they load MUST be excluded from the site-wide byte budget, and note pages MUST instead meet a byte budget per page.
- **FR-015**: Links, headings and body text inside notes MUST NOT inherit styling intended for other page types, and the note styles MUST NOT change the appearance of any existing page.
- **FR-016**: Every site check MUST pass with notes in the build, including the checks this feature changes: accessibility, internal and external links, the image rules, the byte budgets on both sides of their split, and the rule that numbers on the site come from data rather than templates.
- **FR-017**: The feature MUST publish part one of the series *Mapping the mobility experience*, which means the note is live on the deployed site and reachable from the index and the navigation.

### Key Entities

- **Note**: One long-form post. Title, description, date, author, licence, optional series and part number, optional lead image, optional references, and a body of prose with diagram and citation markers.
- **Series**: A named sequence of notes with an introduction and an ordered list of parts, each either published or planned.
- **Reference**: One bibliographic entry belonging to a note: an id used in the text, the full citation, and optionally a link.
- **Diagram**: One explanatory drawing belonging to the notes, named, embedded in the page, drawn only in the site's colour tokens.
- **Note placement**: The kind of image placement that binds a library image to a note or to the index.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reader can open part one, read it to the end and reach the model it talks about, on a phone and on a desktop, in light and in dark mode, with no broken link and no unreadable element.
- **SC-002**: Publishing a further note requires changing content files only, and no file under the source tree.
- **SC-003**: Every site check passes with notes in the build.
- **SC-004**: A note page stays within its own byte budget, and the site-wide budget is met by the pages it still governs.
- **SC-005**: A person who finds a passage reused elsewhere can establish from the page alone who wrote it, when, and under what conditions it may be reused.

## Constitution Compliance

The constitution requires every spec to name the principles it touches and say how it complies.

- **VI, Clean Provenance**: Prose and diagrams are the author's own and are licensed CC-BY-4.0
  through the generated licence records; every other path keeps the licence it has. Library images
  keep their CC0 records, and a picture's use on a note is named in the credits, so origin and use
  stay recorded together.
- **XI, No Claude in Model Learning or Extraction**: Notes are documentation written with a
  development assistant, which the principle permits. Nothing published under this page type may
  become model input. The ontology the series describes would, as a labelling guideline, fall under
  the principle; it is therefore out of scope here and must not be published as a definitions page
  for models without its own provenance from the literature.
- **II, Grounded Evidence over Plausibility**: The principle governs items a model extracts, not
  prose, so it does not bind a note. The feature builds the local analogue anyway: a citation
  without an entry, or an entry never cited, stops the build, so a reference list cannot drift from
  the text it claims to support.
- **IX, Reproducible, Dated Releases** and **X, Scope Discipline**: Not touched. A note is not a
  model release, and the extraction model's task boundary is unaffected.
- **Development Workflow & Quality Gates**: The gates listed there cover labelling runs, data
  generation, experiments, reporting and releases, none of which publishing prose triggers. The gate
  this feature does have to pass is the site's own check suite.

## Assumptions

- Notes are not product material. The gates of the constitution's "Development Workflow & Quality Gates" apply to models, data and releases and are not triggered by published prose; the compliance harness is therefore not extended to notes.
- Notes may be written with an assistant. The ontology that later becomes a labelling guideline for a model is a separate artefact with its own provenance and is explicitly out of scope here, because Principle XI governs what a model learns from.
- The section is called "Field notes" and lives at `/notes/`, matching the term already used by the author's LinkedIn workflow for the English companion piece on the website.
- Part one ships with a borrowed lead image from the existing library. The motif it really needs, two roles meeting at a counter, does not exist yet and is a subject for a later round of the image library, not a blocker for this feature.
- Series are described in their own content file. An index that mixes several series with standalone notes and short snippets is a later change; one series is enough while one series exists.
- The byte budget for a note is set from the measured size of part one with headroom, rather than from a theoretical figure.

## Out of Scope

- Parts two to five of the series. They are content commits against this page type and need no specification.
- The short "Field Note" format that follows a LinkedIn post, and any automated derivation of social posts from a note.
- An index that mixes several series, standalone notes and snippets.
- A narrow variant of each diagram for phone widths. The current diagram shrinks below comfortable label size on a phone; the rule and the second variant follow once the visual language below is settled.
- The visual style of diagrams. The logo and the model motifs are being reworked to sit better with the Siebdruck imagery, and the diagram style has to follow that rework rather than invent its own.
- Comments, a feed, search, tags and author pages.
