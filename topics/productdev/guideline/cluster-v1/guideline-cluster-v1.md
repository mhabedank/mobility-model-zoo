# Labeling guideline cluster-v1: same need, more specific need, belongs together

You compare items that an extraction model found in mobility texts. Every item is a verbatim quote with its kind: `job` (something an actor tries to get done), `pain` (a problem or obstacle) or `gain` (a benefit or desired improvement). You judge **only the quote and its kind**. You never see, and must not guess, the text around the quote.

## 1. Pairs: same, more specific, different

For a pair of items **of the same kind**, answer exactly one label:

| Label | Definition | Test question |
|---|---|---|
| `same` | Both quotes state the same need in other words. A person building a list of needs would write them down once. | "Would one line in a needs list cover both without losing anything?" |
| `a_more_specific` | Quote A states a narrower version of quote B's need: B's need is fully part of A's, A adds a condition, place, time, group or means. | "Is A a special case of B?" |
| `b_more_specific` | The same with B narrower than A. | "Is B a special case of A?" |
| `different` | The needs are not the same and neither is a special case of the other, even if they share a topic. | "Are these two separate lines in a needs list?" |

Rules:

1. Language does not matter. A German and an English quote can be `same`.
2. Wording does not matter, the need does. "Finding a parking space takes forever" and "I spend ages looking for somewhere to park" are `same`.
3. A different actor does not make a need different if the quote states the same need (the actor type is recorded elsewhere).
4. Opposite statements are `different` ("the bus is always late" and "the bus is reliable").
5. A cause and its effect are `different` ("the road is closed" and "I arrive late").
6. When unsure between `same` and a "more specific" label, choose the "more specific" label. When unsure between a "more specific" label and `different`, choose `different`.
7. Very short or generic quotes ("It's too expensive.") are judged as they stand. Do not fill in what they might refer to; a generic quote can be the more general side of a pair.

Pairs of different kinds are never shown to you as pairs: duplicates and the specificity relation stay within one kind.

## 2. Sets: what belongs together

For a set of items **of any kind**, group the items into clusters. A cluster is one opportunity: one job together with the pains and gains about getting that job done, or one problem area that several pains and gains share.

Rules:

1. Every item belongs to exactly one cluster. A cluster of one item is allowed.
2. A job and its pains and gains belong to the same cluster ("get to work on time" with "the train is often cancelled" and "a direct connection would save me twenty minutes").
3. Items that are `same` or "more specific" as defined in section 1 always share a cluster.
4. Do not build clusters by kind, by actor or by language.
5. Optionally, group your clusters into coarser groups when several clusters clearly serve one broader goal (for example "daily commute" over "find parking" and "get a seat on the train"). If no such goal is clear, leave the coarser grouping out.

## 3. Output

Answer only in the JSON format given with the task. Use only the ids you were given. Do not add text, explanations or new items.

Examples: [examples.yaml](examples.yaml).
