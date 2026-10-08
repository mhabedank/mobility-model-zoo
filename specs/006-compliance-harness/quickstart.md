# Quickstart: validating the compliance harness

Validation scenarios for [spec.md](spec.md). Run them from the repository root on branch `006-compliance-harness`. Scenarios that need data use the local `data/` folder, which is never committed.

## Prerequisites

- Python 3.12, `uv`, `gitleaks`; the dev group installs `reuse`.
- `.env` with `MMZ_SUPPRESSION_KEY` (any random secret) and, for audit and publication, `HF_RELEASE_TOKEN`.

```bash
uv sync --extra jtbd --extra release
```

## 1. Register (US1)

```bash
uv run zoo compliance check --stage meta      # passes
uv run zoo validate --all                      # register validated too
```

Then move one `next_review` into the past and run it again: exit 2 with `meta / <record> / next_review`. Revert the change afterwards.

## 2. Generated documents (US2)

```bash
uv run zoo compliance render
uv run zoo compliance render --check           # exit 0
uv run reuse lint
```

Next, edit one line in `NOTICE` and run `render --check`: it exits 2 with `drift / NOTICE`. Revert the edit.

Finally, check that the privacy notice names every logged recipient. `recipients` lists one route per line; each must appear in `PRIVACY.md`:

```bash
uv run zoo compliance recipients --runs data/runs data/span-train-v1/runs
grep -c "" compliance/recipients.yaml
```

## 3. Seeded violations (US4, US5; SC-003)

```bash
HF_HUB_OFFLINE=1 uv run --offline pytest tests/compliance -q
```

Each check id in [contracts/checks.md](contracts/checks.md) has one failing fixture and the clean fixture passes.

## 4. scout-large 0.1.2 (US3)

```bash
uv run zoo compliance bootstrap-sources --topic productdev --model scout-large --version 0.1.1
uv run zoo compliance art9-scan --config configs/productdev/jtbd/span-train-v1.yaml
uv run zoo compliance redaction-recall          # ≥ 0.95
uv run zoo compliance scan-publish --model scout-large --version 0.1.2
uv run zoo compliance signoff --model scout-large --version 0.1.2
uv run zoo check scout-large 0.1.2              # all rules incl. 16 pass
```

Expected: the files and metrics are identical to 0.1.1 (rule 3), and the card preview shows the attribution table, the teacher routes and the policy links. Publication then runs through the existing tag → `release-verify` → owner approval → `release-publish` path.

## 5. Requests and legal watch (US6)

```bash
uv run zoo compliance request add --type takedown --identifier "https://example.org/x" --received 2026-10-08
uv run zoo compliance check --stage meta        # passes until the deadline
```

To check the review dates, set a legal-watch `review_by` to yesterday and run `check --stage meta`: it exits 2. Revert afterwards.
