# Data model: Topic layout and security merge

Phase 1 of [plan.md](plan.md). Entities, fields, validation rules and states. Formats of release files: [contracts/release-format.md](contracts/release-format.md).

## Topic (`zoo/topics.yaml` + `topics/<id>/`)

| Field | Type | Rule |
|---|---|---|
| `id` | string | `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`, ≤ 24 chars, unique, never changes |
| `title` | string | shown as the collection title |
| `description` | string | one sentence |
| `hf_collection` | string or null | null until the first model of the topic is published; `sandbox` always null |

Folder `topics/<id>/` (all topics except `sandbox`): `README.md` (scope, tasks, models, collection link or "not yet published"), `datasets.yaml`, `research/`, `reports/`, `recipes/`. `zoo validate --all` checks that the folder and the two files exist.

Entries added in this feature:

| id | title | description |
|---|---|---|
| `security` | Automotive security | Small models that detect attacks on vehicle buses and radio interfaces, built to run on microcontrollers. |
| `condition-monitoring` | Condition monitoring | Small models that watch machines and movement through sensors, built to run on microcontrollers. |

## Task

Recorded in a task document `topics/<topic>/tasks/<task>.md` (FR-009); not a registry file.

| Field | Content |
|---|---|
| id | `can-ids`, `sound-anomaly`, `activity` (and existing `jtbd`) |
| scope in / out | what the models of the task do and must not do |
| reference | dataset labels (ground truth) or model consensus |
| benchmark | name and version (`can-ids-v1`, `mimii-fan-v1`, `uci-har-v1`), frozen at first use |
| metrics | names, definitions, which one is the headline |
| tool | CLI group (`security can-ids`, `condmon sound-anomaly`, `condmon activity`) |
| framework | chosen per task with justification (constitution VIII as amended) |
| hardware budget | target boards, flash and RAM limits (Principle V) |

## Model (`zoo/models/<name>/model.yaml`)

Unchanged fields from feature 003, plus `runtime` and `card.device_usage` ([release-format.md](contracts/release-format.md)). Models registered in this feature:

| name | topic | task | runtime | license | library_name | pipeline_tag | languages | base_model |
|---|---|---|---|---|---|---|---|---|
| `picket-forest` | security | can-ids | mcu | Apache-2.0 | sklearn | tabular-classification | [] | null |
| `picket-mlp` | security | can-ids | mcu | Apache-2.0 | litert | tabular-classification | [] | null |
| `hum-fan` | condition-monitoring | sound-anomaly | mcu | CC-BY-SA-4.0 (`license_exception`: MIMII share-alike) | litert | audio-classification | [] | null |
| `pace-cnn` | condition-monitoring | activity | mcu | Apache-2.0 | litert | other (free tag `time-series-classification`) | [] | null |

`library_name` and `pipeline_tag` values were checked on 2026-10-08 against the Hugging Face library list (`huggingface.js` `model-libraries.ts`: `sklearn`, `litert`) and the official pipeline tags (`tabular-classification`, `audio-classification`; there is no `time-series-classification`, so `pace-cnn` uses `other`).

Each gets `releases/0.1.0.yaml` as a draft (status `experimental`, `published: null`) with provenance, evaluation and performance budget filled from the research results, `files: []` and `staging: null` until a retraining run stages files. `zoo check` then reports the missing evidence (SC-004).

## Dataset declaration (`topics/<topic>/datasets.yaml`, schema `datasets.schema.json`)

