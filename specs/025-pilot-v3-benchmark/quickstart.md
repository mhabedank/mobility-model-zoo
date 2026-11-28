# Quickstart: validate pilot-v3

`CFG` stands for `configs/productdev/jtbd/pilot-v3.yaml`. Every scenario lists what must be true at its end. The commands are in [contracts/cli.md](contracts/cli.md).

## 0. Without real data (fixtures and mocks)

```bash
UV_NO_SYNC=1 uv run pytest -q tests/unit/v3 tests/integration/test_pilot_v3_chain.py
```

Expected results:

- Statistics:
  - Every statistic matches the hand-computed fixture to three decimals: token IoU matching, kappa, linear weighted kappa, MASI alpha with both-empty, link F1 on matched pairs, and AC1 (SC-002).
  - Every branch of the decision rule gives the outcome the brief prescribes, including underpowered, extend, revise, the keep-always stop and per-language outcomes.
- Mock chain:
  - The mock chain runs sample, freeze-criteria, label pilot with mock references in three passes, agree, decide, full, consensus and freeze.
  - Every parsed output validates (SC-001).
  - A changed package file gives exit 3, an unapproved package exit 7, a Claude model exit 7, and a changed criteria file exit 3.

## 1. Package with pass instructions (owner gate)

```bash
uv run jtbd guide assemble --brief topics/productdev/guideline/scout-v3/brief.yaml \
  --examples topics/productdev/guideline/scout-v3/examples.yaml --out topics/productdev/guideline/scout-v3/package
uv run jtbd guide check --package topics/productdev/guideline/scout-v3/package   # exit 7 until the owner approves
# the owner runs: uv run jtbd guide approve --package … --by "<full name>"
```

## 2. Pool, separation and samples

```bash
uv run zoo catalog query --use benchmark --lang de,en …          # build the fetch list
uv run jtbd --config CFG source fetch … --permitted-uses benchmark_only
uv run jtbd --config CFG corpus autochunk …  &&  … corpus redact  &&  … corpus pii-review --model teacher-qwen3.8  &&  … corpus redact-check
uv run jtbd --config CFG v3 separation                            # exit 0: no overlap with training data
uv run jtbd --config CFG v3 sample --seed 20261128
uv run jtbd --config CFG v3 freeze-criteria
```

Expected results:

- at least 500 usable chunks per language;
- disjoint samples;
- the manifest is in state `criteria_frozen` with every hash.

## 3. Agreement pilot

```bash
uv run jtbd --config CFG label --role reference --backend ollama --model ref-qwen3.8-27b --split pilot
uv run jtbd --config CFG label --role reference --backend openrouter --model ref-deepseek-v4.1-flash --split pilot
uv run jtbd --config CFG label --role reference … --split enriched      # both references
uv run jtbd --config CFG v3 agree --step pilot && uv run jtbd --config CFG v3 decide && uv run jtbd --config CFG v3 report
```

Expected results:

- an outcome with estimate, interval and units for every field and language (SC-003);
- link prevalence from the random pilot only;
- cost within EUR 25 (SC-006);
- no run records a Claude model (SC-004).

## 4. If the decision says revise (at most once)

1. The owner approves the revised brief.
2. Assemble and approve the package again.
3. Run `v3 revise --rationale …`.
4. Label `--split holdout` with both references.
5. Run `v3 agree --step holdout` and then `v3 decide`.

## 5. Full benchmark and baselines

```bash
uv run jtbd --config CFG label --role reference … --split full      # both references, languages that passed
uv run jtbd --config CFG v3 consensus && uv run jtbd --config CFG v3 freeze
uv run jtbd --config CFG label --role baseline … --split full && uv run jtbd --config CFG v3 score --run <run>
```

Expected results:

- the manifest is `frozen` with `absent_fields` per language;
- every baseline is scored per field and language with intervals (SC-007).
