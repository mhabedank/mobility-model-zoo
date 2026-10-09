# Quickstart: validating picket-forest 0.1.0

Run from the repository root on branch `007-picket-forest-release`.

## Prerequisites

- Python 3.12 and `uv`, with `uv sync --extra jtbd --extra release --extra edge --extra edge-train`. Training needs scikit-learn and emlearn.
- A C compiler and `make`.
- PlatformIO (`--extra edge-hw`), Espressif QEMU, and the D1 mini on USB with an entry in `hil/boards.yaml` (`uv run edge discover`).
- About 10 GB free in `$MMZ_DATA`.

```bash
uv run zoo data download can-train-and-test
uv run zoo data download road
```

## 1. Benchmark (US1)

```bash
uv run security can-ids freeze           # writes topics/security/benchmarks/can-ids-v1/manifest.json
uv run security can-ids freeze           # second run: exit 0, no change (SC-001)
git diff --stat topics/security/benchmarks/
```

If the first run exits 1 with duplicate groups, write `resolutions.yaml` and run it again. Then corrupt one cached capture (or point `--data` at a copy with one changed frame) and run `evaluate`: it must exit 1 and name the capture.

## 2. Evaluation (US2)

```bash
uv run security can-ids evaluate picket-forest --benchmark can-ids-v1 --sets set_01   # fast check, partial
uv run security can-ids evaluate all --benchmark can-ids-v1 --report                  # full run, hours
```

The report must show:

- headline tables per split (median and worst set);
- the controls and baselines next to picket-forest;
- `ctrl-shuffled` collapsed;
- the ROAD section;
- the out-of-scope section.

The success, partial or kill outcome of [research R10](research.md) is stated at the top of `report.md`.

## 3. Gate for tree models (US3)

```bash
uv run pytest tests/release -q -k "emlearn or tree"
```

A fixture tree model passes. Flipping one expected score bit fails rules 12 and 13 (SC-006).

## 4. Release (US4)

```bash
uv run security can-ids forest export
uv run security can-ids forest examples --out zoo/models/picket-forest/examples
uv run security can-ids measure --target host --out zoo/models/picket-forest/results/0.1.0/performance.json
uv run security can-ids measure --target esp32-qemu --out zoo/models/picket-forest/results/0.1.0/performance.json
uv run security can-ids measure --target esp8266 -b esp8266-1 --out zoo/models/picket-forest/results/0.1.0/performance.json   # D1 mini on USB
uv run zoo stage picket-forest 0.1.0 --from "$MMZ_DATA/derived/picket-forest/export"
uv run zoo compliance scan-publish --model picket-forest --version 0.1.0
uv run zoo check picket-forest 0.1.0 --offline     # all offline rules pass (SC-005)
```

Then tag `picket-forest/v0.1.0`. `release-verify` must pass every rule. After the owner's review and approval, `release-publish` runs.
