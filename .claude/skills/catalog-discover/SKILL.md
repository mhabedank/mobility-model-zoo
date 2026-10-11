---
name: "catalog-discover"
description: "Find mobility resources for one scope (languages × subdomains × modalities) on the web and add them to the private resource index as a discovery run. Metadata only; never downloads content."
argument-hint: "Scope, e.g. 'es; public_transport, rail; video, text' and optionally the catalog path"
user-invocable: true
disable-model-invocation: false
---

# Catalog discovery (feature 009)

You add candidates to the **mobility resource index**: a metadata-only catalogue in the private
repository `mobility-model-zoo-catalog` (path: `$MMZ_CATALOG`, default `../mobility-model-zoo-catalog`).
Harvesters cover catalogues with APIs. You cover what they cannot see: parliament video archives,
ministry and agency publication series, statistics offices, research-institute reports, podcasts,
video channels, image and chart collections.

## Input

One scope:
- languages (BCP 47 codes from `src/mobility_model_zoo/catalog/vocab/languages.yaml`);
- optional areas (ISO 3166-1 alpha-2 codes or regions from `vocab/areas.yaml`);
- subdomains (from `vocab/subdomains.yaml`);
- modalities (`text`, `audio`, `video`, `image`, `graphic`, `structured_data`).

Ask the user only if no language is given.

## Hard rules

1. **Never download resource content.** Read only landing pages, licence or terms pages, and
   catalogue pages. Stop at a CAPTCHA, a login or a paywall and record the access method instead.
2. **Never copy text.** Write `description` in your own words, in English, with at most 600
   characters. Never paste abstracts, transcripts or page text.
3. **No personal data.** Do not record e-mail addresses, phone numbers or user handles. Name
   private persons only as the publisher of their own podcast or channel, which attribution
   requires (`publisher.kind: individual`).
4. **Evidence for every licence statement.** `licence.evidence_url` is the page that states the
   licence. If you find no licence, write `licence.id: unknown` with `evidence_url: null`.
   "Free to watch" is not a licence.
5. **Explicit unknowns.** A fact you cannot find is written as an unknown value (`und` for the
   language, `unknown` for the licence and for yes/no fields), never left out or guessed.
6. **At least one subdomain** per candidate. Mobility relevance is the scope test (FR-003).
7. Prefer kinds of source that tend to carry open licences: parliaments, ministries, agencies,
   statistics offices, public broadcasters' open archives, universities and research institutes,
   open-data portals.

## Steps

1. **Read the vocabularies and the existing entries of the scope**, so you do not propose known
   resources again. This includes `rejected`, `retired` and `withdrawn` entries. Repeat an option
   for several values:

   ```bash
   uv run zoo catalog query --lang es --lang pt --format table
   ```

   ```bash
   uv run zoo catalog query --lang es --status rejected --status retired --status withdrawn --format ids
   ```

2. **Search the web** per language × subdomain × modality cell. Use search terms in the target
   language; `src/mobility_model_zoo/catalog/harvest/terms.yaml` has a start. Aim for collections
   (an archive, a series, a channel, a portal) rather than single items, unless an item differs
   in licence or language from its collection.
3. **Write one JSON line per candidate** to `runs/<date>-agent-<slug>.jsonl` in the catalog
   repository. The lines follow `src/mobility_model_zoo/catalog/schemas/candidate.schema.json`.
   - Required fields: `level`, `title {original, en}`, `languages [{code, origin}]`, `origin_area`,
     `publisher {name, kind}`, `landing_url`, `resource_type {modality, genre}` (genre allowed for
     the modality in `vocab/resource-types.yaml`), `topics`, `subdomains`, `licence` (`id`, `url`,
     `evidence_url`, `attribution_required`, `commercial_use`, `derivatives`, optionally
     `attribution_text`, `share_alike`), `personal_data {expectation, categories}`,
     `access [{method, url, auth, cost, …}]`, `quality {score 1-5, rationale}` (authority,
     mobility relevance, information density), and `provenance {method: search, evidence: [urls]}`.
   - Audio, video, image and graphic entries also need `content.transcripts {available, languages}`.
   - Never write `status`, `usage`, `signals`, `checks` or `fetched`. The checks set those.
   - Platform terms that restrict automated access or machine learning go in `platform_terms`
     `{url, ml_use, automated_access, checked_at}`.
4. **Write the run header** `runs/<same name>.yaml`:

   ```yaml
   id: <date>-agent-<slug>
   date: <today>
   kind: agent
   scope: {languages: [...], areas: [...], subdomains: [...], modalities: [...]}
   method: <search engines and queries used, skill catalog-discover v1>
   agent: {tool: claude-code, model_id: <your model id>, model_version: null}
   cost: {cash_eur: 0, notes: flat-rate subscription}
   outcome: {}
   ```

5. **Ingest and check**, then report the outcome counts and the rejected lines with their reasons:

   ```bash
   uv run zoo catalog ingest runs/<name>.jsonl --run runs/<name>.yaml
   ```

   ```bash
   uv run zoo catalog check
   ```

   Fix and re-ingest rejected lines only if the reason is a mistake of yours (a typo in a code,
   a missing field). Never re-ingest to get around a rule.
6. **Leave committing to the user** or the calling workflow.

## Quality bar

- A good candidate has an authoritative publisher, clear mobility relevance, and a stated licence.
- Score 5 means official, primary, dense material, for example committee hearings or national
  statistics. Score 1 means marginal relevance or a thin page.
- Empty cells are a valid result. Record them; the run header lists cells with zero candidates.
