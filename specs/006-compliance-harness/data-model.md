# Data model: Compliance harness

Phase 1 of [plan.md](plan.md). Every record type has a JSON Schema in `src/mobility_model_zoo/compliance/schemas/`, with copies in [contracts/](contracts/). Every record carries `owner`, `last_reviewed` and `next_review`, all ISO dates except `owner`. The value `unknown` is allowed only where marked (U) and must come with `unknown_checked_at`.

## Controller (`compliance/controller.yaml`)

| Field | Value |
|---|---|
| `name` | Martin Habedank (private person) |
| `privacy_contact` | privacy@miskatonic-analytics.com |
| `general_contact` | contact@miskatonic-analytics.com |
| `imprint_url` | https://miskatonic-analytics.com/imprint.html |
| `website_privacy_url` | https://miskatonic-analytics.com/privacy.html |
| `supervisory_authority` | Berliner Beauftragte für Datenschutz und Informationsfreiheit |
| `commercial_activity` | `none` (checked by the repository stage) |

## Source class (`topics/<topic>/compliance/source-classes.yaml`)

| Field | Type | Rule |
|---|---|---|
| `id` | string | e.g. `parliamentary-records`, `cc-papers`, `research-interviews`, `forum-review` |
| `description` | string | |
| `copyright_basis` | enum `tdm_44b`, `official_work_5`, `licence` | §60d is not allowed (D5) |
| `gdpr_legal_basis` | enum `art6_1_f`, `none_needed` | `none_needed` only if the class holds no personal data |
| `lia` | object | `purpose`, `necessity`, `balancing`, `safeguards`, `decided_at` (D10) |
| `art9_handling` | enum `quarantine`, `allowed_by_decision` | `allowed_by_decision` needs `decision_id` (D12) |
| `retention_purpose`, `retention_rule` | string | e.g. "review 24 months after freeze" |

## Source (`topics/<topic>/compliance/sources.yaml`)

One record per origin (R2).

| Field | Type | Rule |
|---|---|---|
| `id` | string | stable slug |
| `class` | ref | a source class |
| `origin_url` | URL | canonical |
| `title` | string | |
| `creators` | list (U) | person or organisation names as credited by the source |
| `publisher` | string (U) | |
| `copyright_notice` | string (U) | |
| `licence` | SPDX id or `LicenseRef-*` (U) | |
| `licence_url` | URL (U) | |
| `attribution_text` | string | rendered into cards; required when the licence requires attribution |
| `modifications` | string | e.g. "split into chunks, personal identifiers redacted, labeled" |
| `permitted_use` | enum `training_allowed`, `benchmark_only` | NC/ND licences force `benchmark_only` |
| `redistribution` | enum `allowed`, `not_allowed`, `unclear` | plus `redistribution_basis` |
| `quote_allowed` | bool | true only for `official_work_5` or CC licences; used by the overlap scan |
| `signals` | object | `robots`, `tdmrep`, `x_robots`, `meta_noai`, `ai_txt`: each `allow`, `deny` or `absent`; plus `tos_url`, `tos_sha256`, `tos_flag`, `tos_verdict` (`allow`, `deny`, `owner_confirmed_allow`); `checked_at`; `retrospective: bool` |
| `personal_data` | object | `present: bool`, `categories: [names_of_office_holders, …]`, `special_categories: [..]`, `human_subjects: bool`, `consent_or_ethics: string (U)` |
| `vehicle_data` | object | only for datasets: `vin`, `gps`, `absolute_timestamps`, each `none`, `present` or `removed` |
| `pii_scan` | object | `tool_version`, `date`, `hits_before`, `hits_after` |
| `storage` | string | path class outside git (e.g. `data/snapshots`) |
| `retention_until` | date | |
| `deleted_at` | date or null | |
| `crawl_manifest_sha256` | string or null | |
| `used_by` | list | `<model>@<version>` for training sources, `benchmark:<name>` for benchmark sources (both kinds are registered) |
| `platform_terms` | object or null | for sources obtained through a platform API: `url`, `sha256`, `checked_at`, `ml_use` (`allowed`, `not_allowed`, `unclear`), `hosted_processing` (`allowed`, `not_allowed`, `unclear`), with the clause quoted |

## Example sources (`zoo/models/<name>/examples/SOURCES.yaml`)

One entry per example file: `file`, `source` (`synthetic`, or a source or dataset id whose record has `redistribution: allowed`), `note` (how it was made). An example file without an entry fails C-U4.

## Dataset (`topics/<topic>/compliance/datasets.yaml`)

All fields of Source. Feature 005's declaration fields are folded in: `provider`, `locator`, `license_check` (`api`, `manual`), `approx_size_mb`, `status` (`active`, `broken_at_source`, `rejected`), `reason`, plus `citation` and `doi`.

