# Python API contract

Module `mobility_model_zoo.productdev.jtbd.cluster`. Needs the base install plus the `cluster` extra (research R18).

```python
from mobility_model_zoo.productdev.jtbd.cluster import ClusterStage, read_bundle

stage = ClusterStage.from_settings("configs/productdev/jtbd/cluster-baseline.yaml")
sources = read_bundle("bundle.jsonl")            # list of source lines, validated
result = stage.run(sources, map_dir="my-map")    # writes the map directory, returns the result
result["groups"][0]["representative"]            # an item id
```

- `ClusterStage.from_settings(path)`: loads pinned encoder and NLI model ids and revisions, thresholds, `k`, levels. Downloads models on first use; later runs work offline.
- `ClusterStage.run(sources, map_dir=None)`: without `map_dir`, a one-off run with no state, corrections or annotations; with `map_dir`, the full continuity behaviour (R13–R15). Returns a dict valid against [cluster-output.schema.json](cluster-output.schema.json).
- `read_bundle(path)`: validates every line against [cluster-input.schema.json](cluster-input.schema.json) and refuses other output format versions with `ValueError`.
- Deterministic for identical inputs, settings, corrections, annotations and embedding cache (FR-020).
