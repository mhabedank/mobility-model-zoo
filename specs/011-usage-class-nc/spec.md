# Feature Specification: Usage class and non-commercial releases

**Feature Branch**: `011-usage-class-nc`

**Created**: 2026-10-10

**Status**: Draft

**Input**: User description: "Usage class and non-commercial (NC) releases in the release gate and the compliance harness, following constitution 2.1.0. Every model gets a usage class derived from the most restrictive of its inputs (training and fine-tuning datasets, base model, teacher outputs, third-party models loaded at run time). The release gate and the train check stop rejecting NC-licensed training data outright and allow it for NC models, while data whose licence, terms or opt-out forbid training stays benchmark_only. Outputs of an NC model are NC data. Release record, model card, Hugging Face card and website state usage class and licence; NC models are released under a non-commercial licence, carry the name suffix -nc and name the inputs that make them NC. The gate refuses a release whose licence or marking is less restrictive than the derived usage class. A register of third-party models records model id, pinned revision, pinned remote code commit, licence of the weights and licences of the documented training data; a stage that loads a restricted third-party model states the restriction."

**Owner decisions (2026-10-10)**:
- The zoo MAY build and publish non-commercial models. They are marked as such and carry a fitting licence (constitution 2.1.0, Principles VI and IX).
- Compliance takes precedence over unrestricted use: a user's rights to a model may be restricted, and users learn the restrictions before download.
- Non-commercial models carry the name suffix `-nc` (`<name>-<variant>-nc`).

## Context

Until constitution 2.0.0, a source or dataset under a non-commercial licence had to be `benchmark_only`, and the code enforces that in several places: release gate rule 6, the train check C-T2, the ingest check C-I2 with its licence allowlist ("NC and ND licences are never on this list"), and the dataset and source schemas (`-NC` or `-ND` licence ⇒ `benchmark_only`; `training_allowed` ⇒ `commercial_use: true`). Constitution 2.1.0 replaces the ban with a usage class per model: restrictions of every input carry over to the model, and a non-commercial input makes the model non-commercial instead of being refused.

What exists today and is reused: the dataset declarations with `commercial_use` (feature 005), the compliance register and its stages (feature 006), the release gate with rules 1–17 and the card renderer (feature 003), the website (feature 008), and the provider routes with `output_training_permitted`. What is missing: a usage class anywhere in the code, a register of third-party models, any marking of restrictions on cards and pages, and a naming rule for `-nc`. The website copy currently promises "Open for everyone, including commercial use" for the whole zoo.

Feature 009 (deduplication and clustering) is waiting for this feature: its NLI model is MIT-licensed but trained on XNLI and ANLI (CC BY-NC 4.0), so under 2.1.0 it may be used but makes the stage output non-commercial.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Release a non-commercial model, marked everywhere (Priority: P1)

The owner wants to release a model trained on a dataset under CC BY-NC 4.0 (for example a CAN bus dataset that is only available non-commercially). They declare the model non-commercial, name it with the suffix `-nc`, train it, and run the usual release gate. The gate accepts the NC training data for this model, and every place a user looks shows that the model is for non-commercial use only and why.

**Why this priority**: This is the new capability the owner asked for. Without it, good non-commercial material stays unusable for training, and the other stories only refuse things.

**Independent Test**: Build a fixture model declared non-commercial with one CC BY-NC 4.0 training dataset. The offline gate passes. The rendered card, the Hugging Face front matter, the release record and the website page all show "non-commercial", the licence CC BY-NC 4.0 and the dataset that makes it NC.

**Acceptance Scenarios**:

