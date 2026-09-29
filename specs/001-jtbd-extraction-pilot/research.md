# Research: JTBD Extraction Pilot

Date: 2026-09-25. Sources were checked through web research and the locally installed `claude` CLI. Claims taken from aggregator sites are marked "verify". Nothing here is legal advice.

## R1 Model selection

### Reference: Claude

- **Decision**: the current top Claude model available in the subscription, pinned with `--model` and called through headless `claude -p` (see R9).
- **Rationale**: it is a frontier model at €0 cash cost (Resources & Cost Discipline: subscription before pay-per-use). Anthropic's terms forbid training other models on its outputs, so being excluded from the teacher role costs nothing.
- **Alternatives considered**: the Anthropic API through OpenRouter, rejected because it costs cash for no extra benefit.

### Reference: GPT (user decision: smaller model)

- **Decision**: the **mini tier of the current GPT generation** through OpenRouter, with `provider.order=["openai"]`, `allow_fallbacks=false`, `require_parameters=true`, `data_collection="deny"`, `response_format` json_schema strict, and reasoning effort low.
- **Exact slug and price**: pick them at implementation time from the OpenRouter model list, and record both in `configs/models.yaml` and `budget.yaml`.
- **Rationale**:
  - The flagship `openai/gpt-6-astra` costs $10 / $50 per million tokens, which is about $31 for 220 calls and breaks the €20 budget.
  - `openai/gpt-5.5` costs $5 / $30, which is about $17 before caching, and a rerun would almost double that.
  - The user chose a smaller GPT model, which is expected to cost a few euros.
- **Consequence**: the reference is no longer a pure frontier pair. This is documented as a deviation in [plan.md](plan.md) Complexity Tracking.
- **Report requirements**:
  - The report states the deviation.
  - The report checks whether low agreement comes mainly from the GPT side. A disagreement category "reference B clearly wrong" is kept for this.
  - If the result is Revise and the budget allows, a GPT-5.5 control run on the 30 holdout chunks is an option. It costs about €2.50 and must be decided before the rerun.
- **Alternatives considered**:
  - GPT-5.5 plus a holdout-only rerun (about €13–16), rejected by the user.
  - GPT-6 Astra with a higher budget, rejected.

### Teacher candidates (local, DGX Spark)

- **Decision**: two families, **Qwen** and **GLM**. Both run locally on the Spark through Ollama.
- **Primary picks**:
  - **Qwen3.5-122B-A10B** (Apache 2.0, about 61–81 GB at Q4, about 30 tok/s on the Spark)
  - **GLM-4.5-Air**, 106B-A12B (MIT, about 53–65 GB at Q4)
- **Fallbacks** (already installed):
  - `qwen3.8:27b` (Apache 2.0, released 14 Aug 2026)
  - `glm-4.7-flash`, 30B-A3B (MIT)
- **Verification step**: before pulling the large models, run the primary and fallback models on 5 German sample chunks. Use a large model if its quality is clearly better and a full run takes under about 3 hours.
- **Rationale**:
  - Apache 2.0 and MIT place no restrictions on outputs, so training on them is allowed.
  - Both families differ from Anthropic and OpenAI, and neither is used as a reference, so neither is blocked as a teacher.
  - Running locally costs nothing.
- **Alternatives considered**:
  - Mistral Medium 3.5 (128B dense): a modified MIT license with a revenue clause, and slow on the Spark because it is dense.
  - Qwen3.8-Flash-Next: the "Qwen Community License 1.0" is unverified.
  - MiniMax M2.7: the license changed to non-commercial.
  - GLM-4.6/4.7 full, Qwen3-235B and DeepSeek V3/V4: do not fit at Q4.
  - gpt-oss: an OpenAI family, and OpenAI is a reference family.

### Small baselines (≤ about 4B)

- **Decision**:
  - `qwen3.5:4b` (Apache 2.0, about 3.4 GB)
  - `gemma4:e4b` (Apache 2.0 since Gemma 4, about 5 GB at Q4; verify it fits in the 8 GB VM together with the context)
  - `ministral-3:3b` (Apache 2.0, about 3 GB, German listed explicitly)
