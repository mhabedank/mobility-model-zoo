# Research: Compliance harness

Phase 0 of [plan.md](plan.md). Each entry: decision, rationale, alternatives considered. The legal basis is in [legal-research/report.md](legal-research/report.md) (2026-10-08, not legal advice). Facts about the current code come from a read of branch `006-compliance-harness` at `7c868ce`. File references are given without line numbers where lines will move.

## Owner decisions recorded during planning (2026-10-08)

The following come in addition to the four decisions in the spec's Context.

| # | Decision | Value |
|---|---|---|
| D5 | Copyright basis for text and data mining | §44b UrhG only; §60d is not claimed |
| D6 | Natural-language terms of service | count as an opt-out until the BGH decides I ZR 281/25 (announced for 2026-12-17); review then |
| D7 | Verbatim span in published files | at most 30 consecutive words from the training corpus |
| D8 | Memorisation | no training span longer than 50 tokens reproduced verbatim (generative models); see R9 for extractive models |
| D9 | Redaction recall | at least 0.95 on the labeled redaction test set |
| D10 | Legitimate-interest assessment | one per source class |
| D11 | Impact assessment | one combined, short DPIA document |
| D12 | Special categories (health, religion, politics and the other Art. 9 categories) | excluded by default; exceptions only by a recorded decision |
| D13 | Future dataset compendium | link to the original source only, no re-hosting |

## R1 Where the register lives

- **Decision**: The register is YAML in git, validated by JSON Schemas, and split by scope.
  - **Shared records** go in a top-level `compliance/` folder:
    - `controller.yaml`: controller and contact;
    - `providers.yaml`: teachers, reference models and hosting providers;
    - `decisions.yaml`;
    - `waivers.yaml`;
    - `requests.yaml`;
    - `suppression.yaml`;
    - `legal-watch.yaml`;
    - `recipients.yaml`: a summary of the labeling logs;
    - `lists/`: denylists, the card-lint vocabulary and the licence allowlist.
  - **Topic-specific records** go in `topics/<topic>/compliance/`, following the layout rule of constitution 2.0.0:
    - `sources.yaml`: one record per source origin;
    - `datasets.yaml`: third-party datasets;
    - `source-classes.yaml`: the legitimate-interest assessment per class.
  - **Release records** go in `zoo/models/<name>/releases/<version>.compliance.yaml`: the AI Act classification, licence manifest, scan results and sign-off. They sit next to the existing release record and are not part of it.
- **Rationale**:
  - Constitution 2.0.0 already requires per-topic material under `topics/<topic>/`. Creating `topics/productdev/compliance/` now means feature 005 only adds folders around it.
  - Release records have `additionalProperties: false` and are frozen once published. A separate compliance file per version leaves published records untouched and still versions the evidence.
  - Feature 005's planned `topics/<topic>/datasets.yaml` becomes `topics/<topic>/compliance/datasets.yaml`, using the schema defined here (FR-003). Plan 005 is updated when it is rebased.
- **Alternatives**:
  - One big file (rejected: no topic ownership, merge conflicts).
  - Records inside the release record (rejected: breaks published records).
  - A database (rejected: not reviewable in pull requests).

## R2 Granularity of source records; no personal data in git

- **Decision**: One record per source origin.
  - A text origin is one URL as it already appears in the published card (87 origins for `scout-large` 0.1.1). A dataset is one record.
  - Records carry only what is about the work and its rights: title, creators, publisher, licence, terms, opt-out verdicts and dates. They carry nothing about the people inside the text.
  - Per-document evidence goes to a crawl manifest outside git, `data/compliance/crawl-manifest.jsonl`: URL, time, user agent, HTTP status, robots.txt hash and verdict, TDMRep, `X-Robots-Tag`, meta `noai`, ai.txt, terms hash, content hash. The register references the manifest by its hash.
- **Rationale**:
  - The origins are already public in the 0.1.1 card.
  - Creators of papers and parliamentary bodies are needed for attribution (CC: credit the creator) and are public.
  - Forum usernames never enter git, because forum sources were not used for training and future forum records name the platform and thread, not the users (D12, redaction).
- **Alternatives**: Per-document records in git (rejected: personal data risk, size).

## R3 Fail-closed check engine

