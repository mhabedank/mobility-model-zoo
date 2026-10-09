# Data model: Deduplication and clustering of JTBD items

Feature: [spec.md](spec.md) · Research: [research.md](research.md)

All files live outside git under the JTBD data directory (`data/cluster/…`, gitignored) or in a user's own map directory. Only configs, the guideline, the criteria and hash manifests are committed.

## Input

### Source line (`jtbd-cluster-input-v1`, one JSON object per line)

| Field | Type | Rule |
|---|---|---|
| `input_format_version` | `"jtbd-cluster-input-v1"` | required |
| `source_id` | string | required, unique in the bundle |
| `source_class` | string | required (for the zoo's corpus: the chunk's `source_type`) |
| `date` | ISO date or null | null means undated (FR-016) |
| `origin` | string or null | thread or URL path; independence key when set (R3) |
| `text_sha256` | hex or null | equal values collapse into one independence unit |
| `output` | object | an unchanged `jtbd-span-v1` document; any other version is refused (FR-001) |

## Map directory (state of one opportunity map)

```text
<map>/
├── result.json          # latest jtbd-cluster-v1 output
├── state.json           # id counters, previous membership, settings hash
├── corrections.yaml     # human structure edits (R14)
├── annotations.jsonl    # statements and assignments by node id (R15)
├── changes.json         # what the latest run changed (R13)
└── cache/embeddings/    # vectors by (model, revision, quote hash) (R6)
```

## Entities

### Item

| Field | Type | Rule |
|---|---|---|
| `item_id` | `it-` + 12 hex | SHA-256 over (source_id, start, end, kind) |
| `source_id`, `start`, `end` | string, int, int | from the input |
| `kind` | job, pain, gain | from scout |
| `quote` | string | byte-identical to scout's quote (FR-002) |
| `score` | number | from scout |
| `actor_type`, `evidence_type`, `evidence_scope` | enum or absent | present only if scout's `dimensions` list it |
| `date` | ISO date or null | from the source |
| `independence_key` | string | origin, else source_id; collapsed by text hash |
| `exact_copy_key` | hex | hash of kind + normalised quote (R4) |
| `group_id` | `dg-…` | exactly one (FR-003) |

### Duplicate group

| Field | Type | Rule |
|---|---|---|
| `group_id` | `dg-` + 6 digits | stable across runs (R13) |
| `kind` | job, pain, gain | all members share it (FR-004) |
| `members` | item ids | ≥ 1, sorted |
| `representative` | item id | a member; correction may set it (R14) |
| `parent` | `dg-…`, `cl-…` or null | a `dg-` parent has the same kind and is more general (FR-009) |
| `children` | group ids | more specific groups |
| `counts` | object | `mentions` (members), `independent_sources`, `independence_rule` (`origin`, `source_id`) |
| `distributions` | object | counts per value of actor_type, evidence_type, evidence_scope |
| `dates` | object | `first`, `last`, `undated` count |
| `statement` | object or null | from annotations; this feature never fills it (FR-014) |
| `assignments` | list | `{scheme, value, origin}` from annotations (FR-015) |
| `corrected` | bool | true if a correction touched it |

### Cluster

| Field | Type | Rule |
|---|---|---|
| `cluster_id` | `cl-` + 6 digits | stable across runs |
| `level` | int | 1 = finest cluster level |
| `parent` | `cl-…` or null | a coarser cluster |
| `children` | group or cluster ids | top-level groups of this cluster and finer clusters |
| `representative` | item id | from the items below |
| `counts`, `distributions`, `dates` | as for groups | aggregated over all items below |
| `kinds` | object | number of groups per kind below (FR-010) |
| `statement`, `assignments`, `corrected` | as for groups | |

The structure is a forest: every node has at most one parent, no cycles, every group reachable from at most one top-level node (FR-009, FR-026).

### Correction (`corrections.yaml`)

```yaml
- op: merge            # must-link
  items: [it-…, it-…]  # one item per group to merge
  note: "same need"
- op: split            # cannot-link between the listed sets
  sets: [[it-…], [it-…, it-…]]
- op: move             # pin a node (by one of its items) under a parent (by one of its items)
  item: it-…
  under: it-…          # or null for top level
- op: representative
  item: it-…
```

Every operation gets a status on each run: `applied`, `stale` (items missing) or `refused` (would mix kinds in a group or a specificity link). Moving a group of another kind into a cluster is allowed.

### Annotation (`annotations.jsonl`)

```json
{"node": "cl-000012", "statement": {"text": "…", "by": "person", "at": "2026-10-20"},
 "assignments": [{"scheme": "job-map-step", "value": "locate", "origin": "person"}]}
```

### Change report (`changes.json`)

Per run: `new`, `grown`, `shrunk`, `merged` (`into`, `from`), `split` (`from`, `into`), `removed`, `stale_corrections`, `refused_corrections`, `orphaned_annotations`, each listing ids.

## Benchmark and measurement

### Benchmark `cluster-v1` (`topics/productdev/benchmarks/cluster-v1/manifest.json`, hashes only)

- `hashes`: guideline, examples, prompt, wire schema, criteria, budget, pair list, set list, item pool.
- `pairs`: `pair_id`, `a`, `b` (item ids), `split` (`dev`, `test`, `holdout`), `stratum` (`high`, `middle`, `random`).
- `sets`: `set_id`, `items`, `split`.
- `state`: `draft` → `frozen` → `piloted` → `decided` (as the extraction benchmark).

### Reference label run (`data/cluster/runs/<run_id>/`)

Manifest like `LabelRunManifest` (role `reference`, backend, model version, settings, cost, excluded units), raw responses written once, parsed `pairs.jsonl` (`pair_id`, `label`) and `sets.jsonl` (`set_id`, `clusters`).

### Agreement and scores (`data/cluster/analysis/cluster-v1/`)

- `agreement.json`: per level the reference-vs-reference statistic with bootstrap CI, contested counts, decision (`go`, `revise`, `rethink`).
- `consensus.jsonl`: pairs both references agree on; `contested.jsonl`: the rest.
- `score-<candidate>.json`: per level pair precision, recall, F1; B-cubed precision, recall, F1; specificity F1; ratio to the reference-vs-reference value; deterministic check results; settings hash.
- `perf-<candidate>.json`: items, wall time, peak RSS, machine, origin (`real` or `scale-set`).

## State transitions

```text
benchmark: draft ──freeze──▶ frozen ──label refs──▶ piloted ──decide──▶ decided
                                   ▲                       │ revise (once, holdout)
                                   └───────────────────────┘

map run:   (no state) ──run──▶ result v1 ──run with new input / corrections──▶ result v2 …
```
