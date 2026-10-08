# Handling requests from data subjects and rights holders

How the owner handles objections, erasure and access requests (GDPR) and takedown or opt-out requests (copyright). The commands are part of `zoo compliance`; the register stores no names or URLs, only keyed hashes (`MMZ_SUPPRESSION_KEY` in `.env`).

## Deadlines

| Type | Legal basis | Deadline |
|---|---|---|
| Objection (`objection`) | Art. 21 GDPR | one month |
| Erasure (`erasure`) | Art. 17 GDPR | one month |
| Access (`access`) | Art. 15 GDPR | one month |
| Takedown of a work (`takedown`) | §44b UrhG, licence terms | 14 days (project policy) |
| Opt-out of a website (`opt_out`) | §44b(3) UrhG | 14 days (project policy) |

The weekly `zoo-audit` workflow fails when a request is open past its deadline (check C-M4).

## Steps

1. **Receive.** Requests arrive at the privacy address or as a "Rights request" issue on GitHub (only for requests without personal data). Answer personal requests by e-mail only.
2. **Log and suppress.**

   ```bash
   uv run zoo compliance request add --type objection --identifier "<URL, name or handle>" --received YYYY-MM-DD
   ```

   This writes the request with its deadline to `compliance/requests.yaml` and a keyed hash to `compliance/suppression.yaml`. Use `--suppress url` (default) for a URL, `--suppress identifier` for a name or handle, `--suppress none` for an access request.
3. **Search the stores** (local, never shared):
   - raw snapshots and texts in `data/snapshots/` (`grep -ril`);
   - chunks in `data/chunks/` and `data/span-train-v1/chunks/`;
   - labeling runs in `data/runs/` and `data/span-train-v1/runs/`;
   - published files: model cards, examples, reports (`git grep`).
4. **Act.**
   - Objection or erasure: delete the affected snapshots with `uv run zoo compliance delete --snapshot <id> --reason "request r-..."`. Chunks and labels of a frozen benchmark that contain the text are reported to the owner; a new benchmark version without them is the remedy, since frozen versions are never edited.
   - A model already published is reviewed: the models output spans of the user's input and do not store training text, so withdrawal is decided case by case and recorded as a decision.
   - Access: tell the requester which stores contain text about them, and the purposes, recipients and retention from `PRIVACY.md`.
   - Takedown or opt-out: delete the snapshots and add the domain to `compliance/lists/denylist.yaml` if the whole site opts out.
5. **Close.**

   ```bash
   uv run zoo compliance request close r-YYYY-MM-DD-NNN --action "deleted 2 snapshots; suppressed" --searched snapshots --searched chunks --searched runs --answered YYYY-MM-DD
   ```

Later fetches and training runs skip suppressed URLs and identifiers (checks C-F5 and C-T1).
