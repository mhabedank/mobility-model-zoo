# Research: Mobility model zoo with versioned Hugging Face releases

Facts were checked on 2026-10-01 against the Hugging Face and GitHub documentation (huggingface_hub 2.1.1) and with two live API calls. "Unverified" marks claims the implementation must test before relying on them.

## R1. Try-it hosting (decided: deferred)

- **Finding**: Static Spaces are free for everyone. Gradio and Docker Spaces need a paid plan: PRO for personal accounts, Team or Enterprise for organizations. Free personal accounts may host up to 2 Gradio Spaces on ZeroGPU. CPU Basic is 2 vCPU, 16 GB RAM, sleeps when idle. Source: <https://huggingface.co/docs/hub/spaces-overview>.
- **Decision**: No try-it field in this feature (owner decision, spec Clarifications). The card shows three example texts with real model outputs instead (FR-018).
- **Options for the later feature**:
  - a ZeroGPU Gradio Space under the personal account (free, same Python code, outside the organization, small daily quota for anonymous visitors),
  - a static Space with in-browser inference (free, in the organization, the text never leaves the browser; needs an ONNX export, a JavaScript port of the post-processing and parity tests; about 560 MB download for an int8 XLM-R-large),
  - HF PRO or Team with a CPU Gradio Space (cash cost).

## R2. Model card content and validation

- **Decision**: The card is generated from `model.yaml`, the release record and the results files with one Jinja2 template ([contracts/model-card.md](contracts/model-card.md)). Metadata: `license`, `language`, `library_name` (set explicitly, the Hub no longer infers it), `pipeline_tag`, `base_model`, `tags`, `model-index` with the quality metrics. The gate validates the card in two ways: `huggingface_hub.ModelCard.validate()` and `POST https://huggingface.co/api/validate-yaml` with `{"content": <README>, "repoType": "model"}`. The gate treats **warnings as failures** (an unknown pipeline tag is only a warning there). SC-002.
- **Rationale**: The Hub's own validator is the reference for "passes without warnings". `model-index` is still the supported way to show custom metrics. The newer `.eval_results/*.yaml` format needs a registered benchmark dataset (beta, allow-list), so it does not fit our own benchmark.
- **Alternatives considered**: `.eval_results/` (rejected, see above). The auto-generated `PyTorchModelHubMixin` card (rejected: too thin; it is replaced by our card).

## R3. Versions on the Hub

- **Finding**: Model repos are git repos with branches and tags (`create_tag(..., exist_ok=False)` returns 409 if the tag exists). Tags can be deleted and re-created by anyone with write access. No immutable-tag feature was found (unverified that none exists). Users pin with `revision=` on `from_pretrained`, `hf_hub_download` or `snapshot_download`.
- **Decision**:
  - Each version is one commit on `main` of the public repo, tagged `v<version>`. `main` always holds the latest version (FR-008), so a version must be greater than every published version (gate rule 4).
  - Immutability (FR-007) is enforced by the pipeline (never `exist_ok=True`, never `delete_tag`) and made checkable: the release record stores the commit hash and card hash. `zoo audit` compares every published tag with its recorded commit and fails on a mismatch. The card tells users to pin the commit hash for strict reproducibility.
  - Deprecation is a new commit on `main` that only changes the card; files and tags stay.
- **Alternatives considered**: One repo per version (rejected: breaks "latest by default" and clutters the organization). Branch per version (rejected: tags are the standard way to pin).

## R4. Moving model files from training to release

- **Finding**: `copy_files("hf://src/...", "hf://dst/...")` copies Xet/LFS files server-side without downloading, but only within one storage region, and it is unverified whether it works from a private repo into a public one. File limit 500 GB. Free organizations get 100 GB private storage.
- **Decision**: The training machine runs `zoo stage`: it uploads the model directory to the private staging repo `<name>-staging` in one commit and writes `files[]` (sha256, size) and `staging.revision` into the release record. The release pipeline downloads the files at that revision on the runner, verifies the checksums, and uploads model files plus card to the public repo in **one** commit (`create_commit`), so a version is all-or-nothing (spec edge case).
- **Rationale**: One commit gives atomicity, and download-then-upload works regardless of visibility. The span model is about 2.2 GB, which fits on a GitHub runner (14 GB disk).
- **Alternatives considered**: Server-side `copy_files` (kept as a later optimization once tested; today it would need several commits or an unverified cross-visibility copy). A self-hosted runner on the Spark (rejected by the owner). Training inside CI (rejected: needs GPU).

