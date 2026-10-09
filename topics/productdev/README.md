# Product development (`productdev`)

Models that support product discovery in mobility. Hugging Face collection: [Product development](https://huggingface.co/collections/mobility-model-zoo/product-development-6ac6269f0468c62fefb874a8).

## Tasks and models

| Task | Tool | Models |
|---|---|---|
| `jtbd`: extract jobs-to-be-done, pains and gains with verbatim evidence from German and English texts | `jtbd` | [`scout-large`](https://huggingface.co/mobility-model-zoo/scout-large) |
| `jtbd-cluster`: merge duplicate items, link more specific needs and cluster them into opportunities ([task document](tasks/jtbd-cluster.md)) | `jtbd cluster` | none yet (training-free baseline in development, feature 009) |

## What is where

| Folder | Content |
|---|---|
| [tasks/](tasks/) | Task documents: scope, reference, benchmark, metrics, tool, budget |
| [guideline/](guideline/) | Labeling guideline and examples (frozen per benchmark version) |
| [benchmarks/](benchmarks/) | Frozen benchmark manifests (hashes only, never text) |
| [reports/](reports/) | Pilot, spike and release reports, model card previews |
| [recipes/](recipes/) | How each model was built, with figures |
| [compliance/](compliance/) | Source classes, source records and dataset declarations of this topic (compliance register) |
| [research/](research/) | Background research |
| [spike/](spike/) | Technical spike code (feature 002); never imported by the package |
| [scripts/](scripts/) | Helper scripts for the pilot, the span model, the reference VM and the DGX Spark |
| [deploy/](deploy/) | Build context of the reference machine for speed measurements |

Code: `src/mobility_model_zoo/productdev/jtbd/`. Configuration: `configs/productdev/jtbd/`. Collected texts live in `data/` and are never committed.
