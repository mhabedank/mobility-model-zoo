# Repository layout

One rule: **the top level holds only what all topics share; everything that belongs to one topic and is not package code or configuration lives in `topics/<topic>/`.** One topic is one Hugging Face collection and one folder.

```text
compliance/                      shared compliance register (controller, routes, decisions, requests, legal watch, lists)
configs/<topic>/<task>/          configuration of each task
docs/                            shared guides (adding a model, layout, compliance, edge bench)
firmware/                        microcontroller firmware: bench/ (HIL bench), components/, per-model builds
hil/                             board inventory and targets of the hardware-in-the-loop bench
scripts/                         shared scripts (HF org avatar, cloud setup, history import)
specs/NNN-feature/               feature specs, plans, tasks
src/mobility_model_zoo/          the package: release/, compliance/, datasets/, edge/, <topic>/<task>/
tests/                           tests
topics/<topic>/                  README.md, research/, tasks/, compliance/ (source classes, sources, datasets),
                                 reports/, recipes/, plus topic-specific folders
zoo/                             topics.yaml, MODELS.md, models/<name>/ (model, releases, results, examples)
```

## Where a new topic or task goes

| What | Where |
|---|---|
| Topic entry (collection) | `zoo/topics.yaml` |
| Scope, tasks, models, folder map | `topics/<topic>/README.md` |
| Research, papers, literature | `topics/<topic>/research/` |
| Task scope, reference, benchmark, metrics, budgets | `topics/<topic>/tasks/<task>.md` |
| Third-party datasets, source classes, sources | `topics/<topic>/compliance/` |
| Code | `src/mobility_model_zoo/<topic>/<task>/` (Python identifiers: `condition_monitoring`) |
| Configuration | `configs/<topic>/<task>/` |
| Reports and recipes | `topics/<topic>/reports/`, `topics/<topic>/recipes/` |
| Firmware | `firmware/<model>/` |
| Models and releases | `zoo/models/<name>/` |

`zoo validate --all` checks that every public topic has `README.md` and `compliance/datasets.yaml`. Collected data (`data/`) and build outputs are never committed.
