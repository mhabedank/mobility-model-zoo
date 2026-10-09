"""`edge measure MODEL.npz -b BOARD --out FILE.json`: measure one int8 model on one board.

Builds firmware that contains the model (reference models + $MMZ_EDGE_MODELS), flashes/starts the
board through the normal BoardSession, times the model with the device BENCH command and writes a
`performance` results file in the zoo format (release/schemas/results.schema.json).

Latency samples: each sample is one BENCH call with `batch` timed inferences; its value is the mean
of that call (us_total / batch). The device timer has 1 us resolution, so by default (batch=None) a
sample is a single inference unless the model runs faster than AUTO_BATCH_BELOW_US (typically the
host simulator); then the batch is chosen so that one sample takes about AUTO_BATCH_TARGET_US.
"""

from __future__ import annotations

import os
import platform
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from mobility_model_zoo.edge.int8.model import QModel

from .build import build
from .config import Board, Lab
from .lock import BoardLock
from .session import BoardSession

QEMU_MODULE = "mobility_model_zoo.edge.bench.qemu"
AUTO_BATCH_BELOW_US = 20.0
AUTO_BATCH_TARGET_US = 200.0
AUTO_BATCH_MAX = 10000


class MeasureError(RuntimeError):
    """Usage/config problem (exit code 2)."""


class ModelMissing(RuntimeError):
    """The firmware on the board does not contain the model (exit code 1)."""


@dataclass
class MeasureOptions:
    n: int = 100  # number of latency samples
    warmup: int = 3
    batch: int | None = None  # timed inferences per sample; None = automatic (see module doc)
    model_name: str | None = None  # zoo model name for the results file (default: QModel name)
    version: str | None = None
    synthetic: bool = False


def origin_of(board: Board) -> str:
    """simulator (native build), emulator (QEMU flasher command), otherwise real_board."""
    if board.target.build == "native" or board.target.transport == "process":
        return "simulator"
    if board.flash_method == "command" and QEMU_MODULE in str(board.flash_options.get("command", "")):
        return "emulator"
    return "real_board"


def hardware_of(board: Board, info: dict, origin: str) -> str:
    if origin == "simulator":
        return f"host simulator (native build, {platform.system()} {platform.machine()})"
    chip = info.get("chip") or board.target.description or board.target.name
    mhz = info.get("cpu_mhz") or 0
    clock = f", {mhz} MHz" if mhz else ""
    if origin == "emulator":
        return f"{chip}{clock} in QEMU (emulator, target {board.target.name})"
    return f"{chip}{clock} (target {board.target.name}, board {board.id})"


@contextmanager
def _edge_models_env(extra: Path | None):
    """Temporarily append `extra` to $MMZ_EDGE_MODELS for the firmware build."""
    old = os.environ.get("MMZ_EDGE_MODELS")
    if extra is not None:
        os.environ["MMZ_EDGE_MODELS"] = os.pathsep.join(filter(None, [old, str(extra.resolve())]))
    try:
        yield
    finally:
        if extra is not None:
            if old is None:
                os.environ.pop("MMZ_EDGE_MODELS", None)
            else:
                os.environ["MMZ_EDGE_MODELS"] = old


def _needs_env(model: QModel) -> bool:
    """True if the model is not yet part of the firmware model set."""
    from .reference_models import bench_models

    for m in bench_models():
        if m.name == model.name:
            if m.crc32() != model.crc32():
                raise MeasureError(
                    f"model name '{model.name}' is already used by a different bench model "
                    "- rename the model"
                )
            return False
    return True


def _sizes(model: QModel, manifest: dict) -> tuple[float, str, float, str]:
    if manifest.get("flash_used") is not None and manifest.get("ram_used") is not None:
        return (
            manifest["flash_used"] / 1024,
            "Flash used by the whole firmware image (bench app, inference engine and all bench "
            "models incl. this one), from the PlatformIO build",
            manifest["ram_used"] / 1024,
            "Static RAM used by the whole firmware image (data + bss, incl. the shared tensor "
            "arena), from the PlatformIO build",
        )
    ram = model.arena_size() + model.in_size + model.out_size
    return (
        model.param_bytes() / 1024,
        "Model footprint estimate (no firmware size report for this build): parameter bytes "
        "(int8 weights, int32 bias and multipliers, int8 shifts); excludes engine code, layer "
        "table and test vectors",
        ram / 1024,
        "Model footprint estimate (no firmware size report for this build): tensor arena plus "
        "input and output buffers",
    )


