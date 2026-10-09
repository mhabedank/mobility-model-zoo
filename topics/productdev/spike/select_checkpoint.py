"""Pick the best LoRA checkpoint of a spike training run by generation on the validation examples.

For each checkpoint (and the base model as reference) the model answers the held-out validation
chunks with greedy decoding, exactly as the benchmark server would. Score = mean of
- relevance accuracy (an unparsable answer counts as wrong),
- item F1 against the (repaired) teacher answer: span IoU >= min_iou, items whose quote is not in
  the chunk count as false positives.
The best checkpoint is copied to <adapter_path>-best. Results: data/spike/checkpoints.json.
The evaluation chunks of the benchmark are never used here.

Run: uv run --with mlx-lm==0.31.3 python topics/productdev/spike/select_checkpoint.py \\
    topics/productdev/spike/train_mlx.yaml
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import time
from pathlib import Path

import yaml
from mlx_lm import generate, load
from pydantic import ValidationError

from mobility_model_zoo.productdev.jtbd.labeling.base import parse_json_text
from mobility_model_zoo.productdev.jtbd.matching import match_items
from mobility_model_zoo.productdev.jtbd.runs import locate_items
from mobility_model_zoo.productdev.jtbd.schema import ExtractionOutput

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data/spike/checkpoints.json"
MIN_IOU = 0.3
MAX_TOKENS = 4096


def score(answer: str, target: ExtractionOutput, text: str) -> dict:
    parsed = parse_json_text(answer)
    try:
        out = ExtractionOutput.model_validate(parsed)
    except ValidationError:
        out = None
    targets = locate_items(target, text)
    if out is None:
        return {"valid": 0, "relevance_ok": 0, "tp": 0, "fp": 0, "fn": len(targets)}
    items = locate_items(out, text) if out.relevant else []
    tp = sum(1 for m in match_items(items, targets, MIN_IOU) if m.a and m.b)
    fp = len(items) - tp
    return {"valid": 1, "relevance_ok": int(out.relevant == target.relevant), "tp": tp, "fp": fp,
            "fn": len(targets) - tp}


def evaluate(adapter: Path | None, rows: list[dict], cfg: dict) -> dict:
    model, tokenizer = load(cfg["model"], adapter_path=str(adapter) if adapter else None)
    totals = {"valid": 0, "relevance_ok": 0, "tp": 0, "fp": 0, "fn": 0}
    start = time.monotonic()
    for row in rows:
        messages = row["messages"]
        prompt = tokenizer.apply_chat_template(messages[:-1], add_generation_prompt=True,
                                               tokenize=False)
        answer = generate(model, tokenizer, prompt=prompt, max_tokens=MAX_TOKENS)
        target = ExtractionOutput.model_validate(json.loads(messages[-1]["content"]))
        for k, v in score(answer, target, messages[1]["content"]).items():
            totals[k] += v
    n = len(rows)
    precision = totals["tp"] / (totals["tp"] + totals["fp"]) if totals["tp"] + totals["fp"] else 0
    recall = totals["tp"] / (totals["tp"] + totals["fn"]) if totals["tp"] + totals["fn"] else 0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {**totals, "schema_valid": totals["valid"] / n, "relevance_acc": totals["relevance_ok"] / n,
            "item_f1": round(f1, 4), "score": round((totals["relevance_ok"] / n + f1) / 2, 4),
            "seconds": round(time.monotonic() - start)}


def main(config_path: str) -> None:
    cfg = yaml.safe_load(Path(config_path).read_text())
    adapter_dir = ROOT / cfg["adapter_path"]
    rows = [json.loads(line) for line in (ROOT / cfg["data"] / "valid.jsonl").read_text().splitlines()]
    checkpoints = sorted(adapter_dir.glob("*_adapters.safetensors"))
    results = json.loads(OUT.read_text()) if OUT.exists() else {}
    results.setdefault("adapter_path", cfg["adapter_path"])
    results.setdefault("checkpoints", {})
    if "base" not in results["checkpoints"]:
        results["checkpoints"]["base"] = {"step": 0, **evaluate(None, rows, cfg)}
        OUT.write_text(json.dumps(results, indent=2))
    for ckpt in [*checkpoints, adapter_dir / "adapters.safetensors"]:
        name = ckpt.name
        if name in results["checkpoints"] or not ckpt.exists():
            continue
        tmp = ROOT / "data/spike/tmp-checkpoint"
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True)
        shutil.copy(adapter_dir / "adapter_config.json", tmp / "adapter_config.json")
        shutil.copy(ckpt, tmp / "adapters.safetensors")
        step = int(re.match(r"(\d+)_", name).group(1)) if name[0].isdigit() else "final"
        results["checkpoints"][name] = {"step": step, **evaluate(tmp, rows, cfg)}
        print(name, results["checkpoints"][name], flush=True)
        OUT.write_text(json.dumps(results, indent=2))
    trained = {k: v for k, v in results["checkpoints"].items() if k != "base"}
    best = max(trained, key=lambda k: (trained[k]["score"], -list(trained).index(k)))
    results["best"] = best
    best_dir = adapter_dir.with_name(adapter_dir.name + "-best")
    shutil.rmtree(best_dir, ignore_errors=True)
    best_dir.mkdir()
    shutil.copy(adapter_dir / "adapter_config.json", best_dir / "adapter_config.json")
    shutil.copy(adapter_dir / best, best_dir / "adapters.safetensors")
    OUT.write_text(json.dumps(results, indent=2))
    print("best", best, trained[best])


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "topics/productdev/spike/train_mlx.yaml")
