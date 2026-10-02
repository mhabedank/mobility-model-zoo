# Contract: model files of `productdev-jtbd-span-xlmr`

One flat directory, uploaded by `zoo stage` and published unchanged. No `README.md` (built by the pipeline), no `build.json`, no `.jsonl`, nothing from `data/`, no pickle files.

| File | Content |
|------|---------|
| `model.safetensors` | float32 weights of the encoder and all heads in one file; head tensors are prefixed `heads.` |
| `config.json` | encoder config (`XLMRobertaConfig`) as saved by `transformers` |
| `tokenizer.json`, `tokenizer_config.json`, `special_tokens_map.json`, `sentencepiece.bpe.model` | tokenizer, as saved by `transformers` (the last file only if the tokenizer writes it) |
| `span_config.json` | see below |

## `span_config.json`

```json
{
  "output_format_version": "jtbd-span-v1",
  "model": "productdev-jtbd-span-xlmr",
  "base_encoder": {"name": "FacebookAI/xlm-roberta-large", "revision": "<commit>"},
  "unit_labels": ["O", "job", "pain", "gain"],
  "bio_labels": ["O", "B-job", "I-job", "B-pain", "I-pain", "B-gain", "I-gain"],
  "dimensions": {"actor_type": ["individual", "worker", "organization", "public_sector", "society"]},
  "windows": {"max_length": 512, "stride": 128},
  "unit_split": "(?<=[.!?;])\\s+|\\n\\s*\\n",
  "thresholds": {"unit": 0.3, "relevance": 0.5},
  "training": {"lr": 1.5e-5, "batch_size": 4, "max_epochs": 8, "best_epoch": 5, "seed": 20261002},
  "dataset": {"name": "span-train-v1", "sha256": "<frozen.json hash>", "train_chunks": 900, "val_chunks": 100},
  "validation": {"score": 0.0, "item_f1": 0.0},
  "recipe_commit": "<git commit>"
}
```

Values above are illustrative. `dimensions` contains only the attribute dimensions that passed the pilot, each with its label list; a failed dimension has no key and no head.
