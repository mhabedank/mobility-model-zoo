# Feature Specification: Zoo website with a landing page for scout-large

**Feature Branch**: `008-zoo-website`

**Created**: 2026-10-09

**Status**: Draft

**Input**: User description: "Eine statische landingpage für scout large. Modell USP, Dokumentation der schnittstelle inkl des outputs. quickstart etc. das branding von mobility modellzoo erweitern. ggf. mobility model zoo als landingpage und als eine page das modell mit allen ob beschrieben eigenschaften. wenn branding erweiter werden soll, gib mir prompt für claude design"

**Owner decisions (2026-10-09)**:
- Hosting: a static site served from the public GitHub repository (GitHub Pages, default project URL, no custom domain).
- Scope: a landing page for the Mobility Model Zoo plus one detail page per published model; scout-large is the first and, at launch, the only model page. Further models get their page automatically once they are published.
- Branding: the existing zoo identity (the "M." avatar: white rounded "M" with a mint dot on royal blue) is extended into a web identity. The design brief for Claude Design is in [`branding-brief.md`](branding-brief.md); the delivered identity (2026-10-09) is in [`design/`](design/): the original bundle plus the extracted identity sheet, page mockups, fonts and mark. Mockup content (install line, code, attribute values, versions, citation) is placeholder and is replaced by data from the release records (FR-004).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Understand and try scout-large in minutes (Priority: P1)

A product manager, UX researcher or ML engineer in mobility hears about scout-large (a link in a post, the Hugging Face card, a search result). They open the model page and, within a few minutes, understand what the model does, why it is worth using instead of prompting a large language model, what it costs to run, and how to install and call it on their own machine.

**Why this priority**: This is the core of the request: a landing page that sells the model honestly and gets people to a first successful run. Without it, there is nothing to launch.

**Independent Test**: Give the model page to a person who has never seen the project. Without other help, they can name the model's main advantage, its main limitation and the hardware it needs, and they can run the quickstart to get output for one of the example texts.

**Acceptance Scenarios**:

1. **Given** a visitor on the scout-large page, **When** they read the first screen, **Then** they see what the model does (finds jobs, pains and gains in German and English mobility texts, with verbatim quotes), its key differentiators (local, fast, verbatim evidence, measured) and one call to action leading to the quickstart.
2. **Given** a visitor who wants to try the model, **When** they follow the quickstart, **Then** they find the install line pinned to the latest released version, a copyable code example and the expected output for an example text, and the steps match what the model card on Hugging Face says.
3. **Given** a visitor comparing options, **When** they look at the quality and speed section, **Then** they see the measured numbers of the latest release (quality composite against the best small zero-shot model, latency and throughput on named hardware, memory) together with what the numbers are measured against.

---

### User Story 2 - Integrate the model's output into one's own tooling (Priority: P1)

A developer who wants to feed scout-large's results into their own pipeline (a research repository, a clustering step, a dashboard) needs a precise description of the interface: what goes in, what comes out, every output field with its type, meaning and allowed values, and how the format is versioned.

**Why this priority**: The request names the interface documentation, including the output, explicitly. Without it, the model cannot be used beyond a demo.

**Independent Test**: A developer writes a parser for the output using only the interface section of the page, and it accepts the real output of the released model for all published example texts.

**Acceptance Scenarios**:

1. **Given** the interface section, **When** a developer reads it, **Then** every field of the output format `jtbd-span-v1` is documented with name, type, meaning, value range or allowed values, and whether it can be empty, including `output_format_version`, `relevant`, `relevance_probability`, `dimensions`, `items` and, per item, `kind`, `quote`, `start`, `end`, `score` and each attribute dimension (`actor_type`, `evidence_type`, `evidence_scope`) with its allowed values.
2. **Given** an example text, **When** the developer looks at the worked example, **Then** they see the input text, the complete output of the released model and a view that marks each quote inside the text, so they can see that quotes are verbatim and offsets point into the input.
3. **Given** a future release that changes the output format, **When** the page is rebuilt, **Then** it documents the new format version, says which model versions produce which format, and keeps the documentation of the old format reachable.
4. **Given** edge cases of the input (empty text, a text with no needs, a very long text, a language other than German or English), **When** the developer reads the interface section, **Then** they learn the model's behavior for each (for example, an empty item list is a valid result; long texts are read in overlapping windows).

