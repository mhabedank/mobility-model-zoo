# Adding a topic or a model to the zoo

Every model in the zoo is released the same way, whatever its task (constitution 1.3.0, "Tasks and Releases"). How a model is built and measured belongs to its task: for the JTBD extraction models that is the `jtbd` tool. The release tool is `zoo`. Its commands, exit codes and the 14 gate rules are in [specs/003-model-zoo-hf-release/contracts/cli.md](../specs/003-model-zoo-hf-release/contracts/cli.md).

## Names

A model is named `<name>-<variant>` in lowercase with hyphens, for example `scout-large`: a short, memorable English name for the model family and a size or variant (constitution 1.4.0). The topic and the task are fields in `model.yaml`; they become Hugging Face tags, and the topic's collection (`hf_collection` in `zoo/topics.yaml`) lists the model. The name is used for the Hugging Face repository, the release tag and the release record. It **MUST NOT change after the first publication**: renaming would break every link and every pinned download.

**Usage class** (constitution 2.1.0): every `model.yaml` declares `usage_class`, one of `commercial`, `commercial-share-alike`, `non-commercial`, `non-commercial-share-alike`, before training. Restrictions of every input carry over: a training dataset, base model, teacher or run-time model that allows only non-commercial use makes the model non-commercial; share-alike data makes it share-alike. A non-commercial model is named `<name>-<variant>-nc` (for example `scout-large-nc`, `variant: large`), is released under `CC-BY-NC-4.0` (or `CC-BY-NC-SA-4.0` with share-alike inputs) and says so on its card and website page. The class never changes between versions; a different class is a new model with a new name. `uv run zoo compliance usage` shows the declared and derived class of every model. Licences and their attributes live in `compliance/lists/licence-allowlist.yaml`; base models and other third-party models are registered in `compliance/third-party-models.yaml` with pinned revisions and the licences of the training data their model cards name.

## Add a topic

Where each part of a topic or task goes: [layout.md](layout.md).

Add an entry to `zoo/topics.yaml`:

```yaml
- id: iot                 # ^[a-z][a-z0-9]*(-[a-z0-9]+)*$, at most 24 characters, never changes
  title: Internet of Things
  description: One or two sentences.
  hf_collection: null     # filled in by the first publication
```

Then create `topics/<id>/README.md` and `topics/<id>/compliance/datasets.yaml` (`zoo validate --all` requires both). Nothing else changes. Existing models are not touched.

## Add a task

Write a task document `topics/<topic>/tasks/<task>.md` before the first model: scope in and out, the reference (dataset labels or model consensus), the benchmark and its version, the metrics with the headline, the tool, the framework and why, the riskiest assumption and the hardware budget. Examples: [can-ids](../topics/security/tasks/can-ids.md), [sound-anomaly](../topics/condition-monitoring/tasks/sound-anomaly.md). Declare every dataset the task uses in `topics/<topic>/compliance/datasets.yaml` (`uv run zoo data validate`); training refuses undeclared datasets and datasets that are not `training_allowed`.

## Add a model

1. Create `zoo/models/<name>/model.yaml` following [model.schema.json](../specs/005-topic-layout-security-merge/contracts/model.schema.json). `card.how_to_run` must contain the placeholders `{repo_id}`, `{revision}` and, for Python models, `{text}`, for example:

   ```python
   from mobility_model_zoo.<topic>.<module> import MyModel

   model = MyModel.from_pretrained("{repo_id}", revision="{revision}")
   print(model.predict({text}))
   ```

   The card fills in the public repository, the version tag and the first example text. The release gate fills in the staging repository and revision and runs the code once per example text, in a clean environment on CPU.

   Microcontroller models set `runtime: mcu`, may leave `languages` empty and need `card.device_usage`, a C snippet that calls the model on the device (see [picket-mlp](../zoo/models/picket-mlp/model.yaml)). `how_to_run` then shows the Python host reference.
