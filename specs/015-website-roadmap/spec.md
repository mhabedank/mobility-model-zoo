# Feature Specification: Roadmap and upcoming models on the zoo website

**Feature Branch**: `claude/015-website-roadmap`

**Created**: 2026-10-12

**Status**: Draft

**Input**: User description: "Alle diese Modelle bringen Sie bitte als kleine Karten und in Progress auf unsere Webseite. Darüber hinaus erweitere die Webseite um eine Roadmap, wo wir grob zeigen, was wir im nächsten Quartal, Halbjahr, Halbjahr releasen wollen. Ich überlege auch, ob wir da Updates von den aktuell schon vorhandenen Modellen, also die, die wir schon veröffentlicht haben, bringen wollen, auch die mit rein. Das soll natürlich schön übersichtlich sein und jetzt nicht total vollen Kram. Visuell appealing bitte. Und du musst natürlich vorher auch nochmal priorisieren, was auch mit den Sachen passiert, die wir da schon stehen haben, in welcher Reihenfolge das am meisten Sinn macht."

"All these models" are the model ideas of the research of 2026-10-11 ([model-ideas-research.md](model-ideas-research.md)): transport mode from smartphone motion sensors, battery cell health, road roughness from vehicle signals, bearing faults from vibration, and the roadmap candidates GNSS jamming/spoofing and CAN masquerade detection that the research confirmed.

