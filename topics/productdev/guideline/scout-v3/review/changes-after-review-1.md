# Changes after Fable review 1

Date: 2026-11-28. Basis: `fable-review-1.md` and the owner's decisions recorded in `../brief-provenance.md` (all 15 questions of section 7 plus P5, P15, P16 and P17, recommended option each time, nothing rejected). Drafted by Claude under constitution 3.2.0. Every wording below is a Claude draft and is not valid before the owner approves it. No file under `data/` was read, no real text was labeled and no model output was judged; all example texts are invented.

Files changed: `../brief.yaml`, `../examples.yaml`, `../../../research/opportunity-interface/README.md`. New: `../check_examples.py`, this file.

How to read section 1: each heading is a top-level key of `brief.yaml` (or a nested key with its own approval). Sub-keys are marked *new*, *changed* or *unchanged* against the last commit; unchanged sub-keys are listed so that each key reads in full. Owner answers (`owner`, `*_choice`, `cases_owner`, `teacher_task`, `reader`) are untouched and not repeated. The texts are copied from `brief.yaml` by script, so they match the file exactly. 24 keys carry `approval: pending`; `domain.definition`, `empty_result`, `reader`, `language` and `teacher_task` keep their status.

## 1. Changed and new keys of `brief.yaml`

### `teacher_task_en`

Implements: note (f), decision 14. New English operative version of the owner's German `teacher_task`, which stays verbatim.

Approval: pending.

- `text` (new): Find where the text states pains, gains and jobs to be done. Each of them is then enriched with further fields, as given in the list of fields.

### `domain.owner_en`

Implements: note (f), decision 14. New English operative version of the owner's German `domain.owner`, which stays verbatim. `domain.definition` is unchanged and keeps its approval.

Approval: pending.

- `text` (new): Follow the definition of mobility; everything that belongs to it also belongs to our topic.

### `item_boundaries`

Implements: P1, note (f), decisions 1 and 14. New `rule`: the P1 wording verbatim; it is the English operative version of the owner's sentence, which stays verbatim under `owner`.

Approval: pending.

- `rule` (new): An item is one need. Its quote is the shortest run of whole clauses that states the need, including the words that mark it as a wish, fear or problem (such as 'I want', 'schön wäre', 'I worry that') and the conjunction that opens a clause. A need may run over several sentences. A cause or consequence joined with 'so', 'because', 'weil' or 'sodass' belongs to the same item unless it is a need of its own. Two needs joined by 'and' are two items. Quotes of one text never overlap. Offsets are computed by code.

### `relevant`

Implements: P2, decision 2. Adds "hopes for something or values an outcome they have" to the list of what an actor does, so that a fulfilled gain makes a text relevant.

Approval: pending (previous: owner, 2026-11-28, in chat).

- `definition` (changed): A text is relevant when it states at least one job, pain or gain of an actor within mobility as defined under domain, told by the actor or reported by someone else. The topic alone is not enough. Not relevant: texts that only report facts, figures, events or product features with no actor who wants to get something done, struggles, hopes for something or values an outcome they have; timetables, tariffs and technical specifications; a provider praising its own offer without reporting a customer's need; texts where mobility is only the backdrop of something else. One passage with a need is enough, even if the rest of the text is off-topic.

### `kind`

Implements: P2, P15, P1; decisions 2 and 1. `job`: the sentence "State it, where the text allows, apart from the solution used today" is deleted (P2, R-22). `job_versus_gain` is new (P2 verbatim). `feelings` is new (P15 verbatim). `pain_versus_negated_gain`: the last sentence is replaced by the P1 wording.

Approval: pending (previous: owner, 2026-11-28, in chat).

- `job` (changed): Something an actor is trying to get done or achieve in a situation: a task, a goal or a change of state they want.
- `pain` (unchanged): Something that bothers the actor before, during or after getting the job done: an obstacle, a cost, a risk, an annoyance, a bad outcome, or the fear of one.
- `gain` (unchanged): An outcome or benefit the actor wants, expects or would welcome: something that makes the job easier, faster, cheaper, safer or more pleasant, or a good outcome they already value.
- `job_versus_gain` (new): A job is what the actor wants to get done: it has its own verb of doing and stays the same when the means change. A wish about how well, fast, cheaply, safely or reliably it goes is a gain. A sentence that only reports what someone does, with no want, purpose, obstacle or judgement, is not an item.
- `feelings` (new): A feeling reported as a fact is a pain; a feeling the actor wants or wants to avoid is a job.
- `pain_versus_negated_gain` (changed): Label by what the text describes. A problem the actor has now is a pain, even when phrased as a missing benefit. A wish for a better state is a gain, even when phrased with a negation. Label both only when each has its own clause; otherwise take the kind the wording has.

### `actor_type`

Implements: P10, decision 9. `rule` gains the sentence on needs voiced for others; `individual` now covers groups of private persons; `worker` gains the commuting sentence; `society` drops "or an unnamed group".

