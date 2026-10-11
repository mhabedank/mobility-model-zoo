# mobility-model-zoo-catalog

The private resource index of the [mobility model zoo](https://github.com/mhabedank/mobility-model-zoo)
(feature 009): mobility-related texts, audio, video, images, charts and structured data in many
languages, with language, area, publisher, kind and type of source, licence, opt-out signals and
access routes.

Rules:

- **Metadata only.** This repository never holds the content of a resource: no downloaded files,
  no copied abstracts, no transcripts. Descriptions are written in our own words.
- **No personal data** beyond the names of publishers, public bodies and creators where
  attribution requires them. `zoo catalog validate` (check K9) flags contact data and user handles.
- **Private until published.** Publication as an open catalogue is a separate step with its own
  release check.

Layout: `entries/<area>/<id>.yaml` (one entry per file), `runs/` (discovery runs), `fetch-lists/`,
`reports/`, `pilot/`. Schemas, vocabularies and rules live in the zoo package
(`src/mobility_model_zoo/catalog/`); see `docs/catalog.md` there.

```bash
zoo catalog --catalog . validate
```
