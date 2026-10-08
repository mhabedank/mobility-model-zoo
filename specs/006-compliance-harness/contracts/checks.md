# Contract: checks

Check ids are stable and used in waivers and in failure messages. Fail closed: a missing record or result fails. A stage failure stops the later stages of the same run.

| Id | Stage | Fails when |
|---|---|---|
| M1 | meta | the register does not validate against its schemas |
| M2 | meta | any `next_review` or legal-watch `review_by` is past and not reviewed |
| M3 | meta | a waiver has expired or has no expiry |
| M4 | meta | a request is open past its deadline |
| F1 | fetch | robots.txt disallows the project agent, `*` or any listed AI agent; robots.txt is unreachable (network or 5xx); 401/403 |
| F2 | fetch | TDMRep reservation (well-known file, header or meta) |
| F3 | fetch | `noai`, `noml` or `noimageai` in `X-Robots-Tag` or meta robots |
| F4 | fetch | ai.txt disallows text |
| F5 | fetch | domain on the deny or piracy list, or URL on the suppression list |
| F6 | fetch | terms flagged and no owner verdict (D6) |
| F7 | fetch | login, paywall or CAPTCHA detected |
| F8 | fetch | manual registration without a signals record |
| I1 | ingest | source record missing or a required field empty (not `unknown`) |
| I2 | ingest | licence not on the allowlist; NC/ND licence with `training_allowed` |
| I3 | ingest | official-work series without a §5 decision |
| I4 | ingest | human-subject data without `consent_or_ethics`, or with `unknown` and no decision |
| I5 | ingest | vehicle data with VIN, GPS or absolute timestamps `present` and no decision |
| I6 | ingest | chunk flagged for a special category in a class with `quarantine` |
| P1 | pre-send | an item without a passed redaction of the current pattern version |
| P2 | pre-send | the PII re-scan finds an identifier |
| P3 | pre-send | an item is quarantined |
| P4 | pre-send | the route is not allowed for the role; `consumer_cli` for a new run |
| P5 | pre-send | OpenRouter `provider_order` is null or names a provider outside the route |
| P6 | post-receive | the answering provider differs from the route (response discarded) |
| R1 | retention | a snapshot or dataset is past `retention_until`, or has no purpose |
| T1 | train | a training source is suppressed or now has a deny signal |
| T2 | train | an NC, ND or unknown licence is in the training data |
| T3 | train | a share-alike input and the model licence differ |
| T4 | train | the teacher route has `output_training_permitted` other than `yes` and no decision |
| T5 | train | redaction recall is below 0.95 on the current test set (D9) |
| D1 | model | the memorisation status is missing; generative and above the threshold (D8) |
| D2 | model | the compute estimate is missing; it is ≥ 10^23 FLOP or the model is generative without a GPAI review |
| U1 | publication | the publication scan report is missing or does not match the current file hashes |
| U2 | publication | a file has ≥ 30 consecutive corpus words outside an allowed attributed quote (D7) |
| U3 | publication | a file has PII hits |
| U4 | publication | an example is not synthetic and not from a redistributable source |
| C1 | card | a required section is missing (per topic kind) |
| C2 | card | forbidden wording: high-risk purpose, safety function, marketing claim, "anonymous model" |
| L1 | licence | `reuse lint` fails |
| L2 | licence | NOTICE, third-party notices or card attribution differ from the rendering |
| L3 | licence | Hub licence or base-model metadata differ from the record; a share-alike repo is gated |
| G1 | repository | `LICENSE`, `NOTICE`, `SECURITY.md`, `PRIVACY.md` or `COPYRIGHT_POLICY.md` is missing |
| G2 | repository | funding files or links, prices, consulting promotion, or "Miskatonic" outside the contact lines |
| G3 | repository | gitleaks finds a secret |
| G4 | repository | an mcu release has no firmware SBOM |
| N1 | notices | `PRIVACY.md` misses a route in `recipients.yaml` or a source class |
| N2 | notices | the retention stated in a notice differs from the register or config |
| N3 | drift | any generated document differs from its rendering |
| S1 | sign-off | the release compliance record is not signed off |
