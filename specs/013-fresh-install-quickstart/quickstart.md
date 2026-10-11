# Validation guide: Quickstart that works from a fresh install

How to prove the feature end to end. Steps 1–4 run on any checkout; 5–7 need the Hub tokens and
the owner's approval (release pipeline).

## Prerequisites

- Python 3.12, `uv`, a C compiler (only for step 2b; users never need one).
- `uv sync --extra release --extra edge --extra edge-train --no-install-package torch`
  (edge-train provides emlearn and scikit-learn for the parity test).
- `HF_RELEASE_TOKEN` / `HF_STAGING_TOKEN` for steps 5–7.

## 1. The user-facing module is self-contained

```bash
uv run pytest tests/security/can_ids/test_picket_forest_reference.py -q
```

Expected: every test passes without a compiler. In particular
`test_examples_reproduce_expected_scores_and_alarms` (0 mismatches on the three example captures,
float32 bit patterns and alarm frames) and `test_module_imports_are_user_safe`.

## 2. Parity with the C chain

a. Without a compiler, the examples (step 1) already prove the released scores.

b. With a compiler (what the firmware CI job runs):

```bash
uv run pytest tests/security/can_ids/test_release_export_v2.py -q -k parity
```

Expected: `parity()` reports `score_mismatches == 0`, `alarm_mismatches == 0`,
`numpy_feature_mismatches == 0` on the parity captures and the examples.

## 3. Fresh environment: the install line is enough

```bash
rm -rf /tmp/fresh && uv venv -q --python 3.12 /tmp/fresh && uv pip install -q --python /tmp/fresh/bin/python ".[edge]"
du -sh /tmp/fresh/lib/python3.12/site-packages
/tmp/fresh/bin/python -c "import torch" ; echo "torch import exit: $? (expected 1)"
/tmp/fresh/bin/python -I - <<'EOF'
from mobility_model_zoo.security.can_ids import picket_forest as pf
import json, pathlib
ex = pathlib.Path("zoo/models/picket-forest/examples/01-fabrication.json")
cap = pf.load_capture(ex)
print(len(cap["ts"]), "frames loaded; no compiler, no repo paths used")
EOF
```

Expected: site-packages under 200 MB; `import torch` fails; the capture loads.

The same with `".[text]"` for scout-large: `python -c "import torch, transformers"` succeeds.

## 4. The gate runs the snippet of an mcu model and refuses a broken one

```bash
uv run pytest tests/release -q -k "usage_runner or rule_12 or card_mcu or card_emlearn"
```

Expected: install-line parsing, rule 12 for mcu (runs once, stores output, fails on exit ≠ 0),
golden cards with "Requires Python 3.12 or newer." and the "Output:" block.

Integration (network, optional locally; runs in CI with the slow marker):

```bash
uv run pytest tests/release/test_usage_runner.py -q -m network
```

Expected: a real venv with `[edge]` rejects `import torch`; picket-forest's snippet against the
staging repository exits 0 and prints the summary.

## 5. Patch releases (owner, release pipeline)

picket-forest 0.2.1:

```bash
uv run python -m mobility_model_zoo.security.can_ids.release_export_v2 repack --from-release 0.2.0 --out build/repack-0.2.1
```

(or the two documented steps: `snapshot_download(..., revision="v0.2.0")` into the directory,
then `security can-ids v2 table-json --out build/repack-0.2.1/calibration_table.json` and a copy
of `zoo/models/picket-forest/examples/*.json` into `examples/`). Then:

```bash
uv run zoo stage picket-forest 0.2.1 --from build/repack-0.2.1
uv run zoo check picket-forest 0.2.1
git diff --no-index <(yq '.files' zoo/models/picket-forest/releases/0.2.0.yaml) <(yq '.files' zoo/models/picket-forest/releases/0.2.1.yaml)
```

Expected: the gate passes; the diff shows only the four added files (same sha256 for every 0.2.0
file).

scout-large 0.1.3: copy `0.1.2.yaml` to `0.1.3.yaml` (new `version`, `date`, `change_type: patch`,
`changes`, `recipe.git_commit`; `published: null`, `deprecated: null`), then
`uv run zoo check scout-large 0.1.3`.

Tag `picket-forest/v0.2.1` and `scout-large/v0.1.3` → `release-verify` builds the preview; the owner
approves `release-publish` for each.

## 6. Deprecate the card that cannot be followed

```bash
uv run zoo deprecate picket-forest 0.2.0 --reason "the card's snippet could not be run from a fresh install; use 0.2.1" --successor 0.2.1
```

Expected: the 0.2.0 card carries the deprecation banner; files and tag unchanged.

## 7. The five-minute test (SC-001, SC-007)

On a machine without the repository, following only https://mhabedank.github.io/mobility-model-zoo/quickstart/
and the two cards:

```bash
mkdir try && cd try && uv venv --python 3.12 && source .venv/bin/activate
uv pip install "mobility-model-zoo[edge] @ git+https://github.com/mhabedank/mobility-model-zoo@picket-forest/v0.2.1"
# paste the card's snippet into demo.py
python demo.py
```

Expected within 5 minutes: the summary line of example 01 (one alarm at frame 1155). Repeat with
`[text]` and scout-large 0.1.3: the JSON with two pains. Record both times in
`specs/013-fresh-install-quickstart/validation.md`.
