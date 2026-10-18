# Mobility resource index (`zoo catalog`)

The resource index is a metadata-only catalogue of mobility resources in every language and modality: texts, papers, audio, video, images, charts and structured data such as tables, databases, buckets, APIs and feeds. It records what exists, under which licence, and how it could be obtained, so that later features can fetch resources for training without new research (feature 009, `specs/009-mobility-dataset-index/`).

## Where things live

- **Entries** live in the private repository `mhabedank/mobility-model-zoo-catalog`, one YAML file per entry under `entries/<area>/<id>.yaml`. They never go into this public repository; `zoo catalog init` refuses, and `tests/catalog/test_repo_hygiene.py` fails if one appears.
- **Code, schemas, vocabularies and licence rules** live in `src/mobility_model_zoo/catalog/`: `schemas/`, `vocab/`, `rules.yaml` and `harvest/`.
- The CLI finds the catalogue through `--catalog PATH`, then `$MMZ_CATALOG`, then `../mobility-model-zoo-catalog`.

The index holds no content. It has no downloaded files, no copied abstracts and no transcripts. Its only personal data are the names of publishers and creators, where attribution needs them; check K9 flags contact data and user handles.

## Setup

```bash
uv sync --extra catalog --extra release
```

```bash
git clone git@github.com:mhabedank/mobility-model-zoo-catalog.git ../mobility-model-zoo-catalog
```

Harvester keys go into `.env` (see `docs/credentials.md`):

| Key | Used by |
|---|---|
| `MOBILITYDATABASE_REFRESH_TOKEN` | `mobility-database` |
| `OPENALEX_API_KEY` | `openalex` |
| `PODCASTINDEX_API_KEY` and `PODCASTINDEX_API_SECRET` | `podcast-index` |

The other harvesters need no key. The OpenAlex account has no payment method, so its free daily allowance is a hard limit, and the harvester stops at 80% of it.

## An entry

Every entry carries these mandatory facts (FR-005):

- content language(s) as BCP 47 codes, where `zxx` means no linguistic content and `und` means unknown;
- country or region;
- publisher and kind of source;
- landing page;
- modality and genre;
- topics;
- at least one mobility subdomain, which is the scope test;
- licence, with the page that states it;
- personal-data expectation;
- access routes;
- quality score;
- provenance.

Checks and rules add the opt-out `signals`, the provisional `usage` (`permitted_use`, `redistribution` and the rule that decided them), the `checks` and the `status`. The data model is `specs/009-mobility-dataset-index/data-model.md`, and the authoritative schema is `src/mobility_model_zoo/catalog/schemas/entry.schema.json`.

Status: `candidate` → `verified` → `cleared` (for fetch) → `fetched`. The end states are `rejected`, `retired` and `withdrawn`; entries in them stay in the index so discovery does not propose them again.

## Adding entries

| How | Command |
|---|---|
| By hand | `zoo catalog new --from entry.yaml` |
| Harvester | `zoo catalog harvest <name> --lang es --area ES --subdomain rail --limit 200` |
| Discovery agent | the Claude Code skill `catalog-discover` (`.claude/skills/catalog-discover/SKILL.md`) writes a run and calls `zoo catalog ingest` |
| A run file | `zoo catalog ingest runs/<run>.jsonl --run runs/<run>.yaml` |

Harvesters: `data-europa`, `mobility-database`, `openalex`, `zenodo`, `huggingface`, `wikimedia-commons` and `podcast-index`.

Harvesters never store abstracts or descriptions. They take the judgment fields (personal data, quality) from `harvest/defaults.yaml` and the search terms from `harvest/terms.yaml`.

Ingest deduplicates. A match on the same canonical address or the same DOI merges into the existing entry as another access route. A similar title and publisher adds the flag `possible_duplicate` and nothing is merged. Each run header records its scope, its counts per language × modality cell (including empty cells) and the rejected lines with their reasons.

## Checks and clearing

```bash
zoo catalog validate
```

```bash
zoo catalog check
```

`validate` runs the offline checks and is the CI gate of the catalog repository:

| Check | What it tests |
|---|---|
| K1 | schema and vocabularies |
| K2 | integrity |
| K3 | duplicates |
| K8 | the stored usage matches the rules |
| K9 | personal data in metadata |

