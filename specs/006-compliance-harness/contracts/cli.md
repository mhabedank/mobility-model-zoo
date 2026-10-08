# Contract: commands

New `zoo compliance` command group and changes to existing commands. Exit codes follow the `zoo` convention: 0 ok, 1 usage, 2 check failed, 3 refused, 4 external service, 5 missing input, 6 internal. Every failure prints `stage / record / field / reason`.

## `zoo compliance`

| Command | Behaviour |
|---|---|
| `check [--ci] [--stage S] [--model M --version V]` | Runs the stages in order and stops at the first failing stage. `--ci` runs only stages that need no data: meta, licence, repository, notices, drift. |
| `render [--check]` | Renders every generated document from the register. `--check` writes nothing and exits 2 on any difference. |
| `recipients --runs DIR...` | Aggregates labeling logs into `compliance/recipients.yaml` (no text, no chunk ids). |
| `bootstrap-sources --topic T --model M --version V [--benchmark-config C]` | Proposes source records for the training origins of the release and, with `--benchmark-config`, for every snapshot behind that benchmark's chunks (main and holdout). Sources: local snapshot metadata, the source plan, the release provenance and the Zenodo API. Fields that cannot be filled are written as `unknown` with the attempt date; nothing is invented. |
| `retention [--fail]` | Lists items past their retention date or without a purpose. |
| `delete --snapshot ID --reason TEXT` | Deletes a raw snapshot, logs hash and URL, and sets `deleted_at`. |
| `scan-publish --model M --version V` | Scans every file to be published for corpus overlap (≥ 30 words) and PII. Writes the report referenced by the release compliance record. |
| `art9-scan --config C` | Counts special-category flags per chunk set and writes counts only. |
| `redaction-recall` | Runs the redaction pipeline on the synthetic test set and prints recall per identifier type. |
| `request add/close` | Maintains `requests.yaml`; `add` also adds suppression entries (hashing needs `MMZ_SUPPRESSION_KEY`). |
| `watch review ID --outcome TEXT` | Marks a legal-watch item reviewed. |
| `signoff --model M --version V` | Records the owner sign-off in the release compliance record. |

## Changed commands

| Command | Change |
|---|---|
| `jtbd source fetch`, `jtbd source reddit` | Fail-closed signal checks (research R4). A blocked fetch exits 3 with the signal named. Every attempt is written to the crawl manifest. |
| `jtbd source register` | Requires `--signals FILE` (a manual verdict with URL and date); without it, exits 3. |
| `jtbd corpus autochunk` | Runs the ingest checks and the special-category quarantine. Refuses sources without a complete record. |
| `jtbd label` (runner) | Before each batch: re-scan for PII, check the route allowlist, require a pinned OpenRouter provider. After each response: verify the answering provider. Refusals exit 3. |
| `jtbd span data-check` | Adds the train-stage checks: suppression, licence, route sign-off, retention. |
| `jtbd doctor` | Reports retention and review dates. |
| `zoo check` | New rule 16 "compliance". Rule 6 reads `training_on_outputs_permitted` from the route record. Rule 10 uses the new card sections and the card lint. |
| `zoo validate --all` | Also validates the register. |
