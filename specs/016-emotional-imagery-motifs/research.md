# Research: Emotional mobility imagery and prominent model motifs

Feature: [spec.md](spec.md) · Plan: [plan.md](plan.md) · Date: 2026-10-13 (revised the same day after the image-source decision)

Each entry gives the decision, the reasons for it, and the alternatives that were rejected.

## R1 Where the images come from

**Decision**: images are generated on the project's own DGX Spark (`cst-ai-02`, GB10, 128 GB) with open-weights models run through `diffusers` inside a Docker image derived from the NGC PyTorch container that is already on the machine.
- **Draft model**: `black-forest-labs/FLUX.2-klein-4B` (Apache-2.0, not gated, 4-step distilled, about 4 s per image). Used to explore subjects and styles.
- **Final model**: `Qwen/Qwen-Image-2512` (Apache-2.0, not gated, 20B, 50 steps, about a minute per image). Used for every image that ships. Non-distilled models make fewer structural mistakes (rails, reflections, splashes) than distilled ones.
- Both are cached once in `~/.cache/huggingface` on the Spark. No hosted image API is used.

**Rationale**:
- Two search rounds on Wikimedia Commons (96 candidates under CC0/PDM/CC BY) yielded nothing with the required mood; the few good hits were old Unsplash imports. The owner judged them unusable on 2026-10-13.
- Generation gives full control of mood, series consistency and the absence of people, plates and logos. It removes the licence, restriction and takedown risks of third-party photographs.
- Local generation follows the constitution's cost order (local compute first) and Principle V (no hosted API dependency). There is no cash cost.
- Apache-2.0 model licences place no restriction on outputs, so the images can be published under CC0 and the zoo's usage class is untouched.

**Alternatives considered**:
- **FLUX.1-schnell**: gated on Hugging Face since 2026; needs an account click the agent may not perform. Rejected.
- **FLUX.2-dev** (32B): the strongest open model, but gated, under a non-commercial licence and 178 GB; it would have to be quantised to fit. Kept as an option if Qwen's structural errors prove too frequent.
- **Unsplash / Pexels / Openverse**: real photographs with good mood, but each needs an API key the owner would have to create, the licences are platform-specific, and people, plates and logos would still need filtering. Rejected after the owner chose generation.
- **Own photography**: declined by the owner.

## R2 Which model licences are accepted and what the images are published under

**Decision**:
- A generating model is accepted only if its weights licence is Apache-2.0, MIT or an equally permissive licence that places no restriction on outputs. Models under non-commercial or "community" licences are not used by default; if one is ever used, the restriction is recorded on every image record and in the notices.
- Every generated image is published under **CC0 1.0**. The REUSE annotation sets `SPDX-FileCopyrightText = "NONE"` for the image and names the generating model in the comment.
- The model card reference (id, revision, licence, licence URL) goes into `THIRD_PARTY_NOTICES.md`.

**Rationale**: CC0 is the honest choice for synthetic images whose copyright status is uncertain in the EU. Recording the model keeps provenance complete (Principle VI). Keeping NC models out keeps the record simple.

**Alternatives considered**:
- **Repository licence (Apache-2.0) for images**: unusual for images and implies an authorship claim. Rejected.
- **No licence statement**: leaves reuse unclear. Rejected.

## R3 How images are processed and served

**Decision**:
- **Formats and sizes**: each generated PNG is cropped to its placement's aspect ratio (start hero 16:9, topic 3:2, model stage 3:2) around its focal point, then written as WebP at three widths (480, 960 and 1600 px) at quality 72.
- **Embedded metadata**: every derivative carries XMP with `Iptc4xmpExt:DigitalSourceType = trainedAlgorithmicMedia`, the generating model id and the series name. Nothing else (no camera, no location).
- **Markup**: pages use `<img srcset sizes width height>`. The hero gets `fetchpriority="high"`; every other image `loading="lazy" decoding="async"`.
- **Per-file byte caps**: 60 KB at 480 px, 140 KB at 960 px and 300 KB at 1600 px. A derivative over its cap is re-encoded at lower quality, down to 60; if still too big, the image is rejected.
- **Library**: Pillow.
- **Location**: derivatives and the record in `zoo/site/images/<id>/`; the build copies them to `_site/assets/images/`. The generator's 1344×768 or 1200×800 source PNG is kept next to the record so the hash in FR-018 has something to match.

