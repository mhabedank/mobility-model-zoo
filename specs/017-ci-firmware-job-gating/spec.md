# Feature Specification: Firmware jobs only for firmware-relevant changes

**Feature Branch**: `claude/speckit-specify-die-pipeline-c0136f`

**Created**: 2026-10-14

**Status**: Draft

**Input**: User description: "die pipeline scheint immer noch nicht richtig zu sein. ich habe die webseite aktualisiert, dennoch wird edge-qemu durchgeführt, das dürfte eigentlich nicht sein"

## Background

The CI already selects work per pull request from the files it changes (CI path gating). The two
firmware jobs, the native simulator run and the emulated ESP32 board run ("edge-qemu", up to
45 minutes), are meant to run only for firmware and edge changes.

Pull request #35 (feature 016, website imagery) still ran both firmware jobs. Diagnosis of that run:

- The pull request adds an optional, website-only dependency group to the project manifest and
  therefore also changes the lock file. Any change to either file is classified as "everything",
  which switches the firmware jobs on, although none of the packages the firmware jobs install
  changed.
- The pull request also extends the selection rules themselves. A change to the selection rules is
  classified as "everything" as well.
- After merge, every push to main runs everything by design, so the firmware jobs would run a
  second time for the same website change.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Website change with a new website-only dependency (Priority: P1)

The owner changes the website and, for that, adds a dependency that only the website tooling uses.
The pull request runs the checks every pull request runs and the website-related tests, but neither
firmware job.

**Why this priority**: This is the reported failure. It costs up to 45 minutes of runner time per
push, delays the pull request result and makes the owner distrust the path gating.

**Independent Test**: Replay the changed-file list and the dependency changes of pull request #35
through the selection; the result names no firmware job, and the website and imagery tests are
selected.

**Acceptance Scenarios**:

1. **Given** a pull request that changes website files and adds an optional dependency group used
   only by the website tooling, **When** CI selects the jobs, **Then** neither firmware job runs and
   the website tests run.
2. **Given** a pull request whose lock file change alters only packages outside the firmware jobs'
   install set, **When** CI selects the jobs, **Then** neither firmware job runs.
3. **Given** a pull request whose lock file change alters the version of any package the firmware
   jobs install, **When** CI selects the jobs, **Then** both firmware jobs run.
4. **Given** a pull request that changes the edge dependency groups or the firmware build
   dependencies in the manifest, **When** CI selects the jobs, **Then** both firmware jobs run.

---

### User Story 2 - Changes to the CI configuration and the selection rules (Priority: P2)

The owner adds a selection rule for a new folder, or edits a CI job that has nothing to do with
firmware. The firmware jobs run only when the change can affect them.

**Why this priority**: New features regularly add a folder and therefore a rule (feature 016 did).
Today every such pull request triggers the firmware jobs.

**Independent Test**: Select jobs for a pull request that only adds a selection rule, and for one
that only edits a firmware job definition; the first runs no firmware job, the second runs both.

**Acceptance Scenarios**:

1. **Given** a pull request that changes only the selection rules, **When** CI selects the jobs,
   **Then** the selection rules' own tests run, and each changed file is selected by the new rules
   as for any other pull request; the firmware jobs run only if those files require them.
2. **Given** a pull request that changes the definition of a firmware job, **When** CI selects the
   jobs, **Then** both firmware jobs run.
3. **Given** a pull request that changes a non-firmware part of the CI definition, **When** CI
   selects the jobs, **Then** the Python tests run and neither firmware job runs.

---

### User Story 3 - Merging to main does not re-run unrelated firmware jobs (Priority: P2)

After a website pull request is merged, the push to main runs the same selection a pull request
would, based on the changes since the previous main commit. A weekly scheduled full run and the
manual start remain the safety net for gaps in the rules.

**Why this priority**: Without it the owner sees the firmware jobs on main after every merge, which
is the same symptom one step later.

**Independent Test**: Merge a website-only change; the main run names no firmware job. Start the
pipeline manually or wait for the weekly schedule; that run includes both firmware jobs.

**Acceptance Scenarios**:

1. **Given** a merge of a website-only pull request, **When** the push to main triggers CI,
   **Then** the selection uses the changes since the previous main commit and no firmware job runs.
2. **Given** a push to main that contains several commits, **When** CI selects the jobs, **Then**
   the selection covers all changes between the previous and the new main head.
3. **Given** the weekly schedule fires, **When** CI runs, **Then** everything runs, including both
   firmware jobs.
4. **Given** the owner starts CI manually, **When** CI runs, **Then** everything runs.

---

### User Story 4 - The reason for each firmware run is visible (Priority: P3)

When a firmware job does run, the run summary states which changed file or which changed
dependency caused it.

**Why this priority**: The owner had to ask why edge-qemu ran. A visible reason makes a wrong rule
obvious at the first occurrence.

**Independent Test**: Run the selection for a firmware change and for a dependency change; the
summary names the triggering file or package in each case.

**Acceptance Scenarios**:

1. **Given** a run in which the firmware jobs are selected, **When** the owner opens the run
   summary, **Then** it names at least one triggering file or dependency and the rule that matched.
2. **Given** a run in which the firmware jobs are not selected, **When** the owner opens the run
   summary, **Then** it says that no firmware job was needed.

