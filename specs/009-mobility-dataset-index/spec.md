# Feature Specification: Mobility resource index (multilingual, multimodal)

**Feature Branch**: `claude/mobility-dataset-index-b873c3`

**Created**: 2026-10-10

**Status**: Draft

**Owner decisions (2026-10-10)**:
- Target languages: the 24 EU official languages plus ten major world languages (FR-023).
- Visibility: internal for now, built so it can be published later as an open catalogue (FR-032).
- Size of the first version: at least 2,000 entries in at least 30 languages besides German and
  English (SC-002).

**Input**: User description: "Wir brauchen einen Datensatz index. Erstmal für Mobilitätsbezogene texte, videos, podcasts, papers etc. Ziel: besseres training für Scout und nachfolgende modelle. Momtan haben wir nur deutsche und englishe texte einbezogen, wir sollten explizit international gehen. zur nut muss dann halt der encoder angepasst werden. Ziel ist es nicht die daten runterzuladen, sondern eine übersicht über die ressourcen zu bekommen. diese müssen mindestens sprache (ggf land). quelle, art der quelle, typ der quelle, lizenz enthalten. darüber hinaus denke nach was der index noch braucht. es sollte dann im nachgang möglich sein, diese quellen runterzuladen. explizit können das ach nicht spracheliche quellen sein wie videos, bilder und audiodateien - auch grafiken und charts sind gut. auch tatsächlich quantitative daten (datenbanken, buckets, exceltabelle, json, xml etc pp) sind auch gut."

## Context

scout-large was trained on 1,100 chunks from 87 sources: 28% German, 72% English, almost all of
it parliamentary transcripts, interviews and a few papers. Its base model reads about a hundred
languages, but the training data covers two. Later models of the zoo (other productdev tasks,
security, condition monitoring, models that read audio, images or tables) need material the
project has never looked for.

Today a source becomes known to the project only when it is fetched: the source register of a
topic (feature 006) records sources that already have a raw snapshot. There is no place to record
what exists, in which language, under which licence and how it could be obtained, before anything
is downloaded. Without that overview the project keeps fetching what is nearest (German and English
text) and cannot see its own gaps.

This feature builds that overview: an index of mobility-related resources in any language and any
modality. It records metadata only. Downloading, transcribing, training and changing the encoder are
later features that read from the index.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Record a resource with the facts that decide whether it can be used (Priority: P1)

The owner or a discovery agent finds a mobility resource, for example the video archive of a
Spanish regional parliament's transport committee, a Japanese ministry's open data portal on rail
ridership, or a Brazilian podcast on urban cycling. They add it to the index with its language(s),
country or region, publisher and landing page, kind of source, type of resource and licence. The
index accepts the entry only when every mandatory fact is present and uses the agreed vocabulary;
a fact that cannot be found is recorded explicitly as unknown, never left empty.

**Why this priority**: Without a consistent record per resource nothing else (search, coverage,
later download) works. This alone already replaces scattered research notes.

**Independent Test**: Add ten resources of different modalities and languages; the index accepts
the complete ones, rejects the ones with missing or invalid mandatory facts and names the missing
fact.

**Acceptance Scenarios**:

1. **Given** an empty index, **When** a resource is added with language, country, source, kind,
   type and licence, **Then** it is stored with a stable identifier and status "candidate".
2. **Given** a resource without a licence statement, **When** it is added with licence "unknown",
   **Then** it is accepted, and it is marked as not eligible for download.
3. **Given** a resource whose kind of source is not in the vocabulary, **When** it is added,
   **Then** it is rejected with a message that names the field and the allowed values.
4. **Given** a chart collection without any text, **When** it is added with language "not
   applicable", **Then** it is accepted; "not applicable" and "unknown" stay distinguishable.

---

### User Story 2 - Answer "what do we have?" across languages, countries and modalities (Priority: P1)

Before planning the next model, the owner asks questions such as "which training-usable sources in
Spanish, Portuguese or Arabic exist about public transport?" or "which video sources come with
subtitles?" and gets a filtered list. A coverage report shows counts and estimated volume per
language, country, modality, kind of source and permitted use, and names the gaps: languages or
modalities with no training-usable resource.

