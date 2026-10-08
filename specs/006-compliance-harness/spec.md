# Feature Specification: Compliance harness

**Feature Branch**: `006-compliance-harness`

**Created**: 2026-10-08

**Status**: Draft

**Input**: User description: "Compliance harness for the mobility-model-zoo (feature 006, before feature 005 continues): one machine-readable compliance register as the single source of truth, fail-closed checks along the whole data and release path, generated public compliance documents, an owner decision log, and a patch release scout-large 0.1.2 that closes the gaps found in the published model. Basis: the research report of 2026-10-08 and constitution 2.0.0. Not legal advice."

## Context

The zoo publishes models that others may use commercially. Until now, compliance lived in scattered rules: licence fields in release records, redaction before labeling, teacher terms, a secret scan. The research report of 2026-10-08 ([legal-research/report.md](legal-research/report.md), notes in [legal-research/](legal-research/)) reviewed EU AI Act, GDPR/BDSG, copyright and text and data mining, licences and provider terms, the Cyber Resilience Act, export control, product liability and the German imprint duty.

Its findings for this project:

- **What the exemptions hang on.** The project stays outside most product regimes (AI Act through the open-source exclusion, CRA, product liability, imprint) as long as it is non-commercial and no model card states a high-risk or safety purpose. None of the models is a general-purpose AI model.
- **What binds the project.** GDPR binds it fully: publishing on the internet rules out the household exemption. §44b UrhG binds it, which means respecting opt-outs at fetch time and deleting copies when no longer needed. CC licences require full attribution and share-alike. Provider terms of the teacher and reference models bind as well.
- **Gaps in the published `scout-large` 0.1.x:**
  - teacher calls through OpenRouter without a pinned provider;
  - Claude reference labels made through the consumer subscription;
  - no privacy notice, NOTICE file or security contact;
  - incomplete CC attribution (no creator, no modification notes);
  - no recorded consent basis for the Zenodo interview transcripts;
  - no recorded purpose or deletion date for raw snapshots.

Owner decisions of 2026-10-08 that this feature encodes:

1. Labeling runs locally first (DGX Spark). Hosted models are used only through pinned OpenRouter providers that are in the EU or certified under the EU-US Data Privacy Framework, with zero data retention and no training on inputs. Past unpinned calls are documented retrospectively and named in the privacy notice.
2. Claude reference labels: future runs go through the Anthropic API with a data processing agreement. For `scout-large` 0.1.x the register holds a dated risk acceptance.
3. Contact: the zoo is run by Martin Habedank as a private person.
   - Controller contact: `privacy@miskatonic-analytics.com` and `contact@miskatonic-analytics.com`.
   - The imprint and website privacy policy at https://miskatonic-analytics.com/imprint.html and https://miskatonic-analytics.com/privacy.html are linked.
   - No Miskatonic branding, no consulting promotion and no monetisation appear in the zoo.
4. Feature 006 is implemented before feature 005 continues; the dataset declarations of 005 become part of the register.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One register answers every compliance question (Priority: P1)

The owner opens the compliance register and finds, for every source, dataset, teacher or provider, and model release, what may be done with it and why. That covers licence, attribution, permitted use, redistribution, personal data and legal basis, retention, terms of service and the AI Act classification. Every owner decision is recorded with date and rationale. Each record has a next review date. A missing or overdue record stops the release.

**Why this priority**: Every other part (checks, documents, the scout-large patch) reads from the register. Without it, compliance stays a matter of memory.

**Independent Test**: Validate the register: every source used by `scout-large` 0.1.0/0.1.1, every teacher and provider in its labeling logs, and the model release itself have complete records. Removing one field or moving a review date into the past makes the release gate fail with a message naming the record.

**Acceptance Scenarios**:

1. **Given** the register, **When** the owner looks up any source used by a published model, **Then** licence, creators, attribution text, modifications, permitted use, redistribution status with basis, copyright basis, personal-data categories, legal basis, retention purpose and date, and review dates are present.
2. **Given** a teacher or reference model used for labeling, **When** its record is shown, **Then** it states model and version, access path (consumer, API, pinned hosted provider, local), retention and training settings, data processing agreement, region, the terms version that was checked, whether training on outputs is permitted, and the owner's sign-off.
3. **Given** a model release, **When** its record is shown, **Then** it contains the AI Act classification. That covers AI system and general-purpose assessment with compute estimate, exclusion basis, monetisation status, intended purpose and out-of-scope uses, high-risk and safety-component assessment, transparency trigger, export self-classification, memorisation results, the legal reference versions used, reviewer and next review trigger.
4. **Given** an owner decision (for example the Claude risk acceptance), **When** it is looked up, **Then** it has date, decision, rationale, scope, expiry or review date and the records it affects.
5. **Given** a record with an overdue review, an expired waiver or a missing field, **When** any release check runs, **Then** it fails and names the record and field.

