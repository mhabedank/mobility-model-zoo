# Contract: pace report (`zoo/roadmap/reviews/<quarter>.md`)

Definitions are in [research.md](../research.md) R6. The report is Markdown with these sections, in this order. Everything except "Re-planning" is generated and replaced on every `--write`.

```markdown
# Pace review <quarter label>

Generated <date> from zoo/roadmap/roadmap.yaml and the release records.

## Summary

| | This quarter |
|---|---|
| Releases published | <n> |
| Roadmap entries delivered | <n> (early <n>, on time <n>, late <n>) |
| Delivery rate | <delivered of due> of <due> entries due this quarter |
| Moved | <n> |
| Dropped | <n> |
| Unplanned releases | <n> |

## Delivered

| Entry | Kind | First planned | Delivered | Release | Timing | Slip |
|---|---|---|---|---|---|---|
| <id> | <kind> | <label> | <date> | <model> <version> | early / on time / late | <days> d, <quarters> q |

## Due and not delivered

| Entry | First planned | Now in | Moves (date: reason) |
|---|---|---|---|

## Moved this quarter

| Entry | From | To | Date | Reason |
|---|---|---|---|---|

## Dropped this quarter

| Entry | First planned | Date | Reason |
|---|---|---|---|

## Unplanned releases

| Release | Published | Note |
|---|---|---|

## Trend

| Quarter | Releases | Delivered | Due | Delivery rate | Late |
|---|---|---|---|---|---|

## Re-planning

<hand-written: how the next horizons were filled from the measured pace; at least one sentence (RM7)>
```

Rules:

- Empty tables are replaced by the line "None."
- "Due" counts entries whose first planned horizon ends in the quarter; a two-quarter horizon is due in its second quarter.
- "Slip" is empty for early and on-time entries.
- "Unplanned releases" lists every non-sandbox release published in the quarter that is not the delivering release of an entry; patch releases of a delivered entry are noted as "patch".
- The trend table lists every quarter from `since` up to this one, reading earlier reviews' numbers by recomputing them from the files, not by copying from the old review files.