**Why this priority**: This is the overview the owner asked for. It turns "go international" into
a list of concrete gaps.

**Independent Test**: With a seeded index of at least 50 entries, run five filter questions and
the coverage report; each answer matches a manual count of the seeded entries.

**Acceptance Scenarios**:

1. **Given** an index with entries in several languages, **When** the owner filters by language,
   modality and permitted use, **Then** only matching entries are listed with their mandatory
   facts.
2. **Given** an index, **When** the coverage report is produced, **Then** it lists every language
   and modality in the index with entry count, estimated volume and the share that is
   training-usable, and lists target languages with no training-usable entry as gaps.

---

### User Story 3 - Grow the index internationally through assisted discovery (Priority: P2)

The owner starts a discovery run for a scope (for example "Polish, rail and public transport, all
modalities"). Agents search catalogues, portals, registries and literature and propose candidate
entries with the evidence they found (landing page, licence page). Automated checks run on every
candidate: mandatory facts, vocabulary, link reachable, licence evidence, machine-readable opt-out
signals, duplicates. Candidates that pass enter the index; the rest are listed with reasons. The
owner is not asked to review each entry; only conflicts the rules cannot decide are flagged.

**Why this priority**: Hand entry does not scale to dozens of languages. Discovery with automated
checks is how the index becomes international, but the index (US1, US2) must exist first.

**Independent Test**: Run discovery for one non-German, non-English language and one subdomain;
the run produces a report of searched scope, proposed, accepted and rejected candidates, and every
accepted entry passes the automated checks.

**Acceptance Scenarios**:

1. **Given** a discovery scope, **When** the run finishes, **Then** a run record states scope,
   date, method, agent and model identifiers, cost, and the number of candidates found, accepted
   and rejected, including scopes that yielded nothing.
2. **Given** a candidate that duplicates an existing entry (same normalised URL, same persistent
   identifier, or same title and publisher), **When** it is checked, **Then** it is not added as a
   new entry and the existing entry is referenced.
3. **Given** a candidate whose site signals a text-and-data-mining opt-out, **When** it is checked,
   **Then** it is stored with the signal and is not eligible for download for training.

---

### User Story 4 - Hand a selection to a later download step (Priority: P2)

The owner selects entries (for example "all cleared Spanish and Italian parliamentary video with
subtitles") and exports a fetch list. The list contains everything a later download step needs to
fetch the resource and create its source record without new research: access method, endpoint,
format, estimated size, authentication or cost, licence, attribution, permitted use, redistribution
and personal-data expectation. Entries that are not cleared for download are refused with the
reason. When a resource is fetched later, its index entry links to the resulting source record.

**Why this priority**: The owner wants to download later. The index must be built so that this
works, but the download itself is a separate feature.

**Independent Test**: Export a fetch list for a selection containing cleared and uncleared entries;
the list contains only cleared entries with all required fields, and the refusals name a reason.

**Acceptance Scenarios**:

1. **Given** a selection, **When** a fetch list is exported, **Then** only entries with status
   "cleared for fetch" appear, each with all access and rights fields filled.
2. **Given** an entry that was fetched by a later feature, **When** its source record is created,
   **Then** the index entry shows status "fetched" and links to that record.

---

### User Story 5 - Keep the index current and honour objections (Priority: P3)

Links break, licences change and sites add opt-out signals. A periodic re-check verifies links,
licence pages and opt-out signals of cleared entries. A change moves the entry back to "verified"
and records what changed. A rights holder or data subject who objects through the existing
objection channel gets the entry excluded from every future fetch list.

**Why this priority**: A stale index produces unlawful or broken downloads, but only once
downloads happen.

**Independent Test**: Change the licence evidence of a test entry and run the re-check; the entry
loses its cleared status and the change is recorded with a date.

**Acceptance Scenarios**:

1. **Given** a cleared entry whose landing page no longer resolves, **When** the re-check runs,
   **Then** the entry is flagged and is not exported in fetch lists until verified again.
2. **Given** an objection for an entry, **When** it is recorded, **Then** the entry is marked
   "withdrawn" with the date and reason and never appears in a fetch list again.

---

### User Story 6 - See where the models' languages and the index diverge (Priority: P3)

When planning a model, the owner sees for every language in the index whether the base model of
the current zoo models reads it and how much of the current training data is in that language.
This shows where more data is enough and where a different base encoder would be needed.

**Why this priority**: The owner expects that the encoder may have to change. This report makes
that decision data-driven, but it only matters once the index has international content.

**Independent Test**: For a seeded index, the report lists each language with index volume,
base-model support (yes, no, unknown) and share in the current training data.

**Acceptance Scenarios**:

1. **Given** entries in a language the current base model does not read, **When** the report is
   produced, **Then** that language is listed as "not supported by the current base model" with
   its training-usable volume.

---

### Edge Cases

- A resource has content in many languages (a video archive with subtitles in 24 languages, a
  multilingual EU portal): the entry lists every content language and marks which are original,
  translated, or machine-translated.
- A resource has no language (a sensor table, a chart without labels, a photo set): language is
  "not applicable"; a chart with axis labels has the language of its labels.
- Language and country diverge (Spanish content from the US, French from Canada, English from
  India): language and country are recorded independently; supranational origins (EU, UN, World
  Bank) use a region value instead of a country.
- One collection mixes licences (a portal where some datasets are open and some are not): the
  collection entry records "mixed", and item entries carry their own licence; only items with a
  determined open licence can be cleared.
- "Free to watch" or "free to download" is not a licence: such resources get licence "unknown" or
  "proprietary", not an open licence.
- Platform terms forbid automated access or machine-learning use even where content is openly
  licensed (some video and podcast platforms, some APIs): the terms are recorded, and the entry
  cannot be cleared through that access route.
- The same work exists in several places (preprint and journal version, mirror on a data hub, video
  on two platforms): one entry, with the other locations recorded as alternative access routes.
- Machine-translated or AI-generated content is flagged; it is never counted as original content
  of its language in coverage reports.
- Audio and video contain voices and faces of private persons (podcasts, street footage):
  personal-data expectation is "present", including possible biometric data, so later fetch and
  processing follow the stricter rules.
- Live or continuously updated resources (real-time transit feeds, monthly statistics): the entry
  records update frequency; a later download records its own snapshot date.
- Very large resources (terabytes of video, full database dumps): the entry carries a size
  estimate so a fetch list can be planned against storage.
- Titles in non-Latin scripts: the original title is kept and an English title is added.
- Access requires registration, a request or payment: the access method says so and the entry is
  not cleared for an automated download.
- A resource disappears permanently: the entry is retired with reason and date, not deleted, so
  discovery does not propose it again.

## Requirements *(mandatory)*

### Functional Requirements

**Scope of an entry**

- **FR-001**: The index MUST describe resources, not hold them. An entry MUST NOT contain the
  resource's content beyond its title, an own short description and the metadata listed below.
- **FR-002**: An entry MUST describe either a collection (an archive, series, channel, portal,
  dataset, database, bucket) or a single item. A collection entry MAY have item entries below it.
  Discovery records collections by default and items only where they differ from their collection
  (for example in licence or language).
- **FR-003**: The index MUST cover mobility-related resources of every modality: text (papers,
  reports, laws, transcripts, articles, books, forum threads), audio (podcasts, recorded speeches),
  video (hearings, lectures, talks, documentaries), images (photos, maps), graphics and charts, and
  structured or quantitative data (tables, spreadsheets, databases, object storage buckets, data
  files in formats such as JSON or XML, APIs, feeds, geodata, time series and sensor data).
- **FR-004**: The index MUST be shared by all topics of the zoo. Every entry MUST record which
  topics it is relevant to (for example productdev, security, condition-monitoring), and the list
  of topics MUST be extensible without changing existing entries.

**Mandatory facts**

- **FR-005**: Every entry MUST carry these facts, and the index MUST reject an entry where one is
  missing:
  - a stable identifier that never changes;
  - title in the original language and an English title;
  - content language(s), using a standard language code, with explicit values for "not
    applicable" and "unknown";
  - country or region of origin, using a standard country code or a named supranational region,
    with an explicit value for "global";
  - source: publisher or rights holder, and the landing page address;
  - kind of source (who publishes it), from a controlled vocabulary that includes at least
    parliament, government or authority, research institution or academic publisher, open data
    portal, company or industry body, association or NGO, standards body, media or press,
    community or forum, education provider and individual creator;
  - type of resource (modality and genre), from a controlled vocabulary that covers every modality
    of FR-003;
  - licence: a standard licence identifier where one exists, the licence address, or an explicit
    "unknown", "proprietary" or "mixed".
- **FR-006**: Controlled vocabularies MUST be versioned and documented with a definition per
  value. A value outside the vocabulary MUST be rejected. Adding a value MUST be a recorded change
  with date and reason.

**Further facts the index needs**

- **FR-007**: Every entry SHOULD carry descriptive facts: an own short English description;
  mobility subdomain tags from a controlled vocabulary (for example road, rail, public transport,
  cycling, walking, micromobility, shared mobility, aviation, maritime, freight and logistics,
  electric vehicles and charging, automated driving, vehicle technology, urban and rural planning,
  policy and regulation, safety); time period covered; publication date and date of last update;
  update frequency; estimated volume (number of items, hours of audio or video, size on disk);
  file formats.
- **FR-008**: Every entry with spoken or visual content MUST record whether transcripts,
  subtitles, captions or alternative text exist and in which languages, since these decide whether
  text models can use it.
- **FR-009**: Every entry MUST record the origin of its content: original, human-translated,
  machine-translated, AI-generated, or unknown; and MAY link to entries that are translations of
  the same content.
- **FR-010**: Every entry MUST carry rights facts: whether attribution is required and its text
  where given, whether commercial use is allowed, whether share-alike applies, whether derivatives
  are allowed, access terms of the hosting platform that restrict automated access or machine
  learning, and the machine-readable opt-out signals found with their check date.
- **FR-011**: Every entry MUST carry a provisional usage decision derived by documented rules that
  match Constitution Principle VI and the source register of feature 006: permitted use
  (training_allowed, benchmark_only, not_usable, undetermined) and redistribution (allowed,
  not_allowed, unclear), each with a one-line rationale and the address of the licence evidence.
  The decision is provisional; the binding decision is made when a source record is created at
  fetch time.
- **FR-012**: Every entry MUST record its personal-data expectation (none, possible, present),
  naming the expected categories, including voices and faces of private persons.
- **FR-013**: Every entry MUST carry access facts that a later download needs: access method
  (direct download, bulk dump, API, feed, page by page, streaming platform, on request,
  registration required, paid, not accessible), access address(es), whether authentication is
  needed, cost, known rate limits, and estimated download size. Alternative access routes to the
  same content MUST be recorded on the same entry.
- **FR-014**: Every entry MUST carry a quality assessment on a defined scale with a rationale
  covering source authority, mobility relevance and information density, and MAY name the tasks
  it is expected to serve (for example JTBD extraction).
- **FR-015**: Every entry MUST record its own provenance: who or what added it (person, or
  discovery run with agent and model identifiers), when, how it was found (search, citation,
  recommendation, registry), and when it was last verified.

**Lifecycle and checks**

- **FR-016**: Every entry MUST have one status: candidate, verified, cleared for fetch, fetched,
  rejected, retired or withdrawn. Rejected, retired and withdrawn entries MUST remain in the index
  with reason and date so they are not proposed again.
- **FR-017**: Automated checks MUST run before every status change and on demand: mandatory facts
  present, vocabulary valid, landing page reachable, licence evidence present, opt-out signals
  checked, no duplicate. The result MUST be recorded on the entry.
- **FR-018**: An entry MUST become "cleared for fetch" only when its licence is determined (not
  unknown), its permitted use is training_allowed or benchmark_only, no opt-out signal and no
  platform term forbids the intended use, and it has at least one access route that can be used
  without payment, request or manual registration. Clearing MUST NOT require manual review by the
  owner; cases the rules cannot decide are flagged for an owner decision.
- **FR-019**: Duplicate detection MUST consider normalised addresses, persistent identifiers (such
  as DOIs) and the combination of title and publisher.
- **FR-020**: A periodic re-check MUST verify landing page, licence evidence and opt-out signals of
  every cleared entry. A change MUST revoke the cleared status and be recorded with date and
  previous value.
- **FR-021**: An objection from a rights holder or data subject, received through the project's
  existing objection channel, MUST set the entry to "withdrawn" and exclude it from every later
  fetch list.

**Discovery**

- **FR-022**: Entries MUST be addable by hand and in bulk from discovery runs. A discovery run MUST
  record its scope (languages, countries, subdomains, modalities), date, method, agent and model
  identifiers, cost, and counts of proposed, accepted and rejected candidates, including scopes
  that returned nothing.
- **FR-023**: Discovery MUST explicitly target languages other than German and English. The
  target languages of the first version are the 24 official languages of the EU (Bulgarian,
  Croatian, Czech, Danish, Dutch, English, Estonian, Finnish, French, German, Greek, Hungarian,
  Irish, Italian, Latvian, Lithuanian, Maltese, Polish, Portuguese, Romanian, Slovak, Slovenian,
  Spanish, Swedish) plus ten major world languages (Chinese, Japanese, Korean, Hindi, Arabic,
  Turkish, Russian, Indonesian, Ukrainian, Vietnamese). Regional varieties (for example Brazilian
  Portuguese, Latin American Spanish) are covered through the country field. The target list is
  part of the versioned vocabulary and can be extended.
- **FR-024**: Discovery MUST collect metadata only from publicly accessible pages, catalogues,
  registries and APIs, MUST follow their access terms and MUST NOT download resource content.

**Use of the index**

- **FR-025**: Users MUST be able to filter entries by every mandatory fact and by subdomain, topic,
  status, permitted use, transcript availability, content origin and quality.
- **FR-026**: The index MUST produce a coverage report: entry count and estimated volume per
  language, country, modality, kind of source and permitted use, and a list of gaps (target
  languages or modalities without a training-usable entry).
- **FR-027**: The index MUST produce a language report: per language, its volume in the index,
  whether the base model of each current zoo model reads it (yes, no, unknown), and its share in
  that model's current training data.
- **FR-028**: Users MUST be able to export a fetch list for a selection. The list MUST contain only
  cleared entries and, for each, all access and rights facts needed to fetch it and create its
  source record without further research. Refused entries MUST be listed with the reason.
- **FR-029**: When a resource is fetched by a later feature, its entry MUST link to the resulting
  source record and change to "fetched".
- **FR-030**: The index MUST be versioned. Each version used for a fetch list or a report MUST be
  dated and reproducible, and the change history of each entry MUST be kept.

**Visibility and privacy**

- **FR-031**: The index MUST NOT contain personal data beyond the names of publishers, public
  bodies and creators where attribution requires them.
- **FR-032**: The index is internal to the project in this feature. It MUST be built so that it
  can later be published as an open catalogue without rework: own descriptions only, no copied
  abstracts or content, and every fact traceable to its evidence. Publication itself is a later
  feature with its own release check.

### Key Entities

- **Index entry**: one resource (collection or item) with its mandatory facts, descriptive facts,
  rights facts, provisional usage decision, access facts, quality assessment, provenance and
  status. Items belong to at most one collection.
- **Access route**: one way to obtain the resource (method, address, authentication, cost,
  limits, size); an entry has one or more.
- **Vocabulary**: a versioned, documented list of allowed values (kind of source, type of
  resource, subdomain, topic, status, access method, content origin).
- **Check result**: outcome of one automated check on one entry, with date and details.
- **Discovery run**: one search over a scope, with method, agent, model, cost and outcome counts;
  entries it added point to it.
- **Fetch list**: a dated selection of cleared entries with their access and rights facts, plus
  the refused entries with reasons; tied to an index version.
- **Coverage report and language report**: dated summaries of an index version.
- **Source record** (existing, feature 006): created when a resource is fetched; the index entry
  links to it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of entries in every index version pass the mandatory-fact and vocabulary checks.
- **SC-002**: The first version of the index holds at least 2,000 entries, covering at least 30
  of the target languages of FR-023 other than German and English with at least 20 entries each.
- **SC-003**: Every modality group of FR-003 (text, audio, video, images, graphics and charts,
  structured data) has at least 50 entries in the first version.
- **SC-004**: At least 80% of entries have a determined licence (not "unknown"), and 100% of
  cleared entries carry the address of their licence evidence.
- **SC-005**: In an independent re-check of 30 randomly drawn entries, the provisional permitted
  use agrees with the re-check for at least 90% of entries, and no entry is found cleared that the
  re-check classifies as not usable.
- **SC-006**: The owner answers a coverage question (for example "training-usable video with
  subtitles in Romance languages about rail") in under one minute from the index alone.
- **SC-007**: In a later download pilot of 20 entries from a fetch list, at least 19 can be
  fetched and recorded as sources without additional research.
- **SC-008**: Fewer than 2% of entries are duplicates in an audit of 50 randomly drawn entries.
- **SC-009**: Every cleared entry has been re-checked within the last 6 months.

### Riskiest Assumption and Pilot

Riskiest assumption: outside German and English, enough mobility resources exist whose licence can
be determined from public metadata and that are usable for training. If most international
resources end up "unknown" or not usable, the index shows availability but does not improve
training.

Test before scaling discovery: a pilot discovery run in three target languages from different
language families and three modalities. Success: in each pilot language, at least 30% of accepted
entries have a determined licence and at least 10 entries are training_allowed. Kill or rethink
criterion: if two of three pilot languages miss this, the discovery strategy (sources searched,
kinds of source preferred) is revised before further languages are run. These criteria are fixed
before the pilot starts.

## Constitution Compliance

- **VI. Clean Provenance, Quality First**: the index records origin and licence for every
  resource before it is fetched; the provisional usage decision uses the rules of Principle VI
  (non-commercial is benchmark_only, share-alike recorded, opt-outs and platform terms respected).
  The binding decision stays with the source record at fetch time. The index holds no content and
  no personal data beyond attribution (FR-001, FR-031). Quality is recorded per entry (FR-014).
- **VII. Metadata over Inference**: language, country, kind and type of source, date and subdomain
  are recorded as metadata at discovery time, so no model has to predict them later.
- **IX. Reproducible, Dated Releases**: index versions, fetch lists and reports are dated and
  reproducible (FR-030).
- **Resources & Cost Discipline**: discovery uses local compute and the subscription first;
  pay-per-use APIs only with a stated cash budget in the plan. "Crawl once" is unaffected: the
  index fetches metadata only, and later downloads create one snapshot per resource.
- **Project Scope**: the index is shared by all topics and therefore lives at the shared level of
  the repository; topic relevance is a field, so new topics need no change to existing entries.
- Principles I, II, III, IV (agreement pilot), V, VIII and X concern model tasks and are not
  touched. Principle IV's rule to name and test the riskiest assumption first is applied above.

## Assumptions

- The index is metadata only. Downloading content, transcribing audio and video, building
  training data, retraining models and changing the base encoder are out of scope and are later
  features that read from the index.
- Only mobility-related resources are indexed in this feature; other domains may follow.
- Collections are the default granularity (FR-002); item entries are added only where an item
  differs from its collection.
- The working language of the index is English (own descriptions, English titles); original
  titles are kept.
- Languages and countries use standard codes; supranational bodies use named regions.
- Discovery is done by agents with automated checks. Following the owner's direction, entries are
  not reviewed one by one; the owner decides only flagged conflicts.
- The current base model of scout-large reads about a hundred languages, so a different encoder
  may only be needed for languages outside that set; the language report (FR-027) makes this
  visible.
- The objection channel and the source register of feature 006 exist and are reused.
- The cash budget for discovery is 0 € beyond the flat-rate subscription unless the plan states
  and justifies a pay-per-use budget. At 2,000+ entries the subscription's usage limits matter;
  the plan spreads discovery runs over time and uses local models for checks where possible.
