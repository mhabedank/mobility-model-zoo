# Labeling guideline

## teacher_task_en

**text**: Find where the text states pains, gains and jobs to be done. Each of them is then enriched with further fields, as given in the list of fields.

## reader_en

**text**: A product manager.

## domain

**owner_en**: - **text**: Follow the definition of mobility; everything that belongs to it also belongs to our topic.

**definition**: Mobility is the movement of people, goods and animals in geographic space, together with everything that enables or shapes it. It covers: the trips and transports themselves, by any mode and over any distance, including walking, cycling, cars, public transport, rail, air, water and freight; the options people and organisations have to move, such as access, cost, time and information; the vehicles, services, infrastructure and energy used for it, such as roads, stations, parking, fuel and charging; and the work, rules, business and effects that go with it, such as jobs in transport and logistics, regulation, prices, congestion and emissions. Transport is the movement that actually happens; mobility also includes the possibility to move. Not covered: social mobility between classes or jobs, and the transmission of messages or energy as such.

**sources**:

- source: Wikipedia (de), Räumliche Mobilität; url: https://de.wikipedia.org/wiki/R%C3%A4umliche_Mobilit%C3%A4t; licence: CC-BY-SA-4.0
- source: Wikipedia (en), Transport; url: https://en.wikipedia.org/wiki/Transport; licence: CC-BY-SA-4.0
- source: FGSV, Begriffsbestimmungen; licence: proprietary
- source: Spektrum, Lexikon der Geographie, Verkehrsmobilität; url: https://www.spektrum.de/lexikon/geographie/verkehrsmobilitaet/8614; licence: proprietary

## item_boundaries

**rule**: An item is one need. Its quote is the shortest run of whole clauses that states the need, including the words that mark it as a wish, fear or problem (such as 'I want', 'schön wäre', 'I worry that') and the conjunction that opens a clause. A need may run over several sentences. A cause or consequence joined with 'so', 'because', 'weil' or 'sodass' belongs to the same item unless it is a need of its own. It is a need of its own when it names another burden or another actor than the clause before it. A purpose joined with 'um … zu', 'damit', 'in order to' or 'so that' is an item of its own, and so is the clause it depends on. The opening conjunction may be of either kind ('und', 'aber', 'dass', 'and', 'but', 'that'). A frame that only says who said it ('Viele sagen mir, dass', 'People tell us', 'ich schätze') stays outside the quote; a source named inside the clause ('laut der Erhebung') and a verb that itself states the problem ('complain', 'sich beschweren', 'worry') stay inside. Two clauses joined by 'and' are two items when they name different burdens or actors. Quotes of one text never overlap. Offsets are computed by code.

## relevant

**definition**: A text is relevant when it states at least one job, pain or gain of an actor within mobility as defined under domain, told by the actor or reported by someone else. The topic alone is not enough. Not relevant: texts that only report facts, figures, events or product features with no actor who wants to get something done, struggles, hopes for something or values an outcome they have; timetables, tariffs and technical specifications; a provider praising its own offer without reporting a customer's need; texts where mobility is only the backdrop of something else. One passage with a need is enough, even if the rest of the text is off-topic. The test applies to each item: the need, or the trip or transport on which it arises, must lie within mobility. What a mobility problem does to the actor (being late for work, feeling cut off) is an item. A need about something else that is only mentioned on the way is no item.

## kind

**job**: Something an actor is trying to get done or achieve in a situation: a task, a goal or a change of state they want.

**pain**: Something that bothers the actor before, during or after getting the job done: an obstacle, a cost, a risk, an annoyance, a bad outcome, or the fear of one.

**gain**: An outcome or benefit the actor wants, expects or would welcome: something that makes the job easier, faster, cheaper, safer or more pleasant, or a good outcome they already value.

**job_versus_gain**: A job is what the actor wants to get done: it has its own verb of doing and stays the same when the means change. A wish about how well, fast, cheaply, safely or reliably it goes is a gain. A sentence that only reports what someone does, with no want, purpose, obstacle or judgement, is not an item. This test decides, whatever word the text uses ('goal', 'Ziel', 'need'). A step the actor takes for a stated purpose is a job and is linked to its goal with means_end. A wish for a thing or measure is a gain with states_solution true, also when it has a verb of doing ('order', 'build', 'introduce').

**feelings**: A bad feeling reported as a fact is a pain, a good one a gain. A wish to feel or not to feel something is a job with job_kind emotional, also when it is about how the trip goes; this rule comes before job_versus_gain.

**pain_versus_negated_gain**: Label by what the text describes. A problem the actor has now is a pain, even when phrased as a missing benefit. A wish for a better state is a gain, even when phrased with a negation. Label both only when each has its own clause; otherwise take the kind the wording has.

## actor_type

