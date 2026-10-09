# Automotive security (`security`)

Small models that detect attacks on vehicle buses and radio interfaces, built to run on microcontrollers. Hugging Face collection: not yet published (created with the first model).

The models detect anomalies for monitoring and research. They are not safety mechanisms and are not developed under ISO/SAE 21434 or ISO 26262.

## Tasks and models

| Task | Tool | Models |
|---|---|---|
| `can-ids`: intrusion detection on classic CAN | `security can-ids` | `picket-forest`, `picket-mlp` (registered, not published) |

## What is where

| Folder | Content |
|---|---|
| [research/](research/) | Threat landscape, literature, datasets, hardware, toolchain, notes, merge log |
| [tasks/](tasks/) | Task documents: scope, reference, benchmark, metrics, budgets |
| [compliance/](compliance/) | Source classes and dataset declarations (compliance register) |
| [reports/](reports/) | Research results and model reports |
| [recipes/](recipes/) | How each model is built |

Code: `src/mobility_model_zoo/security/`. Firmware: `firmware/`. Configuration: `configs/security/`.
