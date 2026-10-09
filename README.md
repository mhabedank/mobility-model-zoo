# mobility-model-zoo

A collection of small, fast machine learning models for mobility, grouped by topic. Every model runs locally, is versioned, and is published on Hugging Face with a model card that says what it does, how good it is (and measured against what), how fast it is on which hardware, and where it fails.

- Website: [mhabedank.github.io/mobility-model-zoo](https://mhabedank.github.io/mobility-model-zoo/)
- Models and their latest versions: [zoo/MODELS.md](zoo/MODELS.md)
- On Hugging Face: [huggingface.co/mobility-model-zoo](https://huggingface.co/mobility-model-zoo)
- Constitution (the project rules): [.specify/memory/constitution.md](.specify/memory/constitution.md)
- Repository layout (one folder per topic): [docs/layout.md](docs/layout.md)
- License: [Apache-2.0](LICENSE); third-party notices: [NOTICE](NOTICE), [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
- Privacy notice, copyright policy, security contact: [PRIVACY.md](PRIVACY.md), [COPYRIGHT_POLICY.md](COPYRIGHT_POLICY.md), [SECURITY.md](SECURITY.md)

## Topics

| Topic | Title | Collection | Tasks and models |
|-------|-------|------------|------------------|
| `productdev` | Product development | [Product development](https://huggingface.co/collections/mobility-model-zoo/product-development-6ac6269f0468c62fefb874a8) | `jtbd`: [`scout-large`](https://huggingface.co/mobility-model-zoo/scout-large) |
| `security` | Automotive security | not yet published | `can-ids`: `picket-forest`, `picket-mlp` (registered, not released) |
| `condition-monitoring` | Condition monitoring | not yet published | `sound-anomaly`: `hum-fan`; `activity`: `pace-cnn` (registered, not released) |

Topics are listed in [zoo/topics.yaml](zoo/topics.yaml); one topic is one Hugging Face collection and one folder `topics/<topic>/` (research, reports, recipes, task documents, compliance records). A test topic `sandbox` holds pipeline test models, which are never public.

## Repository layout

Package code lives in `src/mobility_model_zoo/` (one subpackage per topic plus the shared `edge`, `datasets`, `compliance` and `release` packages), configurations in `configs/<topic>/`, firmware in `firmware/`, the hardware-in-the-loop bench inventory in `hil/`, and everything else of a topic in `topics/<topic>/`. Details: [docs/layout.md](docs/layout.md).

## How the zoo is organized

- **Building and measuring belongs to a task.** Each task has one tool, shared by every model of that task, so that all of them are measured with the same benchmark and harness. For JTBD extraction this is `jtbd`, for CAN intrusion detection `security can-ids`, for the condition-monitoring tasks `condmon` (below). Each task document in `topics/<topic>/tasks/` names its reference, benchmark, metrics, tools and hardware budget.
- **Releasing is the same for every model.** Each version has a release record in `zoo/models/<name>/releases/<version>.yaml`. The release tool `zoo` checks it with 16 gate rules (rule 15 for microcontroller models, rule 16 for compliance), builds the model card and publishes through GitHub Actions:

  1. `zoo stage` uploads the trained files to a private staging repository.
  2. A tag `<model>/v<version>` runs `release-verify`: the gate, the build and a preview of the card.
  3. The owner reviews the preview and approves by starting `release-publish`, which publishes exactly that preview as one tagged, immutable version.

  Step-by-step guide: [docs/adding-a-model.md](docs/adding-a-model.md). Commands and gate rules: [specs/003-model-zoo-hf-release/contracts/cli.md](specs/003-model-zoo-hf-release/contracts/cli.md).
- Model names follow `<name>-<variant>`, for example `scout-large`; topic and task are tags, and each topic has a Hugging Face collection. Names never change after the first publication.
- Datasets never go into git. They are declared per topic in `topics/<topic>/compliance/datasets.yaml` (licence, permitted use, redistribution, retention), downloaded with `zoo data download` into `$MMZ_DATA` (default `~/.cache/mobility-model-zoo/datasets`) and used for training only when declared `training_allowed`. No dataset or training text is published unless its licence and terms allow redistribution; models, methods, prompts and evaluation results are published.
- Microcontroller models (`runtime: mcu`) run on the zoo's int8 engine or as emlearn C code; the hardware-in-the-loop bench (`edge`) measures them on simulated, emulated and real boards ([docs/edge/hil-bench.md](docs/edge/hil-bench.md)).

## Compliance

Training data, published material and the naming of third parties are governed by a compliance register and fail-closed checks (feature 006, not legal advice):

- **Register:** `compliance/` (controller, labeling routes and their providers, owner decisions, waivers, requests, suppression list, legal watch list) and `topics/<topic>/compliance/` (source classes with their legitimate-interest assessment, one record per source or dataset with licence, attribution, opt-out signals, personal data and retention). Release evidence lives next to each release record (`<version>.compliance.yaml`, AI Act classification, training data summary, publication scan).
- **Checks:** `jtbd source fetch` honours robots.txt (including AI crawler agents), TDM reservations, `noai` and ai.txt; chunking refuses sources without a record and excludes special categories; labeling re-scans every text for personal identifiers and sends only through approved, pinned routes; training refuses licences and teachers that do not allow it; `zoo check` runs gate rule 16 (publication scan, card lint, licence files, repository hygiene, owner sign-off). The check ids are listed in [specs/006-compliance-harness/contracts/checks.md](specs/006-compliance-harness/contracts/checks.md).
- **Generated documents:** `uv run zoo compliance render` writes the privacy notice, copyright policy, security policy, notices, REUSE files, the record of processing and the legitimate-interest and impact assessment ([docs/compliance/](docs/compliance/)) from the register; CI fails when a committed copy differs (`uv run zoo compliance check --ci`).
- **Requests:** objections, erasure, access and takedown requests are handled as described in [docs/compliance/requests.md](docs/compliance/requests.md).

## Setup

Prerequisites: Python 3.12 and [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync --extra jtbd --extra release --extra edge   # what CI installs
uv run pytest
uv run zoo --help
```

Extras: `jtbd` (JTBD measurement chain), `release` (release tool), `edge` (bench, int8 engine, datasets), `edge-hw` (PlatformIO, esptool, pytest-xdist for real boards), `edge-train` (TensorFlow, scikit-learn, emlearn for training the edge models), `labeling-api` (Anthropic API backend). A model user only needs the install line on each model card. Credentials and where they live: [docs/credentials.md](docs/credentials.md).

Quick commands per topic:

```bash
uv run jtbd doctor                              # productdev: JTBD measurement chain
uv run zoo data list                            # declared datasets of all topics
uv run security can-ids --help                  # security: picket-forest, picket-mlp
uv run condmon sound-anomaly --help             # condition-monitoring: hum-fan
uv run condmon activity --help                  # condition-monitoring: pace-cnn
uv run edge build -t native && uv run edge run -b sim   # HIL bench on the host simulator
```

## Topic: product development, task: JTBD extraction (`jtbd`)

**Published model: [`scout-large`](https://huggingface.co/mobility-model-zoo/scout-large)** (v0.1.0, experimental). It finds jobs, pains and gains in German and English mobility texts and quotes them verbatim, with actor type, evidence type and evidence scope. On the frozen benchmark `pilot-v2` it reaches a comparison composite of 0.72 (best zero-shot small model 0.67); it reads a 9,240-character interview in 8.1 s on 4 CPU cores, 0.84 s on a MacBook M3 Pro GPU and 0.12 s on a DGX Spark. Usage, quality, speed and limits: the [model card](https://huggingface.co/mobility-model-zoo/scout-large); how it was built: [topics/productdev/recipes/scout-large.md](topics/productdev/recipes/scout-large.md); collection: [Product development](https://huggingface.co/collections/mobility-model-zoo/product-development-6ac6269f0468c62fefb874a8).

```python
from mobility_model_zoo.productdev.jtbd.span import SpanExtractor

model = SpanExtractor.from_pretrained("mobility-model-zoo/scout-large", revision="v0.1.0")
print(model.extract("Nach 22 Uhr fährt kein Bus mehr, also nehme ich das Auto."))
```

Build commands (feature 004): `jtbd span …` (data-check, build-rows, freeze-data, train, tune, label, select, results, release-check, pareto, record) and `topics/productdev/scripts/spark/train_span.sh` for training on the DGX Spark. Pilot report: [topics/productdev/reports/pilot-v2/report.md](topics/productdev/reports/pilot-v2/report.md).

The `jtbd` tool (called `pilot` during the proof of concept) runs the agreement pilot and the measurement chain for the JTBD extraction models: fetch sources once, build and redact chunks, freeze guideline and criteria, label with reference models, teachers and small models, check, match, build the consensus, score, measure speed, decide and report. Code: `src/mobility_model_zoo/productdev/jtbd/`. Configuration: `configs/productdev/jtbd/`.

- Pilot spec, plan and tasks: [specs/001-jtbd-extraction-pilot/](specs/001-jtbd-extraction-pilot/)
- CLI contract: [specs/001-jtbd-extraction-pilot/contracts/cli.md](specs/001-jtbd-extraction-pilot/contracts/cli.md) (commands are now `jtbd ...`)

Additional prerequisites for labeling and measurement:

- The `claude` CLI, logged in with the Claude subscription (Claude reference labeler)
- An OpenRouter key with a **hard spending limit** (GPT reference labeler and teachers)
- Ollama on the DGX Spark (teacher candidates, baseline quality runs)
- For performance runs only: a reference machine with 8 GB RAM, 4 vCPU and no GPU (for 0.1.0 a temporary Railway service, `topics/productdev/deploy/railway-perf/`)

```bash
cp .env.example .env   # then fill in the keys and hosts
uv run jtbd doctor
```

## Topics: automotive security and condition monitoring (edge models)

Merged from the former repository `mhabedank/mobility-security-ml` with its history (feature 005; merge log: [topics/security/research/merge-log.md](topics/security/research/merge-log.md)).

- **`can-ids`** ([task document](topics/security/tasks/can-ids.md)): `picket-forest` (random forest exported to C with emlearn, streaming features in `firmware/components/can_features/`, device build in `firmware/picket-forest/`) and `picket-mlp` (int8 MLP). Tool: `uv run security can-ids frames|forest …|mlp train|evaluate|freeze`.
- **`sound-anomaly`** ([task document](topics/condition-monitoring/tasks/sound-anomaly.md)): `hum-fan`, an int8 autoencoder on MIMII fan sounds. **`activity`** ([task document](topics/condition-monitoring/tasks/activity.md)): `pace-cnn`, an int8 CNN on UCI HAR. Tool: `uv run condmon sound-anomaly|activity train|evaluate|freeze`.
- Training reads the task configs (`configs/security/…`, `configs/condition-monitoring/…`, `--config`) and writes to `$MMZ_DATA/derived/<model>/`, never into the repository. `edge measure MODEL.npz -b BOARD` records latency, flash and RAM with the board and whether it was a real board, an emulator or the simulator.
- The research of the former repository is in `topics/security/research/`; its results are kept in `topics/*/reports/<model>/` as pre-zoo research results, not benchmark results.

## Spikes (not released)

The spike models below are technical spikes (feature 002). Their results are spike results, not benchmark results, and spike models are never published (constitution, "Technical Spikes"). The fast span model below is history: it was rebuilt without spike data as the published production model [`scout-large`](https://huggingface.co/mobility-model-zoo/scout-large) (feature 004).

### Try the spike model locally

The best student from the technical spike (feature 002) runs on a Mac with Apple silicon: Qwen3-4B-Instruct-2507 plus the LoRA adapter `spike-v3b`, trained on 200 training examples labeled by the four-teacher ensemble, merged and converted to MLX 8-bit (4.3 GB). It is a **spike result**, not a benchmark result.

```bash
bash topics/productdev/spike/build_local_model.sh          # once: adapter from the Spark, merge, convert -> data/models/spike-v3b-mlx-8bit
uv run --with mlx-lm==0.31.3 python topics/productdev/spike/try_model.py "Der Bus fährt nur zweimal am Tag ..."
uv run --with mlx-lm==0.31.3 python topics/productdev/spike/try_model.py --file text.txt        # or --json for the raw output
uv run --with mlx-lm==0.31.3 python topics/productdev/spike/eval_local_model.py                 # scores on the 35 spike evaluation chunks
```

For a text it prints relevance and each job, pain or gain with actor, evidence and quote, and marks quotes that are not verbatim. On the 35 spike evaluation chunks (agreement with the Claude reference, 2026-10-01) it reaches composite 0.673. For comparison: the same model under vLLM scored 0.639, the untrained base 0.54–0.56 and the teachers 0.75–0.80. It is schema-valid on every chunk; 80% of its quotes are verbatim, and it takes about 50 s per chunk on an M3 Pro. The small model sometimes loops on one quote: generation then stops at the third repeat, the complete items are kept and duplicates are removed, and the output says so in a note.

### Fast span model (encoder, under 1 s per interview)

A second spike architecture for speed: an encoder (XLM-RoBERTa-large, 560M parameters) splits the text into sentences and clauses and classifies each one as job, pain, gain or no item, plus actor type, evidence type and evidence scope. It reads a text in one pass of 512-token windows instead of generating JSON, so quotes are always verbatim and output cannot break. It does **not** produce the free-text actor or the English statement. Trained on the four-teacher ensemble labels plus each teacher's own labels of the 180 spike train chunks (`topics/productdev/spike/train_span.py`, on the DGX Spark with `topics/productdev/spike/train_span_spark.sh`).

```bash
uv run --with torch --with transformers --with sentencepiece --with protobuf \
    python topics/productdev/spike/try_span.py --file data/interviews/fiktiv-interview-fussgaenger-berlin.txt   # --json for JSON
uv run --with torch --with transformers --with sentencepiece --with protobuf \
    python topics/productdev/spike/eval_span.py --model data/models/span-lt-fixed                               # 35 spike chunks
```

The default model is `data/models/span-lt-fixed`. The fictional pedestrian interview (9,300 characters) takes 0.71 s on an M3 Pro GPU (MPS) and finds 46 items; with loading the model, about 5 s. The run peaks at 2.3 GB of memory, so a 16 GB Mac is plenty; on the CPU alone (`--device cpu`) the interview takes 1.9 s. On the 35 spike evaluation chunks (agreement with the Claude reference, 2026-10-01) it reaches composite 0.60 (0.63 without relevance, where only 2 of the 35 chunks are irrelevant). It finds items better than the fine-tuned LLM v3b (item matching 0.62 vs 0.53) and is on par for kind (0.65 vs 0.57), but classifies evidence type and actor type worse (0.66 vs 0.80, 0.59 vs 0.69). A variant whose heads also see the neighbouring units (`--context`) was not better. Thresholds were chosen on 20 held-out train chunks, never on the evaluation chunks. Ollama cannot run this kind of model (it serves generative LLMs only); it runs with PyTorch.

To avoid loading the model for every text, run it as a local server (loads once, about 5 s; binds to 127.0.0.1):

```bash
uv run --with torch --with transformers --with sentencepiece --with protobuf python topics/productdev/spike/serve_span.py   # port 8877
curl -s 127.0.0.1:8877/extract --data-binary @data/interviews/fiktiv-interview-fussgaenger-berlin.txt     # JSON
curl -s '127.0.0.1:8877/extract?format=text' --data-binary 'Der Bus fährt nur zweimal am Tag.'           # readable
curl -s 127.0.0.1:8877/extract -H 'Content-Type: application/json' -d '{"text": "..."}'
```

Each request then takes the analysis time only: 0.72 s for the interview, about 0.12 s for a short text.

## Data handling (JTBD task)

- `data/` holds snapshots, chunks, raw model responses and analysis. It is gitignored and is **never** committed or published (Principle VI).
- Each source is fetched **once** and stored as a complete raw snapshot. Its `source.yaml` records the origin, license, legal basis, permitted uses (`benchmark_only` or `training_allowed`) and `retention_until`. `jtbd source fetch` refuses a second fetch of the same canonical URL unless it is given `--update --reason`.
- Usernames and direct identifiers are removed before labeling (`jtbd corpus redact`, then `jtbd corpus pii-review` with a local model instead of a manual review, then `jtbd corpus redact-check`).
- Reddit content comes only through the official Data API, is always `benchmark_only`, and is fetched only once the Reddit platform terms are recorded as allowing it (check C-I7). Arctic Shift is used only to find thread IDs.
- When a snapshot's `retention_until` date has passed (`uv run zoo compliance retention`), delete it with `uv run zoo compliance delete --snapshot <id> --reason …`, which logs the hashes and marks the source record. The benchmark manifest in `topics/productdev/benchmarks/` keeps only hashes, never text.
- Raw model responses under `data/runs/*/raw/` are never edited.
