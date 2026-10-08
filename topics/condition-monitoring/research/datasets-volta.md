# Training data (sound and IMU): selection, licences, hosting

Goal: realistic, openly licensed data for **several use cases from mobility and cyber security** that
we may also use commercially and, where allowed, mirror on the Hugging Face Hub.
This file covers the sound and IMU datasets of the volta branch dataset notes; the CAN datasets are
in [topics/security/research/datasets.md](../../security/research/datasets.md).
The data is **never in the repository**: `uv run zoo data download <id>` fetches it from the
original provider into `$MMZ_DATA` (default `~/.cache/mobility-model-zoo/datasets`) and
records origin, licence, retrieval time and SHA-256 in `SOURCE.json`.

> Not legal advice. The assessment is based on the licence statements of the providers
> (as of October 2026, checked automatically for Zenodo) and should be confirmed by your legal
> department before publication.

## Selected

| ID | Use case | Licence | commercial | HF mirror allowed | Size | Status |
|---|---|---|---|---|---|---|
| `uci-har` | IMU activity recognition (acceleration + gyro, 6 activities) | CC BY 4.0 | yes | yes (to be confirmed by the redistribution check of the dataset declaration) | 60 MB | **trained** (`pace-cnn`, formerly `har_cnn1d`) |
| `mimii` | anomaly detection on machine sounds (fans, pumps, valves; predictive maintenance) | CC BY-SA 4.0 | yes | yes, **share-alike** (to be confirmed by the redistribution check of the dataset declaration) | 10 GB per machine/SNR; we read only ~1150 clips (~2 GB) through HTTP range requests | **trained** (`hum-fan`, formerly `mimii_fan_ae`, weights under CC BY-SA 4.0) |

### Relation to mobility

Not every dataset comes from a vehicle. For the two where this is not
obvious, this section says why they are in the mobility zoo and where their limits are.

**`mimii`: acoustic condition monitoring of auxiliary units.** Fans, pumps, valves
and slide rails are exactly the components that wear out in vehicles and mobility infrastructure.
Examples: battery and power electronics cooling in electric vehicles (fans,
coolant pumps), air-conditioning blowers, cooling of DC fast chargers, pumps and valves in
rail vehicles, sliding doors in buses and trains. A microphone plus a microcontroller detects
deviating sounds before the part fails. This is predictive maintenance for fleets
and charging infrastructure without a cloud connection. The method only needs recordings in the
normal state, which is the usual case in the field.
*Limit:* the recordings come from a factory hall, not from a vehicle. The model
shows that the pipeline and the hardware hold up. For use on a specific unit we retrain
with our own normal recordings.

**`uci-har`: activity recognition from IMU data.** Acceleration and angular rate sensors
are in every smartphone, wearable, e-scooter and control unit. The model shows how
windows of 6-axis IMU data are classified on the microcontroller: walking,
stairs, sitting, standing, lying. This relates to mobility for pedestrians and micromobility
(e.g. fall detection), for multimodal trip detection and as a
first step towards manoeuvre or driving style recognition with the same architecture.
*Limit:* there are no vehicle classes (car, bus, bicycle), and the sensor was worn on the belt.
Recognising the mode of transport or manoeuvres needs different data with the same pipeline.

Licence check: `uv run zoo data verify` compares the licence that the provider declares **today**
(Zenodo API) with the registry. A licence change makes the workflow `datasets.yml`
(weekly `zoo data verify`, being added in feature 005) fail.

## Rejected

Not in focus (the licence would be fine): Speech Commands v0.02 (CC BY 4.0, keyword spotting).
The model `kws_dscnn` was only a TinyML benchmark reference without a mobility relation and has been removed.

| Dataset | Reason |
|---|---|
| DCASE 2021+ Task 2 / ToyADMOS2 | CC BY-NC-SA 4.0 (non-commercial) |
| DCASE 2020 Task 2 Dev (MIMII+ToyADMOS subsets) | Zenodo declares CC BY-NC-SA 4.0. Detected by the licence check (`hilbench data verify` on the volta branch, now `zoo data verify`), although the source data is CC BY-SA |
| driverBehaviorDataset (GitHub jair-jr) | no licence = all rights reserved |

The rejected CAN and GNSS datasets are listed in
[topics/security/research/datasets.md](../../security/research/datasets.md).

## May we host third-party data on Hugging Face?

| Licence | Mirroring allowed? | Conditions |
|---|---|---|
| CC BY 4.0 | **yes** | attribution (authors, title, licence link), note on changes; no additional restrictions (e.g. no gating that restricts the licence) |
| CC BY-SA 4.0 | **yes** | as CC BY; in addition, the mirror **and every derived version of the data** (e.g. precomputed features) must be under CC BY-SA 4.0 |
| CC BY-NC(-SA) | for commercial projects **no** | – |
| without licence / "on request" | **no** | – |

Under constitution 2.0.0 a dataset may only be published after its licence and terms have been
checked. The former `hilbench hub mirror-dataset` command is not part of the zoo; any publication
goes through the zoo release process ([docs/adding-a-model.md](../../../docs/adding-a-model.md)).
The mirror rules of the volta branch were: only datasets that the registry marks as
`hf_rehost: yes…`, files unchanged, and a dataset card with attribution, citation and licence.

**Models:** weights trained on CC BY data are published under
Apache-2.0 with attribution of the training data in the model card. For CC BY-SA data it is
disputed whether weights are an adaptation; as a precaution the model is then published under
`cc-by-sa-4.0` (on the volta branch `hilbench hub` set this; in the zoo it is set in the release
record).

## Workflow

```bash
uv run zoo data list                          # registry + rejected datasets
uv run zoo data verify                        # check licences at the provider
uv run zoo data download uci-har              # into $MMZ_DATA
uv run condmon activity train --download      # train, export int8, check bit-exactness -> $MMZ_DATA/derived/pace-cnn/
uv run condmon sound-anomaly train --download # same for hum-fan on MIMII
MMZ_EDGE_MODELS=$MMZ_DATA/derived/pace-cnn/pace-cnn.npz uv run edge run -b sim
                                              # HIL suite incl. accuracy on the device
```

Training needs `uv sync --extra edge --extra edge-train`.

**Large archives:** for `mimii` the downloader does not fetch the 10 GB zip, but reads
only the central directory through HTTP range requests and then each selected file with a
single range request (CRC-checked, parallel). The selection (glob + count, fixed seed)
is in the registry (`zip_members`) and is recorded in `SOURCE.json`.

Training runs locally, not in CI: the volta `train` workflow (`models/train-request.json`), which
committed model parameters and reports back to the branch, was not adopted. Trained files go to
staging with `zoo stage`, see [docs/adding-a-model.md](../../../docs/adding-a-model.md).
