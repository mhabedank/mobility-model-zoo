# Research: Mobility image library in the house style

Feature: [spec.md](spec.md) · Plan: [plan.md](plan.md)

Everything that feature 016 settled stays settled: the generator and container, the models, the house style text, the record format, the detectors, the disclosure, the compliance blocks, the deployment approval ([016 research](../016-emotional-imagery-motifs/research.md) R1 to R13). This file covers only what a hundred-image pool adds.

## R1 What the repository stores per image, and what the pool weighs

**Decision**: a library image is the 016 record directory **without the source PNG**: `image.yaml` plus the three WebP derivatives (480, 960, 1600 px). `source.file` becomes optional in the schema; `source.sha256`, `width` and `height` stay required so a regenerated source can be verified. The six 016 images keep their source files (removing them from the tree would not shrink history) but their records are otherwise migrated like all others.

**Measured**: the six 016 images have 18 derivatives totalling 663 KB (average 37 KB each, 110 KB per image); the six sources total 5.9 MB (average 1.0 MB). Flat colour fields compress well in WebP, so the caps (60/140/300 KB) are far away.

**Budget**: 110 images × 110 KB ≈ 12 MB of derivatives; even at twice that, the 40 MB limit of FR-016 holds. All three widths are stored for every image, placed or not, because placement must be a record change only (FR-020) and derivatives cannot be re-cut without the source. A new check (L1) sums the derivatives under `zoo/site/images/` and fails above 40 MB.

**Where sources live**: in the rendering round's output directory on the Spark (`~/zoo-imagery/rounds/<n>/`) and in the owner's synced copy; both are outside git. `zoo site images check --deep` uses the source when it finds one next to the record or in the local cache (`.cache/site/sources/<id>.png`), else runs the detectors on the 1600 px derivative scaled back to the source's pixel size. **Measured during implementation**: the lossy derivative is not the picture the import checked. Run on the 1600 px upscale, the approved picket-forest image reads a 31 px "face" and the text "600"; at source scale the wheelset image still reads "CO" (OCR confidence ≥ 0.7) where the PNG read nothing. Detector hits on derivatives are therefore reported as notes, not findings; the enforced evidence is the record's `checks` block, written by the import on the source (I1 requires it, and `add`/`pick` never write a failing record). A source, local or cached, keeps the hard check. `--regenerate` compares the regenerated PNG with the source if present, else with the 1600 px derivative (pHash is robust to the encoding; the 016 threshold of 4 bits holds).

**Alternatives rejected**: Git LFS (bandwidth quotas on GitHub, a second tool for every contributor, no gain for 12 MB); storing only the 960 px derivative for unplaced images (placement would need the source again); keeping the sources in the repository (110 MB, over budget and against FR-015).

## R2 Themes, subjects and the series file

**Decision**: the series file gains a `themes` map (theme id → list of subjects); each subject is an object `{id, prompt, aspect?, scene, alt}`. The placement-keyed `subjects` map of 016 is migrated into `themes` (the six existing prompts move under `rail`, `private-road` and `workshop` with ids), and `gen.py` renders from `themes`. Check I2 flattens `themes`, so the six existing records stay valid without a prompt change.

Theme ids and the spec's minimums: `rail` 10, `public-road` 6, `private-road` 8, `active` 6, `water` 5, `air` 4, `infrastructure` 14, `workshop` 8, `iot` 10, `ai` 10. The planned subjects, about 105 with the six existing ones, are listed in [subjects.md](subjects.md); the plan adds a reserve of a few subjects per theme so that "none" picks do not push a theme under its minimum.

**Aspect**: default `3:2`; a subject may say `16:9` (wide scenes that could serve as a hero). The schema rule "start-hero requires 16:9" stays; other placements accept either aspect because every stage crops with `object-fit: cover` around the focal point. The record keeps the aspect it was cut with.

**Scene and alt texts** are written per subject in the series file, not per image at import: the subject text is the scene, so one description fits every seed of it. The import copies them; the owner can edit the record afterwards. This keeps the import free of typing (FR-010).

**Why no AI-cliché subjects are possible**: the style text already forbids faces, text and logos; the negative prompt adds `robot, spaceship, neon, chrome`. For the `ai` and `iot` themes the subject prompts name physical objects only (edge computer, rack, antenna, sensor, camera, screen with abstract traces), and the negative prompt gains `brain, glowing network, hologram, floating icons, circuit pattern` for all subjects, which is a series change and therefore a new `negative` text for every image rendered from now on. The six existing records keep their old negative text; I2 compares against the series' current text, so the series file keeps the old negative under `negative_history` and I2 accepts the current or any historical one. Simpler alternative (re-render the six) rejected: the owner approved them as they are.