1. **Given** a model declared non-commercial and named `<name>-<variant>-nc`, **When** its training data includes a dataset under CC BY-NC 4.0 that is declared `training_allowed` with `commercial_use: false`, **Then** the train check and the release gate accept it.
2. **Given** that model, **When** its card is rendered, **Then** the first lines of the card state "Non-commercial use only", the licence and the inputs that make it non-commercial, and the `## License` section repeats them.
3. **Given** that model, **When** its Hugging Face front matter is built, **Then** the licence tag is the non-commercial licence (`cc-by-nc-4.0`, or `cc-by-nc-sa-4.0` when an input is also share-alike).
4. **Given** that model, **When** the website is built, **Then** its model page and its entry on the start page show "non-commercial" next to the licence, and the page says what that permits before the install line.
5. **Given** a model with a share-alike input and a non-commercial input whose licences are compatible (for example CC BY-NC-SA 4.0 data), **When** the release licence is CC BY-NC-SA 4.0, **Then** the gate accepts it; with CC BY-NC 4.0 it refuses because the share-alike term was dropped.

---

### User Story 2 - The gate refuses a release that hides a restriction (Priority: P1)

A model is declared for commercial use, but one of its inputs is restricted: a non-commercial training dataset, a base model under a non-commercial licence, a teacher whose terms permit training on outputs only for non-commercial use, a third-party model loaded at run time whose documented training data is non-commercial, or data generated by a non-commercial zoo model. The train check stops the run before it costs money where it can, and the release gate refuses the release in any case, naming the input and the restriction.

**Why this priority**: Constitution 2.1.0 relaxes a ban; without this story the relaxation would let restricted material slip into commercial releases. Refusing is what keeps users from inheriting a hidden risk.

**Independent Test**: For each of the five input kinds, a fixture model declared commercial with one restricted input of that kind is refused by the gate with a message that names the input and its licence. The same model declared non-commercial passes.

**Acceptance Scenarios**:

1. **Given** a model declared commercial, **When** a training dataset has `commercial_use: false`, **Then** the train check and the gate refuse it and name the dataset.
2. **Given** a model declared commercial, **When** its base model's licence or its base model's documented training data is non-commercial, **Then** the gate refuses it and names the base model and the licence that restricts it.
3. **Given** a model declared commercial, **When** a teacher's terms permit training on outputs for non-commercial use only, **Then** the gate refuses it; a teacher whose terms forbid training on outputs is refused for every model, as today.
4. **Given** a model declared commercial, **When** its training data was generated or labeled by a zoo model whose usage class is non-commercial, **Then** the gate refuses it and names that model.
5. **Given** a model declared commercial, **When** a third-party model it loads at run time is restricted (by its weights licence or by its documented training data), **Then** the gate refuses it.
6. **Given** any model, including a non-commercial one, **When** a training input is under a no-derivatives licence, an unknown licence, "all rights reserved", platform terms that forbid training (for example Reddit) or a machine-readable opt-out, **Then** the train check and the gate refuse it, as today.
7. **Given** a model whose name ends in `-nc`, **When** its declared usage class is commercial, **Then** the gate refuses the name; **given** a model declared non-commercial, **When** its name lacks `-nc`, **Then** the gate refuses it too.
8. **Given** inputs whose terms cannot be met by one release licence (for example a CC BY-SA 4.0 dataset and a CC BY-NC-SA 4.0 dataset), **When** the gate derives the usage class, **Then** it refuses the release and names the conflicting inputs.

---

### User Story 3 - One register of third-party models (Priority: P2)

Base models, encoders and classifiers that a zoo model or a pipeline stage loads come from third parties. Each is recorded once in a register: model id, pinned revision, pinned commit of any remote code it loads (which may live in another repository), licence of the weights, licences of the training data its model card names, and the restriction that follows. Model declarations and stage settings refer to the register, and a check fails when a used third-party model is missing from it, unpinned, or recorded differently.

**Why this priority**: The usage class of a model can only be derived if the licences of its third-party parts are known. The register also answers the open question of feature 009 (NLI model) in a reusable way. It is P2 because the gate's base-model check works from model declarations already, and the register widens coverage.

**Independent Test**: Register `FacebookAI/xlm-roberta-large` (base model of scout-large) and one fixture model with non-commercial training data. A model declaration that names an unregistered base model fails the check; one whose recorded revision differs from the register fails; the registered NC-trained model yields the restriction "non-commercial" when derived.

