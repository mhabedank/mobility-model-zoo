# Synthetic Podcast Index responses (feature 009)

Responses of `GET https://api.podcastindex.org/api/1.0/search/byterm` for
`tests/catalog/test_harvest_podcast_index.py`. The owner has no Podcast Index key yet, so these are
**not recordings**: they are written by hand after the response schema of the official OpenAPI
document (https://podcastindex-org.github.io/docs-api/pi_api.json, read 2026-10-11, response
`search_byterm`, schema `feed_search`). Re-record them, trimmed and with the same placeholders,
once a key exists.

- `search-bicicleta.json`: term `bicicleta`: an association feed (es-ES), a private person's feed
  (es-mx, e-mail address in `author`), a pt-br feed (outside an `es` scope), a `music` medium feed,
  a dead feed, and an Atom feed without link and author (only `ownerName`).
- `search-carril-bici.json`: term `carril bici`: the first feed again (deduplicated).
- `unauthorized.json`: the error body sent with HTTP 401 for a wrong signature.

All names, addresses, ids and GUIDs are placeholders (`example.org`, `Persona Ejemplo`, …). The
documented feed object has no `podcast:license` field, so harvested podcasts carry licence
`unknown`.
