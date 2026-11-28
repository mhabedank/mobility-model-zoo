# Provenance of the scout guideline v3 brief (never sent to any model)

- Owner: Martin Habedank. Answers given in chat (question pop-ups) on 2026-11-27, copied verbatim into `brief.yaml` (spelling unchanged).
- Structure: `brief.yaml` holds only machine keys and the owner's answers, so the writer reads no Claude-written text (constitution XI; precedent `cairn-teacher-v1` and 018 FR-006). Keys so far: `teacher_task` (question A1), `reader` (A3), `domain` (A2).
- Questions: [brief-questions.md](brief-questions.md). Claude asked them in German in chat:
  - A1 "Beschreib in ein paar Sätzen, was der Labeler mit einem Text tun soll."
  - A2 "Welche Texte gehören dazu? Was zählt für dich als Mobilität, und was liegt nur daneben?"
  - A3 "Wen soll sich der Labeler als Leser seines Ergebnisses vorstellen?"
- A1: the owner first said Claude may answer it, since the ban is about distillation. Claude pointed out that constitution 3.1.0 allows Claude drafts only for benchmark reference labelers and never for a teacher, and guideline v3 is read by the teacher of `span-train-v2` too. The owner then chose to write A1 personally (2026-11-27).
- A2: the owner's answer was "Folge der DEfinition von Mobilität, alles was dazu gehört gehört auch zu umserem Thema." Asked which definition, the owner said: "Na eine Domainspezifische Defition die du entweder in wissenschaftlichen paper oder auf wikipedia oder ein einem lexikon foinden soltest". So `domain` will hold an external definition, verbatim and with its source, chosen by the owner. It is not Claude-written. The old `configs/productdev/jtbd/domain/mobility.yaml` is not used for v3; its own provenance is unchecked.
- A2 sources: Claude searched the web and offered four candidates with source and licence (pop-up, 2026-11-27). Claude noted that all four are narrower than the old repository definition. The owner chose all four: Wikipedia (de) "Räumliche Mobilität", Wikipedia (en) "Transport", FGSV "Begriffsbestimmungen", Spektrum "Lexikon der Geographie", entry "Verkehrsmobilität". The owner pastes the defining text of each into chat, and it is stored verbatim under `text`. Claude does not copy the text from the web. Licence duties: the two Wikipedia texts need attribution and share-alike (CC BY-SA 4.0) in guideline v3. FGSV and Spektrum are proprietary, so only a short quote is possible, and whether quoting them in a labeling guideline is permitted still needs a compliance check.
- A2 synthesis: the owner asked Claude to build the definition from the four sources ("nimm die defintionen und bau unsere daraus"). Under 3.1.0 Claude may not write text that a teacher reads. The owner therefore chose to amend the constitution to 3.2.0 (PR #64), so that the owner-approved guideline may also reach the teacher. Claude then drafted `domain.definition` in its own words, quoting no source verbatim. It took the union of the four sources as the owner asked ("alles was dazu gehört"), so animals are included from Wikipedia (en). Social mobility and the transmission of messages or energy are excluded, although the FGSV includes messages and energy under "Verkehr". The owner approved the draft in chat on 2026-11-27. The formal approval with hashes covers the whole guideline package later. The draft is valid only once 3.2.0 is merged.
- Block B, first round (pop-ups, 2026-11-28). For each question Claude offered "Claude entwirft" as an option, which 3.2.0 allows. B2 (item boundaries): the owner answered personally, and the answer is stored verbatim under `item_boundaries.owner`. B1, B3 to B5 and B6: the owner chose a Claude draft. Claude wrote them in English for `brief.yaml` (`relevant`, `kind`, `actor_type`) and showed them in German in the pop-up. The owner approved all three unchanged.
- Block B, second round (pop-ups, 2026-11-28):
  - B9 (quotes): the owner chose "Nur Zitat (Recommended)". The per-item English statement of the 001 list is dropped.
  - B7, B8, B10 and B11: the owner chose Claude drafts (`evidence_type`, `evidence_scope`, `doubt`, `empty_result`) and approved all four unchanged.
  - B11 draws the consequence of B1, and the pop-up said so explicitly: since relevance follows from items, "relevant but no item" is no longer a valid result. It was valid in v1.
  - An estimated figure is `observation` under B7 but `quantified` under B8. The two scales are independent.
- Block C (pop-ups, 2026-11-28):
  - C10 (language): the owner chose "Code erkennt (Recommended)". Language is detected by code per text, is not a label and needs no agreement pilot.
  - C1 to C9: the owner chose Claude drafts (`job_kind`, `executor_role`, `actor_pair`, `mode`, `situation`, `improve`, `states_solution`, `means_end`, `order`) and approved all nine unchanged. Claude stated the common rules: a field is filled only when the text states it, a pointer takes the shortest verbatim span, and links need connecting words in the text.
  - The value lists of `mode` (15 values) and `improve` (11 values) are Claude drafts approved by the owner. The schema draft `jtbd-span-v2` (roadmap phase 1) can now be written from them.
- Block D (pop-ups, 2026-11-28):
  - D1: the owner chose "Fiktiv, Claude entwirft". D3: "12, je 6 de/en".
  - D2: the owner asked for edge cases but also for stratification, so that typical cases are not outnumbered (stored verbatim under `examples.cases_owner`). Claude explained that in-context examples bias a labeler (majority-label and recency bias). It proposed a matrix, which the owner approved: 2 empty examples (about 15 %), 5 typical ones (one long and dense, with about 10 items) and 5 with embedded edge cases.
  - Target distribution: counts only, from the non-Claude teacher run of span-train-v1 (1,100 chunks, `teacher-or-mimo-v2.6-pro`); no text was read. 15 % of chunks were empty, with 12.6 items per relevant chunk. Kind: pain 50 %, job 28 %, gain 22 %. Evidence: opinion 73 %. Scope: multiple 73 %. Actors: individual 44 %, organization 21 %, public_sector 19 %, worker 12 %, society 4 %. 4 % of quotes spanned more than one sentence. Caveat: that teacher read the old guideline v2.
  - `examples.yaml`: 12 examples with 55 items. Code checked that every quote, role and situation is a verbatim substring, that all values are valid and that all links point to existing items. One rebalancing round: e09 now has a mayor as speaker. Final distribution: kind pain 56 %, job 24 %, gain 20 % (close to the target). Still off: individual 65 % (target 44 %), public_sector 9 % (19 %), opinion 42 % (73 %), single 55 % (18 %). The owner approved the examples and sent the gaps to the Fable review.
  - Unclear points found while drafting. Claude did not decide them silently; the examples follow the reading given in brackets.
    - (a) The scope of one person's routine: single (one actor) or multiple (several events)? [single]
    - (b) Does a mode named only as absent or not used count, as in "wer kein Auto hat"? [no]
    - (c) Does a quantity that is not a count of cases, such as a distance, make an item quantified? [avoided in the texts]
    - (d) The same need stated twice in one text with different evidence. [two items, e06 i1/i2]
- Block E (pop-ups, 2026-11-28):
  - E1: "Code setzt zusammen (Recommended)". No writer model is used; code assembles the package from a fixed template.
  - E2: provisional thresholds approved, built on the project conventions (`configs/productdev/jtbd/decision-criteria.yaml`, criteria-v1, and `cluster-criteria.yaml`). They become final after the Fable review and before the pilot (Principle IV).
  - E3: "Kanten zuerst (Recommended)".
  - Notes for the Fable review:
    - (e) For links, the threshold of 0.4 equals the floor below which a field is not produced, so links have no revise band.
    - (f) Code assembly puts the owner's German answers verbatim into an otherwise English guideline: `teacher_task`, `domain.owner` and `item_boundaries.owner`.
- The brief is complete (blocks A to E). Next step: the Fable review with its own agents, then the owner's formal approval of the assembled package with hashes.
- Fable review 1 (2026-11-28, `review/fable-review-1.md`). Seven Fable subagents ran under the lead reviewer: research, five lenses and a synthesis. Verdict: not ready for the pilot. Findings: 6 blockers, 14 major, 11 minor. The owner decided all 15 questions of section 7 in pop-ups and took the recommended option every time:
  1. P1 item boundaries: whole clauses.
  2. P2 job is what gets done, how well it goes is a gain, a bare activity is no item.
  3. P14 no new field: cairn groups items, and the interface document and test I2 are corrected.
  4. P7 Torres test for `states_solution`.
  5. Note (a): single.
  6. Note (b): a mode counts even when negated. This reverses the earlier reading.
  7. Note (c): quantified only for a number of affected actors or occurrences.
  8. Note (d): two items.
  9. P10 the actor is whoever has the need.
  10. P6 pointer: noun phrase, nearest occurrence before the quote.
  11. P4 links scored on matched pairs: threshold 0.5, floor 0.3, enriched sub-sample.
  12. P3 metric sheet with the proposed thresholds.
  13. P13 examples corrected and grown to 16.
  14. Note (f): English operative versions of the owner's German sentences, for owner approval.
  15. P11 `improve`: direction sentence removed, one line per value.
- The owner then decided the four remaining proposals in pop-ups (2026-11-28), again taking the recommended option each time: P5 link definitions adopted (one `{from, to, relation}` encoding); P15 sentence on feelings added; P16 labeling in three passes; P17 new `drop_order`.
- Every new wording that follows from these decisions changes approved text. It is a Claude draft under 3.2.0 and needs the owner's approval before it counts.
- Fable review 2 (2026-11-28, `review/fable-review-2.md`; the reviewer worked alone). Of the 31 review-1 findings, 14 are resolved, 14 partly resolved and 3 open (R-18, R-24, R-29; open by decision or scope, not blocking). New: 3 blockers, 9 major, 10 minor. The owner decided all 10 questions of section 6 in pop-ups and took the recommended option every time:
  1. The speaker is the voice the text carries (M-1).
  2. A single event is an anecdote, whoever tells it.
  3. A step with a stated purpose is a job of its own, linked by means_end (M-4).
  4. A wish for a means with a verb of doing is a gain with `states_solution` true.
  5. `society` only with explicit words for everyone, so e09 i1 and i6 become individual.
  6. A wish about a feeling on the trip is an emotional job; `feelings` comes before `job_versus_gain`.
  7. The time word in a frequency phrase counts as situation.
  8. Pass 3 runs on every chunk with at least two items; the closed connective list only draws the enriched sample (M-2).
  9. The enriched link sample is 100 chunks per language, extended once to 200 if a link type has fewer than 30 units.
  10. Decision rule M-12: one extension; a keep-always field that would not be produced stops the pilot in that language.
- Not asked separately, but planned as drafts on the strength of the report's verdicts on the applying agent's points; they count only after the owner's formal approval: M-9 (domain test per item, R-15), M-10 (`doubt.fields` against required fields, R-22), `reader_en`, a non-printed note on R-24, and the e05 text change is kept. R-29 is picked up in the roadmap later.
- Content approval (2026-11-28): the owner read `review/changes-after-review-2.md` and approved in a pop-up ("Alles freigeben") all 26 pending keys of `brief.yaml` and the 16 examples. The approval includes the four labels the correction agent changed beyond section 7: e06 i3, e07 i1, e08 i1 and e08 i2. Still required before any labeling run: the merge of constitution 3.2.0 (PR #64), code that assembles the package (roadmap phase 2), and the owner's hash approval of the assembled package (`approval.json`).
- Left open by decision or scope: R-18, R-29; N-14, N-15, N-19 and the rest of N-22 (no wording proposed); role-word detection for the link sample, which code cannot check; the borderline labels e07 i6 and e10 i3, flagged in the change log.
- Hash approval (2026-11-28): the owner ran `jtbd guide approve` personally on the assembled package (`package/approval.json`). A first run recorded the copied placeholder "<dein Name>" as approver and was therefore invalid. The code now refuses such names, and `check` rejects such records. The second run recorded "Martin Habedank" at 2026-11-28T15:51:13Z, manifest sha256 `e1aebe37…808d`. `jtbd guide check` passes. Labeling runs still need constitution 3.2.0 on `main` (PR #64) and the v2 labeler schema and passes (roadmap phase 3).
- Pass instructions (2026-11-28, feature 025 task T006, research R2): under constitution 3.2.0, the text that tells a labeler what to return in each pass must be part of the owner-approved package, because the teacher reads it. Claude drafted `pass_instructions` (pass1, pass2, pass3) from the approved `assembly.passes`. The draft adds no new rule and refers to the guideline for every definition. The owner's approval follows in a pop-up (T007). After it, the package is assembled again with the three texts as `instructions/pass{1,2,3}.md`, and the owner approves the hashes again (T010). The hash approval of 2026-11-28 lapses by design.