2. Put at least three example texts without personal data in `zoo/models/<name>/examples/*.txt` (microcontroller models: `examples/*.json` with `input`, `expected` and `source`, see below). Do not use benchmark chunks. Record where each example comes from in `zoo/models/<name>/examples/SOURCES.yaml` (`source: synthetic`, or a source whose register record allows redistribution; check C-U4).
3. Write the website text in `zoo/models/<name>/site.yaml` ([docs/website.md](website.md)): tagline, audience, three to five differentiators and the quickstart example. Numbers only as `{metric:<kind>.<name>}` placeholders. Gate rule 17 checks it before every publish; sandbox models do not need it. A new output format also needs `zoo/formats/<format>.yaml`.
4. Create the private staging repository (owner, with `HF_RELEASE_TOKEN`), then add it to the repository list of `HF_STAGING_TOKEN` on the Hub:

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
   - Sources from a declared dataset carry `dataset: <id>`; the gate checks the declaration and the licence. Data under a non-commercial licence may train non-commercial models only (declaration `training_allowed` with `commercial_use: false`).
   - `usage` holds the release's usage class, its licence and the inputs that restrict it. The gate derives it from the inputs and prints the expected block when it is missing or differs (check C-K5); copy that block into the record.
   - `evaluation.reference_kind` is `ground_truth` when quality is measured against dataset labels (then "accuracy" is allowed) and `model_consensus` (default) for agreement with reference models.
   - Microcontroller models: `performance.budget` is `{ram_kb, flash_kb, target}`. Measure on the bench with `uv run edge measure <model>.npz -b <board> --out performance.json`; every metric records the hardware and whether it came from a real board, an emulator or the simulator. Gate rule 15 needs `latency_us`, `flash_kb` and `ram_kb`, and a real-board latency unless the version is experimental. Examples are `examples/*.json` with an int8 `input`, the `expected` output and a `source` (`synthetic` or a dataset whose declaration allows redistribution); the gate runs them bit-exactly on the host reference.
3. Complete the compliance evidence (feature 006, gate rule 16):
   - every training source and dataset has a record in `topics/<topic>/compliance/` (`uv run zoo compliance bootstrap-sources …` proposes them), and every labeling route is in `compliance/providers.yaml`;
   - write `zoo/models/<name>/releases/<version>.compliance.yaml` (AI Act classification, licences, provenance, scans; see [the data model](../specs/006-compliance-harness/data-model.md));
   - render the documents and scan everything that will be published:

   ```bash
   uv run zoo compliance render
   uv run zoo compliance scan-publish --model <name> --version <version>
   uv run zoo compliance signoff --model <name> --version <version>   # the owner, after reviewing
   ```

4. Check offline, then commit:

   ```bash
   uv run zoo check <name> <version> --offline
   git commit -am "Release record for <name> <version>"
   ```

5. Tag the commit on `main` and push the tag. This starts `release-verify`: the full gate, the build and a preview of the card on the staging branch `rc-v<version>`.

   ```bash
   git tag <name>/v<version> && git push origin <name>/v<version>
   ```

6. Review the preview linked in the job summary.
7. Approve by starting the `release-publish` workflow with `model=<name>`, `version=<version>` and `confirm=<name>/v<version>`. It publishes exactly the reviewed preview as one tagged commit, adds the model to its topic collection and commits the updated release record and `zoo/MODELS.md`.

A published version never changes. A fix is a new version. A broken version is deprecated (`release-publish` with `action: deprecate`), not deleted.

## The sandbox test model

`sandbox-pipeline-tiny` (topic `sandbox`) tests the pipeline. Its recipe is `src/mobility_model_zoo/sandbox/build_test_model.py` with seed 0, which always produces the same files:

```bash
uv run python -m mobility_model_zoo.sandbox.build_test_model --out /tmp/pipeline-tiny
```

Sandbox models are published only to private repositories and never appear in `zoo/MODELS.md` or a collection.