**Acceptance Scenarios**:

1. **Given** a third-party model in the register, **When** its model card names training data under CC BY-NC 4.0 and its weights are MIT, **Then** the derived restriction is non-commercial and the record names the training data as the reason.
2. **Given** a model declaration or stage settings that name a third-party model, **When** the model is not in the register, its revision is not pinned, or its remote code is not pinned to a commit, **Then** the check fails and names the model.
3. **Given** a pipeline stage that loads a restricted third-party model, **When** it writes its output, **Then** the output metadata names the third-party model and the restriction, and the stage's documentation states it.
4. **Given** a register record, **When** its review date has passed, **Then** the compliance meta check reports it like any other overdue record.

---

### User Story 4 - Existing models get a usage class and the zoo stops overpromising (Priority: P2)

The owner runs one command and sees the derived usage class of every model in the zoo (published and draft) with the inputs that determine it. Gaps (a licence written as free text that maps to no known licence, a missing register entry) are listed as findings. The website and the shared site copy no longer promise commercial use for the whole zoo; each model states its own class.

**Why this priority**: Published versions are immutable, so the audit cannot change them; it makes sure the next release of each model is correct and that the website does not claim more than the licences allow. It is P2 because nothing is released while it is open.

**Independent Test**: Run the audit offline on the repository. It lists all six models with a usage class or a finding, finishes in under a minute, and changes no file of a published release.

**Acceptance Scenarios**:

1. **Given** the six models in the zoo (scout-large, sandbox-pipeline-tiny, hum-fan, pace-cnn, picket-forest, picket-mlp), **When** the audit runs, **Then** each gets a derived usage class (for example hum-fan: commercial, share-alike, from MIMII under CC BY-SA 4.0) or a finding that names the input that could not be resolved.
2. **Given** a release-record source whose licence is free text, **When** it maps to no entry of the licence list, **Then** the audit reports it as unresolved instead of guessing a class.
3. **Given** the website, **When** it is built after this feature, **Then** no zoo-wide text promises commercial use for every model, and every model page states its own usage class.
4. **Given** a published release whose derived class is more restrictive than its published licence, **When** the audit finds it, **Then** it is reported as a blocking finding for the next release and listed for an owner decision (deprecate and re-release under a new name, per Principle IX), and no published file is changed.

### Edge Cases

- A dataset with a non-commercial licence is declared `training_allowed` but `commercial_use: true`: the declaration is invalid; a non-commercial licence forces `commercial_use: false`.
- A non-commercial licence that permits reproduction but not adaptation (for example "non-commercial reproduction" terms of official publications): it is not a training licence for any model; only licences listed as permitting non-commercial training (CC BY-NC 4.0, CC BY-NC-SA 4.0 and others the owner adds after review) may train NC models.
- A model is declared non-commercial although all its inputs are commercial: allowed (a model MAY be more restrictive than its inputs); it must still carry `-nc` and the full marking, and the card says that the restriction is the owner's choice.
- A model changes usage class between versions: refused; a change of class is a new model with a new name (constitution, naming rule).
- A third-party model's card names no training data: its restriction follows the weights licence alone; the record says that no training data is named.
- A third-party model's weights licence is permissive but its card lists a non-commercial dataset among many: the restriction is non-commercial (training data governs).
- Evaluation only: a commercial model measured on a non-commercial benchmark keeps its class; the gate does not count `benchmark_only` sources as inputs.
- Spike models: never released (constitution), so the gate is not reached; the train check still applies the class rules to spike training data.
- A source licence is `unknown` or unresolved: fail closed for every model.
- The Hugging Face licence tag of an NC model is changed on the Hub after publication: the existing Hub drift check (C-L3) reports it.

## Requirements *(mandatory)*

### Functional Requirements

**Usage class**

