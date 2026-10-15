# Data Model: Transparency over training data, benchmarks and training runs

**Feature**: 017 | **Spec**: [spec.md](spec.md) | **Research**: [research.md](research.md)

Every entity here is **derived**. The repository registers, frozen manifests, freeze files and release records stay the source of truth (spec decision 3). The overview computes these entities on each call. The tracking store holds copies of the numbers, never the data.

## InventoryRow

One row of the overview (FR-001, FR-002). It is one version of one dataset, source collection, training set or benchmark.

| Field | Type | Source | Notes |
|---|---|---|---|
| `kind` | enum `dataset`, `source-collection`, `training-set`, `benchmark` | collector | |
| `topic` | string | register path or manifest folder | `productdev`, `security`, `condition-monitoring` |
| `id` | string | register `id`, benchmark family, training set name | e.g. `can-train-and-test`, `can-ids`, `span-train` |
| `version` | string | benchmark folder (`can-ids-v3`), freeze file (`span-train-v1`), `SOURCE.json` `retrieved_at` date for datasets | A dataset's version is its retrieval date. A dataset that is not downloaded on this machine has version `register`. |
| `status` | enum `active`, `rejected`, `broken_at_source`, `frozen`, `decided`, `building` | register `status`, manifest `state` | |
| `licence` | string or null | register `licence`, manifest `datasets[].licence` | |
| `permitted_use` | enum `training_allowed`, `benchmark_only`, null | register | Benchmarks inherit the strictest permitted use of their datasets. |
| `redistribution` | string or null | register | |
| `size_mb` | number or null | measured walk of `$MMZ_DATA/<id>/`, else null | |
| `approx_size_mb` | number or null | register `approx_size_mb` | Shown when `size_mb` is null. |
| `files` | int or null | measured | |
| `counts` | map dimension → int | see [Counts by kind](#counts-by-kind) | e.g. `chunks`, `rows`, `captures`, `frames`, `episodes`, `items` |
| `distribution` | map dimension → map value → int | see [Counts by kind](#counts-by-kind) | e.g. `attack_family`, `role`, `split`, `vehicle`, `language` |
| `frozen_at` | date or null | manifest `frozen_at`, freeze file `frozen_at` | |
| `sha256` | 64-hex or null | [Hashes](#hashes) | |
| `last_change` | date or null | git: last commit touching the record or manifest | null outside git or in a shallow clone |
| `lineage` | list of `{relation: supersedes, based_on, built_from; target: <id@version>; sha256?}` | manifest `supersedes`, `based_on`, training set `dataset` | |
| `used_by` | list of `<model>@<version>` or model names | register `used_by`; release records `evaluation.benchmark`; span config | |
| `availability` | enum `measured`, `register-only`, `partial`, `error` | collector | `register-only`: data is not downloaded on this machine (FR-003). |
| `integrity` | enum `ok`, `mismatch`, `unchecked`, `changed-after-freeze` | [Integrity](#integrity) | `mismatch` and `changed-after-freeze` are errors (FR-007). |
| `notes` | list of short strings | collector | e.g. "no label distribution stored in this manifest" |

**Validation**:
- `(kind, id, version)` is unique.
- `sha256` is null only when `availability` is `register-only` and the hash needs data.
- `counts` values are ≥ 0.
- No field holds dataset content. Counts and hashes only (FR-008).

### Counts by kind

| Kind / reader | `counts` | `distribution` |
|---|---|---|
| dataset | `files` | none |
| source-collection (productdev `sources.yaml`) | `sources`, `snapshots` (when `data/snapshots` exists) | `source_class`, `licence`, `permitted_use` |
| benchmark, jtbd pilot | `chunks`, `holdout_chunks`, `train_chunks` | none (the manifest stores none) |
| benchmark, jtbd cluster | `items`, `snapshots`, `pairs`, `sets`, each also per split; `excluded_items`, `excluded_snapshots` | `split` for items, snapshots, pairs by level |
| benchmark, can-ids | `captures`, `frames`, `attack_frames`, `episodes`, `duration_s` | `role`, `split`, `set`, `vehicle`, `dataset`, `attack_family` (capture counts; frames per role) |
| training-set, span | `chunks`, `rows`, `rows_train`, `rows_val`, `relevant_rows`, `items_kept`, `items_dropped` | `language`, `source_type`, `sub_area` (from `rows.stats.json` `composition`) |

### Hashes

| Kind | Hash |
|---|---|
| dataset | sha256 over sorted `name:sha256` lines of `SOURCE.json` `files[]`; for zip-member files `name:checksum` |
| source-collection | sha256 of the canonical `sources.yaml` record list (`freeze.sha256_canonical`) |
| benchmark | `sha256(json.dumps(manifest, sort_keys=True))`, the formula already used by `based_on.manifest_sha256` and run records |
| training-set | `frozen.json` `sha256` (chunks plus rows) |

### Integrity

- **Always checked**: every `based_on.manifest_sha256` equals the parent's current hash. A frozen manifest has no commits after the one that froze it, except the revisions it records itself.
- **With `--verify` and data present**: the existing content verifiers run (jtbd `verify_frozen`, cluster `bench.verify`, can-ids `verify_captures`).

## HistoryEvent

One entry of `zoo data history` (FR-005).

| Field | Type | Notes |
|---|---|---|
| `date` | date | commit date or manifest event date |
| `commit` | 40-hex or null | null for events recorded only inside a manifest |
| `subject` | `<kind>:<id>@<version>` | |
| `event` | enum `registered`, `field-changed`, `frozen`, `superseded`, `revised`, `excluded`, `retrieved` | |
| `field` | string or null | e.g. `permitted_use`, `licence`, `approx_size_mb` |
| `old`, `new` | scalar or null | register values only; never content |

## VersionDiff

The result of `zoo data diff A B` (FR-006). Both sides must have the same `kind` and family.

| Field | Type |
|---|---|
| `a`, `b` | `<id>@<version>` |
| `counts` | map dimension → `{a, b, delta}` |
| `distribution` | map dimension → value → `{a, b, delta}` |
| `members` | `{added: [...], removed: [...], changed: [...]}` of member ids (capture ids, chunk ids, record ids) with their hashes, no content |
| `hashes` | `{a, b}` |
| `protocol` | changed keys of `protocol` or `hashes` blocks with old and new values |

## TrackingRun (in the tracking store)

The wrapper's view of an MLflow run. Keys and allowed values are in [contracts/tracking.md](contracts/tracking.md).

| Field | Notes |
|---|---|
| `experiment` | `datasets`, `<topic>/<task>` (e.g. `productdev/jtbd-span`, `security/can-ids`, `condition-monitoring/sound-anomaly`, `edge/hil-bench`) or `spikes` |
| `run_name` | `<id>@<version>` for data runs, `<model-or-candidate>-<short commit>` for runs |
| `status` | MLflow status: `RUNNING`, `FINISHED`, `FAILED`, `KILLED` |
| `tags` | `mmz.*` allow-list: kind, task, topic, git commit, clean tree, hardware, benchmark, training set, model, model version, imported, import key, spike, superseded_by |
| `params` | flattened committed config values (guarded, R8) |
| `metrics` | per step (epoch or eval step) and final; data runs: sizes, counts, distributions |
| `inputs` | `Dataset(name=<id>@<version>, digest=<sha256[:16]>, source_type=zoo, source=<repo path>, profile=<aggregate JSON>)` with context `training`, `evaluation` or `inventory` |
| `artifacts` | allow-listed aggregate files only (R8), no weights |

**State transitions**:
- A run starts as `RUNNING`.
- It ends as `FINISHED` when the command succeeds, `FAILED` on an exception, and `KILLED` on an interrupt.
- A degraded run (server lost mid-run) keeps whatever state the server last saw. Its local `tracking.json` records `complete: false` (FR-020).

**Data run lifecycle** (idempotent publish, FR-015). The key is `(mmz.id, mmz.version)`:
- not present → created
- same `mmz.sha256` → metrics updated
- new `mmz.sha256` → new run, old run tagged `mmz.superseded_by=<new run id>`
- version `register` (no hash) → updated in place while it stays register-only. When a run with a real version of the same id is created, the `register` run is tagged `mmz.superseded_by`.

## TrackingSidecar (`tracking.json`)

Written next to a run's own outputs when tracking was attempted.

| Field | Type |
|---|---|
| `tracking_uri_host` | string (host and port only, no credentials) |
| `experiment` | string |
| `run_id` | 32-hex or null |
| `complete` | bool |
| `dropped` | int (values refused by the guard or lost to the circuit breaker) |
| `warnings` | list of short strings |

## ReleaseRecord.tracking (optional)

| Field | Type | Rule |
|---|---|---|
| `run_id` | string `^[0-9a-f]{32}$` | form checked by gate rule 1 (schema) |
| `experiment` | string `^[a-z0-9_./-]{1,120}$` | |

The object is optional. Records without it stay valid (FR-022).

## Relationships

```text
Dataset (register) ──built_from──▶ Training set ──used_by──▶ Run (training) ──produces──▶ Model version
      │                                                                                       │
      └──draws_on──▶ Benchmark ──based_on/supersedes──▶ Benchmark       Run (evaluation) ◀──evaluated_on
                         ▲                                                    │
                         └──────────────── measured_on ───────────────────────┘
Release record ──tracking.run_id──▶ Run (optional)
```
