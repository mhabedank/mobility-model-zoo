# Feature Specification: Model pages leave the site-wide size total

**Feature Branch**: `024-model-page-budget`

**Created**: 2026-10-22

**Status**: Draft

**Input**: Follow-up from feature 023, which raised the site-wide total rather than answering why
it was full.

## Context

Feature 023 raised S1's site-wide total from 300 KB to 320 KB because the identity swap needed
more tokens than the one it replaced and the total had 190 bytes of headroom left. That was the
right call for the moment and the wrong answer to the question underneath it.

The question is what the total is for. It is not a load-time guard: no visitor loads the whole
site, and what a reader waits for is guarded per page by S2 (Largest Contentful Paint under Fast
3G throttling), S4 (bytes transferred) and the 150 KB per-page limit. The total is a guard
against creeping growth.

That only works while the site's size is roughly fixed. It is not. Measured at three published
models, a model page averages 51 KB, and the roadmap carries eleven more. Those models alone
would put the total near 870 KB. A limit that has to move every second model has stopped
measuring anything.

Nor is the weight fat to be trimmed. What makes a model page heavy is the record itself: the
metrics tables and the release history with its change descriptions, at about 286 bytes a row
because those rows carry prose. Cutting it means publishing less, which is the opposite of what
the project promises.

The project already solved this shape of problem. Feature 022 took the field notes out of the
site-wide total because they grow with every post, and gave them their own budget. Model pages
grow with every model and again with every release. They get the same treatment.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A reader waits no longer than before (Priority: P1)

A visitor opens the heaviest model page on a mobile connection and sees its main content within
two seconds, exactly as before this change.

**Acceptance**: The per-page guards are untouched. Model pages keep the 150 KB limit, S4 and S2.

### User Story 2 - The catalogue grows without a budget argument (Priority: P1)

Eleven more models ship over the roadmap. No release is blocked by a limit that measures the
whole catalogue rather than any page a reader opens.

**Acceptance**: The site-wide total does not grow with the number of models.

### Edge Cases

- A model page that genuinely becomes too heavy: the 150 KB per-page limit still catches it. The
  heaviest today is at 60 KB, which leaves room for roughly 150 further release rows.
- A future page type that also grows with content: `grows_with_content` is the one place to say
  so, rather than another exclusion scattered through the total.

## Requirements *(mandatory)*

- **FR-001**: Model pages MUST be excluded from S1's site-wide total.
- **FR-002**: Model pages MUST keep the per-page limit unchanged. The exclusion is from the total
  only.
- **FR-003**: The site-wide total MUST return to 300 KB, reversing the raise of feature 023.
- **FR-004**: The reason MUST live next to the code, so that the next change to the number starts
  from the reason rather than the number.
- **FR-005**: The feature 008 identity sheet MUST be marked superseded, and the stylesheet headers
  MUST stop naming it as their source, because since feature 023 that is false.

## Success Criteria *(mandatory)*

- **SC-001**: The site-wide total is under 300 KB and does not grow when a model is added.
- **SC-002**: Every per-page guard still passes, the browser load-time run included.
- **SC-003**: No file claims the identity comes from a document that no longer describes it.

## Constitution Compliance

- **IX, Reproducible, Dated Releases**: Publishing a release adds rows to a model page. This
  change removes a limit that would have made that an argument about bytes rather than about the
  release.

## Out of Scope

- Reducing what a model page says. The weight is the record, and the record is the point.
- The explainer graphics for social posts, whose data inks are documented in tokens but have no
  pipeline in this repository yet.
