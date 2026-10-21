# Release files: pace-cnn 0.1.0

The upload folder written by `condmon activity export` and staged by `zoo stage pace-cnn 0.1.0 --from DIR`. Allow-list: nothing else may be in it. Rule 11 of the release gate and `forbidden_upload` in `zoo stage` refuse `*.eval.npz`, `data/`, `.jsonl`, `.env`, `README.md` and `build.json` independently.

| Path | Content | Why |
|---|---|---|
| `pace-cnn.npz` | int8 QModel (`mmz-qmodel/1`), synthetic `test_inputs` | the int8 gate needs an `.npz` in `files[]`; the host example loads it |
| `pace-cnn.tflite` | full-int8 flatbuffer | for users of other int8 runtimes; same weights |
| `config.json` | labels, input contract, normalisation, quantisation, preparation steps | lets users prepare inputs (FR-021) |
| `c/pace_cnn_model.c`, `c/pace_cnn_model.h` | pace-cnn's generated model source alone | device use without the bench firmware (US2) |
| `c/microinfer.c`, `c/microinfer.h` | the int8 engine, copied from `firmware/bench/lib/microinfer/src/` | needed to call `mi_invoke` |
| `examples/example-1.json` … `example-3.json` (at least three) | synthetic inputs with expected int8 scores | rule 13; bit-exact check on host and board |
| `sbom.cdx.json` | CycloneDX SBOM of the shipped sources | compliance C-G (firmware SBOM for mcu) |

Never in the folder:

- dataset windows of any kind, including `pace-cnn.eval.npz`;
- subject numbers;
- run reports with local paths;
- the evaluation report, which stays in the repository under `topics/condition-monitoring/reports/pace-cnn/0.1.0/` and is linked from the card.

Licence: the shipped sources and weights are under Apache-2.0 (usage class `commercial`, derived from UCI HAR CC BY 4.0). The UCI HAR attribution appears in the card section "Training data and attribution" and in the repository-level `THIRD_PARTY_NOTICES.md`, both rendered by the compliance harness from the declaration's `attribution_text` once `used_by` names `pace-cnn@0.1.0` (research R13).
