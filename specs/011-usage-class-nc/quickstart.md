# Quickstart: validate usage classes and non-commercial releases

Prerequisites: `uv sync --extra jtbd --extra release --extra edge`; no network needed.

## 1. Audit the zoo

```bash
uv run zoo compliance usage
```

Expect one block per model (six models), each with declared and derived class or a named finding; finishes in under a minute; `git status` shows no changes afterwards (SC-004).

## 2. Non-commercial fixture model passes and is marked

```bash
uv run pytest tests/release/test_usage_class.py -k nc_fixture
```

The fixture `nc-fixture-tiny-nc` (declared `non-commercial`, one CC-BY-NC-4.0 dataset) passes the offline gate. Its rendered card, front matter, release record and site page contain "non-commercial", `CC-BY-NC-4.0` and the dataset id (SC-001).

## 3. Hidden restrictions are refused

```bash
uv run pytest tests/release/test_usage_class.py -k refused
```

Five cases, one per input kind (dataset, base model, teacher, third-party run-time model, zoo-model output), each declared commercial; each is refused with a message naming the input (SC-002). Inputs that forbid training are refused for both classes (SC-003).

## 4. Third-party register

```bash
uv run zoo compliance check --ci
```

The meta stage validates `compliance/third-party-models.yaml`; scout-large's base model is registered and matches `configs/productdev/jtbd/span-xlmr.yaml`.

## 5. Website

```bash
uv run zoo site build --out /tmp/site --offline && uv run zoo site check --out /tmp/site --offline
```

Each model page shows its usage class; the start page makes no zoo-wide promise of commercial use (SC-006).

## 6. Full suite

```bash
uv run pytest && uv run ruff check .
```
