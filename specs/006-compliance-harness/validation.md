# Validation: Compliance harness

## Baseline (2026-10-08, before any 006 code)

- `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --offline pytest -q`: 363 passed, 1 skipped, 1 deselected in 119.65 s (wall 122 s).
- `uv run zoo validate --all`: ok; sandbox-pipeline-tiny 0.1.0/0.2.0 and scout-large 0.1.0/0.1.1 published, skipped.

## US1 (2026-10-08)

- `zoo compliance recipients --runs data/runs --runs data/span-train-v1/runs`: 14 routes from 10,798 calls; no text or chunk ids in `compliance/recipients.yaml`; every route mapped to a record in `compliance/providers.yaml`.
- `zoo compliance bootstrap-sources … --benchmark pilot-v2`: 178 source records (87 training origins of scout-large 0.1.x, 91 benchmark origins of pilot-v2; classes: parliamentary-records 72, research-interviews 42, forum-review 39, tdm-documents 23, open-papers 2). All 87 training records have creators, licence, licence URL and retention; open values are on benchmark-only records.
- `zoo compliance check --stage meta`: ok.
- No source of pilot-v2 was fetched through a platform API (no Reddit sources in the benchmark); forum texts were fetched from the web and fall under the terms-of-service rule D6 (task T022).

## US3 (2026-10-08)

- **Art. 9 lexicon count** (`zoo compliance art9-scan`, counts only; an upper bound, terms match general mentions too):
  - training, parliamentary records: 124 of 730 chunks flagged, mostly "disability" (66) and "wheelchair" (64): accessibility topics in transport committee hearings;
  - training, research interviews: 7 of 354;
  - training, open papers: 0 of 16;
  - benchmark: 9 of 180 (main), 0 of 30 (holdout).
- **Redaction recall** on the synthetic set (300 items, `zoo compliance redaction-recall`): the jtbd pattern redaction used for 0.1.x catches 0.52 (not addresses, IBANs, licence plates; phones 0.74); the compliance scan catches 1.0; combined 1.0. Caveat: the set was written together with the scan patterns, so 1.0 overstates real-world recall.
- **Re-scan of the stored texts** with the compliance PII scan: training 1,100 chunks, 1 hit (an ISSN, false positive; pattern fixed); benchmark 180 chunks, 1 hit (business address of an organisation, not personal). The local model review used for 0.1.x removed the identifiers the patterns missed.
- **Release record 0.1.2**: same files and metric values as 0.1.1. Compliance record, AI Act record and training data summary rendered. Publication scan: 8 files, longest overlap with non-quotable sources 0 words, 0 PII hits.
- `zoo check scout-large 0.1.2 --offline`: every rule passes except C-S1 (owner sign-off missing); rules 5 and 12 need the Hub.
- Card preview: `reports/scout-large/model-card-preview-0.1.2.md`. Its privacy section states what was and was not checked for the 0.1.x data, instead of the generic text.

## Final validation (2026-10-08)

- Default test suite: 474 passed, 1 skipped, 1 deselected in 108 s (baseline 363 passed in 120 s); plan goal under 4 minutes met.
- `zoo validate --all`: ok, including the compliance register and gate rule 16 for scout-large 0.1.2.
- `zoo compliance check --ci`: meta, notices, drift, licence (REUSE), repository (hygiene, personal data scan, gitleaks) pass in 2 s.
- `zoo check scout-large 0.1.2 --offline`: every offline rule passes, including rule 16 after the owner's sign-off; rules 5 and 12 run in `release-verify` with Hub access.
- `zoo history-check`: no data files, model files or secrets in any commit.
- Seeded violations: every check id of contracts/checks.md has a failing test in tests/compliance (or tests/release/test_rule16.py) and the clean fixtures pass (SC-003).

## Owner decisions taken on 2026-10-08

Recorded in compliance/decisions.yaml: D-routing-scc (hosted routes with DPA and SCCs), D-interviews-0.1.x, D-accessibility-0.1.x, D-benchmark-optouts; scout-large 0.1.2 signed off. The owner confirmed that the Claude consumer training setting was off during the reference labeling (item 2); route claude-consumer-cli records `training_on_inputs: false`.

## Owner decision items

Collected for the owner (AskUserQuestion before the 0.1.2 sign-off, T047). Nothing below changes a published file.

1. **No hosted route meets the allow rule of D-routing.** None of OpenAI, Anthropic, OpenRouter, DeepInfra or Wafer is listed under the EU-US Data Privacy Framework (DPF list checked 2026-10-08); they rely on standard contractual clauses. Options: (a) keep D-routing as is, hosted labeling is blocked and labeling runs locally only; (b) widen the rule to "EU, DPF, or a DPA with standard contractual clauses plus zero data retention", which DeepInfra (no DPA by default) and OpenAI via OpenRouter (30-day retention) still would not meet without changes.
2. **Claude consumer training setting.** Since 2025-10-08 the consumer terms let Anthropic train on chats and Claude Code sessions unless the user opts out (retention 5 years if on, 30 days if off). Whether the setting was off during the reference labeling on 2026-10-06 is unknown; the owner can check it in the Claude privacy settings. The answer goes into `claude-consumer-cli.training_on_inputs`.
3. **Research interviews without a consent or ethics statement.** The 42 Zenodo interview records (training sources of scout-large 0.1.x) state that the transcripts are anonymised, but none states the consent or ethics basis. Options: keep with the publisher's anonymisation as the basis and record it; ask the dataset authors; or plan 0.2 without them.
4. **AI crawler opt-out at motor-talk.de.** Its robots.txt disallows GPTBot and ChatGPT-User today; 11 benchmark texts of pilot-v2 come from there (no licence, §44b basis). Under D6 this counts as an opt-out. The frozen benchmark is not edited; options: delete the snapshots and accept that pilot-v2 can no longer be rebuilt from raw text, or keep them until the benchmark is retired and replace them in the next benchmark version.
5. **403 on robots.txt** at data.oireachtas.ie (6 training sources, CC BY 4.0 via the Oireachtas Open Data PSI licence) and forum.cyclinguk.org (5 benchmark texts). Most likely bot protection against the new crawler user agent rather than an opt-out. For Oireachtas the licence grants the use; proposal: record "licence, no reliance on §44b". For Cycling UK (no licence): treat like item 4.
6. **TDM reservation at Elsevier** (doi.org links of 8 papers, 1 training source, 7 benchmark): the publisher sends `tdm-reservation: 1`, but the articles are CC BY 4.0, which grants the use regardless of the TDM exception. Proposal: record "licence, no reliance on §44b".
7. **One benchmark source unreachable** for the signal check (mobilitaet-in-deutschland.de); retry later.
8. **Accessibility content in the 0.1.x training data.** Decision D12 excludes special categories by default, but the 0.1.x training texts were collected before the filter existed: 124 parliamentary chunks mention disability or wheelchair access, mostly as policy topics, sometimes as witnesses describing their own situation. Options: (a) keep for 0.1.x with the rationale "public parliamentary evidence on accessibility, given by witnesses for publication" and decide per class for future data; (b) plan a 0.2 retraining without flagged chunks.
9. **Benchmark-only gaps**: 10 records without creators (tdm-documents) and 9 without a licence URL; they are not redistributed or quoted. Proposal: accept as `unknown` with a waiver until the next review.
