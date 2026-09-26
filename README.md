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

## Data handling

- `data/` holds snapshots, chunks, raw model responses and analysis. It is gitignored and is **never** committed or published (Principle VI).
- Each source is fetched **once** and stored as a complete raw snapshot. Its `source.yaml` records the origin, license, legal basis, permitted uses (`benchmark_only` or `training_allowed`) and `retention_until`. `pilot source fetch` refuses a second fetch of the same canonical URL unless it is given `--update --reason`.
- Usernames and direct identifiers are removed before labeling (`pilot corpus redact`, manual review, `pilot corpus redact-check`).
- Reddit content comes only through the official Data API, is always `benchmark_only`, and is deleted or access-restricted when the research ends (§ 60d UrhG). Arctic Shift is used only to find thread IDs.
- When a snapshot's `retention_until` date has passed, delete its directory under `data/snapshots/`, together with the chunks and runs derived from it. The benchmark manifest in `benchmarks/` keeps only hashes, never text.
- Raw model responses under `data/runs/*/raw/` are never edited.
