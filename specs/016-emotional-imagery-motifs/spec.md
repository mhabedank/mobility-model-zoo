# Feature Specification: Emotional mobility imagery and prominent model motifs

**Feature Branch**: `claude/zoo-website-emotional-imagery-6d19f5`

**Created**: 2026-10-13

**Status**: Draft (revised 2026-10-13 after the image-source decision)

**Input**: User description: "die webseite vom zoo gefällt mir nicht, weil sie kaum emotionale mobiltätsbezogene bilder hat. die symbole der modelle dagegen gefallen mir recht gut in ihrer abstraktheit. ich würde erstens: mit emotionalen bildern arbeiten. und diese symbole weiter hervorheben."

(Translation: The owner dislikes the zoo website because it has hardly any emotional, mobility-related images. The owner does like the model symbols for how abstract they are. The owner wants to work with emotional images and to give the symbols more prominence.)

## Context

The zoo website (feature 008, extended by 012, 014 and 015) uses only inline vector graphics today: the zoo mark and five hand-made model motifs. It has no scene imagery. The 008 branding brief forbade stock photos, so the site reads calm and precise but cold, and nothing on it shows the world the models serve: roads, rails, vehicles, workshops, people on the move.

The model motifs are the part of the identity the owner likes. They follow one grammar: a 96-unit grid, thick round strokes, a slight lean, exactly one mint element and no text. They are shown small, though: 40 px on start-page tiles and 28 px on the roadmap. The model-page hero hides them on narrow screens, picket-forest's hero and preview card have none, and eight planned models have no motif at all.

This feature adds documentary-style scene images of mobility as an emotional stage, and makes the model motifs the main figure on everything that concerns a model.

Decisions taken with the owner on 2026-10-13:
1. **Source**: a search of openly licensed photo collections (Wikimedia Commons, CC0/CC BY) found no usable emotional mobility imagery. The images are therefore **generated locally** on the project's own DGX Spark with an open-weights image model under a permissive licence. Nothing is bought, hotlinked or fetched from a photo platform.
2. **Look**: the images are openly illustrated, never photographic, so nobody mistakes them for real scenes and the site does not look like it is passing off synthetic photos. The house style is a 1970s modernist poster look, quietly futurist, calm and precise: flat colour fields, clean geometry, long diagonals, the identity palette (navy, mint, cream) for sky, ground and buildings, and one warm orange-yellow accent reserved for the vehicle or machine in the picture. The mood expresses the project's vision, "Safer, more affordable and better mobility through AI": morning light, departure, motion ahead, open space. Two photographic series (night-and-rain, then morning light) were rendered first and rejected: the first as depressive, the second as too close to real photographs.
3. **People**: may appear only distant, from behind or in silhouette. Never identifiable.
4. **Composition**: the model motif stands in front of the image stage. The motif is the main figure; the image carries the mood of the field the model works in.

This feature supersedes the 008 branding brief's rule "no stock photos" for generated documentary-style images that meet the requirements below. The brief's other hard constraints stay:
- no generic stock look, 3D renders, mascots or AI-cliché imagery (brains, glowing networks, robots)
- no gradients behind text
- no third-party resources
- no company branding

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The start page makes mobility felt (Priority: P1)

A visitor arriving on the start page, for example from a LinkedIn post or a Hugging Face model card, sees a large, atmospheric mobility scene before reading a word: a train leaving a small station at dawn, cyclists on a riverside lane at sunrise, a tram gliding out of a stop on a drying street. Each of the three topics (product development, automotive security, condition monitoring) carries its own image, so the visitor sees at a glance which part of mobility each topic serves.

**Why this priority**: This is the owner's main complaint. The start page is where most first impressions form, and it is the shortest path to visible change.

**Independent Test**: Build the site with only this story done. Open the start page at desktop and phone width in light and dark mode. Check that a hero image and one image per topic are visible, that all text stays readable, and that all existing site checks still pass.

**Acceptance Scenarios**:

