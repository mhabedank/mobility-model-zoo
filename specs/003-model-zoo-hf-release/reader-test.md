# Reader test for a public model card (SC-003)

Give the published model card to a person who did not work on the project. They answer from the card alone, without other sources. The card passes if at least 6 of the 7 answers are correct.

| # | Question | Correct answer comes from |
|---|----------|---------------------------|
| 1 | What does the model do? | Summary, Input and output |
| 2 | Which input languages does it handle? | Summary or metadata (`language`) |
| 3 | How good is it, and measured against what? | Quality (agreement with the named reference on the frozen benchmark) |
| 4 | How fast is it, and on which hardware? | Speed and memory |
| 5 | What are its main limitations? | Limitations and risks |
| 6 | Under which license can it be used? | License |
| 7 | How do you run it? | How to run it |

Record: date, reader (role only, no name), card version, answers, score, and anything the reader found unclear. Unclear points become card improvements in the next patch version.
