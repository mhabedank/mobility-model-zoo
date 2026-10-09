# Pre-zoo research result: not a benchmark result

**hum-fan** (former name `mimii_fan_ae`). The JSON uses the former name and is kept unchanged as a historic record.

- **Model:** int8 dense autoencoder (5 x 40 log-mel frames, 64-64-8-64-64) trained on normal sounds; the anomaly score is the reconstruction MSE averaged over a 10 s clip ([research-report.json](research-report.json)).
- **Dataset:** MIMII fan recordings at 6 dB SNR (Purohit et al., Hitachi, CC BY-SA 4.0), machine ids 00 and 02.
- **Protocol:** per machine id, as many normal clips as abnormal clips held out for testing (DCASE-style, 700 clips, 27,300 windows); `float_auc`, `int8_auc` and `int8_pauc` (max FPR 0.1) are clip-level ROC AUC against the dataset normal/anomaly labels, `int8_window_*` are per-window metrics with a threshold from validation normals, `int8_auc_id_00` and `int8_auc_id_02` are per machine id.

**Origin:** old repository `mhabedank/mobility-security-ml`, branch `claude/cool-volta-rqsgdx`, path `models/zoo/mimii_fan_ae.report.json`.

These numbers were not measured on a frozen zoo benchmark. They must not pass or fail a gate, set a threshold or appear in a zoo model card. The weights are not in the zoo; hum-fan will be retrained and released through the zoo pipeline.
