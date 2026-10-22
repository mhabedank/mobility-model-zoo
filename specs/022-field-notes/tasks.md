---

description: "Task list for feature 022, field notes"
---

# Tasks: Field notes, a long-form page type for the website

**Input**: Design documents from `/specs/022-field-notes/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/checks.md](./contracts/checks.md)

**Tests**: Included. The plan names `tests/website/test_notes.py` and the feature's value depends on
two guards failing loudly, so those guards are tested rather than assumed.

## Starting point

This feature is unusual: a working proof of concept is already in the tree and passes every site
check except the byte budget. The tasks below are written against that tree, not against an empty
one, so several of them are "move", "narrow" or "prove" rather than "build". What already exists:

- `src/mobility_model_zoo/site/blog.py`, templates `post.html.j2` and `notes.html.j2`
- Field-note styles inside the shared `site.css`, which research R2 says must move
- `blog:` placements in the image record schema, the image-page allowlist and the credits builder
- Content: `zoo/blog/01-whose-journey.md`, `zoo/blog/series.yaml`, `zoo/blog/diagrams/three-lanes.svg`
- Placements set on `zoo/site/images/infrastructure-platform-canopy` and `workshop-engine-stand`

Note the naming: the proof of concept says `blog` where every document in this feature says `note`,
because the published address is `/notes/` and the code should follow it. T003 performs that rename
before anything else, so every path named in the later tasks is the one that exists after it.

What does not exist yet: the separate stylesheet, the class-name prefix, the byte-budget split, the
new checks N1 to N6 as checks rather than as behaviour, the CC-BY entry, the tests, the docs.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- Exact file paths are given in each task

---

## Phase 1: Setup

**Purpose**: Clear the scratch work and fix a baseline so later failures are attributable.

- [X] T001 Delete `drafts/blog/` only; `zoo/notes/` is the single source of the note and `specs/022-field-notes/` holds the planning material. Do not remove `drafts/` itself: it is shared scratch space and holds unrelated work in progress, such as `drafts/logo/`
- [X] T002 Record the baseline: run `uv run zoo site build --offline` then `uv run --group site-check zoo site check --a11y` and note in the task list which checks fail today, so that any new failure is known to be new

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: The budget and styling decisions that every later task renders into. Nothing here is
visible to a reader, and everything here changes files that belong to other features.

**⚠️ CRITICAL**: No user story task should be finished before this phase is complete, because the
byte budget and the class prefix change every page the stories produce.

- [X] T003 Rename the proof of concept's `blog` naming to `note`, so code and published address agree: `zoo/blog/` to `zoo/notes/`, `src/mobility_model_zoo/site/blog.py` to `notes.py`, the placement kind `blog:` to `note:` in the schema, in `src/mobility_model_zoo/site/images.py` and in the two placed records under `zoo/site/images/`, and `post.html.j2` to `note.html.j2`
- [X] T004 Create `src/mobility_model_zoo/site/static/css/notes.css` and move every field-note style out of `src/mobility_model_zoo/site/static/css/site.css` into it; the shared stylesheet must end up byte-identical to its state on `main` (research R2)
- [X] T005 Load the new stylesheet only on note pages: add a conditional `<link>` in `src/mobility_model_zoo/site/templates/base.html.j2` driven by a flag the page context already carries, and make sure the file is copied into the build like the other static assets
- [X] T006 Give every class of the page type a prefix that appears nowhere else in `site.css` (for example `fn-`), and rename it in `notes.css`, `note.html.j2` and `notes.html.j2`; research R3 records the collision this prevents
- [X] T007 Split the byte budget in `src/mobility_model_zoo/site/check.py`: exclude note pages and `notes.css` from the site-wide total of check S1, and add a per-page cap of 40,000 bytes for note pages as check N4 (contracts N4, research R1)
- [X] T008 [P] Confirm the `note:<slug>` and `note:series` placement pattern in `src/mobility_model_zoo/site/schemas/image-record.schema.json` matches the data model, and that an unknown `note:` target still fails validation
- [X] T009 [P] Confirm the image-page allowlist in `src/mobility_model_zoo/site/check.py` admits `notes/index.html` and `notes/<slug>/index.html` and nothing wider
- [X] T010 [P] Confirm the credits branch in `src/mobility_model_zoo/site/images.py` names a note by its title rather than its slug, and the index for `note:series`

**Checkpoint**: Code, content and published address all say `note`, the site builds, the shared
stylesheet is unchanged from `main`, and the site-wide budget passes without notes counting
towards it.

---

## Phase 3: User Story 1 - A reader follows the thinking behind a model (Priority: P1) 🎯 MVP

**Goal**: One note reads well end to end, on a phone and a desktop, in light and dark mode, with
working links to the models it talks about and checkable references.

**Independent Test**: Publish only part one, with no index and no navigation entry, and read it.

### Tests for User Story 1

- [X] T011 [P] [US1] In `tests/website/test_notes.py`, assert that a note citing an id absent from its `references` raises, and that the message names the note and the id (contract N1)
- [X] T012 [P] [US1] In `tests/website/test_notes.py`, assert the mirror case: a reference entry never cited in the body raises and names the unused id (contract N1)
- [X] T013 [P] [US1] In `tests/website/test_notes.py`, assert that citation numbers follow order of first use and not the order of the `references` list, and that a second citation of the same id reuses its number
- [X] T014 [P] [US1] In `tests/website/test_notes.py`, assert that a body referencing a diagram with no file raises and names the drawing (contract N2)
- [X] T015 [P] [US1] In `tests/website/test_notes.py`, assert that a file without a front matter block raises and names the file
- [X] T016 [P] [US1] In `tests/website/test_notes.py`, assert that a note without `lead_image` loads and renders without an empty figure (spec edge case)
- [X] T017 [P] [US1] In `tests/website/test_notes.py`, assert that a note without `references` loads and renders without an empty reference section (spec edge case)

### Implementation for User Story 1

- [X] T018 [US1] Finish the loader in `src/mobility_model_zoo/site/notes.py`: front matter split, slug from the file name, body markers, and the two reference guards, with the required and optional fields exactly as listed in [data-model.md](./data-model.md)
- [X] T019 [US1] Make the missing-diagram case a named failure rather than a file-not-found traceback in `src/mobility_model_zoo/site/notes.py` (contract N2)
- [X] T020 [US1] Add check N3 to `src/mobility_model_zoo/site/check.py`: every SVG in `zoo/notes/diagrams/` uses colour only through custom properties, has no gradient, no embedded image and no external reference, and carries a `<title>` and a `<desc>`
- [X] T021 [US1] Render the note page from `src/mobility_model_zoo/site/templates/note.html.j2`: series line, title, description, author and date, optional lead image with its caption as a paragraph after the figure, body, references, licence line; the licence version comes from the note's front matter so no number sits in template text
- [X] T022 [US1] Style the reading column in `notes.css` so title, lead image, body, diagrams and references share one width and the column is centred, using the site's own fonts (FR-004, FR-015)
- [X] T023 [US1] Verify the diagram follows the palette in dark mode without a second file: load `_site/notes/whose-journey/index.html` with the browser set to dark and compare the drawing's computed colours against the dark values in `src/mobility_model_zoo/site/static/css/tokens.css` (FR-005)
- [X] T024 [US1] Check that the three in-text links in `zoo/notes/01-whose-journey.md` resolve in the build: the extraction model's page, the roadmap entry standing in for the unpublished clustering model, and the output format page that documents the actor dimension (FR-012, US1 scenario 3)
- [X] T025 [US1] Run `uv run --group site-check zoo site check --a11y` and fix what it reports for `notes/whose-journey/index.html` in light and dark mode at phone and desktop width

**Checkpoint**: Part one is readable and correct on its own, with no index and no navigation entry.

---

## Phase 4: User Story 2 - A reader finds the series and sees where it is going (Priority: P2)

**Goal**: The index shows the whole series, with the published part linked and the rest honestly
marked as planned.

**Independent Test**: Open `/notes/` with exactly one of five parts published.

- [X] T026 [US2] Load `zoo/notes/series.yaml` in `src/mobility_model_zoo/site/notes.py` and derive, per part, whether it is published, its address and its date, from the note whose slug matches (data model, Series)
- [X] T027 [US2] Add check N6 to `src/mobility_model_zoo/site/check.py`: every part either resolves to a published note or is marked planned, and no entry links to a page that does not exist
- [X] T028 [US2] Render the index from `src/mobility_model_zoo/site/templates/notes.html.j2`: section heading, the series with its introduction, and every part in order with its number, title, one-line text, and either a date and a link or a planned marker
- [X] T029 [US2] Give the index its own lead image through the `note:series` placement, and show each published part's own image as a thumbnail (FR-010)
- [X] T030 [US2] Add the navigation entry in `src/mobility_model_zoo/site/templates/base.html.j2`, shown only when at least one note exists so the link can never be dead (FR-011, research R6)
- [X] T031 [P] [US2] In `tests/website/test_notes.py`, assert that a planned part produces no address, and that adding a slug to a part links it to the matching note

**Checkpoint**: A reader arriving at the site can find the notes and see the shape of the series.

---

## Phase 5: User Story 3 - The author publishes without touching the generator (Priority: P2)

**Goal**: Writing a note is editing content files. No file under `src/` is involved.

**Independent Test**: Add a second markdown file, build, see a page and an index entry; delete it
again.

- [X] T032 [US3] Make the loader discover notes by globbing `zoo/notes/*.md` with no list of known files anywhere in the code, and derive the address from the file name (FR-002)
- [X] T033 [US3] Walk the quickstart as written in [quickstart.md](./quickstart.md) with a throwaway second note, confirm a page and an index entry appear with no change under `src/`, then remove it (SC-002)
- [X] T034 [US3] Trigger each of the four failure cases in [quickstart.md](./quickstart.md) by hand and confirm each stops the build with a message that names the note and the problem

**Checkpoint**: The format can carry parts two to five as ordinary content commits.

---

## Phase 6: User Story 4 - Reuse carries the author's name (Priority: P3)

**Goal**: The licence is stated on the page and recorded in the repository, and a picture's use is
named in the credits.

**Independent Test**: Read the end of a note, then check the repository's licence records for the
same path.

- [X] T035 [US4] Add the CC-BY-4.0 annotation for note prose and diagrams to `src/mobility_model_zoo/compliance/templates/REUSE.toml.j2`, covering `zoo/notes/**`, and regenerate with `zoo compliance render`; `REUSE.toml` carries a do-not-edit header and must not be changed by hand (FR-013)
- [X] T036 [US4] Confirm no other path changed licence by diffing the regenerated `REUSE.toml` against its state on `main` and checking that only the new block appears
- [X] T037 [US4] Render the licence line on the note page from the note's own `author`, `date`, `licence_label` and `licence_url`, so the version number stays out of the template (FR-012, FR-013)
- [X] T038 [US4] Confirm `_site/credits/index.html` lists both placed pictures with the note and the index named as their place of use, and that the image licence shown there is still CC0 (contract C1)
- [X] T039 [P] [US4] Run `uv run reuse lint` and confirm the repository stays compliant with the new annotation

**Checkpoint**: Someone republishing a passage can tell from the page who wrote it and under what
terms.

---

## Phase 7: Polish and cross-cutting concerns

- [X] T040 [P] Document the page type in `docs/website.md`: the content layout under `zoo/notes/`, the front matter fields, the two body markers, the placement kind and the budget rule
- [X] T041 [P] Record in `docs/website.md` the two limitations that are deliberately out of scope: diagrams are laid out for a desktop column and their labels are too small on a phone, and the diagram style has to follow the pending rework of the logo and the model motifs
- [X] T042 Run the full gate, not only the site checks: `uv run ruff check`, the guard tests from `scripts/ci/select_tests.py --guards`, `uv run zoo validate --all`, `uv run zoo roadmap check`, `uv run zoo compliance check --ci`, then `uv run zoo site build --offline` and `uv run --group site-check zoo site check --a11y`. The site checks alone are not the gate: this feature's first pull request went red on the linter while every site check was green
- [X] T043 Run `uv run zoo site check --only L2` and confirm it passes with the references in `zoo/notes/01-whose-journey.md`, with no DOI travelling as a link rather than as text (contract L2)
- [X] T044 Read part one end to end at `/notes/whose-journey/` on a phone and a desktop in both colour modes before publishing, as the last human check of SC-001
- [X] T045 Publish: open the pull request for `022-field-notes`, merge it, and confirm the deployed site serves the note, lists it on the index and shows the navigation entry (FR-017)

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: After setup; blocks every user story, because the stylesheet split, the class prefix and the budget split change every page the stories render
- **US1 (Phase 3)**: After Phase 2. This is the MVP
- **US2 (Phase 4)**: After Phase 2. Reads the notes US1 produces, so in practice after US1
- **US3 (Phase 5)**: After Phase 2; validates what US1 and US2 built rather than adding to it
- **US4 (Phase 6)**: After Phase 2. Independent of the other stories except that T038 needs the pages to exist
- **Polish (Phase 7)**: Last

### Within user story 1

Tests T011 to T017 first, and they must fail before T018 and T019 make them pass. Then the loader,
then the check, then the template, then the styling, then the two verification tasks.

### Parallel opportunities

- T008, T009 and T010 touch three different files and can run together
- T011 to T017 are seven independent test cases in one new file; write them together
- T031 and T039 are independent of everything else in their phases
- T040 and T041 are two sections of the same document and can be written together

---

## Implementation Strategy

### MVP

Phases 1 to 3. That delivers one readable note with working references and diagrams, reachable by
link. It is worth stopping there to read it before building the index around it, because the index
only has to exist once the series is announced.

### Increments

1. Setup and foundational: the site is unchanged for a reader, and the budgets are honest
2. US1: part one is readable → stop and read it
3. US2: the index and the navigation entry → the series is announced
4. US3: prove the format carries the next four parts without code
5. US4: the licence and the credits close the attribution loop
6. Polish: documentation and the full gate

### Note on sequencing

Phase 2 is unusually heavy for a foundational phase because this feature's real risk is not the new
code but the four places where it reaches into features 008, 016 and 019. Doing those first, with
the shared stylesheet returned to its state on `main`, means the rest of the work cannot quietly
make an existing page heavier or differently styled.
