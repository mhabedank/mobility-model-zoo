---
title: Whose journey?
series: Mapping the mobility experience
part: 1
parts: 5
date: 2026-10-22
description: An opportunity without a place is hard to act on. The attempt to read customer
  journeys out of text stalled on a question I thought I had already answered.
lead_image: note:whose-journey
author: Martin Habedank
diagrams:
  three-lanes: One counter, three journeys. Whichever one you draw, the other two
    parties turn into scenery.
licence: CC-BY-4.0
references:
- id: solomon-1985
  text: 'Solomon, M. R., Surprenant, C., Czepiel, J. A., & Gutman, E. G. (1985). A role theory
    perspective on dyadic interactions: the service encounter. Journal of Marketing, 49(1),
    99-111. doi:10.2307/1251180'
- id: shostack-1984
  text: 'Shostack, G. L. (1984). Designing services that deliver. Harvard Business Review,
    62(1), 133-139.'
  url: https://hbr.org/1984/01/designing-services-that-deliver
  link_label: hbr.org
- id: bitner-2008
  text: 'Bitner, M. J., Ostrom, A. L., & Morgan, F. N. (2008). Service blueprinting: a practical
    technique for service innovation. California Management Review, 50(3), 66-94.
    doi:10.2307/41166446'
licence_label: CC BY 4.0
lead_caption: An empty platform. The one version of this story in which
  nobody's journey gets in anybody else's way.
licence_url: https://creativecommons.org/licenses/by/4.0/
---

I have [a model](../../models/scout-large/) that reads a text and marks what someone is
trying to get done, what gets
in the way, and what they would gain if it stopped getting in the way. It returns each item
as a verbatim quote, so every claim can be traced back to the sentence it came from. The
[next model in line](../../roadmap/) takes thousands of those items from many texts and
merges them: the same
need voiced twice becomes one need with a count, and needs that belong together become an
opportunity.

That gives me a ranked list of problems. What it does not give me is where any of them
happens.

A pain without a place is hard to act on. "Buying a ticket is confusing" could mean the app,
the machine, the fare zones, the moment at the counter, or the realisation two stops later
that the wrong ticket was bought. Those are five different products. So the obvious next
step was a model that reads the same texts and reconstructs the journey, and then every
opportunity could be pinned to the point where it hurts.

I did not get as far as building it. I got stuck on the first question.

## The question I got stuck on was whose

The reflex in product work is to answer that with a persona. Give the journey a name, an age,
a commute and a photograph, and the map has a protagonist.

I had ruled that out before this came up, and for reasons that have nothing to do with
taste. My own ground rules say it twice: the first principle is problem-first, not
persona-first, and a later one keeps persona formation out of the extraction model
altogether, as a separate downstream step. The reasoning was about evidence. A persona is a
composite. The moment you average four interviews into one fictional person, you can no
longer point at the sentence that supports a claim, and a claim you cannot trace is the one
thing I refuse to ship.

But mobility breaks personas in a second way, one that is less about method and more about
the subject itself.

The same human being is a different actor several times a day. At seven in the morning they
are a commuter optimising for reliability. At noon they are a parent with a child and a
folded buggy, optimising for step-free access. In the evening they are waiting for a parcel
and have become, without noticing, a customer of a logistics network. Nothing about them has
changed. The role has. And the role, not the person, is what determines what they are trying
to get done.

So the unit is the role. I thought I already had that covered.

## I had the dimension before I had the idea

My extraction model already labels every item with an
[actor type](../../formats/jtbd-span-v1/). There are five: a private
individual, a worker acting in their job, an organisation, a public body, and society at
large.

Looking at that list again with the journey question in hand was uncomfortable. I did not
arrive at those five from a theory of who acts in a mobility system. I arrived at them
because I needed to grade evidence, and knowing whether a complaint came from a passenger
or from an operator changes how much it weighs. The dimension was built for weighing, and I
had been reading it as if it described the world.

It describes one thing well: who *has* the job, pain or gain in this sentence. That is the
right question for a single quote. It is the wrong question for a journey, because it
assumes the item belongs to one party.

## The ticket counter

Here is the example that made the problem concrete, and it is deliberately the most boring
situation in public transport.

Someone wants a ticket. A member of staff is there to sell it. Service research has read that
encounter as two people performing roles for each other for forty years.[ref:solomon-1985] The operator is deciding, on
a longer timescale, whether a staffed counter pays for itself at this station.

Three actors, one moment, and three different problems. The traveller's problem is that they
do not know which ticket is right and the queue is long. The employee's problem is that the
rules they have to apply were written for a tariff system they did not design, and the
person in front of them is becoming angry about something the employee cannot change. The
operator's problem is a cost line.

Now try to put that into one journey. Whose? If you draw the traveller's, the employee
appears as a touchpoint, a box labelled "staff interaction", and their entire problem
disappears, because in the traveller's journey the employee is scenery. If you draw the
employee's, the traveller is scenery. Draw the operator's and both are a throughput number.

Each map is correct. Each one deletes the thing that actually generates the pain, which is
that three parties with different problems are standing in the same two square metres.

[diagram:three-lanes]

## Service design wrote this down decades ago

A service blueprint[ref:shostack-1984] draws the customer's actions and the staff's actions on
separate lanes, splits the staff lanes into what the customer can see and what happens behind
the scenes, and marks the lines where the lanes touch.[ref:bitner-2008]

I am not going to improve on that as a notation. What is different in my case is where
the blueprint comes from. A blueprint is drawn by hand, by a team, for one service they
already understand. I want to read one out of text that was never written to describe a
service: forum posts, complaints, interview transcripts, studies. Nobody writing a complaint
about a ticket machine is documenting a lane in a blueprint. They are describing two minutes
of their life.

Whether that is recoverable at all is an open question, and it is the next thing I have to
test rather than assume.

## What I changed

The actor dimension stays, because weighing evidence still needs it. But it cannot stay a
flat list of five values if it is also supposed to carry the journey. The object that matters
is a pair of actors at a point where their paths cross, together with the pain that exists
because the two of them want different things in that spot.

That is a requirement I now have for the next model, written down before anyone wrote any
code. It is also a warning about the ones I already shipped: a dimension that was designed
for one purpose will quietly be used for another, and nothing in the system complains.

## What I found next, and could not fit in

There is a detail in the ticket counter scene that the actor dimension could not hold, and it
is not about who the three parties are.

The traveller is dealing with the next ninety seconds. The employee is dealing with a
procedure that is the same every day. The operator is dealing with a decision that will stand
for years. They are not only three different parties. They are working at three different
sizes of question, and the smallest one is the only one anybody ever writes a forum post
about.

That is [the next part](../how-big-is-the-question/).
