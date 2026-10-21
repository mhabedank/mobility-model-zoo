# Task: activity recognition from IMU windows (`activity`)

Model: `pace-cnn` (int8 1D-CNN on the `microinfer` engine).

## Scope

- **In:** one of six activities (walking, walking upstairs, walking downstairs, sitting, standing, lying) from a 2.56 s window of a waist-worn 6-axis IMU (accelerometer and gyroscope, 50 Hz; 9 channels including total acceleration).
- **Out:** vehicle or transport-mode classes (car, bus, bicycle), fall detection as a safety function, identification of persons.

## Reference

Dataset labels (ground truth) of UCI HAR (Reyes-Ortiz, Anguita, Ghio, Oneto, Parra; CC BY 4.0).

## Benchmark `uci-har-v1`

- **Test split**: the official UCI HAR test set, 9 of the 30 subjects (2,947 windows), never seen in training.
- **Validation split**: 3 of the 21 training subjects, drawn once by whole subject with `validation_seed` 2026. Windows overlap by 50 %, so a validation set drawn by window would hold near-copies of training windows.
- **Normalisation**: per channel, mean and std of the 18 remaining training subjects; validation is excluded.
- **Manifest**: `condmon activity freeze` writes `topics/condition-monitoring/benchmarks/uci-har-v1/manifest.json`. It records subject counts, window counts and SHA-256 values of the subject lists and of each split's data, never subject numbers. A frozen manifest never changes; a new definition is `uci-har-v2`.
- **Use of the test subjects**: never for training, early stopping, thresholds or any choice. Each model file of a pre-registered run is evaluated on them by one fixed procedure.

The reported result is the int8 arithmetic on the bit-exact host reference; float results are informative only.

## Metrics

All metrics are measured against the UCI HAR dataset labels.

| Metric | Definition |
|---|---|
| accuracy | share of test windows whose int8 prediction equals the dataset label |
| **macro-F1** (headline, with accuracy) | mean of the per-class F1 scores, so rare classes count as much as frequent ones |
| per-class F1 | F1 of each of the six classes; the lowest is `int8_f1_min_class` |
| worst test subject, subject range | macro-F1 per test subject, reported by rank only (lowest, and highest minus lowest) |
| seed spread | minimum, mean and maximum macro-F1 over the five pre-registered seeds |
| interpreter mismatches | test windows on which the int8 host reference and the TFLite reference interpreter disagree (deterministic check, must be 0) |

## Pre-registration

Success and kill criteria, seeds, the selection rule and the budgets are fixed in [`configs/condition-monitoring/activity/pace-cnn-criteria.yaml`](../../../configs/condition-monitoring/activity/pace-cnn-criteria.yaml) before the first training run. `condmon activity train` refuses to run if that file is untracked or modified.

## Tool

`uv run condmon activity freeze|train|evaluate|reproduce|export`. Data and run outputs live in `$MMZ_DATA`; the manifest and the evaluation report live in this topic folder.

## Framework and why

**Keras + LiteRT (TFLite) int8**: three small convolution blocks over the time axis are a common, well-understood baseline for IMU windows, and full-integer quantisation runs on the `microinfer` engine bit-exactly with the TFLite interpreter.

## Mobility relevance and limits

Accelerometers and gyroscopes are in every smartphone, wearable, e-scooter and control unit. The model shows how windows of 6-axis IMU data are classified on a microcontroller. This matters for pedestrians and micromobility, for multimodal trip detection, and as a first step towards manoeuvre or driving-style recognition with the same architecture.

*Limit:* there are no vehicle classes, and the sensor was worn on the belt. Transport-mode or manoeuvre recognition needs other data with the same pipeline.

## Riskiest assumption

Waist-worn activity windows are a useful base for micromobility and manoeuvre detection. Until other data tests it, it is stated as a limit in the model card.

## Hardware budget

Reference hardware: **ESP32 classic** on the HIL bench (`esp32-1`, LilyGO LoRa32, dual core, 240 MHz).

- At most **128 KB flash** and **32 KB RAM** for the model including its working memory (weights, int8 engine code, arena, input and output buffers).
- At most **100 ms** average inference time per 2.56 s window on the reference board.

Every measurement records its origin: real board, emulator or simulator. Emulator and simulator results are informative and never replace the reference board. Other boards (ESP8266, the ESP32 emulator, the host build) are measured as informative results.
