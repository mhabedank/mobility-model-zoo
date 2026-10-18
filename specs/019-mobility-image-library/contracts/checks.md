# Contract: checks added or changed by feature 019

Extends the [016 checks](../../016-emotional-imagery-motifs/contracts/checks.md). A check not listed stays as it is.

## New checks

| Id | Kind | Rule | Requirement |
|----|------|------|-------------|
| **I6** | triage, deep | Style: in CIELAB at 240 px, pixels are assigned to the series' palette anchors within `tolerance_de`; `other` share ≤ `other_max` (12%); `accent` share within `accent_min` (1.5%) and `accent_max` (30%); the largest connected accent region holds ≥ `largest_min` (50%) of accent pixels; accent pixels in the top fifth ≤ `top_max` (15%) of accent pixels unless the largest region reaches into the top fifth. Thresholds and anchors come from the series file, calibrated on the six approved 016 images (research R4). The finding names the failed rule and the measured value. | FR-006 |
| **I7** | triage, static | Duplicate: 64-bit pHash Hamming distance ≤ `duplicate_max_bits` (provisional 10) to any library record or any earlier shown candidate of the same round rejects the candidate and names the twin. Over the records, `zoo site images check` reports any pair within the threshold. | FR-005 |
| **L1** | static | The sum of all derivative bytes under `zoo/site/images/` is ≤ 40 MB. The finding names the three heaviest records. | FR-016 |
| **L2** | static (`--require-coverage`) | Every theme has at least its minimum (rail 10, public-road 6, private-road 8, active 6, water 5, air 4, infrastructure 14, workshop 8, iot 10, ai 10), no theme has more than 20% of the records, and there are at least 100 records. Without the flag the same numbers are printed as a report. | FR-001, FR-002, SC-001 |
| **I8** | static | Every record's `theme/subject` exists in its series' `themes`; a subject is used by at most one record. | FR-002, FR-012 |

## Changed checks

| Id | Before | After | Reason |
|----|--------|-------|--------|
| **I1** | `source.file` required, must exist and match | `source.file` optional; when present it must exist and match; `source.sha256`, `width`, `height` always required. `placements` may be empty. `checks.style` and `checks.duplicate` must be `pass`. | FR-015, FR-012 |
| **I2** | prompt = a subject of the series' placement-keyed `subjects` + style; negative = series negative | prompt = `themes[*][*].prompt` + style; negative = the series' current `negative` or one of `negative_history` | R2 |
| **I3** | every file in `assets/images/` belongs to a record | every file in `assets/images/` belongs to a **placed** record; no derivative of an unplaced record is in the build | FR-018 |
| **I4** (`--deep`) | detectors on the source PNG | on the source if present (next to the record or in `.cache/site/sources/`): findings fail as before. Without a source, on the 1600 px derivative scaled back to the source's pixel size: detector hits are **reported as notes, not findings**, because the lossy derivative is not the picture the import checked (a WebP of the approved wheelset image reads "CO" where the PNG read nothing). The record's `checks` block, written by the import on the source, stays the enforced evidence (I1). | R1 |
| **I5** (`--regenerate`) | pHash against the source | against the source if present, else the 1600 px derivative | R1 |
| **C1** | credits list every record | credits list every **placed** record | FR-013, FR-018 |
| **C2** | compliance blocks for every record | unchanged: every record, placed or not | FR-013 |

## Approval

Unchanged from 016: the deployment asks for the owner's approval when `set.json` differs from the live site. `set.json` lists placed records only, so adding to the pool never triggers it; placing, moving or removing a placement does.

## Where each check runs

- `zoo site images triage`: I4, I6, I7, I1-bytes per candidate (developer machine, `images` extra).
- `zoo site images pick`: the same again per pick, plus I8 and the schema.
- `zoo site build` and `zoo site check`: I1, I2, I7, I8, L1, I3, C1 (no extra needed; I7 reads the pHash stored in `checks.measures.phash`, computed at import, so no image decoding at build time).
- `zoo site images check --deep`: I4 over all records; `--require-coverage`: L2. The CI job `site-images` runs `--deep` when records change, as before.
