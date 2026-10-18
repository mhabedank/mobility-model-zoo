# Rendering rounds: audit trail

One directory per round (feature 019, FR-007; data-model.md "Rendering round"). The PNGs, the contact sheet and the thumbnails are not committed; they live under `~/zoo-imagery/rounds/<n>/` on the Spark and on the owner's machine.

| File | Written by | Content |
|---|---|---|
| `manifest.json` | `scripts/imagery/gen.py` (copied) | one entry per candidate with the full recipe, theme, subject, seed base, aspect |
| `triage.json` | `zoo site images triage` | per candidate: outcome (`shown` / `rejected`), reasons, measures, pHash, default focal point; summary |
| `picks.yaml` | the owner (via chat) | `theme/subject` → number or `none`, optional `focal` and `id` |
| `next.txt` | `zoo site images pick` | subjects for the next round |

Round 0 is the calibration run on the 016 renders (validation.md, section 1); it has no picks.

Container: `zoo-flux`, image id `sha256:373249621b54580b0c38d284e4ddfe433d733800569e5d253b01792ad7c75bcc` on the Spark (NGC PyTorch 25.09 + diffusers; `scripts/imagery/Dockerfile`). Models: FLUX.2-klein-4B for drafts, Qwen-Image-2512 for finals, both Apache-2.0, cached under `~/.cache/huggingface` on the Spark.
