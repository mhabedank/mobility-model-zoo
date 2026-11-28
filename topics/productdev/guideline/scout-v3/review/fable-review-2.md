# Fable review 2 of the scout guideline v3 brief

Date: 2026-11-28. Reviewed: `brief.yaml` and `examples.yaml` at commit d7afcef, against their state at 880d31b, with `fable-review-1.md`, `changes-after-review-1.md`, `brief-provenance.md` and `research/opportunity-interface/README.md`. Method: one lead reviewer, no subagents; every one of the 67 items was read against the rule texts, and a throwaway script checked pointer occurrences, uncovered text and the distributions of `examples.yaml`. No file under `data/` was read, no real text was labeled, no model output was judged, and no existing file was changed. All wordings below are Claude drafts and need the owner's approval under constitution 3.2.0.

## 1. Verdict and summary

**Verdict: not yet ready for formal approval. One short correction round is enough; no new research and no new examples are needed.**

- Of the 31 findings of review 1: 14 resolved, 14 partly resolved, 3 not resolved, 0 newly broken. All six old blockers are resolved or reduced to wording gaps.
- New issues: 3 blockers, 9 major, 10 minor.
- The blockers are small in text but decisive: two evidence rules contradict each other on a keep-always field (N-01), pass 3 cannot be run as written and skips the actor pair that example e04 shows (N-02), and the decision rule has three cases with two answers (N-03).
- The examples are far more consistent than before. About 12 labels in 5 examples still contradict the new rules or each other (e05, e09, e12, e13, e16).
- The remaining agreement risk sits in four borders: split or merge of clauses, job against gain for means and feelings, opinion against routine against observation, and what counts as a situation.

## 2. Resolution of the review 1 findings