---

### User Story 2 - Public compliance documents are generated, never hand-written (Priority: P1)

A reader of the repository or of a model card finds the following:
- **Repository documents:** a privacy notice that says who is responsible, which data is processed, from which kinds of sources, to which recipients, for how long, and how to object; a copyright policy that says which opt-out signals the crawler honours and how to request removal; a security contact; full third-party notices.
- **In each model card:** a complete attribution table, the teacher and labeling models with their access paths, out-of-scope use, dual-use considerations for security models, and a privacy section.

All of these are rendered from the register. The release gate fails if a committed or published document differs from its rendering.

**Why this priority**: These documents close the visible gaps of the published model and are the project's public commitments. Writing them by hand would let them drift from reality.

**Independent Test**: Render all documents from the register. Change one attribution in the register. The check reports the drift until the documents are re-rendered.

**Acceptance Scenarios**:

1. **Given** the register, **When** the documents are rendered, **Then** the repository contains a privacy notice, a copyright policy, a security policy, a NOTICE file, a third-party notices file, licence texts with machine-readable file licensing, and an opt-out and takedown request template, all in English.
2. **Given** the privacy notice, **When** compared with the labeling logs and the register, **Then** it names every provider that received texts (including past unpinned OpenRouter calls), every source class, and every retention period. It also names the controller contact and links the imprint, and it states the right to object separately and prominently.
3. **Given** a model card, **When** rendered, **Then** it contains:
   - an attribution table with title, creator, source link, licence and modification notes for every source or dataset;
   - the XLM-R MIT notice where it applies;
   - a teacher and labeling section;
   - out-of-scope use;
   - dual-use and standards disclaimers where the topic requires them;
   - links to the privacy notice and copyright policy.
4. **Given** a model release, **When** documents are rendered, **Then** its AI Act classification record, export self-classification and a voluntary training-data summary in the structure of the EU AI Office template are produced.
5. **Given** a committed document that was edited by hand, **When** the check runs, **Then** it fails until the document matches its rendering.

---

### User Story 3 - scout-large 0.1.2 closes the gaps of the published model (Priority: P1)

The published model gets a patch release with the same weights, a card that meets the new rules, and complete records behind it. The release note says what changed and why.

**Why this priority**: The published model is the only public artefact today; its gaps are the most concrete exposure.

**Independent Test**: Run the release gate for `scout-large` 0.1.2 with all compliance checks enabled. It passes. The rendered card shows the attribution table, the teacher section with access paths, the privacy and copyright policy links and the NOTICE content. The weights are byte-identical to 0.1.1.

**Acceptance Scenarios**:

1. **Given** the 0.1.1 sources, **When** their records are completed, **Then** each has creator, attribution text and modification notes. The Zenodo interview transcripts record their consent or ethics basis, or are flagged for owner decision.
2. **Given** the 0.1.x labeling history, **When** documented retrospectively, **Then** every provider that received texts is recorded with what is known about retention and region. Unknown values are recorded as unknown, never guessed. The privacy notice names them.
3. **Given** the Claude reference labels made through the consumer subscription, **When** 0.1.2 is checked, **Then** the dated owner risk acceptance is present, and the card states how the reference labels were produced.
4. **Given** raw snapshots kept for `scout-large`, **When** their retention is recorded, **Then** each store has a purpose and a deletion or review date.
5. **Given** the gate passes and the owner approves the preview, **When** 0.1.2 is published, **Then** it goes through the existing release pipeline as a patch with unchanged file hashes and unchanged metric values.

---

### User Story 4 - Published material cannot leak training data or overclaim (Priority: P2)

Before anything is published, the harness checks four things:
- whether cards, examples, evaluation reports and other published files contain text that overlaps with the training corpus or contains personal data;
- whether the model can reproduce training text;
- whether the card makes claims the project must not make: a high-risk or safety purpose, "production-ready", "certified", "anonymous model";
- whether the repository shows monetisation markers.