- **Decision**: A new shared package `mobility_model_zoo.compliance`.
  - It contains `register` (loading and validation), `checks` (one function per stage, returning findings), `signals` (opt-out detection), `scan` (PII, special categories, corpus overlap), `render` (documents) and `cli` (`zoo compliance …`).
  - Stages are numbered as in the spec. A run stops at the first failing stage and prints `stage / record / field / reason`.
  - Missing evidence counts as a failure. `unknown` passes only when a waiver with expiry covers that check and record.
- **Wiring**:
  - **Fetch:** `jtbd source fetch`, `register` and `reddit` call `checks.fetch`.
  - **Ingest:** `jtbd corpus autochunk` calls `checks.ingest`.
  - **Pre-send:** `labeling/runner.py`, before each backend call, calls `checks.pre_send`.
  - **Retention:** `jtbd doctor` and `zoo compliance retention` call `checks.retention`.
  - **Train:** `jtbd span data-check` and future task tools call `checks.train`.
  - **Release:** `zoo check` gets rule 16 "compliance", which runs meta, model, publication, card, licence, repository, notices and sign-off for that release.
  - **CI:** `zoo compliance check --ci` runs meta, licence, repository, notices and drift without data.
- **Rationale**:
  - FR-006 and FR-020: each check runs where its data lives.
  - The release tool and `jtbd` are two consumers, so a shared module is justified ("Tasks and Releases").
- **Alternatives**: A separate compliance CLI outside the existing tools (rejected: checks would be skipped).

## R4 Opt-out signals at fetch time

- **Decision**: `compliance.signals` checks the following, in this order.
  1. **robots.txt** (RFC 9309) for the project user agent, for `*`, and for the AI crawler tokens in `compliance/lists/ai-user-agents.yaml` (GPTBot, CCBot, ClaudeBot, Google-Extended, PerplexityBot, Bytespider, Applebot-Extended, meta-externalagent and others). A disallow for any AI token counts as an opt-out.
     - **Fail closed:** a network error or a 5xx response means "retry later, do not fetch". A 4xx response other than 401/403 means "no robots.txt", as RFC 9309 allows. 401/403 means "do not fetch".
     - Today the code returns `allowed` on every error (`sources/snapshot.py` `robots_allowed`).
  2. **TDMRep**: `/.well-known/tdmrep.json`, the `tdm-reservation` HTTP header, and `<meta name="tdm-reservation">`. A value of 1 is an opt-out.
  3. **`X-Robots-Tag`** and **`<meta name="robots">`** with `noai`, `noimageai` or `noml`.
  4. **ai.txt** (Spawning format): a disallow for text means opt-out.
  5. **Domain lists**: denylist and piracy list (`compliance/lists/`).
  6. **Terms of service**: the terms URL is fetched and hashed. A keyword screen (`text and data mining`, `scraping`, `crawl`, `machine learning`, `KI`, `Data-Mining`, `automatisiert`) sets `tos_flag`. A flagged source needs `tos_verdict` recorded by the owner (D6). Unflagged terms still get their hash and date recorded.
  7. **Access**: no login, paywall or CAPTCHA. A 401/402/403 response or a login form marker blocks the fetch.

  Other settings:
  - The user agent becomes `mobility-model-zoo-crawler/1.0 (+https://github.com/mhabedank/mobility-model-zoo/blob/main/COPYRIGHT_POLICY.md)`.
  - `jtbd source register` (manual files) requires a `--signals` record: a URL plus a manual verdict and date. Without it, registration is refused (today it skips robots.txt entirely).
- **Rationale**: §44b(3) UrhG allows only machine-readable reservations. The OLG Hamburg ruling leaves open whether plain-language terms qualify. The GPAI Code of Practice expects robots.txt compliance including AI agents. D6 takes the conservative reading.
- **Alternatives**: Spawning `datadiligence` (rejected: needs an API key for bulk use and does not cover robots.txt or TDMRep). No small maintained Python library for TDMRep or ai.txt exists, so these are implemented in-house and kept small.

## R5 Personal data scan before sending text to an LLM

- **Decision**: `compliance.scan.pii` runs before every batch is sent and re-scans the text being sent. It does not trust the stored `check_passed` flag alone.
  - **Patterns:** the existing `redact.py` patterns, plus German and EU recognisers: IBAN, German phone formats, German postcode with street, German licence plates, tax ID patterns, date of birth near a name marker, and e-mail obfuscations.
  - **Model review:** the existing local Ollama `pii-review` stays the second pass.
  - **Recall:** measured on a labeled test set of 300 synthetic German and English sentences with known identifiers (`tests/fixtures/compliance/redaction-set/`, synthetic only). The release of any model trained on redacted text needs recall ≥ 0.95 (D9), recorded in the release compliance file.
