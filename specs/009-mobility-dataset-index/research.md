# Research: Mobility resource index

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Date**: 2026-10-10

Each item: decision, rationale, alternatives. Sources were checked on 2026-10-10.

## R1. Where the entries live

**Decision**: The entries live in a new **private GitHub repository** (working name
`mobility-model-zoo-catalog`), one YAML file per entry. Code, JSON schemas, vocabularies and
licence rules live in the public zoo repository under `src/mobility_model_zoo/catalog/`. The CLI
finds the entries through `$MMZ_CATALOG`, with `../mobility-model-zoo-catalog` as the default.
The private repository runs the offline checks in its own CI by installing the zoo package from
the public repository.

**Rationale**: The zoo repository has been public since 2026-10-07. Entries committed there would
be published at once, which contradicts the owner's decision to keep the index internal for now
(FR-032). A private git repository keeps what the spec needs: a reviewable history per entry
(FR-030), dated versions (a commit), merges from parallel discovery runs without conflicts (one
file per entry), and CI. Publishing later means making the repository public or exporting it,
with no rework. The entries are not a dataset in the sense of Principle VI (they hold no content),
so git is allowed. They live outside the public repository only because of the visibility
decision.

**Alternatives**:
- Private Hugging Face dataset repository: closer to a later open catalogue, but it has no GitHub
  CI and weaker review tools. Rejected for now; an export to Hugging Face is a later publication
  step.
- `catalog/` in the public repository: simplest, but published immediately. Rejected by the owner.
- A database (SQLite, Postgres): fast queries but no review history and no diffs. Rejected. At
  2,000 to 10,000 entries a full load of the YAML files takes about a second (R12).

## R2. Base vocabulary and field names

**Decision**: Field semantics follow **DCAT-AP 3.0.1**. A resource is a `dcat:Dataset`, and an
API, bucket or feed endpoint is a `dcat:DataService`. Every field in
[data-model.md](data-model.md) names its DCAT-AP property. Entries store short codes; a later
export maps them to URIs and can also emit schema.org JSON-LD or **Croissant 1.1**, the latter
for machine-learning-ready datasets only.

**Rationale**: DCAT-AP is the only standard that covers texts, media, files and APIs in one model.
data.europa.eu harvests it, so a published catalogue fits Europe's open-data infrastructure.
Croissant describes ML-ready datasets, not podcasts or parliament archives, so it serves as an
export target, not as the base. Dublin Core terms are already part of DCAT (`dct:`).

**Alternatives**: schema.org as the base (looser typing, no access-rights model); Croissant as
the base (wrong scope); DataCite (only for items with a DOI; kept as an optional `doi` field).

## R3. Controlled vocabularies and codes

**Decision**:

| Field | Codes |
|---|---|
| Content language | BCP 47 tags: ISO 639-1 where one exists, else ISO 639-3, with a script subtag where needed (`zh-Hans`, `zh-Hant`). `zxx` = no linguistic content ("not applicable"), `und` = undetermined ("unknown"). These are standard codes, not project inventions. |
| Country or region | ISO 3166-1 alpha-2, plus a small list of supranational regions: `EU`, and UN M49 codes such as `001` (world = "global") and `150` (Europe). |
| Modality | Own six-value enum matching FR-003 (text, audio, video, image, graphic, structured_data), each mapped to a DCMI Type (Text, Sound, MovingImage, StillImage, Dataset or Service). |
| Genre | Own controlled list (paper, report, law, transcript, podcast, hearing, gtfs, api, …); neither DCMI nor DataCite has podcast or GTFS types. |
| Formats | IANA media types, for example `application/zip`, `application/x-protobuf`, `text/csv`. |
| Update frequency | EU Publications Office frequency table codes (`DAILY`, `MONTHLY`, `IRREG`, `NEVER`, …). |
| Licence | SPDX identifiers plus the `LicenseRef-` identifiers already used by the compliance register, and the explicit values `unknown`, `mixed` and `LicenseRef-proprietary`. |

The kind of source, subdomain, topic, status, access method and content origin are own enums.
Each vocabulary file carries a version and a changelog with date and reason (FR-006).

**Rationale**: Standard codes make filters exact and keep a later export cheap. `zxx` and `und`
meet the spec's requirement that "not applicable" and "unknown" stay distinguishable without
inventing values.

**Alternatives**: free-text language and country names (not filterable); EU authority-table URIs in
the entries (long, and they need a network lookup to read).

## R4. Opt-out signals checked at index time

**Decision**: Reuse `compliance/signals.check_url` (robots.txt with the AI agent list, TDMRep
file, header and meta, `X-Robots-Tag`/meta `noai`, `ai.txt`, terms-of-service flag, deny and
suppression lists) on each entry's landing page. Extend it with two signals that matter in 2026:
- Cloudflare **`Content-Signal: ai-train=no`** lines in robots.txt. Cloudflare's managed
  robots.txt sets this by default on millions of domains and documents it as an Article 4
  reservation.