1. **Given** the start page, **When** a visitor opens it at any supported width, **Then** a mobility image fills the hero area and the zoo's purpose line stays readable on a solid surface, not on the image.
2. **Given** the topics section, **When** a visitor scrolls to it, **Then** each of the three topics shows its own image that depicts that field of mobility.
3. **Given** a slow connection, **When** the start page loads, **Then** the text and model motifs appear first, the images fill in without shifting the layout, and the page meets the existing largest-content load target.
4. **Given** a visitor using a screen reader, **When** they reach an image, **Then** they hear a short description of the scene.

---

### User Story 2 - Every model has a prominent motif (Priority: P1)

A visitor scanning the model list, the roadmap or the "Coming next" cards recognises each model by its motif. Every model shown on the site has its own motif, in the same grammar as the existing ones, and the motif is large enough to be the first thing the eye lands on.

**Why this priority**: The owner explicitly likes the motifs and wants them emphasised. Missing motifs (eight planned models, and picket-forest's hero and preview card) are visible gaps today. This story delivers value even if no images ship.

**Independent Test**: Build the site and list every model it shows on the start page, roadmap, model pages and preview cards. Check that each has a distinct motif, shown at the new minimum sizes, at every width.

**Acceptance Scenarios**:

1. **Given** any model shown on the site (published, in progress or planned), **When** its tile, roadmap entry or "Coming next" card is displayed, **Then** it shows that model's own motif.
2. **Given** a model tile on the start page, **When** displayed at any width, **Then** the motif is at least 64 px tall, up from 40 px.
3. **Given** a published model's page, **When** opened at phone width, **Then** the hero still shows the model's motif instead of hiding it.
4. **Given** a new model is added to the site without a motif, **When** the site is built, **Then** the build fails with a message naming the model.
5. **Given** two different models, **When** their motifs are compared, **Then** they are visibly different and each depicts its model's task.

---

### User Story 3 - Model pages put the motif in front of an image stage (Priority: P2)

A visitor opening a published model's page sees the model's motif large, on a calm surface, in front of an image of the field the model works in: a notebook on a sunlit train table for the text model, a microcontroller board wired to a vehicle bus connector for the bus-monitoring model. The page's measured, technical content follows unchanged.

**Why this priority**: This combines both of the owner's wishes in the place where a visitor decides whether to use a model. It depends on stories 1 and 2.

**Independent Test**: Open each published model page at desktop and phone width in light and dark mode. Check that motif and image stage are present and that the motif stays clearly visible against the image.

**Acceptance Scenarios**:

1. **Given** a published model's page, **When** the hero is displayed, **Then** the model's motif sits on a solid plate in front of an image chosen for that model or, failing that, for its topic.
2. **Given** light and dark mode, **When** the hero is displayed, **Then** the motif's strokes keep at least 3:1 contrast against the plate, and all text keeps the existing text contrast levels.
3. **Given** a model with no image of its own, **When** its page is built, **Then** it uses its topic's image. If that is missing too, the page shows the motif alone, and the build reports the gap as a warning, not an error.

---

### User Story 4 - Every image is honest about its origin and reproducible (Priority: P2)

A visitor, a journalist or the owner can see for every image that it is AI-generated, with which model and on whose hardware, and the owner can regenerate or replace any image from its recorded recipe. Nobody has to wonder whether a scene is a real place or a real event. The owner never checks images by hand beyond the one approval at deployment.

**Why this priority**: The constitution makes clean provenance a core principle, the AI Act asks deployers to disclose AI-generated realistic imagery, and a site whose tone is "measured, not claimed" must not pass synthetic scenes off as photographs.

**Independent Test**: Open the image credits page and check that every image in use is listed as AI-generated with model, model licence and date. Delete one image's record, rebuild, and check that the image and its credit disappear and the page falls back. Regenerate an image from its record and check that the result is identical.

**Acceptance Scenarios**:

1. **Given** any image used on the site, **When** a visitor opens the image credits page, **Then** they find it listed as AI-generated, with the generating model, its licence, the generation date, the hardware class (the project's own machine) and a one-line description of the scene.
2. **Given** a page showing images, **When** a visitor looks at the page footer, **Then** a link leads to the credits for the images on that page, and the link text says the images are AI-generated.
3. **Given** an image whose record lacks the generation recipe (model, revision, prompt, seed, steps, size), **When** the site checks run, **Then** they fail and name the image and the missing field.
4. **Given** an image in which an automated check detects an identifiable face or readable text, **When** the site checks run, **Then** they fail and name the image. There is no manual override.
5. **Given** an image is removed from the records, **When** the site is built, **Then** the build no longer contains the file or its credit, and pages fall back as in Story 3.
6. **Given** an image's record, **When** the generator is run again with it in the recorded container image, **Then** the output is perceptually the same image (bit-identical where the toolchain allows it).

---

### User Story 5 - Preview cards carry the motif as the main figure (Priority: P3)

When a zoo page is shared on LinkedIn, Mastodon or a messenger, the preview card shows the model's motif large and centred instead of faint in the corners.

**Why this priority**: This extends motif prominence to the place where the owner shares the work. It depends on Story 2 and is cosmetic compared with stories 1 to 4.

**Independent Test**: Generate the preview cards and check that each model's card shows its motif centred and fully opaque, and that all existing preview-card checks still pass.

**Acceptance Scenarios**:

1. **Given** a model page's preview card, **When** generated, **Then** the model's motif is shown fully opaque inside the card's centre safe area.
2. **Given** a model with a motif, **When** its preview card is generated, **Then** it uses that motif even if the model's site record does not name one explicitly.
3. **Given** a preview card with an image backdrop, **When** checked, **Then** it meets the existing card size, safe-area and contrast checks. If it does not, the card is generated without the image.

---

### Edge Cases

- **Generated image contains an unexpected face, readable text, a brand-like logo or a licence plate**: the automated check rejects it; the owner's agent renders another seed. No manual exception.
- **Generated image contains a physically wrong detail** (rails that do not join, water splashing the wrong way, mirrored instruments): the first pass is done by the agent on a seed sweep; the owner sees only the shortlist at deployment approval. Known-weak subjects are rendered with more seeds.
- **Image resembles a real, recognisable place or vehicle livery**: prompts never name real cities, operators or brands; anything that still reads as a specific real place is rejected.
- **Model weights become unavailable upstream**: the record keeps model id, revision and licence; a cached copy stays on the project's machine, so regeneration still works. A replacement model starts a new series, never a silent swap.
- **Visitor with reduced motion or data-saving preferences**: nothing animates. Images carry no motion effects such as parallax or autoplay video.
- **Phone width**: the image is cropped around a recorded focal point, so its subject stays in view. The motif is never cropped.
- **Dark mode**: images are shown unchanged. The motif plate and all text follow the dark tokens.
- **JavaScript disabled**: images, motifs and credits are all present and readable.
- **Planned model renamed (working name)**: the motif follows the roadmap item, so a rename does not leave a model without a motif.
- **Page weight**: a page whose images push it over the revised budget fails the weight check and names the heaviest image.

## Requirements *(mandatory)*

### Functional Requirements

**Images**

- **FR-001**: The start page MUST show one hero image of mobility and one image for each of the three topics.
- **FR-002**: Each published model's page MUST show an image stage behind or beside the model's motif. The image is chosen for the model or, failing that, taken from the model's topic.
- **FR-003**: Images MUST be illustrated scenes of mobility (vehicles, infrastructure, workshops, test rigs, people travelling) in the house style: flat colour fields, clean geometry, the identity palette (navy, mint, cream) for surroundings and one warm accent on the main vehicle or machine, morning light, forward-looking. Photorealistic renders, generic stock looks, 3D renders, mascots, retro kitsch and AI-cliché motifs (brains, glowing networks, robots) MUST NOT be used.
- **FR-004**: Text MUST NOT be placed directly on an image. Text and motifs that overlap an image stage MUST sit on a solid surface that meets the existing contrast requirements.
- **FR-005**: Every image MUST have a text alternative that describes the scene in one sentence and states that it is AI-generated. The record MUST store this text, and the existing text-alternative check MUST verify it.
- **FR-006**: Each image MUST record a focal point, and every supported width MUST crop the image so that point stays visible.
- **FR-007**: Quickstart, format, roadmap and error pages MUST NOT gain images.

**People, text and real-world references**

- **FR-008**: People MAY appear in images only if they are not identifiable: seen from behind, in silhouette, small in the frame or motion-blurred.
- **FR-009**: An automated check MUST reject any image in which it detects a face at identifiable size or any readable text (including plate-like strings and brand-like words).
- **FR-010**: Prompts MUST NOT name real cities, operators, companies, vehicle models or brands, and images MUST NOT show logos or liveries that read as a real company.

**Generation, provenance and disclosure**

- **FR-011**: Images MUST be generated on the project's own hardware (the DGX Spark or a developer machine) with an open-weights model whose licence permits the use and allows the project to publish the outputs under a permissive licence. Hosted image APIs MUST NOT be used.
- **FR-012**: Each image MUST have a record with: generating model id, revision and licence; the exact prompt, negative prompt, seed, steps, guidance, width and height; the generation date and hardware class; the art-direction series; the placement(s) it serves; text alternative; focal point; and the derivative files with hashes. An image with an incomplete record MUST fail the site checks.
- **FR-013**: The site MUST have an image credits page that lists every image in use as AI-generated with model, model licence, date, hardware class and scene description. Every page that shows images MUST link to it from the footer with wording that says the images are AI-generated. Published image files MUST carry the "AI-generated" marker in their embedded metadata.
- **FR-014**: Images MUST be served from the zoo's own site. No image, script or font may be loaded from another host.
- **FR-015**: The project's licence and third-party notice records MUST cover every image (the image's own licence) and the generating model (its licence and model card reference), so the existing compliance licence check passes.
- **FR-016**: Removing an image's record MUST remove its file and credit from the next build. Pages MUST then fall back to the topic image, or to the motif alone.
- **FR-017**: The owner MUST approve the set of images once per changed set, as part of the site deployment. No other manual review step may be required.
- **FR-018**: An image MUST be reproducible from its record on the same hardware class, model revision and container image: the regenerated image is perceptually the same; bit-identity is reported, not required.

**Motifs**

- **FR-019**: Every model the site shows (published, in progress or planned on the roadmap) MUST have its own motif, drawn in the existing motif grammar: square grid, thick round strokes, slight lean, exactly one mint element, no text.
- **FR-020**: Each motif MUST depict its model's task and MUST be visibly distinct from every other motif.
- **FR-021**: The site build MUST fail when a model it shows has no motif.
- **FR-022**: Motifs MUST be shown at least 64 px tall on start-page tiles and at least 40 px on roadmap entries and "Coming next" cards.
- **FR-023**: On model pages, the hero MUST show the motif at every supported width, including phone width.
- **FR-024**: Motifs MUST keep following light and dark mode, and their strokes MUST reach at least 3:1 contrast against the surface they sit on.
- **FR-025**: A model MUST get its motif without having to name it explicitly in its site record. This applies everywhere the motif is used, preview cards included.
- **FR-026**: Preview cards MUST show the model's motif fully opaque inside the card's centre safe area. An image backdrop MAY be used only if the card still passes all existing preview-card checks.

**Budgets and existing checks**

- **FR-027**: All existing site checks MUST pass: accessibility, privacy, no-branding, depth, roadmap and preview-card checks. The one exception is the total page weight limit, which is revised as follows.
- **FR-028**: The total page weight limit (excluding fonts) MUST be revised from 300 KB to 600 KB for pages that show images. The HTML-per-page limit and the largest-content load target (2 s on a slow mobile profile) MUST stay unchanged.
- **FR-029**: Images MUST NOT delay the display of text or motifs, and MUST NOT shift the layout while loading.
- **FR-030**: The visual identity documentation MUST record the art direction, the generation recipe and the motif-on-stage composition, so later models and series follow them.

### Key Entities

- **Image record**: one generated scene used on the site. It holds:
  - generation: model id, revision, licence; prompt, negative prompt, seed, steps, guidance, width, height; date, hardware class, series
  - placement: the topic or model it serves
  - presentation: text alternative, focal point, aspect
  - files: derivatives with sizes and hashes
  - checks: faces, text, bytes, record completeness
- **Series**: an art direction (style text, negative text, subject prompts per placement) kept with the records, so new images join the same look.
- **Motif**: the abstract symbol of one model, drawn in the shared grammar; used on tiles, roadmap entries, "Coming next" cards, the model hero and preview cards.
- **Image stage**: the pairing of an image record with a page area (start hero, topic, model hero, optional preview-card backdrop). For model heroes it also places the model's motif on a solid plate in front of the image.
- **Image credits page**: the site page that lists every image in use with its AI-generated disclosure and recipe summary. Every page with images links to it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a five-second first-impression test with at least five people, at least four describe the start page with a mobility scene or a feeling such as "morning", "departure" or "calm", not only with "technical" or "documentation", and none with "gloomy".
- **SC-002**: 100% of the models the site shows have a distinct motif, and none is missing from tiles, roadmap entries, "Coming next" cards, model heroes or preview cards.
- **SC-003**: In the same test, at least four of five people can match three models' motifs to their names after viewing the start page once.
- **SC-004**: 100% of the images in use have a complete record, carry the AI-generated marker in file metadata and have a credit on the image credits page. Every missing field, detectable face or readable text added in a test is rejected automatically.
- **SC-005**: Pages with images still render their largest content within 2 seconds on the existing slow mobile test profile, with no visible layout shift.
- **SC-006**: All existing accessibility, privacy, branding and preview-card checks pass in light and dark mode at phone and desktop width.
- **SC-007**: The owner spends no time on image checks. The only manual step is the image-set approval inside the deployment approval.
- **SC-008**: Every image in use can be regenerated from its record on the same hardware class and container image, and the regenerated image is perceptually the same as the stored one (a bit-identical file where the toolchain allows it).

## Assumptions

- The generating model is an open-weights image model under Apache-2.0 whose terms place no restriction on outputs (today Qwen-Image-2512 for final renders, FLUX.2-klein-4B for quick drafts). The project publishes the generated images under CC0 1.0. A model under a non-commercial licence may be used only if the zoo's non-commercial status covers it and the restriction is recorded; it is not the default.
- The minimum set to ship is the start hero plus the three topic images. Model-specific images are added when a fitting one is rendered; until then the topic image is used.
- Automated detection of faces and text is good enough to enforce FR-009 without manual review. A false positive is resolved by rendering another seed, never by overriding the check.
- Physical plausibility (rails, water, reflections) cannot be checked automatically. It is handled by rendering several seeds per subject with a larger, non-distilled model and by the agent's shortlist; the owner's deployment approval is the last look.
- The AI Act's disclosure duty for realistic synthetic imagery (Art. 50) is met by the credits page, the footer wording, the alt text and the embedded metadata marker. No further labelling is needed for a non-commercial private site.
- The 600 KB page budget is a reasonable default for one large image plus a few smaller ones at modern compression. The planning phase may tighten it if measurements allow.
- The existing motif grammar, colour tokens, fonts and the zoo mark stay unchanged. New motifs are drawn to match the five existing ones.
- Video, animation, real photography, stock platforms and the Hugging Face organisation card are out of scope for this feature.
- Depends on features 008 (website and checks), 012 (preview cards), 014 (model page layout), 015 (roadmap and "Coming next" cards) and 006 (compliance harness).