## Provider route (`compliance/providers.yaml`)

| Field | Type | Rule |
|---|---|---|
| `id` | string | e.g. `mimi-or-deepinfra` |
| `model_id`, `model_version` | string | |
| `access_path` | enum `local`, `api`, `openrouter`, `consumer_cli` | `consumer_cli` cannot be `allowed_for` anything new (owner decision 2) |
| `hosting_provider` | string | for OpenRouter: the provider name as logged |
| `region` | string (U) | |
| `dpf_listed` | bool (U) | |
| `zero_data_retention` | bool (U) | |
| `training_on_inputs` | bool (U) | |
| `dpa` | bool (U) | |
| `terms_url`, `terms_sha256`, `terms_checked_at` | | a changed hash makes the route due for re-check |
| `output_training_permitted` | enum `yes`, `no`, `unclear` | with `clause` |
| `allowed_for` | list of `teacher`, `reference`, `pii_review` | empty = blocked |
| `signoff` | object | `by`, `at` |

Allow rule for hosted routes: the route must be in the EU or `dpf_listed: true`, with `zero_data_retention: true`, `training_on_inputs: false` and a recorded `signoff`.

## Recipients summary (`compliance/recipients.yaml`, generated)

Per route seen in the labeling logs: `route_id` or `unrecorded`, `model_id`, `access_path`, `hosting_provider` as logged, `roles`, `first_call`, `last_call`, `calls_ok`, `calls_error`, `runs` (run ids). It holds no text and no chunk ids. The privacy notice lists every entry.

## Decision (`compliance/decisions.yaml`)

`id`, `date`, `decision`, `rationale`, `scope` (records, models, versions), `review_by`, `supersedes`. The decisions recorded at the start:
- the four Context decisions of the spec;
- D5–D13 from research;
- `D-parl-art9` (R6);
- `D-claude-risk-0.1.x` (risk acceptance, review by 2027-04-08).

## Waiver (`compliance/waivers.yaml`)

`id`, `check` (a check id with prefix `C-`), `scope`, `rationale`, `approved_by`, `approved_at`, `expires_at`. `expires_at` is required and at most 6 months after `approved_at`.

## Request (`compliance/requests.yaml`)

`id`, `type` (`objection`, `erasure`, `access`, `takedown`, `opt_out`), `received_at`, `deadline`, `identifier_hash` (HMAC, R12), `stores_searched`, `action`, `suppression_added`, `answered_at`. The deadline is one month for GDPR requests and 14 days for takedowns. The meta stage fails on an open request past its deadline.

## Suppression (`compliance/suppression.yaml`)

`entries[]{hash, kind (identifier|url), request_id, added_at}`.

## Legal watch item (`compliance/legal-watch.yaml`)

`id`, `title`, `kind` (`court`, `legislation`, `guidance`), `expected`, `review_by`, `reviewed_at`, `outcome`, `affects` (checks, decisions).

## Release compliance record (`zoo/models/<name>/releases/<version>.compliance.yaml`)

| Group | Fields |
|---|---|
| AI Act | `ai_system: {is_system, rationale}`; `gpai: {is_gpai, generative, params, training_compute_flop, base_model_compute_flop, method, rationale}`; `exclusion_basis: art2_12`; `monetisation: none`; `intended_purpose`; `out_of_scope`; `annex_iii_match: none`; `annex_i: {legislation, safety_component, rationale}`; `art50_trigger: none`; `legal_references: {ai_act: "2024/1689 incl. omnibus 2026", guidelines: [...], checked_at}` |
| Export | `self_classification`, `rationale` |
| Licence manifest | `weights_licence`, `code_licence`, `base_model_licence`, `notices: [...]`, `share_alike_inputs: bool`, `gated: false` |
| Provenance | `sources: [ids]`, `datasets: [ids]`, `routes: [ids]`, `recipients_sha256` |
| Scans | `redaction_recall`, `art9_counts`, `memorisation: {status: not_applicable or result, rationale}`, `publication_scan: {report_sha256, index_fingerprint, files: [{path, sha256, overlap_max_words, pii_hits}]}` |
| Sign-off | `signed_off_by`, `signed_off_at` |

State: `draft` → `signed_off` → `published`. After publication the file is frozen like the release record, and later facts go into a new version.

## Crawl manifest entry (outside git, `data/compliance/crawl-manifest.jsonl`)

`url`, `canonical_url`, `fetched_at`, `user_agent`, `http_status`, `robots_sha256`, `verdicts {robots, tdmrep, x_robots, meta_noai, ai_txt, denylist}`, `tos_sha256`, `content_sha256`, `decision` (`fetched`, `skipped`), `reason`.
