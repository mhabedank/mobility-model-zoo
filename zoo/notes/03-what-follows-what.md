---
title: What follows what?
series: Mapping the mobility experience
part: 3
parts: 5
date: 2026-10-28
description: Knowing where a pain sits is not knowing what came before it. Most texts describe one
  moment, and an order that only appears across texts is a hypothesis, not evidence.
lead_image: note:what-follows-what
author: Martin Habedank
lead_caption: One of the few places where the order is built into the concrete. The boat waits,
  the gates open, and nobody has to work out which came first.
diagrams:
  told-and-assembled: Above, an order one person wrote down. Below, an order I put together from
    four people who each wrote about one moment.
licence: CC-BY-4.0
licence_label: CC BY 4.0
licence_url: https://creativecommons.org/licenses/by/4.0/
references:
- id: schank-1977
  text: 'Schank, R. C., & Abelson, R. P. (1977). Scripts, Plans, Goals and Understanding: An
    Inquiry into Human Knowledge Structures. Hillsdale, NJ: Lawrence Erlbaum.'
- id: labov-1967
  text: 'Labov, W., & Waletzky, J. (1967). Narrative analysis: oral versions of personal
    experience. In J. Helm (Ed.), Essays on the Verbal and Visual Arts (pp. 12-44). Seattle:
    University of Washington Press.'
- id: allen-1983
  text: 'Allen, J. F. (1983). Maintaining knowledge about temporal intervals. Communications of
    the ACM, 26(11), 832-843. doi:10.1145/182.358434'
- id: vanderaalst-2016
  text: 'van der Aalst, W. M. P. (2016). Process Mining: Data Science in Action (2nd ed.).
    Berlin, Heidelberg: Springer. doi:10.1007/978-3-662-49851-4'
- id: chambers-2008
  text: 'Chambers, N., & Jurafsky, D. (2008). Unsupervised learning of narrative event chains.
    In Proceedings of ACL-08: HLT (pp. 789-797). Columbus, Ohio: Association for Computational
    Linguistics.'
---

[The last note](../how-big-is-the-question/) turned the map's vertical axis into edges: two
items, an "in order to" between them, and the sentence that says so. That settles why someone
does something. It says nothing about what they did before it, and a journey map is mostly
that: a row of steps from left to right.

I assumed the row was the easy part.

## The row everybody already knows

Plan the trip, buy a ticket, walk to the platform, wait, board, ride, change, arrive. I can
write that down from memory, and so can anyone who has ever taken a train. Every journey map I
have seen in mobility starts with a version of it.

That is exactly what should have made me suspicious. Cognitive science has a name for knowledge
of this kind. A script is the stereotyped sequence of a familiar situation, and the classic
example is a restaurant: you go in, sit down, order, eat, pay and leave.[ref:schank-1977] Tell
someone that a friend ordered the fish and left a large tip, and they will understand that she
ate it and paid, although neither was said. The script fills in the steps nobody mentioned.

A journey map is a script for a journey. Most of its order comes from what the person drawing
it already knows. That is fine in a workshop where everyone shares the script. It is a problem
in a model that is supposed to read the order out of text, because the script will supply an
order whether the text contains one or not.

## What a single text contains

So I looked at what the texts actually say about order.

Most of them say nothing. A complaint is usually about one moment. "The machine would not take
my card." "The platform changed and there was no announcement." "The app said the train was
on time." Each of those is one step, with a quote behind it, and no before or after. I have not
counted how common that is yet, and it is the first thing I will count. Reading through them, it
is the normal case.

Some texts do tell a sequence. "I bought the ticket at the machine, got on, and only at the
second stop realised it was the wrong zone." That is three steps in one sentence, and their
order is in the sentence itself. Sociolinguistics worked out why decades ago. In a spoken
account of something that happened, the clauses are in the order of the events, and swapping
two of them changes what the listener thinks happened.[ref:labov-1967] That is the kind of
sentence an order can be read from, the same way an "in order to" can be read from a "so that".

Even those sentences are less tidy than a row. "I missed the connection because the first train
was late" is told back to front. "I was on hold to the hotline the whole time I waited on the
platform" is not before or after at all, it is during. There are thirteen ways two intervals of
time can relate to each other, and "before" is one of them.[ref:allen-1983] A journey map draws
that one and has no notation for the other twelve. And some orders are not fixed even in
principle: in one network you buy the ticket before you board, in the next you buy it on board.

## Why it takes more than one text

This is the reason order is harder than height. An "in order to" joins two things in one breath.
An order needs two events, and the typical text names one. So most of the order in a map built
from texts is not seen inside any text. It is seen across them: one person writes about the app,
another about the queue, a third about the platform, a fourth about the missed connection, and I
put them in a row because I know the row.

[diagram:told-and-assembled]

Process mining makes the difference precise. It reconstructs processes from event logs, and the
one thing an event log cannot do without is a case identifier: the field that says which events
belong to the same order, the same patient, the same trip.[ref:vanderaalst-2016] Only events with
the same case can be said to follow each other. My texts have no case identifier. Each post is a
fragment of a different trip by a different person on a different day. Lining them up is process
mining without the case, and the order that comes out is the order that went in.

There is a serious version of doing it anyway. Research on narrative event chains has learned,
from a large amount of news text, which events tend to follow which, and the chains it recovers
look like scripts.[ref:chambers-2008] That is useful, and it is honest about what it is: a statement
about what usually follows what in the way people write. It is a prior. It is not evidence that,
on this trip, this step followed that one.

## Seen in one text, assumed in the map

That gives me two kinds of order, and they need to stay apart.

An order told inside one text has a sentence behind it, the same as an item or an "in order to".
An order that appears because two items from different texts were placed side by side has
nothing behind it except the person or the model that placed them. Both can be true. Only one is
evidence.

My own rules already say which way to fall. Evidence is graded by how directly the text supports
a claim, not by how plausible the claim is. An order assembled across texts is close to the
purest case of a plausible claim there is: it is plausible because it matches the script, and
the script is where it came from.

There is a second effect that is easy to miss. The texts that do tell a sequence are not a fair
sample of trips. Nobody writes the story of a journey that went the way it was supposed to. The
sequences people tell are the ones where something broke: the wrong zone, the missed connection,
the platform nobody announced. So the transitions that have evidence are mostly the ones that
failed, and the smooth path that a journey map is built around is the part the texts almost never
describe. It is the script again.

## What I changed

The requirement for the next model now has a second kind of edge. An order edge is two items from
the same text, the words that order them ("then", "after", "by the time", "because"), and the
quote. Relations that are not "before" are kept as they were said, during or overlapping, instead
of being forced into a row.

Order across texts is not extracted at all. If it appears, it appears in a later step, drawn
differently and never counted as evidence. It is not worthless. A transition assembled across
texts is a hypothesis with a test attached: find texts that mention both steps, and see which way
round they tell them.

## What comes next

Put the three parts together, whose journey, how high, what follows what, and the map that comes
out has a lot of empty space in it. The script that made the order look obvious will fill all of
it without being asked. Whether it should depends on what kind of gap it is, and there turn out
to be three.

That is the next part.
