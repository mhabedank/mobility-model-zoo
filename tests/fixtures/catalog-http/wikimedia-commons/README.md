# Recorded Wikimedia Commons responses (feature 009)

Trimmed responses of the MediaWiki API (`https://commons.wikimedia.org/w/api.php`,
`action=query&generator=search&gsrnamespace=6&prop=imageinfo&iiprop=url|size|mime|extmetadata`,
`formatversion=2`), recorded on 2026-10-11 for `tests/catalog/test_harvest_wikimedia_commons.py`.
The shape is the live one; the content is reduced to a few files per search term.

- `search-bicicleta-0.json`: term `bicicleta`, first batch (continues at `gsroffset` 3): an SVG
  diagram, a photo, a chart in the public domain (US government category).
- `search-bicicleta-3.json`: term `bicicleta`, second batch: a photo in a "Patrimonio gráfico"
  category with an unmapped licence name, a photo under a ported CC licence.
- `search-carril-bici.json`: term `carril bici`: a map under the GFDL, a diagram under CC0.
- `maxlag.json`: the API's `maxlag` error, answered before a retry.

Personal data is replaced: page ids, file addresses and dimensions are synthetic, every uploader or
author (`extmetadata.Artist`, user pages, "Photographs by …" categories) is `Uploader A`, and the
only e-mail address is `uploader-a@example.org`. The tests assert that none of them reaches a
candidate. `Artist` is kept in the recordings although the harvester does not request it, to prove
it is ignored when present.
