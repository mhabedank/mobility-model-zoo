# CLI contract: pace-cnn first release

Commands this feature adds or changes. Exit codes follow the existing tools: 0 ok, 2 usage error, 3 refused (frozen or pre-registration violated), 4 check failed, 5 not implemented (removed by this feature for `activity`).

## `uv run condmon activity freeze`

Builds the `uci-har-v1` manifest ([records.md](records.md#benchmark-manifest)) from the downloaded dataset and writes `topics/condition-monitoring/benchmarks/uci-har-v1/manifest.json`.

| Case | Result |
|---|---|
| No manifest yet | writes it, exit 0 |
| Manifest exists, content identical (ignoring `frozen_at`) | no change, exit 0 |
| Manifest exists, content differs | refuses, prints the differing fields, exit 3 |
| Dataset missing or licence check fails | exit 4, nothing written |

## `uv run condmon activity train [--seed N] [--out DIR] [--download]`

Changes:

- **Refusals (exit 3)**: no frozen manifest; the criteria file untracked or modified; or `--seed` not one of the criteria record's seeds.
- **Data**: uses the manifest's splits and normalisation (subject-wise validation), and enables op determinism.
- **Interpreter check**: runs over all test windows.
- **Output**: writes to `$MMZ_DATA/derived/pace-cnn/seed-<N>/` (default `--out`), with the run report fields of [data-model.md](../data-model.md#run-report-extends-pace-cnnreportjson).
- `--epochs` is removed: epochs come from the recipe config, which `load_config` already checks.

## `uv run condmon activity evaluate [--version 0.1.0]`

Requires the five runs of the criteria record's seeds and the frozen manifest. It writes:

- `topics/condition-monitoring/reports/pace-cnn/<version>/{evaluation.json,verdict.json,README.md}`;
- `zoo/models/pace-cnn/results/<version>/quality.json`.

It prints the derived status and every missed criterion. If the device results already exist, it reads `performance.json` to decide the budget criteria. Without them, the budget criteria stay `not measured`.

Exits:

- 0 when the report is written, whatever the status;
- 3 when a run used another manifest or criteria version than the current ones;
- 4 when the deterministic check reports a mismatch (the release is blocked).

## `uv run condmon activity reproduce`

Retrains the candidate seed into a temporary folder and compares it with the stored candidate. It prints identical or the metric deviation, and writes the result into `evaluation.json` (`reproduction`). Exit 0 in both cases; the deviation is reported, not hidden.

## `uv run condmon activity export --version 0.1.0 --out DIR`

Writes the upload folder of [release-files.md](release-files.md) from the candidate run:

- the model files `.npz` and `.tflite`;
- `c/`, `config.json`, at least three synthetic `examples/*.json`;
- `sbom.cdx.json`.

It refuses (exit 4) if any file outside the allow-list would be written or if an example does not reproduce bit-exactly on the host reference.

## `uv run edge measure NPZ -b BOARD --footprint model --model-version V --out FILE`

`--footprint model` (new; the default stays `image`) reports flash and RAM of the model as defined in [records.md](records.md#model-footprint), from the symbol sizes of the ELF built for the board's target. It also reports the whole-image values under `*_image` names. Latency and origin are unchanged.

## `uv run edge performance --model pace-cnn --version 0.1.0 --reference FILE [--extra FILE ...]`

Merges `edge measure` outputs into `zoo/models/pace-cnn/results/0.1.0/performance.json`:

- `--reference` gives the plain metric names;
- each `--extra` gives suffixed names (`latency_us_<board>`).

It refuses (exit 4) if the reference file's origin is not `real_board` and `--allow-substitute` is not given. With `--allow-substitute`, the plain rows carry the substitute's origin.

## `uv run zoo init-model pace-cnn` (changed)

It also ensures the topic's Hugging Face collection:

- if `hf_collection` is null, it creates a private collection from the topic title and description and writes the slug into `zoo/topics.yaml`;
- if the collection exists, nothing changes.

## `uv run zoo publish` (changed)

When it adds a model to a private topic collection, it makes the collection public.

## HIL bench (changed behaviour)

`MMZ_EDGE_MODELS=$MMZ_DATA/derived/pace-cnn/seed-0/pace-cnn.npz uv run edge run -b <board>` runs the full suite with pace-cnn:

- **catalogue**: the tests use the same catalogue as their parameters;
- **eval file**: `pace-cnn.eval.npz` is found next to the `.npz`;
- **serial buffer**: the receive buffer is large enough for a 128 × 9 INFER line;
- **latency budget**: `hil/targets.yaml` gives esp32 the budget `pace-cnn: 100000` µs.