- **Rationale**:
  - The current gate trusts a flag set earlier. If the patterns change after `redact-check`, nothing re-checks.
  - Presidio was considered. It adds spaCy models and a dependency stack that is now community-maintained. The local regex set plus the existing local model review keeps personal data on the machine (constitution V, local first) and is measurable through the recall test.
- **Alternatives**: Presidio (rejected for now; can be added as a recogniser source later if recall falls short); a hosted PII API (rejected: sends personal data out).

## R6 Special categories (Art. 9 GDPR)

- **Decision**: A lexicon classifier (`compliance/lists/special-categories.yaml`, German and English terms per category) flags chunks at ingest.
  - **Default (D12):** flagged chunks are quarantined and excluded from labeling and training unless a decision record allows a category for a source class. The quarantine list stores chunk ids only.
  - **Parliamentary records:** these are speeches by office holders, deliberately made public by those persons, so Art. 9(2)(e) applies. That is decided once, as source-class decision `D-parl-art9`. Political content from MPs is therefore not quarantined. Health or religious details about third persons in those records are still flagged.
- **Retrospective step for `scout-large` 0.1.x**: run the classifier over the 1,100 training chunks and the benchmark chunks. Report counts per category in the release compliance file. Hits outside the parliamentary class go to the owner as a decision item (keep with rationale, or plan a 0.2 retraining without them). Weights are never changed in a patch.
- **Rationale**: The CJEU (Meta v Bundeskartellamt) requires a deliberate act by the person themselves for "manifestly made public". That holds for MPs' speeches and not for forum posters.

## R7 Providers and teachers

- **Decision**: `compliance/providers.yaml` holds one record per route, meaning model plus access path plus hosting provider.
  - **Fields:** `model_id`, `model_version`, `access_path` (`local | api | openrouter | consumer_cli`), `hosting_provider`, `region`, `dpf_listed`, `zero_data_retention`, `training_on_inputs`, `dpa`, `terms_url`, `terms_sha256`, `terms_checked_at`, `output_training_permitted` (`yes | no | unclear`) with the clause, `allowed_for` (`teacher`, `reference`, `pii_review`, `none`), `signoff`.
  - **OpenRouter:**
    - `provider_order` must name exactly the allowlisted hosting providers, and `allow_fallbacks: false` stays.
    - After each response, the provider that actually answered (already stored in `backend_meta.provider`) must be on the route's allowlist. Otherwise the response is discarded and the run fails.
    - `models.yaml` entries with `provider_order: null` are refused at run start.
  - **Claude CLI on the consumer subscription:** refused for new runs. The existing runs are covered by decision `D2-claude-0.1.x` (dated risk acceptance, scope `scout-large` 0.1.x reference labels).
  - **Anthropic API:** a new backend `anthropic_api` for future reference labeling (FR, owner decision 2). Its route record needs a DPA and the commercial terms check. It is not run in this feature (cash budget €0).
  - **`training_on_outputs_permitted`:** no longer hard-coded `True` in `span/results.py`. It is read from the route record, and `unclear` fails rule 6 unless a decision covers it.
- **Retrospective recipients**: `zoo compliance recipients --runs data/runs` aggregates the labeling logs of all runs into `compliance/recipients.yaml`. Each entry has model, access path, hosting provider as recorded, first and last date, call count, and run roles. It contains no text and no chunk ids. For `scout-large` 0.1.x the recorded routes are:
  - MiMo through OpenRouter, answered by DeepInfra (1,100 successful training calls; error attempts recorded without a provider);
  - DeepSeek, GLM and MiMo teacher candidates through OpenRouter;
  - the GPT-mini reference through OpenRouter, pinned to OpenAI;
  - the Claude reference through the CLI subscription;
  - local Ollama models.

  Where the log has no provider (error attempts), the entry says `unknown`. Every recorded hosting provider gets a route record with its terms, region, DPF and retention as checked on the day; facts that cannot be established stay `unknown`.
- **Rationale**: Owner decisions 1 and 2. The legal-research report found unpinned routing to be the sharpest GDPR exposure. The logs already hold the provider names, so documentation can rest on evidence.

