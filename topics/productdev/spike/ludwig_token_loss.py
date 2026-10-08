"""Build-time patch for Ludwig 0.17.9 (spike/Dockerfile.ludwig): token-weighted LLM loss.

Ludwig's NextTokenSoftmaxCrossEntropyLoss averages over the answer tokens of one batch. With batch
size 1 every example gets the same weight, so short "nothing found" answers weigh ~50x more per
token than long ones; an MLX run with that loss collapsed to {"relevant": false, "items": []}
(data/spike/findings.md). The patch sums over answer tokens (prompt tokens stay ignored with
-100) and divides by LUDWIG_LOSS_TOKEN_NORM, the mean answer length, so the loss keeps its usual
scale while every answer token has the same weight.

Fails the image build if Ludwig's code does not look exactly as expected.
"""

import importlib.util
import sys
from pathlib import Path

# Locate the file without importing it (importing loss_modules alone hits a circular import).
package = Path(importlib.util.find_spec("ludwig").submodule_search_locations[0])
path = package / "modules" / "loss_modules.py"
source = path.read_text()
start = source.index("class NextTokenSoftmaxCrossEntropyLoss(")
end = source.index("\n@register_loss", start)
block = source[start:end]

old_init = "        self.loss_fn = nn.CrossEntropyLoss()\n"
new_init = ('        self.loss_fn = nn.CrossEntropyLoss(reduction="sum")\n'
            '        self.token_norm = float(\n'
            '            __import__("os").environ.get("LUDWIG_LOSS_TOKEN_NORM", "1"))\n')
old_return = ("        return self.loss_fn(shifted_predictions.reshape(-1, vocab_size), "
              "shifted_targets.reshape(-1))\n")
new_return = ("        return self.loss_fn(shifted_predictions.reshape(-1, vocab_size), "
              "shifted_targets.reshape(-1)) / self.token_norm\n")

for old in (old_init, old_return):
    if block.count(old) != 1:
        sys.exit(f"unexpected Ludwig source in {path}: {old.strip()!r}")
patched = block.replace(old_init, new_init).replace(old_return, new_return)
path.write_text(source[:start] + patched + source[end:])
print(f"patched {path}: token-weighted NextTokenSoftmaxCrossEntropyLoss")
