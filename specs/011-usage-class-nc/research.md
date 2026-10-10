# Research: Usage class and non-commercial releases

Decisions for the plan of feature 011. Facts about the current code come from a read of `main` on 2026-10-10 (release gate rules 1–17, compliance stages, dataset declarations, card renderer, website).

## R1. Representation of the usage class

- **Decision**: Four values, `commercial`, `commercial-share-alike`, `non-commercial`, `non-commercial-share-alike`, stored as `usage_class` in `model.yaml` (declared, required) and in the release record `usage.class` (derived). In code a small value type with two flags (`commercial`, `share_alike`) and an order: a class is at least as restrictive as another if it is not more commercial and not less share-alike.
- **Rationale**: Readable in YAML, on the card and on the website; two flags make "most restrictive" a simple combination.
- **Alternatives considered**: Two booleans in YAML (less readable on cards); a free licence string only (the licence alone does not say why a model is restricted, and the gate needs the class before a licence is chosen).

## R2. One licence list with attributes

- **Decision**: Extend `compliance/lists/licence-allowlist.yaml` (read today by check C-I2) into the project's licence list. Each entry gets attributes `non_commercial` (default false), `share_alike` (default false), `trains` (default true: the licence permits training a model under the class it implies) and, for share-alike entries, `release_licences` (licences that satisfy it). New entries: `CC-BY-NC-4.0` (`non_commercial`), `CC-BY-NC-SA-4.0` (`non_commercial`, `share_alike`, `release_licences: [CC-BY-NC-SA-4.0]`), `CC-BY-SA-4.0` gets `release_licences: [CC-BY-SA-4.0]`. Licences that appear only in training data of third-party models (for example the MS MARCO terms) are added with `trains: false` and their restriction attributes, so a third-party record can be resolved without allowing that data in our own training. No-derivatives licences stay off the list: an unresolved licence fails closed.
- **Rationale**: One place answers "may this train, and what follows from it" for datasets, sources, base models, third-party models and release licences; the gate, the train check, the ingest check and the audit read the same entries (FR-003, FR-022).
- **Alternatives considered**: Pattern matching on SPDX strings (`-NC`, `-SA`) as today (misses free-text and `LicenseRef-` licences, cannot express "reproduction only"); a second list for release licences (two lists drift apart).

## R3. Resolving the licence of a release-record source