**rule**: The actor is who has the need, not who speaks or writes. A need voiced on behalf of others takes the type of those who have it; the speaker's body is the actor only for its own need (budget, staff, duties). actor_type is the coarse class; executor_role marks the words that name the specific role.

**individual**: Private persons acting for themselves or their household, one or many, including named groups such as commuters or residents.

**worker**: A person whose need comes from their work in or around mobility. Commuting is not work in mobility.

**organization**: A company, operator, association or other non-state body acting as such.

**public_sector**: A public authority or public body acting as such.

**society**: The public at large, only when the text says so in words ('alle', 'everyone', 'die Allgemeinheit', 'the public'). The people of a place and generic 'man', 'one' or 'you' are individual.

## evidence_type

**rule**: How the text backs the need, as an ordinal scale from opinion (lowest) to measurement (highest).

**opinion**: A view, belief, wish or judgement with no experience given.

**anecdote**: One concrete experience, a single event.

**routine**: Repeated or habitual experience of the actor (always, every day, usually).

**observation**: Something seen across other people or over a longer time, stated without a figure from counting or measuring.

**measurement**: A figure obtained by counting or measuring, such as a survey result, a statistic or a measured time.

**boundaries**: Grade by the basis the speaker gives, and take the first line that fits. 1. A counted or measured figure with its source: measurement. 2. One concrete event, whoever it happened to and whoever told it: anecdote. 3. The speaker's own repeated experience, shown by a word of frequency, by habitual present tense about the speaker's own trips ("I take", "wenn ich … muss") or by a share of the speaker's own attempts: routine. 4. A statement about several other people or a longer time, when the text says how the speaker knows it (they were told, or they were there) or gives an estimated figure: observation. 5. Everything else, including a plain statement of how things are ("the bus runs twice a day"): opinion. Anecdote versus routine: one event is an anecdote; words of frequency or several events make it routine. Observation versus measurement: a measurement needs a figure that was counted or measured; an estimate such as "about half, I would say" is an observation, or routine when it is a share of the speaker's own repeated experience.

**reported_speech**: The speaker is the person or body whose statement the text gives: the author of a first-person text, or the person a news text or minutes quote. A journalist or minute-taker who only passes a statement on is not the speaker. What third persons told that speaker is graded from the speaker's side, as below.

**same_need_twice**: The same need stated again in a separate passage that does not overlap the first is a second item with its own evidence.

## evidence_scope

**rule**: Scope counts actors or cases; frequency belongs to evidence_type. One person's routine is single. A body speaking of its own need is one actor. The order is single, multiple, quantified.

**single**: One case, one actor or one event.

**multiple**: Several or many cases, stated without a number.

**quantified**: The text gives a number or share of the actors or occurrences that have the need, such as people, trips, tours or complaints; an estimate with a figure counts. Durations, distances, prices, times of day and the size of an operation do not count. A share counts when it is a share of people or events; a share of a stock, such as posts or vehicles, is the size of the problem.

## quote

**rule**: Each item is a verbatim quote in the source language. Code computes its offsets; the labeler does not count characters. No statement or translation is written per item.

## doubt

**item**: When unsure whether a passage is an item, ask whether a product manager could learn a need from it. If not, leave it out. Never add context that the text does not give.

**kind**: Take the kind the wording has; label both only when each has its own clause.

**levels**: For evidence_type and evidence_scope, take the lower grade. evidence_scope is ordered single, multiple, quantified.

**fields**: job_kind, mode, improve, executor_role and situation stay empty when they are not stated or you are unsure; an empty field is correct. kind, actor_type, evidence_type and evidence_scope are never empty: use the rules for kind and levels above, and for actor_type take the type of the persons the need is about.

## empty_result

**rule**: An empty item list is correct when the text states no job, pain or gain in mobility as defined under domain; relevant is then false. Because relevance follows from items, "relevant but no item" is not a valid result. No score rewards filling a result.

## job_kind

**applies_to**: job

**functional**: The practical task or result the actor wants to get done.

**emotional**: How the actor wants to feel, or wants to avoid feeling, while getting it done.

**social**: How the actor wants to be seen by others, or to stand with them.

**rule**: One value per job item: the one the text stresses. Only jobs carry job_kind; it stays empty for pains and gains, also when they have an emotional or social side. If a passage states a practical and a feeling side, label two jobs only when each has its own clause; otherwise take the value the wording stresses.

## executor_role

**rule**: A pointer to the noun phrase, without article, with the modifiers that define the role, that names who has the need: what the person or body is, such as an occupation, a life situation or an organisation type. The pointer must lie in the text the labeler is given, inside or outside the item's quote. If the same words occur more than once, the occurrence inside the quote counts, else the one nearest before it; code resolves offsets. A role named for the same actor applies to all of that actor's items. A role named inside the quote comes before a role named elsewhere for the same actor. If the words occur only after the quote, the nearest occurrence after it counts. A speaker tag counts as a role only when it names the actor itself and the running text names none. Pronouns and generic words such as "I", "we", "people", "members" or "Leute" get no role. If several roles are named, take the one that has this need. Empty if no role is named.

