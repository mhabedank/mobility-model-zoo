# CLI Contract: `pilot`

This file lists every command the pilot exposes. Each command reads configuration from `configs/` and data from `data/`, writes only to its stated outputs, and is idempotent unless noted otherwise.

## Common behavior

**Global options**:
- `--config configs/pilot-v1.yaml` (default)
- `--dry-run`: estimate and validate, write nothing, call no model

**Exit codes**:

| Code | Meaning |
|------|---------|
| `0` | success |
| `1` | validation failure (the data violates a rule) |
| `2` | usage error |
| `3` | frozen-hash mismatch (Principle IV) |
| `4` | budget refusal |
| `5` | crawl-once refusal |
| `6` | backend failure after retries |

**Logging**: human-readable messages go to stderr, and a machine summary (JSON) goes to stdout.

## Sources (crawl once)

### `pilot source fetch <url> --type <source_type> --license <id> --legal-basis <text> --permitted-uses <benchmark_only|training_allowed> --retention-until <date>`

- Fetches the complete document once and writes `data/snapshots/<snapshot_id>/{raw.*, text.txt, source.yaml}`.
- Refuses with exit `5` if a snapshot already exists for the canonical URL. The `--update --reason <text>` option creates a new snapshot that supersedes the old one.
- `--type reddit` forces `benchmark_only` and requires the official-API fetcher.
- Output: a [source-snapshot](source-snapshot.schema.json) record.

### `pilot source reddit <thread_id> --retention-until <date> [--update --reason <text>]`

Fetches a whole thread (post plus comment tree) through the official Reddit Data API with the OAuth credentials from `.env`. It is always stored as `benchmark_only`. Author names are left out of `text.txt`, and the raw API response is the snapshot.

### `pilot source register <path> --url <origin> ...`

Registers a file that was obtained manually (for example a PDF study) as a snapshot. It takes the same metadata and follows the same crawl-once rule.

### `pilot source list [--permitted-uses ...]`

Lists the snapshot registry.

## Corpus

### `pilot corpus build --from <selection.yaml>`

- Cuts chunks from snapshots, using ranges and parent context listed in the selection file. It never fetches.
- Writes `data/chunks/<chunk_id>.json` ([chunk-record](chunk-record.schema.json)).

### `pilot corpus redact` / `pilot corpus mark-reviewed` / `pilot corpus redact-check`

- `redact` applies the pattern-based redaction.
- `mark-reviewed <chunk_ids...> | --all` records the manual review timestamp.
- `redact-check` fails with exit `1` if any known identifier pattern remains, or if a chunk has no `manual_review_at`.

### `pilot corpus split --holdout 30 --seed <n>`

Makes a stratified main/holdout split by sub-area × source type × language. Holdout chunks are write-protected until a rerun is started.

### `pilot corpus validate [--split main|holdout]`

- Checks the composition targets from FR-002 to FR-007, metadata completeness, and the 300–1500 token range.
- Prints a composition table. Exit `1` if a target is missed.

## Freezing

### `pilot freeze`

- Hashes the guideline, the extraction-output schema, `decision-criteria.yaml`, `budget.yaml` and the main chunk IDs and texts.
- Writes `benchmarks/pilot-v1/manifest.json` in state `criteria_frozen`.
- Refuses if the manifest is already frozen and the hashes differ. A new version (`--new-version pilot-v2 --rationale <text>`) is required in that case.

### `pilot freeze --benchmark`

Adds the consensus and contested hashes after `pilot consensus` and sets the benchmark to `frozen`. This runs directly after the reference consensus (US2), before any result is reported or any other model is scored. `pilot agreement` output that goes into a report and `pilot score` both require the `frozen` state.

## Labeling

### `pilot label --role <reference|teacher_candidate|baseline> --backend <claude_cli|openrouter|ollama|openai_compat|mock> --model <id> [--host <name>] [--split main|holdout] [--limit n] [--workers n] [--retry-failed]`

- **Preconditions**:
  - The frozen hashes match (exit `3` otherwise).
  - The budget guard passes (exit `4` otherwise).
  - The role rules hold: a reference model can never be a teacher candidate, and the families must differ (exit `1` otherwise).
  - `--split holdout` requires the pilot state `revise`.
- **Outputs**:
  - `data/runs/<run_id>/manifest.json` ([label-run-manifest](label-run-manifest.schema.json))
  - `raw/<chunk_id>.json`, never modified
  - `parsed/<chunk_id>.json` ([extraction-output](extraction-output.schema.json))
