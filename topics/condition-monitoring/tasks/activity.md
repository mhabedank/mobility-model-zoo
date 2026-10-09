# Task: activity recognition from IMU windows (`activity`)

Model: `pace-cnn` (int8 1D-CNN on the `microinfer` engine).

## Scope

- **In:** one of six activities (walking, walking upstairs, walking downstairs, sitting, standing, lying) from a 2.56 s window of a waist-worn 6-axis IMU (accelerometer and gyroscope, 50 Hz; 9 channels including total acceleration).
- **Out:** vehicle or transport-mode classes (car, bus, bicycle), fall detection as a safety function, identification of persons.

## Reference

Dataset labels (ground truth) of UCI HAR (Reyes-Ortiz, Anguita, Ghio, Oneto, Parra; CC BY 4.0).

## Benchmark `uci-har-v1`

The official UCI HAR split: the test set is 30 % of the subjects, unseen in training. A seventh of the training windows is the validation set. Frozen at first use (`condmon activity freeze`).

The reported result is the int8 arithmetic on the bit-exact host reference; float results are informative only.

## Metrics

| Metric | Definition |
|---|---|
| accuracy | share of test windows whose int8 prediction equals the dataset label |
| **macro-F1** (headline, with accuracy) | mean of the per-class F1 scores, so rare classes count as much as frequent ones |

## Tool

`uv run condmon activity train|evaluate|freeze`. Data and outputs live in `$MMZ_DATA`.

## Framework and why

**Keras + LiteRT (TFLite) int8**: three small convolution blocks over the time axis are a common, well-understood baseline for IMU windows, and full-integer quantisation runs on the `microinfer` engine bit-exactly with the TFLite interpreter.

## Mobility relevance and limits

Accelerometers and gyroscopes are in every smartphone, wearable, e-scooter and control unit. The model shows how windows of 6-axis IMU data are classified on a microcontroller. This matters for pedestrians and micromobility, for multimodal trip detection, and as a first step towards manoeuvre or driving-style recognition with the same architecture.

*Limit:* there are no vehicle classes, and the sensor was worn on the belt. Transport-mode or manoeuvre recognition needs other data with the same pipeline.

## Riskiest assumption

Waist-worn activity windows are a useful base for micromobility and manoeuvre detection. Until other data tests it, it is stated as a limit in the model card.

## Hardware budget

At most **32 KB RAM** and **128 KB flash**. Measured on the HIL bench with the origin of each measurement (real board, emulator, simulator).
