# Data Model: Mobility resource index

**Feature**: [spec.md](spec.md) | **Research**: [research.md](research.md) | **Date**: 2026-10-10

The JSON Schemas in [contracts/](contracts/) are authoritative; this document explains them. The
DCAT-AP column names the property that a later export maps each field to (R2).

## Catalog repository layout (private, R1)

```text
mobility-model-zoo-catalog/
├── catalog.yaml                 # catalog id, schema version, owner, model training-language shares (R9)
├── entries/<origin>/<id>.yaml   # one entry per file; <origin> = lower-case country or region code
├── runs/<date>-<slug>.yaml      # discovery run records (header + outcome; candidate lines in runs/<…>.jsonl)
├── fetch-lists/<date>-<slug>.yaml
├── reports/<date>-coverage.{md,json}, <date>-languages.{md,json}, <date>-audit.{md,json}
├── pilot/pilot-v1.yaml          # pilot scope and criteria, committed before the first pilot run
└── .github/workflows/check.yml  # offline validation on every push
```

The vocabularies, rules and schemas are part of the public package
(`src/mobility_model_zoo/catalog/`), so they are versioned with the code that enforces them.

## Entity: Entry

One resource, either a collection or an item. File name = `id`.

| Field | Type | Req. | DCAT-AP | Rule |
|---|---|---|---|---|
| `id` | slug `^[a-z0-9][a-z0-9-]{2,79}$` | yes | `dct:identifier` | Never changes (FR-005). |
| `schema_version` | int | yes | (none) | Currently 1. |
| `level` | `collection` \| `item` | yes | (none) | FR-002. |
| `parent` | entry id \| null | yes | `dct:isPartOf` | Null for collections. An item has at most one parent (a standalone paper or record has none); a parent must exist and be a collection. |
| `title.original`, `title.en` | string | yes | `dct:title` | `title.en` may equal `title.original` for English. |
| `description` | string ≤ 600 chars | should | `dct:description` | In the curator's own words, never copied (FR-032). Harvesters leave it empty; only the discovery agent or the owner writes it. |
| `languages[]` | `{code, origin}` | yes, ≥ 1 | `dct:language` | `code` is BCP 47 from the vocabulary; `zxx` = not applicable, `und` = unknown. `origin` is one of `original`, `human_translated`, `machine_translated`, `ai_generated`, `unknown` (FR-009). `zxx` and `und` cannot be combined with other codes. |
| `origin_area` | ISO 3166-1 alpha-2 \| region code | yes | `dct:spatial` | `001` = global, `EU`, or another M49 region (R3). |
| `publisher.name` | string | yes | `dct:publisher` | Checked by K9 for contact data and handles (FR-031). |
| `publisher.kind` | enum *source kind* | yes | (none) | The kind of source (FR-005). |
| `publisher.ids` | `{ror?, wikidata?}` | no | `adms:identifier` | |
| `landing_url` | https URL | yes | `dcat:landingPage` | |
| `resource_type.modality` | enum *modality* | yes | `dct:type` (DCMI) | FR-003. |
| `resource_type.genre` | enum *genre* | yes | (none) | The genre must be allowed for the modality (vocabulary table). |
| `topics[]` | enum *topic* (from `zoo/topics.yaml`, without `sandbox`) | yes, ≥ 1 | `dcat:theme` | FR-004. |
| `subdomains[]` | enum *subdomain* | yes, ≥ 1 | `dcat:keyword` | FR-003, FR-007: at least one subdomain is the operational definition of "mobility-related". |
| `licence` | object, see below | yes | `dct:license`, `dct:rights` | FR-005, FR-010. |
| `platform_terms` | `{url, ml_use, automated_access, checked_at, clause?}` \| null | no | `dct:accessRights` | `ml_use` and `automated_access` are `allowed`, `not_allowed` or `unclear`. |
| `signals` | object | set by checks | `odrl:hasPolicy` | robots, tdmrep, x_robots, meta_noai, ai_txt, content_signal, content_usage (`allow`, `deny`, `absent`), `checked_at` (R4). |
| `usage` | object | set by rules | (none) | `permitted_use`, `redistribution`, `share_alike`, `rule`, `rationale`, `evidence_url`, `decided_at` (FR-011, R5). |
| `personal_data` | `{expectation, categories[]}` | yes | (none) | `expectation` is `none`, `possible` or `present`. The categories include `voices`, `faces` and `names` (FR-012). |
| `access[]` | access route, see below | yes, ≥ 1 | `dcat:distribution` / `dcat:DataService` | FR-013. |
| `content` | object | should | | `transcripts {available: yes/no/unknown, languages[]}` (FR-008); `temporal {start?, end?}` (`dct:temporal`); `published`, `updated` (`dct:issued`, `dct:modified`); `frequency` (`dct:accrualPeriodicity`); `volume {items?, hours?, bytes?}`. |
| `quality` | `{score 1–5, rationale, tasks[]}` | yes | (none) | FR-014. The rationale names authority, relevance and density. |
| `relations` | `{translation_of?[], duplicate_of?, possible_duplicates?[]}` | no | `dct:relation` | |
| `identifiers` | `{doi?, other?[]}` | no | `adms:identifier` | Used for duplicate detection (R7). |
| `provenance` | object | yes | `prov:wasGeneratedBy` | `added_by` (`owner` or `run:<run-id>`), `added_at`, `method` (`search`, `citation`, `recommendation`, `registry`, `harvest`), `evidence[]` (URLs), `last_verified` (FR-015). |
| `status` | object | yes | (none) | `value`, `since`, `reason`, `flags[]` (see the state machine). |
| `checks[]` | check result | set by checks | (none) | Latest result per check id (FR-017); history is in git. |
| `fetched` | `{register: sources\|datasets, topic, record_id, linked_at}` \| null | no | (none) | FR-029. |

