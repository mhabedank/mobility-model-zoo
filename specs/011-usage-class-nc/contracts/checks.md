# Contract: checks added or changed by feature 011

Extends the check catalogue of the compliance harness ([specs/006-compliance-harness/contracts/checks.md](../../006-compliance-harness/contracts/checks.md)). Findings print `stage / record / field / reason [check id]`; release gate failures print `C-Kn: reason [record]`.

| Id | Where | Fails when |
|---|---|---|
| C-I2 (changed) | ingest (`jtbd corpus autochunk`) | a training source's licence is not on the licence list for the target class: non-commercial licences only for non-commercial targets, `trains: false` never; or the source is `benchmark_only` |
| C-T2 (changed) | train (`jtbd span data-check`) | an input's licence is unknown, unlisted, no-derivatives or all rights reserved (every class); or it is non-commercial, or its declaration says `commercial_use: false`, and the target is commercial; or it is `benchmark_only` |
| C-T3 (changed) | train | share-alike input and the target class has no share-alike |
| C-T4 (changed) | train | a teacher route does not permit training on outputs (`no`, `unclear`), or permits it for non-commercial models only and the target is commercial |
| C-K1 | gate rule 6, audit | an input's licence resolves to no entry of the licence list |
| C-K2 | gate rule 6, audit | the declared usage class does not cover the class an input forces; names the input and its licence |
| C-K3 | gate rule 6, audit | the release licence is not listed, marks another class than the declared one, or does not satisfy a share-alike input; or share-alike inputs that no single licence satisfies |
| C-K4 | gate rule 2, audit | a non-commercial model is not named `<name>-<variant>-nc`, or a commercial model's name ends in `-nc` |
| C-K5 | gate rule 6, audit | a record not yet published lacks `usage`, `usage` differs from the derivation, or the class differs from an earlier release of the model |
| C-X1 | meta | a base model, a run-time model or a pinned model in `configs/**/*.yaml` is not in `compliance/third-party-models.yaml`, is pinned to another revision or lacks the remote-code commit; or a `used_by` reference does not resolve |
| C-X2 | meta | a third-party model that is used has a training-data licence `unknown`, and no owner decision lists `compliance/third-party-models.yaml#<id>` in its scope |

Gate rule 10 also checks that the card states `**Usage:** …` matching the release record; the site check L3 requires the usage row on every model page.
