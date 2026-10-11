---
title: README
emoji: 🚏
colorFrom: blue
colorTo: green
sdk: static
pinned: false
---

# Mobility Model Zoo

**Safer, more affordable and better mobility through AI.**

We build machine learning models for real mobility problems and make them available to everyone, for research and for commercial products: from product development to vehicles and embedded systems, from compact decision models to large language models. Every model is checked for compliance, runs on your own hardware and ships with a model card that says what it does, how good it is and measured against what, how fast it is on which hardware, and where it fails.

Website with quickstarts, interface documentation and worked examples: [mhabedank.github.io/mobility-model-zoo](https://mhabedank.github.io/mobility-model-zoo/)

## Topics and models

| Topic | What it covers | Models |
|-------|----------------|--------|
| **Product development** (`productdev`) | Product discovery in mobility: extracting jobs-to-be-done, pains and gains with verbatim evidence from interviews, reviews and forum posts (German and English). | [scout-large](https://huggingface.co/mobility-model-zoo/scout-large) (experimental) · [collection](https://huggingface.co/collections/mobility-model-zoo/product-development-6ac6269f0468c62fefb874a8) |
| **Automotive security** (`security`) | Intrusion detection on in-vehicle networks with tiny models on microcontrollers. First task: CAN intrusion detection, calibrated on the target vehicle's normal traffic. | [picket-forest](https://huggingface.co/mobility-model-zoo/picket-forest) (experimental) · [collection](https://huggingface.co/collections/mobility-model-zoo/automotive-security-6acb5e6340d3356db82d9cde) |

More topics follow as separate collections, for example condition monitoring with models on embedded hardware. Existing models do not change when a topic is added.

## What the zoo stands for

- **Compliance comes first.** No model ships before its compliance check has passed. Sources and licences are checked and credited, personal data is kept to a minimum, and every release comes with its EU AI Act classification and a summary of its training data. How texts are collected and processed, and how to object: [privacy notice](https://github.com/mhabedank/mobility-model-zoo/blob/main/PRIVACY.md), [copyright policy](https://github.com/mhabedank/mobility-model-zoo/blob/main/COPYRIGHT_POLICY.md).
- **Built for real use cases.** Every model solves one concrete mobility problem, with a documented interface, a stable output format and a card that says what the model is for and what it must not be used for. Every release states its status: `released` when it meets the success criteria of its task, `experimental` when it does not yet, with the missed criteria and their measured values on the card.
- **Right-sized, from decision models to LLMs.** Every task gets the smallest model that does the job well, from a compact decision model on a control unit to a large language model. It runs on your own hardware, so no data leaves your company, nothing depends on an outside service and there is no cost per call.
- **Known quality, known limits.** Every model states what it achieves, at what speed on which hardware, measured against what, and where it fails.
- **Open for everyone.** Models, methods, prompts and evaluation results are published under an open licence, and companies may build commercial products on them. Where the licence of an input forbids commercial use, the model is published under a non-commercial licence, carries the suffix `-nc` and says so on its card. Datasets are shared only where their own licences allow it.

## License

Models are released under Apache-2.0 unless their card says otherwise (non-commercial models carry the suffix `-nc`).
