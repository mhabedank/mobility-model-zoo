# mobility-model-zoo

A collection of small, fast machine learning models for mobility, grouped by topic. Every model runs locally, is versioned, and is published on Hugging Face with a model card that says what it does, how good it is (and measured against what), how fast it is on which hardware, and where it fails.

- Models and their latest versions: [zoo/MODELS.md](zoo/MODELS.md)
- On Hugging Face: [huggingface.co/mobility-model-zoo](https://huggingface.co/mobility-model-zoo)
- Constitution (the project rules): [.specify/memory/constitution.md](.specify/memory/constitution.md)
- License: [Apache-2.0](LICENSE)

## Topics

| Topic | Short form | What it covers |
|-------|------------|----------------|
| Product development | `productdev` | Product discovery in mobility. First task: extracting jobs-to-be-done, pains and gains with verbatim evidence from texts (`jtbd`). |

Later topics, for example cyber security or IoT, are added as a new entry in [zoo/topics.yaml](zoo/topics.yaml). Existing models do not change. A test topic `sandbox` holds pipeline test models, which are never public.

## How the zoo is organized

- **Building and measuring belongs to a task.** Each task has one tool, shared by every model of that task, so that all of them are measured with the same benchmark and harness. For JTBD extraction this is `jtbd` (below).
- **Releasing is the same for every model.** Each version has a release record in `zoo/models/<name>/releases/<version>.yaml`. The release tool `zoo` checks it with 14 gate rules, builds the model card and publishes through GitHub Actions:

  1. `zoo stage` uploads the trained files to a private staging repository.
  2. A tag `<model>/v<version>` runs `release-verify`: the gate, the build and a preview of the card.
  3. The owner reviews the preview and approves by starting `release-publish`, which publishes exactly that preview as one tagged, immutable version.

  Step-by-step guide: [docs/adding-a-model.md](docs/adding-a-model.md). Commands and gate rules: [specs/003-model-zoo-hf-release/contracts/cli.md](specs/003-model-zoo-hf-release/contracts/cli.md).
- Model names follow `<name>-<variant>`, for example `scout-large`; topic and task are tags, and each topic has a Hugging Face collection. Names never change after the first publication.
- Datasets, training data and raw source texts are never published. Models, methods, prompts and evaluation results are.

## Setup

Prerequisites: Python 3.12 and [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync --all-extras    # base install (inference) plus the jtbd and release extras
uv run pytest
uv run zoo --help
uv run jtbd --help
```

A model user only needs the base install, as shown on each model card.

## Topic: product development, task: JTBD extraction (`jtbd`)

**Published model: [`scout-large`](https://huggingface.co/mobility-model-zoo/scout-large)** (v0.1.0, experimental). It finds jobs, pains and gains in German and English mobility texts and quotes them verbatim, with actor type, evidence type and evidence scope. On the frozen benchmark `pilot-v2` it reaches a comparison composite of 0.72 (best zero-shot small model 0.67); it reads a 9,240-character interview in 8.1 s on 4 CPU cores, 0.84 s on a MacBook M3 Pro GPU and 0.12 s on a DGX Spark. Usage, quality, speed and limits: the [model card](https://huggingface.co/mobility-model-zoo/scout-large); how it was built: [docs/recipes/scout-large.md](docs/recipes/scout-large.md); collection: [Product development](https://huggingface.co/collections/mobility-model-zoo/product-development-6ac6269f0468c62fefb874a8).

```python
from mobility_model_zoo.productdev.jtbd.span import SpanExtractor

model = SpanExtractor.from_pretrained("mobility-model-zoo/scout-large", revision="v0.1.0")
print(model.extract("Nach 22 Uhr fährt kein Bus mehr, also nehme ich das Auto."))
```

Build commands (feature 004): `jtbd span …` (data-check, build-rows, freeze-data, train, tune, label, select, results, release-check, pareto, record) and `scripts/spark/train_span.sh` for training on the DGX Spark. Pilot report: [reports/pilot-v2/report.md](reports/pilot-v2/report.md).

The `jtbd` tool (called `pilot` during the proof of concept) runs the agreement pilot and the measurement chain for the JTBD extraction models: fetch sources once, build and redact chunks, freeze guideline and criteria, label with reference models, teachers and small models, check, match, build the consensus, score, measure speed, decide and report. Code: `src/mobility_model_zoo/productdev/jtbd/`. Configuration: `configs/productdev/jtbd/`.

- Pilot spec, plan and tasks: [specs/001-jtbd-extraction-pilot/](specs/001-jtbd-extraction-pilot/)
- CLI contract: [specs/001-jtbd-extraction-pilot/contracts/cli.md](specs/001-jtbd-extraction-pilot/contracts/cli.md) (commands are now `jtbd ...`)

Additional prerequisites for labeling and measurement:

- The `claude` CLI, logged in with the Claude subscription (Claude reference labeler)
- An OpenRouter key with a **hard spending limit** (GPT reference labeler and teachers)
- Ollama on the DGX Spark (teacher candidates, baseline quality runs)
- For performance runs only: a reference machine with 8 GB RAM, 4 vCPU and no GPU (for 0.1.0 a temporary Railway service, `deploy/railway-perf/`)

```bash
cp .env.example .env   # then fill in the keys and hosts
uv run jtbd doctor
```

## Spikes (not released)

The spike models below are technical spikes (feature 002). Their results are spike results, not benchmark results, and spike models are never published (constitution, "Technical Spikes"). The fast span model below is history: it was rebuilt without spike data as the published production model [`scout-large`](https://huggingface.co/mobility-model-zoo/scout-large) (feature 004).

### Try the spike model locally

The best student from the technical spike (feature 002) runs on a Mac with Apple silicon: Qwen3-4B-Instruct-2507 plus the LoRA adapter `spike-v3b`, trained on 200 training examples labeled by the four-teacher ensemble, merged and converted to MLX 8-bit (4.3 GB). It is a **spike result**, not a benchmark result.

```bash
bash spike/build_local_model.sh          # once: adapter from the Spark, merge, convert -> data/models/spike-v3b-mlx-8bit
uv run --with mlx-lm==0.31.3 python spike/try_model.py "Der Bus fährt nur zweimal am Tag ..."
uv run --with mlx-lm==0.31.3 python spike/try_model.py --file text.txt        # or --json for the raw output
uv run --with mlx-lm==0.31.3 python spike/eval_local_model.py                 # scores on the 35 spike evaluation chunks
```

For a text it prints relevance and each job, pain or gain with actor, evidence and quote, and marks quotes that are not verbatim. On the 35 spike evaluation chunks (agreement with the Claude reference, 2026-10-01) it reaches composite 0.673. For comparison: the same model under vLLM scored 0.639, the untrained base 0.54–0.56 and the teachers 0.75–0.80. It is schema-valid on every chunk; 80% of its quotes are verbatim, and it takes about 50 s per chunk on an M3 Pro. The small model sometimes loops on one quote: generation then stops at the third repeat, the complete items are kept and duplicates are removed, and the output says so in a note.

### Fast span model (encoder, under 1 s per interview)

A second spike architecture for speed: an encoder (XLM-RoBERTa-large, 560M parameters) splits the text into sentences and clauses and classifies each one as job, pain, gain or no item, plus actor type, evidence type and evidence scope. It reads a text in one pass of 512-token windows instead of generating JSON, so quotes are always verbatim and output cannot break. It does **not** produce the free-text actor or the English statement. Trained on the four-teacher ensemble labels plus each teacher's own labels of the 180 spike train chunks (`spike/train_span.py`, on the DGX Spark with `spike/train_span_spark.sh`).

```bash
uv run --with torch --with transformers --with sentencepiece --with protobuf \
    python spike/try_span.py --file data/interviews/fiktiv-interview-fussgaenger-berlin.txt   # --json for JSON
uv run --with torch --with transformers --with sentencepiece --with protobuf \
    python spike/eval_span.py --model data/models/span-lt-fixed                               # 35 spike chunks
```

The default model is `data/models/span-lt-fixed`. The fictional pedestrian interview (9,300 characters) takes 0.71 s on an M3 Pro GPU (MPS) and finds 46 items; with loading the model, about 5 s. The run peaks at 2.3 GB of memory, so a 16 GB Mac is plenty; on the CPU alone (`--device cpu`) the interview takes 1.9 s. On the 35 spike evaluation chunks (agreement with the Claude reference, 2026-10-01) it reaches composite 0.60 (0.63 without relevance, where only 2 of the 35 chunks are irrelevant). It finds items better than the fine-tuned LLM v3b (item matching 0.62 vs 0.53) and is on par for kind (0.65 vs 0.57), but classifies evidence type and actor type worse (0.66 vs 0.80, 0.59 vs 0.69). A variant whose heads also see the neighbouring units (`--context`) was not better. Thresholds were chosen on 20 held-out train chunks, never on the evaluation chunks. Ollama cannot run this kind of model (it serves generative LLMs only); it runs with PyTorch.

To avoid loading the model for every text, run it as a local server (loads once, about 5 s; binds to 127.0.0.1):

```bash
uv run --with torch --with transformers --with sentencepiece --with protobuf python spike/serve_span.py   # port 8877
curl -s 127.0.0.1:8877/extract --data-binary @data/interviews/fiktiv-interview-fussgaenger-berlin.txt     # JSON
curl -s '127.0.0.1:8877/extract?format=text' --data-binary 'Der Bus fährt nur zweimal am Tag.'           # readable
curl -s 127.0.0.1:8877/extract -H 'Content-Type: application/json' -d '{"text": "..."}'
```

Each request then takes the analysis time only: 0.72 s for the interview, about 0.12 s for a short text.

## Data handling (JTBD task)

- `data/` holds snapshots, chunks, raw model responses and analysis. It is gitignored and is **never** committed or published (Principle VI).
- Each source is fetched **once** and stored as a complete raw snapshot. Its `source.yaml` records the origin, license, legal basis, permitted uses (`benchmark_only` or `training_allowed`) and `retention_until`. `jtbd source fetch` refuses a second fetch of the same canonical URL unless it is given `--update --reason`.
- Usernames and direct identifiers are removed before labeling (`jtbd corpus redact`, then `jtbd corpus pii-review` with a local model instead of a manual review, then `jtbd corpus redact-check`).
- Reddit content comes only through the official Data API, is always `benchmark_only`, and is deleted or access-restricted when the research ends (§ 60d UrhG). Arctic Shift is used only to find thread IDs.
- When a snapshot's `retention_until` date has passed, delete its directory under `data/snapshots/`, together with the chunks and runs derived from it. The benchmark manifest in `benchmarks/` keeps only hashes, never text.
- Raw model responses under `data/runs/*/raw/` are never edited.