### Edge Cases

- The previous main commit cannot be determined (first push, force push, history rewrite): the run
  falls back to everything.
- The manifest or lock file cannot be compared (unreadable, conflicting, malformed): the firmware
  jobs run, failing safe.
- A pull request changes the selection rules and a firmware file at once: the firmware jobs run
  because of the firmware file.
- A shared package used by both the website tooling and the firmware jobs changes version: the
  firmware jobs run.
- A change to the build toolchain the firmware jobs use (emulator release, board definitions,
  firmware build configuration) runs the firmware jobs.
- A file no rule matches still runs everything, including the firmware jobs (unchanged behaviour).
- A shared runtime change (Python version pin, shared datasets package) still runs everything.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The selection MUST run the firmware jobs for a dependency change only when it alters
  the set or the versions of packages that the firmware jobs install.
- **FR-002**: The selection MUST treat a change to an optional dependency group as belonging to the
  area that uses that group, and MUST NOT run the firmware jobs for groups they do not install.
- **FR-003**: A change to the selection rules MUST run the selection rules' own tests and MUST NOT by
  itself run the firmware jobs.
- **FR-004**: A change to the CI definition MUST run the firmware jobs only when a firmware job's
  definition, or something every job shares, changes.
- **FR-005**: A push to main MUST be selected from the changes between the previous and the new main
  head, with the same rules as a pull request.
- **FR-006**: CI MUST run everything on a weekly schedule and on manual start.
- **FR-007**: When the comparison base or a dependency comparison is not available, the selection
  MUST fall back to running the affected jobs (fail safe), never to skipping them.
- **FR-008**: The run summary MUST name, for the firmware jobs and for each selected area, the
  triggering files or dependencies and the matching rule.
- **FR-009**: The selection's tests MUST cover the pull request #35 case as a regression case: a
  website change plus a website-only dependency group selects no firmware job.
- **FR-010**: The existing guarantees MUST stay: every tracked file has a rule; unmatched files run
  everything; edge and firmware file changes run both firmware jobs.
- **FR-011**: The project documentation of the CI selection MUST describe the dependency rule, the
  main-branch selection and the weekly full run.

### Key Entities

- **Firmware install set**: the packages and tools the two firmware jobs install; the basis for
  deciding whether a dependency change matters to them.
- **Selection area**: a group of files with the tests and jobs they need; extended so a dependency
  group can belong to an area.
- **Selection reason**: per selected job or area, the files or dependencies and the rule that caused
  it, shown in the run summary (called `Finding` in the data model).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Replaying pull request #35 through the selection runs 0 firmware jobs (today: 2).
- **SC-002**: A website-only change, from pull request to merge, runs 0 firmware jobs in total
  (today: 4, two on the pull request and two on main).
- **SC-003**: Over the last 20 merged pull requests that touched no firmware, edge or shared runtime
  file, replaying the selection runs the firmware jobs for none of them.
- **SC-004**: Every pull request that changed firmware, edge files or the firmware install set in
  the last 20 merged pull requests still selects both firmware jobs when replayed (no lost coverage).
- **SC-005**: For every run that executes a firmware job, the first line of the run summary names
  the triggering file or dependency, so the owner needs no log to find the reason.
- **SC-006**: Each week has at least one full run including both firmware jobs.

## Assumptions

- The weekly full run is sufficient as a safety net against gaps in the selection rules; a defect a
  narrowed main run misses is found within 7 days.
- The weekly full run goes to the owner through the usual failure notification of the repository;
  no new notification channel.
- Runner time on the public repository costs no money, but job time delays results and counts
  against the project's resource discipline; the aim is speed and signal, not cost.
- The firmware install set is derived from what the firmware jobs install today (the base
  dependencies, the edge and firmware hardware dependency groups and the default development group,
  with the deep-learning framework excluded); an automated check keeps it equal to the firmware jobs'
  install steps.
- Other workflows (site deployment, firmware release, HIL, datasets) filter their own paths and are
  out of scope.
- Pull request #35 stays as it is; this feature changes the selection, not that pull request.

## Constitution Compliance

Constitution 3.0.0. This feature changes CI tooling only.

| Principle / section | Touched? | How the spec complies |
|---|---|---|
| I, II, VII, VIII (task modelling) | no | no model, data or label work |
| III Measure Before Optimizing | yes | the change rests on a measured defect (CI run 38504807495) and is accepted by replaying 20 merged pull requests (SC-003, SC-004) |
| IV Validate the Riskiest Assumption First | yes | the riskiest assumption (a website-only dependency leaves the firmware install set unchanged) is checked on the real files of pull request #35 before design |
| V Small and Local by Default | yes | no new dependency or service |
| VI Provenance, IX Releases | no | release workflows and gates unchanged |
| X Scope Discipline | yes | other workflows are out of scope (Assumptions) |
| XI No Claude in Model Learning or Extraction | no | no learning, labeling or extraction; Claude Code only develops tooling |
| Resources & Cost Discipline | yes | fewer runs of the up-to-45-minute emulated-board job on GitHub CI runners; no cash costs, no budget needed |
| Development Workflow & Quality Gates | yes | this section and the plan's Constitution Check list the touched principles |
