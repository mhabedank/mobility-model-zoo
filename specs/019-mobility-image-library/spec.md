# Feature Specification: Mobility image library in the house style

**Feature Branch**: `claude/mobility-image-library-019`

**Created**: 2026-10-14

**Status**: Draft

**Input**: User description: "please create about 100 images of the same style for a diverse set of mobility types, also infrastruktur, also AI also IoT."

## Context

Feature 016 gave the zoo website its first imagery: six AI-generated scenes in one house style (the 1970s modernist poster look called SIEBDRUCK: flat colour fields, navy, mint and cream, one warm orange-yellow accent on the vehicle or machine) plus the checks, records and disclosure that go with them. Those six cover exactly the places the site had at the time: the start hero, the three topics and the two published models.

That is a thin stock. Every new model, every roadmap entry that becomes a page, every post or talk the owner prepares, and every topic the zoo may add needs another scene in the same look, and today each one means a new rendering session with its own prompt writing, seed sweep and review. The six also show a narrow slice of mobility: trains, a tram, a car workshop, a wheelset. Buses, bicycles, ships, aircraft, roads, bridges, depots, sensors and the quiet machinery of AI at work are missing.

This feature builds a library of about one hundred images in the same house style that covers mobility broadly: the modes people and goods move by, the infrastructure that carries them, and the sensing (IoT) and computing (AI) that the zoo's models live in. Every library image is a full 016 record, so it passes the same checks, carries the same disclosure and can be placed anywhere the site places images, now or later.

Decisions taken with the owner on 2026-10-14:
1. **Where the library lives**: in the project repository as a pool of image records. There is no gallery page on the site and no separate publication of the set. A library image reaches the site only when the owner records a placement for it.
2. **Who picks**: the owner picks one image per subject themselves, from a contact sheet that shows every candidate that passed the automated checks. Failed candidates are never shown.

3. **Stop after round 2** (2026-10-16): after two rendering rounds the pool holds 91 images; the owner declined a third round ("we have enough images for now"). The coverage table stays the target for later rounds, but FR-001 (at least 100) and the minimums of `workshop` (5 of 8) and `iot` (8 of 10) are not met at the close of this feature; see validation.md, section 4. `zoo site images check --require-coverage` reports this and is therefore not part of CI.

Decisions carried over from feature 016 and not reopened here:
- generated on the project's own hardware with an open-weights model under a permissive licence; published under CC0
- the SIEBDRUCK house style, with the accent colour on the vehicle or machine only
- people only distant, from behind or in silhouette; no faces, no readable text, no real places, operators or brands
- no AI clichés (brains, glowing networks, robots), no photorealism, no 3D-render look

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A broad, consistent library exists (Priority: P1)

The owner opens the library and sees about one hundred scenes of mobility in one recognisable style: a bus pulling into a stop, a ferry at a pier, cyclists on a winter morning, a motorway bridge, a tunnel portal, a vibration sensor bolted to a bearing housing, a telematics box in a truck cab, a person from behind at a screen showing a waveform in a depot office. The images look like one family, and together they cover the whole of mobility, not just rail.

**Why this priority**: This is the request. Without the library nothing else in this feature has value, and the library has value on its own even if nothing on the site changes.

**Independent Test**: Count the library's images, group them by theme, and check that every theme in the coverage table below meets its minimum, that each image passes the 016 checks (record completeness, no faces, no readable text, byte caps, marker) and that a style check finds every image within the house palette.

**Acceptance Scenarios**:

1. **Given** the finished library, **When** its images are counted, **Then** there are at least 100, the six existing images among them.
2. **Given** the coverage table, **When** images are grouped by theme, **Then** every theme reaches its minimum count and no single theme holds more than a fifth of the library.
3. **Given** any library image, **When** the automated checks run, **Then** it has a complete record, no detectable face or readable text, and its colours stay within the house palette with the accent on the main vehicle or machine.
4. **Given** any two library images, **When** compared, **Then** they are not near-duplicates of each other (different subject or clearly different composition).
5. **Given** an image of AI or IoT at work, **When** viewed, **Then** it shows concrete things (sensors, cabinets, antennas, boards, screens with abstract traces, people at work seen from behind) in a mobility setting, never an abstract cliché.

---

### User Story 2 - The owner picks every image from a clean contact sheet (Priority: P1)

The owner chooses each library image personally, but never wades through unusable renders. Rendering and the rejection of candidates that fail a check (face, text, palette, near-duplicate, record) are automated. The owner then opens a contact sheet, grouped by theme and subject, that shows every passing candidate of every subject with a number, and marks one candidate per subject or "none of these". Subjects marked "none" are re-rendered with new seeds and come back on a further sheet holding only those subjects. After the last pick, import is the only remaining step.

