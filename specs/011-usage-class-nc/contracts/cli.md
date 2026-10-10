# Contract: commands and checks

## `zoo compliance usage [--model NAME] [--json]` (new)

Read-only audit of every model in `zoo/models/` (or one with `--model`). Offline.

Text output, one block per model:

```text
hum-fan  declared commercial-share-alike  derived commercial-share-alike  licence CC-BY-SA-4.0  ok
  share-alike: dataset mimii (CC-BY-SA-4.0)
scout-large  declared commercial  derived commercial  licence Apache-2.0  ok
some-model  declared commercial  derived non-commercial  licence Apache-2.0  BLOCKED
  non-commercial: dataset tue-can-v2 (CC-BY-NC-4.0)
  C-K2 dataset tue-can-v2 (CC-BY-NC-4.0) makes the model non-commercial, but it is declared commercial [tue-can-v2]
```

`--json`: a list of `{model, version, declared, derived, licence, restricting_inputs[], findings[]}`; a finding is `{check, record, field, reason}` as in the compliance harness.

Exit code: 0 when no model has a blocking finding, 1 otherwise, 2 on usage errors.

## `zoo check <model> <version>` (changed)

- Rule 2: name suffix (C-K4 message: `name must be <name>-<variant>-nc for a non-commercial model` / `name ends in -nc but the model is declared commercial`).
- Rule 6: replaces the blanket non-commercial refusal with the derivation; messages carry the check id and the input, for example `C-K2: dataset tue-can-v2 (CC-BY-NC-4.0) makes the model non-commercial, but it is declared commercial [tue-can-v2]`; a record not yet published without `usage`, or with a `usage` that differs from the derivation, fails with C-K5 and prints the expected block.
- Rule 10: the card's usage line must match `usage` of the release record.
- Rule 17 / site: model pages show the usage class.

## `zoo compliance check [--ci]` (changed)

- Meta stage validates `compliance/third-party-models.yaml` and runs C-X1 and C-X2.

## `jtbd span data-check` (changed)

- Passes the declared class of the model named in `span_train.model` of the training dataset config to the train checks (C-T2–C-T4) and to the ingest check of `jtbd corpus autochunk` (C-I2); without it the target counts as commercial.

## Python helpers (internal contract used by other features)

- `mobility_model_zoo.compliance.usage.UsageClass.parse(value)`, `.covers(other)`, `.combine(other)`.
- `derive_release(root, model, record) -> Derivation(cls, restricting_inputs, findings)`.
- `third_party_metadata(root, ids) -> list[dict]` for stage outputs (feature 009).
- `mobility_model_zoo.datasets.require_training_allowed(ds, root=None, model=None)`: refuses `commercial_use: false` data unless `model` is declared non-commercial.
- `audit(root, register, only=None)` behind `zoo compliance usage`.