- The IETF **AIPREF `Content-Usage`** header and robots.txt rule (drafts `aipref-vocab-08` and
  `aipref-attach-05`, not yet an RFC). The label set is kept in `compliance/lists` so it can change
  without a code change.

Any single reservation marks the entry "opt-out" for training. Embedded media metadata (IPTC/PLUS
`DataMining`, C2PA training-and-mining assertions) is checked by the later download feature on the
files themselves, not at index time.

**Rationale**: One signal checker for index and fetch means one interpretation of the law. Fail
closed matches feature 006. The two new signals also make the existing fetch path stricter, which
is the safe direction.

**Alternatives**: a separate, lighter checker for the catalogue (two interpretations, rejected);
checking media metadata at index time (that would require downloading files, which FR-001 and
FR-024 forbid).

## R5. Provisional usage decision (licence rules)

**Decision**: A versioned rule table in the package (`catalog/rules.yaml`) derives `permitted_use`
and `redistribution` from licence, opt-out signals, platform terms and kind of source. Every
outcome records the rule identifier and a one-line rationale (FR-011). Initial rules, first match
wins:

| Rule | Condition | permitted_use | redistribution |
|---|---|---|---|
| U1 | withdrawn, or opt-out signal present, or platform terms `ml_use: not_allowed` | not_usable | not_allowed |
| U2 | licence `unknown` or `mixed` (at collection level) | undetermined | unclear |
| U3 | licence on `compliance/lists/licence-allowlist.yaml` | training_allowed | allowed (share-alike carried as a flag) |
| U4 | licence is NC or ND | benchmark_only | not_allowed |
| U5 | `LicenseRef-proprietary` and the kind of source has a source class with a recorded legal basis in a topic register | as that class decides | not_allowed |
| U6 | anything else | undetermined, flagged for an owner decision | unclear |

`undetermined` entries can never be cleared (FR-018). The binding decision is still made when the
source record is created at fetch time (feature 006 checks C-I1 and C-I2).

**Rationale**: Reusing the licence allow-list keeps one source of truth with the compliance
harness. Rule U5 lets proprietary but text-and-data-minable material (for example parliament
records with no open licence) be cleared only where a source class already documents the legal
basis. Everything else goes to the owner as a flag rather than being guessed (owner direction: no
per-entry review, flags only).

**Alternatives**: a language model decides usage (not reproducible, rejected); treat every
proprietary resource as Article 4 TDM-permitted (too broad for training without a class-level
legitimate-interest assessment).

## R6. How entries are found: harvesters first, agents for the long tail

**Decision**: Two kinds of discovery, both writing a **run file** (one JSON line per candidate,
plus a run header) that `zoo catalog ingest` validates, deduplicates and checks:

1. **Harvesters**: deterministic code against catalogue APIs that expose licence and language as
   fields. The first set covers the pilot:

   | Harvester | Covers | Licence / language in metadata | Key |
   |---|---|---|---|
   | data.europa.eu (search API) | open data and reports of EU and member states (es, pl, …) | `dct:license` (sometimes missing) / `dct:language` | none |
   | Mobility Database | GTFS and GTFS-RT feeds worldwide (es, pl, jp) | licence URL per feed / none (`zxx`) | free token |
   | OpenAlex | papers by language and topic | per location / `language` | free key |
   | Zenodo | datasets, reports, papers | `license.id` / `language` | none |
   | Hugging Face Hub | datasets | card `license`, `language` tags | none |

   Later harvesters (no pilot dependency): Transitland, national CKAN portals (for example
   datos.gob.es, dane.gov.pl, data.go.jp), Podcast Index, YouTube Data API (metadata only; its
   developer policies forbid downloading content through the API), Wikimedia Commons, Eurostat,
   OECD/ITF, World Bank.

2. **Agent discovery** for what no API lists: parliament video archives, ministry publication
   series, podcasts and research-institute reports. A project skill (`.claude/skills/catalog-discover/`)
   tells a Claude Code agent how to search one scope (language × subdomain × modality) and write
   candidates into a run file. The agent never downloads content and records an evidence address
   for every licence statement.

**Rationale**: The 2,000-entry target (SC-002) is reachable cheaply only if most entries come from
APIs whose licence field is machine-readable, which also helps SC-004. Agents cover modalities and
publishers that have no catalogue API. Cost order (Resources & Cost Discipline): harvesters and
checks run locally at no cost; agent discovery uses the flat-rate subscription. A local model
cannot search the web on its own, which is why agents are not local. Cash budget: 0 €. The free
API keys (Mobility Database, OpenAlex, later YouTube and Podcast Index) are created by the owner
and stored like the other credentials (`docs/credentials.md`).

