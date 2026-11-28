# Changes after Fable review 2

Date: 2026-11-28. Basis: `fable-review-2.md` (sections 4, 5 and 7) and the owner's decisions recorded in `../brief-provenance.md`: all 10 questions of section 6, option (a) each time. Also applied as drafts, on the strength of the reviewer's verdicts on the applying agent's points: M-9, M-10, `reader_en`, a non-printed note on R-24, and the e05 text is kept. Drafted by Claude under constitution 3.2.0. Every wording below is a Claude draft and is not valid before the owner approves it. No file under `data/` was read, no real text was labeled and no model output was judged; all example texts are invented.

Files changed: `../brief.yaml`, `../examples.yaml`, `../check_examples.py`. New: this file.

The key texts in sections 1 and 6 are copied from `brief.yaml` by script, so they match the file exactly. Owner answers (`owner`, `*_choice`, `cases_owner`, `teacher_task`, `reader`) are untouched; a script compared all 13 of them with the last commit.

## 1. Changed and new keys of `brief.yaml`

Each entry is one changed or new key, with its new full wording. Every top-level key that contains a change carries `drafted_by: claude` and `approval: pending`; where a `previous_approval` existed it is kept. No key was removed.

### `reader_en.text` (new)

Implements: agent point 5 (N-21, R-20 rest). English operative version of the owner's German `reader`, which stays verbatim and is now on the list of keys the template does not print (see `assembly.rule`).

Approval: pending.

> A product manager.

### `item_boundaries.rule` (changed)

Implements: M-3 (N-04). Four sentences inserted after "… unless it is a need of its own"; "Two needs joined by 'and' are two items" replaced.

Approval: pending.

> An item is one need. Its quote is the shortest run of whole clauses that states the need, including the words that mark it as a wish, fear or problem (such as 'I want', 'schön wäre', 'I worry that') and the conjunction that opens a clause. A need may run over several sentences. A cause or consequence joined with 'so', 'because', 'weil' or 'sodass' belongs to the same item unless it is a need of its own. It is a need of its own when it names another burden or another actor than the clause before it. A purpose joined with 'um … zu', 'damit', 'in order to' or 'so that' is an item of its own, and so is the clause it depends on. The opening conjunction may be of either kind ('und', 'aber', 'dass', 'and', 'but', 'that'). A frame that only says who said it ('Viele sagen mir, dass', 'People tell us', 'ich schätze') stays outside the quote; a source named inside the clause ('laut der Erhebung') and a verb that itself states the problem ('complain', 'sich beschweren', 'worry') stay inside. Two clauses joined by 'and' are two items when they name different burdens or actors. Quotes of one text never overlap. Offsets are computed by code.

### `relevant.definition` (changed)

Implements: M-9 (N-11, R-15 rest, agent point 1). Domain test per item appended at the end.

Approval: pending (previous: owner, 2026-11-28, in chat).

> A text is relevant when it states at least one job, pain or gain of an actor within mobility as defined under domain, told by the actor or reported by someone else. The topic alone is not enough. Not relevant: texts that only report facts, figures, events or product features with no actor who wants to get something done, struggles, hopes for something or values an outcome they have; timetables, tariffs and technical specifications; a provider praising its own offer without reporting a customer's need; texts where mobility is only the backdrop of something else. One passage with a need is enough, even if the rest of the text is off-topic. The test applies to each item: the need, or the trip or transport on which it arises, must lie within mobility. What a mobility problem does to the actor (being late for work, feeling cut off) is an item. A need about something else that is only mentioned on the way is no item.

### `kind.job_versus_gain` (changed)

Implements: M-4 (N-05); decisions 3 and 4. Three sentences appended.

Approval: pending (previous: owner, 2026-11-28, in chat).

> A job is what the actor wants to get done: it has its own verb of doing and stays the same when the means change. A wish about how well, fast, cheaply, safely or reliably it goes is a gain. A sentence that only reports what someone does, with no want, purpose, obstacle or judgement, is not an item. This test decides, whatever word the text uses ('goal', 'Ziel', 'need'). A step the actor takes for a stated purpose is a job and is linked to its goal with means_end. A wish for a thing or measure is a gain with states_solution true, also when it has a verb of doing ('order', 'build', 'introduce').

### `kind.feelings` (changed)

Implements: M-5 (N-06); decision 6. Replaced.

Approval: pending (previous: owner, 2026-11-28, in chat).

> A bad feeling reported as a fact is a pain, a good one a gain. A wish to feel or not to feel something is a job with job_kind emotional, also when it is about how the trip goes; this rule comes before job_versus_gain.

### `actor_type.society` (changed)

Implements: M-6 (N-07); decision 5. Replaced.

Approval: pending (previous: owner, 2026-11-28, in chat).

> The public at large, only when the text says so in words ('alle', 'everyone', 'die Allgemeinheit', 'the public'). The people of a place and generic 'man', 'one' or 'you' are individual.

### `evidence_type.boundaries` (changed)

Implements: M-1 (N-01, N-08); decisions 1 and 2. The first four sentences are replaced by the ordered test; the sentences on anecdote versus routine and on estimates stay.

Approval: pending (previous: owner, 2026-11-28, in chat).

> Grade by the basis the speaker gives, and take the first line that fits. 1. A counted or measured figure with its source: measurement. 2. One concrete event, whoever it happened to and whoever told it: anecdote. 3. The speaker's own repeated experience, shown by a word of frequency, by habitual present tense about the speaker's own trips ("I take", "wenn ich … muss") or by a share of the speaker's own attempts: routine. 4. A statement about several other people or a longer time, when the text says how the speaker knows it (they were told, or they were there) or gives an estimated figure: observation. 5. Everything else, including a plain statement of how things are ("the bus runs twice a day"): opinion. Anecdote versus routine: one event is an anecdote; words of frequency or several events make it routine. Observation versus measurement: a measurement needs a figure that was counted or measured; an estimate such as "about half, I would say" is an observation, or routine when it is a share of the speaker's own repeated experience.