def measure(lab: Lab, board: Board, model_path: Path, opts: MeasureOptions, log=print) -> dict:
    model_path = Path(model_path)
    if not model_path.is_file():
        raise MeasureError(f"model file not found: {model_path}")
    try:
        model = QModel.load(model_path)
    except Exception as e:  # not an npz / not a QModel
        raise MeasureError(f"{model_path}: not a QModel .npz ({type(e).__name__}: {e})") from e
    if opts.n < 1 or (opts.batch is not None and opts.batch < 1) or opts.warmup < 0:
        raise MeasureError("-n and --batch must be >= 1, --warmup >= 0")
    if model.name in board.target.excluded_models:
        raise ModelMissing(f"model {model.name} is excluded on target {board.target.name}")

    extra = model_path if _needs_env(model) else None
    log(
        f"building {board.target.name} firmware"
        + (f" with {model.name} from {model_path}" if extra else f" ({model.name} is a bench model)")
    )
    with BoardLock(lab.lock_dir, f"build-{board.target.name}", timeout=1800), _edge_models_env(extra):
        fw = build(lab, board.target)

    origin = origin_of(board)
    with BoardSession(lab, board, fw, flash=True, log_dir=lab.results_dir / "manual") as s:
        info = dict(s.info)
        dev_models = {m["name"]: m for m in s.device.models()}
        dm = dev_models.get(model.name)
        if dm is None:
            raise ModelMissing(
                f"model {model.name} is not in the firmware on {board.id} "
                f"(device has: {', '.join(dev_models) or 'none'})"
            )
        if int(str(dm["crc"]), 16) != model.crc32():
            raise ModelMissing(
                f"model {model.name} on {board.id} has crc {dm['crc']}, expected {model.crc32():08x}"
            )
        r = s.device.bench(model.name, n=max(opts.warmup, 1), warmup=1, timeout=600)
        batch = opts.batch
        if batch is None:
            batch = 1
            if r["us_total"] / r["n"] < AUTO_BATCH_BELOW_US:
                r = s.device.bench(model.name, n=1000, warmup=0, timeout=600)
                per_inf = max(r["us_total"] / r["n"], AUTO_BATCH_TARGET_US / AUTO_BATCH_MAX)
                batch = int(min(max(round(AUTO_BATCH_TARGET_US / per_inf), 1), AUTO_BATCH_MAX))
        samples = []
        stable = True
        for _ in range(opts.n):
            r = s.device.bench(model.name, n=batch, warmup=0, timeout=600)
            stable &= bool(r.get("stable", True))
            samples.append(r["us_total"] / r["n"])
        if not stable:
            raise MeasureError(f"{model.name}: output changed between identical runs on {board.id}")

    arr = np.asarray(samples, dtype=np.float64)
    median = float(np.median(arr))
    p99 = float(np.percentile(arr, 99))
    flash_kb, flash_desc, ram_kb, ram_desc = _sizes(model, fw.manifest)
    hardware = hardware_of(board, info, origin)
    today = time.strftime("%Y-%m-%d")
    per = "per inference" if batch == 1 else f"per inference (each sample: mean of {batch} runs)"
    n_runs = opts.n * batch

    def metric(name, value, unit, desc, n_items=None):
        m = {
            "name": name,
            "value": value if isinstance(value, int) else round(float(value), 3),
            "unit": unit,
            "description": desc,
            "date": today,
            "hardware": hardware,
            "origin": origin,
        }
        if n_items:
            m["n_items"] = int(n_items)
        return m

    metrics = [
        metric(
            "latency_us",
            median,
            "us",
            f"Median latency {per} over {opts.n} samples ({n_runs} inferences, device BENCH timer)",
            opts.n,
        ),
        metric(
            "latency_p99_us",
            p99,
            "us",
            f"99th percentile latency {per} over {opts.n} samples (device BENCH timer)",
            opts.n,
        ),
        metric("flash_kb", flash_kb, "KiB", flash_desc),
        metric("ram_kb", ram_kb, "KiB", ram_desc),
        metric(
            "arena_bytes",
            model.arena_size(),
            "bytes",
            "Tensor arena of the model (two ping-pong buffers, QModel.arena_size)",
        ),
    ]
    return {
        "kind": "performance",
        "model": opts.model_name or model.name,
        "version": opts.version or str(model.meta.get("version", "0.0.0")),
        "synthetic": bool(opts.synthetic),
        "source_run": (
            f"edge measure {model_path.name} -b {board.id} (build {fw.build_id:08x}, "
            f"fw {info.get('fw', '?')}, {fw.manifest.get('git', '?')})"
        ),
        "metrics": metrics,
    }
