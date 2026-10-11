# Feature Specification: Model pages in progressive depth

**Feature Branch**: `013-model-page-layout`

**Created**: 2026-10-11

**Status**: Draft

**Input**: User description (translated from German): "Rebuild the model pages of our website for published models. I do not like the order of the information, and I do not like its depth. The order must be: what kind of model is this, what can it do, why would you use it? Then quality and speed, which is very important. Then limits and disclaimer, where things like experiments go. Then the quickstart, then deeper references, then deeper information on the quality metrics or on references we have to publish, such as the list of training data, where that is required. At the start, take care that it is not too much and not too detailed, only the most important information piece by piece, and the deeper you get, the more detailed it becomes. Right now it is detailed everywhere. Graphics, for example, matter much more than text details: scout has nice charts, but they only come far down the page. Find out what best practice is and what readers in the target group expect, and then rebuild it."

## Context: the pages today

Measured on the live site on 2026-10-11 in a 1440 × 900 desktop window (one "screen" = 900 px of page height):

| Section (today's order) | scout-large: starts at screen | scout-large: words | picket-forest: starts at screen | picket-forest: words |
|---|---|---|---|---|
| Hero | 0.1 | 65 | 0.1 | 58 |
| Why this model | 0.6 | 167 | 0.6 | 128 |
| Quickstart | 1.3 | 211 | 1.2 | 121 |
| Interface | 3.3 | 798 | 2.4 | 627 |
| Worked examples | 6.2 | 354 | 4.4 | 340 |
| Quality and speed (first chart) | 8.6 (9.3) | 310 | 5.8 (no chart) | 77 |
| Use and limits | 10.1 | 373 | 6.5 | 413 |
| Licence and provenance | 11.1 | 99 | 7.6 | 95 |
| Versions, citation, notes | 11.9 – 14.0 | 426 | 8.3 – 10.0 | 267 |

Findings: a reader passes about 1,600 words of quickstart, interface reference and examples before the first quality number of scout-large, and the charts start in screen 9 of 14. The status chip at the top shows the lifecycle ("published"), not the release status: picket-forest is an `experimental` release, and that is visible only because its hand-written text says so. Every section is written at full depth; there is no layer that a reader can stop after. The Hugging Face model card has the same detail-first order (summary, intended use, input and output, how to run, examples, then quality).

## Context: best practice and reader expectations

Research on 2026-10-11 (sources below) supports the requested order, with one addition that the owner accepted:

- Model documentation standards put scope and limits before usage: the Hugging Face model card template orders summary, details, uses and out-of-scope use, bias, risks and limitations, then "how to get started"; Meta's Llama 3.1 card does the same. In the Hugging Face user study, readers ranked limitations as the second section they look at and found heavily detailed cards overwhelming, suggesting a simple base card with advanced detail layered on top.
- Developer-oriented model pages (Ultralytics YOLO, STMicroelectronics model zoo, Qualcomm AI Hub) show comparison charts and per-hardware speed and memory early; Qualcomm places usage warnings near the top.
- Web reading research (Nielsen Norman Group) shows readers scan the top of a page and the start of lines; an answer should give what was asked plus the caveats needed to keep it accurate, with more on demand. This is why the status and the two or three most important exclusions sit in the first screen, while the full limits come in layer 3.
- Diátaxis separates tutorial (quickstart), reference (interface, format) and explanation (metric definitions, method), which maps to layers 4, 5 and 6.
- No regulation fixes the position of training-data summaries or AI Act notes on a page; they belong in the detail layer and are linked from the limits layer.
- Not adopted: a short "try it" snippet right after the charts. The owner chose to keep all code after the limits and to offer a jump link to the quickstart instead.

Sources: Mitchell et al., "Model Cards for Model Reporting" (2019, arXiv:1810.03993); Hugging Face model card template, annotated model card, model card user studies and model release checklist (huggingface.co/docs/hub); Liang et al., Nature Machine Intelligence 2024 (arXiv:2402.05160); Nielsen Norman Group articles on F-shaped reading, text scanning patterns and B2B specifications; diataxis.fr; model pages of Llama 3.1, Qwen3, Whisper large-v3, Ultralytics YOLO11, STMicroelectronics st_yolo_x and Qualcomm AI Hub.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Decide in the first screen whether the model is relevant (Priority: P1)

A product researcher, an ML engineer or an automotive security engineer arrives on a model page from a shared link, a search or the zoo start page. Within the first screen they learn what kind of model it is, what it does with what input, why they would use it rather than an alternative, and on what terms: its release status (experimental or released), its usage class and licence, and what it runs on. The text is short, there is no reference material yet, and nothing has to be read twice.

**Why this priority**: Most visitors decide within seconds whether to stay. If the first screen does not answer "what is it, is it for me, may I use it", the rest of the page is never read.

**Independent Test**: Open each published model page in a desktop window and at phone width; without scrolling on desktop (and within the first two screens on a phone), find the task, a one-line description, the main reasons to use it, the release status, the usage class and the licence; count the words of the overview layer.

**Acceptance Scenarios**:

1. **Given** a published model whose latest release has status `experimental`, **When** a reader opens its page, **Then** the first screen states that the model is experimental and not ready for production use, derived from the release record and not from hand-written text.
2. **Given** a model whose usage class is non-commercial, **When** a reader opens its page, **Then** "Non-commercial" is visible in the first screen.
3. **Given** any published model, **When** the overview layer is rendered, **Then** it contains no field tables, no code, no metric tables and stays within its word budget.
4. **Given** any published model, **When** a reader looks at the first screen, **Then** they see the two or three most important things the model is not for, with a link to the full limits.

---

### User Story 2 - See how good and how fast it is, as pictures first (Priority: P1)

Right after the overview, the reader sees the model's quality and speed: a small number of headline figures, each with what it is compared against, and the charts the model has (for scout-large: quality against speed of the compared models, and latency per machine). Graphics come before explanatory text; the full metric tables are not here but in the detail layer at the end, one link away.

**Why this priority**: Quality and speed are what technical readers check right after "what is it". The charts already exist and say more than the tables, but today they start in screen 9 of 14.

**Independent Test**: Open the scout-large page in a 1440 × 900 window and measure where the first chart starts; open a model without charts (picket-forest) and check that its headline figures are shown as figures with their comparison, not as a table.

**Acceptance Scenarios**:

1. **Given** a model with charts, **When** the page is rendered, **Then** the quality and speed section comes directly after the overview and shows the headline figures and charts before any prose of more than one sentence.
2. **Given** a model without charts, **When** the page is rendered, **Then** the section shows its headline figures with their comparison and the hardware or benchmark they were measured on, and links to the full metric tables.
3. **Given** any headline figure, **When** a reader follows its note marker, **Then** they reach the note that says what the number is measured against, as today.

---

### User Story 3 - Know the limits before trying it (Priority: P2)

Before the reader installs anything, the page tells them where the model stops being trustworthy: the release status in a sentence, what the model is not for, and the few most important known failure modes, including what experiments showed (for example a criterion that is not met or an outcome that blocked a claim). The full limitations text and the evidence behind it are available one step deeper.

**Why this priority**: The zoo's principle is an honest card. A reader who learns the limits after integrating the model loses time, and an experimental model must not look production-ready because the disclaimer sits below the code.

**Independent Test**: On each published model page, check that the limits section comes before the quickstart, that its first visible part fits the budget, and that the full limitations text of the release is still on the page.

**Acceptance Scenarios**:

1. **Given** an `experimental` release whose card lists unmet criteria, **When** the limits section is rendered, **Then** it states the experimental status and names the unmet criteria in short form before any longer text.
2. **Given** a model with a long limitations text, **When** the limits section is rendered, **Then** the short form is visible and the full text is available on the same page without JavaScript.

---

### User Story 4 - Try it in a few minutes (Priority: P2)

A reader who decided to try the model finds the quickstart after the limits: install, run on an example, the output to expect, and what hardware it needs. Nothing else; the interface reference and the worked examples follow afterwards. A jump link at the top takes readers who already know the model straight to the quickstart.

**Why this priority**: The quickstart is the main action of the page, but it is only useful to a reader who has decided the model fits; it keeps its content, it only moves.

**Independent Test**: From the top of each model page, reach the quickstart in one click; copy its commands and confirm the expected output is shown.

**Acceptance Scenarios**:

1. **Given** any published model, **When** a reader activates the quickstart jump link in the first screen, **Then** the page scrolls to the quickstart.
2. **Given** a non-commercial model, **When** the quickstart is rendered, **Then** the non-commercial notice is repeated there, as today.

---

### User Story 5 - Find the reference and the required documents at the end (Priority: P3)

An engineer integrating the model, or an auditor checking it, scrolls past the quickstart into the deeper layers: first the reference (the interface in summary with a link to the full output-format page, and the worked examples), then the detail layer (the complete metric tables and their notes, the training data summary and source attribution, the AI Act note, the compliance record, the base model and its licence, privacy, the version history and the citation). Everything that has to be published is there; it is just no longer in the way of the first-time reader.

**Why this priority**: These parts are required and valuable, but only for readers who already decided to go deeper.

**Independent Test**: Compare the list of links and documents of each model page before and after the change: nothing required has disappeared, and each item sits in the reference or detail layer.

**Acceptance Scenarios**:

1. **Given** today's page links to a training data summary, AI Act note, compliance record, licence and limitations, **When** the new page is rendered, **Then** every one of these links is still on the page.
2. **Given** a bookmark or external link to a section anchor of today's page (for example `#quickstart`, `#interface`, `#examples`, `#quality`, `#limits`, `#provenance`, `#versions`, `#cite`, a note `#fn-N`), **When** it is opened, **Then** it lands on the section with that content.
3. **Given** the full field-level documentation of an output format, **When** the reference layer is rendered, **Then** the model page shows the interface in short form and links to the format page instead of repeating every field in full.

---

### User Story 6 - Every model page follows the same structure (Priority: P3)

The owner publishes a new model, or a new release of an existing one. Its page gets the same order and depth budgets without anyone arranging it by hand, whether the model is an LLM-based text extractor, a microcontroller detector without charts, or a deprecated release.

**Why this priority**: The zoo grows by models; a structure that each page has to be tuned for will drift.

**Independent Test**: Build the site from the frozen test registry and from the live registry; the build check that verifies order and budgets passes for every model page and fails for a page that breaks them.

**Acceptance Scenarios**:

1. **Given** a model page whose overview exceeds its word budget, **When** the site is checked, **Then** the check fails and names the page, the layer and the count.
2. **Given** a deprecated release, **When** its page is rendered, **Then** the deprecation banner stays at the very top, above the overview.

---

### Edge Cases

- A model without charts (picket-forest today): the quality section shows headline figures with their comparison; it is not empty and does not fall back to the full table in this layer.
- A model with only one or two headline figures, or with a figure that has no comparison.
- A model without worked examples or without an output-format page: the reference layer omits the missing part without leaving an empty heading.
- A model whose hand-written text still repeats the experimental status: the structured status line and the text must not contradict each other; hand-written website text does not state a release status at all.
- A deprecated release: the deprecation banner is shown, and the status chip shows the release status the version had before it was deprecated.
- A model whose limitations text is very long (picket-forest: about 400 words): only the short form is in the visible limits layer.
- JavaScript disabled: every layer, including collapsed detail, is present in the page (check A2, with the field table on the output-format page).
- Phone width (390 px): the order is the same, nothing scrolls sideways, charts stay readable or show their values as a list.
- A release that is experimental and non-commercial at the same time: both statements appear in the first screen without crowding out the description.

## Requirements *(mandatory)*

### Functional Requirements

**Order and layers**

- **FR-001**: Every published model page MUST present its content in this order of layers: (1) overview: what the model is, what it does, why use it, on what terms; (2) quality and speed; (3) limits and status; (4) quickstart; (5) reference: interface summary and worked examples; (6) details and documents: complete metrics with notes, training data and provenance, compliance documents, versions, citation.
- **FR-002**: Each layer MUST open with its most important information in short form; detail beyond the short form MUST be placed later in the same layer, collapsed, or moved to a deeper layer. Depth MUST increase from layer 1 to layer 6, and no earlier layer may contain the full form of something a later layer holds.
- **FR-003**: The page MUST offer jump links in the first screen to at least the quickstart, the limits and the details layer, and an in-page overview of the layers.

**Layer 1: overview**

- **FR-004**: The overview MUST show the model name, task and topic, a one-line description, the main reasons to use it (at most four, each short), the facts that decide whether a reader may use it (release status, usage class, licence, and what it runs on: languages or target hardware), and the two or three most important things the model is not for, linking to the limits layer.
- **FR-005**: The release status (`experimental` or `released`) MUST be derived from the latest release record and shown in the overview; for an `experimental` release, the overview MUST say in one sentence that the model is not ready for production use.
- **FR-006**: The overview MUST stay within a budget of 150 words of running text plus at most 40 words for the "not for" points (chips and buttons excluded) and MUST NOT contain code, tables or metric lists.

**Layer 2: quality and speed**

- **FR-007**: The quality and speed layer MUST follow the overview directly and MUST show at most four headline figures and the model's charts before any explanatory text of more than one sentence.
- **FR-008**: Each headline figure MUST keep its comparison, if it has one, and its note on what it is measured against; every number MUST still equal its source and the model card (today's checks F1–F4).
- **FR-009**: A model without charts MUST still show its headline figures, and the comparison of each figure that has one, in a visual form rather than as a table row.
- **FR-010**: The complete metric tables MUST NOT appear in layer 2; layer 2 MUST link to them in layer 6.

**Layer 3: limits and status**

- **FR-011**: The limits layer MUST come before the quickstart and MUST open with a short form: the release status in one sentence, the unmet success criteria (for an `experimental` release) and the most important known failure modes, at most five items and 120 words in total. What the model is not for is shown in short form in the overview (FR-004) and in full in this layer (FR-013).
- **FR-012**: For an `experimental` release, the short form MUST name the success criteria the release does not meet, as stated on its model card.
- **FR-013**: The full intended-use, out-of-scope and limitations texts of the release MUST remain on the page in layer 3 below the short form or collapsed, and the layer MUST link to the evidence behind the limits (recipe, results, release notes) where it exists.

**Layer 4: quickstart**

- **FR-014**: The quickstart MUST contain only what is needed to run the model once: hardware note, install, run on an example, expected output, and the non-commercial notice where it applies. Its content MUST stay as complete as today.

**Layer 5: reference**

- **FR-015**: The reference layer MUST describe the interface in short form (input, output, guarantees) and link to the output-format page for the full field-level documentation, edge cases and versioning, instead of repeating them in full on the model page.
- **FR-016**: The worked examples MUST be in the reference layer, after the interface.

**Layer 6: details and documents**

- **FR-017**: The details layer MUST contain the complete quality and speed tables, the notes on what each number is measured against, licence and usage, base model and its licence, training data summary and source attribution, AI Act note, compliance record, model files, recipe, code, privacy note, version history and citation, wherever the release provides them.
- **FR-018**: Every link and document a model page offers today MUST remain reachable from the page; links required by today's check L3 (licence, limitations, AI Act note, legal pages) MUST remain.

**Across the page**

- **FR-019**: Existing section anchors (`#quickstart`, `#interface`, `#examples`, `#quality`, `#limits`, `#provenance`, `#versions`, `#cite`, `#notes`, `#fn-N`) MUST keep resolving to the section with that content.
- **FR-020**: Every model page MUST be generated in this structure from the registry without per-page arrangement; hand-written website text per model MUST stay limited to short fields that are validated like today's (no free-standing numbers, placeholders only).
- **FR-021**: The site check MUST verify the layer order and the budgets of FR-006, FR-007 and FR-011 for every model page and fail with the page, layer and measured value when one is broken.
- **FR-022**: All existing site checks (facts, examples, links, privacy, accessibility in both colour schemes, completeness without JavaScript, reflow at 390 px, page weight, load time) MUST keep passing for every page. The completeness check without JavaScript (A2) changes as FR-015 requires: the field table is required on the output-format page instead of the model page.
- **FR-023**: Code MUST NOT appear before the limits layer; the quickstart is reached early only through the jump link of FR-003.
- **FR-024**: The model card template MUST follow the same order of layers (overview, quality and speed, limits, how to run, reference, details) for every release published after this feature; cards of releases already published MUST stay unchanged. Facts and required card content stay the same; only order and short forms change.

### Key Entities

- **Layer**: one of the six ordered parts of a model page, with a purpose, a short form, an optional full form, and a budget (words, items or figures) for what is visible before any collapsed detail.
- **Headline figure**: a quality or speed number chosen for layer 2, with its label, its comparison (optional) and its note on what it is measured against.
- **Release status**: `experimental` or `released`, taken from the latest release record; separate from the lifecycle shown today ("published", "deprecated").
- **Limits short form**: the status sentence, the out-of-scope points and the most important failure modes, taken from the release's card and site text.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a 1440 × 900 desktop window, the first quality graphic (chart or headline figure) of every published model page starts within the first 2 screens (today: screen 8.6 to 9.3 for scout-large, 5.8 for picket-forest).
- **SC-002**: Release status, usage class and licence are visible without scrolling on a 1440 × 900 desktop window and within the first two screens at 390 px width, for every published model page.
- **SC-003**: The limits layer of every published model page starts within the first 4 desktop screens (today: 10.1 for scout-large, 6.5 for picket-forest).
- **SC-004**: The running text a reader passes before the quality layer is at most 200 words (today: about 1,600 for scout-large).
- **SC-005**: In a five-minute test with at least five readers from the target group, at least four can say within 30 seconds of opening a model page what the model does, how good and how fast it is in one sentence, and whether it is experimental.
- **SC-006**: Zero links or documents are lost: an inventory of every link on each model page before and after the change shows no removed target.
- **SC-007**: Every existing site check passes for every page, and the new structure check passes for every published model page.
- **SC-008**: The first release of any model published after this feature has a model card whose sections follow the layer order, and its quality section appears before its how-to-run section.

## Constitution Compliance

Principles this feature touches, and how it complies (constitution 2.2.0):

- **III. Measure before optimizing (metric naming)**: every number on the page keeps its note on what it is measured against; headline figures and unmet criteria take their values from the release results or the task's success criteria, never from hand-typed text (FR-008, FR-012).
- **V. Small and local, budgets per task**: headline figures keep their hardware and measurement origin (board, emulator, host); nothing measured in an emulator is presented as a hardware result.
- **VI. Clean provenance, restrictions carry over**: usage class and licence move into the first screen, "Non-commercial" is visible there (FR-004), and every provenance, training-data and compliance document stays linked (FR-017, FR-018).
- **IX. Reproducible, dated releases**: the release status is shown where users look first, derived from the release record (FR-005); an `experimental` release names every unmet criterion with its measured value (FR-012); published versions, release records and model cards are not changed, and the new card order applies to new releases only (FR-024).
- **Tasks and Releases**: new checks run in the one shared release gate and site check, the same for every task (FR-021).
- Principles I, II, IV, VII, VIII and X and the cost rules are not touched: no change to models, data, prompts or experiments. The reader test (SC-005) has its pass threshold written down before it runs.

## Assumptions

- Target readers are, in this order: product researchers and product managers in mobility, ML engineers, and automotive or embedded security engineers evaluating a model; secondary readers are auditors and other researchers looking for provenance and compliance documents. All read English; the site stays English.
- "Experiments and so on" in the description is read as: the release status (experimental or released), the success criteria an experimental release does not meet, and what experiments showed about the limits. The full experiment reports stay where they are (recipes, results) and are linked from the limits layer.
- The budgets (150 words overview, at most four headline figures, five limit items and 120 words) are starting values chosen from today's pages; they can be tuned during planning without changing the order.
- The quickstart is placed after the limits as requested; readers who want it immediately use the jump link in the first screen.
- The field-level interface documentation already exists on the output-format pages (feature 008) and becomes the single full reference; the model page keeps a short form.
- No model fact or required document is removed; the change is in order, depth and presentation. Existing charts are reused; new chart types are not required.
- The model cards of releases already published are not changed or republished; their hashes stay valid for the example check. The new card order takes effect with each model's next release (FR-024).
- Feature 012 (social preview images, merged) also changed the hero, the site checks, the website-text schema and both models' website text; this feature builds on it and keeps its share line and checks.
- The visual identity (tokens, components) of feature 008 stays; new components follow it.
