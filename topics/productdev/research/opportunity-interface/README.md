# The opportunity interface: what the pipeline must hand to OST and ODI

Date: 2026-11-27. Status: requirements analysis, nothing built. The owner confirmed the field list for scout-large 0.2.0 on 2026-11-27 (rows 3 to 11 and 19). Rows 4, 5, 10 and 14 and test I2 were corrected on 2026-11-28 after Fable review 1 of the guideline v3 brief (owner decision 3: no new field; cairn groups items per cluster). Input to the [scout-large roadmap](../scout-large-architecture/roadmap.md) and to the next cairn feature.

## Why this document exists

scout-large finds jobs, pains and gains in single texts. cairn merges them across texts into an opportunity map. Feature 009 named the two methods the map must feed without conversion: the **Opportunity Solution Tree** (Torres 2021) and the **opportunity landscape of Outcome-Driven Innovation** (Ulwick 2016). Other methods (job map, journey map, Kano, Value Proposition Canvas) attach through the assignment slots of the cairn format.

The owner's requirement (2026-11-27): the output of the models must fit these methods, so that no information the methods need is missing later. Next to the quantitative scores, the interface is a quality criterion of its own. This document lists what each method needs, which stage of the pipeline supplies it, and what is missing today. It ends with acceptance tests for the interface.

Today only scout's per-text output (`jtbd-span-v1`) and cairn's map format (`jtbd-cluster-output`, spec 009) exist. Both were designed before this check.

## What the two methods need

**Opportunity Solution Tree.** The root is a desired outcome that the team sets. Below it sit opportunities: needs, pain points and desires, phrased from the customer's side and found in stories of specific past experiences. Opportunities are ordered from broad to specific. Torres structures the top of the opportunity space along the moments of an experience map, the steps of the customer's experience in time. Solution ideas that customers voice are reframed as the opportunity behind them, so that solutions do not enter the opportunity space. Opportunities are compared by sizing (how many customers, how often) and by customer, company and market factors. Solutions and assumption tests hang below the opportunities and are the team's work.

**Outcome-Driven Innovation.** The unit of analysis is a job executor and a core functional job. The job is broken into the steps of a universal job map (define, locate, prepare, confirm, execute, monitor, modify, conclude). Per step, desired outcome statements are written in a fixed syntax: direction of improvement, performance metric, object of control and contextual clarifier ("minimize the time it takes to … when …"). ODI also separates emotional and social jobs, consumption-chain jobs and the outcomes of the purchase decision maker. Importance and satisfaction of each outcome come from a quantitative survey of job executors. The opportunity score and the landscape (importance against satisfaction) are computed from that survey, and segments are formed from the outcome ratings.

Neither method can be fed with counts of mentions in place of survey ratings. Mentions show that a need exists and where the evidence is; they do not say how important it is.

## Who supplies what

Every piece of information has exactly one stage that can supply it. scout sees one text and can only supply what that text says. cairn sees all texts but no text that scout did not quote. The team and a survey supply the rest.