- **Resumable**: chunks that already have a raw response are skipped. `--retry-failed` retries chunks excluded after backend failures (not schema failures).
- **Workers**: `--workers n` labels chunks in parallel; the manifest, budget and model-version guard stay in one thread. Outputs are identical to a sequential run.
- **Backend specifics**:
  - `claude_cli`: `claude -p --output-format json --json-schema <schema> --system-prompt-file <prompt> --tools "" --model <id> --setting-sources "" --strict-mcp-config --disable-slash-commands --no-session-persistence` in an empty temp directory (no `--bare`, because bare mode ignores the subscription login). The chunk goes in through stdin. Temperature is recorded as `not_settable`.
  - `openrouter`: `response_format` json_schema strict, `temperature: 0`, `provider: {order: [<fixed>], allow_fallbacks: false, require_parameters: true, data_collection: "deny"}`. Teacher candidates set no fixed provider order (recorded as a deviation) but an allowed `quantizations` list, and a per-model `reasoning` setting with a larger `max_output_tokens` (research.md R1).
  - `ollama`: `format: <schema>`, `options.temperature: 0`. The model digest is recorded.
  - `mock`: replays fixture responses. For tests and `--dry-run` only. `pilot freeze --benchmark` accepts mock runs **only** when the config sets `test_fixture: true`. The resulting benchmark is marked `test_only` and can never serve as a real benchmark version. In any other config, mock runs are refused.
- **Model-version guard**: if the model version reported by the backend changes during a run, the run stops with exit `6` and must be repeated (spec Edge Cases).

### `pilot budget [--estimate --model <model_id> [--chunks n]] [--add <item> --eur <x>]`

- Shows the ledger, the cumulative spend, the budget (€20) and the key cap (USD 20 ≈ €18.40 since 2026-09-29, before that €12).
- With `--estimate`, it computes the projected cost of a run and exits `4` if the run would exceed either limit.
- With `--add`, it records a manual charge such as the reference VM.

## Evaluation

Analysis outputs live under `data/analysis/<benchmark version>/`.


| Command | Input | Output |
|---------|-------|--------|
| `pilot check --run <id>` | parsed outputs + chunks | `data/analysis/checks/<run_id>.jsonl` with pass rates per check |
| `pilot match --runs <a> <b>` | parsed outputs with quote spans | `data/analysis/matches/<a>__<b>.jsonl` |
| `pilot consensus --reference <a> <b>` | matches | `data/analysis/consensus.jsonl` and `contested.jsonl` |
| `pilot categorize --export \| --import <csv> \| --check \| --freetext` | contested.jsonl | file-based assignment of one primary category per contested entry, stored in `contested-categories.jsonl` next to `categories.yaml` (contested.jsonl itself stays unchanged because it is hashed). `--freetext` writes the FR-025 sample |
| `pilot agreement [--split main\|holdout]` | consensus meta (names the reference runs), matches and parsed outputs; the main split requires the frozen benchmark | per-dimension agreement with n and CI, plus breakdowns by language, source type and region |
| `pilot ensemble [--split main]` | the complete member runs named in `teacher_ensemble.members` of the frozen criteria | a derived teacher-candidate run `data/runs/<run_id>/` with `manifest.json` (`backend: ensemble`, `derived_from`) and `parsed/`; no model calls, cost €0 beyond the members (FR-019b). Exit `1` if a member run is missing or incomplete, exit `3` on a frozen-hash mismatch |
| `pilot score --run <id>` | frozen benchmark | [ModelScore](../data-model.md#modelscore), with contested items scored neutrally. For teacher candidates it also writes the `repaired` view with the frozen `quote_repair` rule (FR-026a); check pass rates stay raw |

## Performance

### `pilot perf --model <model_id> --host vm [--warmup 3] [--quality-run <run_id>] [--hardware <label>]`

- Runs the model sequentially over the main split on the reference VM.
- Records chunks/min, output tok/s, p50/p95 latency and peak RSS.
- Refuses with exit `1` if the model digest differs from the digest of the quality run.

### `pilot perf --frontier --run <gpt-run> --sample 20`

Measures the frontier reference throughput at concurrency 1.

## Decision and report

### `pilot decide`

- Applies the frozen decision criteria mechanically.
- Writes `data/analysis/decision.json` ([PilotDecision](../data-model.md#pilotdecision)), which includes the path through the decision table and the FR-031a teacher-fitness classification with the recommended teacher.

### `pilot report`

- Generates `reports/pilot-v1/report.md` and `figures/pareto.png`.
- Contains every item listed in FR-032, uses agreement wording (FR-033), and names the benchmark and guideline versions.

## Diagnostics

### `pilot doctor`

Checks that `claude` is on PATH and logged in, that the OpenRouter key and its cap are configured, that both Ollama hosts are reachable, and that the manifest state matches the files on disk. Exit `1` if any check fails. It never calls a model and never writes a file.
