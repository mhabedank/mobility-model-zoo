# Research: new model ideas for the zoo (2026-10-11)

A multi-source web research run (5 search angles, 23 sources fetched, 25 claims checked by three independent verifiers each, 2 refuted) on which new mobility models fit the zoo's data, licences and hardware. This file keeps the verified results that the proposed roadmap of [spec.md](spec.md) relies on. It is research, not a dataset declaration: every licence below is checked again in the model's own declaration (`topics/<topic>/compliance/datasets.yaml`) before training (constitution VI).

Confidence: **high** = all verifiers agreed and the primary source was read; **medium** = majority agreement, a single primary source or a preprint.

## New model ideas

### Transport mode from smartphone motion sensors (`mode-cnn`, working name) — medium

- **Task**: eight transport modes from accelerometer, gyroscope and magnetometer, without GNSS.
- **Reuse**: the `pace-cnn` pipeline plus a magnetometer channel (UCI HAR has none).
- **Data**: Sussex-Huawei Locomotion (SHL). One verifier read its licence as public domain with attribution (LICENSE.txt on IEEE DataPort); **to be confirmed** before training. A second option is the Zenodo dataset of Pervysheva et al. (record 17864507, CC BY 4.0, 409 tracks, 18 people, five EU countries, ten modes), but it holds GNSS RINEX features, not motion data, so it needs a new pipeline.
- **Reference results**: a biLSTM reaches about 95 % on SHL 2018 (arXiv 2310.11087, preprint). In the SHL challenges, the mean F1 of the top ten dropped to about 66.5 % for an unseen phone position (2019) and about 69.5 % for unseen users (2020). The in-distribution figure is an upper bound.
- **Edge of an open model**: an int8 model for the ESP32-S3 whose card reports results per unseen user and per phone position.
- **Rejected**: Collecty (Zagreb, eight modes including e-scooters) has no dataset licence (Kaggle: "Unknown", empty DataCite rights list); only the article is CC BY.

### Battery cell health on a microcontroller (`cell-soh`, working name) — high

- **Task**: capacity or state of health from discharge curves and pulse tests.
- **Data**: TU Berlin degradation dataset, DOI 10.14279/depositonce-17598, CC BY 4.0: 30 LG HE4 18650 cells aged at different temperatures, depths of discharge and mean states of charge, two more cells with FUDS driving profiles, capacity checks every ten full cycles.
- **Feasibility**: a CNN-LSTM with 8,961 parameters reaches a mean absolute error of 0.0434 on NASA PCoE data with held-out batteries, using 35 KB flash, 2.25 KB RAM and 3.9 to 6.3 ms per inference on an ST SPC58 (arXiv 2103.00201, co-authored by STMicroelectronics; the unit of the error is not stated clearly; not an ESP32).
- **Evaluation**: leave cells out by stress factor (unseen temperature or depth of discharge); latency on the board.
- **Risk**: laboratory cells, not fleet data; the card must say so.

### Road roughness from vehicle signals (`rough-road`, working name) — high

- **Task**: International Roughness Index, mean profile depth or rutting per road segment from more than 50 decoded vehicle signals plus acceleration and GPS.
- **Data**: LiRA-CD of DTU, DOI 10.11583/dtu.c.6659909, CC BY 4.0 (all three parts): Renault Zoe electric cars, reference measurements of the Danish road authority, about 230 km of distinct roads (the often quoted 1,796 km count repeated drives). Companion paper: Data in Brief 49:109426 (2023).
- **Evaluation**: spatially separate routes, not random splits.
- **Risk**: labels are matched by place, not time (car and reference drives on different days); GPS trajectories need a privacy review before any derived data is shared.
- **Rejected**: the RSC pothole dataset (IEEE DataPort) needs a subscription and names no licence.

### Bearing faults from vibration, rail context (`hum-bearing`, working name) — medium

