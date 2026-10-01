# mobility-llm: JTBD extraction pilot

This pilot checks the riskiest assumption before any training: can frontier models label the JTBD extraction task consistently, and how far do small local models get without training?

- Spec: [specs/001-jtbd-extraction-pilot/spec.md](specs/001-jtbd-extraction-pilot/spec.md)
- Plan: [specs/001-jtbd-extraction-pilot/plan.md](specs/001-jtbd-extraction-pilot/plan.md)
- Tasks: [specs/001-jtbd-extraction-pilot/tasks.md](specs/001-jtbd-extraction-pilot/tasks.md)
- Constitution: [.specify/memory/constitution.md](.specify/memory/constitution.md)

## Setup

Prerequisites:

- Python 3.12 and [`uv`](https://docs.astral.sh/uv/)
- The `claude` CLI, logged in with the Claude subscription (Claude reference labeler)
- An OpenRouter key with a **hard spending limit of €12** (GPT reference labeler)
- Ollama on the DGX Spark (teacher candidates, baseline quality runs)
- For performance runs only: a Linux VM with 8 GB RAM, 4 vCPU and no GPU, with Ollama installed

```bash
uv sync
cp .env.example .env   # then fill in the keys and hosts
uv run pytest
uv run pilot --help
```

The CLI contract is in [contracts/cli.md](specs/001-jtbd-extraction-pilot/contracts/cli.md). The validation walkthrough is in [quickstart.md](specs/001-jtbd-extraction-pilot/quickstart.md).

## Try the spike model locally

The best student from the technical spike (feature 002) runs on a Mac with Apple silicon: Qwen3-4B-Instruct-2507 plus the LoRA adapter `spike-v3b`, trained on 200 training examples labeled by the four-teacher ensemble, merged and converted to MLX 8-bit (4.3 GB). It is a **spike result**, not a benchmark result.

```bash
bash spike/build_local_model.sh          # once: adapter from the Spark, merge, convert -> data/models/spike-v3b-mlx-8bit
uv run --with mlx-lm==0.31.3 python spike/try_model.py "Der Bus fährt nur zweimal am Tag ..."
uv run --with mlx-lm==0.31.3 python spike/try_model.py --file text.txt        # or --json for the raw output
uv run --with mlx-lm==0.31.3 python spike/eval_local_model.py                 # scores on the 35 spike evaluation chunks
```

For a text it prints relevance and each job, pain or gain with actor, evidence and quote, and marks quotes that are not verbatim. On the 35 spike evaluation chunks (agreement with the Claude reference, 2026-10-01) it reaches composite 0.673. For comparison: the same model under vLLM scored 0.639, the untrained base 0.54–0.56 and the teachers 0.75–0.80. It is schema-valid on every chunk; 80% of its quotes are verbatim, and it takes about 50 s per chunk on an M3 Pro. The small model sometimes loops on one quote: generation then stops at the third repeat, the complete items are kept and duplicates are removed, and the output says so in a note.

## Fast span model (encoder, under 1 s per interview)

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

## Data handling

- `data/` holds snapshots, chunks, raw model responses and analysis. It is gitignored and is **never** committed or published (Principle VI).
- Each source is fetched **once** and stored as a complete raw snapshot. Its `source.yaml` records the origin, license, legal basis, permitted uses (`benchmark_only` or `training_allowed`) and `retention_until`. `pilot source fetch` refuses a second fetch of the same canonical URL unless it is given `--update --reason`.
- Usernames and direct identifiers are removed before labeling (`pilot corpus redact`, manual review, `pilot corpus redact-check`).
- Reddit content comes only through the official Data API, is always `benchmark_only`, and is deleted or access-restricted when the research ends (§ 60d UrhG). Arctic Shift is used only to find thread IDs.
- When a snapshot's `retention_until` date has passed, delete its directory under `data/snapshots/`, together with the chunks and runs derived from it. The benchmark manifest in `benchmarks/` keeps only hashes, never text.
- Raw model responses under `data/runs/*/raw/` are never edited.
