# Feature Specification: Quickstart that works from a fresh install

**Feature Branch**: `013-fresh-install-quickstart`

**Created**: 2026-10-11

**Status**: Draft

**Input**: User description: "Quickstart that works from a fresh install. Every published model must be usable by following its model card alone, from a fresh Python environment, without the zoo repository, a C compiler or guesswork. [...] Done when: picket-forest 0.2.1 and scout-large 0.1.3 are published with cards whose how_to_run passes in the fresh-venv gate, and a newcomer on macOS or Linux with Python 3.12 and uv reaches a printed result for both models within five minutes by following only the card."

## Context

On 2026-10-11 the owner followed the published model cards of picket-forest v0.2.0 and scout-large
v0.1.2 as a newcomer would: a fresh folder, the install line from the card, the run snippet pasted
into an interpreter. Five things went wrong, and together they made the demo a "pain":

1. The install line is refused on Python 3.11 with a bare version error. Neither the card nor the
   website says that Python 3.12 is required.
2. The install line of picket-forest does not install three libraries its run snippet imports, while
   it does install a deep-learning stack of 877 MB that a random-forest model never uses.
3. The Python reference of picket-forest compiles C sources that only exist in the repository
   checkout, so after a plain install the snippet stops with "file not found" even once every
   library is present.
4. The run snippet names two inputs (`benign_captures`, `capture`) that it never defines, and the
   model repository holds no example capture, although three synthetic captures exist in the
   registry and the release's calibration table is published only as a C header.
5. Nothing in the release pipeline catches any of this: the gate's fresh-environment check installs
   the package without the extras the card names, and for microcontroller models it never runs the
   snippet at all.

scout-large's card was verified to work from a fresh Python 3.12 environment; its only obstacle
was the undocumented Python requirement.

The Python requirement statement (card template, website quickstart, golden files) is already
implemented in the working tree of this branch and is part of this feature.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run picket-forest from its card alone (Priority: P1)

A newcomer with Python 3.12 and uv on macOS or Linux opens the picket-forest model card, creates a
fresh environment, runs the install line, pastes the run snippet into a script and runs it. The
snippet downloads an example capture and the calibration table from the model repository, scores
the frames and prints the forest scores and alarms. Nothing else is needed: no repository checkout,
no C compiler, no variable the newcomer has to invent.

**Why this priority**: This is the broken path. Today the card cannot be followed to a result, which
makes the published model unusable for anyone outside the project.

**Independent Test**: In a fresh environment, run the card's install line and its run snippet
unchanged; the printed output equals the example output shown on the card.

**Acceptance Scenarios**:

1. **Given** a fresh Python 3.12 environment on a machine without a C compiler, **When** the newcomer
   runs the install line and the run snippet of the card as pasted, **Then** the snippet prints the
   scores and alarms of the example capture and exits without error.
2. **Given** the same environment, **When** the install completes, **Then** no deep-learning framework
   was downloaded and the installed size is a fraction of today's 877 MB (see SC-002).
3. **Given** the card's second snippet and a benign candump log of the newcomer's own vehicle,
   **When** the newcomer runs it, **Then** it produces a calibration table that the first snippet
   accepts in place of the published one.
4. **Given** the printed scores and alarms of the example capture, **When** they are compared with
   the device chain's output for the same frames, **Then** every score and every alarm is identical.

---

### User Story 2 - The gate refuses a card that cannot be followed (Priority: P1)

Before a release, the gate builds a fresh environment from the card's own install line, including
the extras it names, runs the card's snippet there and records its output as the card's example
output. A snippet that fails for any reason (a missing library, a resource only found in the
repository, an undefined name, a wrong revision) blocks the release with a message that names the
failure. This applies to every model, microcontroller models included.

**Why this priority**: Without this, the next card breaks just as silently. The fix for User Story 1
is only durable if the pipeline enforces it.

**Independent Test**: Give the gate a card whose snippet imports a library the install line does not
provide; the gate fails and names the import. Repeat with a snippet that reads a repository-only
file and with one that uses an undefined name.