| # | Information | OST uses it for | ODI uses it for | Supplied by | Today | Gap and action |
|---|---|---|---|---|---|---|
| 1 | The need in the customer's own words, with source and offsets | evidence of an opportunity | raw material of outcome statements | scout | yes: `quote`, `start`, `end` | none |
| 2 | Kind: job, pain or gain | opportunities are needs, pains and desires | jobs versus outcomes | scout | yes: `kind` | none |
| 3 | Kind of job: functional, emotional or social | helps phrase opportunities | ODI treats them separately | scout | no | **new item attribute** |
| 4 | Who has the need: the role of the job executor, finer than five actor types | sizing by segment | evidence for the job executor and the market | scout (role span per item); cairn (grouping) | partly: `actor_type` with 5 values | **new: a pointer to the verbatim span that names the role**. scout supplies one span per item, in the words and inflection of the text; grouping the spans into job executors across inflection and language is a cairn task. Persona fields were deferred in spec 022 |
| 5 | Two actors at the point where their paths cross, with the pain that comes from their conflicting goals | opportunities between parties | separate executors | scout | no | **new: actor pairs** (field note 1): a link from the item that causes to the other actor's pain. It does not identify the purchase decision maker; that stays open |
| 6 | Mode of transport | branches of the tree, sizing | contextual clarifier | scout | no | **new item attribute**; deferred in spec 022 |
| 7 | Situation: where and when the need arises | placement on the experience map | contextual clarifier | scout | no | **new: a pointer to the verbatim span that states the situation** ("an opportunity without a place is hard to act on", field note 1) |
| 8 | What the actor wants to improve (time, effort, risk of failure, cost and the like) | sharper opportunities | metric and direction of an outcome statement | scout | no | **new item attribute**; the value list comes from the owner's brief |
| 9 | Whether the item states a solution instead of a need | solutions must be reframed, not placed as opportunities | outcomes must be free of solutions | scout | no | **new item attribute** |
| 10 | "In order to" links between two items of one text | evidence for parent and child opportunities | links a step or measure to the goal it serves, where the text joins them with connecting words | scout | no | **new: means-end edges** (field note 2); no band of strategic, tactical, operational. They do not tie each outcome to its job: most pains and gains have no such link (see row 14) |
| 11 | Order of two items within one text, with the words that order them | the sequence of an experience map | the order of job steps | scout | no | **new: order edges** (field note 3); order across texts is never extracted |
| 12 | One entry per need, with mentions and independent sources | opportunity sizing | a candidate list without duplicates | cairn | yes (trained model in spec 022) | none |
| 13 | Broad-to-specific relation between needs | the tree structure | granularity of outcome statements | cairn | yes (spec 022) | none |
| 14 | A job together with its pains and gains | opportunities under a job | outcomes grouped per job | cairn | partly: clusters (untrained) | scout has no field that ties a pain or gain to its job (owner decision 3 after Fable review 1). The grouping rests on cairn clusters alone, and they are untrained; test I2 therefore groups per cluster, not per job |
| 15 | Experience-map moment or job-map step of a need | top level of the tree | step of each outcome | cairn assignment slot | slot exists, nothing fills it | **later cairn feature**, fed by rows 7 and 11 |
| 16 | A normalised statement per need | opportunity label | outcome statement in ODI syntax | cairn statement slot | slot exists, empty | **open**: a person, or a later zoo model; never Claude (Principle XI) |
| 17 | Source date and source class | trends over time | – | input metadata | yes | none |
| 18 | Calibrated confidence per item | filtering and review | filtering and review | scout | score is not calibrated | already in the 0.2.0 plan |
| 19 | Language of the text | per-language thresholds | per-language thresholds | scout | implicit | **new output field** |
| 20 | Importance and satisfaction per outcome; segments | – | opportunity score and landscape | survey | out by design | the map must export a **survey-ready outcome list** |
| 21 | Desired outcome at the root, solutions, assumption tests, prioritisation | the team's part of the tree | – | team | out by design | none |
| 22 | Typed holes and the decision an entry would change | – | – | map step and team | no | map-level (field notes 4 and 5), not scout |

## Rules for the new fields

- **No generated text.** Each new field is either a value from a fixed list or a pointer to a verbatim span of the input with character offsets, like the quote itself. This keeps scout's verbatim rule and Principle II.
- **Empty is a correct answer.** A field that the text does not state stays empty, and no metric rewards filling it. Field note 4 sets this rule for the map, and scout's own rules already require it.
- **Each field earns its place in an agreement pilot.** The two non-Claude reference models must agree on a field above a threshold fixed before the pilot, in German and in English. A field that fails is not produced. The format documents it as absent, so the gap stays visible instead of being filled with noise. This is the rule that cairn already applies to its levels (spec 009).
- **The core does not pay for the extras.** Item-matching F1 and relevance of the model with new fields must not fall below the same model without them, beyond the bootstrap interval.
- **Definitions are the owner's.** This document names the information. The definitions and value lists that a teacher reads come from the owner's brief, through the route chosen for guideline v3. The owner decided on 2026-11-27 that this requirement list may seed the brief, as the lists of feature 001 may (`D-xi-interface-requirements`, next to `D-xi-rewrite-requirements`). It seeds which information to cover, never the wording a teacher reads.

