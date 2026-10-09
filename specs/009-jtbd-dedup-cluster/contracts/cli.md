# CLI contract: `jtbd cluster`

Sub-app of the JTBD tool (research R1). Global options of `jtbd` (`--config`) apply. Exit codes follow `jtbd`: 0 ok, 2 usage, 3 frozen artifact changed, 4 budget guard, 5 validation failed, 6 model version changed mid-run.

## Running the stage

| Command | Does |
|---|---|
| `jtbd cluster collect --run <span-run> --out <bundle.jsonl>` | Builds a `jtbd-cluster-input-v1` bundle from stored chunks and a span run (source id, class, date, origin from the snapshot). |
| `jtbd cluster run --input <bundle.jsonl>… --map <dir> [--settings <cluster-baseline.yaml>]` | Runs deduplication, specificity and clustering; applies corrections; merges annotations; writes `result.json`, `state.json`, `changes.json`. Refuses other input format versions (exit 5). Runs offline once the models are cached. |
| `jtbd cluster check --map <dir>` | Deterministic checks (FR-026): every item in exactly one group, quotes byte-identical to the bundle, no kind mixing in groups or specificity links, forest without cycles, counts consistent, schema valid. Exit 5 on any failure. |
| `jtbd cluster correct --map <dir> merge\|split\|move\|representative …` | Appends one operation to `corrections.yaml` (same as editing the file). |
| `jtbd cluster annotate --map <dir> --node <id> [--statement <text>] [--assign <scheme>=<value>] --by person\|model:<id>` | Appends to `annotations.jsonl`. |
| `jtbd cluster report --map <dir> [--out <dir>]` | Writes `tree.md` (Opportunity Solution Tree view) and `needs.csv` (groups by kind with mention and source counts) from `result.json`. |

## Building and measuring

| Command | Does |
|---|---|
| `jtbd cluster bench build --config cluster-v1.yaml` | Builds the item pool, the dev/test/holdout split by snapshot, stratified pairs and neighbourhood sets (R10). |
| `jtbd cluster freeze --config cluster-v1.yaml` | Freezes guideline, examples, prompt, wire schema, criteria, budget and benchmark lists into the manifest (hashes only). |
| `jtbd cluster label --model <reference-id> --split test\|holdout` | Labels pairs and sets with one reference model (R11): frozen hashes, budget guard, pre-send checks, approved routes, write-once raw responses, resumable. Only models with `role: reference` and `benchmark_labeler: true`. |
| `jtbd cluster agreement --split test\|holdout` | Reference-vs-reference statistics per level with CIs, consensus and contested sets. |
| `jtbd cluster decide` | Applies the frozen criteria (R12): go, revise or rethink per level. |
| `jtbd cluster tune --settings <file> --split dev` | Grid search of `t_dup`, `t_spec`, `t_nli` and cluster levels on development pairs and sets only; writes the chosen values into a new settings file with the grid recorded. Refuses `--split test`. |
| `jtbd cluster score --settings <file>` | Runs the stage on the test pool and scores it per level against the consensus; contested pairs reported separately and scored neutrally. |
| `jtbd cluster perf --settings <file> [--scale 50000]` | Child-process measurement of wall time and peak RSS on the current machine; `--scale` builds the scale set (R17). Records machine and origin. |