**Acceptance Scenarios**:

1. **Given** a model whose install line names an extra, **When** the gate runs, **Then** the fresh
   environment contains exactly what that install line installs, and nothing from the developer's
   environment.
2. **Given** a microcontroller model, **When** the gate runs, **Then** its run snippet is executed in
   the fresh environment like a text model's, and its output appears on the card.
3. **Given** each of the five failures observed on 2026-10-11, reproduced as a test card, **When**
   the gate runs, **Then** it fails and its message names the failing step.
4. **Given** a snippet that passes, **When** the card is built, **Then** the card shows the snippet's
   printed output next to it.

---

### User Story 3 - Small installs, one extra per model kind (Priority: P2)

A user who installs an edge model gets the numeric libraries that model needs and nothing else; a
user who installs a text model gets the text stack. Each card's install line names exactly the
extra its snippet needs, and the base install is small.

**Why this priority**: A 877 MB download for a random-forest model is the second thing a newcomer
notices, and it makes the five-minute goal impossible on an ordinary connection.

**Independent Test**: Install from each published card's install line into a fresh environment and
measure the download size and the set of installed libraries.

**Acceptance Scenarios**:

1. **Given** the picket-forest install line, **When** it is run, **Then** no deep-learning framework
   is installed and every library the run snippet imports is present.
2. **Given** the scout-large install line, **When** it is run, **Then** the text stack is installed
   and the run snippet works as before.
3. **Given** the base install without extras, **When** it is run, **Then** it is smaller than any
   model's install and contains only what every model shares.

---

### User Story 4 - Try it in five minutes (Priority: P2)

A newcomer who has never used the zoo finds a short quickstart on the website and in the
repository README: create an environment with Python 3.12, install one model, run one script, see
the output. The guide names the pitfalls that cost the owner an hour: an interpreter from another
environment answering instead of the fresh one, no `pip` inside environments created by `uv`,
`import` typed into a shell instead of Python. The Python requirement is stated on every card and on
every website model page, next to the install line.

**Why this priority**: The cards alone are terse by design; a newcomer needs one page that walks
them through the environment part, which is the same for every model.

**Independent Test**: A person who has not seen the project follows the quickstart on a clean
machine and reports the time to the first printed result.

**Acceptance Scenarios**:

1. **Given** the website or README, **When** the newcomer follows the quickstart for picket-forest
   and for scout-large, **Then** each reaches a printed result within five minutes (SC-001).
2. **Given** any model card or website model page, **When** the newcomer looks at the install step,
   **Then** the Python requirement is stated there.
3. **Given** a machine with Python 3.11 as default, **When** the newcomer follows the quickstart,
   **Then** the quickstart's first step gives them a Python 3.12 environment before the install.

---

### User Story 5 - Patched releases of both models (Priority: P3)

picket-forest 0.2.1 and scout-large 0.1.3 are published through the pipeline with cards whose
snippets passed the new gate. picket-forest 0.2.0, whose card cannot be followed, is marked
deprecated in favour of 0.2.1. The models themselves are unchanged: same weights, same thresholds,
same device code.

**Why this priority**: The published cards are what users see; the fix is only visible once a new
version carries it. Last because it depends on everything above.

**Independent Test**: The published cards of 0.2.1 and 0.1.3 show the new install line, the Python
requirement, a complete snippet and its output; following them from a fresh environment works.

**Acceptance Scenarios**:

1. **Given** the release pipeline, **When** picket-forest 0.2.1 is released, **Then** its model
   repository contains the example captures and the calibration table the snippet downloads, and
   its weights and device headers are identical to 0.2.0's.
2. **Given** picket-forest 0.2.0 after the release of 0.2.1, **When** a user opens its card,
   **Then** a banner says it is deprecated and points to 0.2.1.
3. **Given** scout-large 0.1.3, **When** a user opens its card, **Then** the install line names the
   text extra, the Python requirement is stated, and the snippet is unchanged otherwise.

### Edge Cases

