# Provenance of the JTBD labeling guidelines and worked examples (Principle XI check)

Date: 2026-10-14. Status: findings confirmed from session transcripts; owner decision recorded
(see "Owner decision"). Nothing has been changed, relabeled or published. Constitution: 3.0.0,
Principle XI "No Claude in Model Learning or Extraction".

## Question

Were `guideline-v1.md`, `guideline-v2.md`, `examples/` and `examples-v2/` (and, for completeness,
`cluster-v1/`) written by Claude? If so, the teacher prompt that labeled `span-train-v1`, and with
it the training data of the published model scout-large 0.1.x, was built from Claude-written
model input.

## Method and limits

- Git history of the files and their pre-move paths (`guideline/…`, moved in `acb76e2` on
  2026-10-08), full commit messages and trailers, tasks of features 001, 004 and 009, the pilot
  revision record `data/analysis/pilot-v1/revisions.md` (not in git), run manifests and frozen
  hashes, PR #4 description, `compliance/decisions.yaml`.
- All commits are authored by the owner's git identity or by "Claude"; authorship is inferred
  from `Co-Authored-By`/`Claude-Session` trailers, commit wording and task records.
- `Co-Authored-By: Claude` trailers are used inconsistently (44 of 150 non-merge commits before
  2026-10-08), so a missing trailer is not evidence of human authorship.
- Local Claude Code CLI transcripts (`~/.claude/projects/*mobility*/*.jsonl`, 2026-09-27 to
  2026-10-14, plus the 2026-09-26 session) were scanned for phrases that occur only in each
  artefact. A hit inside an assistant `Write`, `Edit` or `Bash` tool call proves that Claude
  wrote the text; hits in user-typed messages would have pointed to the owner. Desktop-app session
  search had no mobility-llm sessions before 2026-10-09.

## Findings

| Artefact | Created in | Evidence | Claude-written? | Confidence |
|---|---|---|---|---|
| `guideline-v1.md` | `15fe1f1`, 2026-09-26 (001 setup) | Trailer `Co-Authored-By: Claude`; message: "Includes a draft labeling guideline (guideline-v1) with six worked examples, to be reviewed before `pilot freeze`". Transcript `1bc8b682`, 2026-09-26 09:40: assistant `Write` of `guideline/guideline-v1.md`, model `claude-opus-5-5`. Never edited afterwards. | Yes | Certain |
| `examples/` (6 files) | `15fe1f1` | Same transcript, 09:40: assistant `Bash` calls (model `claude-opus-5-5`) create the files in `guideline/examples`. Never edited afterwards. Task T044 is marked `(ops/doc)`, which in 001 only means "not code". | Yes | Certain |
| `examples-v2/` (6 files) | `c8ee06e`, 2026-10-06 | Copy of `examples/` with two edits (examples 05 and 06: `evidence_scope` single → multiple, one added sentence each). Transcript `75f6dc84`, 2026-10-06 11:51: assistant `Bash` (`cp -r guideline/examples …` plus the edits), model `claude-opus-5-5`. | Yes | Certain |
| `guideline-v2.md` | `c8a8983`, 2026-10-06 (T063/T064) | About 78 of its 121 lines are unchanged from v1. The 43 added lines (R1–R6) were written by an assistant `Bash` heredoc script in transcript `75f6dc84`, 2026-10-06 11:50, model `claude-opus-5-5`. The local model qwen3.8:27b only categorized the contested entries. Between 10:30 and 11:52 the owner typed only a status question; the rest were monitor notifications. | Yes, entirely | Certain |
| `data/analysis/pilot-v1/revisions.md` (R1–R6) | not in git | Same transcript, 11:51: assistant `Bash` script writes the file, model `claude-opus-5-5`. | Yes | Certain |
| `cluster-v1/guideline-cluster-v1.md`, `cluster-v1/examples.yaml` | `9891757`, 2026-10-09 (009 setup) | Commit author "Claude", trailer `Co-Authored-By: Claude Opus 5.5`, `Claude-Session` link; message: "guideline cluster-v1 with DE/EN examples". | Yes | Certain |
| cluster-v1 rules 8–12 and contrast examples | `e6a6532`, 2026-10-11 | Transcript `6250e49b`, 2026-10-11 10:35: assistant `Edit` of `guideline-cluster-v1.md`, model `claude-opus-5-5`. | Yes | Certain |

## Where the texts became model input

`labeling/prompt.py` builds the system prompt from the full guideline text plus every example
(source text, target JSON output and the "Why" note), so these files are few-shot examples in the
literal sense of Principle XI.

- **span-train-v1 → scout-large.** The teacher run
  `data/span-train-v1/runs/run-teacher-teacher-or-mimo-v2.6-pro-train-6b5662fa` records
  `guideline_sha256 6b5662fa…3075`, which matches the current `guideline-v2.md` byte for byte.
  The examples path is `examples-v2` (`configs/productdev/jtbd/span-train-v1.yaml`). The
  teacher's 1,100 labels trained scout-large 0.1.0; 0.1.1–0.1.3 are card and compliance updates
  of the same weights.
- **Benchmarks pilot-v1 / pilot-v2.** The same prompts were used by the GPT reference, the four
  teacher candidates and the three baselines. The quality numbers on the scout-large card are
  agreement on pilot-v2.
- **cluster-v1.** The cluster guideline and examples were the prompt for the cluster-v1 reference
  labelers (Claude and GPT mini). cairn-base has not been released; feature 018 replaces the
  guideline for cluster-v2.

## What Principle XI implies

