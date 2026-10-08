# Validation: Compliance harness

## Baseline (2026-10-08, before any 006 code)

- `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --offline pytest -q`: 363 passed, 1 skipped, 1 deselected in 119.65 s (wall 122 s).
- `uv run zoo validate --all`: ok; sandbox-pipeline-tiny 0.1.0/0.2.0 and scout-large 0.1.0/0.1.1 published, skipped.

## US1 (2026-10-08)

- `zoo compliance recipients --runs data/runs --runs data/span-train-v1/runs`: 14 routes from 10,798 calls; no text or chunk ids in `compliance/recipients.yaml`; every route mapped to a record in `compliance/providers.yaml`.
- `zoo compliance bootstrap-sources … --benchmark pilot-v2`: 178 source records (87 training origins of scout-large 0.1.x, 91 benchmark origins of pilot-v2; classes: parliamentary-records 72, research-interviews 42, forum-review 39, tdm-documents 23, open-papers 2). All 87 training records have creators, licence, licence URL and retention; open values are on benchmark-only records.
- `zoo compliance check --stage meta`: ok.
- No source of pilot-v2 was fetched through a platform API (no Reddit sources in the benchmark); forum texts were fetched from the web and fall under the terms-of-service rule D6 (task T022).

## Owner decision items

Collected for the owner (AskUserQuestion before the 0.1.2 sign-off, T047). Nothing below changes a published file.

1. **No hosted route meets the allow rule of D-routing.** None of OpenAI, Anthropic, OpenRouter, DeepInfra or Wafer is listed under the EU-US Data Privacy Framework (DPF list checked 2026-10-08); they rely on standard contractual clauses. Options: (a) keep D-routing as is, hosted labeling is blocked and labeling runs locally only; (b) widen the rule to "EU, DPF, or a DPA with standard contractual clauses plus zero data retention", which DeepInfra (no DPA by default) and OpenAI via OpenRouter (30-day retention) still would not meet without changes.
2. **Claude consumer training setting.** Since 2025-10-08 the consumer terms let Anthropic train on chats and Claude Code sessions unless the user opts out (retention 5 years if on, 30 days if off). Whether the setting was off during the reference labeling on 2026-10-06 is unknown; the owner can check it in the Claude privacy settings. The answer goes into `claude-consumer-cli.training_on_inputs`.
3. **Research interviews without a consent or ethics statement.** The 42 Zenodo interview records (training sources of scout-large 0.1.x) state that the transcripts are anonymised, but none states the consent or ethics basis. Options: keep with the publisher's anonymisation as the basis and record it; ask the dataset authors; or plan 0.2 without them.
4. **AI crawler opt-out at motor-talk.de.** Its robots.txt disallows GPTBot and ChatGPT-User today; 11 benchmark texts of pilot-v2 come from there (no licence, §44b basis). Under D6 this counts as an opt-out. The frozen benchmark is not edited; options: delete the snapshots and accept that pilot-v2 can no longer be rebuilt from raw text, or keep them until the benchmark is retired and replace them in the next benchmark version.
5. **403 on robots.txt** at data.oireachtas.ie (6 training sources, CC BY 4.0 via the Oireachtas Open Data PSI licence) and forum.cyclinguk.org (5 benchmark texts). Most likely bot protection against the new crawler user agent rather than an opt-out. For Oireachtas the licence grants the use; proposal: record "licence, no reliance on §44b". For Cycling UK (no licence): treat like item 4.
6. **TDM reservation at Elsevier** (doi.org links of 8 papers, 1 training source, 7 benchmark): the publisher sends `tdm-reservation: 1`, but the articles are CC BY 4.0, which grants the use regardless of the TDM exception. Proposal: record "licence, no reliance on §44b".
7. **One benchmark source unreachable** for the signal check (mobilitaet-in-deutschland.de); retry later.
8. **Benchmark-only gaps**: 10 records without creators (tdm-documents) and 9 without a licence URL; they are not redistributed or quoted. Proposal: accept as `unknown` with a waiver until the next review.
