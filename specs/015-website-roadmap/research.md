# Research: Roadmap and upcoming models on the zoo website

Phase 0 of [plan.md](plan.md). Each decision names what was chosen, why, and what was rejected. The research on the model ideas themselves is in [model-ideas-research.md](model-ideas-research.md).

## R1 One record: `zoo/roadmap/roadmap.yaml`

- **Decision**: The roadmap is one YAML file, `zoo/roadmap/roadmap.yaml`, validated against a JSON schema shipped with the site package (`site/schemas/roadmap.schema.json`). Pace reviews live next to it in `zoo/roadmap/reviews/<quarter>.md`.
- **Rationale**: Matches how the zoo keeps every other source of website facts (`zoo/site.yaml`, `zoo/topics.yaml`, `zoo/models/<name>/…`): versioned, reviewed in pull requests, validated by schema (FR-001). A folder keeps record and reviews together.
- **Alternatives**: Roadmap fields inside each `model.yaml` (rejected: working-name models have no `model.yaml`, and update entries are not models); GitHub issues or a project board (rejected: not versioned with the code, not readable by the offline build, and the constitution wants the record in the repository).

## R2 Horizons as quarter spans

- **Decision**: A horizon is a span of calendar quarters with an id: one quarter `2026-Q4`, or two consecutive quarters `2027-Q1..Q2` (same year) or `2027-Q4..2028-Q1` (across a year). The record lists exactly three horizon ids. Validation: the first spans one quarter, the second and third two quarters each, and they follow each other without gaps. Label and end date are derived: `Q4 2026`; `H1 2027` for `Q1..Q2`, `H2 2027` for `Q3..Q4`, otherwise `Q2–Q3 2027` or `Q4 2027 – Q1 2028`.
- **Rationale**: The spec asks for "the next quarter and the two half-years after it" (FR-002). After Q4 2026 rolls over, the half-years are Q2–Q3 2027 and Q4 2027 – Q1 2028, which calendar halves cannot express. Deriving label and end from the id removes two hand-kept fields that could disagree.
- **Alternatives**: Calendar half-years only (rejected: breaks at the first roll-over); free label plus start and end dates (rejected: three fields that can contradict each other; the pace review needs exact boundaries).

## R3 Delivery is read from the release records

- **Decision**: An entry is delivered when the release that delivers it is published, and its delivery date is the UTC date of `published.published_at` in that release record. For `first-release` and `new-model` entries, the delivering release is the first published version of the model named in `model` (set once the model is registered). For `update` entries, the entry names it: `delivered_by: {model, version}`. Nothing else marks an entry delivered.
- **Rationale**: Constitution 2.3.0 says an entry counts as delivered only when its release is published, and feature 008 keeps one source per fact. Reading the date from the record means a publish needs no second edit for first releases, and an update needs one line that the build verifies.
- **Spec refinement**: FR-018 said the build fails when a `new model` or `first release` entry names a published model. With this decision such an entry is simply delivered; it leaves page and cards and counts in the pace report. FR-018 and FR-003 are updated accordingly (the failure that remains: `delivered_by` naming a version that is not published).
- **Alternatives**: A hand-written `delivered: <date>` field (rejected: a second copy of the publication date, open to mistakes and to re-dating); deleting the entry on delivery (rejected: the pace review needs it).

## R4 The first planned horizon cannot change

- **Decision**: Each entry has `planned` (the horizon it was first planned in) and `horizon` (where it is now). A move appends `{date, to, reason}` to `moves` and changes `horizon`; the last move's `to` must equal `horizon`. Check RM5 reads the git history of `roadmap.yaml`: for every entry, `planned` equals the value it had in the first commit that contained the entry's id. In a shallow clone the check sees only the current commit and passes; the site workflow checks out the full history (`fetch-depth: 0`), so the deploy is protected.
- **Rationale**: Constitution 2.3.0 forbids re-dating. A rule in the schema alone cannot see past values; git history can, without a second file.
- **Alternatives**: A separate append-only log file (rejected: two records to keep consistent); trusting review (rejected: the owner asked for measurement that does not depend on discipline).

