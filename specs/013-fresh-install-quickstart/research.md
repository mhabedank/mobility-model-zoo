# Research: Quickstart that works from a fresh install

Findings of 2026-10-11. Every unknown of the Technical Context is resolved here; the evidence is
either read from the repository (file:line) or measured in a scratch environment.

## R1. Dependency layout: small base, one extra per model kind

**Decision**: `dependencies` becomes `huggingface_hub`, `numpy`. New extra `text` = `torch`,
`transformers`, `safetensors`, `sentencepiece` (today's base). `edge` keeps its tooling entries and
gains `scikit-learn>=1.5`, `joblib>=1.3`. `jtbd` gains the self-reference `mobility-model-zoo[text]`
so the JTBD tool and CI keep torch. Install lines: scout-large and sandbox-pipeline-tiny
`mobility-model-zoo[text] @ git+...`; picket-forest, picket-mlp, hum-fan, pace-cnn
`mobility-model-zoo[edge] @ git+...` (unchanged text, now sufficient).

**Rationale**: the base today (`pyproject.toml:21-27`) is the text stack; the only runtime
importers of torch are `productdev/jtbd/span/{extractor,model,train}.py` and `sandbox/model.py`.
A fresh venv with numpy + scikit-learn + joblib + huggingface_hub measures 144 MB installed
(scratch measurement, uv, Python 3.12, 2026-10-11) against 877 MB for today's `[edge]` install.
Self-referencing extras are supported by pip (since 21.2) and uv. CI syncs
(`ci.yml:54,88,104,143`, `firmware.yml:45`, `datasets.yml:26`, `hil.yml:37`) name `edge` or `jtbd`
and keep working; `--no-install-package torch` becomes a no-op where torch is no longer pulled.

**Alternatives considered**: a per-model extra (`[picket-forest]`) — rejected, extras per model
kind are enough and match the two runtimes the gate knows; adding scikit-learn to the base —
rejected, text models do not need it; keeping torch in the base and documenting the size — rejected
by the spec (SC-002).

## R2. Pure-numpy reference of the picket-forest chain, bit-exact with C

**Decision**: new module `mobility_model_zoo/security/can_ids/picket_forest.py` with
`features(cap, table)`, `rules(x, margin)`, `alarms(ts_us, flagged, k, window_ms, holdoff_ms)`,
`vote_score(clf, x)` and `score(cap, table, model)`; `Table`, `calibrate`, `to_us`, `bucket_counts`,
`FEATURE_NAMES` move there and `calibrated.py` / `forest.py` re-export them. `calibrated.features`
(C via ctypes) stays as the parity oracle for developers.

The port follows `firmware/components/can_features/msml_cal.c` (210 lines) and `msml_alarm.c`
(53 lines) feature by feature:

| Feature | C | numpy |
|---|---|---|
| `known_id` | binary search in the sorted table | `np.isin` against the table's ids |
| `log_dt_period` | `q_log2(ts - last_us, period_us)`; `LOG_CAP` for the first frame of an id or `period_us == 0` | per id: `np.diff` of the id's timestamps; first frame and `period == 0` set to `LOG_CAP` |
| `log_count_ratio`, `count_excess` | 8-bucket ring per id, cleared on bucket change (all 8 when the shift is larger than 8); saturates at 65535 | `bucket_counts` (`calibrated.py:100`, already the same arithmetic: frames with bucket index in `[b-7, b]` via `searchsorted`); saturation unreachable in practice, documented |
| `dlc_changed_cal` | `dlc != table dlc` | vectorised compare |
| `hamming`, `bytes_changed` | against the id's previous frame; 0 for the first | per id: `np.bitwise_xor` with the shifted data, popcount via lookup table |
| `unknown_count`, `unknown_count_long` | ring of the last 64 unknown frames; count those within the last 256 / 2048 bus frames and 2 s | cumulative count of unknown frames, windowed by frame index and by `searchsorted` on time, clipped at 64 |
| `log_bus_rate` | 0 until 256 frames seen; `q_log2(256.0 * 1e6 / (ts - ts[n-256]), bus_rate)` | shift by 256 frames; same expression order |
| `q_log2` | `log2(num/den)`, `floor(r*256+0.5)/256`, clip ±8, non-finite → +8, cast float32 | identical in float64 then `astype(float32)` |
| rules | `x[2] > log2(1+margin) or x[7] >= 3 or x[8] >= 8 or x[4] == 1` | `calibrated.rules` (`calibrated.py:239`, already numpy) |
| alarm stage | k flagged within window, then hold-off | loop over flagged frames only (few hundred at most), same integer arithmetic |
| forest score | emlearn hard votes per tree | `forest.vote_score` (`forest.py:127`, already numpy + sklearn `tree.predict`) |

**Float parity risk and its test**: the only transcendental is `log2` on float64 before the
1/256 quantisation. numpy's `log2` and the platform's libm (used by the C build) can differ by one
ulp on some builds; a flip of the quantised value requires the true value to lie within one ulp of a
half-step, which the parity test will show if it ever happens. Fallback, if the parity test fails
on a platform: compute `q_log2` with `math.log2` through `np.frompyfunc` (same libm as the C
build). Parity is proven twice: (a) without a compiler, in every CI run: the numpy reference
reproduces `expected_scores` (float32 bit patterns) and `expected_alarms` of the three example
captures, which the release gate produced with the C scorer; (b) with a compiler, in the firmware
job: numpy against `calibrated.features` (C) on the parity captures and the examples, 0 mismatches
(`release_export_v2.parity` gains a third column).

**Alternatives considered**: shipping the C sources as package data and compiling with ctypes at
first use — rejected by the owner (needs a compiler on the user's machine; Windows out); a
prebuilt wheel with a C extension — rejected (build matrix, release pipeline change, PyPI out of
scope); a Python loop over frames — rejected for the parity captures (millions of frames), kept
only for the alarm stage where it touches flagged frames alone.

## R3. Files in the model repository and patch releases without retraining

**Decision**: picket-forest's model repository gains `examples/01-fabrication.json`,
`examples/02-dos.json`, `examples/03-fuzzing.json` (byte-identical copies of the registry files,
about 190 KB each, source `synthetic`) and `calibration_table.json` (format
`picket-forest-table-v1`, see data-model.md), the same table as `picket_forest_table.h`.
`release_export_v2.export()` writes both for future releases. For 0.2.1 the staging directory is
assembled without retraining: download the public files of 0.2.0 (`huggingface_hub.snapshot_download`
at `v0.2.0`, excluding `README.md`), add the examples and the table JSON (the table is
`release_export_v2.example_table()`, deterministic from the synthetic generator with its seed; a
test checks it equals the header), then `zoo stage picket-forest 0.2.1 --from <dir>`. For
scout-large 0.1.3 no file changes: the record `0.1.3.yaml` is a copy of `0.1.2.yaml` with
`version`, `date`, `change_type: patch`, `changes`, `published: null`, `deprecated: null`; `files`
and `staging` stay, so the gate verifies the same staged revision and `publish` re-uploads the same
bytes under the new tag. Both records point `recipe.git_commit` at the commit of this feature (the
packaging is the change).

**Rationale**: `publish.stage()` (`publish.py:105-134`) uploads every file of a directory and writes
the record's `files` list; `publish()` downloads the staged files by the record (`publish.py:220-256`)
and the gate's tree-file rule compares staged C sources with the recipe commit. A copied record is
the smallest change that keeps every immutability and hash check intact. `forbidden_upload`
(`publish.py:62-70`) allows `.json` under `examples/`.

**Gate addition**: the rule that checks staged C sources against the repository (the
`_staged_tree_scorer` family) also checks that every `examples/*.json` of the registry is staged
byte-identically and that `calibration_table.json` parses to the same entries as
`picket_forest_table.h`.

**Alternatives considered**: a `zoo repack` command — rejected, two one-off steps documented in
quickstart.md are enough; regenerating 0.2.1 by running the full export — rejected, it retrains and
would not be byte-identical to 0.2.0.

## R4. `VenvRunner` installs what the card's install line installs

**Decision**: `VenvRunner.__init__` takes the card's install line; `install_spec(root, line)`
extracts the extras in square brackets after the package name (`mobility-model-zoo[edge] @ ...`
→ `edge`) and installs `"<root>[edge]"`; no extras → `"<root>"`. The gate passes
`model["card"]["install"]` when it constructs the runner (`cli.py:64`, `publish.py:140`). The venv
is built once per gate run and per extras set.

**Rationale**: today `usage.py:33-37` installs `str(self.root)` without extras, which is exactly
failure (2) of the spec. The install line is the one place the card promises something to users.

**Alternatives considered**: installing every extra — rejected, it hides a missing one; parsing
`pyproject.toml` for the model's kind — rejected, the install line is the contract.

## R5. Running `how_to_run` for microcontroller models and showing its output

**Decision**: rule 12 runs `how_to_run` in the fresh environment for every runtime. For `mcu`
models it runs after the device example check, filled with the staging repository and revision
(`cards.fill`, `card.py:80`, tolerates a snippet without `{text}`), and stores the printed output as
`gate.how_to_run_output`. The card template prints it in an "Output:" block under the snippet for
mcu models (text models already show per-example outputs). `build.json` carries it so the website's
quickstart partial shows the same text ("Get this output"). Rule 13 (examples) is unchanged for
mcu. Offline (`zoo check --offline`) skips as today.

**Rationale**: `gate.py:482-491` skips the runner entirely for mcu; the output slot on the card
exists only for text examples. One extra `self.runner.run(code)` call and one template block close
failure (5) without a new rule number; the contract text of rule 12 is updated.

**Alternatives considered**: a new rule 18 — rejected, rule 12 is "the snippet runs"; running the
snippet per example for mcu — rejected, the snippet downloads one example by name.

## R6. Quickstart placement: one source, rendered twice

**Decision**: `docs/quickstart.md` is the single source ("Try it in five minutes"): Python 3.12
with uv, one fresh environment, `uv pip install` with the install line of the model, a script
(`python demo.py`, not an interactive shell), expected output, then the pitfalls. The website
renders it at `/quickstart/` through `site/markdown.py` and links it from the start page hero and
every model page's install step; the README gets a six-line "Try it" section that shows the three
commands for picket-forest and links to the doc. The install lines in the doc are the registry's
(`install_line` with the latest published version) so they never drift.

**Rationale**: the website already renders Markdown fields through `site/markdown.py` and builds
pages from the registry (`site/build.py:176-252`); a hand-copied page would drift.

**Alternatives considered**: README only — rejected, the website is where the public lands;
website only — rejected, the spec names both.

## R7. candump without pandas

**Decision**: `picket_forest.read_candump(path) -> capture` ports `frames.read_candump`
(`frames.py:61-80`): the same regular expression over the bytes of the file, numpy arrays out, no
DataFrame. `frames.read_candump` keeps its DataFrame signature for the tooling by wrapping the
numpy version. The second card snippet (`card.own_data`) uses it with `calibrate` and
`save_table`; `zoo-security can-ids v2 table` writes `picket_forest_table.json` next to the header.

**Rationale**: the user-facing module must not import pandas (spec goal; `release_export_v2.py:29`
is where today's import chain pulls it in).

## R8. What happens to 0.2.0 and 0.1.2

**Decision**: after 0.2.1 is published, `zoo deprecate picket-forest 0.2.0 --reason "card could
not be followed from a fresh install" --successor 0.2.1` (existing command, card-only commit).
scout-large 0.1.2 is not deprecated: its card works.

**Rationale**: constitution IX: a broken version is marked deprecated, never rewritten. The device
artefacts of 0.2.0 are valid; the deprecation banner says what is wrong and where to go.

## R9. Environment tool and the pitfalls to name

**Decision**: the quickstart recommends `uv` (`uv python install 3.12`, `uv venv --python 3.12`,
`uv pip install ...`) and gives the `python3.12 -m venv` + `pip` route in one line. Pitfalls, each
with its symptom from the owner's log of 2026-10-11: an `ipython` from another interpreter answers
although the venv is active (`Python 3.11.7` banner inside a 3.12 venv) — run `python demo.py`
or install ipython into the venv; `pip` is not installed in uv environments (`No module named
pip`) — use `uv pip install`; Python pasted into the shell (`zsh: command not found: from`) — save
the snippet as a file.

## R10. The five failures, replayed as tests

| Failure of 2026-10-11 | Test that rejects it |
|---|---|
| Python requirement not stated | golden card test and website partial test assert "Requires Python 3.12 or newer" (already in the working tree) |
| library missing from the extra | `test_usage_runner`: `install_spec` keeps the extras of the install line; integration test (network marker): a snippet importing a module outside the extra fails with exit ≠ 0 in the real `VenvRunner` |
| repository-only resource | import-hygiene test: AST of `picket_forest.py` imports only numpy, joblib, sklearn, json, re, pathlib, dataclasses, typing; never `edge.paths`, `ctypes`, `subprocess`, `pandas` |
| undefined name in the snippet | gate test with a `FakeRunner` returning exit 1 for an mcu model: rule 12 fails and names `how_to_run`; the real run turns a `NameError` into exit 1 |
| snippet never run for mcu | gate test: for an mcu model rule 12 calls the runner exactly once with the filled snippet and stores its output; the card shows it |