### `evidence_type.reported_speech` (changed)

Implements: M-1 (N-01); decision 1. Text replaced by the M-1 definition of the speaker. The key name `reported_speech` is kept so that the checker and any reader of the old key still find it.

Approval: pending (previous: owner, 2026-11-28, in chat).

> The speaker is the person or body whose statement the text gives: the author of a first-person text, or the person a news text or minutes quote. A journalist or minute-taker who only passes a statement on is not the speaker. What third persons told that speaker is graded from the speaker's side, as below.

### `evidence_scope.quantified` (changed)

Implements: M-11 (N-16). One sentence appended.

Approval: pending (previous: owner, 2026-11-28, in chat).

> The text gives a number or share of the actors or occurrences that have the need, such as people, trips, tours or complaints; an estimate with a figure counts. Durations, distances, prices, times of day and the size of an operation do not count. A share counts when it is a share of people or events; a share of a stock, such as posts or vehicles, is the size of the problem.

### `doubt.fields` (changed)

Implements: M-10 (N-12, R-22 rest, agent point 2). Replaced.

Approval: pending (previous: owner, 2026-11-28, in chat).

> job_kind, mode, improve, executor_role and situation stay empty when they are not stated or you are unsure; an empty field is correct. kind, actor_type, evidence_type and evidence_scope are never empty: use the rules for kind and levels above, and for actor_type take the type of the persons the need is about.

### `executor_role.rule` (changed)

Implements: M-8 (N-10). Three sentences inserted after "A role named for the same actor applies to all of that actor's items", so that the priority rules follow the rule they refine; generic words now "I", "we", "people", "members" or "Leute".

Approval: pending (previous: owner, 2026-11-28, in chat).

> A pointer to the noun phrase, without article, with the modifiers that define the role, that names who has the need: what the person or body is, such as an occupation, a life situation or an organisation type. The pointer must lie in the text the labeler is given, inside or outside the item's quote. If the same words occur more than once, the occurrence inside the quote counts, else the one nearest before it; code resolves offsets. A role named for the same actor applies to all of that actor's items. A role named inside the quote comes before a role named elsewhere for the same actor. If the words occur only after the quote, the nearest occurrence after it counts. A speaker tag counts as a role only when it names the actor itself and the running text names none. Pronouns and generic words such as "I", "we", "people", "members" or "Leute" get no role. If several roles are named, take the one that has this need. Empty if no role is named.

### `mode.rule` (changed)

Implements: M-11 (N-18). One sentence on verbs inserted before "Empty if the quote names no mode".

Approval: pending (previous: owner, 2026-11-28, in chat).

> All modes named in the item's quote, as a list. Decide on the words of the quote: every mode named counts, also when it is negated or missing. Use public_transport when the text names public transport without a mode. A word that belongs to exactly one mode counts, such as a bus driver for bus or a wallbox for car. A verb counts when it belongs to one mode (walk, cycle, fly, drive for car); 'fahren', 'ride' and 'travel' name none. Empty if the quote names no mode; do not infer one from the context alone.

### `situation.rule` (changed)

Implements: M-7 (N-09); decision 7. "without article or preposition" becomes "without article, possessive, demonstrative or preposition"; four sentences inserted before "Not a situation: …".

Approval: pending (previous: owner, 2026-11-28, in chat).

> A pointer to the noun phrase (or time word), without article, possessive, demonstrative or preposition, with the modifiers that define where, when or on what occasion the need arises: a place, a time of day, week or year, or an occasion such as a trip purpose or what the actor carries. The pointer must lie in the text the labeler is given, inside or outside the item's quote. If the same words occur more than once, the occurrence inside the quote counts, else the one nearest before it; code resolves offsets. Place before occasion before time when several are tied to the need. A place, time or occasion counts for an item when it is named in the item's sentence, or when the item points back to it ('there', 'dort', 'dabei', 'dafür'). A time of day or day of the week counts also inside a phrase of frequency: from 'jeden Morgen' point to 'Morgen'. For a job, its own destination or purpose is part of the need; for a pain or gain on that trip, it is a situation. Weather counts as an occasion. Not a situation: words of frequency (every day, immer), the date of a single event, the destination or object that is part of the need itself, and parts of a wished solution. Empty if none is named.

### `improve.comfort` (changed)

Implements: M-5 (N-06); decision 6. "or arriving rushed" replaced by "or noise on board".

Approval: pending (previous: owner, 2026-11-28, in chat).

> How pleasant and calm the trip is, such as shelter, seats, crowding or noise on board.

### `improve.other` (changed)

Implements: M-11 (N-17). "such as staff" becomes "such as staff or equipment".

Approval: pending (previous: owner, 2026-11-28, in chat).

> Only when the quote describes a dimension that is not on this list, such as staff or equipment.

### `assembly.rule` (changed)

Implements: agent point 5 (N-21). `reader_en` added to the printed English versions and `reader` to the German answers that are not printed. Claude wording; the report gives only the instruction.

Approval: pending.

> Code assembles the guideline package from brief.yaml and examples.yaml with a fixed template. The template prints the English operative versions (teacher_task_en, reader_en, domain.owner_en, item_boundaries.rule); the owner's German answers (teacher_task, reader, domain.owner, item_boundaries.owner, examples.cases_owner) stay verbatim in brief.yaml and in the provenance and are not printed. Review-only keys (shows, drafted_by, approval, previous_approval and the *_choice keys) are stripped. The owner approves the assembled package with sha256 hashes before any labeling run.

### `assembly.passes` (changed)

Implements: M-2 (N-02); decision 8. Pass 3 sentence replaced; the sentence on the agreement pilot appended.

Approval: pending.

