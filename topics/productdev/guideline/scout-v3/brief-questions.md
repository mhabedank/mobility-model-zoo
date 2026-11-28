# Questions for the owner's brief of guideline v3 (never sent to any model)

Date: 2026-11-27. Status: questions only, no answers yet. Written by Claude as development assistant (constitution XI). This file is **not** an input of the guideline writer, the teacher or any reference model. Its headings and wording must not reach them (cairn finding C1, 2026-10-22).

## How the brief is made

1. The owner answers the questions below in their own words: in chat or in a file, in any language, in any order. Questions may be skipped, merged or answered with "drop this field".
2. Each answer is copied **verbatim** into `brief.yaml` under an `owner` key. That file holds nothing else except machine keys: the field keys listed below and the value keys of the output schema. This is the pattern of `cairn-teacher-v1` (precedent 018 FR-006: code adds only machine-readable schema content).
3. A `brief-provenance.md` records who answered, when, which questions were asked (this file) and what was dropped. It is never sent to a model either.
4. A local non-Claude writer turns `brief.yaml` into guideline v3 and worked examples. The owner approves the result with hashes (`approval.json`). Only then does any labeling run.

Allowed seeds of the brief (owner decisions): the requirement lists of feature 001 T043/T044 (`D-xi-rewrite-requirements`), the requirement list of the [opportunity interface](../../research/opportunity-interface/README.md) (`D-xi-interface-requirements`), the qwen categories of the contested pilot-v1 entries and the GPT side of those pairs (`D-xi-contested-input`). Not allowed: guideline v1 and v2, examples and examples-v2, `revisions.md`, and any Claude reference label.

## Machine keys of `brief.yaml`

Existing keys of `jtbd-span-v1`, kept as keys only; their meaning comes from the owner's answers:

- `relevant`
- `kind`: `job`, `pain`, `gain`
- `actor_type`: `individual`, `worker`, `organization`, `public_sector`, `society`
- `evidence_type`: `opinion`, `anecdote`, `routine`, `observation`, `measurement`
- `evidence_scope`: `single`, `multiple`, `quantified`

New keys for the confirmed fields (provisional names until the `jtbd-span-v2` schema draft; the owner may rename them):

| Key | Field | Interface row |
|---|---|---|
| `job_kind` | kind of job | 3 |
| `executor_role` | span that names the role of the executor | 4 |
| `actor_pair` | two actors at a crossing, with the pain between them | 5 |
| `mode` | mode of transport | 6 |
| `situation` | span that states where and when | 7 |
| `improve` | what the actor wants to improve | 8 |
| `states_solution` | the item states a solution instead of a need | 9 |
| `means_end` | "in order to" link between two items | 10 |
| `order` | order of two items in one text | 11 |
| `language` | language of the text | 19 |

Value keys for `job_kind`, `mode` and `improve` are added once the owner has named the values.

## A. The task as a whole

- **A1** In a few sentences: what should the labeler do with a text? (In cairn this became `teacher_task`.)
- **A2** Which texts are in scope: what counts as mobility for you, and what is just next to it?
- **A3** Who should the labeler imagine as the reader of its result?

## B. Core items

- **B1 Relevance.** When does a text count as relevant? Which texts look relevant but are not?
- **B2 Item boundaries.** Where does an item start and end: part of a sentence, one sentence, several sentences? What do you do when one need is spread over several sentences, or one sentence holds two needs?
- **B3 Job.** When is something a job?
- **B4 Pain.** When is something a pain? How do you tell a pain from a gain that is said in the negative?
- **B5 Gain.** When is something a gain?
- **B6 Actor type.** What does each of the five values mean for you? Do you keep these five, now that the role of the executor gets its own span (C2)?
- **B7 Evidence type.** What does each of the five levels mean? Where are the borders between anecdote and routine, and between observation and measurement?
- **B8 Evidence scope.** What do single, multiple and quantified mean? What must a text say for "quantified"?
- **B9 Quotes.** The quote stays verbatim in the source language. Is anything allowed besides the quote? (The 001 list also had an English statement per item; under the interface rule "no generated text" it would be dropped. Do you agree?)
- **B10 Doubt.** What should the labeler do when it is unsure: about an item, about a level, about a field?
- **B11 Empty results.** When is an empty result right? Is "relevant, but no item" a valid case for you?

