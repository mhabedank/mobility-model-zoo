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

## Topics

| Topic | What it covers |
|-------|----------------|
| **Product development** (`productdev`) | Product discovery in mobility. First task: extracting jobs-to-be-done, pains and gains with verbatim evidence from interviews, reviews and forum posts (German and English). |

More topics follow as separate collections, for example automotive security with tiny models on embedded hardware. Existing models do not change when a topic is added.

## What the zoo stands for

- **Compliance comes first.** No model ships before its compliance check has passed. Sources and licences are checked and credited, personal data is kept to a minimum, and every release comes with its EU AI Act classification and a summary of its training data. How texts are collected and processed, and how to object: [privacy notice](https://github.com/mhabedank/mobility-model-zoo/blob/main/PRIVACY.md), [copyright policy](https://github.com/mhabedank/mobility-model-zoo/blob/main/COPYRIGHT_POLICY.md).
- **Built for real use cases.** Every model solves one concrete mobility problem and is ready for production, with a documented interface, a stable output format and a card that says what the model is for and what it must not be used for.
- **Right-sized, from decision models to LLMs.** Every task gets the smallest model that does the job well, from a compact decision model on a control unit to a large language model. It runs on your own hardware, so no data leaves your company, nothing depends on an outside service and there is no cost per call.
- **Known quality, known limits.** Every model states what it achieves, at what speed on which hardware, measured against what, and where it fails.
- **Open for everyone, including commercial use.** Models, methods, prompts and evaluation results are published under an open licence, and companies may build commercial products on them. Datasets are shared only where their own licences allow it.

## License

Models are released under Apache-2.0 unless their card says otherwise.