`check` adds the network checks:

| Check | What it tests |
|---|---|
| K4 | landing page |
| K5 | licence evidence, stored as a hash; a page that reserves all rights although the entry carries an open licence sets the blocking flag `licence_conflict`; a licence that only OpenAlex reports must be stated by the evidence page or the DOI registry (Crossref, DataCite), otherwise the blocking flag `licence_unconfirmed` is set |
| K6 | opt-out signals: robots.txt with the AI agent list, TDMRep, `noai`, ai.txt, Cloudflare `Content-Signal` and IETF AIPREF `Content-Usage` |
| K7 | access route |

`check` then applies the licence rules U1–U6 of `rules.yaml` and the state machine. An entry under a listed non-commercial licence is `training_allowed` with `usage.non_commercial: true`: it may train non-commercial models only (feature 011). No-derivatives licences stay `benchmark_only`. It fetches only landing, licence and robots pages, never the resource, at one request per second per host.

An entry is cleared only when all of these hold (FR-018):

- the rules decide `training_allowed` or `benchmark_only`;
- no opt-out signal is set and no platform term forbids the use;
- no blocking flag is set;
- it has a free access route that needs no account per resource. A project-wide API key is fine.

What the rules cannot decide goes to the owner:

```bash
zoo catalog flags
```

```bash
zoo catalog decide <id> --use benchmark_only --reason "…"
```

## Using the index

```bash
zoo catalog query --lang es --lang pt --modality video --use training_allowed
```

```bash
zoo catalog report coverage
```

```bash
zoo catalog report languages
```

```bash
zoo catalog fetchlist spanish-video --lang es --modality video
```

- **Coverage report:** counts and volume per language × modality, area, kind and permitted use, the share of entries with a determined licence, and the gaps among the 34 target languages.
- **Language report:** for each language, whether the base model of each zoo model covers it. XLM-R covers 33 of the 34 target languages; Maltese is missing.
- **Fetch list:** contains only cleared entries. For each it holds a `proposed_record` in the shape of `sources.yaml` (texts and media) or `datasets.yaml` (structured data). After the download, link the entry to its register record:

  ```bash
  zoo catalog link <id> sources:productdev:<record-id>
  ```

## Audit

```bash
zoo catalog audit --sample 30 --dup-sample 50 --seed 9 --model <local model>
```

The audit re-reads the licence pages of a seeded sample with two readers: a deterministic matcher and a local model of a different family than the discovery agent, served from `$OLLAMA_HOST`. Single-page applications (data.europa.eu, Zenodo) are read through the portal's API record of the same resource, and reader answers are mapped to catalog licence ids before they are compared. It reports agreement with the stored decision, cleared entries that a reader finds not usable, and the duplicate rate (SC-005, SC-008).

## Pilot

Before discovery scales to all 34 target languages, `pilot/pilot-v1.yaml` in the catalog repository fixes the pilot. The pilot covers Spanish, Polish and Japanese with text, video and structured data. A language passes with at least 30% determined licences and at least 10 `training_allowed` entries; the pilot passes when two of the three languages pass.

```bash
zoo catalog pilot evaluate pilot/pilot-v1.yaml
```

The command refuses criteria that changed after the first pilot run unless `criteria_changes` records why (constitution IV).

## Maintenance

- **Monthly re-check:** the `recheck` workflow of the catalog repository runs `zoo catalog check` on the 1st of each month and commits changed entries. It re-checks candidates, verified entries and cleared entries last verified more than 180 days ago (FR-020, SC-009). A changed licence page, a new opt-out signal or an unreachable page revokes `cleared`. Run `zoo catalog check` by hand only as a fallback.
- **Owner queue:** `zoo catalog flags`.
- **Objections:** log the request first, then withdraw the entry:

  ```bash
  zoo compliance request add --type objection …
  ```

  ```bash
  zoo catalog withdraw <id> --request <request-id>
  ```

  `withdraw` sets the entry to `withdrawn` and adds keyed hashes of its addresses to `compliance/suppression.yaml`, so the fetch stage refuses them as well (FR-021).
