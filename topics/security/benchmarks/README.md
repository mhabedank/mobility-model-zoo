# Benchmarks of the security topic

Each folder holds one frozen benchmark: its manifest (capture names, splits, vehicles, attack families, frame and episode counts, content hashes, dataset versions) and the recorded resolutions of duplicate captures. No frame, payload or timestamp list is stored here; the data stays in `$MMZ_DATA`.

A frozen manifest never changes. Any change to captures, roles or protocol constants makes a new benchmark version (constitution IX).

| Benchmark | Task | Datasets | Frozen |
|---|---|---|---|
| `can-ids-v1` | `can-ids` ([task document](../tasks/can-ids.md)) | can-train-and-test v1 (Bitbucket commit `2d293b6`), ROAD (Zenodo 10462796) | 2026-10-09; `set_01/test_04` relabelled to Traverse (see `resolutions.yaml`) |
