# Labeling guideline v1: jobs, pains and gains with graded evidence

You extract **jobs, pains and gains** from one text chunk. Every item you extract must be backed by a verbatim quote from that chunk. When the chunk contains nothing to extract, return an empty list. That is a correct and complete answer.

## 1. Problem domain

{{domain_definition}}

You get the domain and nothing else: no persona, no target group, no role. Who has a job, pain or gain is part of what you extract (section 4).

## 2. Relevance

Set `relevant: true` when the chunk is about the domain above, i.e. it talks about moving people or goods or about one of the listed aspects, as experienced, done, measured or decided by someone.

Set `relevant: false` for:
- **Near-misses**: vehicles or transport as a hobby, collector object, sport or aesthetic topic (restoring a classic car, motorsport results, model railways, car design as art).
- Transport used only as a metaphor ("the project is on the fast track").
- Texts where mobility is only mentioned in passing and is not the subject (a recipe that mentions driving to the market).

An irrelevant chunk always has `items: []`. A relevant chunk may also have `items: []` when it contains no job, pain or gain (for example a plain timetable notice).

## 3. Item kinds

| Kind | Definition | Test question |
|------|------------|---------------|
| `job` | Something an actor is trying to get done: a task, goal or progress they want to make. | "What is this actor trying to achieve?" |
| `pain` | A problem, obstacle, risk, cost or frustration the actor experiences in getting a job done, or an unwanted outcome. | "What goes wrong, hurts or blocks them?" |
| `gain` | A benefit, positive outcome or desired improvement the actor experiences or wants. | "What makes it better for them, or what would they like to have?" |

Rules:
- **Pain versus negated gain**: if the text describes a present problem ("there is no bus after 6 pm"), label it a `pain`, even when it could be phrased as a missing gain. Label a `gain` only when the text describes an experienced benefit or an explicitly desired improvement ("I would love a later bus").
- One quote can support more than one item, for example a job and the pain that blocks it. Extract each as a separate item. Do not merge different jobs, pains or gains into one item.
- Do not extract generic background facts that no actor experiences or wants (e.g. "Germany has 16 federal states").
- Do not infer items that are not stated. Plausible is not enough (Principle II).

## 4. Actor and actor type

- `actor`: who has the job, pain or gain, as named or described in the text ("commuters in rural districts", "the parcel courier", "our municipality"). Use the text's own words where possible, in English.
- `actor_type`: exactly one of

| Actor type | Use for |
|------------|---------|
| `individual` | A private person acting for themselves or their household (commuter, car owner, EV driver, parent). |
| `worker` | A person acting in their job in the domain (driver, courier, mechanic, dispatcher, charging-station technician). |
| `organization` | A company, operator, association or other non-state organization (transport operator, logistics firm, car-sharing provider). |
| `public_sector` | A state body or public authority (municipality, ministry, regulator, public transport authority acting as an authority). |
| `society` | The public at large or society-level effects (climate, public health, "residents of the city" as a collective). |

When the same text names several actors with their own jobs, pains or gains, extract separate items per actor.

## 5. Evidence type (ordinal, lowest to highest)

Grade **how directly the text supports the item**, not how plausible or common the claim is in general.

| Grade | Name | The text... | Example cue |
|-------|------|-------------|-------------|
| 0 | `opinion` | states a belief, judgment, expectation or wish without describing experience | "I think car sharing will never work here." |
| 1 | `anecdote` | describes a specific personal experience or event (one or a few occurrences) | "Last Tuesday the charger was broken again." |
| 2 | `routine` | describes a recurring practice or regular experience of the speaker | "I commute 40 km every day." |
| 3 | `observation` | reports what someone systematically observed or what several people reported, without numbers from a defined measurement | "Couriers described double parking as the only way…" |
| 4 | `measurement` | reports a quantified result of a defined measurement, survey or dataset | "63% of the 412 surveyed couriers reported…" |

Boundary rules:
- **Anecdote vs routine**: a single or few events means `anecdote`. Explicit regularity ("every day", "usually", "always", "jeden Tag", "regelmäßig") means `routine`.
- **Observation vs measurement**: a number alone does not make a measurement. Use `measurement` only when the number comes from a defined measurement, survey or dataset. A personal estimate with a number ("about half the time") is not a measurement.
- **When uncertain, assign the lower grade.**

## 6. Evidence scope

| Scope | Use when the quote... |
|-------|-----------------------|
| `single` | refers to one actor or one occurrence |
| `multiple` | refers to several actors or occurrences, without a quantity |
| `quantified` | states a quantity: a number, share, frequency or amount (digits or number words such as "half", "twice", "Hälfte") |

`quantified` requires that the **quote itself** contains the quantity.

## 7. Quote and statement

- `quote`: an exact, contiguous substring of the chunk, in the chunk's language. Do not translate, shorten with "…", fix typos or merge separate sentences. Differences in whitespace and quotation-mark style are tolerated; nothing else is. Choose the shortest span that fully supports the item, usually one sentence or clause.
- `statement`: one normalized sentence **in English**, stating the job, pain or gain from the actor's perspective, without adding information that is not in the quote.

## 8. What not to do

- Do not predict metadata (region, language, source type, date, sub-area). It is known already.
- Do not deduplicate, cluster, rank or prioritize items.
- Do not add items to make the answer look complete. An empty list is a valid answer.