- Python 3.11 or older: the install line is still refused by the installer; the card and the
  quickstart name the requirement so the user knows why before trying.
- No C compiler on the user's machine: the run snippet works regardless. A compiler is needed only
  by developers who build the device code or run the parity test.
- Offline after the install: the snippet needs the model repository for the example capture, the
  table and the model; it fails with the download error, not with a confusing one later.
- A capture that contains identifiers absent from the calibration table: the snippet reports them
  as unknown-identifier events, as the device does; this is documented on the card as expected.
- An older published version (picket-forest 0.2.0) keeps its original card; published versions are
  immutable. It is deprecated, not rewritten.
- The gate runs without network access to the Hub (its offline mode): the fresh-environment run is
  skipped there as the other Hub-dependent checks are, and the release pipeline, which has access,
  runs it.
- A card's install line names an extra that does not exist: the gate fails at the install step
  with the installer's message.
- A text model whose snippet takes longer than the gate's time limit: the gate fails with a
  timeout message naming the limit; the limit stays as today (ten minutes).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every model card and every website model page MUST state the Python version the
  install line needs, next to the install line, derived from one source so that the two cannot
  drift apart.
- **FR-002**: The install line of every card MUST install everything its run snippet imports, and
  nothing a model of another kind needs: the install line of an edge model MUST NOT install a
  deep-learning framework, and the base install MUST contain only what every model shares.
- **FR-003**: The Python reference of picket-forest (calibrated features, rules, alarm stage and
  forest score) MUST run after a plain install, without the repository and without a C compiler.
- **FR-004**: The Python reference MUST produce the same scores and alarms as the device chain,
  frame by frame, on every capture of the existing parity test and on the example captures; the
  parity test MUST prove this and remain part of the gate for picket-forest.
