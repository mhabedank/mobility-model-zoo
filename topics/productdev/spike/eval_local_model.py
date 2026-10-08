"""Score a local MLX model on the spike's evaluation chunks (spike, not a benchmark).

Runs the model on every main-split chunk of spike-v1 and scores the outputs against the Claude
reference exactly like `topics/productdev/spike/ensemble.py` scores its strategies. The frozen-hash checks of the
`pilot` commands are bypassed on purpose: the spike benchmark was frozen with older criteria.
Answers get the same early stop and clean-up as topics/productdev/spike/try_model.py.
Outputs go to data/spike/local-eval/<model name>/ and are reused on a rerun.

Run: uv run --with mlx-lm python topics/productdev/spike/eval_local_model.py [--model data/models/spike-v3b-mlx-8bit]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "spike"))

from ensemble import scores  # noqa: E402

from mobility_model_zoo.productdev.jtbd.config import load_settings  # noqa: E402
from mobility_model_zoo.productdev.jtbd.consensus import load_consensus  # noqa: E402
from mobility_model_zoo.productdev.jtbd.corpus.store import chunk_map  # noqa: E402
from mobility_model_zoo.productdev.jtbd.runs import ChunkOutput, load_outputs, locate_items  # noqa: E402
from mobility_model_zoo.productdev.jtbd.schema import ExtractionOutput  # noqa: E402

V3B_RUN = "run-baseline-spike-v3b-main-3223351c"


def main() -> None:
    from mlx_lm import load
    from try_model import extract, salvage

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, default=ROOT / "data/models/spike-v3b-mlx-8bit")
    args = parser.parse_args()
    settings = load_settings(ROOT / "configs/productdev/jtbd/spike-v1.yaml")
    min_iou = float(settings.pilot.get("min_iou", 0.3))
    consensus, contested, meta = load_consensus(settings, "main")
    chunks = chunk_map(settings, "main")
    out_dir = ROOT / "data/spike/local-eval" / args.model.name
    out_dir.mkdir(parents=True, exist_ok=True)
    system = (args.model / "system_prompt.txt").read_text(encoding="utf-8")
    model, tokenizer = load(str(args.model))

    outputs: dict[str, ChunkOutput] = {}
    invalid, seconds_total = 0, 0.0
    for n, (chunk_id, chunk) in enumerate(sorted(chunks.items()), start=1):
        path = out_dir / f"{chunk_id}.json"
        if path.exists():
            record = json.loads(path.read_text())
        else:
            answer, seconds = extract(model, tokenizer, system, chunk.text)
            record = {"answer": answer, "seconds": round(seconds, 2)}
            path.write_text(json.dumps(record, ensure_ascii=False, indent=1))
        seconds_total += record["seconds"]
        try:
            output = ExtractionOutput.model_validate(salvage(record["answer"])[0])
            outputs[chunk_id] = ChunkOutput(chunk_id, output.relevant,
                                            locate_items(output, chunk.text))
        except Exception:  # noqa: BLE001 - an invalid answer counts against the model
            outputs[chunk_id] = ChunkOutput(chunk_id, None)
            invalid += 1
        print(f"{n}/{len(chunks)} {chunk_id} {record['seconds']:.1f}s", flush=True)

    local = scores(outputs, consensus, contested, meta["chunks"], min_iou)
    vllm = scores(load_outputs(settings, V3B_RUN), consensus, contested, meta["chunks"], min_iou)
    items = [i for o in outputs.values() for i in o.items]
    result = {
        "model": str(args.model),
        "chunks": len(chunks),
        "schema_valid": round(1 - invalid / len(chunks), 3),
        "quote_verbatim": round(sum(i.valid for i in items) / len(items), 3) if items else None,
        "mean_seconds_per_chunk": round(seconds_total / len(chunks), 1),
        "local": local,
        "reference_spike_v3b_vllm_bf16": vllm,
    }
    (out_dir / "summary.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