> Labeling runs in three passes. Pass 1: items with quote, kind, actor_type, evidence_type and evidence_scope; relevant follows from them. Pass 2: the other attributes and the pointers, on the fixed items of pass 1. Pass 3: links, on every chunk with at least two items. A pointer that is not a verbatim part of the given text is set to empty and counted, not retried. The zero-shot baselines use the same passes. In the agreement pilot each reference runs all three passes on its own items; nothing is shared between the references.

### `link_connectives` (new)

Implements: M-2 (N-02); decision 8. New key with the closed lists of M-2. The `rule` sentence is a Claude wording that restates what M-2 says the list is for; `actor_pair_condition` is the M-2 condition verbatim.

Approval: pending.

- `rule`: A closed list that code uses only to draw the enriched link sub-sample of the agreement pilot. It does not decide whether pass 3 runs, and it does not decide a link.
- `means_end`: [um … zu, damit, deshalb, dafür, in order to, so that]
- `order`: [zuerst, danach, bevor, nachdem, während, first, afterwards, before, after, while]
- `actor_pair`: [weil, wegen, because, because of]
- `actor_pair_condition`: together with at least two different role words in the chunk

### `pilot_thresholds.definitions.matching` (changed)

Implements: M-11 (N-22). "Tokens are split at white space." appended.

Approval: pending.

> Items of two references are matched one to one when the token IoU of their quotes is at least 0.5, after stripping punctuation at the edges; pairs with the highest IoU are matched first. Tokens are split at white space.

### `pilot_thresholds.definitions.links` (changed)

Implements: M-2 (N-22). Agreement of two links appended.

Approval: pending.

> Scored only on pairs of items that both references matched: F1 of the links between matched items. The end-to-end F1 is reported next to it and not used for the decision. For order, the relation (before or during) is reported as a separate kappa on links both references found. Two links agree when both ends are matched items, the direction is the same and the relation is the same.

### `pilot_thresholds.definitions.link_sample` (changed)

Implements: M-2; decision 9. Points to `link_connectives` and carries the size of decision 9. Claude wording around the M-2 phrase.

Approval: pending.

> Links are scored on the random pilot plus an enriched sub-sample of 100 chunks per language: chunks in which code finds a word of link_connectives. If a link type has fewer than 30 units, the sub-sample is extended once, to 200 chunks per language. Link prevalence is never estimated from the enriched sub-sample.

### `pilot_thresholds.definitions.pilot_size` (changed)

Implements: decision 9. Size of the enriched sub-sample added, for consistency with `link_sample`. Claude wording.

Approval: pending.

> 100 chunks per language drawn at random, plus the enriched link sub-sample (100 chunks per language, at most 200).

### `pilot_thresholds.definitions.revision` (changed)

Implements: M-12. "of the same size as the pilot" added, for consistency with `decision`. Claude wording.

Approval: pending.

> After a guideline revision, fields are scored again on a fresh holdout of the same size as the pilot, not on the pilot chunks.

### `pilot_thresholds.decision` (changed)

Implements: M-12 (N-03); decision 10. Replaced.

Approval: pending.

> A field is produced when its estimate meets the threshold and the lower bound of its interval meets the floor; a field with two numbers needs both. First count the units: with fewer than 30 the field is underpowered whatever its estimate, and the sample is extended once, to at most twice its size; a field that is still underpowered is not produced in this version and is listed as not measured. With 30 or more units: an estimate below the floor means not produced; an estimate between floor and threshold gets one guideline revision and is scored again on a fresh holdout of the same size as the pilot, and is then produced only if it meets this rule; an estimate at the threshold with a lower bound below the floor is extended once in the same way.

### `pilot_thresholds.keep_always_stop` (changed)

Implements: M-12 (N-03); decision 10. Replaced.

Approval: pending.

> A keep_always field that would be not produced under the decision rule, at any step, stops the pilot in that language, and the guideline goes back to the owner. It is never dropped. relevance_kappa stands for relevant and item_matching_f1 for quote.

### Comment above `evidence_type` (new, not printed)

Implements: agent point 3 (R-24). Wording verbatim from the report. A YAML comment, so the template never prints it and it carries no approval field; the owner approves it with the package.

> The scale orders the kind of backing, not its value; the export must not filter or sort by it (Fable review 1, R-24). Review note, not printed.

Unchanged keys: `means_end` and `order` keep their open lists of connecting words for the labeler; the closed list in `link_connectives` serves only the sampling code.

## 2. Label changes in `examples.yaml`

No example was added or removed, and no text was changed (the e05 text stays as the review recommended). The `shows` lists of e05, e06, e07, e08, e09, e12, e13, e15 and e16 were updated so that they no longer state a rule that changed. Rows marked *beyond section 7* are not on the reviewer's list; they follow from a new rule applied strictly and need the owner's attention.

| Example | Item | Field | Before | After | Reason |
|---|---|---|---|---|---|
| e05 | i3 | situation | null | "Morgen" | decision 7, M-7 |
| e05 | i4 | states_solution | true | false | M-11 (N-13); the quote predicts uptake and asks for nothing, so the means_end link i5 → i4 is now "measure linked to the need behind it" |
| e06 | i3 | quote | "… around a third of our posts are empty, as far as we can tell" | "… around a third of our posts are empty" | *beyond section 7*: M-3, a frame that only says who knows it ('ich schätze') stays outside the quote; the evidence (observation, from the estimate) is unchanged |
| e07 | i1 | situation | "Morgens" | null | *beyond section 7*: M-7, a time counts only when named in the item's sentence or pointed back to; "Morgens" is in the sentence before "Ich nehme das Rad" |
| e07 | i6 | situation | null | "Morgen" | decision 7, M-7 ("dabei" and "jeden Morgen") |
| e08 | i1 | situation | "Saturdays" | "weekend" | *beyond section 7*: M-7 sentence scope; "Saturdays" is in the sentence before; "another weekend" is the time named in the item's own sentence |
| e08 | i2 | situation | null | "weekend" | *beyond section 7*: decision 7 by analogy, the time word inside "every other weekend" |
| e09 | i1 | actor_type | society | individual | decision 5, M-6 |
| e09 | i6 | actor_type | society | individual | decision 5, M-6 (generic "man") |
| e12 | i3 | situation | null | "high street" | M-7 ("there" points back, same sentence) |
| e13 | i2 | situation | "solchen Festen" | "Festen" | M-7 (no demonstrative) |
| e15 | i1 | situation | null | "Morgen" | decision 7, M-7 |
| e16 | i1 | improve | [] | [other] | M-11 (missing equipment) |
| e16 | i3 | evidence_type | observation | anecdote | decision 2, M-1 |
| e16 | i3 | situation | "hospital appointment" | "hill estates" | M-7 ("up there" points back; place before occasion; the appointment is part of the need) |
| e16 | i4 | kind / job_kind | job / functional | gain / null | decision 4, M-4 (states_solution stays true) |
| e16 | i5 | kind / job_kind | job / functional | pain / null | M-4 (an obstacle before the step; the order link i5 before i4 stays) |

