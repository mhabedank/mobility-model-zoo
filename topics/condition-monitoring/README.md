# Condition monitoring (`condition-monitoring`)

Small models that watch machines and movement through sensors, built to run on microcontrollers. Hugging Face collection: [Condition monitoring](https://huggingface.co/collections/mobility-model-zoo/condition-monitoring-6ad880c640d8a30e6bf21dd4).

## Tasks and models

| Task | Tool | Models |
|---|---|---|
| `sound-anomaly`: anomaly score of machine sounds (fans, pumps) | `condmon sound-anomaly` | `hum-fan` (registered, not published) |
| `activity`: activity recognition from IMU windows | `condmon activity` | [`pace-cnn`](https://huggingface.co/mobility-model-zoo/pace-cnn) (0.1.0, experimental; [evaluation report](reports/pace-cnn/0.1.0/)) |

## What is where

| Folder | Content |
|---|---|
| [research/](research/) | Dataset research and mobility relevance |
| [tasks/](tasks/) | Task documents |
| [compliance/](compliance/) | Source classes and dataset declarations (compliance register) |
| [reports/](reports/) | Research results and model reports |
| [recipes/](recipes/) | How each model is built |

Code: `src/mobility_model_zoo/condition_monitoring/`. Configuration: `configs/condition-monitoring/`.
