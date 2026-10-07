"""The span model runs with the base install only (T013, research R18).

Builds a fresh virtual environment with CPU-only torch, installs this repository without extras and
runs `SpanExtractor` on the tiny model there. Run with `uv run pytest -m slow`.
"""

import json
from pathlib import Path

import pytest

from mobility_model_zoo.release.usage import VenvRunner

ROOT = Path(__file__).resolve().parents[2]

CODE = """
import importlib.util, json, sys
from mobility_model_zoo.productdev.jtbd.span import SpanExtractor

# Only in the [jtbd] extra (typer and pyyaml also come with huggingface_hub and transformers).
extras = [m for m in ("openai", "rapidfuzz", "pandas", "trafilatura", "pypdf", "sklearn")
          if importlib.util.find_spec(m) is not None]
model = SpanExtractor.from_pretrained({model_dir!r})
out = model.extract("Der letzte Bus fährt um 18 Uhr. The charger was broken again.")
print(json.dumps({{"extras": extras, "items": len(out["items"]),
                   "version": out["output_format_version"]}}))
"""


@pytest.mark.slow
def test_span_extractor_runs_with_base_install_only(tiny_span_model):
    model_dir = str(tiny_span_model())
    code, out, err = VenvRunner(ROOT, hf_token=None).run(CODE.format(model_dir=model_dir))
    assert code == 0, err
    result = json.loads(out.strip().splitlines()[-1])
    assert result["extras"] == [], "the fresh environment must not contain [jtbd] dependencies"
    assert result["version"] == "jtbd-span-v1"
    assert result["items"] > 0