## R5 Staleness, roll-over and review gate

- **Decision**: The build fails (check RM6) when an open entry (not delivered, not dropped) sits in a horizon whose end has passed; when `as_of` is more than 100 days old; and (check RM7) when a quarter between the record's `since` quarter and the start of the first horizon has no review file `zoo/roadmap/reviews/<quarter>.md` with a filled re-planning section. The build prints a warning, not a failure, in the last 14 days of the first horizon. "Today" is the UTC date, or `ZOO_TODAY` when set (tests, rehearsals).
- **Rationale**: FR-018 and the constitution's gate before rolling the roadmap forward. A review requirement expressed as "every closed quarter since the roadmap began has a review" needs no memory of the previous record, so it works on any checkout.
- **Risk**: After a quarter ends, the site cannot deploy until the roadmap is rolled and reviewed, including a deploy triggered by a model release. That is the forcing function the owner asked for; the 14-day warning and the stale date in the build log give notice. A release itself is never blocked: `zoo check` and the release pipeline do not read the roadmap.
- **Alternatives**: Failing only `zoo site check` (rejected: the deploy job runs build then check, same effect, later); warnings only (rejected: the owner wants the plan kept honest).

## R6 Pace report: definitions

- **Decision**: `zoo roadmap pace <quarter>` computes from the record and the release records:
  - **Delivered in the quarter**: entries whose delivery date falls in it, each classed against its first planned horizon: *early* (before the horizon starts), *on time* (within it), *late* (after its end, with slip in days from the end and in started quarters).
  - **Due and missed**: entries whose first planned horizon ended within or before the quarter and that are not delivered by its end, with current horizon and move reasons.
  - **Moved** and **dropped** in the quarter, with reasons.
  - **Unplanned**: non-sandbox releases published in the quarter that deliver no entry (patches of already delivered entries included).
  - **Counts**: releases published in the quarter (non-sandbox, all versions), entries delivered, and the *delivery rate*: delivered ÷ due (entries whose first planned horizon ends in the quarter), shown as a fraction, not only as a percentage.
  - **Trend**: the same counts for every earlier reviewed quarter, so the review can compare pace over time.
  With `--write`, it writes `zoo/roadmap/reviews/<quarter>.md`: the generated tables plus a heading "Re-planning" that the owner fills in (FR-025). Without `--write`, it prints the report.
- **Rationale**: These are the numbers the constitution names (early, on time, late with slip; moved; dropped; releases per quarter; share of planned entries delivered), defined so that two people get the same result from the same files.
- **Alternatives**: Story points or effort estimates (rejected: not recorded anywhere; the owner asked for plan against actual, not effort); burndown charts (rejected for this feature: the report is for the owner, a table suffices; FR-026 keeps it off the website).

## R7 Start page: one list of upcoming models

- **Decision**: The models section shows published and deprecated models as today's tiles. Below them, under the heading "Coming next", one small card per open roadmap entry of kind `new-model` or `first-release`, ordered by horizon and then by position in the record. The tiles of registered, unpublished models disappear; those models appear only as cards (FR-019). The heading counts "N published · M coming next". A link "See the roadmap" closes the section.
- **Rationale**: Two lists of upcoming models (tiles and cards) would say the same thing twice and could disagree. Check RM2 guarantees every registered, unpublished model has an entry, so no model vanishes.
- **Alternatives**: Keep the in-progress tiles and add cards only for working names (rejected: inconsistent visual weight for the same kind of thing).

## R8 Roadmap page design