**Why this priority**: Publication is the point of no return; leaked personal data or a high-risk purpose in a card changes the legal position of the whole project.

**Independent Test**: Seed a fixture card with:
- a sentence copied from the corpus;
- an e-mail address;
- the phrase "suitable as a safety function";
- a funding link.

Each is reported and blocks the release. A clean card passes.

**Acceptance Scenarios**:

1. **Given** a published file containing a span from the training corpus longer than the configured threshold, **When** checked, **Then** the release fails. The exception is an attributed quote from a source whose record allows it (an official work under §5 UrhG or a CC source).
2. **Given** a model release, **When** the memorisation test runs, **Then** the result is recorded in the release record, and a result above the threshold fails the release.
3. **Given** a model card, **When** linted, **Then** missing required sections fail the release, as do forbidden claims and wording that matches a high-risk use or safety function. Required sections: intended use, out of scope, limitations, dual-use for security topics, standards disclaimer for automotive topics, export note where required, privacy and copyright policy links.
4. **Given** the repository or a model repository, **When** checked, **Then** missing licence, NOTICE or security policy fails the release, as do funding links, paid offers and promotion of commercial services.
5. **Given** a share-alike-trained model, **When** checked, **Then** its licence matches and its Hub repository is not gated.

---

### User Story 5 - The data path stops non-compliant data before it costs money or leaves the machine (Priority: P2)

From fetching a source to training a model, each step checks its compliance preconditions and stops on missing evidence.

| Step | What is checked |
|---|---|
| Fetch | Opt-out signals and blocklists are honoured, and the verdicts are recorded per document. |
| Ingest | Provenance and licence are complete. |
| Pre-send | Before a text is sent to an LLM, redaction is complete, residual personal data is scanned, sensitive categories are quarantined and the provider is allowed and pinned. |
| Retention | Snapshots past their retention date are flagged and deletions are logged. |
| Train | Opt-outs are re-checked, unusable licences are blocked, share-alike sets the model licence, and teachers need a terms sign-off. |

**Why this priority**: Future data generation for every topic runs through this path. Stopping early is cheaper than retracting later.

**Independent Test**: A fixture crawl with one robots.txt disallow, one TDM reservation and one `noai` page is recorded and skipped. A fixture batch with one unredacted e-mail address and one health statement is refused before sending. A labeling call to an unpinned hosted provider is refused.

**Acceptance Scenarios**:

1. **Given** a source whose robots.txt disallows the project crawler or common AI crawlers, or that declares a TDM reservation, `noai` or an ai.txt refusal, **When** fetched, **Then** the document is skipped and the verdict is recorded in the crawl manifest.
2. **Given** terms of service that may forbid mining, **When** detected, **Then** the source is held until the owner confirms. Natural-language reservations count as opt-outs until the owner records otherwise.
3. **Given** a labeling batch, **When** it is about to be sent to a hosted model, **Then** it is refused in any of these cases:
   - redaction did not run on every item;
   - the residual personal-data scan finds hits;
   - a sensitive-category text is not quarantined;
   - the provider is not on the allowlist or not pinned.
4. **Given** a snapshot past its retention date, **When** the retention check runs, **Then** it is reported, and its deletion is logged once done.
5. **Given** training input from a non-commercial, no-derivatives or unknown licence, or from a teacher without terms sign-off, **When** training starts, **Then** it is refused.

---

### User Story 6 - Requests from data subjects and rights holders are handled and dates are watched (Priority: P3)

Anyone can ask to object, to have data erased, to see what is held about them, or to have a work removed. The request reaches the owner through a documented channel. It is logged, searched across the stores, answered within the legal deadline, and added to a suppression list that later fetches and training runs respect. Pending court decisions and legal dates that could change the rules are tracked; each one has a review date that fails the meta check when it passes.

**Why this priority**: Needed for GDPR and copyright compliance, but rare in volume; the channel and log must exist before the next release, while the workflow can stay manual.

**Independent Test**: File a fixture request. It appears in the log with a deadline. Its identifier is added to the suppression list. A later fetch of a matching document is skipped. A review date in the past fails the meta check.

**Acceptance Scenarios**:

1. **Given** the published channels (the request template and the privacy e-mail), **When** a request arrives, **Then** it is logged with type, receipt date, deadline, stores searched, action taken and answer date. The log holds no personal data beyond a hashed identifier.
2. **Given** a suppression entry, **When** later fetches or training runs touch matching content, **Then** they skip it.
3. **Given** the legal watch list (BGH I ZR 281/25, German product liability act from 2026-12-09, end of the AI Act Art. 50(2) grace period 2026-12-02, GEMA v OpenAI appeal, CJEU C-250/25, GDPR omnibus Art. 88bis, final CRA guidance, Latombe appeal), **When** a review date passes without a recorded review, **Then** the meta check fails.

---

### Edge Cases

- **Unknown facts.** A field is unknown and cannot be found out (for example the retention of a past unpinned provider call): it is recorded as `unknown` with the date of the attempt. Unknown never passes a check that needs the value unless a waiver with expiry covers it.
- **Sources licensed in the past.** The source was fetched before opt-out signals were recorded, as for `scout-large` 0.1.x: a retrospective check of the current signals is recorded as such, with its date. Nothing is backdated.
- **A source becomes forbidden after training.** An opt-out or objection arrives after a model was trained on the source: the source is suppressed for future runs, and the model's record gets a review entry. Withdrawing a published model is an owner decision, never automatic.
- **Datasets with human subjects** (UCI HAR, Zenodo interviews): consent or ethics basis unknown means the dataset is not redistributable and needs an owner decision before training use.
- **Vehicle data.** It may contain vehicle identification numbers, GPS or absolute timestamps; a scan hit holds the dataset until the owner accepts or a cleaning step is recorded.
- **Waivers.** A waiver without expiry is invalid. Expired waivers fail the meta check.
- **Third-party examples.** A model card example is taken from a third-party dataset: it must come from a source whose record says redistribution is allowed, and it is attributed.
- **A provider's terms change.** The stored snapshot hash differs from the current terms page, so the teacher's sign-off becomes due again.
- **Generated documents and personal data.** A document must never contain personal data of data subjects. Only the controller's own published contact details appear.

## Requirements *(mandatory)*

### Functional Requirements

**Register and decisions**

- **FR-001**: The project MUST keep one machine-readable compliance register in the repository, with record types for sources and datasets, teachers and providers, model releases, rights and takedown requests, waivers, owner decisions and legal watch items. The register MUST contain no personal data of data subjects.
- **FR-002**: Every record MUST carry owner, last review date and next review date. Every field that a check needs MUST be present or explicitly `unknown` with the date of the attempt.
- **FR-003**: The dataset declarations of feature 005 MUST be part of the register (same fields, extended), not a parallel structure.
- **FR-004**: Crawl manifests (per fetched document: URL, fetch time, user agent, status, opt-out signals and verdicts, terms hash, content hash) MUST be kept with the data outside the repository and referenced from the register by hash.
- **FR-005**: Owner decisions MUST be recorded with date, decision, rationale, scope, affected records and review date. The decisions of 2026-10-08 listed in Context MUST be recorded at the start.

**Checks**

- **FR-006**: Checks MUST fail closed: a missing record, field or result counts as a failure. A failure in one stage MUST stop all later stages of the same run.
- **FR-007**: The meta stage MUST validate the register and fail on overdue reviews, legal references older than their review date, and expired waivers.
- **FR-008**: The fetch stage MUST honour and record the following. A blocked document MUST NOT be stored.
  - robots.txt for the project crawler, `*` and common AI crawler user agents;
  - TDM reservation (TDMRep headers and files);
  - `noai` and `X-Robots-Tag`;
  - ai.txt;
  - a domain denylist and piracy list;
  - a terms-of-service flag that needs owner confirmation;
  - no circumvention of login, paywall or CAPTCHA.
- **FR-009**: The ingest stage MUST refuse sources with incomplete provenance or a licence outside the allowlist. It MUST also refuse official-work series without a recorded §5 decision, human-subject data without a consent or ethics field, and vehicle data with unresolved identifier scan hits.
- **FR-010**: The pre-send stage MUST refuse a batch bound for a hosted model in any of these cases:
  - redaction did not run on every item;
  - the residual personal-data scan (including German identifiers) has hits;
  - special-category content is not quarantined;
  - the provider is not on the allowlist (EU or DPF, zero data retention, no training on inputs);
  - for OpenRouter, the provider is not pinned.
