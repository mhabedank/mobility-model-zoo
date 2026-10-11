# data.europa.eu recorded responses (synthetic-trimmed)

Trimmed recorded responses of `GET https://data.europa.eu/api/hub/search/search`, recorded on
2026-10-11 with `q=ferrocarril`, `filters=dataset` (and, for the Eurostat record, `q=rail passengers`
with an EU corporate-body facet), then combined into one page.

Trimming: only the fields the harvester reads are kept (`id`, `title` in es/en, `language`,
`publisher` name/type/resource, `country`, `corporate-body-classification` id, `catalog` id and
English title, one `translation_meta` entry, up to three `distributions`). Publisher e-mail
addresses and homepages are removed. Each `description` is replaced by a placeholder sentence, so
the tests can show that descriptions never reach a candidate.

Synthetic changes: the Illes Balears CSV distribution gets a `download_url` and `byte_size`; the
Zaragoza record loses its `language` and every distribution `license` (tests `und` and `unknown`);
the Eurostat record is reduced to English only (tests the language filter).
`search-empty.json` is a synthetic empty page that ends paging.
