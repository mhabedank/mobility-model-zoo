# Quickstart: Validating the JTBD Extraction Pilot

This guide proves that the pilot tooling works end to end. It lists commands and expected outcomes, not implementation. Command details are in [contracts/cli.md](contracts/cli.md), and record shapes are in [data-model.md](data-model.md).

## Prerequisites

- Python 3.12 and `uv`
- The `claude` CLI, logged in with the Claude subscription
- In `.env` (gitignored):
  - `OPENROUTER_API_KEY`, with a hard spending limit of €12 set on the key in OpenRouter
  - `OLLAMA_HOST`, pointing to the DGX Spark
- For performance only: a Linux cloud VM with 8 GB RAM, 4 vCPU and no GPU, with Ollama installed and the same model digests pulled

## 1. Install and run the test suite

```bash
uv sync
uv run pytest
```

**Expected result**: all unit tests pass. The fixture values below are computed by hand:
- kappa, weighted kappa and F1
- matching on overlapping spans with the kind tie-break
- quote normalization for whitespace and typographic quotes
- consensus and contested entries
- the decision table, including "Rethink takes precedence" and "second failure after the rerun leads to Rethink"
- the budget guard

## 2. End-to-end run on the mini corpus (mocked backends)

```bash
uv run pilot --config tests/fixtures/mini-corpus/pilot.yaml freeze
uv run pilot --config tests/fixtures/mini-corpus/pilot.yaml label --role reference --backend mock --model mock-a
uv run pilot --config tests/fixtures/mini-corpus/pilot.yaml label --role reference --backend mock --model mock-b
uv run pilot --config tests/fixtures/mini-corpus/pilot.yaml check --run <each run>
uv run pilot --config tests/fixtures/mini-corpus/pilot.yaml match --runs <a> <b>
uv run pilot --config tests/fixtures/mini-corpus/pilot.yaml consensus --reference <a> <b>
uv run pilot --config tests/fixtures/mini-corpus/pilot.yaml freeze --benchmark   # allowed because pilot.yaml sets test_fixture: true
uv run pilot --config tests/fixtures/mini-corpus/pilot.yaml agreement
uv run pilot --config tests/fixtures/mini-corpus/pilot.yaml decide
uv run pilot --config tests/fixtures/mini-corpus/pilot.yaml report
```

**Expected result**: `report.md` contains:
- agreement per dimension with n and CI
- a contested section
- check pass rates
- a decision with its path through the decision table

The benchmark manifest is marked `test_only`. The mini corpus includes one irrelevant chunk (the empty result counts as correct) and one fabricated quote (it fails `quote_verbatim`).

## 3. Guardrails

| Scenario | Command | Expected |
|----------|---------|----------|
| Crawl once | `pilot source fetch <url> ...` twice | the second call exits `5` and no file is written |
| Reddit permitted use | `pilot source fetch <reddit-url> --type reddit --permitted-uses training_allowed` | exits `1`, because Reddit is forced to `benchmark_only` |
| Frozen criteria | `pilot freeze`, then edit `configs/decision-criteria.yaml`, then `pilot label ...` | exits `3` (hash mismatch) |
| Budget | `pilot budget --estimate --model gpt-mini-reference --chunks 100000` | exits `4` before any call |
| Role separation | `pilot label --role teacher_candidate --model <a reference model>` | exits `1` |
| Holdout lock | `pilot label --split holdout` while the pilot state is not `revise` | exits `1` |
| Redaction | a chunk containing `u/someuser`, then `pilot corpus redact-check` | exits `1` and names the chunk |
| Environment | `pilot doctor` | lists what is missing (claude login, OpenRouter key and cap, Ollama hosts, manifest drift) |

## 4. Real corpus readiness

```bash
uv run pilot corpus validate --split main
uv run pilot corpus validate --split holdout
uv run pilot corpus redact-check
```

**Expected result**: composition tables meet FR-002 to FR-007 for both splits, and exit `0`.

## 5. Backend smoke tests (5 chunks, real models)

```bash
uv run pilot label --role reference --backend claude_cli --model claude-reference --limit 5
uv run pilot label --role reference --backend openrouter --model gpt-mini-reference --limit 5
uv run pilot label --role teacher_candidate --backend ollama --model teacher-qwen --host spark --limit 5
uv run pilot budget
```

**Expected result**:
- 5 raw and 5 parsed files per run.
- The manifests contain the model version or digest.
- The Claude manifest records `temperature: not_settable`.
- The ledger shows only cents of spend.

## 6. Performance measurement on the reference VM

```bash
uv run pilot perf --model baseline-qwen3.5-4b --host vm --warmup 3 --hardware hetzner-cx32
uv run pilot perf --frontier --run <gpt-run> --sample 20
```

**Expected result**:
- All performance fields are filled in.
- The digest matches the Spark quality run, and the command refuses if it does not.
- The VM is deleted afterwards, and its cost is added to the ledger.
