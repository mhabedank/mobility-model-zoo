# Benchmarks of the security topic

Each folder holds one frozen benchmark: its manifest (capture names, splits, vehicles, attack families, frame and episode counts, content hashes, dataset versions) and the recorded resolutions of duplicate captures. No frame, payload or timestamp list is stored here; the data stays in `$MMZ_DATA`.

A frozen manifest never changes. Any change to captures, roles or protocol constants makes a new benchmark version (constitution IX).

| Benchmark | Task | Datasets | Frozen |
|---|---|---|---|
| `can-ids-v1` | `can-ids` ([task document](../tasks/can-ids.md)) | can-train-and-test v1 (Bitbucket commit `2d293b6`), ROAD (Zenodo 10462796) | 2026-10-09; `set_01/test_04` relabelled to Traverse (see `resolutions.yaml`) |
| `can-ids-v2` | `can-ids` | as `can-ids-v1` (`based_on` its manifest hash) | 2026-10-10; adds the calibration plan per vehicle and set (`calibration`) |
| `can-ids-v3` | `can-ids` | as `can-ids-v2` (`based_on` its manifest hash) | 2026-10-10; six captures moved to role `excluded`: their benign traffic does not come from the labelled vehicle (`excluded_reason` in the manifest) |

`uv run zoo data stats --kind benchmark` lists the counts, hashes and users of every version; `uv run zoo data diff can-ids-v2 can-ids-v3` shows what changed between two of them (feature 017).
