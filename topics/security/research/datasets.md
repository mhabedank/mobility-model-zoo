# Training data (CAN bus and GNSS): selection, licences, hosting

This file comes from the dataset notes of the volta branch of mobility-security-ml (the CAN parts;
sound and IMU are in
[topics/condition-monitoring/research/datasets-volta.md](../../condition-monitoring/research/datasets-volta.md)).
For the wider dataset survey see [03-datasets.md](03-datasets.md) and
[notes/datasets.md](notes/datasets.md).

Goal: realistic, openly licensed data for **several use cases from mobility and cyber security** that
we may also use commercially and, where allowed, mirror on the Hugging Face Hub.
The data is **never in the repository**: `uv run zoo data download <id>` fetches it from the
original provider into `$MMZ_DATA` (default `~/.cache/mobility-model-zoo/datasets`) and
records origin, licence, retrieval time and SHA-256 in `SOURCE.json`.

> Not legal advice. The assessment is based on the licence statements of the providers
> (as of October 2026, checked automatically for Zenodo) and should be confirmed by your legal
> department before publication.

## Selected

| ID | Use case | Licence | commercial | HF mirror allowed | Size | Status |
|---|---|---|---|---|---|---|
| `road` | CAN bus intrusion detection (real vehicle, fuzzing, fabrication, masquerade) | CC BY 4.0 | yes | yes (to be confirmed by the redistribution check of the dataset declaration) | 560 MB | **trained** (`picket-mlp`, formerly `can_ids_road`) |
| `can-mirgu` | CAN IDS on a modern vehicle while driving | CC BY 4.0 | yes | yes (to be confirmed by the redistribution check of the dataset declaration) | 500 MB | **broken at the provider**: instead of the header and the start of the data, the UCI zip contains ~180 MB of zero bytes, not recoverable. The downloader refuses it with a reason; CAN IDS is covered by `road` |

Licence check: `uv run zoo data verify` compares the licence that the provider declares **today**
(Zenodo API) with the registry. A licence change makes the workflow `datasets.yml`
(weekly `zoo data verify`, being added in feature 005) fail.

## Rejected

| Dataset | Reason |
|---|---|
| SynCAN (ETAS) | non-commercial use only |
| HCRL Car-Hacking / OTIDS | download only after registration, no open redistribution licence |
| GNSS Interference & Spoofing (Mendeley) | CC BY-NC (non-commercial) |

GNSS spoofing: openly licensed data (FGI-SpoofRepo, Tuni2025, both CC BY 4.0)
are raw I/Q recordings. For MCU inference at the navigation solution level they would
first have to go through a software receiver; that is a separate
work step and therefore not yet in the zoo.

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
Apache-2.0 with attribution of the training data in the model card.

## Workflow

```bash
uv run zoo data list                          # registry + rejected datasets
uv run zoo data verify                        # check licences at the provider
uv run zoo data download road                 # into $MMZ_DATA
uv run security can-ids mlp train --download  # train picket-mlp, export int8, check bit-exactness -> $MMZ_DATA/derived/picket-mlp/
MMZ_EDGE_MODELS=$MMZ_DATA/derived/picket-mlp/picket-mlp.npz uv run edge run -b sim
                                              # HIL suite incl. accuracy on the device
```

Training needs `uv sync --extra edge --extra edge-train`. Training runs locally, not in CI: the
volta `train` workflow (`models/train-request.json`), which committed model parameters and reports
back to the branch, was not adopted. Trained files go to staging with `zoo stage`, see
[docs/adding-a-model.md](../../../docs/adding-a-model.md).

## Candidates: benign CAN traffic from many vehicles (noted 2026-10-09)

Benign traffic from many vehicles would let us measure false alarms per hour on vehicles a model has never seen, the weakest point of `picket-forest` ([06 – Competitive landscape](06-competitive-landscape.md)). Attacks can be injected synthetically for detection rates; the real attacks of can-train-and-test and ROAD stay the core benchmark. None of these is declared or downloaded yet; each needs a declaration in `topics/security/compliance/datasets.yaml` before use.

| Candidate | What it is | Licence / access | Notes |
|---|---|---|---|
| **commaCarSegments** (`commaai/commaCarSegments` on Hugging Face) | Raw CAN from the openpilot user fleet, "over 300 different production vehicles", USA and worldwide; segments of `rlog.zst` (openpilot cereal logs, read with openpilot's `LogReader`) | MIT on the dataset card [V, 2026-10-09; 18,641 downloads, updated 2026-01-16] | Bus behind the comma device (usually ADAS/camera bus, not always OBD). Logs also contain GPS and other sensors: use CAN messages only and drop everything else at ingest. Benign only. Likely the largest open source of multi-vehicle CAN traffic. |
| **PIVOT** (University of Memphis, NSF grants 2213733, 2213735, 2245323) | "Open community platform for sharing vehicle telematics data for research and innovation", aims at crowdsourced CAN datasets | Not checked; platform at pivot.cssec.memphis.edu | Poster 2023 [V]; content and terms of the shared data not yet reviewed |
| **DETROIT** (Pesé et al., University of Michigan, IEEE SECON 2022) | Open-source framework for vehicle data collection, translation and sharing; crowdsources translation tables by automated CAN reverse engineering | Framework open source; shared data not checked | Paper [V]; whether raw CAN logs are available is unknown |
| **AutoPi community library** | Users of the AutoPi telematics dongle share OBD PIDs per make, model and year | Shares PID definitions, not raw logs [U] | Useful for decoding, not as traffic data |
| **DIMO** (dimo.org; hardware first by AutoPi, later own devices) | Blockchain-based network: drivers plug in an OBD-II device, data is signed with an Ethereum key on the device, owners grant access and earn tokens | Developer API (GraphQL) to normalised, decoded signals (location, speed, battery, odometer, tyre pressure, trouble codes) with owner consent [U, vendor pages]; no open raw-CAN dataset found | Decoded signals at low rate, not raw frames with timing, so not usable for frame-level intrusion detection; access needs owner consent per vehicle. The community the owner remembered (dongles, anonymised data, distributed ledger) is very likely DIMO |
| **comma2k19** (`commaai/comma2k19`) | 33 h of driving, CAN plus IMU and GNSS, one vehicle model | MIT [V] | Already listed in [03 – Datasets](03-datasets.md); single vehicle |

PIVOT, DETROIT, the AutoPi library and DIMO are kept as later sources; for intrusion detection, which needs raw frames with timing, none of them looks usable today (owner's assessment, 2026-10-09).
