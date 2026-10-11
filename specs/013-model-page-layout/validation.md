# Validation: Model pages in progressive depth

## Baseline

Measured on 2026-10-11 on a local build of `main` cc0f804 (feature 012 merged), Chromium via Playwright. One screen = viewport height. Raw data: [baseline-before.json](baseline-before.json).

### scout-large at 1440x900

First quality figure at screen 9; limits at screen 10.1; page 14 screens.

| Section | Starts at screen | Words |
|---|---|---|
| top | 0.1 | 66 |
| why | 0.6 | 167 |
| quickstart | 1.3 | 211 |
| interface | 3.3 | 798 |
| examples | 6.2 | 354 |
| quality | 8.6 | 310 |
| limits | 10.1 | 373 |
| provenance | 11.1 | 99 |
| versions | 11.9 | 128 |
| cite | 12.5 | 31 |
| notes | 13 | 267 |

### scout-large at 390x844

First quality figure at screen 15.6; limits at screen 17.8; page 25.1 screens.

| Section | Starts at screen | Words |
|---|---|---|
| top | 0.2 | 66 |
| why | 1 | 167 |
| quickstart | 2.3 | 211 |
| interface | 4.9 | 798 |
| examples | 11.5 | 354 |
| quality | 15.1 | 310 |
| limits | 17.8 | 373 |
| provenance | 20 | 99 |
| versions | 21 | 128 |
| cite | 22.8 | 31 |
| notes | 23.3 | 267 |

### picket-forest at 1440x900

First quality figure at screen 6.1; limits at screen 6.5; page 10 screens.

| Section | Starts at screen | Words |
|---|---|---|
| top | 0.1 | 59 |
| why | 0.6 | 128 |
| quickstart | 1.2 | 121 |
| interface | 2.4 | 627 |
| examples | 4.4 | 340 |
| quality | 5.8 | 77 |
| limits | 6.5 | 413 |
| provenance | 7.6 | 95 |
| versions | 8.3 | 141 |
| cite | 8.9 | 31 |
| notes | 9.4 | 95 |

### picket-forest at 390x844

First quality figure at screen 11.6; limits at screen 12.5; page 19.9 screens.

| Section | Starts at screen | Words |
|---|---|---|
| top | 0.2 | 59 |
| why | 0.9 | 128 |
| quickstart | 1.9 | 121 |
| interface | 3.6 | 627 |
| examples | 8.6 | 340 |
| quality | 11.3 | 77 |
| limits | 12.5 | 413 |
| provenance | 15.1 | 95 |
| versions | 16.1 | 141 |
| cite | 18.3 | 31 |
| notes | 18.8 | 95 |

## Link inventory before

Every distinct `href` on the page (input for SC-006).

### scout-large (45 targets)

- `#ex1-i0`
- `#ex1-q0`
- `#ex2-i0`
- `#ex2-i1`
- `#ex2-q0`
- `#ex2-q1`
- `#ex3-i0`
- `#ex3-i1`
- `#ex3-q0`
- `#ex3-q1`
- `#fn-1`
- `#fn-2`
- `#fn-3`
- `#fn-4`
- `#fn-5`
- `#fn-6`
- `#fn-7`
- `#fn-8`
- `#fn-9`
- `#interface`
- `#main`
- `#quickstart`
- `../../`
- `../../#models`
- `../../#principles`
- `../../#topics`
- `../../formats/jtbd-span-v1/`
- `https://github.com/mhabedank/mobility-model-zoo`
- `https://github.com/mhabedank/mobility-model-zoo/blob/main/COPYRIGHT_POLICY.md`
- `https://github.com/mhabedank/mobility-model-zoo/blob/main/LICENSE`
- `https://github.com/mhabedank/mobility-model-zoo/blob/main/PRIVACY.md`
- `https://github.com/mhabedank/mobility-model-zoo/blob/main/topics/productdev/recipes/scout-large.md`
- `https://github.com/mhabedank/mobility-model-zoo/blob/scout-large/v0.1.2/src/mobility_model_zoo/productdev/jtbd/span/jtbd-span-v1.schema.json`
- `https://github.com/mhabedank/mobility-model-zoo/blob/scout-large/v0.1.2/zoo/models/scout-large/releases/0.1.2.ai-act.md`
- `https://github.com/mhabedank/mobility-model-zoo/blob/scout-large/v0.1.2/zoo/models/scout-large/releases/0.1.2.compliance.yaml`
- `https://github.com/mhabedank/mobility-model-zoo/blob/scout-large/v0.1.2/zoo/models/scout-large/releases/0.1.2.training-data-summary.md`
- `https://github.com/mhabedank/mobility-model-zoo/blob/scout-large/v0.1.2/zoo/models/scout-large/results/0.1.2/performance.json`
- `https://github.com/mhabedank/mobility-model-zoo/blob/scout-large/v0.1.2/zoo/models/scout-large/results/0.1.2/quality.json`
- `https://huggingface.co/FacebookAI/xlm-roberta-large`
- `https://huggingface.co/mobility-model-zoo`
- `https://huggingface.co/mobility-model-zoo/scout-large`
- `https://huggingface.co/mobility-model-zoo/scout-large/tree/06291f32c1ede28e11a7c4892faf2d784d58b38d`
- `https://huggingface.co/mobility-model-zoo/scout-large/tree/16da988e372e83eeaf5a41861e3cc2d6624ee3bc`
- `https://huggingface.co/mobility-model-zoo/scout-large/tree/e79568a84e08282374539c1740fa3118dc4dbb45`
- `https://miskatonic-analytics.com/imprint.html`

