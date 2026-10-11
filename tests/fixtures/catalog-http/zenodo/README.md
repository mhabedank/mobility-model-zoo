# Zenodo recorded responses (synthetic-trimmed)

Trimmed recorded responses of `GET https://zenodo.org/api/records`, recorded on 2026-10-11 with
`q="ferrocarril" AND metadata.languages.id:(spa)` and `type=dataset` / `type=publication`, then
combined into one page.

Trimming: only the fields the harvester reads are kept (`id`, `doi`, `links.self_html`, `metadata`
title, language, license, resource_type, access_right, doi, first creator, and `files` key, size and
`links.self`). Every creator name is replaced by the placeholder `Author A`; ORCIDs, owners and
statistics are removed. Each `description` is replaced by a placeholder sentence, so the tests can
show that abstracts never reach a candidate.

Synthetic changes: the journal article loses its `license` (tests `unknown`); the proposal loses its
`language` and creator affiliation (tests `und` and the `Zenodo` community publisher). The
restricted dataset is kept as recorded and must be skipped. `records-empty.json` is a synthetic
empty page that ends paging.