- **FR-011**: The retention stage MUST report snapshots past their retention date or without purpose, and MUST log deletions.
- **FR-012**: The train stage MUST re-check opt-outs and the suppression list. It MUST refuse non-commercial, no-derivatives and unknown licences and teachers without terms sign-off, and MUST force the model licence to match share-alike inputs.
- **FR-013**: The model stage MUST record a memorisation result and a corpus-overlap result per release, and a compute estimate. Results above the thresholds MUST fail the release.
- **FR-014**: The publication stage MUST scan every file that will be published (cards, examples, evaluation reports, READMEs) for corpus overlap above the threshold and for personal data, and MUST require examples to be synthetic or from a source whose record allows redistribution.
- **FR-015**: The card lint MUST require intended use, out of scope, limitations, and links to the privacy notice and copyright policy. It MUST also require dual-use considerations for security topics, a standards disclaimer for automotive topics and an export note where the export self-classification asks for one. It MUST reject:
  - wording that states a high-risk use or a safety function;
  - marketing claims ("production-ready", "certified");
  - the claim that a model is anonymous.
- **FR-016**: The licence-artefact stage MUST verify that NOTICE, third-party notices, licence texts, machine-readable file licensing and card attribution equal their rendering from the register. It MUST also verify that Hub licence and base-model metadata match the register, and that share-alike models are not gated.
- **FR-017**: The repository stage MUST require a licence, NOTICE and security policy, MUST run the secret scan, and MUST reject funding links, paid offers, consulting promotion and Miskatonic branding in the zoo.
- **FR-018**: The notices stage MUST verify that the privacy notice names every provider found in the labeling logs, every source class in the register, and the retention periods from the configuration.
- **FR-019**: The final stage MUST require the owner's sign-off on the AI Act classification record and on the release.
- **FR-020**: Every check MUST run in the tool where its data lives: fetch and label paths of the task tools, the `zoo` release gate, and CI. Each check MUST print the record and field that failed.

**Generated documents**

- **FR-021**: The following MUST be rendered from the register and committed:
  - `PRIVACY.md`: GDPR Art. 14 notice with controller, purposes, legal bases, source classes, recipients including past unpinned calls, retention, rights, a separate and prominent Art. 21 objection right, the complaint right, and links to the imprint and website privacy policy.
  - `COPYRIGHT_POLICY.md`: crawler user agent, signals honoured, blocklists, takedown contact.
  - `SECURITY.md`.
  - `NOTICE` and `THIRD_PARTY_NOTICES.md`.
  - Licence texts with machine-readable file licensing.
  - An opt-out and takedown request template.
  - A record of processing activities.
  - A combined legitimate-interest and impact assessment document.
- **FR-022**: For every model release, the model card sections "Training data and attribution", "Teacher and labeling models", "Out-of-scope use", "Dual-use considerations" (security topics) and "Privacy and personal data", and the Hub metadata (licence, base model and relation, datasets, library), MUST be rendered from the register.
- **FR-023**: For every model release, the AI Act classification record, an export self-classification note and a voluntary training-data summary following the EU AI Office template structure MUST be rendered and kept with the release. Firmware releases MUST include a software bill of materials.

**scout-large 0.1.2**

- **FR-024**: Records for every source, teacher, provider and the release of `scout-large` 0.1.x MUST be completed, using `unknown` where facts cannot be established, with retrospective documentation of past provider calls and the dated Claude risk acceptance.
- **FR-025**: `scout-large` 0.1.2 MUST be a patch release with byte-identical weights and identical metric values. Its card MUST be rendered under the new rules and the release published through the existing pipeline after owner approval.

**Requests and legal watch**

- **FR-026**: A request channel (request template plus privacy e-mail) MUST be published, and a request log MUST record type, dates, deadline, stores searched, action and answer without storing personal data beyond a hashed identifier.
- **FR-027**: A suppression list MUST be honoured by the fetch and train stages.
- **FR-028**: The legal watch list MUST hold each pending decision or date with a review date, and the meta stage MUST fail when a review date passes unreviewed.

**Open owner decisions (collected during planning; defaults apply until decided)**

