# Hand-over to feature 004 (production span model)

Written by feature 003 on 2026-10-01. Feature 004 builds the production span model and releases it through the pipeline of feature 003.

## Dry run of the draft release record (FR-020, T060)

Command: `uv run zoo check productdev-jtbd-span-xlmr 0.1.0 --offline` on the draft in `zoo/models/productdev-jtbd-span-xlmr/`.

| Rule | Result | What 004 must deliver |
|------|--------|-----------------------|
| 1 schemas | FAIL | `files[]` and `staging.revision` (written by `zoo stage`), `recipe.git_commit`, `performance.budget.ram_gb` (the memory budget, Principle V) |
| 2 names | PASS | |
| 3 version and status | PASS | |
| 4 not yet published | PASS | |
| 5 staged files | SKIP offline | the staged files (`zoo init-model`, then `zoo stage`) |
| 6 licenses | PASS (base model MIT, no teachers yet) | the teachers with `license_basis` and `training_on_outputs_permitted: true` |
| 7 provenance | PASS (empty) | the training source groups, all `training_allowed`; `spike_data: false` |
| 8 recipe in git | FAIL | `recipe.git_commit`, `recipe.config`, `recipe.doc` |
| 9 results and traceability | FAIL | `results/0.1.0/quality.json` (frozen benchmark `pilot-v1`, reference, item counts) and `results/0.1.0/performance.json` (measured on the reference VM) |
| 10 model card | FAIL (needs rule 9's results to render) | nothing beyond rule 9; the card texts in `model.yaml` are written |
| 11 upload allow-list | PASS | |
| 12 usage example | SKIP offline | the module `mobility_model_zoo.productdev.jtbd.span` with `SpanExtractor.from_pretrained(repo_id, revision=...)` and `extract(text) -> dict`, as used in `card.how_to_run` |
| 13 examples | PASS (3 texts) | |
| 14 sandbox | PASS | |

Only fields that feature 004 delivers are missing. No gap in the release record format was found.

## Interface the span model must provide

- A class in `src/mobility_model_zoo/productdev/jtbd/span.py` (or a package of that name) that loads with `SpanExtractor.from_pretrained("<repo or dir>", revision="<rev>")` from the files in the staging repo, and an `extract(text: str) -> dict` method whose result is JSON-serializable (the card's `input_output` text describes it; adjust it if the format differs).
- Model files that `zoo stage` can upload as a flat directory: no `README.md`, no `build.json`, nothing under `data/`, no `.jsonl`.
- A base install that is enough to run it: `torch`, `transformers`, `huggingface_hub`, `safetensors`, `sentencepiece` (the package's base dependencies). Add any further runtime dependency to the base dependencies, not to an extra.

## Git history check before going public (FR-003c, T062)

`uv run zoo history-check` on 2026-10-01 (all refs, including the spike commits): **0 findings**. No data files, model files or secrets were found by the path rules or by gitleaks. Synthetic fixtures under `tests/fixtures/` (example.org sources) are allowed by design. Run the check again right before the repository is made public.

## Open steps for the owner

- Done 2026-10-07: repository public after `zoo history-check`; staging repo created (renamed `scout-large-staging`) and added to `HF_STAGING_TOKEN`; `scout-large` 0.1.0 published (https://huggingface.co/mobility-model-zoo/scout-large) and listed in the "Product development" collection.
- Open: the reader test (SC-003) with [reader-test.md](reader-test.md) on the public card.