## R5. Approval before publishing

- **Finding**: Required reviewers for GitHub environments are available only for public repositories on Free, Pro and Team plans. Environment secrets on Free are also public-repo only. The repository stays private during this feature.
- **Decision**: Two workflows.
  1. `release-verify` runs on a tag push `<name>/v<version>`: full gate, build, and a **preview** commit of the card and files to the staging repo branch `rc-v<version>`, so the owner reviews the card as the Hub renders it. The job summary links to it and shows the card hash.
  2. `release-publish` is started by hand (`workflow_dispatch` with `model`, `version` and a `confirm` field that must repeat `<name>/v<version>`). It does **not** rebuild. It publishes the reviewed preview itself: it checks that the preview was built from the tag commit (`build.json.tag_commit`), that the card's hash equals `build.json.card_sha256` and that the model files match the release record, reruns the gate rules that do not run the model, then copies the preview's card and model files to the public repo in one commit. Starting it is the approval.
- **Rationale**: Works on any plan and in a private repo, and the owner approves exactly the reviewed artifact. Not rebuilding avoids false refusals from tiny CPU floating-point differences in the example outputs that the card embeds. Once the repository is public, an environment with a required reviewer can be added on top without changing the flow.
- **Alternatives considered**: An environment with required reviewers (rejected: unavailable while private). Approving via a Hub pull request (rejected: harder to automate and to tie to the git tag).

## R6. Credentials

- **Finding**: Fine-grained HF tokens can be limited to specific repos or organizations. It is unverified whether a write token can be prevented from changing visibility. HF "Trusted Publishers" (OIDC from GitHub Actions) issue a one-hour token for one repo without a stored secret, but must be configured per repo with exact claims and need `huggingface_hub>=1.19`.
- **Decision**:
  - `HF_RELEASE_TOKEN` is a GitHub repository secret. It is a fine-grained token with write access to the `mobility-model-zoo` organization's repos, used only by `release-verify` and `release-publish`.
  - `HF_STAGING_TOKEN` lives on training machines only. It is a fine-grained token with write access to the **explicitly listed** staging repos; fine-grained tokens are scoped to named repos, not to name patterns, and creating repos needs organization rights. So staging repos are created by `zoo init-model` with the release token, and the owner adds each new staging repo to the staging token by hand (FR-012).
  - The pipeline never calls `update_repo_settings(private=False)` except in `zoo publish` for a non-sandbox repo created by itself, and refuses for sandbox models.
  - Tokens are passed through the environment and masked in logs; `zoo` never prints them.
- **Alternatives considered**: Trusted Publishers (deferred: per-repo setup for every new model repo; a good follow-up once the repo is public and models are stable).

## R7. Packaging custom PyTorch models

- **Finding**: `PyTorchModelHubMixin` saves `model.safetensors` and a `config.json` from the `__init__` arguments (download counting works via config.json). `from_pretrained` needs the class code, so a pip package must ship alongside. `trust_remote_code` applies only to transformers architectures. The inference widget does not work for such models (very likely, unverified). `token-classification` is an accepted `pipeline_tag`.
- **Decision**: Model classes live in the `mobility-model-zoo` Python package and use `PyTorchModelHubMixin`. The package's base install is inference-only (torch, transformers, huggingface_hub, safetensors, sentencepiece). The JTBD and release tools are extras (`[jtbd]`, `[release]`). The card's install line pins the git tag of the repository (`pip install "mobility-model-zoo @ git+https://github.com/mhabedank/mobility-model-zoo@<tag>"`). Publishing to PyPI is a later improvement.
- **Usage check (SC-004)**: The gate creates a fresh virtual environment, installs the package from the checkout at the tag commit (the repo is private during this feature), and runs the card's code block on CPU against the staged files. After the repo is public, the gate also checks that the install line's tag exists on GitHub.
- **Alternatives considered**: Custom transformers model with `trust_remote_code` (rejected for the span model: it is not a transformers architecture end to end, and users would execute repo code anyway). A standalone script in the model repo (rejected: duplicates code outside version control of the package).

## R8. Pipeline test model (FR-021)