**Rationale**:
- WebP is supported everywhere the site targets and encodes with Pillow alone.
- The IPTC "trained algorithmic media" marker is the standard way to flag synthetic images in file metadata (FR-013); C2PA would need a signing identity the project does not have.
- Width and height prevent layout shift; lazy loading keeps below-the-fold images out of the LCP path.
- Keeping images under `zoo/` keeps them out of the wheel; `zoo/**` already triggers the site workflow.

**Alternatives considered**:
- **AVIF**: smaller, but Pillow support depends on the wheel build. Not now.
- **Keeping only the WebP derivatives**: the source PNG (about 1.5 MB) is what regeneration is compared against; without it SC-008 cannot be checked. Kept, within the 12-image cap.

## R4 How identifiable faces are detected

**Decision**: OpenCV's YuNet face detector (`cv2.FaceDetectorYN`, opencv-python-headless, Apache-2.0) with the opencv_zoo model `face_detection_yunet_2023mar.onnx` (MIT, about 230 KB, pinned by sha256). It runs on the source PNG and on two 2× upscaled halves. Any detection with score ≥ 0.5 and box height ≥ 16 px rejects the image. No override.

**Rationale**: the prompts ask for people from behind or distant, but diffusion models sometimes turn a figure around. The check is cheap, local and catches that. It does not fire on backs or silhouettes.

**Alternatives considered**: MediaPipe (heavier), RetinaFace (needs torch, slower). Blurring instead of rejecting (changes the image; rejecting plus another seed is simpler).

## R5 How readable text, plate-like strings and brand-like words are detected

**Decision**: RapidOCR (`rapidocr-onnxruntime`, Apache-2.0) reads the source PNG. Any token with confidence ≥ 0.7 and at least two alphanumeric characters rejects the image. There is no declared-text allowance: generated scenes must carry no readable text at all.

**Rationale**: generated text is pseudo-text at best and brand-like at worst (FR-009, FR-010). Forbidding all of it is simpler than classifying it, and the prompts already ask for none.

**Alternatives considered**: a declared-text list as in the photo version of this research. Dropped; there is no legitimate station name in a synthetic scene.

## R6 How the images are disclosed as AI-generated

**Decision**:
- **Credits page** `/credits/`: every image is listed as "AI-generated with <model> (<licence>) on the project's own hardware, <date>", with its scene description and placements.
- **Footer** on every page with images: "Images are AI-generated · Image credits" (a per-page details block was tried and dropped by the owner as clutter).
- **Alt text** ends with "(AI-generated image)".
- **File metadata**: the IPTC digital source type marker (R3).
- **Record of processing**: no personal data is involved; the entry only notes that the site contains synthetic imagery and where it is disclosed.

**Rationale**: AI Act Art. 50 asks deployers to disclose realistic synthetic imagery. A site whose tone is "measured, not claimed" should over-disclose rather than under-disclose. All four places are generated from the records, so nobody maintains them by hand.

**Alternatives considered**: a visible watermark on each image (hurts the emotional purpose; the four disclosures are sufficient).

## R7 Attribution and generated legal files

**Decision**:
- `zoo compliance render` reads the image records and writes:
  - one `REUSE.toml` annotation per image directory (`CC0-1.0`, copyright text `NONE`, comment naming model and revision);
  - a section "Website imagery" in `THIRD_PARTY_NOTICES.md` naming each generating model once with licence and model card URL;
  - the record-of-processing note from R6.
- `LICENSES/CC0-1.0.txt` is added.

**Rationale**: keeps the existing compliance check C-L1 (`reuse lint`) green (FR-015) and makes the model provenance visible where the project already lists third-party components.

## R8 How page weight and loading are measured

