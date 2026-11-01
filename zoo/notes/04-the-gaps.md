---
title: The gaps
series: Mapping the mobility experience
part: 4
parts: 5
date: 2026-11-01
description: A map built only from what texts say has holes in it. Some close when you read more,
  some only when you ask, and one kind must never be filled, least of all by a model.
lead_image: note:the-gaps
author: Martin Habedank
lead_caption: A shelter, a bench and a bus. No ticket machine, no platform, no departure board. A
  journey map with a column for each would show three gaps here, and nothing is missing.
diagrams:
  three-holes: Three empty places on one trip. On the map they look the same, and each needs a
    different answer.
licence: CC-BY-4.0
licence_label: CC BY 4.0
licence_url: https://creativecommons.org/licenses/by/4.0/
references:
- id: maynez-2020
  text: 'Maynez, J., Narayan, S., Bohnet, B., & McDonald, R. (2020). On faithfulness and factuality
    in abstractive summarization. In Proceedings of the 58th Annual Meeting of the Association for
    Computational Linguistics (pp. 1906-1919). Association for Computational Linguistics.
    doi:10.18653/v1/2020.acl-main.173'
- id: rubin-1976
  text: 'Rubin, D. B. (1976). Inference and missing data. Biometrika, 63(3), 581-592.
    doi:10.1093/biomet/63.3.581'
- id: nisbett-1977
  text: 'Nisbett, R. E., & Wilson, T. D. (1977). Telling more than we can know: verbal reports on
    mental processes. Psychological Review, 84(3), 231-259. doi:10.1037/0033-295X.84.3.231'
---

[The last note](../what-follows-what/) ended with a map that has a lot of empty space in it. Each
of the three notes so far removed something. An item needs a quote. An "in order to" needs a
sentence that says so. An order needs one text that tells it. What is left is sparse: a few
crossings between actors, a few short chains, a few told sequences, and blank paper in between.

The obvious next step is to fill the blank paper. Almost everything else in this project is done
by a model, so whether a model could fill it is not in doubt. Whether it should depends on what
kind of hole it is.

## A model does not leave a blank

I have one measurement that bears on this. It comes from the benchmark the
[extraction model](../../models/scout-large/) is scored on, and the task there is narrow: read a
text, find what someone is trying to get done and what gets in their way, and give each finding as
a word-for-word quote. Whether a quote occurs in the text is a string comparison. It needs no judge
and no opinion.

Every generative model in that pilot failed it some of the time. The best one, Claude, returned 20
quotes out of 1,412 that were not in the text. The mini tier of the GPT family returned 204 out of
1,348, about one in seven. The small local models I ran as baselines missed between 18 and 41 per
cent. Very few of these quotes were made up from nothing. For the three models I considered as
teachers, 470 of 484 could be matched back to a passage of the source. Each model had quoted a
sentence close to the one in the text, but not that sentence.

The extraction model returned 1,441 quotes, and all of them were in the text, because it has no
way to write one. It marks where a quote starts and where it ends, and the quote is whatever lies
in between. It agrees with the reference models less often than the large models did, on every
dimension, and I accept that trade.

If a model cannot leave a sentence alone when the only job is to copy it, a model asked to complete
a map will put into each empty place what usually goes there. Research on summarisation found the
same thing at the scale of a whole document: systems add content the source does not contain, and
some of that content is even true, learned elsewhere, and still not in the document.[ref:maynez-2020]

So whether a model would fill a gap is settled. It will. The question is which gaps it must not.

## Three holes

On a map the holes look identical, a place with nothing in it. They come from three different
places.

The first kind is **not read**. The thing exists and somebody wrote it down, just not in the texts
I have. [The second note](../how-big-is-the-question/) had a pain at the ticket counter whose
cause sits in the fare zones, and the fare zones are described in tariff documents and planning
reports, not in forum threads. The hole on the operator's side of the counter is a hole in my
corpus. It closes when I read something else, and I can say what that something is.

The second kind is **not said**. The step happened, and nobody wrote about it because nothing went
wrong. Reading more texts of the same kind does not help here, because the reason for the silence
is the very thing that is missing. Statistics separates values that are missing for reasons
unrelated to them, values missing for reasons visible elsewhere in the data, and values missing
because of what they are.[ref:rubin-1976] The third sort cannot be filled from the values you
have, since those are exactly the ones that were different. Trips that went smoothly are missing
because they went smoothly. Fill the gap from the complaints and it fills with trouble; fill it
from the script and it fills with the timetable brochure. This hole closes only with another
instrument: asking people, or counting trips.

The third kind is **not there**. The map expects something in this place, and on this trip there
was nothing to expect. The stop in the picture above is a shelter at the edge of a field. There is
no machine, so nobody bought a ticket at one; they paid the driver. There is no platform to walk to
and no display to check. A journey map with the usual columns (plan, buy, walk to the platform,
wait, board) shows three empty cells at this stop, and none of them is missing anything. Survey
research keeps this apart as a matter of routine. "Does not apply" is a different answer from "no
answer", and you do not impute a commute for someone who works from home.

[diagram:three-holes]

## The frame as an alibi

The first two holes are real. Something happened there, and a model that fills them is guessing at
a fact. The third has no fact behind it. The place exists only because the frame of the map has a
column for it. A model asked to complete the map does not see that difference. It sees an empty
cell in a structure it knows, and it knows what usually goes there.

This is where the frame turns into an alibi. A filled cell under a named stage of a recognised
method looks like a result of the method, and nobody asks where the entry came from, because the
column asked for it. "Buy ticket: long queue at the machine, fares unclear" reads like a finding.
At the field shelter it is a sentence a model wrote because the stage was called "buy ticket".

People do the same, and it has been measured. Asked why they chose one item over another, people
give confident reasons that often have nothing to do with what changed their choice, and their
reasons match what an outsider would have guessed, as if both drew on the same idea of what usually
causes what.[ref:nisbett-1977] The word for this is confabulation. It is not lying. It is a fluent
account produced because an account was expected, assembled from what usually happens. A model
filling a cell that does not apply is doing exactly that, and the vocabulary of the method makes it
look like work.

## What I changed

The map has no fixed grid. There is no row of stages that every journey is laid against, so there
is no empty cell for a stage a trip did not have. What gets drawn is what the texts support:
crossings, chains, told sequences.

A hole is drawn only when something points at it, and it carries its kind and what would close it.
A pain whose cause sits on another actor's side points at a "not read" hole, and the hole names the
kind of document that would describe the cause. A transition assembled across texts, the
hypothesis from the last note, points at a "not said" hole between two told steps, and the hole
names the question to ask. A "not there" is not stored, because there is nothing to store.

No model fills a hole. A model may point at a passage that closes one, the way the extraction model
points at a quote, and then the passage closes it.

Nothing that measures the map rewards it for being full. Coverage, the share of stages that have an
entry, is the easiest number to put on a journey map and the one that pays most for confabulation.
My own rules already say that an empty result from the extraction model is a correct result, and
that no metric may reward filling it. The map inherits that rule.

## What comes next

Take the grid away and fill nothing, and what is left is honest and patchy. It will not look like
the journey maps people are used to, and it will not cover a whole trip. That turns the question
this series started with around. If the map does not have to be complete, what does it have to do
to be worth drawing at all?

That is the next part.