**Why this priority**: The owner wants the final say on every image in the library, and the owner's time is the scarce resource. Without a clean, numbered sheet the choice among several hundred renders is not practical.

**Independent Test**: Run a rendering round, open the sheet, and check that it shows only passing candidates, grouped by theme and subject, each numbered; mark one candidate for some subjects and "none" for others; check that the next round renders only the "none" subjects and that the import takes exactly the marked candidates.

**Acceptance Scenarios**:

1. **Given** a batch of renders with several seeds per subject, **When** the checks run, **Then** every failing candidate is rejected with the check named and does not appear on the sheet.
2. **Given** the sheet, **When** the owner opens it, **Then** candidates are grouped by theme and subject, each carries a visible number and is shown at a size that lets the owner judge composition and detail, and the owner can state picks by number.
3. **Given** the owner marks a subject "none of these", **When** the next round runs, **Then** that subject is re-rendered with new seeds and only such subjects appear on the next sheet.
4. **Given** the owner's picks, **When** the library is imported, **Then** exactly the marked candidates enter the records, and the owner has nothing else to do.

---

### User Story 3 - Library images are placed from the pool (Priority: P2)

A model that gets a page, or a topic that needs a new scene, receives a fitting image from the pool by one record change instead of a new rendering session. The owner can see the whole pool at a glance, with theme, subject and id, without building the site. Images that are not placed stay in the pool and never reach the site.

**Why this priority**: Placement is why the pool exists for the site. It depends on Story 1.

**Independent Test**: Open the pool overview and find a fitting image for a model that had only its topic image; record the placement, rebuild, and check the model page shows it with the motif in front. Check that unplaced images are absent from the built site and that all existing checks pass.

**Acceptance Scenarios**:

1. **Given** the pool, **When** the owner opens its overview, **Then** every image is shown small with its theme, subject and id, grouped by theme, so a fitting image can be found in a minute.
2. **Given** a library image recorded as the placement for a model or topic, **When** the site is built, **Then** that page shows it, with the motif on its plate in front as in feature 016, and the credits page lists it.
3. **Given** a library image with no placement, **When** the site is built, **Then** none of its files is part of the built site, it has no credit, and the build does not warn about it.
4. **Given** a placement is moved from one pool image to another, **When** the site is built, **Then** the old image leaves the site and its credit, the new one takes its place, and the page weight stays within budget.

---

### User Story 4 - The library stays reproducible and light (Priority: P2)

Any library image can be regenerated from its record, the project repository does not become slow to clone because of the library, and the generating model, revision and container stay pinned so that images rendered weeks apart still match.

**Why this priority**: The constitution requires reproducibility and clean provenance, and a hundred images are the first time the imagery's weight matters for everyone who clones the project.

**Independent Test**: Measure how much the library adds to the repository and to a fresh clone. Regenerate three images from their records on the recorded container and check they are perceptually the same as the stored ones.

**Acceptance Scenarios**:

1. **Given** the full library, **When** the repository is measured, **Then** the library's published files add no more than 40 MB, and full-resolution sources are not stored in the repository.
2. **Given** any library image, **When** regenerated from its record on the recorded model revision and container image, **Then** the result is perceptually the same image.
3. **Given** a later rendering round, **When** it uses a different model revision or container, **Then** it is recorded as such, and a style check confirms the new images still fall within the house palette before they join the library.

---

### Edge Cases