- **FR-029**: The plan MUST collect these owner decisions and record them in the register. Until a decision is recorded, the default applies:

  | Decision | Default |
  |---|---|
  | Copyright basis | §44b only |
  | Natural-language terms as opt-out | yes, until the BGH rules in the LAION case |
  | Verbatim span threshold for published files | at most 30 consecutive words from the corpus |
  | Memorisation threshold | no training span longer than 50 tokens reproduced verbatim in extraction probes |
  | Redaction recall target | measured and reported, with no release below 0.95 on the labeled redaction test set |
  | Legitimate-interest assessment | one per source class |
  | Impact assessment | a combined DPIA-lite document |
  | Sensitive-but-relevant content | excluded |
  | Future compendium | link only, no re-hosting |

### Key Entities

- **Compliance register**: the single source of truth; a set of typed records with owner and review dates.
- **Source / dataset record**: what a source or dataset is, who made it, under which licence and terms it may be used, trained on, quoted and redistributed, which personal data it contains and on which legal basis, where it is stored and until when.
- **Fetched document (crawl manifest entry)**: per-document evidence of lawful access and honoured opt-outs, kept outside git with the data.
- **Teacher / provider record**: a model used for labeling and the route the texts took to it, with terms, retention, region and sign-off.
- **Model release record**: the AI Act classification and licence manifest of one published version, with memorisation and overlap results.
- **Owner decision**: a dated, scoped decision with rationale and review date.
- **Request**: an objection, erasure, access, takedown or opt-out request, its handling and deadline.
- **Waiver**: a time-limited exception to one check.
- **Legal watch item**: a pending decision or legal date with its review date.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100 % of the sources, teachers, providers and releases behind published models have complete records (or `unknown` with a dated attempt), and the register validates without errors.
- **SC-002**: 100 % of the public compliance texts (privacy notice, copyright policy, security policy, notices, card attribution and policy sections) are rendered from the register, and an edit to any of them by hand is detected before release.
- **SC-003**: Each seeded violation in the test fixtures is caught by its stage, and a clean fixture passes every stage. Seeded violations: one per check, covering a robots.txt disallow, a TDM reservation, an unredacted e-mail, an unpinned provider, a non-commercial licence, a corpus sentence in a card, a safety-function claim, a funding link, a missing NOTICE, an overdue review and an expired waiver.
- **SC-004**: `scout-large` 0.1.2 is published with weights and metrics identical to 0.1.1, and its card shows a complete attribution entry for every source, the teacher and labeling routes, and links to the privacy notice and copyright policy.
- **SC-005**: The privacy notice names every provider that appears in the labeling logs of published models (zero unnamed recipients).
- **SC-006**: A request filed through the published channel is logged with its deadline within one working day of receipt.
- **SC-007**: No personal data of data subjects in the repository, the register or any published file, confirmed by the publication scan over the whole repository.

## Assumptions

- **Not legal advice.** The register and checks implement the research report's reading of the law; where the report marks law as unsettled, the conservative reading is the default. A lawyer review is not planned. The owner may order one for specific decisions.
- **Owner role.** The owner approves releases and decisions (memory: autonomy). Records, checks and documents are produced and verified automatically.
- **Labeling.** Local inference on the DGX Spark is available for future labeling. Hosted labeling, if needed, runs through pinned providers or the Anthropic API under a cash budget stated in the plan.
- **Copyright scope.** `scout-large` 0.1.x used parliamentary records, CC BY papers and CC BY Zenodo interviews, not forum or review texts (per its card). The retrospective documentation relies on the stored snapshots and labeling logs.
- **Feature 005.** Topics, layout and edge models come later. The register is designed for all topics but filled only for what exists today (scout-large, the sandbox model, and the dataset declarations planned in 005).
- **Hosting.** The controller contact and imprint are reused from miskatonic-analytics.com without branding the zoo (memory: zoo private, not branded).

## Constitution Compliance

| Principle | How this feature complies |
|---|---|
| III Measure Before Optimizing | Memorisation and overlap results become recorded, thresholded measurements (FR-013). |
| V Small and Local, Budgets per Task | Local labeling first; hosted only with a stated budget (owner decision 1). |
| VI Clean Provenance | The register makes origin, licence, permitted use, redistribution and retention checkable for every source and dataset (FR-001 to FR-004, FR-008 to FR-012); datasets stay out of git. |
| IX Reproducible, Dated Releases | Compliance documents are versioned and rendered per release (FR-021 to FR-023); 0.1.2 is a patch with identical files (FR-025). |
| Resources & Cost Discipline | Crawl once stays; snapshots get retention dates (FR-011). |
| Development Workflow & Quality Gates | The gate before a release gains the compliance stages (FR-006 to FR-020). |
