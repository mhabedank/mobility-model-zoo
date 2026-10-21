"""Model footprint on a device, from the symbol sizes of the firmware ELF (feature 021, research R7).

The budget of a model (for example 128 KB flash, 32 KB RAM for pace-cnn) concerns the model, not
the bench firmware image around it. This module reads `nm --size-sort -S` of the linked ELF and
sums (specs/021-pace-cnn-first-release/contracts/records.md, "Model footprint"):

- flash: the model's constant data (`mi_model_<id>` and every `<id>_*` array: weights, bias,
  multipliers, shifts, layer table, self-test vectors) plus the int8 engine code and constants
  used for inference (`mi_*` functions except the weight-CRC helpers, which only the bench calls);
- RAM: the model's tensor arena, its input and output buffers, and the engine's static data.

The shared bench arena (MI_ZOO_ARENA_SIZE) is not used: it is the maximum over all compiled-in
models. Values are rounded up to 0.1 KiB.
"""

from __future__ import annotations

import math
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

# Engine functions that serve the bench's weight verification (CRC), not inference.
NOT_INFERENCE = {
    "mi_crc32_update",
    "mi_crc_i8_const",
    "mi_crc_i32_const",
    "mi_weight_count",
    "mi_model_crc32",
}
CODE_TYPES = set("tTwW")
CONST_TYPES = set("rRnN")
DATA_TYPES = set("dDbBgGsSvV")

# PlatformIO toolchain of each supported target family (relative to the packages directory).
NM_TOOLS = {
    "esp32": "toolchain-xtensa-esp32/bin/xtensa-esp32-elf-nm",
    "esp8266": "toolchain-xtensa/bin/xtensa-lx106-elf-nm",
}


@dataclass(frozen=True)
class Symbol:
    name: str
    size: int
    kind: str  # nm type letter


def c_ident(model_name: str) -> str:
    """The C identifier that `edge.int8.codegen` derives from a model name."""
    from mobility_model_zoo.edge.int8.codegen import _ident

    return _ident(model_name)


def parse_nm(text: str) -> list[Symbol]:
    """Lines `ADDRESS SIZE TYPE NAME` of `nm -S`; symbols without a size are skipped."""
    out = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 4:
            _, size, kind, name = parts
            try:
                out.append(Symbol(name, int(size, 16), kind))
            except ValueError:
                continue
    return out


def nm_tool(pio_env: str | None) -> str | None:
    """The `nm` of the target's toolchain, or None if the target has no supported ELF."""
    if not pio_env:
        return None
    family = "esp8266" if pio_env.startswith("esp8266") else pio_env
    rel = NM_TOOLS.get(family)
    if rel is None:
        return None
    core = Path(os.environ.get("PLATFORMIO_CORE_DIR", Path.home() / ".platformio"))
    path = core / "packages" / rel
    return str(path) if path.exists() else shutil.which(Path(rel).name)


def kib(n_bytes: int) -> float:
    return math.ceil(n_bytes / 1024 * 10) / 10


def _is_engine(s: Symbol) -> bool:
    """An inference symbol of the int8 engine: `mi_*`, but not the bench's model table
    (`mi_zoo*`), not a model's data (`mi_model_<id>` objects) and not a CRC helper."""
    if not s.name.startswith("mi_") or s.name.startswith("mi_zoo") or s.name in NOT_INFERENCE:
        return False
    return s.kind in CODE_TYPES or not s.name.startswith("mi_model_")


def model_footprint(
    symbols: list[Symbol], model_name: str, arena: int, in_size: int, out_size: int
) -> dict:
    """Flash and RAM of one model from the ELF symbols (bytes and KiB, with the parts)."""
    ident = c_ident(model_name)
    model = [s for s in symbols if s.name == f"mi_model_{ident}" or s.name.startswith(f"{ident}_")]
    if not any(s.name == f"mi_model_{ident}" for s in model):
        raise ValueError(f"mi_model_{ident} is not in the firmware ELF")
    engine = [s for s in symbols if _is_engine(s)]
    model_const = sum(s.size for s in model)
    engine_code = sum(s.size for s in engine if s.kind in CODE_TYPES | CONST_TYPES)
    engine_data = sum(s.size for s in engine if s.kind in DATA_TYPES)
    flash = model_const + engine_code
    ram = arena + in_size + out_size + engine_data
    return {
        "flash_bytes": flash,
        "ram_bytes": ram,
        "flash_kb": kib(flash),
        "ram_kb": kib(ram),
        "parts": {
            "model_constant_data": model_const,
            "engine_code": engine_code,
            "arena": arena,
            "input": in_size,
            "output": out_size,
            "engine_static_data": engine_data,
        },
    }


def elf_footprint(elf: Path, pio_env: str | None, model) -> dict | None:
    """Footprint of a QModel in a built ELF, or None when the toolchain's nm is not available."""
    tool = nm_tool(pio_env)
    if tool is None or not Path(elf).exists():
        return None
    res = subprocess.run([tool, "--size-sort", "-S", str(elf)], capture_output=True, text=True)
    if res.returncode != 0:
        return None
    return model_footprint(
        parse_nm(res.stdout), model.name, model.arena_size(), model.in_size, model.out_size
    )
