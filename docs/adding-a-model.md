# Adding a topic or a model to the zoo

Every model in the zoo is released the same way, whatever its task (constitution 1.3.0, "Tasks and Releases"). How a model is built and measured belongs to its task: for the JTBD extraction models that is the `jtbd` tool. The release tool is `zoo`. Its commands, exit codes and the 14 gate rules are in [specs/003-model-zoo-hf-release/contracts/cli.md](../specs/003-model-zoo-hf-release/contracts/cli.md).

## Names

A model is named `<name>-<variant>` in lowercase with hyphens, for example `scout-large`: a short, memorable English name for the model family and a size or variant (constitution 1.4.0). The topic and the task are fields in `model.yaml`; they become Hugging Face tags, and the topic's collection (`hf_collection` in `zoo/topics.yaml`) lists the model. The name is used for the Hugging Face repository, the release tag and the release record. It **MUST NOT change after the first publication**: renaming would break every link and every pinned download.

## Add a topic

Add an entry to `zoo/topics.yaml`:

```yaml
- id: iot                 # short form used in model names, ^[a-z][a-z0-9]{1,15}$, never changes
  title: Internet of Things
  description: One or two sentences.
  hf_collection: null     # filled in by the first publication
```

Nothing else changes. Existing models are not touched.

## Add a model

1. Create `zoo/models/<name>/model.yaml` following [model.schema.json](../specs/003-model-zoo-hf-release/contracts/model.schema.json). `card.how_to_run` must contain the placeholders `{repo_id}`, `{revision}` and `{text}`, for example:

   ```python
   from mobility_model_zoo.<topic>.<module> import MyModel

   model = MyModel.from_pretrained("{repo_id}", revision="{revision}")
   print(model.predict({text}))
   ```

   The card fills in the public repository, the version tag and the first example text. The release gate fills in the staging repository and revision and runs the code once per example text, in a clean environment on CPU.
2. Put at least three example texts without personal data in `zoo/models/<name>/examples/*.txt`. Do not use benchmark chunks.
3. Create the private staging repository (owner, with `HF_RELEASE_TOKEN`), then add it to the repository list of `HF_STAGING_TOKEN` on the Hub:

   ```bash
   uv run zoo init-model <name>
   ```

## Release a version

1. Train the model with its task's tool and recipe. On the training machine, with `HF_STAGING_TOKEN` in `.env`:

   ```bash
   uv run zoo stage <name> <version> --from <directory with the model files>
   ```

   This uploads the files in one commit and writes `files[]` and `staging.revision` into `zoo/models/<name>/releases/<version>.yaml`.
2. Fill in the rest of the release record: `changes`, `output_format_version`, `recipe` (the commit and the paths of the training configuration and the recipe document), `provenance`, `evaluation` and `performance`. Copy the numbers into `results/<version>/quality.json` and `performance.json`; the card shows only numbers from these files.
3. Check offline, then commit:

   ```bash
   uv run zoo check <name> <version> --offline
   git commit -am "Release record for <name> <version>"
   ```

4. Tag the commit on `main` and push the tag. This starts `release-verify`: the full gate, the build and a preview of the card on the staging branch `rc-v<version>`.

   ```bash
   git tag <name>/v<version> && git push origin <name>/v<version>
   ```

5. Review the preview linked in the job summary.
6. Approve by starting the `release-publish` workflow with `model=<name>`, `version=<version>` and `confirm=<name>/v<version>`. It publishes exactly the reviewed preview as one tagged commit, adds the model to its topic collection and commits the updated release record and `zoo/MODELS.md`.

A published version never changes. A fix is a new version. A broken version is deprecated (`release-publish` with `action: deprecate`), not deleted.

## The sandbox test model

`sandbox-pipeline-tiny` (topic `sandbox`) tests the pipeline. Its recipe is `src/mobility_model_zoo/sandbox/build_test_model.py` with seed 0, which always produces the same files:

```bash
uv run python -m mobility_model_zoo.sandbox.build_test_model --out /tmp/pipeline-tiny
```

Sandbox models are published only to private repositories and never appear in `zoo/MODELS.md` or a collection.
