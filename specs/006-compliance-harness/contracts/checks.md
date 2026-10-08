# Contract: checks

Check ids are stable and used in waivers and in failure messages. All carry the prefix `C-`, so they cannot be confused with decision ids (`D…`) or task ids (`T0…`). Fail closed: a missing record or result fails. A stage failure stops the later stages of the same run.

| Id | Stage | Fails when |
|---|---|---|
| C-M1 | meta | the register does not validate against its schemas |
| C-M2 | meta | any `next_review` or legal-watch `review_by` is past and not reviewed |
| C-M3 | meta | a waiver has expired or has no expiry |
| C-M4 | meta | a request is open past its deadline |
| C-F1 | fetch | robots.txt disallows the project agent, `*` or any listed AI agent; robots.txt is unreachable (network or 5xx); 401/403 |
| C-F2 | fetch | TDMRep reservation (well-known file, header or meta) |
| C-F3 | fetch | `noai`, `noml` or `noimageai` in `X-Robots-Tag` or meta robots |
| C-F4 | fetch | ai.txt disallows text |
| C-F5 | fetch | domain on the deny or piracy list, or URL on the suppression list |
| C-F6 | fetch | terms flagged and no owner verdict (D6) |
| C-F7 | fetch | login, paywall or CAPTCHA detected |
| C-F8 | fetch | manual registration without a signals record |
| C-I1 | ingest | source record missing or a required field empty (not `unknown`) |
| C-I2 | ingest | licence not on the allowlist; NC/ND licence with `training_allowed` |
| C-I7 | ingest | a source obtained through a platform API has no `platform_terms`, or the intended use (benchmark, training, hosted processing) is `not_allowed` or `unclear` without a decision |
| C-I3 | ingest | official-work series without a §5 decision |
| C-I4 | ingest | human-subject data without `consent_or_ethics`, or with `unknown` and no decision |
| C-I5 | ingest | vehicle data with VIN, GPS or absolute timestamps `present` and no decision |
| C-I6 | ingest | chunk flagged for a special category in a class with `quarantine` |
| C-P1 | pre-send | an item without a passed redaction of the current pattern version |
| C-P2 | pre-send | the PII re-scan finds an identifier |
| C-P3 | pre-send | an item is quarantined |
| C-P4 | pre-send | the route is not allowed for the role; `consumer_cli` for a new run |
| C-P5 | pre-send | OpenRouter `provider_order` is null or names a provider outside the route |
| C-P6 | post-receive | the answering provider differs from the route (response discarded) |
| C-R1 | retention | a snapshot or dataset is past `retention_until`, or has no purpose |
| C-T1 | train | a training source is suppressed or now has a deny signal |
| C-T2 | train | an NC, ND or unknown licence is in the training data |
| C-T3 | train | a share-alike input and the model licence differ |
| C-T4 | train | the teacher route has `output_training_permitted` other than `yes` and no decision |
| C-T5 | train | redaction recall is below 0.95 on the current test set (D9) |
| C-D1 | model | the memorisation status is missing; generative and above the threshold (D8) |
| C-D2 | model | the compute estimate is missing; it is ≥ 10^23 FLOP or the model is generative without a GPAI review |
| C-U1 | publication | the publication scan report is missing or does not match the current file hashes |
| C-U2 | publication | a file has ≥ 30 consecutive corpus words outside an allowed attributed quote (D7) |
| C-U3 | publication | a file has PII hits |
| C-U4 | publication | an example has no entry in `examples/SOURCES.yaml`, or its source is neither `synthetic` nor a record with `redistribution: allowed` |
| C-C1 | card | a required section is missing (per topic kind) |
| C-C2 | card | forbidden wording: high-risk purpose, safety function, marketing claim, "anonymous model" |
| C-L1 | licence | `reuse lint` fails |
| C-L2 | licence | NOTICE, third-party notices or card attribution differ from the rendering |
| C-L3 | licence | Hub licence or base-model metadata differ from the record; a share-alike repo is gated |
| C-G1 | repository | `LICENSE`, `NOTICE`, `SECURITY.md`, `PRIVACY.md` or `COPYRIGHT_POLICY.md` is missing |
| C-G2 | repository | funding files or links, prices, consulting promotion, or "Miskatonic" outside the contact lines |
| C-G3 | repository | gitleaks finds a secret |
| C-G4 | repository | an mcu release has no firmware SBOM |
| C-G5 | repository | a versioned text file has a PII hit outside the allowlist (controller contact lines, licence-required creator credits from the register, synthetic fixtures under `tests/fixtures/compliance/`) |
| C-N1 | notices | `PRIVACY.md` misses a route in `recipients.yaml` or a source class |
| C-N2 | notices | the retention stated in a notice differs from the register or config |
| C-N3 | drift | any generated document differs from its rendering |
| C-S1 | sign-off | the release compliance record is not signed off |
