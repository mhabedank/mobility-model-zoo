# Labeling guideline v2: jobs, pains and gains with graded evidence

You extract **jobs, pains and gains** from one text chunk. Every item you extract must be backed by a verbatim quote from that chunk. When the chunk contains nothing to extract, return an empty list. That is a correct and complete answer.

## 1. Problem domain

{{domain_definition}}

You get the domain and nothing else: no persona, no target group, no role. Who has a job, pain or gain is part of what you extract (section 4).

## 2. Relevance

Set `relevant: true` when the chunk is about the domain above, i.e. it talks about moving people or goods or about one of the listed aspects, as experienced, done, measured or decided by someone.

Judge relevance by the **main subject of the chunk**, not by single sentences in it.

Set `relevant: false` for:
- **Near-misses**: vehicles or transport as a hobby, collector object, sport or aesthetic topic. This includes:
  - restoring, storing, documenting or finding spare parts for classic, vintage or "youngtimer" vehicles kept for pleasure rather than for getting around;
  - sport or leisure riding and driving where the ride itself is the purpose (training rides, audax, route planning for fun, track days), unless the text is about traffic, safety, infrastructure or rules experienced while riding;
  - motorsport, racing results and racing-vehicle engineering;
  - model railways and car design as art.
  A near-miss chunk is `relevant: false` with `items: []` **even when it contains tasks or problems** (a collector looking for a spare part, a racing team tuning aerodynamics).
- Transport used only as a metaphor ("the project is on the fast track").
- Texts where mobility is only mentioned in passing and is not the subject (a recipe that mentions driving to the market).

An irrelevant chunk always has `items: []`. A relevant chunk may also have `items: []` when it contains no job, pain or gain (for example a plain timetable notice).

## 3. Item kinds

| Kind | Definition | Test question |
|------|------------|---------------|
| `job` | Something an actor is trying to get done: a task, goal or progress they want to make. | "What is this actor trying to achieve?" |
| `pain` | A problem, obstacle, risk, cost or frustration the actor experiences in getting a job done, or an unwanted outcome. | "What goes wrong, hurts or blocks them?" |
| `gain` | A benefit, positive outcome or desired improvement the actor experiences or wants. | "What makes it better for them, or what would they like to have?" |

### What counts as an item

Extract an item when the text states, for an actor, something they try to get done (job), a problem they experience or expect (pain), or a benefit they experience or want (gain), within the domain. Extract **every** statement in the chunk that passes this test, not only the main points.

Extract:
- what speakers say about their own jobs, pains and gains, including complaints, wishes and plans;
- research findings and survey results about the jobs, pains or gains of an actor ("the new regional ticket increased bus ridership" is a gain for bus users; grade the evidence in section 5);
- goals, demands or problems that an organization or authority states for itself, for example in a hearing ("we want to open ten new depots next year" is a job of that operator; "we cannot find enough drivers" is its pain).

Do not extract:
- single steps or tactics of a job that is already extracted (packing the trailer and pumping the tyres are steps of "take the children to school by cargo bike"). Extract the job once, at the level of its goal; a step that meets its own obstacle can be a pain;
- trip or location reports that only set the scene ("I'm sitting on the train to Hamburg right now"), unless the trip itself is a job the text talks about;
- advice or tips addressed to others ("always photograph the car before you rent it"), unless they report the speaker's own job, pain or gain;
- method descriptions, model properties, definitions and literature summaries that state no effect on an actor;
- generic background facts that no actor experiences or wants (e.g. "Germany has 16 federal states").

Rules:
- **Pain versus negated gain**: if the text describes a present problem ("there is no bus after 6 pm"), label it a `pain`, even when it could be phrased as a missing gain. Label a `gain` only when the text describes an experienced benefit or an explicitly desired improvement ("I would love a later bus").
- One quote can support more than one item, for example a job and the pain that blocks it. Extract each as a separate item. Do not merge different jobs, pains or gains into one item.
- Do not infer items that are not stated. Plausible is not enough (Principle II).

