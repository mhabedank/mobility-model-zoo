# Task: machine-sound anomaly detection (`sound-anomaly`)

Model: `hum-fan` (int8 autoencoder on the `microinfer` engine).

## Scope

- **In:** an unsupervised anomaly score per 10 s clip from one microphone, trained on recordings of the machine in normal condition only.
- **Out:** fault classification (which part fails), remaining-useful-life estimates, multi-microphone setups, safety functions. The score supports maintenance planning; it does not decide whether a vehicle is safe to operate.

## Reference

Dataset labels (ground truth): the MIMII normal / abnormal folder of each clip (Purohit et al., Hitachi, CC BY-SA 4.0).

## Benchmark `mimii-fan-v1`

MIMII 6 dB SNR fan recordings, machines `id_00` and `id_02`. Per machine id, as many normal clips as abnormal clips are held out for testing (DCASE protocol); the remaining normal clips train the autoencoder, and a tenth of them (whole clips) is the validation set for the threshold. Frozen at first use (`condmon sound-anomaly freeze`).

The reported result is the int8 arithmetic on the bit-exact host reference; float results are informative only.

## Metrics

| Metric | Definition |
|---|---|
| **clip AUC** (headline) | ROC AUC of the clip score (mean squared reconstruction error of the int8 model, averaged over the windows of a clip) |
| pAUC | partial AUC for FPR ≤ 0.1, normalised to [0, 1] as in DCASE |
| per machine id | clip AUC for each machine id |
| window detection rate / FPR | at the window threshold, the 95th percentile of the validation normals (never tuned on the test set); used by the HIL test |

## Tool

`uv run condmon sound-anomaly train|evaluate|freeze`. Data and outputs live in `$MMZ_DATA`.

## Framework and why

**Keras + LiteRT (TFLite) int8**: a small dense autoencoder over 5 × 40 log-mel frames trains in minutes on a CPU, and full-integer quantisation runs on the `microinfer` engine bit-exactly with the TFLite interpreter. The log-mel front end is plain NumPy so the same features can be computed on a microcontroller.

## Mobility relevance and limits

Not every dataset comes from a vehicle; this one does not, so the reason it is in the zoo is stated here.

**Acoustic condition monitoring of auxiliary units.** Fans, pumps, valves and slide rails are exactly the components that wear out in vehicles and mobility infrastructure. Examples: battery and power-electronics cooling in electric vehicles (fans, coolant pumps), climate blowers, cooling of DC fast chargers, pumps and valves in rail vehicles, sliding doors in buses and trains. A microphone plus a microcontroller detects unusual sounds before the part fails. This is predictive maintenance for fleets and charging infrastructure without a cloud connection. The method needs only recordings in normal condition, which is the usual case in the field.

*Limit:* the recordings come from a factory hall, not from a vehicle. The model shows that the pipeline and the hardware work. For use on a specific unit it is retrained with own normal recordings.

## Riskiest assumption

Factory-hall fan recordings transfer to vehicle and charger auxiliaries. It is tested later with own recordings; until then it is stated as a limit in the model card.

## Hardware budget

At most **64 KB RAM** (audio window, log-mel features, model arena) and **256 KB flash**. Measured on the HIL bench with the origin of each measurement (real board, emulator, simulator).
