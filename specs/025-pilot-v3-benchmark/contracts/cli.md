# CLI contract: pilot-v3

Global options are as today: `jtbd --config <cfg> [--dry-run] …`. The config is `configs/productdev/jtbd/pilot-v3.yaml`, which has a `v3:` block.

| Exit | Meaning |
|---|---|
| 0 | ok |
| 1 | validation failed or the transition is not allowed |
| 2 | usage |
| 3 | a frozen input changed (chunks, package, schema, criteria or budget) |
| 4 | budget refused |
| 5 | crawl once refused |
| 6 | backend failure or model version change |
| 7 | Claude gate, or an unapproved package with Claude drafts |

## Package and labeling

| Command | Does | Notes |
|---|---|---|
| `jtbd guide assemble \| approve \| check` | as in PR #65; `assemble` also writes `instructions/pass{1,2,3}.md` | the owner runs `approve` |
| `jtbd label --role reference\|baseline --backend <b> --model <m> --split pilot\|holdout\|enriched\|full [--limit n] [--workers n]` | with a `v3:` config: three passes per chunk, writes raw and parsed files per pass, merges, locates quotes and pointers | order of checks: Claude gate, package check, role check, frozen check, sample lock, redaction, pre-send. `--split holdout` only in state `revise`; `--split full` only in `full_labeling` |

## Benchmark steps (`jtbd v3 …`)

| Command | Does | State change |
|---|---|---|
| `separation` | reverse check of every pool snapshot against training data | none; exit 1 on a hit |
| `sample --seed <n>` | draws pilot, holdout, enriched (100) and full per language | draft → draft (writes `samples.json`) |
| `extend-enriched` | extends the enriched sample once to 200 per language | allowed once, before `decide` |
| `freeze-criteria` | freezes the chunks, samples, package, schemas, instructions, criteria and budget; refuses criteria that differ from the brief | draft → criteria_frozen |
| `agree --step pilot\|extension\|holdout` | matching, all statistics, bootstrap, per language | none (writes `agreement.json`) |
| `decide` | applies the decision rule; writes outcomes, `absent_fields` and stops | pilot_labeled → decided, or → revise |
| `revise --rationale <text>` | records the single revision; requires a reassembled and re-approved package | revise → revise (package hashes updated) |
| `consensus` | consensus and contested entries per produced field and language on `full` | full_labeling → full_labeling |
| `freeze` | freezes the benchmark; refuses mock runs unless `test_fixture` | full_labeling → frozen |
| `score --run <run>` | scores a baseline against the consensus, per field and language, with intervals | none |
| `report` | renders `report.md` from the analysis files | none |