Checked against the new rules without a change: the ordered evidence test of M-1 gives the existing grade for every other item, as the review said; all reporting frames already stand outside the quotes; e12 i5 keeps "older passengers" (a role inside the quote comes first), e16 i6 keeps the speaker tag "BUS OPERATOR" (the running text names no role) and e16 i4 and i5 keep "district council"; e13 i2 keeps society ("alle").

## 3. `check_examples.py`

New checks, each one only where a new rule is checkable by code:

- `executor_role` and `situation` do not start with an article, possessive, demonstrative or preposition (M-7; German and English word list).
- `executor_role` is not a generic word such as "I", "we", "people", "members" or "Leute" (M-8).
- `society` only when the quote holds a word for everyone ('alle', 'everyone', 'Allgemeinheit', 'public') (M-6).
- `states_solution` true only on gains (M-4).
- `link_connectives` in `brief.yaml` is a closed, non-empty list of words for each link field (M-2).

A negative test on a copy (situation "solchen Festen", e09 i1 as society, e16 i4 as pain) made all three item checks fire. Not checked by code: whether a situation is named in the item's sentence (pointing back is not limited to the listed words, for example "durchfahre" in e15 i2), and "pass 3 on every chunk with two items", which is a property of the labeling run, not of the examples.

Results: `check_examples.py` reports 0 errors; `ruff check` passes; `ruff format --check` passes.

## 4. Final distribution

16 examples (8 de, 8 en), 3 empty, 67 items. Before = last commit; target = counts of the span-train-v1 teacher run (see provenance).

| Field | Value | Before | After | Target |
|---|---|---|---|---|
| kind | pain | 41 (61 %) | 42 (63 %) | 50 % |
|  | gain | 14 (21 %) | 15 (22 %) | 22 % |
|  | job | 12 (18 %) | 10 (15 %) | 28 % |
| actor_type | individual | 42 (63 %) | 44 (66 %) | 44 % |
|  | worker | 10 (15 %) | 10 (15 %) | 12 % |
|  | public_sector | 6 (9 %) | 6 (9 %) | 19 % |
|  | organization | 6 (9 %) | 6 (9 %) | 21 % |
|  | society | 3 (4 %) | 1 (1 %) | 4 % |
| evidence_type | opinion | 34 (51 %) | 34 (51 %) | 73 % |
|  | routine | 16 (24 %) | 16 (24 %) |  |
|  | observation | 10 (15 %) | 9 (13 %) |  |
|  | anecdote | 5 (7 %) | 6 (9 %) |  |
|  | measurement | 2 (3 %) | 2 (3 %) |  |
| evidence_scope | single | 39 (58 %) | 39 (58 %) | 18 % |
|  | multiple | 23 (34 %) | 23 (34 %) | 73 % |
|  | quantified | 5 (7 %) | 5 (7 %) |  |
| states_solution | true | 8 | 7 |  |
| links | means_end / actor_pair / order | 3 / 2 / 2 | 3 / 2 / 2 |  |

Per language, actor_type after: de individual 21, worker 6, public_sector 3, organization 3, society 1; en individual 23, worker 4, organization 3, public_sector 3. The decisions move two labels away from the target: job falls to 15 % (e16 i4 and i5) and society to one item, in German only. The gaps the review named under R-17 (items per example, opinion, scope, no society in English) remain; closing them needs new or longer examples, which this round does not add.

## 5. Not applied or still open

- **README row 11 (M-11).** "with the words that order them" is in `research/opportunity-interface/README.md`, outside the files of this round; not changed.
- **N-14, N-15, N-19, rest of N-22.** The report gives no wording: which item is `from` when the cause sits in the victim's quote (e04), the antecedent of "deshalb" and a definition of "event" for `order`, the thin `order` field, and `same_need_twice` filed under `evidence_type`. Not changed.
- **R-18, R-24, R-29.** Open by decision or scope. R-24 has only the non-printed comment; R-29 goes to the roadmap before phase 7.
- **Frame example in M-3.** The frame example 'Viele sagen mir, dass' contains "dass", while the same rule keeps the opening conjunction inside the quote. The examples keep "dass" inside (e05 i2, e13 i1). The owner may want the example without "dass".
- **Role words for `actor_pair` sampling.** `link_connectives.actor_pair_condition` asks for "at least two different role words in the chunk", but code has no closed list of role words. The sampling code needs one, or the condition needs a different test.
- **"weekend" as a day of the week.** e08 i1 and i2 read "weekend" as a day of the week under M-7. If the owner reads it otherwise, e08 i2 goes back to null; e08 i1 keeps "weekend" as a time of week named in its own sentence ("another weekend"), or becomes null if that phrase is read as frequency too.
- **e07 i1 and e08 i1.** Both lose the time named in the sentence before. If the owner wants a time named once to carry over to the next sentence of the same trip, M-7 needs an extra sentence and the old labels come back.
- **e07 i6 evidence.** The wish "nicht jeden Morgen gehetzt ankommen" has a frequency word, which line 3 of the ordered test could read as routine. It stays opinion (a wish, not a reported experience), as before.
- **e10 i3 situation.** It keeps "long trips" although the place "motorway" stands in the same sentence; the planning burden does not arise on the motorway. A labeler applying "place before occasion" mechanically may pick "motorway".

