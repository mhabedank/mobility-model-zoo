# Pre-zoo research result: not a benchmark result

**picket-mlp** (former name `can_ids_road`). The JSON uses the former name and is kept unchanged as a historic record.

- **Model:** int8 MLP (32-64-32-2) on 32 per-frame CAN features, exported to TFLite ([research-report.json](research-report.json)).
- **Dataset:** ROAD, Real ORNL Automotive Dynamometer CAN Intrusion Dataset (Verma et al., CC BY 4.0), with fuzzing, fabrication and masquerade attacks.
- **Protocol:** attack captures whose name ends in `_2` and about one in four ambient captures (by name hash) held out as test set (2,202,096 frames); `float_accuracy` and `int8_accuracy` are accuracy against the dataset labels, `int8_precision`, `int8_recall`, `int8_f1` and `int8_false_positive_rate` are frame-level against the same labels.

**Origin:** old repository `mhabedank/mobility-security-ml`, branch `claude/cool-volta-rqsgdx`, path `models/zoo/can_ids_road.report.json`.

These numbers were not measured on a frozen zoo benchmark. They must not pass or fail a gate, set a threshold or appear in a zoo model card. The weights are not in the zoo; picket-mlp will be retrained and released through the zoo pipeline.
