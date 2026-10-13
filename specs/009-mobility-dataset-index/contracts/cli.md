# Contract: `zoo catalog` commands and the discovery skill

New commands under `zoo catalog` (package `mobility_model_zoo.catalog`, mounted like `zoo data`).
Existing commands keep their behaviour, except the signal checker extension (R4), which only adds
blocking reasons. Exit codes follow `release/errors.py`: 0 ok, 1 check failed, 2 usage, 3 refused,
5 credentials or missing input, 6 external service.

Every command reads the entries from `--catalog PATH`, then `$MMZ_CATALOG`, then
`../mobility-model-zoo-catalog`, and exits 5 if none exists. Commands that write change only
files inside the catalog repository, and never commit; committing is left to the caller or the CI.

## Maintenance

| Command | Behaviour | FR |
|---|---|---|
| `zoo catalog init PATH` | Creates the catalog repository layout ([data-model.md](../data-model.md)) with `catalog.yaml`, an empty `entries/`, and the CI workflow that runs `zoo catalog validate`. Refuses a non-empty directory (exit 3) and any path inside the public repository (exit 3). | FR-032 |
| `zoo catalog validate [--zoo-root PATH]` | Offline checks K1, K2, K3, K8 and K9 on every entry; runs without a zoo checkout (package-data lists). Prints one line per finding (`FAIL <id> K1 languages[0].code: 'esp' is not in vocab languages v1`). Exit 1 on any `fail`. This is the CI gate of the catalog repository. | FR-005, FR-006, FR-017, FR-019 |
| `zoo catalog check [--id ID…] [--status S] [--stale DAYS] [--offline]` | Runs all checks (K1–K8) on the selection and writes the results into the entries. It also applies the transitions of the state machine: candidate → verified, verified → cleared, cleared → verified when something changed, and retired. Default selection: every candidate, plus every cleared entry last verified more than 180 days ago (FR-020, SC-009). The network checks throttle per host (R12). Exit 6 only when the checks could not run at all (no network); individual unreachable URLs are recorded as findings. | FR-017, FR-018, FR-020 |
| `zoo catalog flags [--flag F]` | Lists entries with flags: id, flag, reason, and the rule that raised it. These are the owner's decision queue. | FR-018 |
| `zoo catalog decide ID --use training_allowed\|benchmark_only\|not_usable --reason TEXT` | Records an owner decision for a flagged entry (rule U6): sets `usage` with rule `U0` (owner) and removes `owner_decision_needed`. | FR-018 |
| `zoo catalog withdraw ID --request REQ` | Requires `REQ` in `compliance/requests.yaml` (exit 3 otherwise). Sets the entry to `withdrawn` and adds its canonical address hashes to `compliance/suppression.yaml` in the public repository (the only write outside the catalog). | FR-021 |
| `zoo catalog retire ID --reason TEXT`, `zoo catalog reject ID --reason TEXT` | Manual end states. | FR-016 |
| `zoo catalog link ID REGISTER:TOPIC:RECORD` | Checks that the record exists in `topics/<topic>/compliance/<register>.yaml`, then sets `fetched` and the status. | FR-029 |

## Discovery

| Command | Behaviour | FR |
|---|---|---|
| `zoo catalog harvest NAME --lang L… [--area A…] [--subdomain S…] [--modality M…] [--limit N] [--run-id ID]` | Runs a harvester (`data-europa`, `mobility-database`, `openalex`, `zenodo`, `huggingface` in the first set; `wikimedia-commons` and `podcast-index` for the scale-up). `--modality` limits a run to some of the modalities the harvester yields (Wikimedia Commons: image, graphic, video, audio); a run limited to modalities it does not yield finds nothing. It writes `runs/<date>-<slug>.yaml` (header) and `.jsonl` (candidates), then calls `ingest`. A missing API key is exit 5 and names the environment variable. | FR-022, FR-024 |
| `zoo catalog ingest RUN.jsonl --run RUN.yaml` | Validates each line against `candidate.schema.json`, deduplicates (R7: merges on an exact key, flags on a fuzzy one), assigns ids, writes entries with status `candidate`, runs the offline checks, and writes the outcome counts per language × modality cell into the run header. Lines that fail are listed in the run header with a reason; they never become entries. Exit 1 if more than 20% of the lines fail, which points to a broken harvester or agent. | FR-019, FR-022 |
| `zoo catalog new --from FILE.yaml` | Adds one entry by hand (`provenance.added_by: owner`), through the same path as `ingest`. | FR-022 |

### Discovery skill (`.claude/skills/catalog-discover/SKILL.md`, public repository)

Input: one scope (languages, areas, subdomains, modalities) and the catalog path. The agent:
1. Reads the vocabularies and the existing entries of that scope, so it does not propose known
   resources again. This includes rejected, retired and withdrawn entries.
2. Searches the web for publishers and archives in that scope. It favours kinds of source with
   open licences (parliaments, ministries, statistics offices, research institutions).
3. Writes the candidates as JSON lines that follow `candidate.schema.json`. Every licence
   statement needs an `evidence` URL, and a fact that is not known is written as an explicit
   unknown value. `description` is written in the agent's own words (at most 600 characters), never
   copied from the page.
4. Writes the run header with the agent tool, the model id and the scope, and runs
   `zoo catalog ingest`.
5. Never downloads resource content. It reads only landing pages, licence pages and catalogue
   pages, and stops on a CAPTCHA or a login.

## Use

| Command | Behaviour | FR |
|---|---|---|
| `zoo catalog query [--lang L…] [--area A…] [--modality M…] [--genre G…] [--kind K…] [--topic T…] [--subdomain S…] [--status S…] [--use U…] [--transcripts yes\|no] [--origin O…] [--min-quality N] [--format table\|json\|ids]` | Filters by AND across options and OR within one option. A language filter matches entries that list the language, or that list it only as a transcript language when `--include-transcripts` is set. | FR-025 |
| `zoo catalog report coverage [--out DIR]` | Writes `reports/<date>-coverage.{md,json}` and prints the gap list. | FR-026 |
| `zoo catalog report languages [--out DIR]` | Writes `reports/<date>-languages.{md,json}` (R9). | FR-027 |
| `zoo catalog audit [--sample N] [--dup-sample M] [--seed S] [--model ID]` | The independent re-check of the usage decision on N entries (default 30) and the duplicate audit on M entries (default 50) (R8). Exit 1 if agreement is below 90% or any cleared entry is classified `not_usable` (SC-005). | SC-005, SC-008 |
| `zoo catalog fetchlist NAME [query options]` | Writes `fetch-lists/<date>-<name>.yaml` following `fetch-list.schema.json`. Only `cleared` entries become items; every other selected entry goes to `refused` with its status and reason. Exit 3 if no item remains. | FR-018, FR-028 |
| `zoo catalog pilot evaluate pilot/pilot-v1.yaml` | Computes the pilot criteria per language from the runs named in the pilot file and prints pass or fail per language and overall. It refuses (exit 3) if the pilot file was changed after its first run without a `criteria_changes` entry (constitution IV). | Spec: Riskiest Assumption |

## Library interface (used by the later download feature)

- `catalog.load(path) -> Catalog`: the entries, indexed by id, with the index version (commit
  and SHA-256).
- `catalog.fetchlist.read(path) -> FetchList`: reads a fetch list and validates it against its
  schema.
- `catalog.require_cleared(entry_id)`: raises `UsageRefused` (exit 3) unless the entry is
  `cleared` and has been verified within the last 180 days.
