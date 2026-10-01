"""Build the sandbox test model: `python -m mobility_model_zoo.sandbox.build_test_model --out <dir>`.

Writes `model.safetensors` and `config.json` (the generated README is removed: the release
pipeline writes the model card). The weights come from a fixed seed, so every run
produces the same files (the recipe of the sandbox release record).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from mobility_model_zoo.sandbox.model import PipelineTestModel


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    model = PipelineTestModel(seed=args.seed)
    model.save_pretrained(args.out)
    (args.out / "README.md").unlink(missing_ok=True)
    for path in sorted(args.out.iterdir()):
        print(path)


if __name__ == "__main__":
    main()
