# Contract: files in the picket-forest model repository

Added with 0.2.1 (and written by `release_export_v2.export()` for every later release), next to the
files of 0.2.0, which stay byte-identical.

## `examples/<file>.json`

Byte-identical copies of `zoo/models/picket-forest/examples/*.json` (format: gate
`TREE_EXAMPLE_FIELDS`: `source`, `generator`, `frames`, `expected_scores`, `expected_alarms`).
Only files whose `source` is `synthetic` or a dataset declared `redistribution: allowed` may be
published; today all three are synthetic (`examples/SOURCES.yaml`).

Gate: the staged `examples/` holds every registry example with the same sha256; a missing or
differing file fails the tree-file rule with the file name.

## `calibration_table.json` (format `picket-forest-table-v1`)

```json
{
  "format": "picket-forest-table-v1",
  "note": "synthetic calibration (picket-synth seed 7), 40000 frames",
  "seconds": 123.4,
  "bus_rate": 1234.5,
  "ids": [
    {"id": 256, "period_us": 10000, "window_us": 250000, "max_count": 27, "dlc": 8}
  ]
}
```

- `ids` sorted ascending by `id`; `period_us` is 0 when fewer than 5 benign frames were seen.
- `bus_rate` is the float32 value as a JSON number; `seconds` the benign seconds used.
- Equivalent to `picket_forest_table.h` of the same release: same ids, `period_us`, `window_us`,
  `max_count`, `dlc`, and `bus_rate` within float32.

Gate: `calibration_table.json` parses with `picket_forest.load_table`, and its entries equal the
entries parsed from the staged `picket_forest_table.h`; otherwise the tree-file rule fails.

## Unchanged files

`model.joblib`, `config.json`, `picket_forest_model.h`, `picket_forest_config.h`,
`picket_forest_table.h`, `c/*.c`, `c/*.h`, `sbom.cdx.json`: the sha256 of each in the 0.2.1 record
equals the one in the 0.2.0 record (checked in quickstart.md step 5).
