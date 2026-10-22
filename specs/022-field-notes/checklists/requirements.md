# Specification Quality Checklist: Field notes, a long-form page type for the website

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-22
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

The specification was written from a working proof of concept rather than ahead of one, so the
requirements describe behaviour that has already been observed. The risk that carries is the
opposite of the usual one: not vagueness, but a specification that quietly records the first
implementation's choices as if they were decisions. Two places were kept free of it on purpose.
The marker syntax for diagrams and citations is not named, because the requirement is that a note
can place a drawing and cite a source, not how the characters look. The byte budget for a note
carries no figure, because the number belongs in the plan and has to be measured from part one.

One judgement call is recorded rather than resolved. The Context and Assumptions sections name
files and principles of this repository, which a spec template would normally keep out. That is
deliberate here: the reader of this spec is the owner of the repository, and the constitution
requires every spec to state how it sits against the principles it touches.

No clarification markers were needed. Four decisions that would otherwise have become markers were
answered by the owner before the spec was written and are recorded in Assumptions: notes get their
own byte budget and leave the site-wide one, part one ships with a borrowed lead image, the section
is called Field notes at `/notes/`, and the work goes through a specification rather than straight
to main.

One requirement and one success criterion were removed after a first draft. Both turned on the page
announcing that it is not a model card. The owner's objection was that a reader does not need to be
told, and it reads as padding. The separation is now carried by the page itself rather than by a
disclaimer on it.
