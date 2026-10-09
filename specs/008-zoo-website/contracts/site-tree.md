# Contract: site tree and page content

The base is `https://mhabedank.github.io/mobility-model-zoo/`. All internal links are relative. Every page has:

- the header: mark, wordmark, and navigation (Models, Topics, Principles, Hugging Face, GitHub);
- the footer: imprint, privacy notice, copyright policy, licence, and the line "Private, non-commercial project. No cookies, no analytics, no third-party requests.";
- `lang="en"`, one `h1`, landmark elements, and a skip link;
- the `color-scheme: light dark` meta and the tokens of both themes.

## `/` start page

In this order:

1. Hero: the zoo's purpose (`zoo/site.yaml` tagline) and two actions, "Browse the models" and "Read the principles".
2. Three short value points (local, measured on frozen data, published with a model card). These are the principles in short form, without numbers.
3. Topics: one block per topic in `topics.yaml`, with its title, description and HF collection link.
4. Models: one tile per non-sandbox model, with name, topic, task, latest version and a status chip. Published and deprecated tiles link to the model page; "in progress" tiles do not link.
5. Principles: the four from `zoo/site.yaml`.

## `/models/<name>/` model page (status published or deprecated)

In this order, with an anchor for each section:

| # | Section | Anchor | Content | Source |
|---|---|---|---|---|
| 1 | Hero | `#top` | title, tagline, audience, language chips, licence chip, CTA "Quickstart" | model.yaml, site.yaml |
| 2 | Why this model | `#why` | differentiators with resolved metrics, each number linked to its footnote (reference / hardware) | site.yaml + results |
| 3 | Quickstart | `#quickstart` | install line pinned to the latest tag, `how_to_run` with repo/revision filled, input (the quickstart example) and its output, hardware/memory note | model.yaml `card.*`, release record, examples |
| 4 | Interface | `#interface` | input description, a field table of the output format (link to `/formats/<id>/`), dimensions with allowed values, how the format is versioned, edge cases (empty text, irrelevant text, long text, other language) | model.yaml `input_output`, OutputFormat |
| 5 | Worked examples | `#examples` | span formats: one output viewer per example (the text with marked quotes, kind by colour and underline style; the JSON item list; the full raw JSON in a `<details>` element). Other formats: input and output as code blocks | Example |
| 6 | Quality and speed | `#quality` | a visible line with the frozen benchmark version, the deterministic checks (verbatim quote rate, schema-valid rate, consistency rate) and the number of contested items; metric cards (composite vs best baseline, latency per machine, memory, throughput); the charts declared in `site.yaml` with text alternatives; the full metric table in `<details>` | results JSON, site.yaml `charts` |
| 7 | Use and limits | `#limits` | intended use, out of scope, every limitation in full (callout) | model.yaml `card.*` |
| 8 | Licence and provenance | `#provenance` | licence, base model + licence, links to the training-data summary, source attribution, AI Act note and compliance record of the latest release | model.yaml, release files |
| 9 | Versions | `#versions` | table: version, date, status, format, changes, HF revision link; deprecated versions are marked | release records |
| 10 | Cite | `#cite` | citation block with a copy button | model.yaml `card.citation` |

A deprecated model shows a banner at the top that names the successor if one is given.

## `/formats/<id>/` output format page

The full field table, the meaning and empty case of each field, the release versions that produce the format, and a link to the JSON schema file on GitHub at the tag of the latest producing release. Format pages are never removed (US2 scenario 3).

## `/404.html`

Header, a short message, links to `/` and to the models list.

## Assets

`/assets/css/tokens.css`, `/assets/css/site.css`, `/assets/js/site.js`, `/assets/fonts/*.woff2` (+ `OFL.txt`), `/assets/img/mark.svg`, `/assets/img/favicon.svg`, `/assets/img/motifs/*.svg`.

Assets are served from the site only, with no hashes and no CDN.