- **FR-001**: Every model declaration MUST state a declared usage class: commercial or non-commercial, each with or without share-alike. The declared class is set by the owner before training.
- **FR-002**: The system MUST derive a usage class for each release from all of its inputs: declared training and fine-tuning datasets and sources marked `training_allowed`, the base model, teachers, third-party models loaded at run time, and data generated or labeled by zoo models. The derived class is the most restrictive combination of the inputs' restrictions.
- **FR-003**: Each licence that may appear on an input MUST be resolvable to known attributes: whether it permits training at all, whether it is non-commercial, whether it is share-alike, and which release licences satisfy it. Licences are resolved through the project's licence list; an input whose licence cannot be resolved MUST fail closed.
- **FR-004**: Inputs measured only (benchmark, agreement pilot, comparison baseline) MUST NOT count towards the derived class.

**Training and data**

- **FR-005**: A dataset or source under a licence that permits non-commercial training MAY be declared `training_allowed` with `commercial_use: false`. A non-commercial licence MUST force `commercial_use: false`. No-derivatives licences, unknown licences, "all rights reserved", platform terms that forbid training and opt-outs MUST stay `benchmark_only`, as today.
- **FR-006**: The train check MUST know the declared usage class of the model being trained. It MUST refuse training data with `commercial_use: false` for a model declared commercial, MUST accept it for a model declared non-commercial, and MUST refuse share-alike data when the declared class lacks share-alike. A training run with no declared target class MUST be treated as commercial.
- **FR-007**: Provider routes and teacher records MUST be able to say that training on outputs is permitted for non-commercial use only. Such a teacher makes the student non-commercial.
- **FR-008**: Data generated or labeled by a zoo model whose usage class is non-commercial MUST be recorded with `commercial_use: false` and the producing model, and MUST be treated as non-commercial input.

**Release gate**

- **FR-009**: The release gate MUST refuse a release whose declared usage class is less restrictive than the derived one, and MUST name every input that causes the difference with its licence.
- **FR-010**: The release gate MUST refuse a release whose licence does not satisfy the derived class: a non-commercial class needs a non-commercial licence; a share-alike class needs the share-alike licence its inputs require; inputs whose terms no single licence satisfies MUST be refused as a conflict.
- **FR-011**: The naming rule MUST require the suffix `-nc` (`<name>-<variant>-nc`) for a model declared non-commercial and MUST refuse it for a model declared commercial.
- **FR-012**: The usage class of a model MUST NOT change between versions; a change is refused and requires a new model name.
- **FR-013**: Every new release record MUST store the derived usage class, the release licence and the list of inputs that restrict it. Release records of versions published before this feature MUST stay unchanged and remain valid.

**Marking**

- **FR-014**: The model card MUST state the usage class and licence in its first lines. For a non-commercial model it MUST say "Non-commercial use only", name the licence and the inputs that make the model non-commercial (or that the owner chose the restriction), and the `## License` section MUST repeat this. For a share-alike model it MUST say that derivatives must keep the licence.
- **FR-015**: The Hugging Face front matter MUST carry the release licence as its licence tag; for a non-commercial model that tag MUST be a non-commercial licence identifier.
- **FR-016**: The website MUST show the usage class next to the licence on each model page and on the start page entry, and for a non-commercial model MUST state the restriction before the install line. Zoo-wide copy MUST NOT promise commercial use for every model. The site check MUST fail a model page that lacks its usage class.

**Third-party models**

- **FR-017**: The project MUST keep one register of third-party models with, per model: id, pinned revision, remote code repository and pinned commit if remote code is loaded, weights licence, the training data named on its model card with their licences, the derived restriction with its reason, where it is used, owner and review dates.
- **FR-018**: A model declaration's base model and every third-party model named in stage settings MUST be in the register with the same revision; a missing, unpinned or differing entry MUST fail the compliance check.
- **FR-019**: Where the weights licence of a third-party model is more permissive than the licences of its documented training data, the training data MUST govern the derived restriction.
- **FR-020**: A pipeline stage that loads a restricted third-party model MUST write the model and its restriction into the metadata of its output, and its documentation MUST state the restriction.

