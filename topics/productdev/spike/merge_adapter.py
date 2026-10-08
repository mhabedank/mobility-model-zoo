"""Merge a PEFT LoRA adapter into its bf16 base model and save a standalone Hugging Face model.

The result can be converted to MLX for local use (topics/productdev/spike/build_local_model.sh).

Run: uv run --with torch --with transformers --with peft --with accelerate \
         python topics/productdev/spike/merge_adapter.py data/models/spike-v3b-adapter data/models/spike-v3b-merged
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    adapter, out = Path(sys.argv[1]), Path(sys.argv[2])
    base_id = json.loads((adapter / "adapter_config.json").read_text())["base_model_name_or_path"]
    print(f"base {base_id}, adapter {adapter}", flush=True)
    model = AutoModelForCausalLM.from_pretrained(base_id, torch_dtype=torch.bfloat16)
    model = PeftModel.from_pretrained(model, str(adapter)).merge_and_unload()
    out.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out, safe_serialization=True)
    AutoTokenizer.from_pretrained(base_id).save_pretrained(out)
    # transformers 5 writes `rope_parameters`, which mlx_lm 0.31 cannot read; the architecture is
    # unchanged by the merge, so keep the base model's original config.
    from huggingface_hub import hf_hub_download

    (out / "config.json").write_text(Path(hf_hub_download(base_id, "config.json")).read_text())
    (out / "MERGED_FROM.json").write_text(json.dumps(
        {"base": base_id, "adapter": str(adapter)}, indent=2) + "\n")
    print(f"saved {out}", flush=True)


if __name__ == "__main__":
    main()
