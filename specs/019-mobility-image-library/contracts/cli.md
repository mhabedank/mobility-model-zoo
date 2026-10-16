# Contract: command line of feature 019

Extends the [016 CLI contract](../../016-emotional-imagery-motifs/contracts/cli.md). Commands not listed keep their behaviour.

## Generator: `scripts/imagery/gen.py` (changed)

```
python gen.py --series <name>.yaml --model {draft|final} [--seeds N] [--seed-base B] [--steps N]
              [--only theme[/subject],...] [--reserve] --out <dir>
```

- Renders from the series' `themes` map (data model) instead of placement-keyed subjects. File names: `<theme>--<subject>--<seed>.png`.
- Seeds: `seed = seed_base + (97 · crc32("theme/subject")) mod 1_000_000 + s` for `s` in `0..N-1`; `--seed-base` defaults to 0. A subject keeps its seeds across runs; a second round uses `--seed-base 1000`.
- `--only` takes themes or `theme/subject` pairs; `--reserve` includes subjects marked `reserve: true` (default: excluded). A file `next.txt` in `--out` (one `theme/subject` per line) acts like `--only` when `--only` is not given.
- The manifest entry gains `theme`, `subject`, `seed_base`, `aspect`. Everything else as in 016.
- Existing files are skipped; a run can be resumed.

## `zoo site images triage <round-dir> [--round N]`

Runs the automated rejection over a round copied from the Spark (needs the `images` extra).

| Input | Output |
|---|---|
| `<round-dir>/manifest.json`, `<round-dir>/*.png` | `<round-dir>/triage.json`, `<round-dir>/sheet.html`, `<round-dir>/thumbs/*.webp` |

Behaviour, per candidate in manifest order: I4 faces, I4 text, I6 style, I7 duplicate (against every library record and every earlier shown candidate of the round), I1 bytes (encodes the three derivatives into `thumbs/` as a cache). The first failure sets `outcome: rejected` with the check and detail; otherwise `outcome: shown` and a number within its subject. Prints a summary: candidates, shown, rejected per check, subjects without a shown candidate.

Exit codes: 0 (even if every candidate is rejected), 2 if the manifest is missing or the extra is not installed.

## `zoo site images pick <round-dir> [--picks picks.yaml] [--dry-run]`

Imports the owner's picks of a round.

- Reads `picks.yaml` (`theme/subject` → number or `none`, optional `focal`, optional `id`). Every numbered pick must be a `shown` candidate of `triage.json`.
- For each numbered pick: the `add` behaviour of 016 (checks run again; nothing written on failure) with `theme`, `subject`, `round`, `placements: []`, scene and alt from the series' subject, focal point from the pick or the I6 default, derivatives from `thumbs/` if their hashes match the re-encode, else re-encoded. The source PNG is **not** copied; `source.file` is omitted. Record id: `--id` from the pick, else `<theme>-<subject>` (truncated to 40 characters, de-duplicated with a numeric suffix).
- Writes `<round-dir>/next.txt` with every `none` pick and every subject that had no shown candidate.
- Refuses the whole import if any pick fails a check (nothing written), so one `picks.yaml` imports atomically.

Exit codes: 0 written (or dry run passed), 1 a pick failed a check, 2 a pick names an unknown or rejected candidate.

## `zoo site images overview [--out PATH]`

Writes the pool overview (data model) as one static HTML file, default `.cache/site/pool.html`, and prints the path. Needs no extra.

## `zoo site images check [--deep] [--regenerate] [--require-coverage]` (changed)

- I1 accepts records without `source.file`; `--deep` runs the detectors on the source if present next to the record or in `.cache/site/sources/<id>.png`, else on the 1600 px derivative.
- New: I7 over all records (pairwise pHash), L1 (derivative bytes ≤ 40 MB), coverage report per theme; `--require-coverage` turns the coverage report into L2 findings.
- `--regenerate` compares with the source if present, else with the 1600 px derivative.
- New: `--only <id>,...` restricts `--deep` and `--regenerate` to the named records (the regeneration sample of SC-006).

## `zoo site images list [--theme T]` (changed)

Adds theme and subject columns; `--theme` filters.

## `zoo site images add` (changed)

Gains `--theme`, `--subject` (required), `--no-source` (omit the PNG), and allows no `--placement`. Kept for one-off imports; `pick` is the way for rounds.

## `zoo site build` (changed)

Copies derivatives, writes `set.json`, renders `/credits/` and page images for **placed records only**. Validates all records (I1, I2, I7, L1) and fails on any finding. No warning for unplaced records.

## Dependencies

No new package. The `images` extra (Pillow, OpenCV, RapidOCR) covers I6 (Lab conversion and connected components with NumPy/OpenCV) and I7 (existing pHash). The container is unchanged except for the generator script.
