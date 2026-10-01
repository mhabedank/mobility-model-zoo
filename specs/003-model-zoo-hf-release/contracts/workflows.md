# Contract: GitHub workflows and secrets

## Tags

A release tag is `<model>/v<version>`, for example `productdev-jtbd-span-xlmr/v0.1.0` or `sandbox-pipeline-tiny/v0.1.0`. It is pushed on the commit that holds the release record. Other tags are ignored by the release workflows.

## Workflows

| File | Trigger | Does | Secrets |
|------|---------|------|---------|
| `.github/workflows/ci.yml` | push, pull request | `uv sync`, `ruff`, `pytest`, `zoo validate --all` | none |
| `.github/workflows/release-verify.yml` | push of a tag matching `*/v*` | `zoo check` → `zoo build` → `zoo preview`; job summary with the gate table, the preview URL and `card_sha256`; uploads `build.json` and `README.md` as an artifact | `HF_RELEASE_TOKEN` |
| `.github/workflows/release-publish.yml` | `workflow_dispatch` with inputs `model`, `version`, `confirm` | checks out the tag `<model>/v<version>`, `zoo publish --confirm` (publishes the reviewed preview, no rebuild), commits the updated release record and `zoo/MODELS.md` to `main` | `HF_RELEASE_TOKEN`, `GITHUB_TOKEN` (contents: write) |
| `.github/workflows/zoo-audit.yml` | weekly schedule, `workflow_dispatch` | `zoo audit` | `HF_RELEASE_TOKEN` (read is enough) |

- Every workflow checks out with `fetch-depth: 0`, because gate rule 8 looks up `recipe.git_commit` in the full history.
- `workflow_dispatch` workflows can only be started from the default branch `main`, so the workflows must be merged into `main` before the first real release.
- `release-publish` uses `concurrency: release-<model>` so two publish runs of the same model never overlap.
- Starting `release-publish` is the owner's approval (spec FR-009, research R5). Only users with write access to the repository can start it.
- Logs never print tokens: `zoo` reads them from the environment and GitHub masks secrets.

## Secrets and tokens

| Name | Where | Scope |
|------|-------|-------|
| `HF_RELEASE_TOKEN` | GitHub repository secret | Fine-grained HF token: write to repos and collections of the `mobility-model-zoo` organization |
| `HF_STAGING_TOKEN` | `.env` on training machines only | Fine-grained HF token: write only to the explicitly listed `<model>-staging` repos; no repo creation. The owner adds each new staging repo after `zoo init-model`. |

Neither token is ever committed (FR-012). `.env` stays gitignored.