**Alternatives**: agents only (expensive in subscription limits, weaker licence evidence);
harvesters only (no podcasts, parliament archives or most video); a paid search API (cash cost
with no clear quality gain).

## R7. Duplicate detection

**Decision**: Candidates are matched against existing entries on (a) the canonical landing or
access address (`signals.canonical`), (b) DOI, ROR or another persistent identifier, and (c) a
normalised title plus publisher with fuzzy similarity ≥ 0.92 (`rapidfuzz`, already a dependency of
`jtbd`; added to the catalog extra). A match on (a) or (b) merges the candidate into the existing
entry as an extra access route. A match on (c) only is flagged as `possible_duplicate`.

**Rationale**: FR-019 names exactly these three keys. Automatic merges happen only on exact keys;
fuzzy matches are flagged, not merged, so SC-008 (fewer than 2% duplicates) is met without
silently losing distinct resources.

## R8. Independent re-check of the usage decision (SC-005)

**Decision**: `zoo catalog audit --sample 30` draws a seeded random sample. For each entry it
fetches the licence evidence page and classifies it twice: once by a deterministic SPDX text
matcher (licence names, URLs and badges), and once by a **local model of a different family** than
the discovery agent, run on the DGX Spark. It reports agreement with the stored decision, and
whether any cleared entry was classified as not usable.

**Rationale**: SC-005 needs an independent check. The discovery agent is Claude, so the second
reader must be neither Claude nor the same rule table. A local model costs nothing in cash
(Principle V, cost order).

**Alternatives**: owner review of 30 entries (works, but the owner asked not to review entries);
re-running the same rules (not independent).

## R9. Language report and the base encoder

**Decision**: The language report reads `base_model` and `languages` from every
`zoo/models/*/model.yaml`, the pretraining languages of each base model from a vocabulary file
`catalog/vocab/base-models.yaml`, and the training-language shares per model from the catalog
repository's `config.yaml` (scout-large: span-train-v1, 28% de and 72% en, citing the recipe).

Findings for the target list:
- XLM-RoBERTa (CC-100, 100 languages) covers 33 of the 34 target languages. **Maltese is missing**;
  Irish is covered.
- Broader alternatives for a later encoder decision:
  - mmBERT: over 1,800 languages, including Maltese.
  - Glot500-m: 511 languages, but weaker on high-resource languages.
  - XLM-V and mDeBERTa-v3: the same 100 languages as XLM-R.

**Rationale**: The report makes "change the encoder only if needed" a data question (US6). With
today's target list the base model is not the bottleneck; the training data is.

## R10. Versions, fetch lists and the hand-off to downloads

**Decision**:
- **Index version**: the commit hash of the catalog repository, plus a SHA-256 over the normalised
  entries. Every report and fetch list records both together with its date (FR-030); per-entry
  history is the git history of its file.
- **Fetch list**: a YAML file written to `fetch-lists/<date>-<name>.yaml` in the catalog repository.
  Each item carries a `proposed_record` in the shape of the target register, using the same field
  names as the existing schemas:
  - a source record (`topics/<topic>/compliance/sources.yaml`) for texts, audio, video and images;
  - a dataset declaration (`topics/<topic>/compliance/datasets.yaml`, with `provider`/`locator`) for
    structured data.
- **After download**: `zoo catalog link <entry> <register>:<record-id>` sets the entry to
  "fetched" (FR-029).

**Rationale**: SC-007 asks that a download needs no further research. Pre-filling the existing
register shapes is the most direct way to meet that and keeps one record format.

## R11. Objections and withdrawals

**Decision**: `zoo catalog withdraw <entry> --request <request-id>` requires an existing entry in
`compliance/requests.yaml` (type `objection`, `takedown` or `opt_out`). It sets the entry to
"withdrawn" and adds the canonical address hashes of the entry to `compliance/suppression.yaml`, so
the fetch-time signal check (C-F5) refuses the resource as well (FR-021).

**Rationale**: It reuses the objection channel and suppression list of feature 006. A withdrawal is
then enforced twice, in the catalogue and at fetch.

## R12. Scale and performance

**Decision**: Entries are loaded completely into memory. At 2,000 entries (10,000 as a planning
ceiling), loading and validating takes under 2 s and a query under 1 s on the development laptop,
which is enough for SC-006 (an answer in under a minute). Network checks throttle to one request
per second per host, run up to eight hosts in parallel, and cache robots.txt per host for one day.
A full re-check of 2,000 entries takes about 15 to 30 minutes.

**Rationale**: No database is needed at this size. Per-host throttling keeps the checks polite to
small publishers; the crawler identifies itself with the project user agent of `signals.py`.
