# OpenAlex recorded responses

Trimmed recorded responses, personal data removed. Recorded on 2026-10-11 from
`GET https://api.openalex.org/works` with
`filter=language:es,open_access.is_oa:true,has_doi:true,topics.subfield.id:3313|3322|3305|2203|2202|2212|2205|1803,title_and_abstract.search:ferrocarril|"tren de cercanías"|"transporte ferroviario"`,
`select=id,doi,display_name,language,publication_date,primary_location,best_oa_location,authorships`,
`per_page=3`, cursor paging (`works-es-rail-1.json` for `cursor=*`, `works-es-rail-2.json` for the
next cursor).

Trimming: only the fields the harvester reads are kept. Every author name is replaced by the
placeholder `Author A`; author ids, ORCIDs, raw author names and affiliation strings are removed;
institutions keep only `country_code`. `meta` keeps `count`, `per_page`, `next_cursor` and
`cost_usd`; the second page's `next_cursor` is set to `null` so paging ends there. Work titles,
DOIs, journal and publisher names are bibliographic metadata and stay as recorded.

The rate-limit headers (`x-ratelimit-*`) are set by the test's mock transport.
