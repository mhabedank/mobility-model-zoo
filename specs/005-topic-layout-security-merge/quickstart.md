# Quickstart: validating the topic layout and security merge

Validation scenarios for [spec.md](spec.md). Run from the repository root on the feature branch unless stated otherwise.

## Prerequisites

- Python 3.12, `uv`, `git`, `git-filter-repo`, `gitleaks`, `gh` (logged in as the owner), a C compiler and `make`.
- Optional: PlatformIO (firmware builds), Espressif QEMU (emulated ESP32), a board on USB.

```bash
uv sync --extra jtbd --extra release --extra edge
```

## 1. Layout (US1)

```bash
ls topics/                                   # productdev  security  condition-monitoring
ls guideline reports benchmarks spike deploy docs/recipes 2>&1 | grep -c "No such"   # 6
uv run zoo validate --all                    # ok, including topic folders and dataset declarations
HF_HUB_OFFLINE=1 uv run --offline pytest -q  # all pass (baseline before the feature: 363 passed, 1 skipped)
uv run zoo audit                             # scout-large 0.1.0 and 0.1.1 ok (needs HF_RELEASE_TOKEN)
```

Expected: no JTBD folder at the top level; every published `scout-large` link still resolves (they point at fixed commits and tags).

## 2. History (US2 scenario 1, SC-001)

```bash
git log --follow --format='%h %an %ad %s' -- src/mobility_model_zoo/security/can_ids/metrics.py | tail -3
git log --follow --format='%h %an %s' -- src/mobility_model_zoo/edge/int8/reference.py | tail -3
uv run python scripts/import/check_merge_log.py   # every source file is mapped or listed as dropped
```

Expected: commits from 2026-10-07 by the original authors; the merge-log check exits 0.

## 3. No data, no secrets (SC-005)

```bash
uv run zoo history-check                     # gitleaks over all commits + forbidden paths
git log --all --format= --name-only | grep -E 'test_vectors\.h|\.bin$|model_zoo\.c|\.joblib$' | wc -l   # 0
```

## 4. Datasets (US3)

```bash
uv run zoo data list --topic security
uv run zoo data verify                       # api entries ok, manual entries show their check date
MMZ_DATA=$(mktemp -d) uv run zoo data download uci-har
uv run zoo data download syncan              # refused, exit 3, reason "rejected: non-commercial"
git status --porcelain | wc -l               # 0: nothing landed in the repository
```

## 5. Edge bench and models (US4)

```bash
uv run edge build -t native && uv run pytest -m hil --hil-board sim -q
uv run edge --boards hil/qemu-boards.yaml run -b esp32-qemu --quick     # optional, needs QEMU
for m in picket-forest picket-mlp hum-fan pace-cnn; do uv run zoo check $m 0.1.0 --offline; done
uv run zoo build pace-cnn 0.1.0 --out /tmp/pace-cnn-card   # renders the mcu card (build needs no Hub access)
```

Expected: `zoo check` exits 2 for each model with a concrete list (files not staged, no real-board latency), never with a schema error; the rendered card shows the KB budget, the origin column and the ground-truth quality sentence.

## 6. Credentials and retirement (US5)

```bash
gh secret list -R mhabedank/mobility-model-zoo        # HF_RELEASE_TOKEN
gh variable list -R mhabedank/mobility-model-zoo      # HIL_RUNNER_ENABLED
# after the merge to main and retirement:
gh repo view mhabedank/mobility-security-ml --json isArchived    # true
gh secret list -R mhabedank/mobility-security-ml                 # empty
```