---

### User Story 3 - Discover the zoo and its other models (Priority: P2)

A visitor lands on the zoo's start page. They understand what the Mobility Model Zoo is (small, fast, locally runnable models for mobility, each measured and versioned), which topics it covers, which models are published and which are in progress, and how the zoo publishes (measured not claimed, immutable versions, open method and closed data, compliance).

**Why this priority**: The owner wants the zoo as the umbrella, so that later models do not each need their own site. It matters less than scout-large's page at launch, because there is one published model.

**Independent Test**: A visitor can, from the start page alone, name the zoo's topics, find scout-large and reach its page in one click, and find the zoo's publishing principles and legal links.

**Acceptance Scenarios**:

1. **Given** the start page, **When** a visitor opens it, **Then** they see the zoo's purpose, its topics with a one-line description each, and a list of models with name, task, latest version and status.
2. **Given** a model that is listed in the zoo but not yet published, **When** it appears on the start page, **Then** it is marked as in progress and has no detail page and no quickstart.
3. **Given** a new model that is published through the release pipeline, **When** the site is rebuilt, **Then** the model appears on the start page and gets its own detail page without hand-written page content.

---

### User Story 4 - Check whether the model may be used, and on what terms (Priority: P2)

A team lead or a compliance contact checks the model before adopting it: licence, base model and its licence, where the training data came from, what the model must not be used for, known limitations, AI Act classification, privacy notice and how to object, and how to cite it.

**Why this priority**: The project treats compliance as first-class, and adoption in companies depends on these answers. The facts already exist in the release records; the page must surface them, not hide them.

**Independent Test**: A reviewer finds licence, intended use, out-of-scope uses, limitations, training-data summary, AI Act note, privacy notice, copyright policy, imprint and citation from the model page in at most two clicks each.

**Acceptance Scenarios**:

1. **Given** the model page, **When** a reviewer looks for the terms of use, **Then** licence and base-model licence, intended use and out-of-scope uses are on the page itself, and limitations are shown in full, not only behind a link.
2. **Given** the model page, **When** the reviewer looks for provenance, **Then** a link leads to the release's training-data summary, the attribution of sources and the AI Act note of the latest version.
3. **Given** any page of the site, **When** a visitor looks for legal information, **Then** every page links to the imprint, the privacy notice and the copyright policy.

---

### User Story 5 - Recognize the zoo's identity across Hugging Face, GitHub and the website (Priority: P3)

A visitor who knows the zoo from its Hugging Face avatar recognizes the website as the same project, and the website looks like a modern technical product site, not like a template.

**Why this priority**: Branding raises trust and recall but does not block use; the site can launch with a minimal application of the existing logo and colors and adopt the extended identity later.

**Independent Test**: Shown the Hugging Face org page and the website side by side, people identify them as one project; the site uses the same mark and colors.

**Acceptance Scenarios**:

1. **Given** the extended identity from the design brief, **When** it is applied, **Then** the site uses the existing "M." mark unchanged, the same primary colors, and a defined type scale, color set for light and dark mode, code style and a visual for scout-large.
2. **Given** the identity is not delivered yet, **When** the site launches, **Then** it uses the existing avatar and its two colors and stays consistent.

### Edge Cases

- A model version is withdrawn or superseded: the page shows the latest valid version and lists older versions with their dates; a version that must not be used is marked as such.
- Numbers on the page and on the Hugging Face card disagree: this must not happen; both come from the same release record, and the build fails if a number has no source in it.
- The page shows a metric without its reference: not allowed; every quality number names what it is measured against (agreement with frontier reference models on the frozen benchmark), and none is called "accuracy".
- A visitor without JavaScript, on a phone or with a screen reader: all content, including code examples and the output example, is readable; only conveniences such as copy buttons or highlighting may need scripts.
- A visitor in dark mode: the site respects the system setting and stays readable in both modes.
- Example output: only the synthetic example texts are shown; no collected source text appears on the site.
- A broken link to a release file, the Hugging Face repo or a legal page: the build detects it before publishing.

## Requirements *(mandatory)*

