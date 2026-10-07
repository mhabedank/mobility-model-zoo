# Data Model: Mobility model zoo with versioned Hugging Face releases

All entities are versioned files in the repository (YAML or JSON). Model files never enter the repository. They live in the private staging repository on Hugging Face (spec FR-006a).

The JSON Schemas for these files are in [contracts/](contracts/). The release tool (`zoo`) validates every file against its schema before doing anything else.

## Layout

```text
zoo/
├── topics.yaml                              # Topic list
├── MODELS.md                                # Generated overview (FR-004); never edited by hand
└── models/
    └── <model-name>/                        # e.g. productdev-jtbd-span-xlmr
        ├── model.yaml                       # Model: stable facts and card text
        ├── releases/
        │   └── <version>.yaml               # Release record, one per version (e.g. 0.1.0.yaml)
        ├── results/
        │   └── <version>/                   # Evaluation and performance results the card cites (FR-016)
        │       ├── quality.json
        │       └── performance.json
        └── examples/                        # Example texts for the card (no personal data, FR-018)
            ├── 01-<slug>.txt
            ├── 02-<slug>.txt
            └── 03-<slug>.txt
```

## Topic

File: `zoo/topics.yaml`. Schema: [topics.schema.json](contracts/topics.schema.json).

| Field | Type | Rule |
|-------|------|------|
| `id` | string | Short form used in model names. Pattern `^[a-z][a-z0-9]{1,15}$`. Unique. Never changes. |
| `title` | string | Display name, e.g. "Product development". |
| `description` | string | One or two sentences. |
| `hf_collection` | string or null | Slug of the Hugging Face collection for this topic. Set by `zoo index` on first publication. |

Initial content: two topics. `productdev` ("Product development") holds the JTBD models. `sandbox` ("Pipeline tests") holds only test models; every model in it MUST have `sandbox: true` and private repositories, and it is never listed in `MODELS.md` or a collection. New topics (for example `cybersec`, `iot`) are added by a new entry only (FR-003).

## Model

File: `zoo/models/<model-name>/model.yaml`. Schema: [model.schema.json](contracts/model.schema.json).

| Field | Type | Rule |
|-------|------|------|
| `name` | string | `<name>-<variant>` (amended 2026-10-07): pattern `^[a-z][a-z0-9]*(-[a-z0-9]+)+$`, ending with `-<variant>`. Equals the directory name. The first segment MUST be a topic `id`. Never changes after the first publication (FR-003a). |
| `topic` | string | Topic `id`. MUST equal the first segment of `name`. |
| `task` | string | Short task id, e.g. `jtbd`. MUST equal the second segment of `name`. |
| `variant` | string | Rest of the name, e.g. `span-xlmr`. |
| `title` | string | Human-readable title for the card. |
| `summary` | string | 1–3 sentences: what the model does. |
| `license` | string | SPDX id. `Apache-2.0` unless the base model or teacher terms require otherwise (FR-003b). |
| `license_exception` | string or null | Required if `license` is not `Apache-2.0`: the reason. |
| `base_model` | string | Hugging Face id of the base model, e.g. `FacebookAI/xlm-roberta-large`. |
| `base_model_license` | string or null | SPDX id of the base model's license. Checked by the release gate (rule 6). Null only in the `sandbox` topic. |
| `languages` | list of ISO 639-1 codes | At least one. |
| `pipeline_tag` | string | Hugging Face task tag, e.g. `token-classification`. |
| `library_name` | string | e.g. `transformers`. |
| `tags` | list of strings | Free tags. The topic id and `mobility` are added automatically. |
| `repos.public` | string | `mobility-model-zoo/<name>`. Derived; stored for readability and checked. |
| `repos.staging` | string | `mobility-model-zoo/<name>-staging`. Private. |
| `card.intended_use` | markdown | Who should use it, for what. |
| `card.out_of_scope` | markdown | What it must not be used for. |
| `card.input_output` | markdown | Input format, output format, an example output. |
| `card.how_to_run` | code block (string) | Copy-paste example. MUST contain the placeholders `{repo_id}`, `{revision}` and `{text}` (a Python string literal, e.g. `print(model.predict({text}))`). The card replaces them with `repos.public`, `v<version>` and the first example text; the release gate replaces them with `staging.repo` and `staging.revision`, runs the code in a clean environment once per example text, and uses the printed output as the example's output (SC-004, FR-018). |
| `card.limitations` | markdown | Known limitations and risks. For the span model, this includes what it does not produce (spec FR-019). |
| `card.citation` | string (BibTeX) | Citation entry. |
| `card.install` | string | Install line shown on the card, e.g. `pip install "mobility-model-zoo @ git+https://github.com/mhabedank/mobility-model-zoo@<tag>"`. `<tag>` is replaced by the release's git tag. |

