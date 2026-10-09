# Credentials

Every secret and repository variable the zoo uses, where it lives, what it may do and how to rotate it. Secrets are never committed: local values go into `.env` (gitignored, template `.env.example`), CI values into GitHub repository secrets. `zoo history-check` and the CI secret scan (gitleaks) fail on a committed secret. A test (`tests/unit/test_workflow_secrets.py`) fails if a workflow uses a secret or variable that is not in the table below.

| Name | Kind | Scope | Used by | Rotation |
|---|---|---|---|---|
| `HF_RELEASE_TOKEN` | GitHub repository secret; also in the owner's `.env` | fine-grained Hugging Face token with write access to the repos and collections of the `mobility-model-zoo` organization | workflows `release-verify`, `release-publish`, `zoo-audit`; `zoo publish` on the owner's machine | create a new fine-grained token on huggingface.co/settings/tokens, update the secret (`gh secret set HF_RELEASE_TOKEN -R mhabedank/mobility-model-zoo`) and `.env`, then revoke the old token on Hugging Face |
| `HF_STAGING_TOKEN` | local `.env` only | fine-grained token with write access only to the private `<model>-staging` repos, no organization rights | `zoo stage` on training machines | create a new token with the same repo list, update `.env` on each training machine, revoke the old token |
| `HIL_RUNNER_ENABLED` | GitHub repository variable (not a secret) | none; `true` lets `hil.yml` run on the self-hosted runner with label `hil` | `hil.yml` | not a secret; set with `gh variable set HIL_RUNNER_ENABLED --body true` once a runner is registered, `false` otherwise |

Other local settings in `.env` (not used by CI): `OPENROUTER_API_KEY` (hosted labeling, hard spending limit), `OLLAMA_HOST`, `OLLAMA_HOST_VM`, `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` / `REDDIT_USER_AGENT`, `MMZ_SUPPRESSION_KEY` (HMAC key of the compliance harness; losing it makes existing suppression hashes unmatchable), `MMZ_DATA` (dataset cache, default `~/.cache/mobility-model-zoo/datasets`).

Deleting a GitHub secret does not revoke the token behind it: always revoke on Hugging Face as well.
