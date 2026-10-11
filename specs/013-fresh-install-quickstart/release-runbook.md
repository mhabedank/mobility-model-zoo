# Runbook: picket-forest 0.2.1 and scout-large 0.1.3 (tasks T048–T053)

Everything the code needs is in the branch. These steps need the owner's Hugging Face tokens, the
compliance sign-off and the approval of the reviewed cards, so nobody else can run them.

Both releases are card and packaging patches: weights, thresholds, features and device code are the
ones of 0.2.0 and 0.1.2 (the gate's sha256 list proves it). `README.md` names
`picket-forest/v0.2.1`, whose draft record is in the branch.

## 0. Prerequisites

```bash
set -a; source .env; set +a        # HF_STAGING_TOKEN, HF_RELEASE_TOKEN
git add -A && git commit -m "feature 013: quickstart that works from a fresh install"
RECIPE=$(git rev-parse HEAD)       # the recipe commit of both patches
```

## 1. Repack the files of picket-forest 0.2.0 (already done once; repeat on a fresh checkout)

```bash
rm -rf build/repack-0.2.1
uv run python -c "
import yaml
from huggingface_hub import snapshot_download
files = [f['path'] for f in yaml.safe_load(open('zoo/models/picket-forest/releases/0.2.0.yaml'))['files']]
snapshot_download('mobility-model-zoo/picket-forest', revision='v0.2.0', local_dir='build/repack-0.2.1', allow_patterns=files)
"
rm -rf build/repack-0.2.1/.cache
mkdir -p build/repack-0.2.1/examples && cp zoo/models/picket-forest/examples/*.json build/repack-0.2.1/examples/
uv run zoo-security can-ids v2 table-json --from-header build/repack-0.2.1/picket_forest_table.h --out build/repack-0.2.1/calibration_table.json
```

The directory holds the 12 files of 0.2.0 (byte-identical), the three example captures and
`calibration_table.json`.

## 2. picket-forest 0.2.1

The draft record (`zoo/models/picket-forest/releases/0.2.1.yaml`, results, compliance drafts) is in the
branch, created with `zoo new-patch picket-forest 0.2.0 0.2.1 --restage`; `files[]` and the staging
revision are empty until `zoo stage` fills them, so `zoo validate --all` skips it.

```bash
uv run zoo stage picket-forest 0.2.1 --from build/repack-0.2.1     # fills files[] and staging.revision
uv run zoo compliance scan-publish --model picket-forest --version 0.2.1
uv run zoo compliance signoff --model picket-forest --version 0.2.1  # owner decision
uv run zoo check picket-forest 0.2.1
```

`zoo check` builds a fresh Python 3.12 environment from `mobility-model-zoo[edge]` and runs the
card's snippet there (rule 12). Expected: PASS, and the card shows
`3000 frames, ... s; 1 alarm at frame 1155 ...` under "Output:".

## 3. scout-large 0.1.3

```bash
uv run zoo new-patch scout-large 0.1.2 0.1.3 --commit "$RECIPE" \
  --changes "Card and packaging only: the install line names the text extra and states the Python requirement. Weights identical to 0.1.2."
uv run zoo compliance scan-publish --model scout-large --version 0.1.3
uv run zoo compliance signoff --model scout-large --version 0.1.3   # owner decision
uv run zoo check scout-large 0.1.3
```

No `zoo stage`: the staged files are those of 0.1.2.

## 4. Merge, tag, publish (owner)

1. Commit the two records, their results and companions; open the pull request; merge when CI is green.
2. On `main`: `git tag picket-forest/v0.2.1 && git tag scout-large/v0.1.3 && git push origin picket-forest/v0.2.1 scout-large/v0.1.3`.
3. `release-verify` builds both previews. Review the cards (install line, "Requires Python 3.12 or newer", the snippet, the "Output:" block).
4. Start `release-publish` for each (model, version, confirm the tag).

## 5. Deprecate the card that cannot be followed

```bash
uv run zoo deprecate picket-forest 0.2.0 --reason "The card's snippet could not be run from a fresh install; use 0.2.1." --successor 0.2.1
```

scout-large 0.1.2 stays: its card works.

## 6. The five-minute test (SC-001, SC-007)

On a machine without the repository, only with the website quickstart and the two cards:
`uv venv --python 3.12`, the install line, `python demo.py`. Record the two times and any friction in
`specs/013-fresh-install-quickstart/validation.md`.

## Checks done on 2026-10-11 without tokens

- The card snippet of picket-forest, run in a fresh Python 3.12 environment with `[edge]` from the
  checkout, a PATH without a compiler and the repack directory standing in for the model repository:
  exit 0, `3000 frames, 6.37 s; 1 alarm at frame 1155 (t=2.552 s); highest forest score 1.000`;
  no torch; 173 MB installed.
- The card snippet of scout-large with `[text]` from the checkout: JSON result; 693 MB installed.
- The example captures of the release reproduce the released C chain bit for bit in the numpy
  reference, and the numpy reference equals the ctypes build of `msml_cal` on the parity captures.