## R3 Automated rejection before the owner sees anything

**Decision**: a new command `zoo site images triage <round-dir>` runs on the developer machine over a round's PNGs and manifest and writes `triage.json`: one entry per candidate with `outcome` (`shown`, `rejected`) and `reasons` (check ids and detail). Checks, in order, stopping at the first failure:

1. **I4 faces, text**: as in 016, on the source PNG.
2. **I6 style** (new, FR-006): palette and accent-location measurement, R4.
3. **I7 duplicate** (new, FR-005): perceptual-hash distance to every library record and to every earlier-listed candidate of the same round, R5.
4. **I1 bytes**: the three derivatives encode within their caps (encoded once here and cached in the round directory, so the import does not encode again).

The round directory is the generator's output copied from the Spark (`rsync` over the VPN; 400 PNGs ≈ 400 MB, under a minute). Detectors and encoding run on CPU: about 2 s per candidate, so a 400-candidate round triages in about 15 minutes. Running triage inside the container on the Spark was rejected: it would need the package and its extra inside the container and a second code path.

**Audit trail** (FR-007): `triage.json` and the owner's `picks.yaml` of every round are committed under `specs/019-mobility-image-library/rounds/<n>/`; the PNGs are not.

## R4 The style check I6

**Decision**: measure, do not judge. Each candidate is reduced to 240 px on the long side and converted to CIELAB. Every pixel is assigned to the nearest of five anchors (`navy`, `mint`, `cream`, `accent`, or `other` when the nearest anchor is farther than a tolerance ΔE). The anchors and tolerance live in the series file under `palette`, measured once from the six approved 016 images (median Lab of the dominant clusters) during implementation, so the check is calibrated on what the owner accepted.

Rules (all thresholds in the series file, calibrated so that all six 016 images pass with margin and the rejected night-and-rain and photoreal series of 016 fail):

- `other` share ≤ 12% of pixels (the image stays in the palette);
- `accent` share between 1.5% and 30% (there is a subject, and it is not the whole picture);
- the largest connected accent region holds ≥ 50% of accent pixels (the accent is one machine or vehicle, not scattered);
- accent pixels in the top fifth of the image ≤ 15% of all accent pixels unless the largest accent region itself reaches into it (no orange sky);
- the accent region's centroid is recorded and becomes the default focal point of the record (clamped to 0.2 to 0.8 on each axis), overridable in `picks.yaml`.

**Kill criterion (Principle IV)**: if on the calibration set more than 30% of the renders the owner picked in 016 (the six) or more than 30% of the agent's shortlist of 016's 60 renders fail I6, the thresholds are wrong, not the images; the check is loosened to the point where the shortlist passes, and if no setting separates the approved set from the rejected series, I6 is downgraded to a warning on the sheet and the spec's FR-006 is reported as not met in `validation.md`.

