# Data Model: Emotional mobility imagery and prominent model motifs

Feature: [spec.md](spec.md) · Research: [research.md](research.md)

All records are files in the repository. Nothing is stored at run time.

## Image record: `zoo/site/images/<id>/image.yaml`

One generated scene. The directory also holds the source PNG `<id>.png` and the derivatives `<id>-480.webp`, `<id>-960.webp` and `<id>-1600.webp`. Schema: [contracts/image-record.schema.json](contracts/image-record.schema.json).

| Field | Type | Rule |
|---|---|---|
| `id` | slug | Equals the directory name; `^[a-z0-9]+(-[a-z0-9]+)*$`, at most 40 characters |
| `series` | string | Art-direction series the image belongs to (today `siebdruck`) |
| `generation` | object | See below; the complete recipe |
| `licence` | const | `CC0-1.0` (research R2) |
| `placements` | list | One or more of `start-hero`, `topic:<topic-id>`, `model:<model-name>` |
| `scene` | string | One-line description for the credits page, 20 to 120 characters |
| `alt` | string | One sentence, 40 to 160 characters, ending with "(AI-generated image)" |
| `focal_point` | `[x, y]` | Fractions 0–1 of the source's width and height |
| `aspect` | enum | `16:9` for `start-hero`, `3:2` otherwise |
| `source` | object | `{file, width, height, sha256}` of the generator's PNG |
| `derivatives` | map | width → `{file, bytes, sha256}` for 480, 960 and 1600 |
| `checks` | object | See below |

`generation` holds everything needed to regenerate the image (FR-012, FR-018):

| Field | Content |
|---|---|
| `model` | Hugging Face id, for example `Qwen/Qwen-Image-2512` |
| `revision` | Commit hash of the snapshot used |
| `model_licence`, `model_card` | SPDX id and model card URL |
| `pipeline` | diffusers pipeline class |
| `prompt`, `negative_prompt` | Exact texts as sent |
| `seed`, `steps`, `guidance`, `width`, `height` | Sampling parameters |
| `generated` | Date |
| `hardware` | `dgx-spark` or `dev-machine`; the machine class, never a hostname |
| `generator` | Version of `scripts/imagery/gen.py` (git commit) and the container image digest |

`checks` holds the results of `zoo site images add` and `check --deep`:

| Field | Content |
|---|---|
| `tools` | Versions of Pillow, OpenCV and RapidOCR; the YuNet model sha256 |
| `ran` | Timestamp |
| `faces` | `pass` and the count of detections below the threshold (for audit) |
| `text` | `pass` and the OCR tokens examined |
| `bytes` | `pass` and the byte sizes against the caps |

**Validation**:
- A record is valid only if every `checks` entry is `pass`, every hash matches its file, every placement names an existing topic or a model the site shows, and `generation` is complete.
- Two records MUST NOT share a placement.
- Records that fail are never committed: `add` writes nothing on failure.

**Lifecycle**:
1. `draft`: rendered on the Spark into the generator's output directory, listed in its manifest, not in the repository.
2. `committed`: imported with `zoo site images add`, merged to `main`.
3. `live`: deployed after the owner approves the site deployment (FR-017; [contracts/checks.md](contracts/checks.md) "Approval").
4. `removed`: on replacement, the directory is deleted; the release notes record it.

The owner's approval is not stored in the record. The deployment asks for it through the GitHub environment `site-images` only when the image set differs from the last approved deployment. GitHub's deployment history is the audit trail.

## Series: `zoo/site/images/series/<name>.yaml`

The art direction, kept with the records so new images join the same look.

| Field | Content |
|---|---|
| `name` | `siebdruck` |
| `style` | The style text appended to every subject prompt (research R13) |
| `negative` | The negative prompt |
| `subjects` | Map placement → list of subject prompts |
| `models` | Draft and final model ids with default steps and guidance |

A record's `generation.prompt` MUST equal one of the series' subjects followed by the series' style text; check I2 verifies it. A subject MAY serve a placement other than the one it is listed under (the owner chose the workshop subject for product development); I2 checks series membership, not the placement.

## Placement resolution

| Page area | Looks for | Fallback |
|---|---|---|
| Start hero | `start-hero` | none (text-only hero as today) and a warning |
| Topic card | `topic:<id>` | no image; the card keeps its text and plates; warning |
| Model hero stage | `model:<name>` | `topic:<model's topic>`, then motif plate alone; warning (FR-016, Story 3) |
| Preview card | `model:<name>`, then topic | none, if the card fails 012 checks O2/O3 with it (FR-026) |

## Motif

The abstract symbol of one model. Files live in `src/mobility_model_zoo/site/static/img/motifs/<name>.svg`.

| Attribute | Rule |
|---|---|
| name | The model or roadmap name. A model's `site.yaml` may name another file via `motif` (kept for compatibility) |
| grammar | Check M2: viewBox `0 0 96 96`; one group `skewX(-8)`; round caps; stroke widths 4.5, 5, 8, 12 or 16; colours only `var(--text)`, `var(--border-strong)` and `var(--mark)`; exactly one `var(--mark)` element; no text, gradients or raster images; at most 1.5 KB |
| distinctness | Check M3: ink overlaps every other motif by at most half (Jaccard distance ≥ 0.5) at 96 px |
| coverage | Check M1: every name the site shows resolves to a motif |

Resolution is done in one place, `motifs.resolve(reg, name)` (R10). A renamed working name keeps its motif because the roadmap entry id is tried before the name.

## Credits entry (derived)

Rendered from image records for `/credits/` and the per-page credit block.

| Field | From |
|---|---|
| scene | `scene` |
| disclosure | "AI-generated with `generation.model` (`model_licence`) on the project's own hardware, `generated`" |
| used on | `placements`, resolved to page links |
| licence | `licence` with deed link |

## Generated compliance blocks (derived)

`zoo compliance render` reads the image records and writes:
- **`REUSE.toml`**: one annotation per image directory with `SPDX-FileCopyrightText = "NONE"`, `SPDX-License-Identifier = "CC0-1.0"` and a comment naming model and revision.
- **`THIRD_PARTY_NOTICES.md`**: a section "Website imagery" naming each generating model once with licence and model card URL.
- **record of processing**: a note that the site carries synthetic imagery and where it is disclosed (R6). No personal data.

## Site configuration changes

- `zoo/site.yaml`: no new field.
- `zoo/models/<name>/site.yaml`: `motif` stays optional. The `-hero.svg` convention is dropped (R10).