## C. New fields

For every field: when is it filled, which values does it have, when does it stay empty, and which case is hard to decide? An empty field is a correct answer; the questions on empty cases matter as much as the others.

- **C1 Kind of job** (`job_kind`). Which kinds do you distinguish? When is a job one kind and not the other? Can one item have more than one kind? Does the field apply to pains and gains as well, or only to jobs?
- **C2 Role of the executor** (`executor_role`). Which words in a text count as naming the role? How specific must it be to be marked? What if several roles are named?
- **C3 Actor pairs** (`actor_pair`). When are two actors "at a crossing"? Must the pain between them be stated, or is it enough that their goals clash? Which of the two items carries the pair?
- **C4 Mode of transport** (`mode`). Which values? How fine (bus versus public transport)? What about trips with several modes, and texts where the mode is only implied?
- **C5 Situation** (`situation`). Which words count as the situation: place, time, occasion, all of these? Must it belong to the same item, or may it be elsewhere in the text?
- **C6 What the actor wants to improve** (`improve`). Which values? What happens when an item names none, or several? Does this apply to jobs, pains, gains or all three?
- **C7 Solution instead of need** (`states_solution`). When does an item state a solution? Is the item then still labeled as job, pain or gain, or is it dropped?
- **C8 "In order to" links** (`means_end`). Which words or structures show that one item serves another? Must both items be from the same actor? What if the link is only implied?
- **C9 Order** (`order`). Which words show that one item comes before another? Which relations do you want besides before and after (at the same time, during)? Order across different texts is never extracted.
- **C10 Language** (`language`). Should the labeler state it, or does code detect it? What about a text that mixes languages?

## D. Worked examples

- **D1** Which real texts should the examples come from? (cairn used the owner's own decisions on real pairs.) Do you label the examples yourself, or does the writer draft them for your approval?
- **D2** Which cases must the examples show? The 001 list asked for at least six in German and English: a correct empty result, a near-miss, an item at measurement level and an item with several actors. Which cases do the new fields need (an actor pair, a means-end link, an order link, a solution, an empty field)?
- **D3** How many examples in all, and in which languages?

## E. After the brief

These are not part of the brief but must be decided before labeling:

- **E1** Writer model: a local non-Claude model with a clean licence.
- **E2** Agreement threshold per field and language for the pilot, fixed before the pilot runs.
- **E3** Which fields you would drop first if a pilot fails.

## Coverage

Every item of the allowed requirement lists has a question:

| Requirement | Source | Question |
|---|---|---|
| Domain definition | 001 T043 | A2 |
| Relevance rule with near-misses | 001 T043 | B1, D2 |
| Job, pain, gain; pain versus negated gain | 001 T043 | B3, B4, B5 |
| Five actor types | 001 T043 | B6 |
| Five evidence types with boundary rules | 001 T043 | B7 |
| Three evidence scopes | 001 T043 | B8 |
| Verbatim quote; English statement | 001 T043 | B9 |
| Take the lower grade when uncertain | 001 T043 | B10 |
| An empty result is valid | 001 T043 | B11 |
| Minimum IoU | 001 T043 | none: a scoring setting in the config, not a labeling rule |
| At least six examples with the named cases | 001 T044 | D1, D2, D3 |
| Rows 1, 2 (quote, kind) | interface | B2 to B5, B9 |
| Row 3 kind of job | interface | C1 |
| Row 4 role of the executor | interface | B6, C2 |
| Row 5 actor pairs | interface | C3 |
| Row 6 mode | interface | C4 |
| Row 7 situation | interface | C5 |
| Row 8 what to improve | interface | C6 |
| Row 9 solution instead of need | interface | C7 |
| Row 10 means-end links | interface | C8 |
| Row 11 order | interface | C9 |
| Row 18 calibrated confidence | interface | none: a model output, not a label |
| Row 19 language | interface | C10 |
| Rows 12 to 17, 20 to 22 | interface | none: cairn, survey or team, not scout |

Item boundaries (B2) are not in either list. They are added because the unit-level head of 0.2.0 depends on them.