**Alternatives rejected**: a learned aesthetic or style scorer (not deterministic, not explainable, and Claude or another model judging images would conflict with the project's rule against model judgement in the loop); colour histograms in RGB (hue tolerance behaves badly on the navy/black boundary); asking the owner to strike off-palette images (the spec moves this to automation).

## R5 The duplicate check I7

**Decision**: the 64-bit pHash of 016 (`images_process.phash`) with a Hamming-distance threshold. Two candidates with distance ≤ `DUP_MAX_BITS` are near-duplicates; the later-listed one is rejected with the earlier one named. The threshold is calibrated during implementation on the 016 renders still on the Spark (`~/zoo-imagery/out6/`, four seeds for every subject): the distance distribution between seeds of one subject versus between different subjects. Provisional value 10 bits (016's reproducibility threshold is 4 bits for "the same image"; 10 keeps compositions that differ in layout while catching seeds that converged on one composition). If the distributions overlap so that no threshold separates "same composition" from "different composition" with at most one false rejection in twenty, the threshold is set at the conservative end (fewer rejections) and the sheet marks suspected twins without hiding them.

Also applied at import against the whole library (a pick is refused if it duplicates an existing record) and reported by `zoo site images check` as I7 over all records.

## R6 The contact sheet and the picks

**Decision**: `triage` also writes `sheet.html` into the round directory: a static page, no scripts, grouped by theme then subject, each shown candidate as a 480 px thumbnail (the cached derivative) with its number (`<theme>/<subject>#<k>`), seed, and a link to the full PNG; rejected candidates are listed per subject by number and reason in a collapsed line; subjects without a shown candidate are listed at the top under "needs another round". The owner opens the file in a browser. Sheets of 300 thumbnails at about 12 KB each are 4 MB: one page.

The owner states picks in chat or in `picks.yaml`: `{"rail/high-speed-viaduct": 3, "rail/freight-containers": "none", ...}`, optionally with `focal: [x, y]` per pick. `zoo site images pick <round-dir>` imports every numbered pick with the semantics of `add` (same checks again, nothing written on failure), writes `theme`, `subject`, `placements: []`, copies scene and alt from the subject, and writes `round` into the record. Subjects marked `none` and subjects with no shown candidate go into `next.txt`; the next round renders only those with `--only` and new seeds (`--seed-base` advanced), and its sheet holds only those subjects.

**Alternatives rejected**: an interactive sheet that writes picks (needs a script or a server, against the no-script rule and more code than the problem needs); a printed PDF contact sheet (no link to the full image); picking on the Spark through the terminal (no images).

## R7 The pool overview

**Decision**: `zoo site images overview [--out .cache/site/pool.html]` writes a static page like the sheet, from the records instead of a round: grouped by theme, every image as its 480 px derivative (relative file links into `zoo/site/images/`), with id, subject, aspect and placements, and a per-theme count against the minimum and the cap. It is the owner's tool for placing (FR-019). Not deployed, not under `_site/`.

`zoo site images list` gains `--theme` and prints theme and subject columns.

## R8 What changes on the site

**Decision**: as little as the spec allows (FR-018, FR-021, FR-022).

- `build` copies derivatives, writes `set.json`, renders credits and page images **for placed records only**. Unplaced records are validated (I1, I2, I7) but produce no files; the build does not warn about them. The set digest therefore changes only when a placement changes, so the deployment approval is untouched by pool growth.
- I3 (no orphans in `assets/images/`) is unchanged and now implies "no unplaced image in the build" (new assertion in the check: every file in `assets/images/` belongs to a placed record).
- Compliance (`zoo compliance render`) keeps covering every record, placed or not, because the files are in the repository: REUSE annotation per directory, model notices, record-of-processing note.
- No template changes. No new page.

## R9 Rendering plan and compute budget

**Decision**: two passes per round, as in 016. A **draft pass** with FLUX.2-klein-4B (about 4 s per image, two seeds per subject, about 15 minutes for 105 subjects) is reviewed by the agent only, to catch subjects the model misreads (016: "vehicle bus connector" became a toy bus) and to rewrite them before any final render. The **final pass** with Qwen-Image-2512 (50 steps, about 190 s per image on the GB10) renders four seeds per subject: 105 × 4 × 190 s ≈ 22 hours, unattended, resumable (existing files are skipped). A second round for "none" subjects at an assumed 25% is about 5 hours. Both passes run in the pinned `zoo-flux` container; the manifest records the container digest and the generator commit (now versioned: `gen.py` is in the repository).

Seeds: `1000 + 10·i + s` as in 016 collides across themes once subjects are indexed per theme; the generator switches to `seed = base + 97·hash(subject id) mod 10⁶ + s`, recorded per image, so a subject keeps its seeds across runs and no two subjects share one.

**Cost**: no cash; one day of the Spark's GPU time; the VPN link for the copy.

## R10 Migration of the six existing records

**Decision**: one hand-written migration in the implementation, not a command: add `theme` and `subject` to the six records, run the new I6 and I7 checks over them and write `checks.style: pass` and `checks.duplicate: pass` (if any of the six fails I6 after calibration, R4's kill criterion applies before anything else), keep their `source.file`. Their prompts stay valid under `themes` (R2). The set digest changes because the records change, so the next deployment asks for the owner's approval once; the job summary will show six changed records with unchanged images.

## R11 Order of work and the riskiest assumption

The riskiest assumption of this feature is that the automated rejection (I6 style, I7 duplicate) rejects what the owner would reject and little else; if it rejects good candidates, the owner sees too few, and if it rejects nothing, the owner wades through off-palette renders, which the spec forbids. It is tested first: calibrate I6 and I7 on the 016 renders and the rejected series before any new rendering, with the kill criteria of R4 and R5. Second comes the draft pass (subjects the model misreads). Only then the 22-hour final pass.

## Budget

| Item | Estimate |
|---|---|
| GPU time | 1 day Spark (final pass) + 5 h (second round) + 15 min (drafts) |
| Owner time | contact sheets: about 300 shown candidates over 105 subjects, 1 to 3 sittings |
| Repository growth | about 12 MB derivatives + 100 KB round records |
| CI | `site-images` deep check over about 110 records: about 4 minutes on the 1600 px derivatives |
| Cash | none |