### Licence object

| Field | Type | Rule |
|---|---|---|
| `id` | SPDX id \| `LicenseRef-…` \| `unknown` \| `mixed` | Same pattern as `sources.schema.json`, extended by `mixed`. |
| `url` | URL \| null | |
| `evidence_url` | URL \| null | The page that states the licence. Required unless `id` is `unknown` (SC-004). |
| `attribution_required` | yes \| no \| unknown | |
| `attribution_text` | string \| null | As given by the publisher. |
| `commercial_use` | yes \| no \| unknown | |
| `share_alike` | bool \| null | |
| `derivatives` | yes \| no \| unknown | |

### Access route

| Field | Type | Rule |
|---|---|---|
| `method` | enum: `direct_download`, `bulk_dump`, `api`, `feed`, `page_by_page`, `streaming_platform`, `on_request`, `registration`, `paid`, `not_accessible` | FR-013. |
| `url` | URL | `dcat:accessURL`, or `dcat:endpointURL` for APIs. |
| `download_url` | URL \| null | `dcat:downloadURL`; only for direct files. |
| `auth` | `none` \| `api_key` \| `account` | |
| `cost` | `free` \| `paid` | |
| `rate_limit` | string \| null | As documented by the provider. |
| `formats[]` | IANA media types | `dct:format` / `dcat:mediaType`. |
| `size_bytes_est` | int \| null | `dcat:byteSize` (an estimate). |
| `provider_hint` | `zenodo` \| `uci` \| `huggingface` \| `mobilitydatabase` \| `url` \| null | Pre-fills the dataset declaration `provider` (R10). |
| `notes` | string | |

## Entity: Status (state machine)

```text
              checks pass            rules: cleared            linked to source record
candidate ───────────────▶ verified ───────────────▶ cleared ─────────────────────────▶ fetched
    │                         ▲  │                     │
    │ fails permanently       │  │ re-check changed    │ re-check changed (link, licence,
    ▼                         │  ▼ (FR-020)            │ signals) → back to verified + flag
 rejected            retired ◀┘ (gone for good)        ▼
                                                    verified
any state ── objection (FR-021) ──▶ withdrawn (terminal; never in a fetch list)
```

Transition rules:
- **candidate → verified**: every check of FR-017 has passed, with no `fail`. A `warn` (for example
  `possible_duplicate`) adds a flag but does not block.
- **verified → cleared**: the rule outcome (R5) is `training_allowed` or `benchmark_only`, every
  signal is `allow` or `absent`, `platform_terms.ml_use` and `automated_access` are not
  `not_allowed`, no flag `unreachable`, `personal_data_in_metadata`, `owner_decision_needed` or
  `licence_conflict` is set, and at least one access
  route has `method` in {`direct_download`, `bulk_dump`, `api`, `feed`, `page_by_page`} with
  `cost: free` and `auth` in {`none`, `api_key`}. `api_key` means a project-wide key registered once
  (FR-018); `account` (per-resource registration) never clears.
- **cleared → verified**: a re-check finds a change; the previous values are kept in the check
  result.
- **→ rejected**: a mandatory check fails permanently (for example out of scope, or the URL never
  resolves).
- **→ retired**: the resource is gone (the landing page has answered 404 or 410 on three checks at
  least 7 days apart).
- **→ withdrawn**: only through `zoo catalog withdraw` with a request id (R11).
- `rejected`, `retired` and `withdrawn` entries stay in the index (FR-016).

Flags (`status.flags[]`) record what the rules cannot decide or what needs attention:
`owner_decision_needed` (rule U6), `possible_duplicate`, `licence_changed`,
`mixed_licence_children_missing`, `unreachable` (the landing page did not answer on the last
re-check), `personal_data_in_metadata` (K9 warn), `licence_conflict` (K5: the evidence page reserves
all rights although the entry carries an open licence; audit 2026-10-14). `zoo catalog flags`
lists them.

## Entity: Check result

