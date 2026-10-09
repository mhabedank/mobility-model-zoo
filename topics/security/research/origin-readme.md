*README of the former repository mhabedank/mobility-security-ml, kept for reference.*

# mobility-security-ml

Machine learning models for **mobility and automotive security**. The focus is on
**TinyML**: the models should run on small microcontrollers such as ESP32-S3, STM32 or NXP S32K.
Finished models are published on **Hugging Face** under an organisation of their own.

> Status: **Phase 0, research.** There is no code yet. The results are under [`docs/research/`](README.md).

## What it is about

Vehicles and mobility devices have many ECUs, buses (CAN, CAN FD, LIN, automotive Ethernet) and
radio interfaces (keyless, GNSS, BLE, V2X). Many of these interfaces have no authentication.
Attacks can often only be detected via **anomalies in behaviour**, i.e. via timing,
sequences, physical plausibility or radio characteristics.

Detection should run directly on the device: cheap, with little energy, in real time and
without a cloud. This fits the architecture that UNECE R155 and AUTOSAR IdsM envisage:
security sensor → IdsM / Security Event Memory → vehicle SOC.

## Documentation

| Document | Content |
|---|---|
| [Research overview](README.md) | Executive summary and entry point |
| [01 – Threat landscape](01-threat-landscape.md) | Which security problems can TinyML address? |
| [02 – Literature](02-literature.md) | Important papers, MCU deployments, pitfalls |
| [03 – Datasets](03-datasets.md) | Public data, licences, suitability for Hugging Face |
| [04 – Hardware](04-hardware.md) | Processors and boards, CAN connection, lab setup |
| [05 – Toolchain & publishing](05-toolchain-and-publishing.md) | Training → quantisation → MCU → Hugging Face |
| [Roadmap](../roadmap.md) | Low-hanging fruits, order of the models, open decisions |

## Licence

The code is under [Apache-2.0](../../../LICENSE). Trained models may be subject to other
licences depending on the training data. See [Datasets → Licences](03-datasets.md#licences-what-may-we-publish).
