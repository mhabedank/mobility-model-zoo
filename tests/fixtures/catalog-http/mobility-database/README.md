# Mobility Database: trimmed recorded responses

Trimmed recorded responses of the Mobility Database catalogue API
(`https://api.mobilitydatabase.org/v1`), recorded on 2026-10-11 for
`tests/catalog/test_harvest_mobility_database.py`.

- `gtfs_feeds-<CC>.json`, `gtfs_rt_feeds-<CC>.json`: `GET /v1/gtfs_feeds` and `/v1/gtfs_rt_feeds`
  with `country_code=<CC>`, reduced to a few feeds each (active, inactive and cross-border ones).
  Fields the harvester does not read (`latest_dataset`, `bounding_box`, `reliability_seal`, …)
  are removed, `locations` is cut to at most three entries, `related_links` is emptied and `feed_contact_email` is blanked.
- `tokens.json`: the shape of the `POST /v1/tokens` answer with a placeholder access token.

No feed content and no personal data.
