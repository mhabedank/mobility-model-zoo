"""`edge performance`: merge `edge measure` outputs into a release's performance.json (feature 021, R9).

    uv run edge performance --model pace-cnn --version 0.1.0 --reference esp32.json \\
        --extra qemu.json --extra esp8266.json --extra sim.json

The reference file (the task's reference hardware) gives the plain metric names that the budgets,
the card and gate rule 15 read (`flash_kb`, `ram_kb`, `latency_us`, ...). Every other file gives
suffixed names (`latency_us_esp32_qemu`, `latency_us_esp8266`, `latency_us_host`); the whole-image
sizes of the reference board become `flash_kb_image_<board>`. Every row keeps its `origin` and
`hardware`, so an emulator or simulator value is never presented as a hardware value. A reference
that is not a real board is refused unless `--allow-substitute` is given; the plain rows then carry
the substitute's origin.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

PLAIN = (
    "latency_us",
    "latency_mean_us",
    "latency_p99_us",
    "flash_kb",
    "ram_kb",
    "arena_bytes",
    "device_bit_exact_vectors",
)
EXTRA = ("latency_us", "latency_mean_us")


class PerformanceRefused(Exception):
    pass


def board_suffix(result: dict) -> str:
    """Suffix of a measurement file's board: `sim` -> host, `esp32-qemu` -> esp32_qemu,
    `esp8266-1` -> esp8266 (from `source_run`, '... -b BOARD ...')."""
    m = re.search(r" -b (\S+)", result.get("source_run", ""))
    board = m.group(1) if m else "unknown"
    if board == "sim" or result["metrics"][0].get("origin") == "simulator":
        return "host"
    return re.sub(r"[^a-z0-9]+", "_", re.sub(r"-\d+$", "", board.lower())).strip("_")


def merge(
    model: str,
    version: str,
    reference: dict,
    extras: list[dict],
    allow_substitute: bool = False,
) -> dict[str, Any]:
    ref_rows = {m["name"]: m for m in reference["metrics"]}
    origins = {ref_rows[n].get("origin") for n in ("flash_kb", "ram_kb", "latency_us") if n in ref_rows}
    if origins != {"real_board"} and not allow_substitute:
        found = ", ".join(map(str, sorted(map(str, origins))))
        raise PerformanceRefused(
            f"the reference measurement is not from a real board (origin {found}); "
            "measure the reference hardware or pass --allow-substitute"
        )
    rows = [dict(ref_rows[n]) for n in PLAIN if n in ref_rows]
    ref_suffix = board_suffix(reference)
    for n in ("flash_kb_image", "ram_kb_image"):
        if n in ref_rows:
            rows.append({**ref_rows[n], "name": f"{n}_{ref_suffix}"})
    seen = {r["name"] for r in rows}
    for result in extras:
        suffix = board_suffix(result)
        by_name = {m["name"]: m for m in result["metrics"]}
        for n in EXTRA:
            if n in by_name:
                name = f"{n}_{suffix}"
                if name in seen:
                    raise PerformanceRefused(f"two measurement files give {name}")
                rows.append({**by_name[n], "name": name})
                seen.add(name)
    sources = [reference.get("source_run", "")] + [e.get("source_run", "") for e in extras]
    return {
        "kind": "performance",
        "model": model,
        "version": version,
        "synthetic": bool(reference.get("synthetic", False)),
        "source_run": "; ".join(s for s in sources if s),
        "metrics": rows,
    }


def write(root: Path, merged: dict) -> Path:
    path = root / "zoo" / "models" / merged["model"] / "results" / merged["version"] / "performance.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(merged, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