## 6. Approval list for the owner

26 keys of `brief.yaml` carry `approval: pending`: 25 top-level keys and 1 nested key (`domain.owner_en`). Each is listed with its full wording; owner answers inside a key are marked and need no approval. Not pending: `teacher_task` and `reader` (owner answers), `domain` with `definition` (owner, 2026-11-27), `empty_result` (owner, 2026-11-28) and `language` (owner choice). The comment on R-24 (section 1) and `examples.yaml` (16 examples, under the key `examples`) are approved with the package.

### 1. `teacher_task_en`

Approval: pending.

- `text`: Find where the text states pains, gains and jobs to be done. Each of them is then enriched with further fields, as given in the list of fields.

### 2. `reader_en`

Approval: pending.

- `text`: A product manager.

### 3. `domain.owner_en`

Approval: pending.

- `text`: Follow the definition of mobility; everything that belongs to it also belongs to our topic.

### 4. `item_boundaries`

Approval: pending.

- `owner` (owner, verbatim): ALso wir sochen merkmale wie pain, gain und JTBD. diese sind durch sprache vcodiert. diese sprache kann auch mehrere sätze dafür verwenden. wir beschrenken nicht nach dem Tool (Sprache) sondern nach der Sinneinheit (z.B. JTBD)
- `rule`: An item is one need. Its quote is the shortest run of whole clauses that states the need, including the words that mark it as a wish, fear or problem (such as 'I want', 'schön wäre', 'I worry that') and the conjunction that opens a clause. A need may run over several sentences. A cause or consequence joined with 'so', 'because', 'weil' or 'sodass' belongs to the same item unless it is a need of its own. It is a need of its own when it names another burden or another actor than the clause before it. A purpose joined with 'um … zu', 'damit', 'in order to' or 'so that' is an item of its own, and so is the clause it depends on. The opening conjunction may be of either kind ('und', 'aber', 'dass', 'and', 'but', 'that'). A frame that only says who said it ('Viele sagen mir, dass', 'People tell us', 'ich schätze') stays outside the quote; a source named inside the clause ('laut der Erhebung') and a verb that itself states the problem ('complain', 'sich beschweren', 'worry') stay inside. Two clauses joined by 'and' are two items when they name different burdens or actors. Quotes of one text never overlap. Offsets are computed by code.

### 5. `relevant`

Approval: pending (previous: owner, 2026-11-28, in chat).

- `definition`: A text is relevant when it states at least one job, pain or gain of an actor within mobility as defined under domain, told by the actor or reported by someone else. The topic alone is not enough. Not relevant: texts that only report facts, figures, events or product features with no actor who wants to get something done, struggles, hopes for something or values an outcome they have; timetables, tariffs and technical specifications; a provider praising its own offer without reporting a customer's need; texts where mobility is only the backdrop of something else. One passage with a need is enough, even if the rest of the text is off-topic. The test applies to each item: the need, or the trip or transport on which it arises, must lie within mobility. What a mobility problem does to the actor (being late for work, feeling cut off) is an item. A need about something else that is only mentioned on the way is no item.

### 6. `kind`

Approval: pending (previous: owner, 2026-11-28, in chat).

- `job`: Something an actor is trying to get done or achieve in a situation: a task, a goal or a change of state they want.
- `pain`: Something that bothers the actor before, during or after getting the job done: an obstacle, a cost, a risk, an annoyance, a bad outcome, or the fear of one.
- `gain`: An outcome or benefit the actor wants, expects or would welcome: something that makes the job easier, faster, cheaper, safer or more pleasant, or a good outcome they already value.
- `job_versus_gain`: A job is what the actor wants to get done: it has its own verb of doing and stays the same when the means change. A wish about how well, fast, cheaply, safely or reliably it goes is a gain. A sentence that only reports what someone does, with no want, purpose, obstacle or judgement, is not an item. This test decides, whatever word the text uses ('goal', 'Ziel', 'need'). A step the actor takes for a stated purpose is a job and is linked to its goal with means_end. A wish for a thing or measure is a gain with states_solution true, also when it has a verb of doing ('order', 'build', 'introduce').
- `feelings`: A bad feeling reported as a fact is a pain, a good one a gain. A wish to feel or not to feel something is a job with job_kind emotional, also when it is about how the trip goes; this rule comes before job_versus_gain.
- `pain_versus_negated_gain`: Label by what the text describes. A problem the actor has now is a pain, even when phrased as a missing benefit. A wish for a better state is a gain, even when phrased with a negation. Label both only when each has its own clause; otherwise take the kind the wording has.

### 7. `actor_type`

Approval: pending (previous: owner, 2026-11-28, in chat).

- `rule`: The actor is who has the need, not who speaks or writes. A need voiced on behalf of others takes the type of those who have it; the speaker's body is the actor only for its own need (budget, staff, duties). actor_type is the coarse class; executor_role marks the words that name the specific role.
- `individual`: Private persons acting for themselves or their household, one or many, including named groups such as commuters or residents.
- `worker`: A person whose need comes from their work in or around mobility. Commuting is not work in mobility.
- `organization`: A company, operator, association or other non-state body acting as such.
- `public_sector`: A public authority or public body acting as such.
- `society`: The public at large, only when the text says so in words ('alle', 'everyone', 'die Allgemeinheit', 'the public'). The people of a place and generic 'man', 'one' or 'you' are individual.

### 8. `evidence_type`

Approval: pending (previous: owner, 2026-11-28, in chat).