Approval: pending (previous: owner, 2026-11-28, in chat).

- `rule` (changed): The actor is who has the need, not who speaks or writes. A need voiced on behalf of others takes the type of those who have it; the speaker's body is the actor only for its own need (budget, staff, duties). actor_type is the coarse class; executor_role marks the words that name the specific role.
- `individual` (changed): Private persons acting for themselves or their household, one or many, including named groups such as commuters or residents.
- `worker` (changed): A person whose need comes from their work in or around mobility. Commuting is not work in mobility.
- `organization` (unchanged): A company, operator, association or other non-state body acting as such.
- `public_sector` (unchanged): A public authority or public body acting as such.
- `society` (changed): The public at large, only when the need is stated for everyone.

### `evidence_type`

Implements: P9, notes (c) and (d), decisions 7 and 8. `boundaries` opens with the three P9 sentences. The approved sentence on estimates is extended ("or routine when it is a share of the speaker's own repeated experience") so that it does not contradict P9. `reported_speech` is new (Claude's addition, see section 3). `same_need_twice` is new (note d).

Approval: pending (previous: owner, 2026-11-28, in chat).

- `rule` (unchanged): How the text backs the need, as an ordinal scale from opinion (lowest) to measurement (highest).
- `opinion` (unchanged): A view, belief, wish or judgement with no experience given.
- `anecdote` (unchanged): One concrete experience, a single event.
- `routine` (unchanged): Repeated or habitual experience of the actor (always, every day, usually).
- `observation` (unchanged): Something seen across other people or over a longer time, stated without a figure from counting or measuring.
- `measurement` (unchanged): A figure obtained by counting or measuring, such as a survey result, a statistic or a measured time.
- `boundaries` (changed): Grade by what the speaker gives as basis. A general claim with no experience or source is an opinion. What others told the speaker is an observation. A share from the speaker's own repeated experience is routine. Anecdote versus routine: one event is an anecdote; words of frequency or several events make it routine. Observation versus measurement: a measurement needs a figure that was counted or measured; an estimate such as "about half, I would say" is an observation, or routine when it is a share of the speaker's own repeated experience.
- `reported_speech` (new): In reported speech, the speaker is the person whose words are reported, not the writer who reports them.
- `same_need_twice` (new): The same need stated again in a separate passage that does not overlap the first is a second item with its own evidence.

### `evidence_scope`

Implements: P9, notes (a) and (c), decisions 5 and 7. New `rule` with note (a), the collective-speaker rule and the declared order. `quantified` rewritten with note (c).

Approval: pending (previous: owner, 2026-11-28, in chat).

- `rule` (new): Scope counts actors or cases; frequency belongs to evidence_type. One person's routine is single. A body speaking of its own need is one actor. The order is single, multiple, quantified.
- `single` (unchanged): One case, one actor or one event.
- `multiple` (unchanged): Several or many cases, stated without a number.
- `quantified` (changed): The text gives a number or share of the actors or occurrences that have the need, such as people, trips, tours or complaints; an estimate with a figure counts. Durations, distances, prices, times of day and the size of an operation do not count.

### `quote`

Implements: P1 (R-23). "with its offsets" replaced: code computes offsets, the labeler does not count characters. Follows from the last sentence of P1.

Approval: pending.

- `rule` (changed): Each item is a verbatim quote in the source language. Code computes its offsets; the labeler does not count characters. No statement or translation is written per item.

### `doubt`

Implements: P1, P9. `kind` replaced by the P1 wording. `levels` states the order of evidence_scope (P9 offered this or restricting the rule to evidence_type; Claude chose the order).

Approval: pending (previous: owner, 2026-11-28, in chat).

- `item` (unchanged): When unsure whether a passage is an item, ask whether a product manager could learn a need from it. If not, leave it out. Never add context that the text does not give.
- `kind` (changed): Take the kind the wording has; label both only when each has its own clause.
- `levels` (changed): For evidence_type and evidence_scope, take the lower grade. evidence_scope is ordered single, multiple, quantified.
- `fields` (unchanged): When a field is not stated or you are unsure, leave it empty. An empty field is correct.

### `job_kind`

Implements: P15, P1. `rule` documents that only jobs carry job_kind (P15 minimal) and applies the P1 wording to the two-jobs case.

Approval: pending (previous: owner, 2026-11-28, in chat).

- `applies_to` (unchanged): job
- `functional` (unchanged): The practical task or result the actor wants to get done.
- `emotional` (unchanged): How the actor wants to feel, or wants to avoid feeling, while getting it done.
- `social` (unchanged): How the actor wants to be seen by others, or to stand with them.
- `rule` (changed): One value per job item: the one the text stresses. Only jobs carry job_kind; it stays empty for pains and gains, also when they have an emotional or social side. If a passage states a practical and a feeling side, label two jobs only when each has its own clause; otherwise take the value the wording stresses.

### `executor_role`

Implements: P6, decision 10. "Shortest verbatim span" replaced by the defining noun phrase; nearest-occurrence rule; pointer inside the labeled text; role applies to all items of the same actor; generic words get no role.

Approval: pending (previous: owner, 2026-11-28, in chat).

- `rule` (changed): A pointer to the noun phrase, without article, with the modifiers that define the role, that names who has the need: what the person or body is, such as an occupation, a life situation or an organisation type. The pointer must lie in the text the labeler is given, inside or outside the item's quote. If the same words occur more than once, the occurrence inside the quote counts, else the one nearest before it; code resolves offsets. A role named for the same actor applies to all of that actor's items. Pronouns and generic words such as "I", "we" or "people" get no role. If several roles are named, take the one that has this need. Empty if no role is named.

### `link_encoding`

Implements: P5. New key: one `{from, to, relation}` encoding for all three link fields.

Approval: pending.

- `rule` (new): Every link is written as {from, to, relation}: from and to are ids of items of the same text, and relation is one of the values of the link field.

### `actor_pair`

Implements: P5. New `values` [causes]. `rule` rewritten as a directed link from the causing item (job or pain) to the other actor's pain; the text must name the cause.

Approval: pending (previous: owner, 2026-11-28, in chat).

- `values` (new): `[causes]`
- `rule` (changed): A directed link from the item of the actor who causes to the pain of the actor who suffers, when the text says that the one causes the other at the same place, time or resource. The causing item may be a job or a pain. The text must name the cause. Both items must be in the text, and their actors differ. A clash known only from general knowledge is not linked. Written as {from: causing item, to: pain, relation: causes}.

### `mode`

Implements: P8, note (b), decision 6. `rule`: decide on the words of the quote, negated or missing modes count (reverses the earlier bracketed reading). New `boundaries` with the border lines of P8.

Approval: pending (previous: owner, 2026-11-28, in chat).

- `values` (unchanged): `[walk, bicycle, micromobility, motorcycle, car, taxi_ridehailing, bus, tram_metro, train, coach, public_transport, truck_van, air, water, other]`
- `rule` (changed): All modes named in the item's quote, as a list. Decide on the words of the quote: every mode named counts, also when it is negated or missing. Use public_transport when the text names public transport without a mode. A word that belongs to exactly one mode counts, such as a bus driver for bus or a wallbox for car. Empty if the quote names no mode; do not infer one from the context alone.
- `boundaries` (new): A pedelec is bicycle. E-scooters and other small electric devices are micromobility. A moped is motorcycle. Minibus and on-demand shuttle are bus. A freight train is train. Charger, petrol station, motorway and parking give car only together with a vehicle word. Use other only for a named mode outside the list.

### `situation`

Implements: P6, P12, decision 10. `rule` rewritten: noun phrase pointer and occurrence rule (P6), priority place before occasion before time and the four non-situations (P12). A YAML comment records that typed situations are a later format version (P12).

Approval: pending (previous: owner, 2026-11-28, in chat).

- `rule` (changed): A pointer to the noun phrase (or time word), without article or preposition, with the modifiers that define where, when or on what occasion the need arises: a place, a time of day, week or year, or an occasion such as a trip purpose or what the actor carries. The pointer must lie in the text the labeler is given, inside or outside the item's quote. If the same words occur more than once, the occurrence inside the quote counts, else the one nearest before it; code resolves offsets. Place before occasion before time when several are tied to the need. Not a situation: words of frequency (every day, immer), the date of a single event, the destination or object that is part of the need itself, and parts of a wished solution. Empty if none is named.

### `improve`

Implements: P11, decision 15. Direction sentence deleted; "Only values the text states" replaced by the P11 wording; one line per value with the P11 tie rules. A YAML comment records that the export derives direction from a polarity table.

Approval: pending (previous: owner, 2026-11-28, in chat).

- `values` (unchanged): `[time, cost, effort, reliability, safety, comfort, access, information, flexibility, environment, other]`
- `rule` (changed): The dimensions the item is about, as a list, for jobs, pains and gains. Only when the quote names or clearly describes the dimension. When two values fit, follow the lines below. Empty if no dimension is named or described.
- `time` (new): How long it takes, including waiting and detours; a duration is time.
- `cost` (new): Money the actor pays or lacks, such as fares, fuel, fines, prices or budgets.
- `effort` (new): Steps, planning and hassle needed to get it done.
- `reliability` (new): Whether it happens as planned; late, cancelled, broken down or unpredictable is reliability.
- `safety` (new): Risk of accident, injury or other harm.
- `comfort` (new): How pleasant and calm the trip is, such as shelter, seats, crowding or arriving rushed.
- `access` (new): Whether a service, place or vehicle is available or within reach at all.
- `information` (new): What the actor knows or can find out, such as timetables, delays or changes.
- `flexibility` (new): Choice of time or route, including how often a service runs.
- `environment` (new): Emissions, noise and other effects of traffic on people and nature around it.
- `other` (new): Only when the quote describes a dimension that is not on this list, such as staff.

### `states_solution`

Implements: P7, decision 4. `rule`: the Torres test replaces "names a concrete product, service, feature or measure". No third value.

Approval: pending (previous: owner, 2026-11-28, in chat).

- `rule` (changed): True when the quote asks for a particular thing or measure, so that only one way would satisfy it (a named product, a new facility, a specific rule or schedule). False when it asks for a property or result that several things could deliver, and false otherwise. The item keeps its kind and is not dropped. The need behind it is a separate item only if the text states it.

### `means_end`

Implements: P5. New `values` [in_order_to]. "because I need to" dropped; the connecting words must join the two quotes; "deshalb" and the measure-for-need reading added.

Approval: pending (previous: owner, 2026-11-28, in chat).

- `values` (new): `[in_order_to]`
- `rule` (changed): A directed link from item A to item B of the same actor when the text says that A is done or wanted in order to achieve B, or that A is the measure the actor wants for B. The connecting words must join the two quotes, such as "um zu", "damit", "deshalb", "in order to" or "so that". No link when the connection is only implied. Items of different actors are not linked here. Written as {from: A, to: B, relation: in_order_to}.

### `order`

Implements: P5. New `values` kept [before, during]. `rule`: only events; "A after B" written as B before A; during has no direction, the earlier quote is `from`.

Approval: pending (previous: owner, 2026-11-28, in chat).

- `values` (unchanged): `[before, during]`
- `rule` (changed): A link between two items of one text when words in the text order them in time, such as "zuerst", "dann", "bevor", "während", "first", "then", "after" or "while". Link only items that are events. before means that from comes before to; write "A after B" as B before A. during means that both happen at the same time; it has no direction, so the earlier quote is from. The order of sentences alone does not count. Order across texts is never labeled.

### `examples`

Implements: P13, decision 13. New `size`: 16, 8 de and 8 en. `size_choice` stays verbatim.

Approval: pending (previous: owner, 2026-11-28, in chat; distribution gaps go to the Fable review).

- `size` (new): 16, 8 de and 8 en (Fable review 1, decision 13)

### `assembly`

Implements: P16, note (f); decisions 14 and P16. `rule`: the template prints the English operative versions and not the German owner answers (note f); `previous_approval` added to the stripped keys. New `passes` (P16).

Approval: pending.

- `rule` (changed): Code assembles the guideline package from brief.yaml and examples.yaml with a fixed template. The template prints the English operative versions (teacher_task_en, domain.owner_en, item_boundaries.rule); the owner's German answers (teacher_task, domain.owner, item_boundaries.owner, examples.cases_owner) stay verbatim in brief.yaml and in the provenance and are not printed. Review-only keys (shows, drafted_by, approval, previous_approval and the *_choice keys) are stripped. The owner approves the assembled package with sha256 hashes before any labeling run.
- `passes` (new): Labeling runs in three passes. Pass 1: items with quote, kind, actor_type, evidence_type and evidence_scope; relevant follows from them. Pass 2: the other attributes and the pointers, on the fixed items of pass 1. Pass 3: links, only on chunks in which code finds a connecting word named in the link rules. A pointer that is not a verbatim part of the given text is set to empty and counted, not retried. The zero-shot baselines use the same passes.

### `pilot_thresholds`

Implements: P3, P4, section 5, R-14; decisions 11 and 12. Rebuilt: a `definitions` block (P3), per-field thresholds and floors (section 5), links on matched pairs with threshold 0.5 and floor 0.3 and an enriched sub-sample (P4, note e), `reported_only`, a `decision` rule, the `keep_always` stop rule and the per-language rule. The old `core`, `attributes`, `pointers`, `links`, `revise_band` and `not_produced` keys are replaced. `status: provisional` and `owner_choice` stay.

Approval: pending.

Full new wording:

```yaml
status: provisional
owner_choice: Freigeben (vorläufig)
per:
- field
- language
definitions:
  matching: Items of two references are matched one to one when the token IoU of their quotes is at least
    0.5, after stripping punctuation at the edges; pairs with the highest IoU are matched first.
  item_matching: F1 of matched items. The F1 at any overlap is reported next to it and not used for the
    decision.
  relevance: Cohen's kappa over all chunks of the pilot. Raw agreement and a prevalence-robust coefficient
    (Gwet's AC1) are reported next to it.
  attributes: Cohen's kappa on items matched by both references, for kind, actor_type, evidence_scope
    and states_solution; job_kind only on matched items that both references call job. evidence_type uses
    a weighted kappa with linear weights.
  lists: 'mode and improve: Krippendorff''s alpha with the MASI set distance on matched items; both empty
    counts as agreement. For improve, a kappa per value is reported to find values to merge.'
  pointers: 'executor_role and situation: two numbers each, on matched items. A kappa of filled against
    empty, and a token F1 on items that both references filled, comparing the pointed strings, not their
    offsets.'
  links: 'Scored only on pairs of items that both references matched: F1 of the links between matched
    items. The end-to-end F1 is reported next to it and not used for the decision. For order, the relation
    (before or during) is reported as a separate kappa on links both references found.'
  link_sample: 'Links are scored on the random pilot plus an enriched sub-sample: chunks in which code
    finds one of the connecting words named in the link rules. Link prevalence is never estimated from
    the enriched sub-sample.'
  intervals: 95 % bootstrap intervals, resampling chunks.
  units: Items or links that at least one reference filled, counted per field and language.
  pilot_size: 100 chunks per language drawn at random, plus the enriched link sub-sample.
  revision: After a guideline revision, fields are scored again on a fresh holdout, not on the pilot chunks.
thresholds:
  core:
    relevance_kappa:
      threshold: 0.75
      floor: 0.6
    item_matching_f1:
      threshold: 0.6
      floor: 0.45
    kind_kappa:
      threshold: 0.6
      floor: 0.4
    actor_type_kappa:
      threshold: 0.6
      floor: 0.4
    evidence_scope_kappa:
      threshold: 0.6
      floor: 0.4
    evidence_type_weighted_kappa:
      threshold: 0.5
      floor: 0.4
  attributes:
    job_kind_kappa:
      threshold: 0.5
      floor: 0.4
      on_fail: collapse to functional against other and score again before dropping
    mode_masi_alpha:
      threshold: 0.7
      floor: 0.4
    improve_masi_alpha:
      threshold: 0.5
      floor: 0.35
    states_solution_kappa:
      threshold: 0.5
      floor: 0.4
    states_solution_true_f1:
      threshold: 0.6
      floor: 0.4
      min_true_items: 30
  pointers:
    executor_role_filled_kappa:
      threshold: 0.6
      floor: 0.4
    executor_role_token_f1:
      threshold: 0.6
      floor: 0.4
    situation_filled_kappa:
      threshold: 0.6
      floor: 0.4
    situation_token_f1:
      threshold: 0.6
      floor: 0.4
  links:
    actor_pair_f1:
      threshold: 0.5
      floor: 0.3
    means_end_f1:
      threshold: 0.5
      floor: 0.3
    order_f1:
      threshold: 0.5
      floor: 0.3
reported_only:
- relevance raw agreement and Gwet's AC1
- evidence_scope Gwet's AC1
- item F1 at any overlap
- end-to-end F1 of each link field
- order relation kappa
- improve kappa per value
- actor_type per class, with society marked as underpowered
decision: 'A field is produced when its estimate meets the threshold and the lower bound of its interval
  meets the floor; a field with two numbers needs both. An estimate between floor and threshold gets one
  guideline revision, and the field is then produced only if it meets this rule on the holdout. An estimate
  below the floor means not produced. An estimate that meets the threshold with a lower bound below the
  floor, or fewer than 30 units, means underpowered: extend the sample. Too few units is never by itself
  a reason not to produce a field.'
keep_always_stop: A keep_always field whose estimate falls below its floor stops the pilot, and the guideline
  goes back to the owner. It is never dropped.
per_language: Each field is decided per language and is produced only in the languages where it passed.
```

### `drop_order`

Implements: P17, P3. `order` reordered as P17 proposes. New `trigger` (P3: drop order applies only when the core-does-not-pay test fails). `keep_always` unchanged.

Approval: pending.

- `order` (changed): `[actor_pair, order, means_end, executor_role, situation, states_solution, job_kind, improve, mode]`
- `trigger` (new): The drop order applies only when the model's core-does-not-pay test fails: item-matching F1 or relevance of the model with the extra fields falls below the same model without them, beyond the bootstrap interval. Fields are then dropped in this order until the test passes.
- `keep_always` (unchanged): `[relevant, kind, quote, actor_type, evidence_type, evidence_scope]`

## 2. Where Claude went beyond the report's wording

The report gives exact wordings for most changes. Where it did not, or where its wordings collide, Claude wrote the following. Each needs the owner's explicit look.

1. **Conjunctions in quotes (P1).** P1 says the quote includes "the conjunction that opens a clause" and does not distinguish "und/and/aber/but" from "dass/weil/wenn". The examples include both kinds (e05 i3 "und sie trotzdem …", e12 i5 "but some pull away …"). The alternative is to include only subordinating conjunctions.
2. **Reporting frames stay outside (P1).** "Viele Pendler sagen mir, dass …", "several members have told me …", "People tell us …" are not wish, fear or problem markers, so the examples leave them outside the quote. P1 does not say this explicitly.
3. **`evidence_type.reported_speech` (new sentence).** P9 says "What others told the speaker is an observation", while P13 asks for third-person news items graded as opinion. Without a rule on who "the speaker" is, a journalist quoting a spokesperson would turn every claim into an observation. Added: in reported speech the speaker is the person whose words are reported.
4. **Estimates in `evidence_type.boundaries`.** The approved sentence "an estimate … is an observation" contradicts P9's "a share from the speaker's own repeated experience is routine" (e10 i2, e11 i2). Extended with "or routine when it is a share of the speaker's own repeated experience".
5. **Pointer occurrence rule (P6).** "The occurrence nearest before the quote counts" leaves open what happens when the words occur inside the quote. Written as "the occurrence inside the quote counts, else the one nearest before it".
6. **`situation` form.** "Without article or preposition" and "(or time word)" were added, so that "on the motorway" gives "motorway" and adverbs such as "Morgens" are allowed.
7. **`improve` value lines (P11).** P11 gives tie rules for six values; the lines for cost, safety, comfort, information and environment are Claude's wording. Two additions resolve inconsistencies the review found: "including how often a service runs" under flexibility (e03 "zweimal am Tag"), and "such as staff" under other (staff shortage was other in one example and effort in another). The opening sentence "What the actor wants more or less of" implied a direction and was replaced by "The dimensions the item is about".
8. **`doubt.levels` (P9).** P9 offered two options; Claude chose to state the order single, multiple, quantified rather than restricting the rule to evidence_type.
9. **Link relation names (P5).** `causes` and `in_order_to` are Claude's names; P5 fixes only the `{from, to, relation}` shape.
10. **`pilot_thresholds` details (P3, section 5).** Not in the report and added by Claude: one-to-one matching takes the highest IoU first; the prevalence-robust coefficient is named (Gwet's AC1); floor 0.4 wherever section 5 gives no band (the old general floor); a field with two numbers needs both; an estimate at the threshold with a lower bound below the floor counts as underpowered; after the one revision the field is produced only if it then passes on the holdout; link prevalence is never estimated from the enriched sub-sample. The size of the enriched link sub-sample is not set (the report gives none).
11. **`drop_order.trigger`.** The core-does-not-pay test is spelled out from the interface document, and "dropped in this order until the test passes" is Claude's reading of P3.
12. **`assembly`.** "The zero-shot baselines use the same passes" is taken from the P16 trade-off text and written as a rule.
13. **`quote.rule`.** P1 ends with "Offsets are computed by code"; the approved quote rule still said "with its offsets". Rewritten so the two do not disagree.

## 3. Per-example summary

The order is now e05, e10, **e01**, e04, e13, e12, e07, **e02**, e15, e06, e09, e16, e03, **e14**, e11, e08 (empty examples in bold at positions 3, 8 and 14). Languages alternate de and en. The longest text is e12 at position 6; the last, e08, is of middle length. All quotes are whole clauses without trailing full stops, links use `{from, to, relation}` under `links`, and `improve` carries no direction. Old item ids are given in brackets where they differ.

- **e05 (de, position 1).** Text changed in one clause: the survey figure now counts employees with no alternative to the car, because the old figure measured car commuting, not the pain (R-10). i1 is the whole clause; measurement and quantified now describe the pain; situation "Wahlkreis". i2 now starts with "dass", i3 with "und"; the frequency word "jeden Morgen" is no longer a situation (P12). i4 is cut to the clause after "ich schätze"; the closure sentence is no item; mode is empty because the quote names the line only as "sie"; states_solution becomes true (P7). i5: actor public_sector becomes individual (the demand is voiced for constituents, P10); improve becomes empty because the quote names a measure, not a dimension (P11). New means-end link i5 to i4, joined by "Deshalb" (P5).
- **e10 (en, 2).** i1 evidence routine becomes opinion (no frequency word, P9). i2 now includes the problem marker "The problem is long trips:" (P1); routine with quantified stays (a share of the speaker's own attempts, P9). i3 stays a second item because the "so" consequence is a need of its own; trailing full stop removed. i4 unchanged.
- **e01 (de, 3).** Unchanged, moved.
- **e04 (en, 4).** i1 is the whole sentence including "As a delivery driver in the city centre"; situation "city centre" (P6). i3 and i5 start with "and". i4: "Last Tuesday" is no longer a situation (date of a single event, P12); mode adds truck_van for "my van" (P8). i6: improve becomes empty (a named facility, P11). The actor pair i2 to i3 is rewritten in the new encoding.
- **e13 (de, 5).** New, see section 4.
- **e12 (en, 6).** 11 items become 9. i1 keeps both clauses as one need; mode becomes [car] ("no longer drive", negated mode counts, P8); evidence becomes opinion (no source given). i2: evidence becomes opinion; situation "high street". i3: the frame "several members have told me" is outside the quote; "uneven kerb" is no longer a situation (the hazard, P12). i4 unchanged. i5 starts with "but"; evidence becomes opinion. i6: evidence becomes opinion; improve [effort, access] becomes [effort, flexibility] (booking only on weekday mornings is a choice of time, P11). i7 (old i7): the frame "People tell us" is outside. i8 merges old i8 and i9: the "because" clause stays inside (P1); actor organization becomes individual (the residents' need, P10); evidence anecdote. i9 merges old i10 and i11: the sub-clause "without having to depend on their children" joins its clause (P1 trade-off); improve becomes empty.
- **e07 (de, 7).** Old i1 and i2 are bare activities and no longer items (P2), so the old order link goes. New i1 "Ich nehme das Rad" with a means-end link to i2 "um den Zug um 7:12 zu schaffen" (the "um zu" clause, P2 trade-off and P5). Old i4 is split: i3 the lateness (reliability), i4 the embarrassment, a feeling reported as a fact and therefore a pain (P15). i5 "Ich will pünktlich sein" becomes a gain (P2). i6: "jeden Morgen" is no longer a situation.
- **e02 (en, 8).** Unchanged, moved.
- **e15 (de, 9).** New, see section 4.
- **e06 (en, 10).** i1 starts with "that", i2 with "and"; i2 stays quantified (a count of complaints, P9 c). i3: scope quantified becomes single (a share of the operator's own posts is the size of the problem, not a count of actors with the need, P9 c). i4: improve drops reliability. i1 and i2 remain the same need twice with different evidence (note d).
- **e09 (de, 11).** i1: public_sector becomes society (the need of everyone in the place, voiced by the mayor, P10). i2: society becomes individual (a named group, "wer kein Auto hat", P10); mode becomes [car] (P8). i3 unchanged. i4 starts with "und"; improve effort becomes other (staff). i5: public_sector becomes individual, scope multiple. i6: gain becomes job ("wegkommen" is a verb of doing, P2); mode becomes [bus] for the negated "nicht um einen Bus" (P8); trailing full stop removed.
- **e16 (en, 12).** New, see section 4.
- **e03 (de, 13).** i1 starts with "und"; evidence routine becomes opinion (a general claim, no frequency word); improve access becomes flexibility (how often the bus runs). i2 unchanged. i3: situation becomes "Kreisstadt" (place; for the job i2 the same word is the destination and no situation). i4 starts with "aber". i5: states_solution becomes true (a specific schedule, P7); improve becomes flexibility.
- **e14 (en, 14).** New, see section 4.
- **e11 (de, 15).** Old i1 (bare activity with "rund 300 Filialen") is no longer an item (P2). i1 (old i2) becomes a gain and includes "Unser Ziel ist," (P1, P2). i2 (old i3): evidence observation becomes routine (a share from the firm's own repeated experience, P9). i3 (old i4) includes "Für uns wäre schon viel gewonnen,"; "am Nachmittag" is no longer a situation (part of the wished solution, P12).
- **e08 (en, 16).** i1: situation "Saturdays". i3 includes "And honestly,"; situation becomes "interchange" (the crowd is the hazard). i2 and i4 unchanged.

## 4. The four new examples

- **e13 (de, position 5): third-person news text, mostly off-topic.** A town festival report in eight sentences; two items. i1: the administration admits it lacks staff for traffic planning at large events (public_sector, its own need, opinion, single, improve other). i2: a transport-association spokesperson says full roads at such festivals are a problem for everyone (society, opinion, multiple, reported speech graded by the person quoted). Shows plain asserted pains without experience.
- **e14 (en, 14): long study report, empty.** A household travel survey summary with mode shares, trip rates and purposes; many figures, no actor who wants or struggles. The longest empty text, so that length no longer predicts relevance.
- **e15 (de, 9): worker text.** A truck driver. i1 job (deliver the first load by seven) is linked as actor pair to i2, the residents' pain (windows rattle when the truck passes, observation, multiple, truck_van). i3 is a routine reported for many people ("Wir Fahrer verlieren jeden Morgen eine halbe Stunde", routine with multiple). i4 and i5 are joined by "Während" (order, during, from the earlier quote). i6 "eine eigene Baustraße" (states_solution true) is linked by "damit" to i7, the safety need behind it (states_solution false, modes truck_van, bus, bicycle): this is the P7 contrast pair.
- **e16 (en, 12): noisy council minutes.** Speaker tags, a microphone aside and a cut-off sentence ("and we –") that gives no item. i1: the district council cannot keep up with gritting because it has only six lorries (public_sector, its own need; six lorries is the size of an operation, so single). i2 and i3: residents stuck, and one resident who missed a hospital appointment (observation about one case, single). i4 "We want to order four more lorries" (job, states_solution true) and i5 "but first the capital budget has to be approved" are linked i5 before i4, so text order and time order differ. i6: the bus operator's own pain (organization). No actor pair from i1 to i6, because the text does not say who failed to grit the access road.

## 5. Distribution against the target

Target from the provenance (non-Claude teacher run of span-train-v1, read under the old guideline v2). "Before" is the approved set of 12 examples, "after" the 16 examples of this revision. Per item, 67 items in 13 relevant examples (before: 55 in 10).

| Field | Value | Target | Before | After |
|---|---|---|---|---|
| kind | pain | 50 % | 56 % | 61 % |
| | job | 28 % | 24 % | 18 % |
| | gain | 22 % | 20 % | 21 % |
| actor_type | individual | 44 % | 65 % | 63 % |
| | organization | 21 % | 15 % | 9 % |
| | public_sector | 19 % | 9 % | 9 % |
| | worker | 12 % | 7 % | 15 % |
| | society | 4 % | 4 % | 4 % |
| evidence_type | opinion | 73 % | 42 % | 51 % |
| | routine | – | 25 % | 24 % |
| | observation | – | 24 % | 15 % |
| | anecdote | – | 5 % | 7 % |
| | measurement | – | 4 % | 3 % |
| evidence_scope | multiple | 73 % | 33 % | 34 % |
| | single | 18 % | 55 % | 58 % |
| | quantified | – | 13 % | 7 % |

Per language: German now has worker items (e15) and English public_sector items (e16), as section 4 of the review asked. English still has no society item.

Reading the gaps:

- **job 18 % against 28 %.** Lower than before, as the P2 trade-off predicted: bare activities (e07, e11, e08) are no longer jobs, and two wishes became gains. The old teacher counted activities as jobs, so the target is not comparable here, like the scope target.
- **opinion 51 % against 73 %.** Up from 42 %, through plain asserted pains in e12, e13 and e16. Still well short; closing the gap would need more third-person texts with bare claims.
- **individual 63 %, organization 9 %, public_sector 9 %.** P10 moves needs voiced for others to the people who have them, which shrinks public_sector and organization (the review predicted this for public_sector). The four new examples could not close the gap without breaking their P13 brief.
- **multiple 34 % against 73 %.** Not rebalanced, as the review advised (section 4: the target is not comparable under reading a). Type and scope are no longer coupled: routine with multiple (e15 i3), routine with quantified (e10 i2, e11 i2), observation with single (e06 i3, e16 i3), anecdote with multiple (e12 i8, e16 i2).

Other figures: states_solution true on 8 items; links: means_end 3, actor_pair 2, order 2 (one before, one during). Quotes over more than one sentence: 1 of 67 (e10 i3).

## 6. `opportunity-interface/README.md` (P14, minimal route)

- Header: notes the correction date and owner decision 3.
- Row 4: scout supplies one role span per item; grouping spans into job executors across inflection and language is a cairn task. The ODI column now says "evidence for the job executor" instead of "defines".
- Row 5: actor pairs link a causing item to the other actor's pain; they do not identify the purchase decision maker, which stays open.
- Row 10: means-end links tie a step or measure to its goal only where connecting words join them; they do not tie each outcome to its job.
- Row 14: "Today" becomes "partly"; the gap states that scout has no field tying a pain or gain to its job and that the grouping rests on untrained cairn clusters.
- Test I2: "per job" means per cairn cluster. Columns that may be absent without failing: improve, situation and executor, each only when its field was not produced in that language, and then marked absent; importance and satisfaction are empty by design. All other columns must be present. A minimum-fill check on a fixture built from the worked examples was added (part of P14 minimal).

## 7. Validation

`uv run python topics/productdev/guideline/scout-v3/check_examples.py` reports 0 errors. It checks verbatim quotes and pointers, unique and non-overlapping quotes without edge punctuation, enum and list values against `brief.yaml`, the link encoding and link targets, relevant if and only if items exist, and job_kind on jobs only. A run on a copy with seven planted errors reported all seven.

## 8. Not applied or still open

- **R-15 rest.** Whether the domain test applies per text or per item, and a test for "backdrop", have no proposal; not changed.
- **R-22 rest.** `doubt.fields` ("leave it empty") still collides with required fields such as actor_type; no proposal; not changed.
- **R-24.** The rule that the export must not filter by the evidence rank has no wording in P9; not added.
- **R-29.** Roadmap phases 7 and 8 are outside the files of this change.
- **`reader`.** "Ein Produkt Manager" is a German owner answer too; note (f) names only three keys, so it has no English version.
- **Tension in P2 and the e07 trade-off.** P2 says a job "stays the same when the means change", but the review keeps the bike ride of e07 as an item through its "um zu" clause. "Ich nehme das Rad" is a means; the examples label it a job so that the means-end link has two items. The owner may prefer a different kind or no item.
- **Judgement calls in the examples.** e09 i1 is society as the review suggested ("Bei uns" read as everyone in the place), while e12 i4 "nobody can read" is individual (the speaker speaks for the older residents). e16 i4 "We want to order four more lorries" is a job (verb of doing), while e04 i6 "We need loading bays" is a gain; both carry states_solution true.