## Release record (model version)

File: `zoo/models/<model-name>/releases/<version>.yaml`. Schema: [release-record.schema.json](contracts/release-record.schema.json).

| Field | Type | Rule |
|-------|------|------|
| `model` | string | MUST equal the model `name`. |
| `version` | string | Semantic version `MAJOR.MINOR.PATCH`. MUST equal the file name and the tag version. |
| `date` | date | Release date. |
| `status` | enum | `experimental`, `released`, `deprecated`. Below 1.0.0 it MUST be `experimental` (FR-005a). |
| `change_type` | enum | `major`, `minor`, `patch`, `initial` (FR-005). Checked against the previous version: a change to `output_format_version` is `major` from 1.0.0 on and at least `minor` before. |
| `changes` | markdown | What changed since the previous version. Shown in the version history. |
| `output_format_version` | string | Identifier of the output format, e.g. `jtbd-span-v1`. |
| `sandbox` | boolean | `true` only for models in the `sandbox` topic. Their target repository is created private and is never made public (FR-021). |
| `files` | list | One entry per model file: `path`, `sha256`, `size_bytes`. MUST be non-empty. |
| `staging.repo` | string | MUST equal the model's `repos.staging`. |
| `staging.revision` | string | Full commit hash in the staging repo that contains exactly `files`. |
| `recipe.git_commit` | string | Commit of this repository that the model was trained from. |
| `recipe.config` | string | Path of the training configuration at that commit. |
| `recipe.doc` | string | Path of the recipe document (how to retrain). |
| `provenance.sources` | list | Per source group: `origin`, `license`, `permitted_use` (MUST be `training_allowed` for training data), `count`. No data, no URLs to raw snapshots. |
| `provenance.teachers` | list | Per teacher: `model_id`, `license_basis`, `training_on_outputs_permitted` (MUST be `true`). |
| `provenance.spike_data` | boolean | MUST be `false` for any non-sandbox release (FR-015). |
| `evaluation.benchmark` | string | Frozen benchmark version, e.g. `pilot-v1`. |
| `evaluation.reference` | string | Who the numbers agree with, e.g. "consensus of Claude and GPT". |
| `evaluation.results` | path | `results/<version>/quality.json`. MUST exist. |
| `performance.hardware` | string | The low-resource reference hardware. |
| `performance.budget` | object | `ram_gb`, `gpu: false`. |
| `performance.results` | path | `results/<version>/performance.json`. MUST exist. |
| `published` | object or null | Written by the pipeline after publication: `repo_commit`, `tag`, `published_at`, `card_sha256`. Null before. |
| `deprecated` | object or null | `reason`, `successor` (version). Set only through `zoo deprecate`. |

### Results files

`quality.json` and `performance.json` follow [results.schema.json](contracts/results.schema.json). Every number shown on the card is read from these files and nowhere else (FR-016, SC-008). Each quality metric carries `name`, `value`, `description`, `reference`, `benchmark`, `n_items`, `date`. Quality metric names must not include "accuracy" (FR-014).

## State transitions

```text
                zoo stage (training machine)
 (none) ─────────────────────────────────────▶ staged
   files in staging repo, checksums in the release record, published = null

 staged ── tag <name>/v<version> ──▶ verified ── owner approval ──▶ published
             checks + dry run +                 (manual publish run)
             preview card on the                upload + tag +
             staging branch rc-v<version>       collection + index

 verified ── approval rejected or missing ──▶ staged (nothing uploaded; fix → new version)

 published ── zoo deprecate ──▶ deprecated
   record updated; one card-only commit on the public repo's main: a banner if the deprecated
   version is the latest one, otherwise only its row in the version history; files and tags unchanged
```

- `published` is final for the files: the public tag `v<version>` points to one commit, and the pipeline refuses to publish a version whose tag already exists (FR-007).
- The verified state is the preview on the staging branch `rc-v<version>` (card, model files and `build.json`). The publish run does not rebuild: it publishes the preview's card and model files, after checking that the preview was built from the tag commit and that its hashes match, so the owner approves exactly what is published.
- A failure during `published` (network, rejected upload) leaves the public repo without the tag. A rerun of the same version is allowed only if the tag does not exist yet; it checks whether the public repo's head already has exactly the staged files and then only creates the tag (edge case "upload rejected halfway").

## Validation rules (release gate)

The gate (`zoo check`) evaluates 14 rules and fails with exit code 1, naming every failing rule. The rules and their spec references are listed once, in [contracts/cli.md](contracts/cli.md#release-gate-rules), and the fields above note which rule checks them.