**Decision**: the 008 check S1 is split into static and browser checks.
- **S1a** static: HTML ≤ 150 KB per page (unchanged).
- **S1b** static: total site bytes without fonts, preview cards and images ≤ 300 KB.
- **S1c** static: every image derivative within its cap (R3).
- **S4** browser: transferred bytes per page at 390 px width and device pixel ratio 2, without fonts, ≤ 600 KB with images, ≤ 300 KB without.
- **S3** browser: Cumulative Layout Shift ≤ 0.1.
- **S2** browser: LCP ≤ 2 s on Fast 3G with 4× CPU slowdown (unchanged).

**Rationale**: today's S1 sums the whole site, which a few images would break although each page loads only its own. The real cost is what one page transfers on a phone, which only the browser run can measure.

## R9 Composition: motif plate and image stage

**Decision**:
- **Motif plate**: wherever a motif appears (tile, roadmap entry, "Coming next" card, model hero, preview card) it sits on a rounded plate drawn with the dark-scheme tokens in both colour schemes: plate `#111846`, ink `#EEF1FF`, greys `#6F7DC4`, mint `#6FFFC8`, via a `.plate` class that re-declares the custom properties locally.
- **Sizes**: tiles 72 px plate / 64 px motif; roadmap and "Coming next" 48 / 40; model hero plate at least 160 px on phones, at most 260 px.
- **Image stage** in the model hero: a 3:2 image with the plate overlapping its lower-left corner; at phone width the stage moves above the headline. Text never sits on the image (FR-004).
- **Start hero**: from 860 px up, purpose line and calls to action on the page surface to the left, the 16:9 image to the right; below 860 px the image band sits above the text.
- **Topic cards**: 3:2 image on top, then title, description and the topic's model plates.

**Rationale**: on white, mint `#6FFFC8` reaches only about 1.2:1, so today's motifs fail FR-024 in light mode. On the dark plate every motif colour reaches at least 4:1, the plate echoes the mark and the dark preview cards, and overlapping it on the image makes the motif the main figure.

**Alternatives considered**: a darker mint in light mode (changes the mark); the royal-blue plate (ink and greys would need new colours); motif directly on the image (contrast depends on the image).

## R10 Motif coverage and one way to resolve a motif

**Decision**: a new module `site/motifs.py` holds the only resolver: `site.yaml` `motif` key, else `static/img/motifs/<name>.svg`. Every template, `roadmap.motif_name` and `og.cards` use it. The `-hero.svg` convention is dropped; the hero draws the same motif larger. `scout-large-hero.svg` stays as an illustration in the reference layer.

Check **M1**: every name the build shows must resolve. Today without a motif: hum-bearing, mode-cnn, cell-soh, gnss-guard, jtbd-cluster, rough-road, v2x-guard, picket-signal, and cairn-base if shown.

**Rationale**: three places resolve motifs in three ways today, which is why picket-forest's hero and preview card lack one. One resolver satisfies FR-025 by construction.

## R11 How motifs are drawn and checked

**Decision**: new motifs are hand-authored SVG in the existing grammar, one per model, depicting its task (rough-road: a road profile; v2x-guard: two radio arcs and a shield bracket; cell-soh: a battery cell with a level; and so on).

Check **M2** lints every motif: viewBox `0 0 96 96`; one group with `skewX(-8)`; round caps; stroke widths 4.5, 5, 8, 12 or 16; colours only `var(--text)`, `var(--border-strong)`, `var(--mark)`; exactly one `var(--mark)` element; no text, raster or gradient; at most 1.5 KB.

Check **M3** (browser) rasterises every motif at 96 px on its plate and requires every pair to differ in at least 12% of pixels.

**Rationale**: the grammar is what the owner likes; linting keeps new motifs in the family, and a pixel difference catches near-duplicates.

## R12 Where generation and the checks run, and how the owner approves

