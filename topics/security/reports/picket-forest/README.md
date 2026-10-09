# Pre-zoo research result: not a benchmark result

**picket-forest** (former name `can-ids-tiny`). The JSON files use the former name and are kept unchanged as a historic record.

- **Model:** 30-tree random forest (max depth 12) exported to C with emlearn, scoring each CAN frame, followed by a k-of-window alarm stage ([config.json](config.json)).
- **Dataset:** can-train-and-test (Lampe & Meng, doi:10.11583/DTU.24805533, CC BY 4.0), four vehicles `set_01` to `set_04`.
- **Protocol:** per vehicle, the four test splits (known/unknown vehicle x known/unknown attack), with and without the CAN ID feature; frame-level precision, recall, f1, fpr and auc_pr against the dataset labels, plus alarm-level episode_recall, median_latency_ms and false_alarms_per_hour ([protocol_results.json](protocol_results.json)).
- **QEMU checks:** [benchmarks/qemu-esp32.json](benchmarks/qemu-esp32.json) and [benchmarks/qemu-esp32s3.json](benchmarks/qemu-esp32s3.json) are functional checks of the C code in QEMU (score mismatches, detected frames, alarms, state bytes); QEMU latency is not representative.
- **Research card:** [research-card.md](research-card.md), the model card written in the old repository.

**Origin:** old repository `mhabedank/mobility-security-ml`, branch `claude/clever-goldberg-ygio83`, path `models/can-ids-tiny/results/` (`config.json`, `protocol_results.json`, `benchmarks/`).

These numbers were not measured on a frozen zoo benchmark. They must not pass or fail a gate, set a threshold or appear in a zoo model card. The weights are not in the zoo; picket-forest will be retrained and released through the zoo pipeline.