### picket-forest (30 targets)

- `#fn-1`
- `#fn-2`
- `#fn-3`
- `#fn-4`
- `#interface`
- `#main`
- `#quickstart`
- `../../`
- `../../#models`
- `../../#principles`
- `../../#topics`
- `../../formats/picket-forest-v2/`
- `https://github.com/mhabedank/mobility-model-zoo`
- `https://github.com/mhabedank/mobility-model-zoo/blob/main/COPYRIGHT_POLICY.md`
- `https://github.com/mhabedank/mobility-model-zoo/blob/main/LICENSE`
- `https://github.com/mhabedank/mobility-model-zoo/blob/main/PRIVACY.md`
- `https://github.com/mhabedank/mobility-model-zoo/blob/main/src/mobility_model_zoo/security/can_ids/picket-forest-v2.schema.json`
- `https://github.com/mhabedank/mobility-model-zoo/blob/main/topics/security/recipes/picket-forest.md`
- `https://github.com/mhabedank/mobility-model-zoo/blob/picket-forest/v0.2.0/zoo/models/picket-forest/examples/01-fabrication.json`
- `https://github.com/mhabedank/mobility-model-zoo/blob/picket-forest/v0.2.0/zoo/models/picket-forest/examples/02-dos.json`
- `https://github.com/mhabedank/mobility-model-zoo/blob/picket-forest/v0.2.0/zoo/models/picket-forest/examples/03-fuzzing.json`
- `https://github.com/mhabedank/mobility-model-zoo/blob/picket-forest/v0.2.0/zoo/models/picket-forest/releases/0.2.0.ai-act.md`
- `https://github.com/mhabedank/mobility-model-zoo/blob/picket-forest/v0.2.0/zoo/models/picket-forest/releases/0.2.0.compliance.yaml`
- `https://github.com/mhabedank/mobility-model-zoo/blob/picket-forest/v0.2.0/zoo/models/picket-forest/releases/0.2.0.training-data-summary.md`
- `https://github.com/mhabedank/mobility-model-zoo/blob/picket-forest/v0.2.0/zoo/models/picket-forest/results/0.2.0/performance.json`
- `https://github.com/mhabedank/mobility-model-zoo/blob/picket-forest/v0.2.0/zoo/models/picket-forest/results/0.2.0/quality.json`
- `https://huggingface.co/mobility-model-zoo`
- `https://huggingface.co/mobility-model-zoo/picket-forest`
- `https://huggingface.co/mobility-model-zoo/picket-forest/tree/9d5beab03ad2cc57e4cdfca7bcf6a3dd3679144c`
- `https://miskatonic-analytics.com/imprint.html`

## After the change

Measured on 2026-10-11 on a local build of this branch after US1–US5, same method as the baseline. Raw data: [measure-after.json](measure-after.json).

| Model | Viewport | First quality figure (screen) before → after | Limits (screen) before → after | Page (screens) before → after |
|---|---|---|---|---|
| scout-large | 1440x900 | 9 → 1.6 | 10.1 → 2.7 | 14 → 16.7 |
| scout-large | 390x844 | 15.6 → 2.8 | 17.8 → 5.1 | 25.1 → 32 |
| picket-forest | 1440x900 | 6.1 → 1.5 | 6.5 → 1.9 | 10 → 12.1 |
| picket-forest | 390x844 | 11.6 → 2.5 | 12.5 → 3.4 | 19.9 → 23.8 |

SC-001 (first quality figure ≤ 2 desktop screens) and SC-003 (limits ≤ 4 desktop screens) are met for both models. The page is longer than before because the full metric tables are open in the details layer.

## Link inventory after

Compared with "Link inventory before" (SC-006):

- **scout-large**: removed `#fn-8`, `#fn-9`, `#interface`; added `#details`, `#limits`, `#metrics`, `#quality`, `#reference`, `#versions`, `https://github.com/mhabedank/mobility-model-zoo/blob/scout-large/v0.1.2/docs/recipes/productdev-jtbd-span-xlmr.md`, `https://github.com/mhabedank/mobility-model-zoo/tree/scout-large/v0.1.2/zoo/models/scout-large/results/0.1.2`.
- **picket-forest**: removed `#interface`; added `#details`, `#limits`, `#metrics`, `#quality`, `#reference`, `#versions`, `https://github.com/mhabedank/mobility-model-zoo/blob/picket-forest/v0.2.0/topics/security/tasks/can-ids.md`, `https://github.com/mhabedank/mobility-model-zoo/tree/picket-forest/v0.2.0/zoo/models/picket-forest/results/0.2.0`.

Assessment: no document or external target was removed. `#interface` is no longer a hero button (replaced by Limits and Details), and the anchor still resolves (check D5). The scout-large footnotes `#fn-8` and `#fn-9` belonged to numbers that the shortened differentiators no longer quote; those numbers remain in the charts and the metric tables.
