# Pre-zoo research result: not a benchmark result

**pace-cnn** (former name `har_cnn1d`). The JSON uses the former name and is kept unchanged as a historic record.

- **Model:** int8 1D-CNN over 2.56 s of accelerometer and gyroscope signals (9 x 128 at 50 Hz), six activity classes ([research-report.json](research-report.json)).
- **Dataset:** Human Activity Recognition Using Smartphones (UCI HAR, Reyes-Ortiz, Anguita et al., CC BY 4.0).
- **Protocol:** the official UCI HAR test split (2,947 windows); `float_accuracy` and `int8_accuracy` are accuracy against the dataset activity labels.

**Origin:** old repository `mhabedank/mobility-security-ml`, branch `claude/cool-volta-rqsgdx`, path `models/zoo/har_cnn1d.report.json`.

These numbers were not measured on a frozen zoo benchmark. They must not pass or fail a gate, set a threshold or appear in a zoo model card. The weights are not in the zoo; pace-cnn will be retrained and released through the zoo pipeline.
