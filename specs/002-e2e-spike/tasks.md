# Tasks: End-to-end spike

**Type**: technical spike. **Input**: [spec.md](spec.md), [plan.md](plan.md).

## Phase 1: Code

- [X] S001 Add split value `train` to `src/jtbd_pilot/schema.py` and to `specs/001-jtbd-extraction-pilot/contracts/chunk-record.schema.json`
- [X] S002 Implement `src/jtbd_pilot/corpus/autochunk.py` with `pilot corpus autochunk`:
  - cuts paragraph windows of 300–1500 tokens from snapshots listed in a snapshot map
  - takes training chunks only from `training_allowed` snapshots and evaluation chunks (`main`) from the other snapshots
  - uses a seed, and respects the size bounds from FR-S01
- [X] S003 Implement `src/jtbd_pilot/labeling/openai_compat.py`:
  - works with any OpenAI-compatible server, with `base_url` from the model entry
  - uses a `json_schema` response format and temperature 0
  - costs €0
- [X] S004 Ollama backend: optional `think: false` from the model entry, in `src/jtbd_pilot/labeling/ollama.py`
- [X] S005 Single-reference consensus for configs with `spike: true`, in `src/jtbd_pilot/consensus.py`. Scoring works without `agreement.json` in spike mode, in `src/jtbd_pilot/scoring.py`
- [X] S006 Implement `src/jtbd_pilot/spike.py` with `pilot spike export-sft` and `pilot spike report`. The SFT export drops items without a verbatim quote and chunks without a valid output
- [X] S007 Add tests for S002, S003 (mocked), S005 and S006 in `tests/unit/test_spike.py`
- [X] S008 Write the Spark scripts `spike/train_ludwig.yaml`, `spike/train.sh` and `spike/serve.sh`, and the spike config `configs/spike-v1.yaml`

## Phase 2: Run (ops)

- [ ] S009 Write the snapshot map `data/spike/snapshot-map.yaml` (plan id, sub-area, language, region, date). Then autochunk about 200 training and 35 evaluation chunks
- [ ] S010 Run redact, spot-check about 10 chunks, then mark-reviewed and redact-check
- [ ] S011 Run `pilot freeze` for the spike version
- [ ] S012 Label the evaluation chunks with Claude as the reference, then build the consensus (single reference) and run `freeze --benchmark`
- [ ] S013 Label the training chunks and the evaluation chunks with the teacher `qwen3.6:35b` on the Spark
- [ ] S014 Export SFT data, copy it to the Spark, and train LoRA (Ludwig, or the fallback)
- [ ] S015 Serve the base model and the adapter with vLLM, label the evaluation chunks with both, and score all three models
- [ ] S016 Write the spike report and the findings