### Functional Requirements

**Site and pages**

- **FR-001**: The site MUST consist of a zoo start page and one detail page per published model, served as static pages from the public repository at the default project address of the hosting service.
- **FR-002**: The start page MUST describe the zoo's purpose, list its topics with descriptions, list all models with name, topic, task, latest version and status, link each published model to its detail page, and state the zoo's publishing principles.
- **FR-003**: Models that are not published MUST appear on the start page as in progress, without a detail page, quickstart or performance claims.
- **FR-004**: Page content about models (title, summary, numbers, intended use, limitations, versions, install line, citation) MUST come from the zoo's model metadata and release records, the same sources as the Hugging Face model card; no model fact may be written by hand into the site.
- **FR-005**: Adding a published model MUST produce its detail page without new site code or templates. Model-specific text the metadata does not hold (for example the value proposition) MUST live next to the model's metadata, not in the site, and MUST be checked by the release gate before the model is published, so that a release can never break the site build.

**scout-large detail page**

- **FR-006**: The page MUST open with the model's value proposition: what it does, for whom, and its differentiators as measured facts (runs locally on a CPU or laptop GPU, every item is a verbatim quote with offsets, quality and speed against the pilot's generative models, German and English, open licence).
- **FR-007**: The page MUST have a quickstart: install line pinned to the latest released version, a minimal code example, the expected output for one example text, and the hardware and memory needed.
- **FR-008**: The page MUST document the interface: input (language, length, windowing), the output format `jtbd-span-v1` field by field with types, meanings, allowed values and empty cases, the attribute dimensions and their values, and the versioning of the output format.
- **FR-009**: The page MUST show at least one worked example per published example text: input, full output of the released model, and the quotes marked in the input text. The output MUST be produced by the released model version, not written by hand.
- **FR-010**: The page MUST show quality and speed of the latest release with their references and hardware, including the comparison figures already in the model card, and MUST name metrics honestly (agreement with reference models, not accuracy).
- **FR-011**: The page MUST show intended use, out-of-scope uses and all limitations in full.
- **FR-012**: The page MUST show licence and base-model licence, link the training-data summary, source attribution and AI Act note of the latest release, and give the citation in a copyable form.
- **FR-013**: The page MUST list all released versions with date, status and change summary, and link each to its Hugging Face revision.
- **FR-014**: The page MUST link to the model on Hugging Face, to the recipe and to the code repository.

**Compliance and privacy**

- **FR-015**: The site MUST NOT set cookies, use analytics or tracking, or load fonts, scripts, images or other resources from third parties; everything is served from the site itself.
- **FR-016**: Every page MUST link to the imprint, the privacy notice and the copyright policy. The privacy notice MUST be extended to cover the website and its hosting provider (access logs kept by the host).
- **FR-017**: The site MUST carry no consulting branding, advertising, funding links or paid offers, in line with the owner's non-commercial decision.
- **FR-018**: The site MUST contain no collected source text and no personal data; examples are the synthetic example texts only.
- **FR-019**: The site's own content and assets MUST carry licence and copyright information that passes the repository's existing licence compliance check.

**Quality and publishing**

- **FR-020**: The site MUST meet WCAG 2.1 level AA (contrast, keyboard use, alt text for figures, semantic structure) in light and dark mode.
- **FR-021**: All content MUST be readable without scripts; scripts may only add conveniences.
- **FR-022**: The site MUST be rebuilt and published automatically when a model release is published or site content changes on the main branch, and the build MUST fail on a broken internal or release link, a model fact without a source in the metadata, or a failed accessibility or licence check.
- **FR-023**: The site MUST be in English, matching the model cards.
- **FR-024**: The site MUST apply the zoo's existing mark and colors; the extended identity from the design brief MUST be adoptable by changing the site's design settings, without touching page content.
- **FR-025**: The Hugging Face org card and the repository README MUST link to the website.

### Key Entities

