# Validation: Topic layout and security merge

## Baseline (2026-10-08, branch at main 966effe plus 005 docs)

- Default test suite: 474 passed, 1 skipped, 1 deselected in 108 s (run on the merged feature 006 state).
- `uv run zoo validate --all`: ok, compliance register ok.

## Tools

- git-filter-repo a40bce548d2c, gitleaks 8.30.1, Apple clang 21.0.0, GNU Make 3.81, gh logged in.

## US1 (2026-10-08)

- Productdev material moved to `topics/productdev/` in one rename-only commit (66 files); references in configs, code, scripts, tests, README and `model.yaml` updated. Frozen benchmark `pilot-v2` still verifies (`verify_frozen` ok; hashes are content-based).
- Default test suite: 482 passed, 1 skipped, 1 deselected in 120 s. `zoo validate --all` ok including topic folders; `zoo compliance check --ci` ok; `zoo audit`: scout-large 0.1.0, 0.1.1, 0.1.2 OK.
- Card links (`scripts/import/check_card_links.py`): all links of the published 0.1.0 and 0.1.1 cards resolve. The 0.1.2 card has one broken link that the move did not cause: the Senedd licence URL written by the feature 006 bootstrap (`senedd.wales/help/copyright/`, 404). Register and THIRD_PARTY_NOTICES now point to https://research.senedd.wales/commission/access-to-information/copyright/; the published card is immutable and gets the fix with the next card patch.