- **Fallbacks**:
  - `phi4-mini` (MIT; weaker in German)
  - `gemma4:e2b`, if e4b exceeds the memory limit
- **Rationale**: all three have permissive licenses, three different families, stated German support, and fit in 8 GB.
- **Alternatives considered**:
  - Llama 3.2 3B: community license with an acceptable-use policy.
  - SmolLM3: weak in German.

## R2 Reddit

> **Update 2026-09-29:** Reddit is dropped for pilot-v1 (project decision, no access request). The substitution `reddit → forum_review` is recorded in `configs/pilot-v1.yaml`. The decision below remains the rule if Reddit is used later.

- **Decision**:
  - Reddit text is retrieved **only** through the official Reddit Data API, after applying through **Reddit for Researchers**, which has been required for academic use since 2025.
  - Every Reddit snapshot is `benchmark_only`.
  - Arctic Shift is used only as a search index to find thread IDs. Its dumps are never used as a text source.
  - Legal basis: § 60d UrhG (TDM by individual non-commercial researchers; contracts cannot override it) together with lawful access through the API.
  - Snapshots are deleted or restricted when the research ends (retention).
- **Rationale**:
  - The Data API terms forbid training ML models on User Content without permission. A benchmark or analysis use is allowed in principle.
  - Arctic Shift has no license or terms and is not authorised by Reddit, so "lawful access" through it is doubtful.
- **Fallback**: if access is not granted in time, fill the source-type slot with Stack Exchange (CC BY-SA) and other open communities with TDM-friendly terms. Record the substitution in the corpus composition report.
- **Alternatives considered**:
  - Arctic Shift dumps as the text source: legal grey zone, rejected.
  - Scraping: violates the terms and robots.txt, rejected.

## R3 Other sources

- **Papers and industry studies**:
  - Open access under CC BY, via OpenAlex or arXiv, plus institute studies (Agora Verkehrswende, ICCT, Fraunhofer, and non-European sources).
  - Each study gets its own license check. Studies without a license are `benchmark_only` under § 60d.
  - This category supplies most of the observation- and measurement-level evidence (FR-008).
- **Forums and reviews**:
  - Check the terms and robots.txt of each platform before the first fetch, and record the date.
  - Platforms whose terms forbid scraping are excluded.
  - Content without an explicit license is `benchmark_only`.
- **Transcripts**:
  - Bundestag plenary protocols are official works under § 5 (2) UrhG and therefore `training_allowed`. They are available through Open Data or the DIP API, and as ready-made corpora from Open Discourse and CPP-BT on Zenodo.
  - Committee Wortprotokolle (for example the Verkehrsausschuss): § 5 status is likely but should be checked. Expert statements (Stellungnahmen) are excluded or marked `benchmark_only`.
  - EU Parliament debates.
  - Scientists for Future podcast (CC BY-SA 4.0, mobility episodes).
  - Other mobility podcasts have no CC license, so they are `benchmark_only` under § 60d, or used with permission.
- **Non-European material (10–15%)**: English open-access papers and English communities.
- **Rationale**: every source records its permitted use once, at snapshot time (crawl once and Principle VI).

## R4 Matching

- **Decision**:
  - The quote locator maps each quote to a character span, after normalizing whitespace, line breaks and typographic quotes.
  - Match score = span IoU. A same-kind bonus is used only to break ties.
  - Minimum IoU is 0.3, frozen in `pilot-v1.yaml` and in the guideline.
  - One-to-one assignment with `scipy.optimize.linear_sum_assignment`.
  - Items that fail the quote check are excluded from matching and counted.
- **Rationale**: this is deterministic, the same for every model, and follows the clarification (span first, kind as tie-break).
- **Alternatives considered**: embedding similarity of the statements, rejected as model-dependent and non-deterministic across versions.

## R5 Agreement statistics

