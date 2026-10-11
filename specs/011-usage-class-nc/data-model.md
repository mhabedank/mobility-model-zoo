# Data model: Usage class and non-commercial releases

## Usage class (value)

| Value | commercial | share_alike |
|---|---|---|
| `commercial` | true | false |
| `commercial-share-alike` | true | true |
| `non-commercial` | false | false |
| `non-commercial-share-alike` | false | true |

- Combination (most restrictive): `commercial = a.commercial and b.commercial`, `share_alike = a.share_alike or b.share_alike`.
- `a` covers `b` (a is at least as restrictive as b): `(not a.commercial or b.commercial) and (a.share_alike or not b.share_alike)`.
- Declared class: `model.yaml` `usage_class` (required). Derived class: computed per release. Rule: declared covers derived.

## Licence entry (`compliance/lists/licence-allowlist.yaml`)

| Field | Type | Meaning |
|---|---|---|
| `id` | string | SPDX id or `LicenseRef-…` |
| `non_commercial` | bool, default false | an input under it makes a model non-commercial; a release licence with it is a non-commercial licence |
| `share_alike` | bool, default false | an input under it makes a model share-alike |
| `release_licences` | list of ids | share-alike only: release licences that satisfy it |
| `trains` | bool, default true | data under it may be used as training data of our models (of the class it implies) |
| `note` | string | optional |

Validation: `release_licences` required when `share_alike`; every id in `release_licences` is itself an entry. Entries not on the list are unresolved (fail closed).

Initial additions: `CC-BY-NC-4.0 {non_commercial}`, `CC-BY-NC-SA-4.0 {non_commercial, share_alike, release_licences: [CC-BY-NC-SA-4.0]}`, `CC-BY-SA-4.0 {share_alike, release_licences: [CC-BY-SA-4.0]}`, licences of third-party training data with `trains: false` (`LicenseRef-MSMARCO-terms {non_commercial}`, `LicenseRef-CommonCrawl-ToU`, and others found while filling the register).

## Restricting input

| Field | Values |
|---|---|
| `kind` | `source`, `dataset`, `base_model`, `teacher`, `third_party`, `zoo_model_output` |
| `id` | origin URL, dataset id, model id |
| `licence` | resolved licence id or terms (`output_training_permitted: non_commercial`) |
| `restriction` | `non-commercial`, `share-alike` or both |

## Model declaration (`zoo/models/<name>/model.yaml`), changed

- New required `usage_class` (enum of the four values).
- Name rule: `name == <base>-<variant>` for commercial classes, `name == <base>-<variant>-nc` for non-commercial classes.
- `license` must satisfy the declared class (R5); `license_exception` names the inputs that make the model non-commercial or share-alike, or "owner's choice".
- Initial values: scout-large `commercial`, sandbox-pipeline-tiny `commercial`, hum-fan `commercial-share-alike`, pace-cnn `commercial`, picket-forest `commercial`, picket-mlp `commercial` (confirmed or corrected by the audit).

## Release record (`zoo/models/<name>/releases/<version>.yaml`), changed

New optional object, required by the gate for records not yet published. `class` is the release's usage class as users get it (the declared class, which the gate checks covers the derived one); `restricting_inputs` are the inputs that restrict the derived class:

```yaml
usage:
  class: non-commercial
  licence: CC-BY-NC-4.0
  restricting_inputs:
    - {kind: dataset, id: tue-can-v2, licence: CC-BY-NC-4.0, restriction: non-commercial}
```

`provenance.teachers[]` gets optional `outputs_non_commercial: bool`.

## Dataset declaration (`topics/<topic>/compliance/datasets.yaml`), changed

- Licence matching `-ND` ⇒ `permitted_use: benchmark_only` (unchanged).
- Licence matching `-NC` ⇒ `commercial_use: false` (new); `training_allowed` allowed.
- Removed: `training_allowed` ⇒ `commercial_use: true`.
- New optional `produced_by`: zoo model name; a non-commercial producer forces `commercial_use: false` (checked by the dataset check, not the schema).

Source records (`sources.yaml`): `-ND` ⇒ `benchmark_only`; `-NC` no longer forces `benchmark_only`.

## Provider route (`compliance/providers.yaml`), changed

`output_training_permitted`: `yes | no | unclear | non_commercial`.

## Third-party model record (`compliance/third-party-models.yaml`, new)

```yaml
models:
- id: Alibaba-NLP/gte-multilingual-base
  revision: 9bbca17d9273fd0d03d5725c7a4b0f6b45142062
  remote_code: {repo: Alibaba-NLP/new-impl, revision: 40ced75c3017eb27626c9d4ea981bde21a2662f4}
  weights_licence: Apache-2.0
  training_data_named: false
  training_data: []
  used_by:
  - {kind: stage, ref: "configs/productdev/jtbd/cluster-gte-base.yaml#encoder"}
  notes: Remote code reviewed 2026-10-10 (model code only).
  owner: Martin Habedank
  last_reviewed: '2026-10-10'
  next_review: '2027-04-10'
```

| Field | Rule |
|---|---|
| `id` | unique, `org/name` |
| `revision` | 40-hex commit |
| `remote_code` | null or `{repo, revision}` with 40-hex commit |
| `weights_licence` | resolvable licence id |
| `training_data` | list of `{name, url, licence}`; `licence` resolvable or `unknown` |
| `training_data_named` | false ⇒ `training_data` empty |
| `used_by` | `{kind: base_model, ref: <zoo model name>}` or `{kind: stage, ref: <config path>#<dotted key>}` |
| `owner`, `last_reviewed`, `next_review` | as every register record |

Derived restriction: combination of the weights licence and every training-data licence (FR-019). `unknown` training-data licence ⇒ finding unless an owner decision in `compliance/decisions.yaml` lists the record id in `affected_records`.

## Stage output metadata (FR-020)

A stage that loads registered third-party models writes `third_party_models: [{id, revision, usage_class, reason}]` into the settings block of its output (helper `third_party_metadata(ids)` in `compliance/usage.py`).

## Findings (new or changed check ids)

| Id | Stage | Meaning |
|---|---|---|
| C-T2 | train | input cannot train any model, or non-commercial input for a commercial target |
| C-T3 | train | share-alike input for a target class without share-alike |
| C-I2 | ingest | licence not on the list, `benchmark_only`, or non-commercial licence for a commercial target |
| C-K1 | usage | input licence unresolved |
| C-K2 | usage | declared class does not cover the derived class |
| C-K3 | usage | release licence does not satisfy the class, or share-alike conflict |
| C-K4 | usage | name suffix `-nc` does not match the class |
| C-K5 | usage | class differs from an earlier release or from `model.yaml` |
| C-X1 | meta | third-party model missing, unpinned or recorded differently |
| C-X2 | meta | third-party training-data licence `unknown` without owner decision |
