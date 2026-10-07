---
title: README
emoji: 🚏
colorFrom: green
colorTo: yellow
sdk: static
pinned: false
---

# Mobility Model Zoo

Small, fast machine learning models for mobility: public transport, cycling, shared and on-demand mobility. Every model runs locally on ordinary hardware, is versioned, and ships with a model card that says what it does, how good it is and measured against what, how fast it is on which hardware, and where it fails.

## Topics

| Topic | What it covers |
|-------|----------------|
| **Product development** (`productdev`) | Product discovery in mobility. First task: extracting jobs-to-be-done, pains and gains with verbatim evidence from interviews, reviews and forum posts (German and English). |

More topics follow as separate collections. Existing models do not change when a topic is added.

## How we publish

- **Measured, not claimed.** Every model is scored on a frozen benchmark with a fixed harness, and the card reports quality, speed on named hardware and known failure modes.
- **Immutable versions.** Each release is one tagged version (`v0.1.0`, …) and is never overwritten. Older versions stay available.
- **Open method, closed data.** Models, methods, prompts and evaluation results are published. Datasets and source texts are not, because they contain text written by people who did not agree to its redistribution.
- **Names stay.** Models are named `<topic>-<task>-<variant>`, for example `productdev-jtbd-span-xlmr`, and the name never changes after the first release.

## License

Models are released under Apache-2.0 unless their card says otherwise.
