# Quickstart: validate the release pipeline end to end

This guide proves feature 003 works. It uses the sandbox test model only; the production span model follows in feature 004. Commands and exit codes are in [contracts/cli.md](contracts/cli.md), workflows and secrets in [contracts/workflows.md](contracts/workflows.md).

## Prerequisites (one time)

1. Hugging Face organization `mobility-model-zoo` exists, and the owner is an admin.
2. Two fine-grained tokens:
   - `HF_RELEASE_TOKEN` (write to the organization's repos and collections) is stored as a GitHub repository secret.
   - `HF_STAGING_TOKEN` (write only to the listed staging repos, no repo creation) is in the local `.env`.
5. The 003 branch is merged into `main`, so the release workflows can be started.
3. The repository is renamed: `git remote -v` shows `mhabedank/mobility-model-zoo`.
4. `uv sync --all-extras` succeeds, and `uv run pytest` and `uv run zoo validate --all` pass.

## Scenario 1: offline gate catches broken records (SC-005)

```bash
uv run zoo validate --all                                    # exit 0
# Delete `license` from zoo/models/sandbox-pipeline-tiny/model.yaml, then:
uv run zoo validate sandbox-pipeline-tiny                    # exit 1, names rule 1 (license missing)
git checkout zoo/models/sandbox-pipeline-tiny/model.yaml
```

Repeat for each required field. The automated test `tests/release/test_gate_required_fields.py` does this for every field (100% blocked).

## Scenario 2: stage the test model

```bash
HF_RELEASE_TOKEN=... uv run zoo init-model sandbox-pipeline-tiny                        # creates the private staging repo
# add mobility-model-zoo/sandbox-pipeline-tiny-staging to HF_STAGING_TOKEN's repo list on the Hub
uv run python -m mobility_model_zoo.sandbox.build_test_model --out /tmp/pipeline-tiny   # writes model.safetensors, config.json
uv run zoo stage sandbox-pipeline-tiny 0.1.0 --from /tmp/pipeline-tiny
```

Expected: the private repo `mobility-model-zoo/sandbox-pipeline-tiny-staging` exists with one commit, and `releases/0.1.0.yaml` has `files[]` and `staging.revision`. Commit the record.

## Scenario 3: tag, verify, review the preview (FR-013)

```bash
git tag sandbox-pipeline-tiny/v0.1.0 && git push origin sandbox-pipeline-tiny/v0.1.0
```

Expected in the `release-verify` run:
- every gate rule is `PASS`, including 10b (Hub validation, no warnings) and 12 (usage example in a fresh environment),
- the job summary links the preview on the `rc-v0.1.0` branch of the staging repo and shows `card_sha256`,
- nothing exists yet at `mobility-model-zoo/sandbox-pipeline-tiny`.

Open the preview and check the card against [contracts/model-card.md](contracts/model-card.md).

## Scenario 4: approve and publish (SC-001, SC-007)

Start `release-publish` with `model=sandbox-pipeline-tiny`, `version=0.1.0`, `confirm=sandbox-pipeline-tiny/v0.1.0`.

Expected:
- `mobility-model-zoo/sandbox-pipeline-tiny` exists, is **private**, has tag `v0.1.0`, and its files match the record,
- less than 30 minutes between starting the run and the tag being visible,
- a commit on `main` sets `published` in the release record,
- the sandbox model is absent from `zoo/MODELS.md` and from every collection.

Check the download by version:

```bash
uv run python -c "from huggingface_hub import snapshot_download; print(snapshot_download('mobility-model-zoo/sandbox-pipeline-tiny', revision='v0.1.0'))"
```

## Scenario 5: refusals

| Action | Expected |
|--------|----------|
| Start `release-publish` again for 0.1.0 | exit 3, repo unchanged (SC-006) |
| Start it with a wrong `confirm` | exit 4, nothing uploaded |
| Overwrite the `rc-v0.1.0` preview with a build from another commit, then start publish | exit 4 (preview not built from the tag commit) |
| Corrupt one staged file (upload a different file to staging), re-tag as 0.1.1 | rule 5 fails, nothing uploaded |
| Remove `HF_RELEASE_TOKEN` | exit 5, clear message |

## Scenario 6: second version and history (US4)

Stage, tag, verify and publish `0.2.0` with a changed record. Expected: `revision='v0.1.0'` still returns the 0.1.0 files; the default branch returns 0.2.0; the card's version history lists both with their metrics side by side.

## Scenario 7: span model dry run (FR-020)

Fill in a draft `zoo/models/productdev-jtbd-span-xlmr/releases/0.1.0.yaml` and run `uv run zoo check productdev-jtbd-span-xlmr 0.1.0 --offline`. Expected: the only failures are the fields that feature 004 has to deliver (staged files, results, recipe commit). The list is copied into the 004 spec.

## Scenario 8: history check before going public (FR-003c)

```bash
uv run zoo history-check     # exit 0 required before the repository becomes public (feature 004)
```