```yaml
datasets:
  - id: road                       # ^[a-z0-9][a-z0-9-]*$, unique across all topics
    title: ROAD CAN intrusion dataset
    use_case: CAN bus intrusion detection on a real vehicle
    provider: zenodo               # zenodo | uci | bitbucket | url
    locator: {zenodo_record: 10462796}   # provider-specific: zenodo_record, uci_id, repo, urls, file filters, zip_members
    homepage: https://0xsam.com/road
    license: CC-BY-4.0             # SPDX id
    license_url: https://creativecommons.org/licenses/by/4.0/
    license_check: api             # api | manual
    license_checked: 2026-10-07    # last check date (manual: by a person; api: by CI)
    permitted_use: training_allowed  # training_allowed | benchmark_only
    redistribution: unclear        # allowed | not_allowed | unclear
    redistribution_basis: "CC BY 4.0 permits redistribution with attribution; provider terms not yet checked"
    commercial_use: true
    attribution: "Verma et al., ORNL"
    citation: "…"
    approx_size_mb: 600
    retention: "local cache, delete 12 months after the last training run that used it"
    status: active                 # active | broken_at_source | rejected
    reason: null                   # required unless status is active
    used_by: [picket-mlp]
```

Rules: `redistribution: allowed` requires a non-empty `redistribution_basis` naming the license clause and the date of the check (constitution VI); every entry starts as `unclear` in this feature, and no dataset is published here (FR-011). `permitted_use: training_allowed` requires `commercial_use: true` and a license without `NC` or `ND`; `rejected` and `broken_at_source` require `reason`; `license_check: manual` requires `license_checked`; ids are unique across all topic files.

Initial declarations:

| Topic | id | License | Permitted use | Status |
|---|---|---|---|---|
| security | `can-train-and-test` | CC-BY-4.0 (manual check, DTU DOI 10.11583/DTU.24805533) | training_allowed | active |
| security | `road` | CC-BY-4.0 (Zenodo API) | training_allowed | active |
| security | `can-mirgu` | CC-BY-4.0 | training_allowed | broken_at_source (zero-filled archive at UCI) |
| security | `syncan`, `hcrl-car-hacking`, `tue-can-v2`, `gem-can` | non-commercial | benchmark_only | rejected for training (reason: NC) |
| security | `veremi-extension`, `gps-spoofing-aissou` | CC-BY-4.0 | training_allowed | active (planned models, not downloaded yet) |
| condition-monitoring | `mimii` | CC-BY-SA-4.0 | training_allowed | active (fan, 6 dB, selected zip members) |
| condition-monitoring | `uci-har` | CC-BY-4.0 | training_allowed | active |
| condition-monitoring | `dcase2020-task2-dev`, `dcase2021-toyadmos2`, `gnss-interference-mendeley`, `driver-behavior` | NC or no license | benchmark_only | rejected (reason recorded) |

`SOURCE.json` (next to the downloaded data, never in the repository): `id`, `title`, `license`, `license_url`, `attribution`, `citation`, `homepage`, `retrieved_at`, `files[]{name, url, sha256, bytes}` (or `archive_bytes`, `members_extracted`, `selection` for range reads).

## Device measurement (a performance metric with `origin`)

| Field | Rule |
|---|---|
| `name` | `latency_us` (median), `latency_p99_us`, `flash_kb`, `ram_kb`, `arena_bytes` |
| `value`, `unit`, `description`, `date` | as in feature 003 |
| `hardware` | board and clock, for example `ESP32-S3 DevKitC, 240 MHz` |
| `origin` | `real_board`, `emulator`, `simulator`, `host` |

State rule: an `mcu` release may leave `experimental` only with a `real_board` latency (gate rule 15).

## Credential (`docs/credentials.md`)

| Name | Kind | Scope | Used by | Rotation |
|---|---|---|---|---|
| `HF_RELEASE_TOKEN` | GitHub secret | write to the `mobility-model-zoo` HF org | release-verify, release-publish, zoo-audit | create a new fine-grained HF token, update the secret, revoke the old token |
| `HF_STAGING_TOKEN` | local `.env` | write to private `*-staging` repos | `zoo stage` on the owner's machine | same, in `.env` |
| `HIL_RUNNER_ENABLED` | GitHub variable | none | `hil.yml` runs only when `true` | n/a |

## Merge log (`topics/security/research/merge-log.md`)

One row per file of both source branches: source branch, old path, new path or "dropped", reason. Generated by the import script from the path map, then completed by hand for files changed after import. SC-001 is checked against it.
