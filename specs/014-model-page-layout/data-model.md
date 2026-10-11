# Data model: Model pages in progressive depth

Extends the data model of feature 008 ([specs/008-zoo-website/data-model.md](../008-zoo-website/data-model.md)). Only the changes are listed.

## Inputs (hand-maintained, in the repository)

### `zoo/models/<name>/model.yaml` → `card` block (new optional fields)

| Field | Type | Rules | Shown in |
|---|---|---|---|
| `not_for` | list of strings, 2–3 items | each ≤ 15 words, together ≤ 40 words; no free-standing numbers; `{metric:…}` placeholders allowed | site layer 1 (overview), card "Summary" |
| `limits_short` | list of strings, 1–5 items | each ≤ 25 words; together with `unmet_criteria` ≤ 5 items and ≤ 120 words; no free-standing numbers; placeholders allowed | site layer 3 short form, card "Limitations and risks" (top) |
| `unmet_criteria` | list of objects | required and non-empty when the release status is `experimental`; absent or empty when `released` (gate rule 18) | site layer 3 short form, card "Limitations and risks" (top) |

`unmet_criteria` item:

| Field | Type | Rules |
|---|---|---|
| `criterion` | string | ≤ 12 words; no numbers; names the success criterion (for example "False alarms per hour on unknown vehicles") |
| `target` | object, optional | `op` (`<=`, `>=`, `<`, `>`, `=`), `value` (number), `unit` (string, may be empty); `source`: repository path of the task document that defines the criterion |
| `measured` | string, optional | `{metric:<kind>.<name>}` that resolves in the release's results |
| `note` | string, optional | ≤ 15 words; no numbers (for example "measured only in an emulator, not on a board") |

At least one of `measured` and `note` is present. Numbers on the page come only from `target.value` (source: `model.yaml`) and `measured` (source: results JSON); both are registered as facts (F1) and printed on the card (F4).

The fields are optional in `model.schema.json`, so `model.yaml` at older release tags remains valid. Presence is enforced by check D1 (site, published models) and gate rule 18 (new releases).

### `zoo/models/<name>/site.yaml` (changed limits)

| Field | Today | New |
|---|---|---|
| `differentiators` | 3–5 items, text free length | 3–4 items; `title` ≤ 5 words; `text` ≤ 20 words |
| `audience` | free length | ≤ 25 words |
| `metric_cards` | ≤ 6 | ≤ 4 (headline figures of layer 2) |
| `tagline` | ≤ 120 characters | unchanged; must not repeat the release status (it is generated) |

Word limits are checked by gate rule 17 (`pitch_errors`) and by check D2 on the rendered page; the JSON schema keeps its character limits as a first line. Feature 012's `share_line` is unaffected.

## Derived (built from the registry, not stored)

### Release status

`status` of the latest published release record: `experimental` | `released`. `zoo release deprecate` overwrites a record's status with `deprecated`; for such a record the release status is read from the record as committed at its release tag (`<name>/v<version>`), so the chip still says what the version was. Lifecycle `deprecated` (from `context.status`) stays separate and keeps its banner. Hand-written website text (`tagline`, `audience`, differentiators) must not state a release status (the words "experimental", "released", "production ready"); rule 17 and D4 reject it. Shown as a chip in layer 1; for `experimental`, a status sentence links to `#limits`. Wording comes from `card.BANNERS` (shared with the card).

### Layer

| Order | `data-layer` | Section id (anchor) | Contains | Old anchors kept inside |
|---|---|---|---|---|
| 1 | `overview` | `top` | name, task, topic, tagline, audience, status chip + sentence, usage class, licence, languages or target, differentiators, `not_for`, jump links, layer navigation | – |
| 2 | `quality` | `quality` | benchmark/check line, ≤ 4 headline figures (with comparison bar where a comparison exists), charts, link to `#metrics` | – |
| 3 | `limits` | `limits` | short form (status sentence, `unmet_criteria`, `limits_short`), evidence links, then full intended use, out of scope, limitations (collapsed) | – |
| 4 | `quickstart` | `quickstart` | hardware note, NC notice, install, run, expected output | – |
| 5 | `reference` | `reference` | interface short form, link to format page and schema, worked examples | `interface`, `examples`, `ex<N>` |
| 6 | `details` | `details` | all metrics tables, notes, licence and provenance, documents, versions, citation | `metrics`, `notes`, `fn-<N>`, `provenance`, `versions`, `cite` |

### Headline figure (unchanged source, new presentation)

From `metric_cards`: label, value, unit, note number, `against` text; optional comparison value and label. New: when a comparison exists, a bar pair (value and comparison on one scale) rendered as inline SVG with the numbers as text; the facts are the same as today's card values (no new facts).

### Budget

A constant table in the site package: per layer the counted scope, the limit and the check ID. Values are the starting budgets of [research.md R5](research.md#r5-word-budgets-measured-on-rendered-text-enforced-twice). One table feeds the gate (rule 17, 18), the offline checks (D2–D4) and the docs.

## State and validation summary

| When | What is validated | Where |
|---|---|---|
| Release gate, every new release | site text budgets (rule 17 extended); `not_for`, `limits_short` present; `unmet_criteria` consistent with status, metrics resolve, targets have a source (rule 18) | `zoo check` |
| Site build and check | short forms present for every published model (D1); rendered budgets (D2–D4); layer order and anchors (D5); placement on screen (D6, browser) | `zoo site check` |
| Card render | section order equals `card.SECTIONS`; short-form blocks only when the fields exist | `tests/release/test_card_build.py` |