## R8 Retention

- **Decision**:
  - Snapshot `retention_until` (already stored) and dataset retention from the register are enforced by `checks.retention`.
  - Expired items are reported by `jtbd doctor`, by `zoo compliance retention`, and weekly by `zoo-audit.yml` through `--ci` on the register dates (no data needed).
  - Deletion is a command, `zoo compliance delete --snapshot <id>`. It removes the raw snapshot, keeps hash and URL in a deletion log (`data/compliance/deletions.jsonl`), and sets `deleted_at` in the source record.
  - Retention purposes are recorded per source class: "reproduce the frozen benchmark and the training set of a current model; review 24 months after freeze", matching `span-train-v1.yaml`.
- **Rationale**: §44b(2) UrhG and Art. 5(1)(e) GDPR. Today `retention_until` is stored but never enforced.

## R9 Memorisation and corpus overlap

- **Decision**:
  - **Corpus overlap (all models):** a local shingle index of the training and benchmark corpus is built from `text.txt` of the snapshots used, as hashed 8-word shingles in `data/compliance/corpus-index/` outside git. `zoo compliance scan-publish <model> <version>` checks every file to be published: card, examples, evaluation files, README. It reports any run of ≥ 30 consecutive corpus words (D7), except attributed quotes from sources whose record sets `quote_allowed: true` (official works under §5 UrhG, CC sources).
    - The scan report stores counts, file hashes and the index fingerprint. The gate checks that the report exists and matches the current file hashes.
  - **Memorisation for extractive models (`scout-large`):** the model cannot generate text; it labels spans of the input text, so it cannot reproduce training text that is not in its input. The release compliance file records `memorisation: not_applicable` with this rationale and the architecture check: no generative head, `pipeline_tag: token-classification`. A generative model must run the probe of D8 instead.
  - **Compute estimate:** recorded per release from parameters × tokens × 6 (fine-tune) plus the base model's published estimate, so it can be compared with the 10^23 FLOP GPAI indicator.
- **Rationale**: LG München I (GEMA v OpenAI, not final) treats reproducible works in weights as a reproduction. The real risk for this project is verbatim text in published files, so the scan covers exactly those files.

## R10 Generated documents

- **Decision**: Jinja templates in `src/mobility_model_zoo/compliance/templates/` render the following from the register:
  - `PRIVACY.md`
  - `COPYRIGHT_POLICY.md`
  - `SECURITY.md`
  - `NOTICE`
  - `THIRD_PARTY_NOTICES.md`
  - `REUSE.toml` and `LICENSES/`
  - `.github/ISSUE_TEMPLATE/rights-request.yml`
  - `docs/compliance/record-of-processing.md`
  - `docs/compliance/lia-dpia.md`
  - per release, `zoo/models/<name>/releases/<version>.ai-act.md` and `<version>.training-data-summary.md` (EU AI Office template structure: general information, sources by category with top domains, processing and opt-out measures).

  How the documents are checked and published:
  - **Drift:** `zoo compliance render --check` fails when a committed file differs from its rendering (FR-016, SC-002).
  - **Contact:** generated files name the controller and contact only as in `compliance/controller.yaml`: Martin Habedank, `privacy@miskatonic-analytics.com`, `contact@miskatonic-analytics.com`, links to the imprint and website privacy policy (owner decision 3). No branding text.
  - **Request template:** the GitHub template says not to post personal data and to use the e-mail address for anything personal.
  - **Model card:** new sections render from the register: "Training data and attribution" (TASL table plus modification notes plus the XLM-R MIT notice text), "Teacher and labeling models" (route, provider, terms version), "Out-of-scope use", "Dual-use considerations" (security topics), "Privacy and personal data". They replace the current provenance tables. The card section list in `card.py` and rule 10 grow accordingly. Published cards are not touched.
  - **Hugging Face upload:** for a patch, the HF repo files stay as they are (rule 3 requires identical files). The NOTICE content is in the card text; the training-data summary and AI Act record are linked at the GitHub tag.
- **Rationale**: FR-021 to FR-023; single source of truth. REUSE gives machine-readable file licensing that `reuse lint` can check.
- **Alternatives**: Hand-written documents with a checklist (rejected: they drift).

## R11 Card lint and repository hygiene