- `rule`: How the text backs the need, as an ordinal scale from opinion (lowest) to measurement (highest).
- `opinion`: A view, belief, wish or judgement with no experience given.
- `anecdote`: One concrete experience, a single event.
- `routine`: Repeated or habitual experience of the actor (always, every day, usually).
- `observation`: Something seen across other people or over a longer time, stated without a figure from counting or measuring.
- `measurement`: A figure obtained by counting or measuring, such as a survey result, a statistic or a measured time.
- `boundaries`: Grade by the basis the speaker gives, and take the first line that fits. 1. A counted or measured figure with its source: measurement. 2. One concrete event, whoever it happened to and whoever told it: anecdote. 3. The speaker's own repeated experience, shown by a word of frequency, by habitual present tense about the speaker's own trips ("I take", "wenn ich … muss") or by a share of the speaker's own attempts: routine. 4. A statement about several other people or a longer time, when the text says how the speaker knows it (they were told, or they were there) or gives an estimated figure: observation. 5. Everything else, including a plain statement of how things are ("the bus runs twice a day"): opinion. Anecdote versus routine: one event is an anecdote; words of frequency or several events make it routine. Observation versus measurement: a measurement needs a figure that was counted or measured; an estimate such as "about half, I would say" is an observation, or routine when it is a share of the speaker's own repeated experience.
- `reported_speech`: The speaker is the person or body whose statement the text gives: the author of a first-person text, or the person a news text or minutes quote. A journalist or minute-taker who only passes a statement on is not the speaker. What third persons told that speaker is graded from the speaker's side, as below.
- `same_need_twice`: The same need stated again in a separate passage that does not overlap the first is a second item with its own evidence.

### 9. `evidence_scope`

Approval: pending (previous: owner, 2026-11-28, in chat).

- `rule`: Scope counts actors or cases; frequency belongs to evidence_type. One person's routine is single. A body speaking of its own need is one actor. The order is single, multiple, quantified.
- `single`: One case, one actor or one event.
- `multiple`: Several or many cases, stated without a number.
- `quantified`: The text gives a number or share of the actors or occurrences that have the need, such as people, trips, tours or complaints; an estimate with a figure counts. Durations, distances, prices, times of day and the size of an operation do not count. A share counts when it is a share of people or events; a share of a stock, such as posts or vehicles, is the size of the problem.

### 10. `quote`

Approval: pending.

- `owner_choice` (owner, verbatim): Nur Zitat (Recommended)
- `rule`: Each item is a verbatim quote in the source language. Code computes its offsets; the labeler does not count characters. No statement or translation is written per item.

### 11. `doubt`

Approval: pending (previous: owner, 2026-11-28, in chat).

- `item`: When unsure whether a passage is an item, ask whether a product manager could learn a need from it. If not, leave it out. Never add context that the text does not give.
- `kind`: Take the kind the wording has; label both only when each has its own clause.
- `levels`: For evidence_type and evidence_scope, take the lower grade. evidence_scope is ordered single, multiple, quantified.
- `fields`: job_kind, mode, improve, executor_role and situation stay empty when they are not stated or you are unsure; an empty field is correct. kind, actor_type, evidence_type and evidence_scope are never empty: use the rules for kind and levels above, and for actor_type take the type of the persons the need is about.

### 12. `job_kind`

Approval: pending (previous: owner, 2026-11-28, in chat).

- `applies_to`: job
- `functional`: The practical task or result the actor wants to get done.
- `emotional`: How the actor wants to feel, or wants to avoid feeling, while getting it done.
- `social`: How the actor wants to be seen by others, or to stand with them.
- `rule`: One value per job item: the one the text stresses. Only jobs carry job_kind; it stays empty for pains and gains, also when they have an emotional or social side. If a passage states a practical and a feeling side, label two jobs only when each has its own clause; otherwise take the value the wording stresses.

### 13. `executor_role`

Approval: pending (previous: owner, 2026-11-28, in chat).

- `rule`: A pointer to the noun phrase, without article, with the modifiers that define the role, that names who has the need: what the person or body is, such as an occupation, a life situation or an organisation type. The pointer must lie in the text the labeler is given, inside or outside the item's quote. If the same words occur more than once, the occurrence inside the quote counts, else the one nearest before it; code resolves offsets. A role named for the same actor applies to all of that actor's items. A role named inside the quote comes before a role named elsewhere for the same actor. If the words occur only after the quote, the nearest occurrence after it counts. A speaker tag counts as a role only when it names the actor itself and the running text names none. Pronouns and generic words such as "I", "we", "people", "members" or "Leute" get no role. If several roles are named, take the one that has this need. Empty if no role is named.

### 14. `link_encoding`

Approval: pending.

- `rule`: Every link is written as {from, to, relation}: from and to are ids of items of the same text, and relation is one of the values of the link field.

### 15. `actor_pair`

Approval: pending (previous: owner, 2026-11-28, in chat).

- `values`: [causes]
- `rule`: A directed link from the item of the actor who causes to the pain of the actor who suffers, when the text says that the one causes the other at the same place, time or resource. The causing item may be a job or a pain. The text must name the cause. Both items must be in the text, and their actors differ. A clash known only from general knowledge is not linked. Written as {from: causing item, to: pain, relation: causes}.

### 16. `mode`

Approval: pending (previous: owner, 2026-11-28, in chat).

- `values`: [walk, bicycle, micromobility, motorcycle, car, taxi_ridehailing, bus, tram_metro, train, coach, public_transport, truck_van, air, water, other]
- `rule`: All modes named in the item's quote, as a list. Decide on the words of the quote: every mode named counts, also when it is negated or missing. Use public_transport when the text names public transport without a mode. A word that belongs to exactly one mode counts, such as a bus driver for bus or a wallbox for car. A verb counts when it belongs to one mode (walk, cycle, fly, drive for car); 'fahren', 'ride' and 'travel' name none. Empty if the quote names no mode; do not infer one from the context alone.
- `boundaries`: A pedelec is bicycle. E-scooters and other small electric devices are micromobility. A moped is motorcycle. Minibus and on-demand shuttle are bus. A freight train is train. Charger, petrol station, motorway and parking give car only together with a vehicle word. Use other only for a named mode outside the list.

