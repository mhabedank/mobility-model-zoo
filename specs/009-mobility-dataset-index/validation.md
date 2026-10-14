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

## Scale-up batch 1 (catalog repository, 2026-10-11/12, T082)

Batch 1 covered the 20 remaining EU languages. Its runs are in catalog commits e27993c and 3dad640.

The first run on 2026-10-11 found three defects:

- **Search terms.** `terms.yaml` had terms only for en, es, pl and ja, so the harvesters searched the other 20 languages with English terms. Hungarian got 0 hits.
- **Dedupe identity.** Dedupe treated a shared access address as the same resource. Distinct datasets behind one WFS endpoint, catalogue search page or publisher page were merged into one entry.
- **Network check crash.** One host label over 63 characters crashed the network check after 2.5 hours. Nothing was saved, because the check writes only at the end of a run.

All three are fixed in PR #28. The catalog was then reset to the pilot commit and batch 1 run again.

Data that national portals hand to data.europa.eu without a licence:

- dane.gov.pl (Poland) and data.gov.lv (Latvia): the licence is now read from the portal's own API.
- si and hu: the portals publish no licence.
- hr and ro: the portals did not answer.
- cy and bg: no usable API.

Owner decision on 2026-10-11: a dataset that declares no language takes the original language of its title, and the quality rationale says so. This applied to 810 entries.

Result after batch 1:

- 5,051 entries in total.
- 24 target languages besides de and en have entries, and each of them has at least one `training_allowed` entry.
- 54.5% of entries have a determined licence; the SC-004 target is 80%. The lowest shares are et 2%, bg 8%, sl 10%, cs 16%, hr 20% and hu 23%.

## Scale-up batch 2 (catalog repository, 2026-10-12, T083)

Batch 2 covered the world languages zh, ja, ko, hi, ar, tr, ru, id, uk and vi. The sources were
OpenAlex, Zenodo, Mobility Database (CN, KR, IN, SA, AE, EG, TR, ID, UA, VN) and Hugging Face,
followed by the network check.

The index now holds 6,391 entries:

| Status | Entries |
|---|---|
| cleared | 2,961 |
| verified | 2,490 |
| candidate | 940 |

| Permitted use | Entries |
|---|---|
| training_allowed | 2,770 |
| benchmark_only | 617 |
| undetermined | 2,947 |
| not_usable | 57 |

Owner targets for the first version:

- At least 2,000 entries: met, with 6,391.
- At least 30 languages besides de and en: met, with 32. Each of the 32 has at least one `training_allowed` entry.
- The coverage report shows no target-language gap. Of the 34 targets, de has entries but no `training_allowed` entry yet.

Still open:

- 58.4% of entries have a determined licence; the SC-004 target is 80%.
- Audio, video, image and graphic have no usable entry. Batch 3 (T084) addresses these modalities.

## Scale-up batch 3, media (catalog repository, 2026-10-12/13, T084 in part)

Wikimedia Commons was searched over all 34 target languages for images and graphics, then for video and audio. For video and audio the harvester gained two genres, `footage` and `field_recording`. Catalog commits: ec6a1f0, 84a0f3f, 38ae0ab.

Owner decision D-catalog-licences-2026-10b added these licences to the list:

- CC BY 2.0 and 2.5;
- CC BY-SA 2.0 and 2.5;
- CC BY-SA 3.0, which now trains;
- LicenseRef-public-domain.

Jurisdiction ports count as their listed version.

The index after batch 3:

- 7,840 entries in total, 4,419 of them cleared.
- 4,219 entries are `training_allowed`, and 65.8% have a determined licence.
- `training_allowed` by modality: 846 images, 81 graphics, 350 videos and 139 audio files.
- The coverage report shows no gap for any target language or modality.

Two parts of T084 are still open:

- `podcast-index` needs the owner's API key.
- Agent discovery (`catalog-discover`) has not run yet, because the coverage report shows no gap left to fill.

## Final measurement (catalog repository, 2026-10-14, T085)

The index holds 7,840 entries:

| Status | Entries |
|---|---|
| cleared | 4,077 |
| verified | 2,900 |
| candidate | 863 |

The usage rules are at rules version 3. By permitted use:

| Permitted use | Entries |
|---|---|
| `training_allowed` | 4,309 (199 of them for non-commercial models only) |
| `undetermined` | 3,232 |
| `benchmark_only` | 235 |
| `not_usable` | 58 |

| Criterion | Result | Met |
|---|---|---|
| SC-001 mandatory facts and vocabularies | `zoo catalog validate` passes on all entries | yes |
| SC-002 at least 2,000 entries, at least 30 target languages besides de and en with at least 20 entries each | 7,840 entries; 30 of 32 languages reach 20 (ga has 14, mt has 19) | yes |
| SC-003 at least 50 entries per modality | text 3,159; structured data 3,177; image 874; video 381; audio 166; graphic 83 | yes |
| SC-004 at least 80% of entries with a determined licence; 100% of cleared entries carry evidence | 65.8% determined; 4,077 of 4,077 cleared entries carry evidence | no (80% part) |
| SC-005 at least 90% re-check agreement; no cleared entry re-read as not usable | Holdout seed 13: model 93%, matcher 83%. Two cleared entries are each read as not usable by one reader; the other reader confirms them | no (matcher part) |
| SC-008 under 2% duplicates in 50 entries | 0 of 50 in each run | yes |
| SC-009 every cleared entry re-checked within 6 months | All re-checked on 2026-10-14 | yes |

SC-006 is measured by the owner, and SC-007 by the later download feature.

### Audit runs (SC-005)

Two readers re-read the licence evidence of 30 seeded entries: a deterministic matcher and a local model on the DGX Spark. The matcher and the readers were improved between runs.

The runs on seeds 9 and 11 were used to find the problems and fix them, so their late results are tuning results, not measurements. Seed 13 had not been used before it was measured, so it is the holdout and the reported result.

| Run | Seed | Model | Matcher | Model agreement | What the run found |
|---|---|---|---|---|---|
| 1 | 9 | qwen3:30b | 37% | 54% | data.europa.eu and Zenodo pages are app shells; model answers were not mapped to catalog ids; Licence Ouverte was read as OGL-UK |
| 2 | 9 | qwen3:30b | 77% | 50% | the model saw only the first 6,000 characters |
| 3 | 9 | qwen3:30b | 83% | 67% | OpenAlex licences that neither the page nor Crossref states; a paper listed CC BY-NC whose publisher page reserves all rights |
| 4 | 9 | qwen3.6:35b | 77% | 86% | blocked entries still showed `training_allowed`; unreadable evidence counted as disagreement |
| 5 | 9 | qwen3.6:35b | 100% | 100% | not valid: a reading of a flagged entry agreed whatever it read |
| 6 | 9 | qwen3.6:35b | 100% | 97% | tuned on this sample |
| 7 | 11 | qwen3.6:35b | ≥90% | 77% | written-out Creative Commons names; dane.gov.pl app shell; the model answered unknown for JSON records |
| 8 | 13 | qwen3.6:35b | 83% | 93% | the matcher missed MIT on a Hugging Face card and confused ODbL with ODC-By (both fixed after the measurement) |

### What changed in the catalog because of the audit

- **K5 licence conflict.** An evidence page that reserves all rights against an open licence sets the blocking flag `licence_conflict` (24 entries).
- **OpenAlex evidence** (owner decision D-catalog-openalex-evidence-2026-10). An OpenAlex licence clears only if the evidence page or the DOI registry states it; otherwise K5 sets the blocking flag `licence_unconfirmed` (271 entries). Rule U2 makes both kinds of entry `undetermined`.
- **K5 change detection.** A licence change is now a change of the licence read from the page, not of the page bytes. Changing page bytes had revoked 2,526 clearings in one re-check.
- **Readers.** Both readers now read portal APIs for app shells and the DOI registry licence (Crossref, DataCite). The matcher recognises written-out Creative Commons names in ten languages, the national licence names, MIT and Apache.

### Open

- SC-004: the share of determined licences is too low. National portals publish no licences: et, bg, sl, cs, hr, hu and cy.
- SC-005: on the holdout the matcher is below 90%. Measure again with an unused seed at the next monthly re-check.
- `podcast-index` needs the owner's key.
