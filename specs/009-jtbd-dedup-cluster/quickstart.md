# Quickstart: validation scenarios

Feature: [spec.md](spec.md) · Contracts: [contracts/cli.md](contracts/cli.md) · Data model: [data-model.md](data-model.md)

## Prerequisites

```bash
uv sync --extra jtbd --extra cluster
uv run jtbd doctor
```

Stored, redacted chunks and a span run of the released `scout-large` (feature 004) in the JTBD data directory. For hosted reference labeling: the approved routes and keys from [docs/credentials.md](../../docs/credentials.md).

## S1. Duplicates become groups (User Story 1, SC-001)

```bash
uv run jtbd cluster collect --run <span-run> --out data/cluster/bundles/sample.jsonl
uv run jtbd cluster run --input data/cluster/bundles/sample.jsonl --map data/cluster/maps/sample
uv run jtbd cluster check --map data/cluster/maps/sample
```

Expected: `check` exits 0; every input item is in exactly one group; quotes are byte-identical; no group mixes kinds; a fixture bundle with the same text under two source ids gives one independence unit; a German and an English paraphrase in the fixture land in one group.

## S2. Agreement pilot and baseline score (User Story 2, SC-002, SC-003)

```bash
uv run jtbd cluster bench build --config configs/productdev/jtbd/cluster-v1.yaml
uv run jtbd cluster freeze --config configs/productdev/jtbd/cluster-v1.yaml
uv run jtbd cluster label --model claude-reference --split test
uv run jtbd cluster label --model gpt-mini-reference --split test
uv run jtbd cluster agreement --split test
uv run jtbd cluster decide
uv run jtbd cluster tune --settings configs/productdev/jtbd/cluster-baseline.yaml --split dev
uv run jtbd cluster score --settings configs/productdev/jtbd/cluster-baseline.yaml
```

Expected: `agreement.json` lists kappa (duplicate, specificity) and B-cubed F1 (clusters) with CIs and a decision per level against the frozen criteria; contested pairs are counted separately; `tune --split test` is refused; `score-*.json` reports each level separately, named as agreement with the two reference models on `cluster-v1`, with the ratio to the reference-vs-reference value. Changing the guideline after freezing makes `label` exit 3.

## S3. Hierarchy with mixed kinds (User Story 3)

Run S1 on a fixture with a job, two of its pains, a gain, and a more specific variant of the job.

Expected: the specific job group is a child of the general job group; job, pains and gain share a cluster; the cluster's `kinds` shows all three kinds; `report` writes `tree.md` with the nesting and `needs.csv` with every group exactly once per kind.

## S4. Continue a map (User Story 4, SC-004)

```bash
uv run jtbd cluster correct --map data/cluster/maps/sample merge <it-a> <it-b>
uv run jtbd cluster correct --map data/cluster/maps/sample split <it-c> -- <it-d>
uv run jtbd cluster correct --map data/cluster/maps/sample move <it-e> --under <it-f>
uv run jtbd cluster run --input data/cluster/bundles/sample.jsonl data/cluster/bundles/more.jsonl \
    --map data/cluster/maps/sample
```

Expected: groups with unchanged members keep their ids (at least 95% after adding 10% new sources); all three corrections show `applied`; a correction naming removed items shows `stale`; merging a pain with a job shows `refused`; `changes.json` lists new, grown, merged and split nodes; running the same command twice gives byte-identical `result.json`.

## S5. Annotations survive (User Story 5)

```bash
uv run jtbd cluster annotate --map data/cluster/maps/sample --node <cl-id> \
    --statement "Minimise the time it takes to find a parking space" --by person \
    --assign job-map-step=locate
uv run jtbd cluster run --input data/cluster/bundles/sample.jsonl --map data/cluster/maps/sample
```

Expected: the cluster still carries the statement and the assignment with origin `person`; items without a source date are counted as undated.

## S6. Budget (SC-005)

On the reference VM (8 GB RAM, 4 vCPU, no GPU), models downloaded beforehand, network off:

```bash
uv run jtbd cluster perf --settings configs/productdev/jtbd/cluster-baseline.yaml
uv run jtbd cluster perf --settings configs/productdev/jtbd/cluster-baseline.yaml --scale 50000
```

Expected: the 50,000-item scale set finishes in ≤ 15 minutes with peak RSS ≤ 4 GB; the record states machine, item count and origin (`real` or `scale-set`).

## S7. Reader check (SC-006)

A person who did not build the stage gets `result.json`, `tree.md` and `needs.csv` from S3 and builds the opportunity layer of an Opportunity Solution Tree and a needs list with counts in under 30 minutes, without converting the format.