**Decision**:
- **Generator**: `scripts/imagery/gen.py`, `Dockerfile` and the series files live in the repository. They are run on the Spark inside the `zoo-flux` image (`docker run --gpus all --ipc=host`). The generator writes a manifest with model, revision, prompt, negative prompt, seed, steps, guidance, size and seconds per image.
- **Import**: `zoo site images add <png> --manifest <manifest.json> --placement … --focal … --alt …` creates the record from the manifest entry, runs the checks (faces, text, bytes), writes the derivatives with metadata and the source PNG. Nothing is written on failure.
- **Static checks** in `zoo site check` (I1 to I4): record complete and valid, hashes match, placements unique, credits page complete.
- **Deep check** `zoo site images check --deep` re-runs the detectors on the source PNGs; a CI job `site-images` runs it when `zoo/site/images/**` changes, and `scripts/ci/select_tests.py` gains the matching area.
- **Dependencies**: a new optional extra `images` (Pillow, opencv-python-headless, rapidocr-onnxruntime). `zoo site build` and `check` never import it.
- **Approval** (FR-017): the `deploy` job of `site.yml` waits for the GitHub environment `site-images`, whose required reviewer is the owner, only when the build's image-set digest (`assets/images/set.json`) differs from the deployed site's. The job summary lists added, changed and removed images with scene, series, model and placements. Unchanged sets deploy without a prompt.

**Rationale**: generation needs the GPU machine; checks and build must stay light and run in CI. One environment approval is the single manual step the owner keeps, recorded in GitHub's deployment history.

**Alternatives considered**: running the detectors on every build (adds about 200 MB of dependencies for no gain); an approval date in each record set at the next model release (holds images hostage to unrelated releases).

## R13 Art direction: series SIEBDRUCK (house style)

**Decision**: the series that ships is **SIEBDRUCK**, a house style the owner developed on 2026-10-13 from two favourites of a four-style test (a 1930s railway-poster look). It is openly illustrated, never photographic.
- **Character**: 1970s West German modernist poster illustration, quietly futurist, calm and precise, in the spirit of Kraftwerk-era design (Autobahn, Trans-Europe Express) without pastiche: flat screen-print colour fields with crisp edges, clean geometric forms, long diagonals, morning light drawn as graphic shapes, people only as small simple silhouettes.
- **Palette**: deep navy, pale mint and warm cream for sky, ground and buildings, so the images share the identity tokens; **one warm orange-yellow accent reserved for the main vehicle or machine** (the train, tram, bus, motor, board). Sky and ground are never orange.
- **Negative text**: text, letters, watermark, logo, face, portrait, photo, photorealistic, glossy, 3D render, neon, chrome, robot, spaceship, retro kitsch, cluttered, orange sky, orange ground.
- **Subjects** per placement, with the accent on the vehicle: start hero (orange-yellow tram leaving a stop at sunrise with a cyclist ahead; orange-yellow regional train leaving a small station at dawn; riverside bike lane with a tram on a distant bridge), product development (empty tram interior with orange-yellow seats; bus stop with one small figure from behind and an orange-yellow bus), security (dashboard with orange-yellow needles and the road ahead; workshop bay with an orange-yellow car, hood open), condition monitoring (fan with an orange-yellow motor on a test rig; orange-yellow bogie in a bright hall), scout-large (notebook on a train table, orange-yellow train outside), picket-forest (board with an orange-yellow connector and a bus plug, oscilloscope trace).
- **Selection**: 4 seeds per subject with the final model; the agent shortlists by composition and the FR-008 to FR-010 rules; the owner approves at deployment.
- **Set**: at most 12 images (one hero, three topics, up to one per published model, the rest reserve), so sources and derivatives stay under about 25 MB in git.

**Rationale**: the owner judged the photographic series (night/rain, then FORWARD morning light) as "really good" but wanted the imagery to be *obviously* synthetic rather than near-real, to avoid looking cringe on a site that is honest about AI. A drawn house style reads as deliberate design, matches the abstract motifs, and ties the images to the identity palette. The accent-on-vehicle rule keeps each image's subject unmistakable and gives the series one recognisable signature.

**Alternatives considered**: FORWARD photographic series (rendered with Qwen, 44 images, kept as reserve under the generator's output); BRIGHT (stock-like, rejected); steel engraving (Industrial Revolution look, charming but monochrome and backward-looking); steampunk (warm but nostalgic and close to kitsch); constructivist/Bauhaus (closest to the motifs but cooler and less emotional); an airbrush variant of the house style (softer, but vehicles drifted towards retro costume).

## Budget

No cash cost. Generation and checks run on the Spark and the existing GitHub runners. Model downloads are one-off (24 GB klein, 58 GB Qwen) and stay in the Spark's cache.