- **FR-005**: The model repository of picket-forest MUST contain at least three example captures
  (synthetic, as the registry's examples are) and the release's calibration table in a form the
  Python reference reads directly.
- **FR-006**: The run snippet of every card MUST be complete: it defines or downloads every input it
  uses, and running it as pasted prints a result. picket-forest's snippet MUST download an example
  capture and the calibration table from the model repository, score the capture and print the
  scores and alarms.
- **FR-007**: picket-forest's card MUST carry a second snippet that builds a calibration table from
  the user's own benign candump log in the format the card already names, and that table MUST be
  usable in place of the published one.
- **FR-008**: The release gate MUST execute the run snippet of every model, microcontroller models
  included, in a fresh environment built from the card's own install line including its extras,
  with no access to the developer's environment or repository checkout.
- **FR-009**: A run snippet that does not exit successfully in that environment MUST block the
  release, and the gate's message MUST name the failing step (install, download or run) and the
  last lines of the error.
- **FR-010**: The printed output of a passing run snippet MUST appear on the card as the example
  output, as it does for text models today.
- **FR-011**: The five failures observed on 2026-10-11 (missing Python requirement, missing library
  in the extra, repository-only resource, undefined name, snippet never run for a microcontroller
  model) MUST each be covered by a test that shows the gate rejecting them.
- **FR-012**: The website and the repository README MUST carry a quickstart that takes a newcomer
  from no environment to a printed result for one model, names the Python requirement, uses the
  environment tool the project recommends, and names the pitfalls observed: an interpreter from
  another environment, no `pip` inside `uv` environments, and Python typed into a shell.
- **FR-013**: picket-forest 0.2.1 and scout-large 0.1.3 MUST be released through the pipeline with
  cards that passed the new gate; their weights, thresholds and device artefacts MUST be identical
  to 0.2.0 and 0.1.2 respectively.
- **FR-014**: picket-forest 0.2.0 MUST be marked deprecated in favour of 0.2.1 after that release;
  scout-large 0.1.2, whose card works, stays as it is.
- **FR-015**: Nothing in this feature MAY change a model's behaviour, its device code or the
  release's quality and performance results.

### Key Entities

- **Model card**: the published description of one model version; for this feature its install
  line, the Python requirement, the run snippet(s) and the recorded example output.
- **Install line**: the one command that installs a model's software; names the extra its snippet
  needs.
- **Run snippet**: the pasted-as-is program on the card; complete, with every input defined or
  downloaded.
- **Example capture**: a short synthetic CAN capture with expected scores and alarms, redistributed
  in the model repository so the snippet has input.
- **Calibration table**: the per-vehicle table the picket-forest rules use; published with the
  release in the device's header form and in a form the Python reference reads.
- **Fresh environment**: an environment the gate builds from the install line alone, with nothing
  from the developer's machine, in which the snippet must run.
- **Quickstart**: the one-page guide (website, README) from no environment to a printed result.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A newcomer with Python 3.12 and uv on macOS or Linux, on an ordinary broadband
  connection, reaches a printed result for picket-forest within 5 minutes and for scout-large
  within 5 minutes, following only the quickstart and the card.
- **SC-002**: The install of picket-forest from its card is under 300 MB installed (macOS about 150 MB,
  Linux about 240 MB; today: 877 MB) and installs no deep-learning framework.
- **SC-003**: On every parity capture and every example capture, the Python reference and the
  device chain disagree on 0 scores and 0 alarms.
- **SC-004**: 100 % of published cards have a run snippet that passed in the gate's fresh
  environment; a card whose snippet fails cannot be published.
- **SC-005**: Every published card and website model page states the Python requirement next to the
  install line; no run snippet on a published card uses a name it does not define or download.
- **SC-006**: Each of the five failures of 2026-10-11, replayed as a test, is rejected by the gate.
- **SC-007**: The owner's demo of both models, repeated from a fresh folder, succeeds at the first
  attempt.

## Assumptions

- Newcomers use `uv` as the quickstart recommends; the quickstart also names the standard
  `venv` + `pip` route in one line for those who do not.
- The three synthetic example captures in the registry are redistributable (their source record
  says `synthetic`) and small enough (about 200 KB each) for the model repository.
- The calibration table published with picket-forest 0.2.0 is the one compiled into its
  `picket_forest_table.h`; 0.2.1 republishes the same table in both forms.
- The candump format for the user's own calibration is the one the card already names
  ("benign candump logs"); one common log format is enough for the second snippet.
- scout-large's text stack moves from the base install into an extra, and its install line names
  that extra; the base install keeps only what every model shares.
- A C compiler stays a developer requirement for building device code and running the parity
  test; it is never a user requirement.
- The gate's existing time limit for a snippet (ten minutes) and its offline mode stay as they are.
- The fresh-environment check installs from the local checkout under gate with the extras the card
  names, which is equivalent to the git-tag install line once the tag exists; the release pipeline
  runs the same check on the tag.
- Deprecating picket-forest 0.2.0 follows the constitution's rule that a broken version is marked,
  never rewritten; the device artefacts of 0.2.0 remain valid, only its card cannot be followed.
- Publishing to a package index stays out of scope; the install line keeps pointing at the git tag.

## Constitution Compliance

- **Principle III (Measure Before Optimizing)**: the Python reference is a second implementation of
  the device chain; its bit-exact agreement with the device chain is a deterministic check (FR-004,
  SC-003) and stays part of the gate.
- **Principle V (Small and Local by Default)**: the install of an edge model shrinks to what it
  needs (FR-002, SC-002); no hosted service enters the run path.
- **Principle VI (Clean Provenance)**: only synthetic example captures are redistributed (FR-005);
  no dataset content enters the model repository.
- **Principle IX (Reproducible, Dated Releases)**: published versions stay immutable; the fix is a
  new version (FR-013), the broken card is deprecated (FR-014); both patches go through the release
  pipeline and the gate, and the owner approves the cards.
- **Development Workflow & Quality Gates**: the gate before a release gains the fresh-environment
  run (FR-008, FR-009); every model is checked the same way (Tasks and Releases: one gate for all).
- **Principle X (Scope Discipline)** and **FR-015**: no model behaviour changes.
