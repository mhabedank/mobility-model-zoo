# Handover: continue feature 009 on a local machine

State on 2026-10-09, branch `009-jtbd-dedup-cluster`, PR #14 (draft). The cloud build environment could not reach `huggingface.co` or `download.pytorch.org`, so the steps below need a machine with network access.

## Done

- Spec, plan, research, data model, contracts, quickstart and tasks; `/speckit-analyze` findings fixed.
- Phase 1 (setup) except T008 and T009, Phase 2 (foundations), Phase 3 (user story 1, deduplication MVP): `jtbd cluster collect | run | check`, 56 tests on fictional fixtures with fixed vectors. CI green.
- T008 in part: licence bases recorded from the model cards (via web search) for multilingual-e5-small and -base (MIT), gte-multilingual-base and LaBSE (Apache-2.0).

## First steps locally

1. **T009, the `cluster` extra.** Add to `[project.optional-dependencies]` in `pyproject.toml`, then regenerate the lockfile with the repository's tooling:

   ```toml
   # Deduplication and clustering stage (`jtbd cluster`, feature 009) for users who run it after scout
   cluster = [
       "numpy>=1.26",
       "scipy>=1.13",
       "scikit-learn>=1.5",
       "pyyaml>=6.0",
       "jsonschema>=4.23",
       "typer>=0.12",
   ]
   ```

   ```bash
   uv lock
   uv sync --extra jtbd --extra cluster --extra release --extra edge
   ```

   Mention the extra in the README Setup section and tick T009.

2. **T008, pin the revisions.**

   ```bash
   uv run python topics/productdev/scripts/cluster/pin_revisions.py          # dry run
   uv run python topics/productdev/scripts/cluster/pin_revisions.py --write
   ```

   While pinning, read each model's LICENSE file and, for `Alibaba-NLP/gte-multilingual-base`, the remote code it loads (`trust_remote_code: true`).

3. **Owner decision: the NLI model.** `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7` is MIT, but its training data `multilingual-NLI-26lang-2mil7` contains ANLI subsets. Check the licences of that dataset and its sources for commercial use. If they do not allow it, choose another multilingual NLI model or drop the specificity relation from the baseline (spec FR-024 allows a level that is not produced). Its `licence_basis` stays `null` until then, so the stage refuses to load it (this only matters from user story 3 on).

4. **Smoke test with a real encoder.** After pinning, run the stage once on the fixture bundle with the real e5 encoder and check the result:

   ```bash
   uv run jtbd cluster run --input tests/fixtures/cluster/bundles/basic.jsonl --map /tmp/map-e5
   uv run jtbd cluster check --map /tmp/map-e5
   ```

   Expect the German/English paraphrase pairs to share groups; the thresholds are starting values until tuning (T032, T043, T044).

## Next

User story 2 (T022–T033 code, then the owner steps T063, T034–T036), then user stories 3–5 and the polish phase, in the order of `tasks.md`. Cash is spent only from T035 on (reference labeling, at most €20 in `budget-cluster.yaml`; confirm the OpenRouter key first).