**Audit**

- **FR-021**: One command MUST report, offline, the declared and derived usage class of every model in the zoo with the determining inputs, and list unresolved licences, missing register entries and mismatches as findings. It MUST NOT modify any file.
- **FR-022**: The audit and the gate MUST share one derivation, so that both give the same class for the same inputs.

### Key Entities

- **Usage class**: commercial or non-commercial, each with or without share-alike; declared per model, derived per release.
- **Licence entry**: an identifier in the project's licence list with its attributes: permits training, non-commercial, share-alike, no-derivatives, and the release licences that satisfy it.
- **Third-party model record**: id, revision, remote code repository and commit, weights licence, named training data with licences, derived restriction and reason, used by, owner and review dates.
- **Restricting input**: an input of a release (dataset, source, base model, teacher, third-party model, zoo model output) together with the licence or terms that restrict it.
- **Release record** (extended): derived usage class, release licence, restricting inputs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A non-commercial fixture model passes the offline release gate, and "non-commercial" with the release licence and the restricting input appears in all four places a user looks: card top, Hugging Face licence tag, release record and website page.
- **SC-002**: For each of the five input kinds (dataset, base model, teacher, third-party run-time model, output of a non-commercial zoo model), a model declared commercial with one restricted input is refused, and the message names the input: 5 of 5.
- **SC-003**: Inputs that forbid training (no-derivatives, unknown, all rights reserved, platform terms, opt-out) are refused for commercial and for non-commercial models alike: every case covered by a test.
- **SC-004**: The audit gives a usage class or a named finding for all six models of the zoo, offline, in under one minute, and changes no file.
- **SC-005**: Every release made after this feature states its usage class in the release record, and the gate refuses a release record without one.
- **SC-006**: The website contains no zoo-wide promise of commercial use, and every model page shows its usage class; the site check enforces it.
- **SC-007**: Existing tests of commercial models keep passing, except where the audit finds a real gap; each such change is listed with its reason.

## Assumptions

- The licences that permit non-commercial training are, at the start, CC BY-NC 4.0 and CC BY-NC-SA 4.0. Other non-commercial terms (for example "non-commercial reproduction" of official publications) do not permit training until the owner reviews them and adds them to the licence list.
- Non-commercial models are not gated on Hugging Face; the restriction is carried by the licence and the marking. Gating stays out of scope.
- Code in the repository stays under Apache-2.0; usage classes apply to released weights and data.
- The declared class lives in the model declaration; the derived class is computed from the release record, the dataset declarations, the provider routes and the third-party register.
- Feature 009 adopts the third-party register and the output metadata rule (FR-018, FR-020) for its cluster settings on its own branch after this feature is merged; this feature registers the third-party models used on `main` (the base model of scout-large) and the four candidates of 009 so that its branch only has to reference them.
- Published releases are not changed. If the audit finds a published release whose licence is less restrictive than its derived class, the owner decides how to proceed (deprecation and re-release under a new name).
- No cash costs: all checks run offline; the Hub licence drift check stays as it is.

## Constitution Compliance

- **VI. Clean Provenance, Restrictions Carry Over**: this feature implements the usage class, the carry-over of restrictions, the NC training rule, the teacher and NC-output rules and the third-party register (FR-001–FR-008, FR-017–FR-020).
- **IX. Reproducible, Dated Releases**: marking of usage class and licence, NC licence, never less restrictive than the inputs, immutable published versions (FR-009–FR-016, FR-013).
- **Project Scope & Iterative Delivery**: naming rule `<name>-<variant>-nc`; a change of class is a new name (FR-011, FR-012).
- **Development Workflow & Quality Gates**: the gate before a release checks the usage class against the licence and covers third-party models (FR-009, FR-010, FR-018).
- **III. Measure Before Optimizing**: inputs used only to measure do not change the class (FR-004).
- Other principles are not touched.