**Owner decisions (2026-10-12)**:
- The priority order of the proposed roadmap is approved.
- The roadmap looks too slow for AI-assisted work. Delivery against the plan is measured, and the
  measured pace decides how the next quarters are filled (constitution 2.3.0, "Roadmap and
  Delivery Pace"). The first plan is filled from the pace observed so far (see Proposed roadmap).
- Updates of published models are on the roadmap, as a quieter kind of entry (FR-009).
- An entry is `in progress` only while the zoo is working on it; everything else is `planned`.

## Context

The website (feature 008, model pages in feature 014) shows published models as tiles and registered but unpublished models (`hum-fan`, `pace-cnn`, `picket-mlp`) as "in progress". It does not show what the zoo plans next, and model ideas that are not registered do not appear at all. Visitors (researchers, engineers at OEMs and suppliers, possible collaborators) cannot tell whether the zoo is active, where it is heading or whether a model they need is coming.

The owner wants two things: the upcoming models on the start page as small cards, and a roadmap that shows roughly what the zoo plans to release in the next quarter and in the two half-years after it. The roadmap has to be ordered by priority, and that order has to cover what is already in flight (registered models, open criteria of published models), not only the new ideas. The proposed order is in [Proposed roadmap](#proposed-roadmap-for-owner-approval) below.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See at a glance what the zoo releases next (Priority: P1)

A visitor (an engineer at a supplier, a researcher, a possible data partner) wants to know whether the zoo is alive and where it is going. They open the roadmap page and see, in three columns, what is planned for the next quarter, the following half-year and the half-year after. Each entry is a small card: name, topic, one sentence on what the model does, whether it is a new model or an update of a published one, and its stage. They understand in under a minute what comes next and when, roughly.

**Why this priority**: This is the core request. Without the roadmap, the cards on the start page have no time frame and the prioritisation is invisible.

**Independent Test**: Show the roadmap page to a person who has not seen the project. Within 60 seconds they name the next three planned releases, say for one of them whether it is a new model or an update, and say which period it is planned for.

**Acceptance Scenarios**:

1. **Given** the roadmap page, **When** a visitor opens it on a desktop screen, **Then** they see three horizons side by side, each labelled with its calendar period (for example "Q4 2026", "H1 2027", "H2 2027"), with the entries of each horizon in priority order.
2. **Given** the roadmap page, **When** a visitor opens it on a phone, **Then** the horizons are stacked in time order and every card is readable without horizontal scrolling.
3. **Given** any entry, **When** a visitor reads its card, **Then** they see the name (marked "working name" while the model is not registered), the topic, one sentence on what it does, the kind (new model, first release of a registered model, update of a published model), the stage (planned or in progress) and, where one exists, the one precondition it waits for (for example "data licence to be confirmed").
4. **Given** the roadmap page, **When** a visitor looks for how reliable it is, **Then** the page states the date of the roadmap and that it is a plan, not a commitment, in one short line at the top.
5. **Given** an entry that is an update of a published model, **When** the visitor selects it, **Then** they reach that model's page.

---

### User Story 2 - Upcoming models as small cards on the start page (Priority: P1)

A visitor on the start page sees the published models as today's tiles and, below them, every upcoming model as a small card: name, topic and the horizon it is planned for. The cards are compact enough that the start page stays calm: the published models remain the visual focus. A link leads to the full roadmap.

**Why this priority**: The owner asked for these cards explicitly. They show the breadth of the zoo where most visitors land.

**Independent Test**: Open the start page. Every model that is registered but not published, and every new model on the roadmap, appears as a small card with its horizon; no update entries appear there; the published tiles appear above the cards and are visually larger; one link leads to the roadmap.

**Acceptance Scenarios**:

1. **Given** the start page, **When** a visitor scrolls to the models, **Then** the published models come first as full tiles, followed by one row or grid of small cards for upcoming models, ordered by horizon and then by priority.
2. **Given** an upcoming model card, **When** a visitor reads it, **Then** it shows name, topic and horizon, and no version, no numbers and no performance claim; the sentence is on the roadmap entry it links to.
3. **Given** the upcoming cards, **When** a visitor selects one, **Then** they reach its entry on the roadmap page.
4. **Given** the start page's model heading, **When** it counts models, **Then** it counts published models and upcoming models separately and the numbers match the cards shown.

---

### User Story 3 - The owner keeps the roadmap current with one edit (Priority: P2)

The owner (or Claude on their behalf) changes the plan: moves an item to a later horizon, adds a new idea, marks one as in progress, or a model gets published. They edit one roadmap record in the repository; the site build updates the roadmap page, the start-page cards and the counts. When the roadmap is stale or contradicts the model registry, the build fails with a message that says what to fix.

**Why this priority**: A roadmap that rots is worse than none. Keeping it consistent with the registry automatically is what makes the feature trustworthy, but it matters only once the page exists.

**Independent Test**: Make each of these changes in a copy of the repository and build the site: move an entry between horizons (page and cards follow); publish a model that is on the roadmap as a new model (the entry leaves page and cards and counts as delivered); let a horizon end with an unfinished entry (the build fails and names the entry).

**Acceptance Scenarios**:

1. **Given** the roadmap record, **When** an entry is moved to another horizon and the site is rebuilt, **Then** the roadmap page and the start-page card show the new horizon and nothing else changes.
2. **Given** a model on the roadmap as a new model or first release, **When** its first version is published, **Then** the entry counts as delivered with that release's publication date and leaves page and cards, without a second edit.
3. **Given** a model that is registered but not published, **When** it has no roadmap entry, **Then** the build fails and names the model.
4. **Given** a horizon whose period has ended, **When** it still holds an entry, **Then** the build fails and names the entry, so the owner moves it forward, drops it or marks it done.
5. **Given** the roadmap date, **When** it is more than 100 days old, **Then** the build fails with a reminder to review the roadmap.
6. **Given** a horizon, **When** it holds more entries than the limit (FR-006), **Then** the build fails and names the horizon.

---

### User Story 4 - Know whether we are faster or slower than planned (Priority: P2)

At the end of a quarter, the owner wants to know how the zoo did against its plan: which entries were published early, on time or late against the horizon they were first planned in, which were moved or dropped and why, how many releases were published per quarter, and which share of the planned entries was delivered. From that, they fill the next horizons: more when the zoo is ahead, fewer or re-scoped entries when it is behind (constitution, "Roadmap and Delivery Pace").

**Why this priority**: The owner expects AI-assisted work to move faster than a classic plan assumes, and wants evidence instead of a guess. The report needs the roadmap record (US3) but nothing on the page.

**Independent Test**: In a copy of the repository, publish one roadmap entry before its horizon ends, move a second one to the next horizon and drop a third. Produce the pace report: it lists the first as early or on time with its publication date, the second as late with its first planned horizon, the slip and the reason of the move, and the third as dropped with its reason; the counts per quarter match the release records.

**Acceptance Scenarios**:

1. **Given** an entry that is moved to a later horizon, **When** the record is changed, **Then** its first planned horizon stays as it was and the move is recorded with date and reason.
2. **Given** an entry that is dropped, **When** the record is changed, **Then** the entry stays in the record with the date and reason of the drop and disappears from page and cards.
3. **Given** an entry whose release is published, **When** the site is built, **Then** it takes the publication date from the release record, leaves page and cards and counts as delivered in the quarter of that date.
4. **Given** the end of a quarter, **When** the owner produces the pace report, **Then** it shows per entry early, on time or late (slip in horizons and days to the end of the first planned horizon), moved and dropped entries with reasons, releases published per quarter and the share of planned entries delivered, and it is stored dated in the repository.
5. **Given** a roadmap whose horizons are rolled forward, **When** the build runs, **Then** it fails unless a pace review for the closed quarter exists.

---

### User Story 5 - Share the roadmap (Priority: P3)

The owner shares the roadmap link on LinkedIn or Mastodon. The preview shows the zoo identity and a share line for the roadmap, as for the other pages.

**Why this priority**: Visibility is a stated goal of the zoo, but the roadmap works without a dedicated preview.

**Independent Test**: Build the site and check that the roadmap page has its own preview image that passes the existing preview-image checks.

**Acceptance Scenarios**:

1. **Given** the built site, **When** the roadmap page's metadata is read, **Then** it names a preview image made for the roadmap, with a share line of at most 90 characters and no free-standing numbers except the dates of the horizons.

---

### Edge Cases

- **Empty horizon**: a horizon without entries shows one quiet line ("Nothing planned yet") instead of an empty column, so the layout does not break.
- **Model renamed before registration**: working names may change until the model is registered; the card shows "working name". Once a model is registered, its roadmap entry uses the registered name, and names never change after first publication (constitution, Project Scope).
- **Item dropped**: a dropped entry stays in the record with date and reason (constitution, "Roadmap and Delivery Pace") and disappears from page and cards. The page does not show dropped items.
- **Item moved**: a moved entry keeps its first planned horizon; it counts as late in the pace report even if it is published on time for its new horizon.
- **Published entry**: when a roadmap entry's release is published, the entry is delivered with the release's publication date: automatically for a first release or new model, through the one-line `delivered by` reference for an update. A delivered entry leaves page and cards.
- **Several releases for one entry**: an entry is delivered with its first published release; later patch releases do not count again.
- **Work published that was never on the roadmap**: it is not an error; the pace report lists it as unplanned delivery, so the plan can learn from it.
- **Item blocked**: an entry waiting for a precondition (a licence check, a privacy review) stays in its horizon and shows the precondition; it is not called "in progress" until work on the model itself has started.
- **Non-commercial or share-alike model**: an upcoming model whose planned training data makes it non-commercial or share-alike shows that label on its card, as published models do (constitution IX). If the usage class is not known yet, the card shows nothing about it rather than a guess.
- **No JavaScript**: roadmap and cards are complete without scripts.
- **Long names or sentences**: the record limits the sentence length (FR-004); the build fails on a longer one instead of truncating it on the page.

## Requirements *(mandatory)*

### Functional Requirements

**Roadmap content**

- **FR-001**: The roadmap MUST live in one versioned, hand-maintained record in the repository, next to the model registry. Every roadmap fact on the site (entries, order, horizons, date) MUST come from that record; no roadmap text is written into pages or templates.
- **FR-002**: The record MUST hold a roadmap date and exactly three horizons in time order: the next quarter, the half-year after it and the half-year after that. Each horizon has a calendar label and an end date.
- **FR-003**: Each entry MUST state: name (registered name, or a working name marked as such), topic (one of the zoo's topics), kind (`new model`, `first release` of a registered model, or `update` of a published model), stage (`planned` or `in progress`), one sentence on what the model does or what the update changes, and optionally one precondition it waits for. An update entry MUST name the published model it updates. For the pace review, each entry MUST also record the horizon it was first planned in (never changed afterwards), every move with date, new horizon and reason, a drop with date and reason, and, for an update once released, the release that delivers it. The delivery date is read from that release record; a first release or new model is delivered by the first published version of its model (research R3).
- **FR-004**: The sentence MUST be at most 20 words and the precondition at most 8 words. Neither may contain numbers, metric placeholders or performance claims, in line with the rule for hand-written site text (check F2 of feature 008).
- **FR-005**: The order of entries inside a horizon MUST be their priority order, and the site MUST show them in that order.
- **FR-006**: A horizon MUST hold at most 6 entries, so the roadmap stays an overview.
- **FR-007**: An entry MAY carry a usage-class label (non-commercial, share-alike) only when it is already known from the planned training data's declaration. A label MUST NOT be guessed.

**Roadmap page**

- **FR-008**: The site MUST have a roadmap page that shows the three horizons as columns on wide screens and stacked in time order on narrow screens, with each entry as a small card (FR-003 fields).
- **FR-009**: Kind and stage MUST be distinguishable by text and shape, not by colour alone. Updates of published models MUST be visually quieter than new models.
- **FR-010**: The page MUST state the roadmap date and that the roadmap is a plan, not a commitment, in one line above the horizons.
- **FR-011**: An update entry MUST link to the published model's page. A new-model or first-release entry has no link to a model page (there is none until it is published).
- **FR-012**: The roadmap page MUST be reachable from the navigation of every page.
- **FR-013**: The roadmap page MUST have a preview image for shared links, made by the existing preview-image pipeline, with its own share line.

**Start page**

- **FR-014**: The start page MUST show, after the published model tiles, one small card per upcoming model: every entry of kind `new model` or `first release`. Update entries MUST NOT appear there.
- **FR-015**: Each small card MUST show name, topic and the horizon label (the sentence stays on the roadmap page, to keep the cards small), and link to the entry on the roadmap page. It MUST NOT show a version, numbers or performance claims (feature 008, FR-003).
- **FR-016**: The upcoming cards MUST take less visual weight than the published tiles (smaller, quieter), and the start page MUST link to the roadmap page from the models section.
- **FR-017**: The models heading MUST count published and upcoming models separately; the counts MUST equal the tiles and cards shown.

**Consistency with the registry**

- **FR-018**: The build MUST fail when a registered, unpublished model has no roadmap entry; when an `update` entry names a model that is not published; when a horizon that has ended still holds an entry that is neither delivered, moved nor dropped; when an entry's first planned horizon differs from the one it had when it was added; when an update entry names a delivering release that is not published; when the horizons are rolled forward without a pace review of the closed quarter; when the roadmap date is more than 100 days old; or when a horizon exceeds the limit of FR-006. Each failure MUST name the entry or model and what to change.
- **FR-019**: Registered, unpublished models MUST keep appearing as upcoming (feature 008, FR-003); after this feature, they appear through their roadmap entry, so there is one list of upcoming models, not two.

**Quality bar shared with the rest of the site**

- **FR-020**: Roadmap page and cards MUST pass every existing site check that applies to them: privacy (no third-party resources, no cookies), accessibility (WCAG 2.1 AA in light and dark mode, complete without scripts, keyboard), legal links, internal links and anchors, page weight and load time.
- **FR-021**: Roadmap page and cards MUST use the zoo identity (design tokens, components, fonts) without new external assets. They MAY reuse existing model motifs for registered models; new models do not need a motif.
- **FR-022**: The site text MUST be in English, like the rest of the site.

**Initial content**

- **FR-023**: The first published roadmap MUST be the proposed roadmap below, after the owner has approved or changed it. Dataset licences and privacy reviews named as preconditions MUST NOT be presented as resolved on the site.

**Pace review**

- **FR-024**: The owner MUST be able to produce a pace report from the roadmap record and the release records with one command. It reports, for a closed quarter: per entry delivered early, on time or late against its first planned horizon (slip in horizons and days), moved entries with their reasons, dropped entries with their reasons, unplanned deliveries (published releases without a roadmap entry), releases published per quarter, and the share of the entries first planned for that quarter that were delivered in it.
- **FR-025**: Each pace review MUST be stored, dated, in the repository, and MUST state how the next horizons were filled from the measured pace (constitution, gate before rolling the roadmap forward).
- **FR-026**: Delivered and dropped entries MUST stay in the record and MUST NOT appear on the roadmap page or as cards. The pace report is for the owner; it is not published on the website in this feature.

### Key Entities

- **Roadmap**: the roadmap date and three horizons in time order.
- **Horizon**: calendar label (for example "Q4 2026"), end date, ordered list of at most six entries.
- **Roadmap entry**: name and whether it is a working name, first planned horizon, topic, kind (`new model`, `first release`, `update`), stage (`planned`, `in progress`), sentence, optional precondition, optional usage-class label, and for updates the published model it updates.
- **Move**: date, new horizon and reason; an entry may have several. **Drop**: date and reason.
- **Delivery**: the publication date of the entry's first published release, taken from its release record.
- **Pace review**: dated report for a closed quarter (FR-024) and the note on how the next horizons were filled from it (FR-025).
- **Upcoming model card**: the start-page view of an entry of kind `new model` or `first release`, with its horizon label.
- Existing entities used: model (registry), release record (published or not), topic.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a test with at least three people who have not seen the project, each names the next three planned releases and the period of one of them within 60 seconds on the roadmap page.
- **SC-002**: On a 1440 × 900 desktop screen, all three horizons are visible side by side and the roadmap page needs at most two screen heights; on a 390-pixel-wide phone screen, no card needs horizontal scrolling.
- **SC-003**: On the start page, the upcoming cards take less than half the vertical space of the models section on a desktop screen, and the published tiles are above them.
- **SC-004**: 100% of registered, unpublished models appear on the roadmap and as start-page cards; a registered model without an entry, an update naming an unpublished release, an ended horizon with an open entry and a roadmap older than 100 days each fail the build (each tested with a deliberate fault).
- **SC-005**: Changing the plan (moving, adding, dropping an entry) takes one edit of one record; no page or template changes.
- **SC-006**: The roadmap page passes the accessibility, privacy, link and weight checks with zero violations in light and dark mode and loads its main content in under 2 seconds on a slow mobile connection, like the other pages.
- **SC-007**: The pace report for a quarter is produced with one command in under a minute, and its delivered, moved, dropped and unplanned entries and its counts agree 100% with the roadmap record and the release records (checked by hand on the first review).
- **SC-008**: The first pace review (end of Q4 2026) states whether the zoo delivered faster or slower than planned, and the horizons of 2027 are re-filled from it.

## Proposed roadmap (order approved 2026-10-12)

Order follows four rules: (1) finish what is in flight before starting new work; (2) close open criteria of published models where that moves them towards `released`; (3) new models that reuse a pipeline the zoo already has come before models that need a new pipeline; (4) models waiting for a licence or privacy check come after those that can start now. "Horizon" is the period in which the release is planned, not when work starts.

**Pace used to fill the horizons.** Since the constitution was ratified on 2026-09-25, the zoo published four releases of two models in about two and a half weeks (`scout-large` 0.1.0 to 0.1.2, `picket-forest` 0.2.0; sandbox releases not counted). Those releases ran on pipelines that existed or were built alongside; new models need new data declarations, and some need new pipelines or licence checks. The first plan therefore puts six entries into Q4 2026 (the most a horizon holds, FR-006) and fills H1 2027 completely; H2 2027 keeps room for ideas that the resource index or the pace review bring in. Compared with the first draft, `picket-mlp` moves from H1 2027 into Q4 2026 and `picket-forest` (shuffled-label control) from H2 into H1 2027; the priority order is unchanged. These are the first planned horizons for the pace review. The first review at the end of Q4 2026 shows whether this is still too slow and pulls 2027 entries forward if so.

### Q4 2026 (until 2026-12-31)

| # | Entry | Kind | Topic | Stage | Why here | Precondition |
|---|---|---|---|---|---|---|
| 1 | `picket-forest`: measured on a real ESP32 board | update | security | planned | Closes one of its two unmet criteria; the hardware-in-the-loop bench exists. | – |
| 2 | `scout-large`: reader test and clean-machine run | update | productdev | planned | Its two unmet criteria; meeting them makes it the zoo's first candidate for status `released`. | – |
| 3 | `pace-cnn` | first release | condition-monitoring | in progress | Registered, pipeline and data ready; only training on the frozen benchmark is missing. | – |
| 4 | `hum-fan` | first release | condition-monitoring | in progress | Same as `pace-cnn`; share-alike because of MIMII (CC BY-SA). | – |
| 5 | `hum-bearing` (working name): bearing faults from vibration, rail context | new model | condition-monitoring | planned | Lowest effort of the new ideas: reuses the `hum-fan` pipeline, data under CC BY 4.0. | – |
| 6 | `picket-mlp` | first release | security | planned | Registered; second CAN model gives `can-ids` a comparison with `picket-forest`. | – |

### H1 2027 (until 2027-06-30)

| # | Entry | Kind | Topic | Stage | Why here | Precondition |
|---|---|---|---|---|---|---|
| 1 | `mode-cnn` (working name): transport mode from smartphone motion | new model | condition-monitoring | planned | Reuses the `pace-cnn` pipeline; strong public interest; honest per-user evaluation is its edge. | Data licence to be confirmed |
| 2 | `cell-soh` (working name): battery cell health on a microcontroller | new model | condition-monitoring | planned | Strongest evidence of the research (open data, published microcontroller results); needs a new regression pipeline. | – |
| 3 | `gnss-guard` (working name): GNSS jamming and spoofing detection | new model | security | planned | Confirmed gap: no open model trained on real jamming data. | Data licence to be confirmed |
| 4 | `scout-large`: more languages | update | productdev | planned | Uses the multilingual resource index (feature 009); pilot languages Spanish, Polish, Japanese. | Resource index first version |
| 5 | `jtbd-cluster` (working name): first baseline | new model | productdev | planned | Completes the JTBD chain after extraction (feature 009). | – |
| 6 | `picket-forest`: features that pass the shuffled-label control | update | security | planned | Fixes the failed control of the pre-registered evaluation; needs new feature design, so after the first releases. | – |

`jtbd-cluster` is a task, not a registered model yet; its entry is a new model with a working name until the baseline model is registered.

### H2 2027 (until 2027-12-31)

| # | Entry | Kind | Topic | Stage | Why here | Precondition |
|---|---|---|---|---|---|---|
| 1 | `rough-road` (working name): road roughness from vehicle signals | new model | condition-monitoring | planned | Open data from electric cars with official road measurements; new signal pipeline. | Privacy review of GPS data |
| 2 | `v2x-guard` (working name): V2X misbehaviour detection | new model | security | planned | On the security roadmap since 2026-10-07; open data, no hardware needed. | Data access to be confirmed |
| 3 | `picket-signal` (working name): CAN masquerade detection on signal level | new model | security | planned | Closes the gap of timing-only detection; builds on `picket-*` and the ROAD data. | – |

### Not on the roadmap, and why

- **Clock-skew sender identification, driver profiling, EV charger anomalies**: no commercially usable data found yet (security roadmap of 2026-10-07; not confirmed by the research of 2026-10-11).
- **Language-model ideas beyond JTBD** (compliance assistant for UN R155/R156 and ISO 21434, accident reports, passenger feedback): the research found no verified evidence on data or demand. They return when the resource index (feature 009) shows usable data.
- **Road surface from the RSC dataset and transport mode from Collecty**: no licence for training.

## Constitution Check

- **III. Measure before optimizing, metric naming**: roadmap and cards carry no numbers and no performance claims (FR-004, FR-015); results appear only on model pages of published releases.
- **VI. Clean provenance, restrictions carry over**: an upcoming model shows a usage-class label only when its planned data declares it (FR-007); open licence questions stay visible as preconditions and are never presented as resolved (FR-023). Every new model still needs its dataset declaration before training.
- **IX. Reproducible, dated releases**: the roadmap is dated and called a plan, not a commitment (FR-010); it never implies a release status. Publishing stays with the release pipeline; the roadmap only follows it (FR-018).
- **Project scope & iterative delivery**: working names are marked as such and may change until registration; registered names never change (edge cases). Every new model on the roadmap still needs its own task document or spec that defines scope, reference, budgets and riskiest assumption before work starts.
- **Roadmap and delivery pace (2.3.0)**: every entry keeps its first planned horizon; moves and drops are recorded with date and reason, never silently (FR-003, FR-026); delivered means published through the release pipeline (FR-018); the pace review reports plan against actual and is required before the horizons roll forward (FR-018, FR-024, FR-025); the first plan is filled from the pace observed so far (Proposed roadmap).
- **Feature 008 rules**: one source per fact (FR-001), unpublished models without page or claims (FR-015), no third-party resources, accessibility and legal links (FR-020).

## Assumptions

- Horizons are calendar periods: the current quarter counts as "the next quarter" because it has most of its weeks ahead (as of 2026-10-12 that is Q4 2026), followed by H1 2027 and H2 2027. When a quarter ends, the owner runs the pace review and rolls the horizons forward; the stale check (FR-018) enforces both.
- Updates do not appear as start-page cards (FR-014), so the start page stays focused on models; they are on the roadmap page (owner decision 2026-10-12).
- `in progress` means work on the entry has started (for a model: registered and its pipeline running); the start-page section is called "Coming next", which covers `planned` and `in progress` (owner decision 2026-10-12).
- The working names follow the zoo's naming scheme (`<name>-<variant>`) and reuse family names where a model reuses a pipeline (`hum-`, `picket-`); they are proposals.
- The roadmap is public. It contains no dates finer than a horizon, no partner names and no internal costs.
- The stale-roadmap limit of 100 days is a little longer than a quarter, so one review per quarter keeps the build green.
- The pace report is internal for now (FR-026). Publishing delivery pace on the website (for example "delivered last quarter") is possible later, but would add a second kind of content to a page meant to stay calm.
- The research findings that the proposed roadmap relies on are kept with this feature in [model-ideas-research.md](model-ideas-research.md); licences named there are checked again in each model's own dataset declaration before training.
