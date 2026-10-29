"""Table output of the data overview (contracts/cli.md `zoo data stats`)."""

from __future__ import annotations

from collections import Counter

from .rows import HistoryEvent, InventoryRow, VersionDiff

# The count that best describes a row's size, per kind.
MAIN_COUNT = ("captures", "chunks", "items", "rows", "sources", "files")


def _main_count(row: InventoryRow) -> str:
    for key in MAIN_COUNT:
        if key in row.counts:
            return f"{row.counts[key]:,} {key}"
    return f"{row.files:,} files" if row.files is not None else "-"


def _size(row: InventoryRow) -> str:
    if row.size_mb is not None:
        return f"{row.size_mb:,.1f} MB"
    if row.approx_size_mb:
        return f"~{row.approx_size_mb:,.0f} MB"
    return "-"


def _use(row: InventoryRow) -> str:
    return {"training_allowed": "training", "benchmark_only": "bench-only"}.get(
        row.permitted_use or "", "-"
    )


def _table(header: list[str], body: list[list[str]]) -> str:
    widths = [max(len(h), *(len(r[i]) for r in body)) if body else len(h) for i, h in enumerate(header)]
    lines = ["  ".join(h.ljust(w) for h, w in zip(header, widths, strict=True)).rstrip()]
    lines.append("  ".join("-" * w for w in widths))
    lines += ["  ".join(c.ljust(w) for c, w in zip(r, widths, strict=True)).rstrip() for r in body]
    return "\n".join(lines)


def stats_table(rows: list[InventoryRow], hidden: int, notes: list[str], wide: bool = False) -> str:
    header = [
        "topic",
        "kind",
        "id",
        "version",
        "status",
        "use",
        "size",
        "files",
        "main count",
        "frozen",
        "last change",
        "integrity",
    ]
    if wide:
        header += ["licence", "redistribution", "sha256", "lineage", "used by"]
    body = []
    for r in rows:
        line = [
            r.topic,
            r.kind,
            r.id,
            r.version,
            r.status,
            _use(r),
            _size(r),
            f"{r.files:,}" if r.files is not None else "-",
            _main_count(r),
            r.frozen_at or "-",
            r.last_change or "-",
            r.integrity if r.availability != "error" else "ERROR",
        ]
        if wide:
            line += [
                r.licence or "-",
                r.redistribution or "-",
                (r.sha256 or "-")[:12],
                ", ".join(f"{x['relation']} {x['target']}" for x in r.lineage) or "-",
                ", ".join(r.used_by) or "-",
            ]
        body.append(line)
    out = [_table(header, body), ""]
    kinds = Counter(r.kind for r in rows)
    out.append("totals: " + ", ".join(f"{n} {k}" for k, n in sorted(kinds.items())) or "totals: none")
    by_topic = Counter(r.topic for r in rows)
    out.append("by topic: " + ", ".join(f"{t} {n}" for t, n in sorted(by_topic.items())))
    measured = sum(r.size_mb or 0 for r in rows)
    out.append(f"measured size on this machine: {measured:,.1f} MB")
    if hidden:
        out.append(f"hidden: {hidden} rejected or broken dataset(s) (--include-rejected)")
    for r in rows:
        if r.availability == "error" or r.failed_integrity:
            out.append(f"{r.kind} {r.name}: " + "; ".join(r.notes))
    out += notes
    return "\n".join(out)


def history_table(events: list[HistoryEvent], lineage: list[str], incomplete: bool) -> str:
    body = []
    for e in events:
        change = ""
        if e.field:
            change = (
                f"{e.field}: {e.old!r} -> {e.new!r}"
                if e.event == "field-changed"
                else f"{e.field}: {e.new}"
            )
        body.append([e.date or "-", (e.commit or "-")[:12], e.subject, e.event, change[:100]])
    out = [_table(["date", "commit", "subject", "event", "change"], body)]
    if lineage:
        out += ["", "lineage: " + " -> ".join(lineage)]
    if incomplete:
        out += [
            "",
            "history incomplete (shallow clone or no git): "
            "run `git fetch --unshallow` for the full record",
        ]
    return "\n".join(out)


def diff_table(d: VersionDiff) -> str:
    out = [
        f"{d.a} -> {d.b}",
        f"sha256: {(d.hashes.get('a') or '-')[:12]} -> {(d.hashes.get('b') or '-')[:12]}",
        "",
    ]
    body = [[k, str(v["a"]), str(v["b"]), str(v.get("delta", ""))] for k, v in d.counts.items()]
    out.append(_table(["count", "a", "b", "delta"], body))
    for dim, values in d.distribution.items():
        out += ["", f"{dim}:"]
        out.append(
            _table(
                ["value", "a", "b", "delta"],
                [[k, str(v["a"]), str(v["b"]), str(v.get("delta", ""))] for k, v in values.items()],
            )
        )
    if d.protocol:
        out += ["", "changed settings:"]
        out += [f"  {k}: {v['a']!r} -> {v['b']!r}" for k, v in d.protocol.items()]
    out += ["", "members:"]
    for k, v in d.members.items():
        out.append(f"  {k}: {', '.join(v) if v else 'none'}")
    return "\n".join(out)