- **Model**: a published or planned model of the zoo; name, topic, task, variant, title, summary, licence, base model, languages, intended use, out-of-scope uses, limitations, citation, value proposition. Source: the model's metadata in the zoo.
- **Release**: one immutable version of a model; version, date, status, changes, output format version, files, provenance summary, links to the training-data summary and AI Act note, quality and performance results.
- **Output format**: a versioned description of a model's output (here `jtbd-span-v1`): fields, types, allowed values; produced by one or more releases.
- **Example**: a synthetic example text published with the model, and the output the released model produces for it.
- **Topic**: a group of models (productdev, security, condition-monitoring) with a name and description.
- **Identity**: the zoo's mark, colors, type scale and visual rules, applied across the website, the Hugging Face org card and the README.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a test with at least three people from the target group who have not seen the project, each states the model's main advantage, a main limitation and the hardware it needs after at most 3 minutes on the model page.
- **SC-002**: A developer gets output for an example text by following only the quickstart, in under 10 minutes on a laptop (excluding model download time).
- **SC-003**: A parser written only from the interface section accepts 100% of the released model's outputs for all published example texts.
- **SC-004**: 100% of the model facts on the site match the latest release record and the Hugging Face card; a deliberate mismatch fails the build.
- **SC-005**: The site makes zero requests to third-party hosts and sets zero cookies, checked on every page.
- **SC-006**: Every page passes an automated WCAG 2.1 AA check with zero violations in light and dark mode.
- **SC-007**: Every page loads its main content in under 2 seconds on a typical mobile connection.
- **SC-008**: Publishing a new model's release makes its detail page appear on the next site build with no change to the site's code or templates; a release whose page text is missing or invalid is stopped by the release gate, not by the site build.
- **SC-009**: From any page, imprint, privacy notice and copyright policy are reachable in one click; licence, limitations and AI Act note of a model in at most two.

## Constitution Compliance

Principles and sections this feature touches, and how it complies (constitution 2.0.0):

- **II. Grounded evidence**: worked examples show every item at its offsets in the input; an example whose quote does not equal the text at its offsets blocks publication (FR-009). An empty item list is shown as a valid result.
- **III. Measure before optimizing, metric naming**: every number names its reference, benchmark or hardware; agreement with reference models is never called accuracy (FR-010). Results shown on the site carry the frozen benchmark version, the deterministic checks and the number of contested items, as the gate before reporting a result requires.
- **V. Budgets per task**: hardware and memory figures are shown with the hardware they were measured on, as recorded in the release results.
- **VI. Clean provenance**: only synthetic example texts are shown; no collected source text or personal data appears on the site (FR-018). Training-source attribution is linked from the release, not copied.
- **IX. Reproducible, dated releases**: the site never publishes model files; it only reflects versions published through the release pipeline, shows deprecated versions as such and shows the outputs of the published card (FR-004, FR-013).
- **Project scope & layout**: the site is shared by all topics; per-model text lives with the model; a new topic or model needs no site code change (FR-005).
- **Tasks and releases**: the release pipeline stays the only way to publish a model; the site is rebuilt after it (FR-022), and per-model site text is checked by the one release gate (FR-005).
- **Resources & cost**: hosting and CI are free for the public repository; no cash budget is needed.
- **Compliance (owner direction 2026-10-08)**: no cookies, tracking or third-party resources; legal links on every page; privacy notice extended to the website; no branding or advertising (FR-015 to FR-019).

Principles I, IV, VII, VIII and X are not touched: the site does not extract, label, train or compare architectures.

## Assumptions

- The site is served from the public GitHub repository at the default project address; a custom domain may follow later and is out of scope.
- Hosting through GitHub means GitHub sees visitors' IP addresses in its access logs; the zoo itself collects nothing. The privacy notice is extended accordingly (FR-016).
- Imprint and privacy contact reuse the existing pages and addresses linked from the privacy notice; no new legal entity or contact is created.
- There is no live demo that runs the model in the browser or on a server; worked examples use outputs produced with the released model. A live demo can be a later feature.
- The value proposition and differentiators are written once per model as part of its metadata and checked against the release numbers; they claim nothing that the release record does not support.
- The extended identity (type, color set, visuals) comes from Claude Design using the brief in `branding-brief.md`; the site launches with the existing mark and colors if the identity is not ready.
- The Hugging Face org card stays the zoo's home on Hugging Face; the website complements it and does not replace the model cards.
- Unpublished models (security, condition monitoring) are listed without detail pages until their first release.