- **A subject the generator renders badly** (drones, bogies, pantographs, lock gates): the subject gets more seeds and, if still unusable, a rewritten prompt. A theme's minimum count is never met by silently dropping a subject; the subject list changes and the change is recorded.
- **Two picks come out nearly the same** (same composition from neighbouring seeds, or two subjects collapsing to one scene): the near-duplicate check rejects the second; another seed or subject takes its place.
- **Readable text sneaks in** on signals, number plates, screens or signs: the text check rejects the image. No override.
- **A render drifts out of the palette** (orange sky, orange ground, the accent on a building): the style check rejects it. The accent belongs to the vehicle or machine only.
- **AI or IoT subject turns into a cliché** (glowing brain, floating network, robot): the subject prompt forbids it, and the owner marks such subjects "none"; the subject is rewritten towards concrete equipment before the next round.
- **A real place or livery becomes recognisable** (a famous bridge, a national railway's colours): prompts name no real places or operators; anything that still reads as one is not picked.
- **Model weights change upstream**: the recorded revision and the cached copy on the project's machine keep regeneration working. A new model starts a new series, never a silent swap within SIEBDRUCK.
- **A subject has no passing candidate at all**: it is absent from the sheet, listed separately with the reasons, and re-rendered or rewritten; it is never silently dropped.
- **The six existing images**: they stay unchanged, keep their placements and simply become library members.
- **Owner marks "none" for most of a theme**: the theme is re-rendered with new seeds or new subjects; rounds repeat until every theme meets its minimum. The feature is not done before that.
- **The pool is large but the site is small**: unplaced images never enter the built site, so the pool's size does not affect page weight or the deployment approval; only placements do.

## Requirements *(mandatory)*

### Functional Requirements

**Library content**

- **FR-001**: The library MUST hold at least 100 images in the SIEBDRUCK house style, the six images of feature 016 included.
- **FR-002**: Every library image MUST belong to exactly one theme of the coverage table below, and every theme MUST meet its minimum count. No theme MAY hold more than 20% of the library.
- **FR-003**: Images of AI and IoT MUST depict concrete, recognisable equipment or work in a mobility setting (sensors, antennas, cabinets, boards, cables, test rigs, screens showing abstract traces, people at work seen from behind). Abstract AI clichés (brains, glowing networks, robots, floating data) MUST NOT be used.
- **FR-004**: Every image MUST satisfy the content rules of feature 016: no identifiable people, no readable text, no real places, operators, brands or liveries, no photorealism.
- **FR-005**: No two library images MAY be near-duplicates. An automated similarity check MUST reject a candidate that is too close to an image already in the library.
- **FR-006**: An automated style check MUST reject an image whose colours leave the house palette beyond a recorded tolerance or whose accent colour is not concentrated on the main subject (for example an orange sky or ground). The tolerance is set so that every image the owner has approved passes and every series the owner has rejected fails; if no setting achieves both, the check is shown as a warning on the contact sheet, the decision stays with the owner, and the outcome is recorded with the feature's validation.
- **FR-007**: Every subject MUST be rendered with several seeds, and every candidate (accepted or rejected) MUST be listed with the outcome and the reason for rejection.

**Coverage table** (minimum counts; the subject list itself is a planning artifact)

| Theme | What it covers | Minimum |
|---|---|---|
| Rail | regional, high-speed, tram, metro, freight, shunting, mountain and maintenance railways | 10 |
| Public road transport | city and articulated buses, coaches, trolleybuses, minibuses, depots, charging | 6 |
| Private and commercial road | cars, charging, trucks, vans, motorcycles, agricultural and rural road use | 8 |
| Active and micro-mobility | walking, cycling, cargo bikes, e-scooters, bike parking, footbridges | 6 |
| Water | ferries, inland ships, ports, locks, pilot and harbour craft | 5 |
| Air | regional aircraft, aprons, towers, helicopters, cargo drones | 4 |
| Infrastructure | stations, bridges, tunnels, overhead lines, signals, junctions, charging hubs, parking, shelters, winter service, control rooms | 14 |
| Workshops and testing | maintenance pits, lifts, test rigs, test stands, benches | 8 |
| IoT and sensing | sensors on bearings, bridges, tracks and tyres; telematics, antennas, gateways, cameras, lidar | 10 |
| AI at work | edge boxes in vehicles and cabinets, racks in depots, workstations by windows, screens with abstract traces, inspection rigs, assistance views through windshields | 10 |

**Selection and picking**

- **FR-008**: Candidates that fail any automated check MUST be rejected with the check named and MUST NOT be shown to the owner. Every passing candidate of a subject MUST be shown.
- **FR-009**: The owner MUST be able to review a round on a contact sheet grouped by theme and subject, with every candidate numbered and shown large enough to judge, and MUST be able to state one pick per subject, or "none", by number. Subjects marked "none" and subjects without a passing candidate MUST be re-rendered and presented on a further sheet holding only those subjects.
- **FR-010**: Only the owner's picks MAY enter the library records. After the last pick the owner MUST NOT need to do anything except the existing deployment approval when a placement changes.

**Records, provenance and disclosure**

- **FR-011**: Every library image MUST be a complete feature 016 image record (model, revision, licence, prompt, negative prompt, seed, steps, guidance, size, date, hardware class, series, text alternative, focal point, derivatives with hashes, check results) and MUST pass the existing record, face, text and byte checks.
- **FR-012**: Every library image MUST additionally record its theme and its subject, and MAY record zero or more placements.
- **FR-013**: Every library image MUST be published under CC0 and MUST carry the AI-generated marker in its file metadata. The compliance notices MUST cover every library image; the credits page and the footer wording MUST cover every placed one, as they cover the six existing images.
- **FR-014**: Every library image MUST be reproducible from its record on the recorded hardware class, model revision and container image, in the sense of feature 016 (perceptually the same; bit-identity reported, not required).
- **FR-015**: The library MUST NOT store full-resolution sources in the project repository. The record MUST keep the source's hash so a regenerated source can be verified.
- **FR-016**: The library's published files MUST add no more than 40 MB to the repository in total.

**Site**

- **FR-017**: A library image recorded with a placement MUST be used on that page exactly as feature 016 images are, including the motif-on-plate composition on model pages, and MUST be listed on the credits page.
- **FR-018**: A library image without a placement MUST NOT be part of the built site: none of its files is copied, it has no credit, and the build MUST NOT warn about it.
- **FR-019**: The owner MUST be able to see the whole pool as one overview, grouped by theme, with each image small and its theme, subject and id, without building or deploying the site.
- **FR-020**: Placing, moving or removing a placement MUST be one change to the records and MUST need no rendering.
- **FR-021**: All existing site checks (accessibility, privacy, no-branding, depth, roadmap, preview-card, image and motif checks) MUST keep passing. Quickstart, format, roadmap and error pages MUST NOT gain images. The site MUST NOT gain a gallery or library page.
- **FR-022**: The pages of the site MUST NOT change because of this feature except where the owner records a new placement.

**Documentation**

- **FR-023**: The visual identity documentation MUST describe the library: its themes, how a subject is added, how a rendering round and approval work, and how an image is placed.

### Key Entities

- **Library image**: a feature 016 image record extended with a theme and a subject; placements optional. It is the unit the pool overview, the contact sheets, the site and the credits page work with.
- **Theme**: one of the ten coverage groups above, with its minimum count. Every library image has exactly one.
- **Subject**: one scene description in the series file under a theme; the thing that gets rendered with several seeds. A subject yields at most one library image.
- **Rendering round**: one batch of candidates for a set of subjects, with the pinned model revision and container, and the outcome (rejected with reason, shown on the sheet, picked) of every candidate.
- **Contact sheet**: the review the owner uses to pick one candidate per subject, or "none", from the passing candidates of a round; grouped by theme and subject, every candidate numbered.
- **Pool overview**: a locally generated view of every library image with theme, subject and id, grouped by theme; the owner's tool for finding an image to place.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The library holds at least 100 images; all ten themes meet their minimum and none exceeds 20%.
- **SC-002**: 100% of library images pass the record, face, text, byte, near-duplicate and style checks; every rejection in the rendering rounds is listed with its reason.
- **SC-003**: In a ten-image blind test, at least four of five people say the images come from one source or series, and at least four of five identify the mobility subject of each image correctly.
- **SC-004**: The owner never sees a candidate that failed an automated check, states every pick by number, and does nothing after the last pick except the existing deployment approval when a placement changes.
- **SC-005**: The library's published files add no more than 40 MB to the repository; a fresh clone is at most 25% slower than before the feature on the same connection.
- **SC-006**: Three images chosen at random can be regenerated from their records and are perceptually the same as the stored files.
- **SC-007**: The built site contains no file of an unplaced library image, and all existing site checks pass in light and dark mode at phone and desktop width.
- **SC-008**: Giving a model page a library image takes one record change and no rendering, and the fitting image is found in the pool overview within a minute.

## Assumptions

- The generating setup of feature 016 stays: open-weights model under Apache-2.0 on the project's DGX Spark in the pinned container, drafts with the fast model, finals with the large one. At the measured rate of about three minutes per final render and several seeds per subject, the rendering takes a few machine-days; it runs unattended.
- "About 100" means at least 100 and not markedly more; the plan may add a small reserve of subjects so that "none" picks do not push the library under the minimum.
- Theme minimums sum to 81; the remaining images go where the owner's picks are strongest, within the 20% cap.
- The style check is an automated palette and accent-location measurement with a tolerance set from the six approved 016 images; it does not judge beauty. Physical plausibility stays unautomated, as in 016, and is what the owner's pick is for.
- The near-duplicate check uses the perceptual comparison already used for 016's reproducibility check, with a threshold set so that neighbouring seeds of one subject count as duplicates and different subjects do not. On the sheet, near-duplicate seeds of one subject are shown once.
- Several seeds per subject means about four finals per subject; with roughly 110 subjects that is a few hundred renders, which the owner reviews on contact sheets over one or more sittings. The owner accepted this effort on 2026-10-14.
- Full-resolution sources stay on the project's machine and are regenerable; only the published derivatives live in the repository. If repository weight still exceeds the budget, the plan may reduce the number of derivative sizes for unplaced images.
- The pool overview and the contact sheets are local artifacts (a generated page opened in a browser, or a sheet image); they are not deployed and need no accounts or scripts.
- A separate publication of the library (a gallery page, a dataset release) was considered and declined by the owner on 2026-10-14; the pool is for the zoo's own use. Video, animation, photography, new house styles, the Hugging Face organisation card and new motifs are out of scope.
- Depends on feature 016 (records, checks, series, credits page, compliance notices) and on features 008, 012, 014 and 015 as 016 does.
