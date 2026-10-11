# Handover to feature 009: usage class of the cluster stage

Feature 011 adds the usage class (constitution 2.1.0) and the register of third-party models. Once 011 is merged into `main` and `main` is merged into `009-jtbd-dedup-cluster`, feature 009 adopts it as follows.

## What 011 already provides

- `compliance/third-party-models.yaml` has records for all five models of 009 at the revisions pinned on the 009 branch on 2026-10-10, including the remote code of `Alibaba-NLP/gte-multilingual-base` (`Alibaba-NLP/new-impl` at `40ced75c…`). `used_by` is empty for them.
- Derived classes (see [audit-2026-10-10.md](audit-2026-10-10.md)): multilingual-e5-base and -small **non-commercial** (MS MARCO, Quora), gte-multilingual-base and LaBSE **commercial** (no training data named on their cards), the mDeBERTa NLI model **non-commercial** (XNLI, ANLI).
- `mobility_model_zoo.compliance.usage.third_party_metadata(root, ids)` returns `[{id, revision, usage_class, reason}]` for the stage output.
- Check C-X1 refuses any pinned model in `configs/**/*.yaml` that is not registered with the same revision, and a model with remote code whose settings lack `code_revision` at the registered commit. The cluster settings on the 009 branch already use `model_id`, `revision` and `code_revision`, so they are found by the scan.

## Steps on the 009 branch

1. Add `used_by` entries to the register for the models the stage settings name, for example `{kind: stage, ref: "configs/productdev/jtbd/cluster-baseline.yaml#encoder"}`, one per settings file and block (`encoder`, `nli`, `labeling.pairs.samplers.0`).
2. Write `third_party_metadata` of the loaded encoder (and the NLI model when it is used) into the settings block of `result.json` (`settings.third_party_models`) and state the usage class of the output in the stage documentation (FR-020).
3. Once a model is used, unknown training-data licences become check C-X2: the e5 records list Reddit, TriviaQA, ELI5 and the SBERT mix as `unknown`, the NLI record lists 2mil7, MultiNLI and LingNLI. Either research the licences and fill them in, or record an owner decision whose scope names `compliance/third-party-models.yaml#<id>`.
4. Remove `licence_basis` from the cluster settings or keep it as a pointer to the register; the register is the single place to review.

## Owner decisions for 009

- **Encoder of the baseline**: e5 (non-commercial output) or gte-multilingual-base / LaBSE (commercial). The smoke test of 2026-10-10 used e5-base.
- **Specificity relation**: use the NLI model (non-commercial output) or drop the relation from the baseline (spec FR-024).
- If the stage output is non-commercial, any model trained on it later is non-commercial too (`produced_by` and teacher rules of constitution 2.1.0).
