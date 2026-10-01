# Implementation Plan: End-to-end spike

> **Note (feature 003):** Since feature 003 the CLI `pilot` is `jtbd`, the code is in `src/mobility_model_zoo/productdev/jtbd/` and the configs are in `configs/productdev/jtbd/`. Paths and commands below are historical.

**Branch**: `002-e2e-spike` | **Date**: 2026-09-27 | **Spec**: [spec.md](spec.md) | **Type**: technical spike

## Summary

This spike reuses the pilot package `jtbd_pilot` and adds only what the chain is missing:

- automatic chunking from snapshots, with a `train` split
- a generic OpenAI-compatible backend for vLLM
- a single-reference consensus for spike configs
- an SFT export
- a spike report

Training and serving run on the DGX Spark over SSH, in Docker with the GPU.

## Technical Context

- **Orchestration**: the Mac, with `uv run pilot --config configs/spike-v1.yaml ...`. Data lives in `data/spike/`, which is gitignored.
- **Teacher**: Ollama on the Spark (`http://10.123.47.52:11434`), model `qwen3.6:35b`, with thinking off and schema-constrained output.
- **Reference**: `claude -p` on the subscription, labeling the evaluation chunks only.
- **Base model**: `Qwen/Qwen3-4B-Instruct-2507`.
- **Training**: Ludwig LLM fine-tuning (LoRA) in an NVIDIA PyTorch container on the Spark. The fallback is Hugging Face TRL plus PEFT, used only if Ludwig fails, and recorded as a finding.
- **Serving for evaluation**: `vllm/vllm-openai` on the Spark, with the base model plus the LoRA adapter (`--enable-lora`) and structured output. Both models are labeled through the new `openai_compat` backend.
- **Scoring**: the existing harness. The consensus is built from the single Claude run (`spike: true`), so every item counts as consensus.
- **Budget**: €0.

## Constitution Check (v1.2.0)

| Rule | Status |
|------|--------|
| Technical Spikes | ✅ Declared as a spike, with bounds (≤ 250 training and ≤ 40 evaluation chunks) and a budget of €0. Results labeled "spike". |
| I / II | ✅ Same prompt. Items without a verbatim quote are dropped from the training data. |
| III | ✅ Claude is the reference only, and the teacher is local. The frozen-benchmark requirement is waived (spike exemption). |
| V | ✅ Throughput is labeled as development hardware (Spark). |
| VI | ✅ `permitted_uses` is enforced in autochunk. Redaction is applied. Nothing is released. |
| VIII | ✅ Ludwig is primary. A fallback is documented in Complexity Tracking if it is used. |
| X | ✅ Extraction only. |

## Additions to the code base

```text
configs/spike-v1.yaml                 # spike config: data -> data/spike, spike: true, models
configs/models.yaml                   # + teacher-qwen3.6, spike-base, spike-tuned (openai_compat)
src/jtbd_pilot/corpus/autochunk.py    # paragraph windows from snapshots, train/main split by permitted_uses
src/jtbd_pilot/labeling/openai_compat.py  # vLLM / any OpenAI-compatible server, no cost
src/jtbd_pilot/spike.py               # SFT export, spike report
spike/train_ludwig.yaml, spike/train.sh, spike/serve.sh   # run on the Spark (not used, see Complexity Tracking)
spike/train_mlx.yaml                  # MLX LoRA on the MacBook (used)
```

## Complexity Tracking

| Deviation | Why | Simpler alternative rejected because |
|-----------|-----|--------------------------------------|
| Training with MLX (`mlx_lm.lora`, spike/train_mlx.yaml) on the MacBook (M3 Pro, 36 GB) instead of Ludwig on the Spark (Principle VIII) | The first Ludwig run crashed (Qwen has no BOS token; patched). The second loaded the model in fp32 without gradient checkpointing, filled the Spark's shared 119 GB and hung the machine for about 5 hours (3 of 552 steps). The Spark is shared; it is not used again for training this weekend. | Ludwig on Apple silicon (MPS) would again load fp32 weights, which does not fit 36 GB with ~5.5k-token examples. The TRL fallback also needs the Spark. |
| Base and tuned model are the 4-bit MLX conversion `mlx-community/Qwen3-4B-Instruct-2507-4bit` (QLoRA) | Fits and trains on the MacBook; both models use the same file, so the comparison stays fair. | bf16 would take 2-3 times longer and load the laptop fully. |
| `mlx_lm.server` does not enforce the JSON schema (`structured_output: post_validation`) | vLLM with guided decoding is not available on the Mac. Both spike models are affected equally; schema validity is itself a measured result. | - |
| Attempt 2 trains with a custom MLX script (spike/train_mlx.py: token-sum loss, ChatML without think block) and picks the checkpoint by generation on the validation examples (spike/select_checkpoint.py); SFT export repairs near-miss teacher quotes | Attempt 1 collapsed to "nothing relevant" on all 35 evaluation chunks (per-example loss mean with batch 1; see findings) | `mlx_lm.lora` has no option for the loss normalization or the chat template. |
| No throughput measurement for the spike models | The MacBook is not the target hardware (Resources & Cost Discipline). | - |

Fixes kept for a later Spark run: spike/train.sh unloads Ollama models, runs a memory watchdog (kills the container below 16 GB available) and spike/train_ludwig.yaml enables gradient checkpointing and mixed precision.