- **Decision**:
  - Cohen's kappa for relevance, kind, actor type and evidence scope, on matched items.
  - **Quadratic**-weighted kappa for evidence type, with linear also reported.
  - Item existence as F1 between the reference models.
  - 95% bootstrap CIs with 1000 resamples, resampling **by chunk**.
  - A dimension with n < 30 is marked underpowered.
- **Rationale**:
  - Quadratic weighting is the standard for ordinal scales and penalizes distant disagreements more.
  - Resampling by chunk respects the fact that items within a chunk are not independent.
- **Alternatives considered**: Krippendorff's alpha, which is only needed for more than two raters.

## R6 Performance measurement

- **Decision**:
  - A rented Linux VM with 8 GB RAM, 4 vCPU and no GPU (Hetzner CX32 class, about €0.01 per hour). The exact type and CPU model are recorded.
  - Ollama with the **same digests** as the Spark quality runs.
  - 3 warm-up chunks, then a sequential run over the main split.
  - Metrics: chunks/min, output tok/s, p50 and p95 latency, and peak RSS of the runner process (sampled from `/proc`).
  - The frontier reference throughput is a separate GPT sample of 20 chunks at concurrency 1.
  - The VM is deleted afterwards.
- **Rationale**: this follows Principle V and the development-versus-target-hardware rule. The Spark is not representative.
- **Alternatives considered**: a container on the Mac or a CPU-limited Spark. Both are host-dependent and not representative.

## R7 Redaction

- **Decision**:
  - Versioned regex patterns for `u/…` and `@…` handles, emails, phone numbers and profile URLs, and names in quoted signatures where they can be found.
  - A manual review of each chunk, with a timestamp.
  - `redact-check` as a hard gate before freezing.
- **Rationale**: Principle VI and FR-012 require verifiable removal.

## R8 Budget

- **Decision**: a cash budget of €20, with a hard cap of €12 on the OpenRouter key.

  | Item | Estimate |
  |------|----------|
  | GPT mini, about 220 calls (main, frontier sample, retries) | a few euros (verify the price) |
  | OpenRouter fee | 5.5%, minimum $0.80 |
  | VM | about €1 |
  | Rerun buffer (main and holdout) | same order as the GPT line |
  | Claude (subscription) and all Spark runs | €0 |

- The expected total is well under €12. `budget.py` estimates each run's cost from token counts and the recorded price before any call.
- **Rationale**: this follows the cost order and the hard-cap rule in the constitution.

## R9 Claude through the subscription (headless)

- **Decision**: `claude -p --output-format json --json-schema <schema> --system-prompt-file <prompt> --tools "" --model <id> --setting-sources "" --strict-mcp-config --disable-slash-commands --no-session-persistence`, run in an empty temporary working directory. **No `--bare`**: in bare mode the CLI reads only `ANTHROPIC_API_KEY` and never the subscription OAuth login (verified with `claude --help` on 2026-09-26). The user-level `~/.claude/CLAUDE.md` may still be loaded as context; this is recorded as a deviation in the run manifest, with the chunk sent through stdin, one call per chunk, paced at 1–2 seconds.
  - Verified locally with `claude --help`: `--json-schema`, `--system-prompt[-file]`, `--tools`, `--model`, `--setting-sources` and `--strict-mcp-config` all exist.
  - The JSON output contains `result`, `structured_output`, `session_id` and `total_cost_usd`. The model ID is taken from the output or the usage data and recorded.
- **Temperature**: cannot be set, and is recorded as `not_settable`. This is a documented deviation from "temperature 0".
- **Validation**: Pydantic validation after each call, with at most 2 retries.
- **Terms**: headless and Agent SDK use under a Max plan draws from the same usage limits as interactive use. Personal, non-commercial use is permitted as of mid-2026 (verify against the current Anthropic help article before the first run). OAuth tokens must not be taken outside the official CLI or SDK.
- **Usage**: about 220 calls of about 7.5k tokens each fit into normal Max usage. If a limit is hit, the run can continue in a later session, because runs are resumable.
- **Alternatives considered**:
  - The Anthropic API: costs cash.
  - The Agent SDK with a subscription token: works, but adds nothing over the CLI here.