- **Decision**: `compliance/lists/card-lint.yaml` defines the required sections per topic kind and forbidden patterns. Card lint runs inside rule 10 and in CI on every draft card.
  - **Forbidden patterns:**
    - high-risk wording: Annex III purposes (recruitment, employee monitoring, credit scoring, biometric identification, critical infrastructure safety, education scoring);
    - safety-function wording ("safety function", "safety component", "ASIL", "type-approved");
    - marketing claims ("production-ready", "certified", "guaranteed");
    - "anonymous model".
  - **Repository hygiene:**
    - required files: `LICENSE`, `NOTICE`, `SECURITY.md`, `PRIVACY.md`, `COPYRIGHT_POLICY.md`;
    - no `FUNDING.yml`, sponsor links, prices or "hire" or "consulting" promotion;
    - no "Miskatonic" outside the generated contact lines;
    - gitleaks as today;
    - `reuse lint`.
- **Rationale**: The AI Act exclusion (Art. 2(12)), the CRA, product liability and the imprint position all rest on being non-commercial and having no high-risk purpose. Memory: the zoo stays private and unbranded.

## R12 Requests, suppression and legal watch

- **Decision**:
  - **`requests.yaml`:** each entry has `id`, `type` (objection, erasure, access, takedown, opt-out), `received_at`, `deadline` (GDPR: one month; takedown: 14 days by policy), `identifier_hash`, `stores_searched`, `action`, `answered_at`.
    - The identifier hash is HMAC-SHA-256 with a secret salt from `.env` (`MMZ_SUPPRESSION_KEY`), so the hashes cannot be reversed by guessing names.
  - **`suppression.yaml`:** keyed HMAC hashes of normalised identifiers and canonical URLs.
    - The fetch stage hashes each candidate URL.
    - The ingest and train stages hash word 1–3-grams of each chunk and match them against identifier hashes.
  - **`legal-watch.yaml`:**
    - BGH I ZR 281/25 (2026-12-17)
    - ProdHaftG (2026-12-09)
    - AI Act Art. 50(2) grace end (2026-12-02)
    - GEMA v OpenAI appeal
    - CJEU C-250/25
    - GDPR Art. 88bis
    - final CRA guidance
    - Latombe appeal

    Each item has a `review_by` date. The meta stage fails after `review_by` unless `reviewed_at` is set.
  - **`zoo-audit.yml`** (weekly) also runs the meta stage, so overdue reviews and request deadlines surface without a release.
- **Rationale**: FR-026 to FR-028. Keyed hashes keep personal data out of git while still allowing matches.

## R13 scout-large 0.1.2

- **Decision**: `scout-large` 0.1.2 is a patch.
  - **Same files:** same files and metric values (rule 3); a new card rendered from the register; release notes "compliance documentation: attribution, teachers and routes, privacy and copyright policy, NOTICE".
  - **Source records:** filled by `zoo compliance bootstrap-sources` from the local `source.yaml` files, `data/sources/source-plan.yaml` and the 0.1.1 provenance. Title, creators, licence, legal basis and terms come from the metadata, and Zenodo creators and licence come from the Zenodo API.
  - **Unknown fields:** stay `unknown` with the attempt date.
  - **Zenodo interview records:** the description is searched for consent and ethics statements. If none is found, the field is `unknown` and an owner decision item is raised.
  - **Owner approval:** the owner approves the card preview through the existing pipeline. A short "Compliance update" note in the card says what changed and when.
- **Rationale**: Spec US3; no retraining (weights unchanged).

## R14 Testing

- **Decision**:
  - Every stage gets unit tests with seeded violations (SC-003): fixture robots.txt and TDMRep responses served by `httpx` mock transports, synthetic PII batches, fixture cards and fixture registers.
  - The drift check is tested by editing a rendered file.
  - Rule 16 is tested in the release fixtures.
  - The redaction recall test runs on the synthetic set.
  - No test uses real personal data.
- **Rationale**: Fail-closed checks are only trustworthy when each failure path is tested.

## R15 CI

- **Decision**:
  - **`ci.yml`:** a new step runs `uv run zoo compliance check --ci` (meta, licence, repository, notices, drift) and `uv run reuse lint`. `reuse` comes from the dev dependency group.
  - **`zoo-audit.yml`** (weekly): adds the meta stage.
  - **Release workflows:** they need no change; rule 16 runs inside `zoo check`.
- **Rationale**: Without data, CI can check the register, documents and repository. Data-dependent stages run locally and leave a report that the gate verifies (R9).
