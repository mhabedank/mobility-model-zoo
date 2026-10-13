# Data model: Roadmap and delivery pace

Phase 1 of [plan.md](plan.md). The record format is fixed in [contracts/roadmap.schema.json](contracts/roadmap.schema.json); the checks in [contracts/checks.md](contracts/checks.md).

## Files

| File | Written by | Content |
|---|---|---|
| `zoo/roadmap/roadmap.yaml` | owner (by hand, in pull requests) | the roadmap record: date, horizons, entries with their history |
| `zoo/roadmap/reviews/<quarter>.md` | `zoo roadmap pace <quarter> --write`, then the owner | the pace review of a closed quarter, with a hand-written "Re-planning" section |
| `zoo/site.yaml` → `roadmap.share_line` | owner | the share line of the roadmap page's preview image (optional) |
| `zoo/models/<name>/releases/<version>.yaml` | release pipeline (unchanged) | `published.published_at`: the delivery date of the entries it delivers |

## Roadmap (`roadmap.yaml`, top level)

| Field | Type | Rules |
|---|---|---|
| `as_of` | date | date of the last review of the plan; not in the future; at most 100 days old (RM6) |
| `since` | quarter id | first quarter the roadmap covers (`2026-Q4`); never changes; reviews are required from here on (RM7) |
| `horizons` | list of 3 horizon ids | first: one quarter; second and third: two consecutive quarters each; no gaps (RM4) |
| `entries` | list of entries | order = priority within a horizon (FR-005); ids unique |

## Horizon id

Grammar: `YYYY-Qn` (one quarter) or `YYYY-Qa..Qb` (two quarters in one year, `b = a + 1`) or `YYYY-Q4..ZZZZ-Q1` (across a year, `ZZZZ = YYYY + 1`).

| Derived | Rule | Example |
|---|---|---|
| start | first day of the first quarter | `2027-Q1..Q2` → 2027-01-01 |
| end | last day of the last quarter | `2027-Q1..Q2` → 2027-06-30 |
| label | `Qn YYYY`; `H1 YYYY` for `Q1..Q2`; `H2 YYYY` for `Q3..Q4`; else `Qa–Qb YYYY` or `Q4 YYYY – Q1 ZZZZ` | `2026-Q4` → "Q4 2026"; `2027-Q2..Q3` → "Q2–Q3 2027" |
| months | month names of start and end | "October – December" |

## Entry

| Field | Type | Required | Rules |
|---|---|---|---|
| `id` | slug `[a-z0-9-]+` | yes | unique, never reused; anchor on the roadmap page (`#<id>`) |
| `name` | string | yes | the registered model name, or a working name |
| `working_name` | bool | yes | `true` until the model is registered; must be `false` when `model` is set for a `new-model` entry |
| `model` | model name | for `first-release` and `update`; for `new-model` once registered | must be a registered, non-sandbox model (RM2) |
| `topic` | topic id | yes | one of `zoo/topics.yaml`, not `sandbox`; equals the model's topic when `model` is set |
| `kind` | `new-model` \| `first-release` \| `update` | yes | `update`: `model` is published; `first-release`: `model` is registered (RM2) |
| `stage` | `planned` \| `in-progress` | yes | `in-progress` only while work on it runs (owner decision 2026-10-12; not machine-checked) |
| `text` | string | yes | ≤ 20 words; no free-standing number, no placeholder, no release-status word (RM3) |
| `precondition` | string | no | ≤ 8 words; same text rules (RM3) |
| `planned` | horizon id | yes | the horizon the entry was first planned in; unchanged since the entry was added (RM5) |
| `horizon` | horizon id | yes | current horizon; equals `planned` without moves, else the `to` of the last move; for an open entry one of `horizons` (RM4) |
| `moves` | list of `{date, to, reason}` | no | dates ascending; `reason` ≤ 20 words |
| `dropped` | `{date, reason}` | no | an entry with `dropped` is closed; it may not also be delivered |
| `delivered_by` | `{model, version}` | `update` only, once released | that version is published (RM8) |

### Derived per entry

| Value | Rule |
|---|---|
| delivering release | `update`: `delivered_by`; `first-release`/`new-model`: the lowest published version of `model`, if any |
| delivery date | UTC date of `published.published_at` of the delivering release |
| state | `dropped` if `dropped`; else `delivered` if a delivering release exists; else `open` |
| timing (delivered only) | against `planned`: `early` (date < start), `on time` (start ≤ date ≤ end), `late` (date > end); slip = date − end in days, and in quarters started after the end |
| usage label | from `model`'s `usage_class`: `commercial-share-alike` → "share-alike", `non-commercial` → "non-commercial", `commercial` or no `model` → none (FR-007) |
| motif | `motif` of the model's `site.yaml` if present, else `<model>.svg` if it exists, else none |

### State transitions

```text
open ──(release published)──────────▶ delivered   (date from the release record)
open ──(moves += {date, to, reason})─▶ open        (horizon := to; planned unchanged)
open ──(dropped := {date, reason})──▶ dropped
```

Delivered and dropped entries stay in the record (FR-026) and leave page and cards.

## Pace review (`reviews/<quarter>.md`)

Generated sections (from [contracts/pace-report.md](contracts/pace-report.md)): delivered (early, on time, late with slip), due and missed, moved, dropped, unplanned releases, counts and delivery rate, trend over reviewed quarters. Hand-written section: `## Re-planning` with at least one sentence on how the next horizons were filled from the measured pace (RM7, FR-025).

## Page context (what the templates receive)

- `roadmap.as_of`, `roadmap.horizons[]`: `{id, label, months, start, end, is_first}`, each with its open `entries[]` in record order.
- `entry`: `{id, name, working_name, model, topic_title, kind, stage, text, precondition, usage_label, motif, model_url}`. `model_url` is set only for `update` (FR-011).
- `upcoming[]` (start page): open entries of kind `new-model` or `first-release`, ordered by horizon, then by record order, each with `horizon_label`.
- `counts`: `{published, upcoming}` (FR-017).

## Initial record

The proposed roadmap of the spec (order approved 2026-10-12): 6 entries in `2026-Q4`, 6 in `2027-Q1..Q2`, 3 in `2027-Q3..Q4`; `since: 2026-Q4`; `as_of: 2026-10-12`. Ids: `picket-forest-board`, `scout-large-reader-test`, `pace-cnn`, `hum-fan`, `hum-bearing`, `picket-mlp`, `mode-cnn`, `cell-soh`, `gnss-guard`, `scout-large-languages`, `jtbd-cluster`, `picket-forest-control`, `rough-road`, `v2x-guard`, `picket-signal`.