- **Decision**: In order: (1) the dataset declaration when `dataset:` is set; (2) the compliance source or dataset record with the same origin (its `licence` is SPDX or `LicenseRef-`); (3) the licence string as a list id; (4) the bootstrap mapping from free text to SPDX (`compliance/bootstrap.py` `LICENCES`). Anything else is unresolved and fails closed.
- **Rationale**: scout-large's 87 sources carry free-text licences in the release record, but their compliance source records are SPDX; resolving through the register keeps the record unchanged (published records are immutable).
- **Alternatives considered**: Rewriting release records to SPDX (forbidden for published versions); failing every free-text licence (would block scout-large's next release for formatting, not for a real gap).

## R4. Derivation in one module

- **Decision**: A new module `src/mobility_model_zoo/compliance/usage.py` collects the inputs of a release (sources marked `training_allowed`, base model, teachers, third-party run-time models, zoo-model outputs), resolves each licence (R2, R3, R6–R8), and returns the derived class, the restricting inputs and findings (unresolved, forbidden, share-alike conflict). It also decides whether a release licence satisfies a class. The release gate (rule 6), the train check (C-T2/C-T3), the dataset training guard and the audit call it.
- **Rationale**: FR-022 (one derivation); the module lives in `compliance` because the register, the licence list and the provider routes live there, and the release package already imports it lazily.
- **Alternatives considered**: Logic inside `gate.py` (the train check and the audit could not reuse it).

## R5. Share-alike conflicts

- **Decision**: The release licences that satisfy a class are the intersection of the `release_licences` of all share-alike inputs, filtered to non-commercial licences when the class is non-commercial. An empty intersection is a conflict naming the inputs (for example CC BY-SA 4.0 data and CC BY-NC-SA 4.0 data: CC BY-SA requires CC BY-SA, CC BY-NC-SA requires CC BY-NC-SA). Without share-alike inputs, a commercial class accepts any listed licence that is not non-commercial; a non-commercial class accepts `CC-BY-NC-4.0` or `CC-BY-NC-SA-4.0`.
- **Rationale**: Matches the existing rule (model licence equals the share-alike source licence) and generalises it.
- **Alternatives considered**: A compatibility matrix (CC BY-SA 4.0 → GPLv3 one-way compatibility); not needed for the zoo's models, can be added as `release_licences` entries later.

## R6. Teachers whose outputs may train non-commercial models only

- **Decision**: Provider routes get a fourth value `output_training_permitted: non_commercial`. Release-record teachers get an optional `outputs_non_commercial: true`. A teacher whose `model_id` is a zoo model takes that model's declared class. `Register.output_training_terms(teacher)` returns `yes`, `non_commercial`, `no` or `unclear`; `output_training_permitted` keeps its meaning (`yes` only) for existing callers.
- **Rationale**: FR-007 and FR-008 with the smallest change to records that exist.
- **Alternatives considered**: A separate teacher register (duplicates providers.yaml and configs/productdev/jtbd/models.yaml).

## R7. Outputs of non-commercial zoo models

- **Decision**: Dataset declarations get an optional `produced_by` (a zoo model name). The dataset check refuses `commercial_use: true` when `produced_by` names a model declared non-commercial. The derivation treats such a dataset like any non-commercial input.
- **Rationale**: FR-008; labels and generated data enter training only through declared datasets or teachers, so these two hooks cover both paths.

## R8. Register of third-party models

- **Decision**: New shared register file `compliance/third-party-models.yaml` with schema `third-party-models.schema.json`, loaded by `Register` like the other shared files. Record: `id` (Hugging Face id), `revision`, `remote_code` (`{repo, revision}` or null), `weights_licence`, `training_data` (list of `{name, url, licence}`; `licence` may be `unknown`), `training_data_named` (false when the card names none), `used_by` (list of `{kind: base_model|stage, ref}`, where `ref` is a model name or `config-path#dotted.key`), `notes`, `owner`, `last_reviewed`, `next_review`. The restriction is not stored; it is derived (R4) so it cannot drift.
  - Training-data licence `unknown`: a finding that a recorded owner decision (compliance/decisions.yaml) can accept, because third-party cards rarely license every dataset they name.
  - Only non-commercial and share-alike restrictions carry over from third-party training data. Upstream issues that do not restrict our use (for example a third party training on Reddit) are recorded in `notes` for the owner, not computed.
- **Checks**: The meta stage validates the register (schema, review dates). A new check (C-X1) fails when a `model.yaml` `base_model` is not registered, when a `used_by` reference points to a config key whose model id or revision differs, or when a config names a Hugging Face model with a `revision` that has no register record. The config scan looks at mappings with a `revision` and a `model_id` or `name` of the form `org/name` in `configs/**/*.yaml`; the teacher and baseline register `configs/productdev/jtbd/models.yaml` is excluded because teachers are governed by provider routes and `license_basis`.
- **Initial records**: `FacebookAI/xlm-roberta-large` (base model of scout-large; MIT; trained on CC-100, filtered CommonCrawl). For feature 009's candidates, as found on their model cards on 2026-10-10: `intfloat/multilingual-e5-base` and `-small` (MIT; the card names fine-tuning data including MS MARCO, whose terms permit non-commercial research only, and Quora), `Alibaba-NLP/gte-multilingual-base` (Apache-2.0; no training data named; remote code `Alibaba-NLP/new-impl`), `sentence-transformers/LaBSE` (Apache-2.0; no training data named) and `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7` (MIT; XNLI and ANLI, CC BY-NC 4.0). The register derives non-commercial for the e5 models and the NLI model.
- **Rationale**: FR-017–FR-019; deriving the restriction keeps records short and consistent with R4.
- **Alternatives considered**: Recording third-party models in each settings file (feature 009's `licence_basis`); no single place to review, no check across files.

## R9. Naming rule

- **Decision**: Gate rule 2 accepts `<name>-<variant>` for commercial classes and requires `<name>-<variant>-nc` for non-commercial classes; `variant` stays the size or variant (`large`), the suffix is not part of it. A commercial model whose name ends in `-nc` is refused.
- **Rationale**: Constitution 2.1.0 naming rule; keeps `variant` meaningful for collections and tags.

## R10. Release record and immutability

- **Decision**: Release-record schema gets an optional `usage` object `{class, licence, restricting_inputs: [{kind, id, licence, restriction}]}`. The gate requires it for every record it checks whose `published` is empty (not yet published), recomputes it and refuses a mismatch. Published records without it stay valid. The gate also refuses a record whose `usage.class` differs from the class of an earlier record of the same model that has one, and a `model.yaml` `usage_class` that differs from the release's class.
- **Rationale**: FR-012, FR-013 without touching published files.

## R11. Train-time checks

- **Decision**: `check_training` takes the target model's declared class (`usage_class`, default commercial when unknown). C-T2 keeps refusing unknown, no-derivatives, all-rights-reserved, unresolved and `benchmark_only` inputs for every class, and refuses non-commercial inputs only for a commercial target. C-T3 refuses share-alike inputs when the target class lacks share-alike (it no longer needs the model licence string). `jtbd span data-check` passes the declared class of the model named in its span config. `require_training_allowed` in `mobility_model_zoo.datasets` takes the declared class of the model being trained and refuses `commercial_use: false` for a commercial target; its callers (edge Keras export, security forest) pass the class of the model they build when they know it.
- **Ingest (C-I2)**: The licence list now contains non-commercial entries, so `check_snapshots` takes a target class too; with the default (commercial) it refuses non-commercial licences for training exactly as before.

## R12. Schemas of declarations

- **Decision**: `datasets.schema.json` and `sources.schema.json`: a licence matching `-ND` forces `benchmark_only` (unchanged); a licence matching `-NC` forces `commercial_use: false` (datasets) and no longer forces `benchmark_only`; the rule "`training_allowed` ⇒ `commercial_use: true`" is removed. `model.schema.json` gets `usage_class` (enum, required). The existing NC declarations (dcase, gnss-interference, tue-can-v2, gem-can, …) stay `benchmark_only` and `status: rejected` until the owner decides to train an NC model on them.

## R13. Marking on card, Hub and website

- **Decision**:
  - Card: a usage line directly under the version line: "**Usage:** Non-commercial use only · licence CC-BY-NC-4.0 · because <inputs>" or "**Usage:** commercial use permitted · licence Apache-2.0" (share-alike: "derivatives must keep CC-BY-SA-4.0"). `## License` repeats it. Gate rule 10 checks that the line matches the release record.
  - Hub: the front matter `license` stays the lowercased release licence (`cc-by-nc-4.0`, `cc-by-nc-sa-4.0` are valid Hub identifiers).
  - Website: the hero chip shows `Licence <id> · <class>`, the provenance table gets a "Usage" row with the reason, a non-commercial page shows a notice before the install line, the start page lists each model's class. The site check (L3) requires the usage class on each model page.
  - Zoo-wide copy in `zoo/site.yaml`: the principle "Open for everyone, including commercial use" and the lead are rewritten so that they promise open licences and name the per-model class instead of commercial use for every model.
- **Rationale**: FR-014–FR-016; SC-001 needs the four places.

## R14. Audit command

- **Decision**: `zoo compliance usage [--model NAME] [--json]` prints, for every model in `zoo/models/`, the declared class, the derived class of its latest release (from the record, the declarations and the registers), the restricting inputs and the findings. Exit code 1 when a finding blocks a release. Read-only.
- **Rationale**: FR-021; it sits next to `zoo compliance check`.

## R15. CommonCrawl and CC-100 (base model of scout-large)

- **Decision**: Record the training data of `FacebookAI/xlm-roberta-large` as CC-100 (filtered CommonCrawl) under `LicenseRef-CommonCrawl-ToU`, added to the licence list with `trains: false` (we do not train on it) and no non-commercial or share-alike attribute, after reading the Common Crawl terms of use during implementation. If the terms restrict commercial use, the record says so and the audit reports scout-large as a finding for the owner.