- **Decision**:
  - **Layout**: a horizontal timeline band across the top with one marker per horizon and a "now" marker inside the first; below it three columns (CSS grid, `repeat(3, 1fr)` from 960 px, one column below), each headed by the horizon label and its months.
  - **Cards**: compact (name, topic eyebrow, sentence, chips, optional precondition line "Waits for: …"). New models and first releases sit on the surface colour with a mint accent bar; updates have no fill and a dashed outline, so they are quieter (FR-009) and are labelled "Update of `<model>`" in text.
  - **Stage chips**: hollow dot for `planned`, half-filled dot for `in progress`, with the word in both cases, so shape and text carry the meaning, not colour (FR-009).
  - **Motifs**: registered models with a motif show it at 28 px; working names show none.
  - **Top line**: "A plan, not a commitment. As of <date>." (FR-010).
  - **Empty horizon**: "Nothing planned yet."
  - **No JavaScript** is needed for any of it.
- **Rationale**: Columns in time order are the fastest way to answer "what comes when" (SC-001, SC-002); the timeline band gives the page a visual anchor without adding text. Reusing tokens, chips and the card component keeps the identity (FR-021); the new CSS is about 60 lines in `site.css`.
- **Alternatives**: A Gantt-style chart (rejected: implies dates finer than a horizon, which the spec excludes, and needs a text alternative for every bar); a single list grouped by horizon (rejected: does not show the three periods at a glance on desktop).

## R9 Text rules for entries

- **Decision**: Validation of each entry (check RM3): `text` at most 20 words, `precondition` at most 8; neither contains a free-standing number (same regex as F2, `facts.NUMBER`), a `{metric:…}` placeholder, or a release-status word (`budgets.STATUS_WORDS`). The usage label on a card is derived, not written: for an entry with a registered `model`, the model's `usage_class` (`commercial-share-alike` shows "share-alike", `non-commercial` shows "non-commercial"); for a working name, no label (FR-007).
- **Rationale**: Reuses the site's existing rules for hand-written text, so a roadmap card cannot claim more than a model page could. Deriving the label from the registration keeps FR-007's "only when known from the declaration" true by construction.
- **Alternatives**: A free `usage` field on the entry (rejected: a guess could slip in).

## R10 Preview image for the roadmap page

- **Decision**: `og.cards` adds a card for `roadmap/` with eyebrow "Roadmap", title "What comes next", and the share line from `zoo/site.yaml` → `roadmap.share_line` (new optional block, same rules as the other share lines, check B6). The horizon labels are not drawn on the image, so it carries no numbers.
- **Rationale**: Reuses feature 012's pipeline and checks O1–O5 unchanged (FR-013).
- **Alternatives**: Drawing the three horizons on the image (rejected: numbers on an image, which B6 forbids for share lines, and an image that goes stale every quarter).

## R11 Where the code lives, and the CLI

- **Decision**:
  - **Code**: new modules `site/roadmap.py` (load, validate, derive horizons, delivery and the page context) and `site/pace.py` (the report).
  - **CLI**: a new sub-app `zoo roadmap` with `check` (validation without building the site) and `pace`, registered in `release/cli.py` like `zoo site`.
  - **Build integration**: `zoo site build` calls the same validation.
- **Rationale**: The roadmap is website content plus a planning tool. Putting it in the site package reuses schema loading, text rules and templates. Constitution "Tasks and Releases": shared code goes into a common module only when needed; here it is needed by build and CLI.
- **Alternatives**: A separate package `mobility_model_zoo.roadmap` (rejected: it would import half of `site` anyway).

## R12 Tests

- **Decision**:
  - **Fixture**: the website test fixture registry gets a small roadmap (three horizons, one entry per kind, one registered unpublished model, one working name).
  - **Tests** in `tests/website/test_roadmap_*.py`, with `ZOO_TODAY` pinned:
    - page and card rendering;
    - each failure of checks RM1–RM7 with a deliberate fault (SC-004);
    - the pace report on a constructed history: a temporary git repository with two commits, so the first-planned check is exercised;
    - start-page counts.
  - **Browser tests**: the existing browser checks (A1–A5, S2) pick up the new page automatically, because they iterate over all pages.
- **Rationale**: Same pattern as features 008, 012 and 014; offline and deterministic.
