# Contract: roadmap checks

`zoo roadmap check` runs RM1–RM8. `zoo site build` runs them too and fails on any finding, like the `B*` checks of feature 008. RM9 runs in `zoo site check` against the built site. Findings print as `<id> <where> <detail>`. "Today" is the UTC date, or `ZOO_TODAY` (ISO date) when set.

| ID | Check | Spec |
|---|---|---|
| RM1 | `zoo/roadmap/roadmap.yaml` exists and validates against [roadmap.schema.json](roadmap.schema.json); entry ids are unique | FR-001 |
| RM2 | Registry consistency: `model` names a registered, non-sandbox model whose topic equals `topic`; `topic` is a zoo topic other than `sandbox`; a `first-release` entry's model is registered; an open `update` entry's model has a published version; every registered, non-sandbox model without a published version has an open `first-release` or `new-model` entry naming it; a `new-model` entry with `model` has `working_name: false` | FR-018, FR-019 |
| RM3 | Text: `text` ≤ 20 words, `precondition` ≤ 8 words, move and drop reasons ≤ 20 words; none contains a free-standing number (`facts.NUMBER`), a `{metric:…}` placeholder or a release-status word (`budgets.STATUS_WORDS`) | FR-004 |
| RM4 | Horizons: exactly three; the first spans one quarter, the second and third two quarters each, consecutive without gaps. Entries: `horizon` equals `planned` when there are no moves, else the `to` of the last move; move dates ascend; an open entry's `horizon` is one of the three; at most 6 open entries per horizon; an entry is not both dropped and delivered | FR-002, FR-006, FR-005 |
| RM5 | First planned horizon fixed: for every entry, `planned` equals its value in the first commit of `zoo/roadmap/roadmap.yaml` that contains the entry's id (git history; passes trivially on a shallow clone, the site workflow uses the full history) | FR-003, constitution 2.3.0 |
| RM6 | Staleness: `as_of` is not in the future and at most 100 days before today; no open entry has a `horizon` whose end is before today. Warning only: today is within 14 days of the first horizon's end | FR-018 |
| RM7 | Reviews: for every quarter from `since` up to the quarter before the first horizon's start, `zoo/roadmap/reviews/<quarter>.md` exists and its `## Re-planning` section has at least one sentence of text | FR-018, FR-025, constitution gate |
| RM8 | Delivery: `delivered_by` names a version of `model` that has a published release record (`published.published_at` set) | FR-018, constitution 2.3.0 |
| RM9 | Rendered parity (`zoo site check`): the roadmap page lists exactly the open entries, per horizon in record order, each with an element `id="<entry id>"`; the start page shows one card per open `new-model`/`first-release` entry and no tile for an unpublished model; the counts in the models heading equal the tiles and cards shown | FR-005, FR-014, FR-017, SC-004 |

## Changes to existing checks

- **L1**: covers the roadmap page and the card links `roadmap/#<id>` (anchors from RM9).
- **A1–A5, S1, S2, P1–P3, E1, L3**: run on `roadmap/index.html` like on every page; no change to the checks themselves.
- **B6, O1–O5**: one more preview image (`roadmap/`); share line from `zoo/site.yaml` → `roadmap.share_line`, else the default "What the zoo plans to release next." (no numbers).
- **F2**: unchanged; the roadmap template has no literal numbers (horizon labels and dates come from data).
- **Start page test of feature 008** (in-progress tiles): replaced by RM9; unpublished models are no longer tiles.