## link_encoding

**rule**: Every link is written as {from, to, relation}: from and to are ids of items of the same text, and relation is one of the values of the link field.

## actor_pair

**values**: `causes`

**rule**: A directed link from the item of the actor who causes to the pain of the actor who suffers, when the text says that the one causes the other at the same place, time or resource. The causing item may be a job or a pain. The text must name the cause. Both items must be in the text, and their actors differ. A clash known only from general knowledge is not linked. Written as {from: causing item, to: pain, relation: causes}.

## mode

**values**: `walk`, `bicycle`, `micromobility`, `motorcycle`, `car`, `taxi_ridehailing`, `bus`, `tram_metro`, `train`, `coach`, `public_transport`, `truck_van`, `air`, `water`, `other`

**rule**: All modes named in the item's quote, as a list. Decide on the words of the quote: every mode named counts, also when it is negated or missing. Use public_transport when the text names public transport without a mode. A word that belongs to exactly one mode counts, such as a bus driver for bus or a wallbox for car. A verb counts when it belongs to one mode (walk, cycle, fly, drive for car); 'fahren', 'ride' and 'travel' name none. Empty if the quote names no mode; do not infer one from the context alone.

**boundaries**: A pedelec is bicycle. E-scooters and other small electric devices are micromobility. A moped is motorcycle. Minibus and on-demand shuttle are bus. A freight train is train. Charger, petrol station, motorway and parking give car only together with a vehicle word. Use other only for a named mode outside the list.

## situation

**rule**: A pointer to the noun phrase (or time word), without article, possessive, demonstrative or preposition, with the modifiers that define where, when or on what occasion the need arises: a place, a time of day, week or year, or an occasion such as a trip purpose or what the actor carries. The pointer must lie in the text the labeler is given, inside or outside the item's quote. If the same words occur more than once, the occurrence inside the quote counts, else the one nearest before it; code resolves offsets. Place before occasion before time when several are tied to the need. A place, time or occasion counts for an item when it is named in the item's sentence, or when the item points back to it ('there', 'dort', 'dabei', 'dafür'). A time of day or day of the week counts also inside a phrase of frequency: from 'jeden Morgen' point to 'Morgen'. For a job, its own destination or purpose is part of the need; for a pain or gain on that trip, it is a situation. Weather counts as an occasion. Not a situation: words of frequency (every day, immer), the date of a single event, the destination or object that is part of the need itself, and parts of a wished solution. Empty if none is named.

## improve

**values**: `time`, `cost`, `effort`, `reliability`, `safety`, `comfort`, `access`, `information`, `flexibility`, `environment`, `other`

**rule**: The dimensions the item is about, as a list, for jobs, pains and gains. Only when the quote names or clearly describes the dimension. When two values fit, follow the lines below. Empty if no dimension is named or described.

**time**: How long it takes, including waiting and detours; a duration is time.

**cost**: Money the actor pays or lacks, such as fares, fuel, fines, prices or budgets.

**effort**: Steps, planning and hassle needed to get it done.

**reliability**: Whether it happens as planned; late, cancelled, broken down or unpredictable is reliability.

**safety**: Risk of accident, injury or other harm.

**comfort**: How pleasant and calm the trip is, such as shelter, seats, crowding or noise on board.

**access**: Whether a service, place or vehicle is available or within reach at all.

**information**: What the actor knows or can find out, such as timetables, delays or changes.

**flexibility**: Choice of time or route, including how often a service runs.

**environment**: Emissions, noise and other effects of traffic on people and nature around it.

**other**: Only when the quote describes a dimension that is not on this list, such as staff or equipment.

## states_solution

**rule**: True when the quote asks for a particular thing or measure, so that only one way would satisfy it (a named product, a new facility, a specific rule or schedule). False when it asks for a property or result that several things could deliver, and false otherwise. The item keeps its kind and is not dropped. The need behind it is a separate item only if the text states it.

## means_end

**values**: `in_order_to`

**rule**: A directed link from item A to item B of the same actor when the text says that A is done or wanted in order to achieve B, or that A is the measure the actor wants for B. The connecting words must join the two quotes, such as "um zu", "damit", "deshalb", "in order to" or "so that". No link when the connection is only implied. Items of different actors are not linked here. Written as {from: A, to: B, relation: in_order_to}.

## order

**values**: `before`, `during`

**rule**: A link between two items of one text when words in the text order them in time, such as "zuerst", "dann", "bevor", "während", "first", "then", "after" or "while". Link only items that are events. before means that from comes before to; write "A after B" as B before A. during means that both happen at the same time; it has no direction, so the earlier quote is from. The order of sentences alone does not count. Order across texts is never labeled.
