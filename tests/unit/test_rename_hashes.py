"""The freeze hashes must survive the move of configs and code (feature 003, T004).

Freeze hashes are content-based, so moving files must not change them. The expected values were
computed from `configs/pilot-v1.yaml` before the rename (now `configs/productdev/jtbd/pilot-v1.yaml`).
Later intended content changes update the fixture: `budget.yaml` got the GPT mini price in 001 T046
(2026-10-06), and the default config points at guideline-v2 and examples-v2 for the pilot-v2
rerun (001 T081, 2026-10-06).
"""

from __future__ import annotations

import json
from pathlib import Path

from mobility_model_zoo.productdev.jtbd.config import DEFAULT_CONFIG, load_settings
from mobility_model_zoo.productdev.jtbd.freeze import schema_sha256, sha256_canonical

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = json.loads((ROOT / "tests/fixtures/rename-hashes.json").read_text(encoding="utf-8"))


def test_default_config_hashes_unchanged_by_rename():
    settings = load_settings(ROOT / DEFAULT_CONFIG)
    current = {k: sha256_canonical(settings.paths[k]) for k in EXPECTED if k != "schema"}
    current["schema"] = schema_sha256()
    assert current == EXPECTED