`{check, result: pass|warn|fail, at, detail, previous?}`. Check ids:

| Id | What | Network |
|---|---|---|
| K1 | Schema and vocabulary valid | no |
| K2 | Referential integrity: parent exists, topics exist, translation targets exist | no |
| K3 | Duplicates (R7) | no |
| K4 | Landing page reachable (2xx after redirects) | yes |
| K5 | Licence evidence present and reachable (skipped when the licence is `unknown`) | yes |
| K6 | Opt-out signals (R4) | yes |
| K7 | Access route reachable (HEAD or a small range GET on `download_url`; API base answers) | yes |
| K8 | Usage rule applied (R5) | no |
| K9 | Personal data in metadata (FR-031): `compliance.scan.pii` over `title`, `description` and `publisher.name`, plus handle and user-path patterns (`@name`, `/user/`, `/u/`, `?user=`) in addresses. Contact data (e-mail, phone) → `fail`; a handle or user path → `warn` plus the flag `personal_data_in_metadata` | no |

The offline checks (K1–K3, K8, K9) run in CI. They need no checkout of the zoo repository: the
lists they read (`licence-allowlist.yaml`) ship with the package as package data, and the zoo
repository's copy wins when `--zoo-root` is given. The network checks run through `zoo catalog check`.

## Entity: Discovery run

Header file `runs/<date>-<slug>.yaml`:

| Field | Rule |
|---|---|
| `id`, `date` | |
| `kind` | `harvester:<name>` or `agent` |
| `scope` | `{languages[], areas[], subdomains[], modalities[]}` |
| `method` | Free text: queries, endpoints, skill version. |
| `agent` | `{tool, model_id, model_version}` or null for harvesters |
| `cost` | `{cash_eur, notes}` (subscription usage noted, cash normally 0) |
| `outcome` | `{proposed, accepted, merged, rejected, by_cell: [{language, modality, proposed, accepted}]}`. Empty cells are listed too (FR-022, FR-013 of the run). |

The candidates go in `runs/<date>-<slug>.jsonl`, one partial entry per line, with the fields of
[contracts/candidate.schema.json](contracts/candidate.schema.json). Ingest assigns an `id` when none
is given, sets `provenance.added_by: run:<id>` and the status `candidate`.

## Entity: Fetch list

`fetch-lists/<date>-<slug>.yaml`:
- `selection`: the query that produced it;
- `catalog_commit` and `catalog_sha256`: the index version (R10);
- `created_at`;
- `items[]`: `{entry_id, access_route, proposed_record}`;
- `refused[]`: `{entry_id, reason}`.

`proposed_record` follows `sources.schema.json` for texts, audio, video and images, and
`datasets.schema.json` for structured data. It fills every field the index knows and leaves the
fetch-time fields (`storage`, `retention_until`, `crawl_manifest_sha256`, `pii_scan`) to the
download feature.

## Entity: Reports

- **Coverage** (FR-026): counts and the sum of estimated volume per language × modality, per
  country, per kind of source and per `permitted_use`, and the share of entries with a determined
  licence (SC-004). Gaps are the target languages (vocabulary
  `targets`) and modalities with zero `cleared` or `training_allowed` entries. Machine-translated
  and AI-generated languages are counted separately.
- **Languages** (FR-027): per language: entries, cleared entries, and volume; for each model in
  `zoo/models`, whether its base model covers the language (`base-models.yaml`) and the language's
  share in the model's training data (`catalog.yaml`).
- **Audit** (SC-005, SC-008): the sample ids and seed, agreement with the deterministic matcher
  and with the local model, the cleared entries classified as not usable, and the duplicates
  found.

Every report records `catalog_commit`, `catalog_sha256` and `vocab_version`.

## Vocabularies (`src/mobility_model_zoo/catalog/vocab/`)

| File | Content |
|---|---|
| `languages.yaml` | Allowed BCP 47 codes with English names; `targets` = the 34 target languages of FR-023. |
| `areas.yaml` | ISO 3166-1 alpha-2 list plus regions (`EU`, `001`, `150`, …). |
| `source-kinds.yaml` | parliament, government, research, open_data_portal, company, association, standards_body, media, community, education, individual, international_org. |
| `resource-types.yaml` | The modalities with their DCMI mapping, and the genres allowed per modality. |
| `subdomains.yaml` | road, rail, public_transport, cycling, walking, micromobility, shared_mobility, aviation, maritime, freight_logistics, ev_charging, automated_driving, vehicle_technology, vehicle_security, condition_monitoring, urban_planning, rural_mobility, policy_regulation, safety, accessibility. |
| `frequencies.yaml` | EU frequency codes used. |
| `base-models.yaml` | Base model → pretraining language codes (XLM-R: the CC-100 list). |

Each file has `version`, and a `changelog[]` of `{date, change, reason}` (FR-006).
`rules.yaml` (R5) is versioned the same way.
