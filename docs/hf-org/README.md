---
title: README
emoji: 🚏
colorFrom: blue
colorTo: green
sdk: static
pinned: false
---

# Mobility Model Zoo

Small, fast machine learning models for mobility in the broad sense: from product development and data analysis to vehicles, IoT and embedded systems. Every model runs locally, from a laptop down to a microcontroller, is versioned, and ships with a model card that says what it does, how good it is and measured against what, how fast it is on which hardware, and where it fails.

Website with quickstarts, interface documentation and worked examples: [mhabedank.github.io/mobility-model-zoo](https://mhabedank.github.io/mobility-model-zoo/)

## Topics

| Topic | What it covers |
|-------|----------------|
| **Product development** (`productdev`) | Product discovery in mobility. First task: extracting jobs-to-be-done, pains and gains with verbatim evidence from interviews, reviews and forum posts (German and English). |

More topics follow as separate collections, for example automotive security with tiny models on embedded hardware. Existing models do not change when a topic is added.

## How we publish

- **Measured, not claimed.** Every model is scored on a frozen benchmark with a fixed harness, and the card reports quality, speed on named hardware and known failure modes.
- **Immutable versions.** Each release is one tagged version (`v0.1.0`, …) and is never overwritten. Older versions stay available.
- **Open method, closed data.** Models, methods, prompts and evaluation results are published. Datasets and source texts are not, because they contain text written by people who did not agree to its redistribution.
- **Names stay.** Models are named `<name>-<variant>`, for example `scout-large`; topic and task are tags, and the name never changes after the first release.
- **Compliance.** Sources and their licences are credited in every card; how texts are collected and processed, and how to object: [privacy notice](https://github.com/mhabedank/mobility-model-zoo/blob/main/PRIVACY.md), [copyright policy](https://github.com/mhabedank/mobility-model-zoo/blob/main/COPYRIGHT_POLICY.md).

## License

Models are released under Apache-2.0 unless their card says otherwise.