- **Task**: four classes on a spherical roller bearing FAG 22205E1KC3: normal, outer race, inner race, rolling element.
- **Data**: UPM/CITEF (railway technology research group), Zenodo 8241764, CC BY 4.0, version 1 of 2023-08-12, labels in the file names; paper Mathematics 11(16):3498. The licence covers this record only.
- **Reuse**: the `hum-fan` signal processing (spectrogram, int8), as anomaly autoencoder or small classifier.
- **Risk**: small (15 files, apparently one speed, fault levels F0 to F4); test-bench data. Leave-run-out split by fault level and a card that states the limited transfer.

## Roadmap candidates checked

### GNSS jamming and spoofing — medium

- The best published results (attention models with early fusion of pseudorange data, 0.16 % error) come from self-simulated landing-approach data without a published dataset; the authors name the missing test on real data themselves (arXiv 2510.19890, preprint).
- Machine-learning detectors on real Jammertest data exist (a federated LSTM on Jammertest 2024, an isolation forest on u-blox F9P, a chi-square detector with code), but no trained models or weights are published.
- An open model with card, trained and tested on real Jammertest 2025 data, with false alarms per hour and unseen receivers, would be new. The Jammertest 2025 licence was **not checked**. The Aissou dataset replays simulated attacks and fits only as an additional benchmark.

### CAN intrusion detection (`picket-*`) — high

- Tiny models exist: TinyCNNCANNet (about 13,000 parameters, IEEE Access 2026) and an LSTM autoencoder on SynCAN (6,272 parameters, about 25 KB flash, about 4 KB RAM, 6 to 11 ms on an ST SPC58).
- Neither reports false alarms per hour or tests on unseen vehicles; the autoencoder reaches precision 0.86 and recall 0.81 over five attack types. The zoo's edge is honest evaluation and measured ESP32-S3 latency, not size.
- The Hugging Face bundle "Multi-CAN-Datasets" (Apache-2.0 tag) contains HCRL and CIC data of unclear origin licence: comparison benchmark at most, not training data.
- **Refuted** (0 of 3 verifiers): a 514-parameter CNN with 99.46 % on four CAN attacks. Do not cite.

## Not answered

No claim passed verification for: gaps and download counts on Hugging Face; language-model use cases (UN R155/R156 and ISO 21434 assistants, accident reports, customer feedback); concrete industry demand; GTFS delay prediction; EV charging demand and charger anomalies; manoeuvre recognition from comma2k19. All microcontroller figures come from ST SPC58, not ESP32.

## Open questions

- Licence of the Jammertest 2025 data, and whether models trained on it may be released for commercial use.
- Licence of SHL, read from the provider directly.
- Whether model weights inherit CC BY-SA obligations from their training data (affects `hum-fan`; the zoo treats them as share-alike, constitution VI).
- Size and latency of the SPC58 results when ported to the ESP32-S3 in int8.

## Sources

- arXiv 2310.11087 (FPbiLSTM, SHL) — https://arxiv.org/abs/2310.11087v1
- SHL challenge review, Frontiers in Computer Science 2021 — https://doi.org/10.3389/fcomp.2021.713719
- Collecty article — https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10425662/
- Pervysheva et al. dataset — https://zenodo.org/records/17864507
- TU Berlin cell degradation — https://depositonce.tu-berlin.de/items/7f5e44ac-7371-4d6e-9015-007beea1ffa1/full
- Tiny models on SPC58 — https://arxiv.org/pdf/2103.00201
- LiRA-CD — https://orbit.dtu.dk/en/datasets/live-road-assessment-custom-dataset-lira-cd/
- RSC — https://ieee-dataport.org/documents/rsc-dataset-smartphone-based-sensor-data-road-surface-condition-monitoring
- UPM/CITEF bearing data — https://zenodo.org/records/8241764
- GNSS spoofing with attention models — https://arxiv.org/html/2510.19890v1
- Multi-CAN-Datasets — https://huggingface.co/datasets/Thi-Thu-Huong/Multi-CAN-Datasets
