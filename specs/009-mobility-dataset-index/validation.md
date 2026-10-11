# Validation: Mobility resource index

**Feature**: [spec.md](spec.md) | **Quickstart**: [quickstart.md](quickstart.md)

## Quickstart scenarios 1–5 (fixture catalog, 2026-10-11, T079)

| Scenario | Result |
|---|---|
| 1. Mandatory facts enforced | Pass. Validation and duplicate tests are green. The 12 valid fixture entries pass. Each of the 7 invalid entries fails with its intended check: K1 for no licence, `blog` kind, `zxx`+`es`, `evidence_url: null` and empty subdomains; K2 for the missing parent; K9 for an e-mail address. |
| 2. State machine and clearing rules | Pass. One case per rule U1–U6, the owner decision U0, the clearing conditions (an API key is allowed, an account is not), the fallback after a changed re-check, and retirement after three 404/410 answers at least 7 days apart. |
| 3. Query and coverage report | Pass. `query --lang es --lang pt --modality video --use training_allowed` returns `pt-lecture-cycling`, as `EXPECTED.md` lists. The coverage report shows 11 of 12 licences determined (91.7%), keeps the machine-translated English apart, and reports `graphic` as the only modality gap. |
| 4. Ingest and duplicates | Pass. 10 candidates give 7 new entries, 2 merges (same address, same DOI) and 1 rejected line (missing evidence). The run header lists every language × modality cell, including empty ones. |
| 5. Fetch list hand-off | Pass. 6 cleared entries become items and 6 are refused with reasons. Text records validate against `sources.schema.json` and structured-data records against `datasets.schema.json` once the fetch-time fields are added. |

Test totals at this point: the catalog tests (`tests/catalog`), the extended signal tests
(`tests/compliance/test_signals.py`), and the compliance, datasets, release and guard suites are all
green. The Mobility Database and Hugging Face harvesters were still being written by a parallel
agent.

## Harvester smoke runs (live APIs, small limits, outputs deleted)

| Harvester | Scope | Candidates | Ingest |
|---|---|---|---|
| data-europa | es, public_transport, limit 5 | 5 | 5 accepted, 0 rejected |
| zenodo | es, public_transport, limit 5 | 5 | 5 accepted, 0 rejected |
| openalex | es, pl, ja, public_transport, limit 15 | 15 | 15 accepted, 0 rejected |
| wikimedia-commons | es, cycling, limit 8 | 8 | 8 accepted, 0 rejected |
| podcast-index | no key yet | – | built from the official API description; synthetic test responses |

Findings from these runs:

- **OpenAlex budget.** The free key allows 10,000 credits a day, and one search page costs 10 credits. The harvester stops at 80% of the allowance, and also earlier when the account's remaining-credit headers fall below 20%.
- **data.europa.eu language filter.** The API has no language filter. The harvester searches with terms in the target language and keeps a dataset only when its language metadata lists that language.
- **OpenAlex topic filter.** The harvester restricts OpenAlex results to transport-related subfields. Without this filter the term search also returned literature, so precision wins over recall here.

## Pilot v1 (catalog repository, 2026-10-11, T058–T060)

The pilot criteria were committed before the first run (catalog commit 7cbacc1). The runs, entries
and reports are in catalog commit faacb9a, and the full report is
`catalog:reports/2026-10-11-pilot.md`.

| Language | Accepted | Licence determined | `training_allowed` | Result |
|---|---|---|---|---|
| es | 353 | 77% | 180 | PASS |
| pl | 282 | 72% | 167 | PASS |
| ja | 178 | 58% | 43 | PASS |

**Overall: PASS**, so the scale-up (T082–T085) may start.

Index after the pilot: 1,270 active entries, of which 782 are cleared. 76.4% have a determined
licence; the SC-004 target is 80%.

What the pilot changed in the code:

- **Gzip fix.** The network check decoded cached robots.txt responses twice.
- **HTTP 429.** The shared client now retries after Retry-After.
- **Progress output** is now reported in completion order.
- **dane.gov.pl licences.** data.europa.eu drops the reuse conditions of dane.gov.pl, so the
  data-europa harvester now reads them from the dane.gov.pl API. This raised the Polish determined
  licences from 41% to 72%.

Still open:

- Video and audio have no `training_allowed` entry in the three pilot languages. YouTube falls
  under platform terms, and the podcasts have no licence.
- The owner queue holds 111 flags, 70 of them possible duplicates.
