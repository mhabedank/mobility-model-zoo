# CLI contract: `zoo`

`zoo` is the release tool, installed with the `[release]` extra (`uv run zoo ...`). It reads the files described in [data-model.md](../data-model.md). It never reads `data/` except in `zoo stage`, which reads one model directory given on the command line.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | OK |
| 1 | Validation failed (gate rule, schema, checksum, card validation). Every failing rule is printed. |
| 2 | Usage error (unknown model, bad version string, bad arguments) |
| 3 | Immutability refusal: the version is already published, the tag exists, or a version is not greater than the latest published one |
| 4 | Approval refusal: `confirm` does not match, or the preview is missing, was built from another commit, or its hashes do not match |
| 5 | Credential missing, expired or without the needed permission |
| 6 | Hugging Face or GitHub unreachable or returned an error (retry is safe) |

## Commands

### `zoo validate [--all | <model>]`

Offline checks only (no network): schemas, name scheme, topic known, version and file name consistent, status vs version, results files present and valid, card renders with every required section, no metric named accuracy. Runs in normal CI on every push. Exit 0 or 1. Records that are not staged yet (empty `staging.revision`) are drafts and are skipped; published records are skipped. Use `zoo check --offline` on a draft to see what is missing.

### `zoo init-model <model>`

Runs with `HF_RELEASE_TOKEN` (owner's machine or a workflow). Validates `model.yaml` and creates `mobility-model-zoo/<model>-staging` as a private repo. Refuses if it exists and is public. Prints a reminder to add the new staging repo to `HF_STAGING_TOKEN`'s repo list.

### `zoo stage <model> <version> --from <dir>`

Runs on the training machine with `HF_STAGING_TOKEN`.
- Never creates repos. Exit 2 if `<model>-staging` does not exist ("run `zoo init-model` first"); exit 1 if it is public.
- Uploads every file in `<dir>` in one commit. Refuses files under `data/`-like paths, `.env`, `*.jsonl` (gate rule 11).
- Writes `files[]` and `staging.revision` into `zoo/models/<model>/releases/<version>.yaml`. Creates the record from a template if missing, with every other field left for the owner to fill in.
- Exit 3 if the record already has `published` set.

### `zoo check <model> <version> [--offline]`

The full release gate (rules below). With `--offline`, network rules (5, 10b, 12, tag existence) are skipped and reported as skipped. Exit 0, 1, 3, 5 or 6.

### `zoo build <model> <version> --out <dir>`

Runs `zoo check`, then writes `<dir>/` with the model files (downloaded from staging at `staging.revision`), the generated `README.md` card and `build.json` (`card_sha256`, file list with sha256, `tag_commit`, staging revision). Running it twice on the same inputs produces byte-identical output.

### `zoo preview <model> <version> --build <dir>`

Uploads the build, including `build.json`, to the staging repo branch `rc-v<version>` (created or overwritten) as one commit, and prints the URL and `card_sha256`. This is the "dry run" the owner reviews (FR-013).

### `zoo publish <model> <version> --confirm <model>/v<version>`

Publishes the reviewed preview. It does not rebuild.

1. Exit 4 if `--confirm` does not equal `<model>/v<version>`.
2. Downloads the head of the staging branch `rc-v<version>`. Exit 4 if it is missing, if `build.json.tag_commit` differs from the checked-out tag commit, if the card's sha256 differs from `build.json.card_sha256`, or if a model file differs from `files[]` in the release record.
3. Reruns gate rules 1–11 and 14 (not 12 and 13, which run the model; their results are part of the reviewed card). Exit 1 on failure.
4. Exit 3 if tag `v<version>` exists in the public repo, or the version is not greater than the latest published one.
5. Creates the target repo if needed: public for normal models, private for sandbox models. Refuses to change the visibility of an existing repo.
6. If `main`'s head already contains exactly the preview's card and model files (a previous run failed after the commit), skips to 7. Otherwise uploads the card and model files (not `build.json`) as one commit on `main`.
7. Creates tag `v<version>` on that commit (`exist_ok=False`).
8. Adds the model to the topic collection (non-sandbox; creates the collection on first use and writes its slug to `topics.yaml`).
9. Writes `published` into the release record and regenerates `zoo/MODELS.md`. The workflow commits these two files to the git repository.

### `zoo deprecate <model> <version> --reason <text> [--successor <version>]`

Sets `status: deprecated` and `deprecated` in the release record, then (in the publish workflow) pushes one card-only commit to `main`: with a deprecation banner if `<version>` is the latest published version, otherwise only with the updated row in the version history. Files and tags are unchanged.

### `zoo index`

Regenerates `zoo/MODELS.md` from all models and release records: one table per topic with name, task, latest version, status and link. Sandbox models are left out.

### `zoo audit [<model>]`

For every published version: the tag exists, points to `published.repo_commit`, and the card there has `published.card_sha256`. Every `*-staging` repo and every sandbox model repo is private. Exit 1 on any mismatch. Runs weekly in CI.

### `zoo history-check`

Scans all commits on all refs for forbidden paths and secrets (research R11). Prints offending commits. Exit 0 or 1.

## Release gate rules

`zoo check` evaluates all rules and prints one line per rule (`PASS`, `FAIL: <reason>` or `SKIP`).

| # | Rule | Spec |
|---|------|------|
| 1 | `topics.yaml`, `model.yaml` and the release record are valid against their schemas | FR-006 |
| 2 | Name follows `<name>-<variant>` (amended 2026-10-07; topic and task are fields); topic exists; name equals directory, record `model`, tag prefix and repo names | FR-003a |
| 3 | Tag version equals file name equals `version`; status matches version (FR-005a); `change_type` matches the previous version and `output_format_version` | FR-005 |
| 4 | Tag `v<version>` absent from the public repo; version greater than every published version | FR-007, FR-008 |
| 5 | Every file in `files[]` exists at `staging.revision` with the recorded sha256 and size; no extra files | FR-006a, FR-009 |
| 6 | `license` is Apache-2.0 or has `license_exception`; `base_model_license` (null only in the `sandbox` topic) and every teacher's `license_basis` permit publication; every teacher has `training_on_outputs_permitted: true` | FR-003b |
| 7 | Every source used for training is `training_allowed`; `spike_data` is false; `synthetic` results only in sandbox | FR-015, FR-021 |
| 8 | `recipe.git_commit` exists and contains `recipe.config` and `recipe.doc` | FR-009 |
| 9 | Both results files exist and validate; every number on the card comes from them; quality metrics name reference, benchmark and item count | FR-014, FR-016 |
| 10 | (a) Card has every required section; (b) Hugging Face `validate-yaml` returns no errors and no warnings | FR-010, SC-002 |
| 11 | The upload contains only `files[]` and `README.md` (`build.json` stays local); no paths under `data/`, no `.env`, no `*.jsonl` | FR-011 |
| 12 | `card.how_to_run`, with `{repo_id}` and `{revision}` set to `staging.repo` and `staging.revision`, runs in a fresh virtual environment on CPU and exits 0 | SC-004 |
| 13 | At least three example texts exist; their outputs come from running the staged model | FR-018 |
| 14 | `sandbox` is true exactly for the `sandbox` topic | FR-021 |
