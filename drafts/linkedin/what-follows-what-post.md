# LinkedIn: What follows what? (Field note, part 3, English)

Bild: drafts/linkedin/what-follows-what-linkedin.png
Bildnachweis: River lock with its gates opening and a push boat waiting (AI-generated, CC0)

## Post

Plan the trip, buy a ticket, walk to the platform, wait, board, change, arrive.

Anyone can write that order down from memory. That is exactly why I thought it was the easy part.

I am building a model that reconstructs customer journeys from text: complaints, forum posts, interviews. Who is affected, and what something is for, often sits in a single sentence. The order almost never does.

The reason is mundane. A complaint usually describes one moment.
"The machine would not take my card."
"Platform changed, no announcement."
One step, one quote, no before and no after.

The order only appears once I put four of those texts side by side. And then it does not come from the texts. It comes from me, because I know how a train journey goes.

In process mining terms, that is an event log without a case ID: plenty of events, but nothing says which ones belong to the same trip. What comes out is the order you put in.

There is a second effect. People tell a sequence mostly when something went wrong. The transitions with evidence behind them are the ones that failed. The smooth path that every journey map is built around is barely in the data.

So the model now stores an order only when a single text tells it, with a quote. Anything that only appears across texts is a hypothesis, and it is marked as one.

What I have not solved is how to test those hypotheses properly. If you build journeys from interviews or complaints: where does your order come from, and how do you keep it apart from what you already knew?

#CustomerJourney #ServiceDesign #ProcessMining #PublicTransport

## First comment

The strongest objection to this post is one I have myself: a well-run interview is not a complaint. People tell whole sequences there, with a before and an after. How often that happens in my texts, I have not counted yet. That is the next step.

Two things that did not fit in the post. Many transitions are not "after" at all, they are "during" ("I was on hold to the hotline the whole time I waited"). And in some networks you buy the ticket before you board, in others on the bus. A row from left to right can show neither.

Written out, with sources (Schank & Abelson, Labov & Waletzky, Allen, van der Aalst):
https://mhabedank.github.io/mobility-model-zoo/notes/what-follows-what/
