# Contract: release gate, card template, website and schema changes

## `VenvRunner` (release/usage.py)

```python
VenvRunner(root: Path, hf_token: str | None, install_line: str, timeout: int = 600)
install_spec(root: Path, install_line: str) -> str   # "<root>[edge]" or "<root>"
```

- `install_spec` takes the extras from the first `[...]` after the package name of the install
  line (`mobility-model-zoo[edge] @ git+...` → `edge`; `mobility-model-zoo[text,extra2]` → both);
  no brackets → no extras. Anything else in the line is ignored (the git tag is replaced by the
  local checkout under gate).
- The venv is created once per runner; `uv venv --python 3.12`, then
  `uv pip install "<spec>"` with `UV_TORCH_BACKEND=cpu`. A failed install raises `UsageError`
  with the installer's last lines ("install" step of FR-009).
- `run(code)` unchanged: temp `HOME`, `HF_HOME`, `HF_TOKEN`, 600 s, token masked in stderr.
- `cli._runner()` and `publish.build()` pass `model["card"]["install"]`.

## Gate rule 12 (release/gate.py)

- runtime `python`: unchanged (first example through the runner).
- runtime `mcu`: after the device example check, when a runner is present:
  `code = cards.fill(how_to_run, staging.repo, staging.revision, "")`; `rc, out, err = runner.run(code)`;
  `rc != 0` → failure `"how_to_run failed (exit {rc}): {last 5 lines of err}"`; else
  `self.how_to_run_output = out.strip()[:MAX_OUTPUT_CHARS]`. Offline: `Skip` as today.
- The contract text in `specs/005-.../contracts/release-format.md` rule 12 gains: "for runtime mcu
  the snippet is run in the fresh environment built from the card's install line and its output is
  printed on the card".

## Tree-file rule (the rule that compares staged C sources with the recipe commit)

Adds, for engine `emlearn`: every `zoo/models/<name>/examples/*.json` is staged under
`examples/<file>` with the same sha256; `calibration_table.json` is staged and its entries equal the
entries of the staged `picket_forest_table.h` (parsed with the same regular expression the
header writer uses). Failure messages name the file.

## Card template (release/templates/model_card.md.j2)

After the `how_to_run` block, for mcu models with a recorded output:

```
Output:

```text
{{ how_to_run_output }}
```
```

After the device block, when `m.card.own_data` is set:

```
### Use it on your own vehicle

```python
{{ own_data }}
```
```

`card.py`: `CardInput` gains `how_to_run_output: str | None`; `render` passes `own_data` filled
with repo and revision. `build.json` carries `how_to_run_output`. Golden files regenerated.

## `model.schema.json` (release/schemas)

`card.own_data`: optional string. Rule 1 (conditional) requires nothing new; a snippet with
`{text}` in `own_data` is a failure for runtime mcu (no text input exists).

## Website (site/)

- Model page quickstart partial: for mcu models, step "Get this output" shows
  `how_to_run_output` from the published card (same source as the F4 parity check); a further step
  "Use your own vehicle" shows `own_data` when set.
- New page `/quickstart/` rendered from `docs/quickstart.md` with `site/markdown.py`; the install
  lines in the doc are written as `{install:<model>}` placeholders that the build replaces with
  `install_line(model, latest published version)`; the README shows the same lines verbatim and a
  test checks they match the registry.
- Start page hero: a "Try it in five minutes" link to `/quickstart/`; model page install step:
  "New here? Start with the quickstart."

## Replayed failures (tests/release)

| Test | Asserts |
|---|---|
| `test_usage_runner.py::test_install_spec` | extras parsed from the install line; none → bare root |
| `test_usage_runner.py::test_fresh_env_rejects_import_outside_extra` (network, slow) | real runner with `[edge]`: `import torch` snippet exits ≠ 0 |
| `test_gate_rules.py::test_rule_12_runs_how_to_run_for_mcu` | `FakeRunner.calls == [filled snippet]`; output stored; card shows it |
| `test_gate_rules.py::test_rule_12_fails_when_mcu_snippet_fails` | `FakeRunner(returncode=1)` → failure names `how_to_run` |
| `test_picket_forest_reference.py::test_module_imports_are_user_safe` | AST imports ⊆ allowlist; no `edge.paths`, `ctypes`, `subprocess`, `pandas` |
| `test_card_mcu.py` / website partial test | "Requires Python 3.12 or newer." next to the install line |