### 17. `situation`

Approval: pending (previous: owner, 2026-11-28, in chat).

- `rule`: A pointer to the noun phrase (or time word), without article, possessive, demonstrative or preposition, with the modifiers that define where, when or on what occasion the need arises: a place, a time of day, week or year, or an occasion such as a trip purpose or what the actor carries. The pointer must lie in the text the labeler is given, inside or outside the item's quote. If the same words occur more than once, the occurrence inside the quote counts, else the one nearest before it; code resolves offsets. Place before occasion before time when several are tied to the need. A place, time or occasion counts for an item when it is named in the item's sentence, or when the item points back to it ('there', 'dort', 'dabei', 'dafür'). A time of day or day of the week counts also inside a phrase of frequency: from 'jeden Morgen' point to 'Morgen'. For a job, its own destination or purpose is part of the need; for a pain or gain on that trip, it is a situation. Weather counts as an occasion. Not a situation: words of frequency (every day, immer), the date of a single event, the destination or object that is part of the need itself, and parts of a wished solution. Empty if none is named.

### 18. `improve`

Approval: pending (previous: owner, 2026-11-28, in chat).

- `values`: [time, cost, effort, reliability, safety, comfort, access, information, flexibility, environment, other]
- `rule`: The dimensions the item is about, as a list, for jobs, pains and gains. Only when the quote names or clearly describes the dimension. When two values fit, follow the lines below. Empty if no dimension is named or described.
- `time`: How long it takes, including waiting and detours; a duration is time.
- `cost`: Money the actor pays or lacks, such as fares, fuel, fines, prices or budgets.
- `effort`: Steps, planning and hassle needed to get it done.
- `reliability`: Whether it happens as planned; late, cancelled, broken down or unpredictable is reliability.
- `safety`: Risk of accident, injury or other harm.
- `comfort`: How pleasant and calm the trip is, such as shelter, seats, crowding or noise on board.
- `access`: Whether a service, place or vehicle is available or within reach at all.
- `information`: What the actor knows or can find out, such as timetables, delays or changes.
- `flexibility`: Choice of time or route, including how often a service runs.
- `environment`: Emissions, noise and other effects of traffic on people and nature around it.
- `other`: Only when the quote describes a dimension that is not on this list, such as staff or equipment.

### 19. `states_solution`

Approval: pending (previous: owner, 2026-11-28, in chat).

- `rule`: True when the quote asks for a particular thing or measure, so that only one way would satisfy it (a named product, a new facility, a specific rule or schedule). False when it asks for a property or result that several things could deliver, and false otherwise. The item keeps its kind and is not dropped. The need behind it is a separate item only if the text states it.

### 20. `means_end`

Approval: pending (previous: owner, 2026-11-28, in chat).

- `values`: [in_order_to]
- `rule`: A directed link from item A to item B of the same actor when the text says that A is done or wanted in order to achieve B, or that A is the measure the actor wants for B. The connecting words must join the two quotes, such as "um zu", "damit", "deshalb", "in order to" or "so that". No link when the connection is only implied. Items of different actors are not linked here. Written as {from: A, to: B, relation: in_order_to}.

### 21. `order`

Approval: pending (previous: owner, 2026-11-28, in chat).

- `values`: [before, during]
- `rule`: A link between two items of one text when words in the text order them in time, such as "zuerst", "dann", "bevor", "während", "first", "then", "after" or "while". Link only items that are events. before means that from comes before to; write "A after B" as B before A. during means that both happen at the same time; it has no direction, so the earlier quote is from. The order of sentences alone does not count. Order across texts is never labeled.

### 22. `examples`

Approval: pending (previous: owner, 2026-11-28, in chat; distribution gaps go to the Fable review).

- `source_choice` (owner, verbatim): Fiktiv, Claude entwirft
- `cases_owner` (owner, verbatim): überlege was edge cases sein können, das muss mit rein, denk aber auch an stratifiing. nicht dass wir 100 edge case beispiele und nur 5 beispiele für fälle haben, die 90% der echten fälle ausmachen. kein plan ob das ein problem ist, aber wenn dann sollten wir es berücksichtigen
- `cases_choice` (owner, verbatim): [Kernfälle, Kanten, Felder, Grenzfälle]
- `size_choice` (owner, verbatim): 12, je 6 de/en (Recommended)
- `size`: 16, 8 de and 8 en (Fable review 1, decision 13)
- `file`: examples.yaml

### 23. `assembly`

Approval: pending.

- `owner_choice` (owner, verbatim): Code setzt zusammen (Recommended)
- `rule`: Code assembles the guideline package from brief.yaml and examples.yaml with a fixed template. The template prints the English operative versions (teacher_task_en, reader_en, domain.owner_en, item_boundaries.rule); the owner's German answers (teacher_task, reader, domain.owner, item_boundaries.owner, examples.cases_owner) stay verbatim in brief.yaml and in the provenance and are not printed. Review-only keys (shows, drafted_by, approval, previous_approval and the *_choice keys) are stripped. The owner approves the assembled package with sha256 hashes before any labeling run.
- `passes`: Labeling runs in three passes. Pass 1: items with quote, kind, actor_type, evidence_type and evidence_scope; relevant follows from them. Pass 2: the other attributes and the pointers, on the fixed items of pass 1. Pass 3: links, on every chunk with at least two items. A pointer that is not a verbatim part of the given text is set to empty and counted, not retried. The zero-shot baselines use the same passes. In the agreement pilot each reference runs all three passes on its own items; nothing is shared between the references.

### 24. `link_connectives`

Approval: pending.