## Acceptance tests for the interface

Next to the quantitative scores, the release of a model in this pipeline is held to these tests:

| # | Test | How it is checked |
|---|---|---|
| I1 | **Contract.** The output format (`jtbd-span-v2`) has a schema and a field-meaning file. Each field names the row of the table above that it serves. cairn accepts the new format as input. | schema check in CI; `zoo site build` check B5 |
| I2 | **Lossless build.** From pipeline output alone, two exports are built: the opportunity layer of an OST (needs with children, counts and quotes) and an ODI candidate list (per cairn cluster: outcomes with what to improve, situation, executor, counts, and empty columns for importance and satisfaction). "Per job" means per cairn cluster; scout does not tie outcomes to jobs. The test fails if any column needs information from outside the output. Columns that may be absent without failing: what to improve (`improve`), situation (`situation`) and executor (`executor_role`), each only when its field was not produced in that language after the agreement pilot, and then marked as absent in the export; importance and satisfaction, which are empty by design. All other columns (need, kind, quote with source and offsets, cluster, children, counts) must be present. Minimum fill: on a fixture built from the guideline's worked examples, every column of a produced field is filled in at least one row. | automated, on a fixture bundle |
| I3 | **Traceability.** Every node of both exports links to at least one verbatim quote with source id and offsets. | automated |
| I4 | **Field agreement.** Per field and language, agreement of the model with the reference consensus and of the references with each other, with confidence intervals. Fields that failed their pilot are listed as absent. | benchmark report |
| I5 | **Practitioner test.** A person who did not build the pipeline reaches the opportunity layer of an OST from a pipeline result in under half an hour (the outcome named in field note 5, never recorded in a spec or measured so far), and can name the ODI outcome list that would go into a survey. | session with one outside person; can run together with the open reader test |

## Consequences

**For scout-large 0.2.0.** Rows 3 to 11 and 19 are new outputs of scout. They change the output format to `jtbd-span-v2` and must be in guideline v3, because the benchmark and the teacher labels are rebuilt anyway. A later addition would repeat guideline, agreement pilot and relabeling. The item attributes (rows 3, 6, 8, 9) and the span pointers (rows 4, 7) fit the unit-level head as extra heads per item. The two kinds of edge (rows 5, 10, 11) need a relation head over pairs of items; the biaffine scorer over units from the architecture research can carry it.

**For cairn.** The next cairn feature reads `jtbd-span-v2`, carries the new fields into the distributions of groups and clusters, and builds the two exports of test I2 in its report step. Filling the moment and step slot (row 15) from the situation spans and order edges is a cairn feature of its own.

**Not for any model.** Importance, satisfaction, segments, the root outcome, solutions and prioritisation stay with the survey and the team. The interface makes this explicit by exporting empty columns rather than estimates.

## Sources

- Torres, T. (2021). *Continuous Discovery Habits: Discover Products that Create Customer Value and Business Value.* Product Talk LLC.
- Ulwick, A. W. (2016). *Jobs to be Done: Theory to Practice.* IDEA BITE PRESS.
- Spec 009 (`specs/009-jtbd-dedup-cluster/spec.md`): target methods and the statement and assignment slots.
- Spec 022 (cairn branch): persona and mode fields deferred; opportunity layer as broad-to-specific relation.
- Field notes 1 to 5 (`zoo/notes/`): actor pairs, means-end edges, order edges, typed holes, the decision test and the half-hour outcome.
