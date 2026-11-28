# Contract: benchmark manifest pilot-v3

`topics/productdev/benchmarks-v3/pilot-v3/manifest.json`. Keys are added as the state advances; existing keys never change, except where this contract says so.

```json
{
  "benchmark": "pilot-v3",
  "state": "criteria_frozen",
  "frozen_at": "2026-12-..Z",
  "chunks": {"<chunk_id>": {"text_sha256": "…", "language": "de", "source_class": "new-benchmark-source"}},
  "samples_sha256": "…",
  "package": {"manifest_sha256": "…", "approval_sha256": "…", "approved_by": "…", "approved_at": "…"},
  "labeler_schema_sha256": {"1": "…", "2": "…", "3": "…"},
  "instructions_sha256": {"1": "…", "2": "…", "3": "…"},
  "criteria_sha256": "…",
  "budget_sha256": "…",
  "runs": {"pilot": {"ref-qwen3.8-27b": "run-…", "ref-deepseek-v4.1-flash": "run-…"}},
  "outcomes": {"de": {"kind_kappa": "produced"}, "en": {}},
  "absent_fields": {"de": [], "en": []},
  "stopped": {"de": null, "en": null},
  "revisions": [{"at": "…", "rationale": "…", "fields": ["…"], "package_manifest_sha256": "…"}],
  "consensus_sha256": {"de": "…", "en": "…"},
  "contested_sha256": {"de": "…", "en": "…"}
}
```

## Rules

- `outcomes` values are one of `produced`, `revise`, `extend`, `underpowered`, `not_produced` or `pilot_stopped`.
- `stopped[lang]` names the keep-always field that stopped the pilot in that language, or is null.
- `revisions` has at most one entry. An entry replaces `package` and keeps the old value under `revisions[0].previous_package`.