- **Decision**: A tiny, deterministic PyTorch module `mobility_model_zoo.sandbox.PipelineTestModel` (a few KB, random weights from a fixed seed) in the `sandbox` topic, model name `sandbox-pipeline-tiny`. It is not a spike model and is never public. It takes text and returns output in a fixed JSON shape, so the usage check, the examples block and the card rendering are exercised. Its results files hold clearly labeled synthetic numbers that are valid against the schema and marked `synthetic: true`; the gate refuses `synthetic: true` outside the sandbox.
- **Rationale**: Exercises the whole pipeline in seconds, at no cost, without touching the constitution's spike rules.

## R9. Collections and overview

- **Decision**: One Hugging Face collection per topic in the organization (`create_collection`, `add_collection_item`), created on the topic's first publication; the slug is written to `topics.yaml`. `zoo/MODELS.md` is generated from all `model.yaml` and release records and committed by the publish run. Sandbox models appear in neither (FR-004, US3).

## R10. Rename

- **Decision**:
  - GitHub repository `mhabedank/mobility-llm` → `mhabedank/mobility-model-zoo` (`gh repo rename`; GitHub keeps redirects).
  - Python distribution `jtbd-pilot` → `mobility-model-zoo`. Import package `mobility_model_zoo`, with `mobility_model_zoo.productdev.jtbd` (the former `jtbd_pilot`, moved with `git mv` and imports rewritten), `mobility_model_zoo.release` (new) and `mobility_model_zoo.sandbox` (new). The proof-of-concept CLI `pilot` is renamed to `jtbd` without an alias (owner decision: the PoC phase is over); configs move to `configs/productdev/jtbd/`; open 001 tasks are rewritten to the new commands. The frozen benchmark keeps the identifier `pilot-v1`. A second CLI `zoo` handles releases.
  - The 001 and 002 documents keep their historical paths; a note at the top of each points to the new package path.
  - Hugging Face organization `mobility-model-zoo` (name available on 2026-10-01; letters, digits and single hyphens are allowed).
- **Rationale**: One tool per task, not per model: every model of a task must use the same benchmark and harness (Principle VIII). A cyber security or IoT task will likely need a different pipeline (no frontier labeling), so shared code is extracted only when a second task exists. One package keeps the shared code (schemas, scoring) importable by later topics. Moving instead of re-creating keeps git history.

## R11. Git history check before the repository goes public (FR-003c)

- **Decision**: `zoo history-check` scans every commit on every ref: (a) paths: anything under `data/`, `.env`, `*.jsonl`, `*.safetensors`, `*.pt`, snapshot and raw-response directories; (b) content: patterns for OpenRouter, Anthropic, OpenAI and Hugging Face keys and private keys, using `gitleaks` with its default rules plus these path rules. It prints offending commits and exits 1. Running it is a manual pre-step of feature 004, not of every release. If it finds something, history is rewritten before the repository goes public.
- **Alternatives considered**: `gitleaks` alone (rejected: it finds secrets, not data files). A fresh public repository without history (kept as fallback if rewriting is too invasive).

## R12. Runner capacity

- **Finding**: GitHub-hosted `ubuntu-latest` for private repositories: 2 vCPU, 7 GB RAM, 14 GB SSD; Free plan includes 2,000 minutes/month for private repositories (unverified for 2026).
- **Decision**: Enough for the span model (2.2 GB download, CPU usage check of a few seconds). The gate caches the CPU-only torch wheel. Expected run time: verify about 10 minutes, publish about 10 minutes, well within SC-007 (30 minutes).

## R13. Constitution amendment (FR-002)

- **Decision**: Version 1.3.0 (MINOR). The preamble and "Project Scope" describe the zoo. Principles I, II, VII and X and the JTBD scope apply to the `productdev` JTBD models; III, IV, V, VI, VIII, IX, Resources, Spikes and Gates apply zoo-wide, with wording made task-neutral where it names JTBD (for example "benchmark labeling models" stays, "extraction" becomes "the model's task"). Principle IX gains: published versions are immutable; publication only through the release pipeline with owner approval; datasets are never published. A new section states the task/release split: each task has its own build-and-measure tooling shared by all its models; every model, whatever its task, is released through the common release record and gate. No principle is removed, so no MAJOR bump.
- **Alternatives considered**: One constitution per topic (rejected: shared rules would drift).