## 4. Actor and actor type

- `actor`: who has the job, pain or gain, as named or described in the text ("commuters in rural districts", "the parcel courier", "our municipality"). Use the text's own words where possible, in English.
- `actor_type`: exactly one of

| Actor type | Use for |
|------------|---------|
| `individual` | A private person acting for themselves or their household (commuter, car owner, EV driver, parent), also as a group ("rural commuters", "EV drivers", "users"). |
| `worker` | A person acting in their job in the domain (driver, courier, mechanic, dispatcher, charging-station technician). |
| `organization` | A company, operator, association or other non-state organization (transport operator, logistics firm, car-sharing provider). |
| `public_sector` | A state body or public authority (municipality, ministry, regulator, public transport authority acting as an authority). |
| `society` | The public at large or society-level effects (climate, public health, "residents of the city" as a collective). Not for a group of users: users of a service are `individual`. |

Boundary rules:
- A person speaking about their own paid work in the domain (a courier, a self-employed driver, a mechanic) is a `worker`; the company they work for is an `organization`.
- An organization speaking in a hearing (association, operator, company) is an `organization`; a ministry, municipality or regulator is `public_sector`, also when it operates a service.
- Use `society` only when the text names effects on the public at large, not when it describes many individuals.

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
- **Opinion vs observation**: a speaker's general claim about how things are ("e-bikes are cheaper to maintain", "most charging apps are confusing") is an `opinion`, even when it is phrased as a fact. Use `observation` only when the text says the claim rests on systematic observation or on reports from several people ("our members report…", "in our depots we see…", "studies show…" without numbers from them). Research findings without numbers are `observation`; with numbers from the study they are `measurement`.
- **Anecdote vs opinion**: when the quote describes an event the speaker experienced, use `anecdote`, even if it also contains a judgment ("the scooter I rented yesterday was filthy").
- **Anecdote vs routine**: a single or few events means `anecdote`. Explicit regularity ("every day", "usually", "always", "jeden Tag", "regelmäßig") means `routine`.
- **Observation vs measurement**: a number alone does not make a measurement. Use `measurement` only when the number comes from a defined measurement, survey or dataset. A personal estimate with a number ("about half the time") is not a measurement.
- **When uncertain, assign the lower grade.**

## 6. Evidence scope

| Scope | Use when the quote... |
|-------|-----------------------|
| `single` | refers to one actor and one occurrence (one event, one decision) |
| `multiple` | refers to several actors or occurrences, without a quantity, including general or habitual statements |
| `quantified` | states a quantity: a number, share, frequency, price or amount (digits or number words such as "half", "twice", "Hälfte", "zwei Wochen") |

Rules:
- Scope counts the actors or occurrences the quote **refers to**, not the number of speakers. One speaker saying "I always…", "most services…", "people here…" or making a general claim refers to several occurrences: `multiple`. One speaker reporting one event: `single`.
- `quantified` requires that the **quote itself** contains the quantity. Prices and costs count ("a 1,200 € repair bill"). Vague words without a number ("many", "several", "mehrere", "a few") are `multiple`.

## 7. Quote and statement

- `quote`: an exact, contiguous substring of the chunk, in the chunk's language. Do not translate, shorten with "…", fix typos or merge separate sentences. Differences in whitespace and quotation-mark style are tolerated; nothing else is. Choose the shortest span that fully supports the item, usually one sentence or clause.
  - Keep the original capitalization, also when the span starts in the middle of a sentence ("da entfallen…", not "Da entfallen…").
  - Do not leave out words, asides or parentheses inside the span. If the span contains an aside you do not need, choose a shorter span before or after it instead.
  - Do not join text from different places of the chunk into one quote.
- `statement`: one normalized sentence **in English**, stating the job, pain or gain from the actor's perspective, without adding information that is not in the quote.

## 8. What not to do

- Do not predict metadata (region, language, source type, date, sub-area). It is known already.
- Do not deduplicate, cluster, rank or prioritize items.
- Do not add items to make the answer look complete. An empty list is a valid answer.