1. The ban explicitly covers "worked or few-shot examples, gold items or label examples that a
   model sees as input", and says that what Claude writes as a development assistant "MUST NOT
   be used as model input data". The findings above confirm that the teacher prompt for
   span-train-v1 violates both clauses. It was produced before constitution 3.0.0 (2026-10-13), but the
   principle governs the published artefacts as they are.
2. The carve-out for existing material covers only "the Claude reference labels" in pilot-v1,
   pilot-v2, cluster-v1 and spike-v2. It does not cover guidelines or examples. Decision
   `D-claude-risk-0.1.x` (2026-10-08) covers the same labels, and its rationale ("not as training
   data") does not address the teacher prompt.
3. "Derived form (paraphrased, filtered, aggregated …)" is broad. Whether the teacher's labels
   and the student weights count as derived from Claude output, or only as conditioned on it, is
   an interpretation the constitution leaves open. The strict reading puts span-train-v1 and
   scout-large 0.1.x inside the ban.
4. The principle "admits no deviation". A documented owner decision that accepts the current
   state therefore does not fit the constitution as written; it needs a constitution amendment
   (a new carve-out) or one of the remediation paths below.
5. Any rewrite must not start from the existing text. A non-Claude model that paraphrases the
   Claude-written guideline or examples produces "derived form" again. A clean rewrite starts from
   sources that Claude did not write, for example the qwen3.8:27b categorization output
   (`data/analysis/pilot-v1/contested-review.csv`). `revisions.md` is Claude-written and is not a
   clean source. Two inputs need an owner ruling: the requirement lists in 001 T043/T044 (written
   in a Claude-assisted spec), and the contested entries themselves, which contain Claude
   reference labels; using those to shape a new guideline would be a new role outside the
   carve-out ("in the role they have").
6. The scout-large card and compliance records currently say how the reference labels were made,
   but not that the guideline and examples were Claude-written.

## Options

| Option | What it means | Consequences |
|---|---|---|
| A. Clean rebuild | A non-Claude model (for example on the DGX Spark) writes a new guideline and fictional examples from the requirements, not from the old text; a new benchmark version is labeled without Claude (XI already requires that for new versions); the teacher relabels span-train with the new prompt; scout-large is retrained as a new version. | Removes the issue at the root. Costs teacher API spend, Spark time and a new benchmark; the new numbers will not be comparable with pilot-v2. |
| B. Rebuild plus handling of 0.1.x | Option A, and 0.1.x is marked experimental or deprecated on Hugging Face with a card notice that names the Claude-written prompt. | Honest for current users until the new version exists. A deprecation note keeps the published install lines working. |
| C. Withdraw 0.1.x now | Make the 0.1.x repositories private or delete them until a clean version exists. | Strongest signal of compliance; breaks the published install lines and website links. |
| D. Owner decision and amendment | Record a decision (like `D-claude-risk-0.1.x`) and amend Principle XI with a narrow carve-out for the existing guideline v1/v2 and examples in pilot-v1, pilot-v2 and span-train-v1. | Cheapest. Weakens the "no deviation" rule the owner set on 2026-10-13; needs a constitution version bump and a card disclosure. |
| E. Disclosure only (with any option) | Add the guideline provenance to the card and the 0.1.x compliance records. | Needed in every option except a full withdrawal; does not resolve the XI conflict on its own. |

For cluster-v1, feature 018 already replaces the guideline and examples. The same rule as in
point 5 applies: the cluster-v2 guideline should not be produced by rewriting the cluster-v1 text.

## Owner decision (2026-10-14)

The owner chose **option A**: a clean rebuild (new guideline and examples without Claude, a new
benchmark version labeled without Claude, teacher relabeling of the training split, retraining as
a new scout-large version). scout-large 0.1.x stays published unchanged until the new version
exists. The owner asked for the transcript check before deciding; it confirmed every row of the
findings table.

Follow-up rulings by the owner on the same day:

1. **No interim disclosure.** The card and the 0.1.x compliance records stay as they are until the
   rebuilt version ships (option E is not applied).
2. **Teacher labels are not "derived form".** Labels produced by a non-Claude teacher with a
   Claude-written prompt, and the student trained on them, are not Claude output in derived
   form. 0.1.x therefore needs no deprecation notice because of this finding; the
   Claude-written prompt itself is replaced by option A.
3. **Requirement lists allowed.** The requirement lists in 001 T043/T044 (Claude-assisted spec,
   development-assistant role) may be the starting point for the non-Claude rewrite.
4. **Contested entries allowed.** The contested entries, which contain Claude reference labels,
   may inform the new guideline.

Ruling 4 is narrowed to stay inside Principle XI, which lists "any signal used for … prompt
optimization" among the forbidden uses and keeps the existing Claude reference labels only "in
the role they have". The rewrite may use the qwen3.8:27b categories, the source chunk texts and
the non-Claude (GPT) side of each contested pair; it does not read, quote or use the Claude
reference labels themselves. The constitution stays unchanged.

## Side observations (not investigated)

- `zoo/models/scout-large/examples/*.txt`, the picket-forest examples and the sandbox examples are
  demo inputs for model cards and the website. They are not learning input, but their authorship
  was not checked. The owner may want to decide whether XI applies to inference demo inputs.
- `tests/fixtures/mini-corpus/` contains a guideline and an example used only by unit tests. No
  model learns from them.

## Open questions for the owner

All questions were answered on 2026-10-14 (see "Owner decision"). Rulings 2–4 are recorded in
`compliance/decisions.yaml` as `D-xi-teacher-labels-0.1.x`, `D-xi-rewrite-requirements` and
`D-xi-contested-input` (narrowed input, no constitution amendment).