- `rule`: A closed list that code uses only to draw the enriched link sub-sample of the agreement pilot. It does not decide whether pass 3 runs, and it does not decide a link.
- `means_end`: [um … zu, damit, deshalb, dafür, in order to, so that]
- `order`: [zuerst, danach, bevor, nachdem, während, first, afterwards, before, after, while]
- `actor_pair`: [weil, wegen, because, because of]
- `actor_pair_condition`: together with at least two different role words in the chunk

### 25. `pilot_thresholds`

Approval: pending.

- `status`: provisional
- `owner_choice` (owner, verbatim): Freigeben (vorläufig)
- `per`: [field, language]
- `definitions`:
  - `matching`: Items of two references are matched one to one when the token IoU of their quotes is at least 0.5, after stripping punctuation at the edges; pairs with the highest IoU are matched first. Tokens are split at white space.
  - `item_matching`: F1 of matched items. The F1 at any overlap is reported next to it and not used for the decision.
  - `relevance`: Cohen's kappa over all chunks of the pilot. Raw agreement and a prevalence-robust coefficient (Gwet's AC1) are reported next to it.
  - `attributes`: Cohen's kappa on items matched by both references, for kind, actor_type, evidence_scope and states_solution; job_kind only on matched items that both references call job. evidence_type uses a weighted kappa with linear weights.
  - `lists`: mode and improve: Krippendorff's alpha with the MASI set distance on matched items; both empty counts as agreement. For improve, a kappa per value is reported to find values to merge.
  - `pointers`: executor_role and situation: two numbers each, on matched items. A kappa of filled against empty, and a token F1 on items that both references filled, comparing the pointed strings, not their offsets.
  - `links`: Scored only on pairs of items that both references matched: F1 of the links between matched items. The end-to-end F1 is reported next to it and not used for the decision. For order, the relation (before or during) is reported as a separate kappa on links both references found. Two links agree when both ends are matched items, the direction is the same and the relation is the same.
  - `link_sample`: Links are scored on the random pilot plus an enriched sub-sample of 100 chunks per language: chunks in which code finds a word of link_connectives. If a link type has fewer than 30 units, the sub-sample is extended once, to 200 chunks per language. Link prevalence is never estimated from the enriched sub-sample.
  - `intervals`: 95 % bootstrap intervals, resampling chunks.
  - `units`: Items or links that at least one reference filled, counted per field and language.
  - `pilot_size`: 100 chunks per language drawn at random, plus the enriched link sub-sample (100 chunks per language, at most 200).
  - `revision`: After a guideline revision, fields are scored again on a fresh holdout of the same size as the pilot, not on the pilot chunks.
- `thresholds`:
  - `core`:
    - `relevance_kappa`: {threshold: 0.75, floor: 0.6}
    - `item_matching_f1`: {threshold: 0.6, floor: 0.45}
    - `kind_kappa`: {threshold: 0.6, floor: 0.4}
    - `actor_type_kappa`: {threshold: 0.6, floor: 0.4}
    - `evidence_scope_kappa`: {threshold: 0.6, floor: 0.4}
    - `evidence_type_weighted_kappa`: {threshold: 0.5, floor: 0.4}
  - `attributes`:
    - `job_kind_kappa`: {threshold: 0.5, floor: 0.4, on_fail: collapse to functional against other and score again before dropping}
    - `mode_masi_alpha`: {threshold: 0.7, floor: 0.4}
    - `improve_masi_alpha`: {threshold: 0.5, floor: 0.35}
    - `states_solution_kappa`: {threshold: 0.5, floor: 0.4}
    - `states_solution_true_f1`: {threshold: 0.6, floor: 0.4, min_true_items: 30}
  - `pointers`:
    - `executor_role_filled_kappa`: {threshold: 0.6, floor: 0.4}
    - `executor_role_token_f1`: {threshold: 0.6, floor: 0.4}
    - `situation_filled_kappa`: {threshold: 0.6, floor: 0.4}
    - `situation_token_f1`: {threshold: 0.6, floor: 0.4}
  - `links`:
    - `actor_pair_f1`: {threshold: 0.5, floor: 0.3}
    - `means_end_f1`: {threshold: 0.5, floor: 0.3}
    - `order_f1`: {threshold: 0.5, floor: 0.3}
- `reported_only`: [relevance raw agreement and Gwet's AC1, evidence_scope Gwet's AC1, item F1 at any overlap, end-to-end F1 of each link field, order relation kappa, improve kappa per value, actor_type per class, with society marked as underpowered]
- `decision`: A field is produced when its estimate meets the threshold and the lower bound of its interval meets the floor; a field with two numbers needs both. First count the units: with fewer than 30 the field is underpowered whatever its estimate, and the sample is extended once, to at most twice its size; a field that is still underpowered is not produced in this version and is listed as not measured. With 30 or more units: an estimate below the floor means not produced; an estimate between floor and threshold gets one guideline revision and is scored again on a fresh holdout of the same size as the pilot, and is then produced only if it meets this rule; an estimate at the threshold with a lower bound below the floor is extended once in the same way.
- `keep_always_stop`: A keep_always field that would be not produced under the decision rule, at any step, stops the pilot in that language, and the guideline goes back to the owner. It is never dropped. relevance_kappa stands for relevant and item_matching_f1 for quote.
- `per_language`: Each field is decided per language and is produced only in the languages where it passed.

### 26. `drop_order`

Approval: pending.

- `owner_choice` (owner, verbatim): Kanten zuerst (Recommended)
- `order`: [actor_pair, order, means_end, executor_role, situation, states_solution, job_kind, improve, mode]
- `trigger`: The drop order applies only when the model's core-does-not-pay test fails: item-matching F1 or relevance of the model with the extra fields falls below the same model without them, beyond the bootstrap interval. Fields are then dropped in this order until the test passes.
- `keep_always`: [relevant, kind, quote, actor_type, evidence_type, evidence_scope]
