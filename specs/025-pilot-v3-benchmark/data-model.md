# Data model: Benchmark pilot-v3

All files are written by code. Paths are relative to the repository root.

## Guideline package (read only)

`topics/productdev/guideline/scout-v3/package/` contains:

- `guideline.md`
- `examples/NN-<id>.yaml`
- `instructions/pass1.md`, `instructions/pass2.md` and `instructions/pass3.md` (new, see research R2)
- `package.json`
- `approval.json`

Rule: every v3 run calls `guideline_package.require_for_run`. A changed package gives exit 3; an unapproved package that contains Claude drafts gives exit 7.

## Labeler pass answers (`contracts/labeler-pass{1,2,3}.schema.json`)

| Pass | Shape | Validation added by code |
|---|---|---|
| 1 | `{relevant, items: [{kind, quote, actor_type, evidence_type, evidence_scope}]}` | `relevant` is false exactly when `items` is empty; every quote is located verbatim with the existing quote rule (`quotes.locate`); quotes do not overlap |
| 2 | `{items: [{index, job_kind, mode[], improve[], states_solution, executor_role, situation}]}` | `index` refers to a pass-1 item; `job_kind` is set only when kind is job; `states_solution` is true only on gains; a pointer that is not a verbatim part of the chunk is set to null and counted |
| 3 | `{links: [{from, to, relation}]}` | indices exist; `causes` joins different actors and at least one pain; `in_order_to` joins items of the same actor; `during` is written with the earlier item first. A link that breaks a rule is dropped and counted |

## Labeler output v3 (merged per chunk)

`data/pilot-v3/runs/<run>/parsed/<chunk>.json` holds the merged answer in the shape of `jtbd-span-v2` without `score`:

- `language`, detected by code;
- `relevant`;
- `items[]` with `start` and `end` and pointer offsets;
- `links[]`;
- `invalid` counts per field;
- `passes`: the attempt number and model version of each pass.

## Pass record

`data/pilot-v3/runs/<run>/raw/<chunk>.p<pass>.a<attempt>.json` holds the raw body, usage, model version and parsed candidate. It is written exclusively and never overwritten.

## Run manifest

This is the existing `LabelRunManifest`, extended through `RunSettings` (which allows extra keys) with:

- `passes: [1, 2, 3]`;
- `instructions_sha256` per pass;
- `labeler_schema_sha256` per pass;
- `package_manifest_sha256`.

The gate fields are unchanged.

## Chunk pool and samples

- **Pool:** `data/pilot-v3/chunks/<id>.json` uses the existing `Chunk` model. Each chunk has its source snapshot, `language`, redaction status and `source_class` (`pilot-v2-text` or `new-benchmark-source`).
- **Samples:** `topics/productdev/benchmarks-v3/pilot-v3/samples.json` holds, per language:
  - `pilot`: 100 chunk ids;
  - `holdout`: 100, locked;
  - `enriched`: 100, extended at most once to 200, with the connective that drew each chunk;
  - `full`: the rest;
  - `seed`.

  The sets are disjoint per language.

## Criteria

`configs/productdev/jtbd/criteria-pilot-v3.yaml` is a verbatim copy of the brief's `pilot_thresholds`, plus:

- `bootstrap`: resamples 2,000 and a seed;
- `role_words`: the approximation of R10.

The freeze refuses the file if it differs from the brief's `pilot_thresholds`, apart from those two keys.

## Benchmark manifest (`contracts/benchmark-manifest-v3.md`)

`topics/productdev/benchmarks-v3/pilot-v3/manifest.json` holds:

- `state`;
- `frozen_at`;
- the chunk ids and text sha256;
- the samples sha256;
- the package manifest and approval sha256;
- the labeler schema sha256 per pass;
- the instructions sha256 per pass;
- the criteria sha256;
- the budget sha256;
- the reference run ids per step;
- the outcomes per field and language;
- `absent_fields` per language;
- `revisions` (at most one).

State transitions:

```
draft ─freeze-criteria→ criteria_frozen ─label pilot (both refs)→ pilot_labeled
pilot_labeled ─decide→ decided ──(any revise and no revision yet)──→ revise
revise ─owner re-approves package, holdout labeled, decide→ decided (revision recorded)
decided ─(core passed in a language)→ full_labeling ─consensus, freeze→ frozen
decided ─(keep-always stop in a language)→ stopped[lang]   (the other language may continue)
```

A transition that the table does not allow is refused with exit 1, and a changed frozen input with exit 3.

## Agreement report

`data/pilot-v3/analysis/<step>/agreement.json`, per language and field, holds:

- `estimate`, `ci_low`, `ci_high`, `units`;
- `outcome`;
- `step` (pilot, extension or holdout);
- the figures in `reported_only`.

Also included:

- link prevalence from the random pilot;
- invalid-pointer counts;
- excluded chunks per pass;
- the cost per run.

A rendered `report.md` sits next to it.

## Consensus and contested entries (full benchmark)

`data/pilot-v3/analysis/full/consensus.jsonl` and `contested.jsonl`, per language and per produced field, cover:

- relevance;
- matched items, with their agreed attributes and pointers and a union span;
- links between matched items.

Entries that disagree are kept as contested with the field name. Fields that are not produced are omitted and listed in `absent_fields`.
