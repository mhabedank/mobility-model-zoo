# Contract: commands and checks

## `zoo compliance usage [--model NAME] [--json]` (new)

Read-only audit of every model in `zoo/models/` (or one with `--model`). Offline.

Text output, one block per model:

```text
hum-fan  declared commercial-share-alike  derived commercial-share-alike  licence CC-BY-SA-4.0  ok
  share-alike: source https://zenodo.org/records/3384388 (CC-BY-SA-4.0)
scout-large  declared commercial  derived commercial  licence Apache-2.0  ok
some-model  declared commercial  derived non-commercial  licence Apache-2.0  BLOCKED
  C-U2 dataset tue-can-v2 (CC-BY-NC-4.0) makes the model non-commercial
```

`--json`: a list of `{model, version, declared, derived, licence, restricting_inputs[], findings[]}`; a finding is `{check, record, field, reason}` as in the compliance harness.

Exit code: 0 when no model has a blocking finding, 1 otherwise, 2 on usage errors.

## `zoo check <model> <version>` (changed)

- Rule 2: name suffix (C-U4 message: `name must be <name>-<variant>-nc for a non-commercial model` / `name ends in -nc but the model is declared commercial`).
- Rule 6: replaces the blanket non-commercial refusal with the derivation; messages carry the check id and the input, for example `C-U2: dataset tue-can-v2 (CC-BY-NC-4.0) is non-commercial but the model is declared commercial`.
- Rule 10: the card's usage line must match `usage` of the release record.
- Rule 17 / site: model pages show the usage class.

## `zoo compliance check [--ci]` (changed)

- Meta stage validates `compliance/third-party-models.yaml` and runs C-X1 and C-X2.

## `jtbd span data-check` (changed)

- Passes the declared class of the model named in the span config to the train checks; an unknown model counts as commercial.

## Python helpers (internal contract used by other features)

- `mobility_model_zoo.compliance.usage.UsageClass.parse(value)`, `.covers(other)`, `.combine(other)`.
- `derive_release(root, model, record) -> Derivation(cls, restricting_inputs, findings)`.
- `third_party_metadata(root, ids) -> list[dict]` for stage outputs (feature 009).
- `mobility_model_zoo.datasets.require_training_allowed(ds, usage_class="commercial")`.
