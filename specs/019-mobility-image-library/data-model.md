# Data Model: Mobility image library in the house style

Feature: [spec.md](spec.md) · Research: [research.md](research.md) · Builds on the [016 data model](../016-emotional-imagery-motifs/data-model.md).

All records are files in the repository. Nothing is stored at run time.

## Image record: `zoo/site/images/<id>/image.yaml` (changed)

Schema: [contracts/image-record.schema.json](contracts/image-record.schema.json). Changes against 016:

| Field | Change | Rule |
|---|---|---|
| `theme` | **new, required** | One of `rail`, `public-road`, `private-road`, `active`, `water`, `air`, `infrastructure`, `workshop`, `iot`, `ai` |
| `subject` | **new, required** | Slug of the subject in the series file; `theme/subject` must exist in the series (I2) |
| `round` | new, optional | Integer, the rendering round the image was picked in (absent for the six 016 images) |
| `placements` | `minItems` 0 | Empty list means "in the pool, not on the site" |
| `aspect` | rule relaxed | `start-hero` still requires `16:9`; any other placement, and no placement, accepts `16:9` or `3:2` |
| `source.file` | now optional | When present, the file must exist and match `sha256` (I1). When absent, `sha256`, `width`, `height` describe the source the generator wrote (kept outside git, R1) |
| `focal_point` | unchanged | Default from the accent centroid of check I6; may be overridden in `picks.yaml` |
| `checks.style` | **new, required** `pass` | Check I6 (R4) |
| `checks.duplicate` | **new, required** `pass` | Check I7 (R5) |
| `checks.measures` | new, optional | The I6 numbers for audit: `other_share`, `accent_share`, `accent_largest_share`, `accent_top_share`, `accent_centroid` |

Derivatives stay three per image. The directory holds `image.yaml`, `<id>-480.webp`, `<id>-960.webp`, `<id>-1600.webp`, and for the six 016 images also `<id>.png`.

**Validation** (I1, I2, I6, I7, L1): every check `pass`; every hash matches its file; theme and subject exist in the series; no two records share a placement; every placement names an existing topic or shown model; no two records are near-duplicates; the sum of all derivative bytes under `zoo/site/images/` ≤ 40 MB.

**Lifecycle**:
1. `candidate`: rendered on the Spark in a round, in the round's `manifest.json`, not in the repository.
2. `shown` or `rejected`: after `triage`, in the round's `triage.json`; shown candidates are on the sheet.
3. `picked`: in the round's `picks.yaml`; imported by `pick`, now a record with `placements: []` (`pool`).
4. `placed`: a placement is recorded; the next build copies it and lists it on the credits page; the set digest changes and the deployment asks for approval.
5. `removed`: directory deleted; placements fall back as in 016.

## Series: `zoo/site/images/series/siebdruck.yaml` (changed)

| Field | Change | Content |
|---|---|---|
| `name`, `style`, `models` | unchanged | |
| `negative` | changed text | Gains `brain, glowing network, hologram, floating icons, circuit pattern` (R2) |
| `negative_history` | **new** | List of earlier `negative` texts; I2 accepts the current or any listed one |
| `themes` | **new** | Map theme id → list of subject objects (below). Replaces `subjects` |
| `subjects` | removed | The six 016 prompts move into `themes` with ids |
| `palette` | **new** | Anchors `{navy, mint, cream, accent}` as Lab triples, `tolerance_de`, and the I6 thresholds `other_max`, `accent_min`, `accent_max`, `largest_min`, `top_max` (R4) |
| `duplicate_max_bits` | **new** | The I7 threshold (R5), provisional 10 |

**Subject object**:

| Field | Rule |
|---|---|
| `id` | Slug, unique within the theme |
| `prompt` | The subject text; the record's prompt is `prompt + ", " + style` (I2) |
| `aspect` | Optional, `16:9` or `3:2` (default) |
| `scene` | 20 to 120 characters; copied into the record |
| `alt` | One sentence; the record gets it with the suffix "(AI-generated image)"; 40 to 160 characters after the suffix |
| `reserve` | Optional `true`: rendered only when the theme is under its minimum after a round |

Theme minimums and the 20% cap are constants of the check (`images.THEME_MINIMUMS`, `images.THEME_CAP`), not series data, because they are the spec's coverage table.

## Rendering round: `specs/019-mobility-image-library/rounds/<n>/`

Committed audit trail of one round (FR-007). The PNGs and the sheet are not committed.

| File | Written by | Content |
|---|---|---|
| `manifest.json` | generator (copied) | One entry per candidate: the full recipe as in 016, plus `theme`, `subject`, `seed_base` |
| `triage.json` | `zoo site images triage` | Per candidate: `file`, `theme`, `subject`, `number` (1-based within the subject among shown ones, `null` if rejected), `outcome` (`shown`/`rejected`), `reasons` (list of `{check, detail}`), `measures` (I6 numbers), `phash`, `focal_default`; plus `round`, `container`, `generator`, `tools`, `ran` |
| `picks.yaml` | the owner (via chat, written by the agent) | `round`, `picks`: map `theme/subject` → number or `none`, optional `focal` per pick, optional `id` override |
| `next.txt` | `pick` | Subjects for the next round: `none` picks and subjects without a shown candidate |

Round directories on the machines (not committed): `~/zoo-imagery/rounds/<n>/` on the Spark holds `*.png` and `manifest.json`; the developer machine's copy adds `triage.json`, `sheet.html`, `thumbs/<file>-480.webp` (the cached derivatives) and `picks.yaml`.

## Contact sheet (derived, local)

`sheet.html` in the round directory: a static page without scripts. Order: "needs another round" (subjects with no shown candidate, with their rejection reasons), then themes in the coverage-table order, then subjects in series order, then shown candidates by number. Each candidate: 480 px thumbnail (links to the PNG), number, seed, I6 measures in a `title` tooltip. Rejected candidates of a subject: one collapsed line "rejected: #seed (I4 text 'ROUTE'), #seed (I7 twin of 2)".

## Pool overview (derived, local)

`.cache/site/pool.html` from `zoo site images overview`: themes in coverage-table order with "n of minimum m, cap c"; each record as its 480 px derivative with id, subject, aspect, placements, round. Built from records only; no round data.

## Placement resolution (unchanged)

As in 016. A library image takes part only when a placement names it. The fallback table is unchanged.

## Credits entry and compliance blocks

Credits (`/credits/`): **placed records only**, as 016 defines them. Compliance blocks (`REUSE.toml`, `THIRD_PARTY_NOTICES.md`, record of processing): **all records**, because their files are in the repository.

## Coverage (derived)

`zoo site images check` prints per theme: count, minimum, share; `--require-coverage` fails when a theme is under its minimum, over the cap, or the total is under 100 (L2). The quickstart uses it as the acceptance of SC-001.