| Id | Status | Evidence |
|---|---|---|
| R-01 item boundaries | partly | `item_boundaries.rule` exists, quotes never overlap, wish frames and opening conjunctions are handled the same way in all 67 quotes. Open: the test for "a need of its own" (e10 i2/i3 split, e12 i2 merged), purpose clauses (e07 i1/i2 and e15 i6/i7 split, e12 i9 merged), reporting frames (only in the examples). See N-04. |
| R-02 job, gain, activity | partly | `kind.job_versus_gain`; bare activities are no items in e07, e08, e11, e15. Open: `kind.job` still says "a goal" while e11 i1 "Unser Ziel ist" is a gain; a means is a job in e07 i1 and e16 i4 but a gain in e04 i6; feelings collide with comfort. See N-05, N-06. |
| R-03 metrics undefined | partly | `pilot_thresholds.definitions` covers matching, units, lists, pointers, links, weights, intervals, size. Open: how the three passes run in the pilot, when two links agree, holdout size. See N-02, N-03. |
| R-04 links cannot pass | partly | Matched pairs, 0.5 and 0.3, enriched sub-sample. Open: sub-sample size; the connective list is open-ended, hardly selective ("dann", "then", "after") and has no word for `actor_pair`. See N-02. |
| R-05 pointers | partly | Strings instead of offsets, occurrence rule, pointer inside the given text, role applies to all items of the actor. Open: how far modifiers reach, two role words for one actor (e12 i5), speaker tags (e16). See N-10. |
| R-06 `states_solution` | resolved | Torres test in `states_solution.rule`; e03 i5, e11 i3, e04 i6 true; contrast pair e15 i6/i7. One leftover in e05 i4 (N-13). |
| R-07 tie to the job | resolved (accepted) | Owner decision 3; README rows 10 and 14 and test I2 say "per cairn cluster". |
| R-08 `improve` | resolved | Direction sentence removed, one line per value, tie rules; staff is `other` in e06 i3, e09 i4, e13 i1. |
| R-09 `actor_type` | partly | `actor_type.rule` and the new `individual`, `worker`, `society` lines; e05 i5, e09 i5, e12 i8 follow them. Open: `society` against `individual` inside e09. See N-07. |
| R-10 evidence | partly | Notes (a) and (c) are in `evidence_scope`; order declared; type and scope are decoupled (e15 i3, e06 i3, e12 i8); e05 i1 now measures the pain. Open: who "the speaker" is, and the borders of opinion. See N-01, N-08. |
| R-11 `mode` | resolved | `mode.rule` and `mode.boundaries`; e09 is consistent (i1 public_transport, i2 car, i3 bus, i6 bus); e04 i4 has truck_van. |
| R-12 `situation` | partly | Priority and four exclusions in `situation.rule`; e04 i4, e11 i3, e12 i3 corrected. Open: time of day inside a frequency phrase, places reached by "there", e16 i3. See N-09. |
| R-13 link definitions | partly | One encoding, directed `actor_pair`, "after" inverted, `during` shown in e15. Open: cause inside the victim's quote (e04), the antecedent of "deshalb" (e05), "events" undefined. See N-14, N-15. |
| R-14 decision rule | partly | `keep_always_stop`, `drop_order.trigger`, `per_language`, holdout, intervals. Open: three undefined cases. See N-03. |
| R-15 relevance | partly | `relevant.definition` admits a valued outcome; threshold 0.75 with floor 0.6. Open: domain test per item and the test for "backdrop" (agent's point 1). See N-11. |
| R-16 emotional and social side | resolved (accepted) | `kind.feelings`, `job_kind.rule`; e07 i4 pain, e07 i6 emotional job. It creates N-06. |
| R-17 example shortcuts | partly | Empties at positions 3, 8, 14; third-person texts e13, e14, e16; German worker, English public_sector. Open: 5.2 items per relevant example (before 5.5, target 12.6), opinion 51 % against 73 %, no `society` in English. |
| R-18 solution in use | not resolved | Owner decision 4 chose no third value. e10 i1 (fulfilled gain) still carries no marker; the workaround in e03 is no item. Accepted, but it stays a gap for the tree. |
| R-19 labeling cost | partly | `assembly.passes`; invalid pointers are set to empty. Open: the package hash after a dropped field, cost of local labeling. |
| R-20 German sentences | resolved | `teacher_task_en`, `domain.owner_en`, `item_boundaries.rule`; `assembly.rule` prints the English versions. `reader` is left over (agent's point 5). |
| R-21 free role spans | resolved (accepted) | README row 4. |
| R-22 `doubt.fields`, job sentence | partly | Job sentence deleted. `doubt.fields` still tells the labeler to leave required fields empty (agent's point 2). See N-12. |
| R-23 offsets, full stops | resolved | `quote.rule`; no quote has edge punctuation. |
| R-24 rank of anecdote | not resolved | No text anywhere (agent's point 3). |
| R-25 interface overclaims | resolved | README rows 4, 5, 10, 14. Row 11 has a leftover (N-20). |
| R-26 `drop_order` | resolved | `drop_order.order`. |
| R-27 mode borders | resolved | `mode.boundaries`. |
| R-28 kappa weights | resolved | `definitions.attributes`: linear. |
| R-29 roadmap phases 7, 8 | not resolved | Outside the changed files (agent's point 4). |
| R-30 test I2 | resolved | README I2: absent columns and minimum fill. |
| R-31 same need twice | resolved | `evidence_type.same_need_twice`; e06 i1/i2. |

## 3. New issues, ranked

### Blockers

**N-01. Two evidence rules contradict each other (`evidence_type.boundaries`, `evidence_type.reported_speech`).** `boundaries` says "What others told the speaker is an observation". `reported_speech` says the speaker is "the person whose words are reported". In "Viele Pendlerinnen und Pendler sagen mir, dass …" (e05 i2, i3) the commuters' words are reported, so under `reported_speech` they are the speaker and the items are opinion or routine; the example says observation. The same holds for e12 i3, e12 i7, e06 i1 and e16 i3. Only e13 shows the reading the agent meant (a journalist is not the speaker). Two labelers will split on every hearsay item, on a keep-always field whose failure stops the pilot.

**N-02. Pass 3 cannot run as written, and it contradicts e04 (`assembly.passes`, `definitions.link_sample`).** Pass 3 and the enriched sub-sample depend on "a connecting word named in the link rules". (1) The rules give open lists ("such as"), so code has no closed list. (2) `actor_pair.rule` names no word at all. Example e04 holds none of the listed words (its marker is "because"), so pass 3 would skip it, yet it carries an actor pair. (3) "dann", "then", "after", "first" and "while" occur in most chunks, so the filter filters little and the sub-sample is hardly enriched. (4) Nothing says whether, in the pilot, each reference runs passes 2 and 3 on its own items or on shared items; the `definitions` assume the first.

**N-03. The decision rule has three cases with two answers (`pilot_thresholds.decision`, `keep_always_stop`).** (1) A keep-always field between floor and threshold that still misses on the holdout is "not produced" under `decision` and "never dropped" under `keep_always_stop`. (2) An estimate below the floor with fewer than 30 units is "not produced" by one sentence and "underpowered" by the next. (3) "Extend the sample" has no size and no limit, and the holdout has no size. Under Principle IV these must be fixed before the pilot. Also unstated: whether a keep-always stop in one language stops both, and that `relevance_kappa` and `item_matching_f1` stand for the keep-always fields `relevant` and `quote`.

### Major

**N-04. Split or merge is still a judgement (`item_boundaries.rule`).** Three patterns are decided only by the examples. (a) "Unless it is a need of its own" has no test: e10 i2/i3 are split at "so", e12 i2 is merged at "so", e12 i1 merges two clauses joined by "and" although "two needs joined by 'and' are two items". (b) Purpose clauses are not named: e07 i1/i2 ("um … zu") and e15 i6/i7 ("damit") are split, e12 i9 ("without having to") is merged. Every in-sentence `means_end` link depends on this split; a labeler who quotes the whole sentence of e07 matches i2 (IoU 0.6) and loses i1 and the link. (c) Reporting frames stay outside in e05, e12, e13, e16 but the rule does not say so, and e15 i2 keeps "Die Anwohner beschweren sich, weil" inside.

**N-05. A means is a job in two examples and a gain in the others (`kind.job_versus_gain`).** The rule says a job "stays the same when the means change". e07 i1 "Ich nehme das Rad" and e16 i4 "We want to order four more lorries" are means and are labeled job; e04 i6, e05 i5, e15 i6, e11 i3 are wished means and are labeled gain. `kind.job` also still says "a goal", while e11 i1 "Unser Ziel ist, dass …" is a gain. e16 i5 "but first the capital budget has to be approved" is labeled job although it has no verb of doing by the actor and reads as an obstacle.

**N-06. `kind.feelings` collides with the gain definition and the `comfort` line.** "A feeling the actor … wants to avoid is a job" makes e07 i6 ("nicht jeden Morgen gehetzt ankommen") an emotional job. But `job_versus_gain` calls a wish about how it goes a gain, `kind.gain` lists "more pleasant", and `improve.comfort` lists "arriving rushed" by name. Labelers will split job against gain on exactly the items that feed the rare emotional class, and `job_kind` is scored only where both say job. `feelings` also has no line for a good feeling reported as a fact.

**N-07. `society` against `individual` flips inside e09 (`actor_type`).** `individual` includes "named groups such as … residents"; `society` needs a need "stated for everyone". e09 i1 ("Bei uns …") and e09 i6 ("dass man überhaupt wegkommt") are society, e09 i2 and i5 are individual, and e12 i4 ("nobody can read") is individual. All of e09 is about the same villagers. Only e13 i2 ("ein Problem für alle") meets the written rule.

**N-08. Opinion against routine against observation rests on unwritten tests (`evidence_type.boundaries`).** The examples follow three tests that the text does not state. (a) A statement of how things are, without event or frequency word, is opinion even in the first person (e10 i1, e03 i1, e16 i1), but habitual present tense about one's own trips is routine (e07 i1 to i3, e03 i2, e15 i5). (b) A claim about other people is observation only when the text says how the speaker knows: told (e06 i1, e12 i7) or present (e04 i3, e15 i2); otherwise opinion (e12 i1, i2, i4, i5, i6). (c) One event is an anecdote when witnessed or asserted (e04 i4, e16 i2) but an observation when told by the person concerned (e16 i3), which ranks hearsay above witness and contradicts `doubt.levels` ("take the lower grade"). Opinion is the majority class, so these borders decide the kappa.

**N-09. `situation`: three open borders.** (a) Time of day against frequency: "Morgens" (e07 i1) and "Saturdays" (e08 i1) are situations, "jeden Morgen" (e05 i3, e07 i6, e15 i1) is none, though it names the same time of day. (b) A place reached by an anaphor: e15 i2 takes "Wohnstraße" and e10 i3 takes "long trips" from the sentence before, but e12 i3 ("on the uneven kerb there") is empty and e16 i3 ("up there") takes the occasion "hospital appointment" instead of the place "hill estates", against "place before occasion"; the appointment is also the thing lost, so it is "part of the need itself". (c) No rule says for which items a situation named once applies: e07 i1 has "Morgens", i2 and i3 have none; e04 i1 has "city centre", i2 has none. The examples do follow one clean pattern that is not written down: for a job, its own destination is no situation; for a pain or gain on that trip, it is (e03 i2 against i3).

**N-10. Pointers: which words, when two candidates exist (`executor_role`, `situation`).** (a) Two role words for one actor: e12 i5 takes "older passengers" from the quote, the other e12 items take "older residents"; "members" stands in three quotes and is not taken. The rule gives no priority. (b) Speaker tags: e16 i6 takes "BUS OPERATOR", while for e16 i4 the nearer tag "HIGHWAYS OFFICER" is not taken. (c) Modifiers: "solchen Festen" (e13 i2) keeps a demonstrative, "Wahlkreis" (e05 i1) drops "meinem", "Gemeinde" (e09) drops "kleinen", "engen Kreuzung" (e15 i7) keeps "engen". (d) The occurrence rule has no case for a role named only after the quote.

**N-11. Domain test per item is still missing (`relevant`, agent's point 1).** e07 i4 (the boss's look) and e12 i7 (feeling lonely) are items, so consequences of a mobility problem count; nothing says so, and nothing says what "backdrop" excludes. Relevance follows from items, so one marginal item flips a chunk.

**N-12. `doubt.fields` still allows empty required fields (agent's point 2).** Pass 1 needs `kind`, `actor_type`, `evidence_type` and `evidence_scope` on every item; "leave it empty" produces invalid records or unmatched kappa units.

### Minor

- **N-13. e05 i4 treats one pronoun two ways.** `mode` is empty because the quote says only "sie", but `states_solution` is true because "sie" is the rail line. After the re-cut the quote also no longer asks for anything; it predicts uptake. With false, the link i5 → i4 becomes the clean pattern "measure linked to the need behind it".
- **N-14. `actor_pair`: the named cause sits in the victim's quote.** In e04 "because I block the bike lane" is inside i3, and i4 "because of my van" names a cause with no causing item. The rule does not say which item is `from` in that case.
- **N-15. `means_end` with "deshalb", and `order` with "events".** "Deshalb" points back to a whole argument (e05: i1 to i4); the example takes the nearest item, the rule does not say so. "Link only items that are events" has no definition of an event.
- **N-16. `evidence_scope.quantified`: share of events against share of a stock.** "Half the fast chargers I try" (e10 i2) and "jeder fünften Tour" (e11 i2) are quantified; "a third of our posts" (e06 i3) is single. A growth rate ("rose by 30 percent", e06 i2) counts as quantified. The rule names neither case.
- **N-17. `improve`: small inconsistencies.** Missing equipment is empty in e16 i1, missing staff is `other` (e13 i1, e09 i4). "Im Stau stehen" is `time` (e05 i3), "volle Straßen" is empty (e13 i2). e10 i4 names paying more and has no `cost`.
- **N-18. `mode`: verbs.** "No longer drive" gives car (e12 i1). The rule speaks of words that belong to one mode and gives only nouns.
- **N-19. P2 empties the `order` field.** Sequences of activities ("zuerst … dann") are no longer items, so order links exist only between needs that are events: 2 in 67 items, both constructed. Interface row 11 (experience-map sequence) will get little. No change proposed; the owner should know.
- **N-20. README row 11** still promises "the words that order them"; `link_encoding` has no field for them.
- **N-21. `reader`** is German and not on the list of keys the template leaves out (agent's point 5).
- **N-22. Small definition gaps.** Tokenisation for the token IoU; when two links agree (ends and direction); `same_need_twice` is a boundary rule filed under `evidence_type`.

## 4. The agent's points

Read as: the seven bullets of section 8 of the change log plus the text change in e05 (section 3). The 13 points of section 2 follow in short form.

| # | Point | Verdict |
|---|---|---|
| 1 | R-15 rest: domain test per text or item, "backdrop" | **Change.** Add wording M-9. |
| 2 | R-22 rest: `doubt.fields` against required fields | **Change.** Add wording M-10. |
| 3 | R-24: export must not filter by evidence rank | **Keep** out of the labeler text. Add a non-printed YAML comment above `evidence_type`: "The scale orders the kind of backing, not its value; the export must not filter or sort by it (Fable review 1, R-24). Review note, not printed." |
| 4 | R-29: roadmap phases 7 and 8 | **Keep** (outside these files). It must be picked up in the roadmap before phase 7, now also because of the three passes. |
| 5 | `reader` has no English version | **Change.** Add `reader_en.text`: "A product manager." and add `reader` to the keys that `assembly.rule` does not print. |
| 6 | P2 against e07: "Ich nehme das Rad" as a job | **Owner decides** (decision 3). Recommended: keep it as a job and say why (M-4). |
| 7 | Judgement calls: e09 i1 society against e12 i4 individual; e16 i4 job against e04 i6 gain | **Change** both, after owner decisions 4 and 5. Recommended: e09 i1 and e09 i6 become individual; e16 i4 becomes a gain. |
| 8 | e05 text change (the survey figure now counts employees without an alternative) | **Keep.** The figure now measures the pain, which makes measurement and quantified teachable. The text is invented, so nothing is lost. |

Section 2 of the change log:

| # | Point | Verdict |
|---|---|---|
| 2.1 | Coordinating conjunctions inside the quote | Keep. One token never decides a match, and "the clause as it stands" is the simplest rule. Name both kinds in the rule (M-3). |
| 2.2 | Reporting frames outside | Keep, but write it into the rule (M-3). |
| 2.3 | `reported_speech` | Change (M-1); it causes N-01. |
| 2.4 | Estimates: "or routine when …" | Keep. |
| 2.5 | Occurrence inside the quote first | Keep, with two additions (M-8). |
| 2.6 | `situation` without article or preposition, time words | Keep; add possessives and demonstratives (M-7). |
| 2.7 | `improve` lines | Keep, with two edits (M-11). |
| 2.8 | `doubt.levels` states the order | Keep. |
| 2.9 | Relation names `causes`, `in_order_to` | Keep. |
| 2.10 | Threshold details; sub-sample size not set | Keep the details; the size must be set (decision 9). |
| 2.11 | `drop_order.trigger` | Keep. |
| 2.12 | Baselines use the same passes | Keep. |
| 2.13 | `quote.rule` | Keep. |

## 5. Mitigations with exact wordings

**M-1 (N-01, N-08). `evidence_type`.** Replace `reported_speech` by:

> The speaker is the person or body whose statement the text gives: the author of a first-person text, or the person a news text or minutes quote. A journalist or minute-taker who only passes a statement on is not the speaker. What third persons told that speaker is graded from the speaker's side, as below.

Replace the first four sentences of `boundaries` by an ordered test:

> Grade by the basis the speaker gives, and take the first line that fits. 1. A counted or measured figure with its source: measurement. 2. One concrete event, whoever it happened to and whoever told it: anecdote. 3. The speaker's own repeated experience, shown by a word of frequency, by habitual present tense about the speaker's own trips ("I take", "wenn ich … muss") or by a share of the speaker's own attempts: routine. 4. A statement about several other people or a longer time, when the text says how the speaker knows it (they were told, or they were there) or gives an estimated figure: observation. 5. Everything else, including a plain statement of how things are ("the bus runs twice a day"): opinion.

The sentence on estimates stays. Consequence in the examples: e16 i3 becomes anecdote (decision 2); all other labels stay.

**M-2 (N-02). `assembly.passes` and `definitions`.** Replace the pass 3 sentence by:

> Pass 3: links, on every chunk with at least two items.

Add to `passes`: "In the agreement pilot each reference runs all three passes on its own items; nothing is shared between the references." Add a new key `link_connectives` with a closed list that code uses only to draw the enriched sub-sample: `means_end: [um … zu, damit, deshalb, dafür, in order to, so that]`, `order: [zuerst, danach, bevor, nachdem, während, first, afterwards, before, after, while]`, `actor_pair: [weil, wegen, because, because of]` together with at least two different role words in the chunk. Change `link_sample` to "… chunks in which code finds a word of `link_connectives`". Add to `definitions.links`: "Two links agree when both ends are matched items, the direction is the same and the relation is the same."

**M-3 (N-04). `item_boundaries.rule`.** Add after "A cause or consequence … unless it is a need of its own":

> It is a need of its own when it names another burden or another actor than the clause before it. A purpose joined with 'um … zu', 'damit', 'in order to' or 'so that' is an item of its own, and so is the clause it depends on. The opening conjunction may be of either kind ('und', 'aber', 'dass', 'and', 'but', 'that'). A frame that only says who said it ('Viele sagen mir, dass', 'People tell us', 'ich schätze') stays outside the quote; a source named inside the clause ('laut der Erhebung') and a verb that itself states the problem ('complain', 'sich beschweren', 'worry') stay inside.

Replace "Two needs joined by 'and' are two items" by "Two clauses joined by 'and' are two items when they name different burdens or actors."

**M-4 (N-05). `kind.job_versus_gain`.** Add:

> This test decides, whatever word the text uses ('goal', 'Ziel', 'need'). A step the actor takes for a stated purpose is a job and is linked to its goal with means_end. A wish for a thing or measure is a gain with states_solution true, also when it has a verb of doing ('order', 'build', 'introduce').

Examples: e16 i4 kind gain, job_kind null. e16 i5 kind pain, job_kind null (an obstacle before the job; the order link stays).

**M-5 (N-06). `kind.feelings`.** Replace by:

> A bad feeling reported as a fact is a pain, a good one a gain. A wish to feel or not to feel something is a job with job_kind emotional, also when it is about how the trip goes; this rule comes before job_versus_gain.

In `improve.comfort`, replace "or arriving rushed" by "or noise on board".

**M-6 (N-07). `actor_type.society`.** Replace by:

> The public at large, only when the text says so in words ('alle', 'everyone', 'die Allgemeinheit', 'the public'). The people of a place and generic 'man', 'one' or 'you' are individual.

Examples: e09 i1 and e09 i6 become individual; the `shows` entry of e09 is corrected.

**M-7 (N-09). `situation.rule`.** Change "without article or preposition" to "without article, possessive, demonstrative or preposition". Add:

> A place, time or occasion counts for an item when it is named in the item's sentence, or when the item points back to it ('there', 'dort', 'dabei', 'dafür'). A time of day or day of the week counts also inside a phrase of frequency: from 'jeden Morgen' point to 'Morgen'. For a job, its own destination or purpose is part of the need; for a pain or gain on that trip, it is a situation. Weather counts as an occasion.

Examples: e13 i2 "Festen"; e16 i3 "hill estates"; e12 i3 "high street"; e05 i3, e07 i6 and e15 i1 "Morgen" (decision 7).

**M-8 (N-10). `executor_role.rule`.** Add:

> A role named inside the quote comes before a role named elsewhere for the same actor. If the words occur only after the quote, the nearest occurrence after it counts. A speaker tag counts as a role only when it names the actor itself and the running text names none.

Change the generic words to: "'I', 'we', 'people', 'members', 'Leute'".

**M-9 (N-11). `relevant.definition`.** Add at the end:

> The test applies to each item: the need, or the trip or transport on which it arises, must lie within mobility. What a mobility problem does to the actor (being late for work, feeling cut off) is an item. A need about something else that is only mentioned on the way is no item.

**M-10 (N-12). `doubt.fields`.** Replace by:

> job_kind, mode, improve, executor_role and situation stay empty when they are not stated or you are unsure; an empty field is correct. kind, actor_type, evidence_type and evidence_scope are never empty: use the rules for kind and levels above, and for actor_type take the type of the persons the need is about.

**M-11 (N-13, N-16 to N-18). Small edits.**

- e05 i4: `states_solution` false.
- `evidence_scope.quantified`, add: "A share counts when it is a share of people or events; a share of a stock, such as posts or vehicles, is the size of the problem."
- `improve.other`: "… such as staff or equipment." e16 i1: `improve` [other].
- `mode.rule`, add: "A verb counts when it belongs to one mode (walk, cycle, fly, drive for car); 'fahren', 'ride' and 'travel' name none."
- README row 11: delete "with the words that order them".
- `definitions.matching`, add: "Tokens are split at white space."

**M-12 (N-03). `pilot_thresholds.decision`.** Replace by:

> A field is produced when its estimate meets the threshold and the lower bound of its interval meets the floor; a field with two numbers needs both. First count the units: with fewer than 30 the field is underpowered whatever its estimate, and the sample is extended once, to at most twice its size; a field that is still underpowered is not produced in this version and is listed as not measured. With 30 or more units: an estimate below the floor means not produced; an estimate between floor and threshold gets one guideline revision and is scored again on a fresh holdout of the same size as the pilot, and is then produced only if it meets this rule; an estimate at the threshold with a lower bound below the floor is extended once in the same way.

Replace `keep_always_stop` by:

> A keep_always field that would be not produced under the decision rule, at any step, stops the pilot in that language, and the guideline goes back to the owner. It is never dropped. relevance_kappa stands for relevant and item_matching_f1 for quote.

## 6. Decisions for the owner

The first option is the recommendation.

1. **Who is "the speaker" for evidence (M-1)?** (a) The voice the text carries: the author of a first-person text or the person a news text quotes; what others told that speaker is graded from the speaker's side. (b) Always the innermost person whose words are reported. (c) Always the author of the text.
2. **One event that the person concerned told the speaker (e16 i3).** (a) Anecdote: a single event is an anecdote whoever tells it. (b) Observation, as now.
3. **A step taken for a stated purpose (e07 i1 "Ich nehme das Rad").** (a) A job of its own, linked by means_end, with the sentence of M-4. (b) No item of its own: the whole sentence is one job and there is no link. (c) Keep the example without a rule.
4. **A wish for a means with a verb of doing (e16 i4 "order four more lorries").** (a) Gain with states_solution true, like e04 i6. (b) Job, as now.
5. **`society`.** (a) Only with explicit words for everyone; e09 i1 and i6 become individual. (b) Also the people of a named place; e09 i2 and i5 become society. (c) Keep e09 as it is.
6. **A wish about a feeling on the trip (e07 i6).** (a) Emotional job; `feelings` comes before `job_versus_gain`. (b) Gain with comfort; emotional jobs are only wishes with a feeling word.
7. **Time of day inside a frequency phrase ("jeden Morgen").** (a) The time word counts as situation. (b) No habitual time counts, so "Morgens" and "Saturdays" become empty too. (c) Keep as it is.
8. **Pass 3 (M-2).** (a) On every chunk with at least two items; a closed connective list only draws the enriched sample. (b) Keep the gate, with a closed list that includes causal words. (c) Keep as written.
9. **Size of the enriched link sub-sample.** (a) 100 chunks per language, extended once to 200 if a link type has fewer than 30 units. (b) Draw until each link type has 30 units, at most 300 chunks. (c) No enriched sample; links are decided on the random pilot alone.
10. **Decision rule (M-12).** (a) Adopt M-12: one extension, a keep-always field that would not be produced stops the pilot in that language. (b) Same, but a keep-always stop in one language stops both. (c) Keep the current text.

## 7. Pilot readiness

Not yet. Before the owner's formal approval:

1. Fix the three blockers: M-1, M-2, M-12 (decisions 1, 8, 9, 10).
2. Apply the wordings for the major issues: M-3 to M-10 (decisions 2 to 7).
3. Correct the labels that follow: e05 i4; e09 i1, i6; e12 i3; e13 i2; e16 i1, i3, i4, i5; the situation of e05 i3, e07 i6, e15 i1 under decision 7 (a). Extend `check_examples.py` only if a new rule is checkable by code (pointer without determiner, pass 3 on every chunk with two items).
4. Run the checker again and regenerate the change log from the files.

After that the package can go to formal approval with hashes and then to the pilot. A third full review is not needed; a diff check of the changed keys and the nine or so changed items is enough. R-18, R-24 and R-29 stay open by decision or scope and do not block the pilot.
