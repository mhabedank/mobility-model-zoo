# Quickstart: validate the model pages in progressive depth

How to prove feature 014 works end to end. Commands are those of [docs/website.md](../../docs/website.md); checks are defined in [contracts/checks.md](contracts/checks.md).

## Prerequisites

- Feature 012 merged into `main`, this branch rebased onto it.
- `uv sync --extra release --group site-check` and `uv run playwright install chromium` (once).

## 1. Offline: structure, budgets, facts

```bash
uv run pytest tests/website tests/release/test_card_build.py tests/release/test_gate_site_text.py
```

Expected: all pass, including the tests for D1–D5, the changed A2 and F2 scope, gate rules 17 and 18, the card section order and the regenerated golden card.

## 2. Build and check the real registry

```bash
uv run zoo site build
```

```bash
uv run zoo site check --a11y
```

Expected: zero findings. D6 reports the measured positions; for scout-large and picket-forest the first quality figure is at or below 2.0 screens, `#limits` at or below 4.0 screens (baseline 2026-10-11: 9.3 and 10.1 for scout-large).

## 3. Look at it

```bash
uv run zoo site serve
```

Open http://localhost:8000/mobility-model-zoo/models/scout-large/ and /models/picket-forest/ and confirm:

- First screen: name, one-line description, "experimental" chip and sentence, licence and usage class chips, 3–4 short reasons, 2–3 "not for" points, jump links.
- Directly below: headline figures and (scout-large) both charts; picket-forest shows figures with comparison bars where a comparison exists.
- Then the limits short form with the unmet criteria and their measured values, then the quickstart, then interface and examples, then all metrics, provenance and documents, versions, citation.
- Old links still land: `#quickstart`, `#interface`, `#examples`, `#provenance`, `#fn-1`.
- With JavaScript disabled, the collapsed limitations text is still in the page; at 390 px nothing scrolls sideways.

## 4. Negative checks

- Lengthen a differentiator text in a copy of the frozen test registry beyond 20 words: `zoo check` (rule 17) and `zoo site check` (D2) fail and name the model, the field and the count.
- Remove `unmet_criteria` from an `experimental` model in the test registry: rule 18 and D1 fail.
- Add a field table back into the interface partial: D3 fails.

## 5. Card

```bash
ZOO_UPDATE_GOLDEN=1 uv run pytest tests/release/test_card_build.py -k golden
```

Then `git diff` the golden card: only moved sections and the new short-form blocks, no changed number.

## 6. Reader test (SC-005)

After deployment, five readers from the target group open a model page and answer within 30 seconds: what does it do, how good and how fast in one sentence, is it experimental. Pass: at least four of five. Recorded in `specs/014-model-page-layout/validation.md`; it can be combined with the open SC-001 user test of feature 008.
