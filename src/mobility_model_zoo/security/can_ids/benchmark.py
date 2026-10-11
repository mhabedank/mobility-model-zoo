"""Benchmark can-ids-v1: freeze, manifest and capture checks (feature 007, research R1, R2, R6).

The benchmark is a manifest in git (capture names, splits, vehicles, attack families, counts,
content hashes, dataset versions) over data that stays in $MMZ_DATA. It is frozen at first use and
never changes; a change makes a new version (constitution IX).

Roles:

- can-train-and-test v1, per set: `train_01` captures are training data, except the
  highest-numbered capture of each attack type, which is validation data (thresholds, alarm rule,
  hyperparameters). `test_01`..`test_04` are test data.
- ROAD: attack runs ending in `_2` (also `_2_masquerade`) and every fourth ambient capture by
  CRC32 of its file name are test data; the rest is training data. Masquerade and accelerator
  captures are out of scope for this benchmark (reported separately).

Duplicates: two captures with the same content hash are a conflict when they carry different
vehicle labels, or when one is training/validation and the other test data of the same set. A
conflict stops the freeze until `resolutions.yaml` records what to do and why.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import zlib
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from mobility_model_zoo.security.can_ids import frames as fmt
from mobility_model_zoo.security.can_ids.metrics import attack_episodes

BENCHMARK = "can-ids-v1"
PROTOCOL = {
    "episode_gap_s": 1.0,
    "grace_s": 1.0,
    "budgets_per_hour": [1, 10],
    "benign_keep": 0.1,
    "seed": 0,
    "recall_at_frame_fpr": 0.001,
    "validation": "highest-numbered capture per attack type in train_01",
    "can_train_and_test_tests": [
        "test_01_known_vehicle_known_attack",
        "test_02_unknown_vehicle_known_attack",
        "test_03_known_vehicle_unknown_attack",
        "test_04_unknown_vehicle_unknown_attack",
    ],
    "road_test": "attack runs ending in _2 (also _2_masquerade); every 4th ambient capture by CRC32",
}
HASH_COLUMNS = ["ts_us", "can_id", "dlc", *fmt.PAYLOAD, "label"]


class UnresolvedDuplicates(Exception):
    def __init__(self, groups: list[dict]):
        self.groups = groups
        lines = [f"{g['sha256'][:12]}: {', '.join(g['captures'])}" for g in groups]
        super().__init__("duplicate captures with conflicting labels:\n  " + "\n  ".join(lines))


class FrozenChanged(Exception):
    """The benchmark is frozen and its content would change: make a new version."""


class CaptureChanged(Exception):
    """A capture in the data cache differs from the frozen manifest."""


# ---- loading --------------------------------------------------------------------------------


def _attack_type(stem: str) -> str:
    return re.sub(r"-\d+$", "", stem)


def _road_family(stem: str) -> str:
    if "masquerade" in stem:
        return "masquerade"
    if "accelerator" in stem:
        return "accelerator"
    if "fuzzing" in stem:
        return "fuzzing"
    return "fabrication"


def _ctt_captures(root: Path) -> Iterator[tuple[dict, pd.DataFrame]]:
    stems: dict[tuple[str, str], list[str]] = defaultdict(list)
    for df in fmt.from_can_train_and_test(root):
        set_name, split, stem = df["capture"].iat[0].split("/")
        stems[(set_name, split)].append(stem)
        yield (
            {
                "dataset": "can-train-and-test",
                "set": set_name,
                "split": split,
                "stem": stem,
                "vehicle": df["vehicle"].iat[0],
                "attack_family": _attack_type(stem),
            },
            df,
        )


def _road_captures(root: Path) -> Iterator[tuple[dict, pd.DataFrame]]:
    for df in fmt.from_road(root):
        kind, name = df["capture"].iat[0].split("/", 1)
        stem = Path(name).stem
        family = "benign" if kind == "ambient" else _road_family(stem)
        yield (
            {
                "dataset": "road",
                "set": "road",
                "split": kind,
                "stem": stem,
                "file": name,
                "vehicle": "road-vehicle",
                "attack_family": family,
            },
            df,
        )


def capture_hash(df: pd.DataFrame) -> str:
    """SHA-256 of the frame table in the common format (independent of the file format)."""
    h = hashlib.sha256()
    for col in HASH_COLUMNS:
        h.update(col.encode())
        h.update(np.ascontiguousarray(df[col].to_numpy()).tobytes())
    return h.hexdigest()


def _roles(entries: list[dict]) -> None:
    """Assign train / validation / test / out_of_scope (research R1, R6)."""
    last: dict[tuple[str, str], int] = {}
    for e in entries:
        if e["dataset"] == "can-train-and-test" and e["split"] == "train_01":
            m = re.search(r"-(\d+)$", e["stem"])
            n = int(m.group(1)) if m else 0
            key = (e["set"], e["attack_family"])
            last[key] = max(last.get(key, -1), n)
    for e in entries:
        if e["dataset"] == "can-train-and-test":
            if e["split"] == "train_01":
                m = re.search(r"-(\d+)$", e["stem"])
                n = int(m.group(1)) if m else 0
                e["role"] = "validation" if last[(e["set"], e["attack_family"])] == n else "train"
            elif e["split"] in PROTOCOL["can_train_and_test_tests"]:
                e["role"] = "test"
            else:
                e["role"] = "out_of_scope"  # e.g. v1.5 suppression and masquerade splits
        elif e["attack_family"] in ("masquerade", "accelerator"):
            e["role"] = "out_of_scope"
        elif e["split"] == "ambient":
            e["role"] = "test" if zlib.crc32(e["file"].encode()) % 4 == 0 else "train"
        else:
            e["role"] = "test" if e["stem"].removesuffix("_masquerade").endswith("_2") else "train"


def scan(sources: dict[str, Path]) -> list[dict]:
    """Every capture with its labels, role, counts and hash (reads all data once)."""
    entries = []
    loaders = {"can-train-and-test": _ctt_captures, "road": _road_captures}
    for ds, root in sources.items():
        for meta, df in loaders[ds](Path(root)):
            ts = df["ts_us"].to_numpy() / 1e6
            y = df["label"].to_numpy()
            path = (
                f"{meta['set']}/{meta['split']}/{meta['stem']}"
                if ds != "road"
                else (f"{meta['split']}/{meta['stem']}")
            )
            entries.append(
                {
                    **{k: v for k, v in meta.items() if k not in ("stem", "file")},
                    "stem": meta["stem"],
                    "file": meta.get("file", ""),
                    "id": f"{ds}/{path}",
                    "frames": int(len(df)),
                    "attack_frames": int(y.sum()),
                    "episodes": len(attack_episodes(ts, y, PROTOCOL["episode_gap_s"])),
                    "duration_s": round(float(ts[-1] - ts[0]) if len(ts) > 1 else 0.0, 6),
                    "sha256": capture_hash(df),
                }
            )
    _roles(entries)
    return entries


# ---- duplicates and resolutions --------------------------------------------------------------


def conflicts(entries: list[dict]) -> list[dict]:
    """Groups of equal content whose labels disagree (vehicle, or train vs test in one set)."""
    by_hash: dict[str, list[dict]] = defaultdict(list)
    for e in entries:
        by_hash[e["sha256"]].append(e)
    out = []
    for sha, group in sorted(by_hash.items()):
        if len(group) < 2:
            continue
        vehicles = {e["vehicle"] for e in group}
        sets_roles: dict[str, set[str]] = defaultdict(set)
        for e in group:
            sets_roles[e["set"]].add("test" if e["role"] == "test" else "fit")
        leak = any(len(r) > 1 for r in sets_roles.values())
        if len(vehicles) > 1 or leak:
            out.append(
                {
                    "sha256": sha,
                    "captures": sorted(e["id"] for e in group),
                    "labels_seen": {
                        "vehicle": sorted(vehicles),
                        "split": sorted({e["split"] for e in group}),
                    },
                }
            )
    return out


def load_resolutions(path: Path | None) -> list[dict]:
    if path is None or not Path(path).exists():
        return []
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    out = []
    for r in data.get("resolutions") or []:
        if not str(r.get("reason") or "").strip():
            raise ValueError(f"resolution for {r.get('sha256')} needs a reason")
        if r.get("action") not in ("keep", "drop", "relabel"):
            raise ValueError(f"resolution for {r.get('sha256')}: action must be keep, drop or relabel")
        out.append(r)
    return out


def _apply(entries: list[dict], resolutions: list[dict]) -> None:
    by_id = {e["id"]: e for e in entries}
    for r in resolutions:
        if r["action"] == "drop":
            for cid in r.get("captures", []):
                if cid in by_id:
                    by_id[cid]["role"] = "dropped"
        elif r["action"] == "relabel":
            for cid, vehicle in (r.get("relabel") or {}).items():
                if cid in by_id:
                    by_id[cid]["vehicle"] = vehicle


# ---- freeze and verify ----------------------------------------------------------------------


def _dataset_versions(sources: dict[str, Path]) -> list[dict]:
    out = []
    for ds, root in sorted(sources.items()):
        marker = None
        for cand in (Path(root) / "SOURCE.json", Path(root).parent / "SOURCE.json"):
            if cand.exists():
                marker = json.loads(cand.read_text())
                break
        out.append(
            {
                "id": ds,
                "licence": (marker or {}).get("license"),
                "retrieved_at": (marker or {}).get("retrieved_at"),
            }
        )
    return out


def build_manifest(sources: dict[str, Path], resolutions_path: Path | None = None) -> dict[str, Any]:
    entries = scan(sources)
    resolutions = load_resolutions(resolutions_path)
    resolved = {r["sha256"] for r in resolutions}
    open_groups = [g for g in conflicts(entries) if g["sha256"] not in resolved]
    if open_groups:
        raise UnresolvedDuplicates(open_groups)
    _apply(entries, resolutions)
    keys = (
        "id",
        "dataset",
        "set",
        "split",
        "vehicle",
        "attack_family",
        "role",
        "frames",
        "attack_frames",
        "episodes",
        "duration_s",
        "sha256",
    )
    return {
        "benchmark": BENCHMARK,
        "datasets": _dataset_versions(sources),
        "protocol": PROTOCOL,
        "captures": [{k: e[k] for k in keys} for e in sorted(entries, key=lambda e: e["id"])],
        "resolutions_sha256": (
            hashlib.sha256(Path(resolutions_path).read_bytes()).hexdigest()
            if resolutions_path and Path(resolutions_path).exists()
            else None
        ),
    }


def _dump(manifest: dict) -> str:
    return json.dumps(manifest, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def freeze(
    sources: dict[str, Path], out_dir: Path, resolutions_path: Path | None = None
) -> dict[str, Any]:
    """Write `manifest.json`; identical content is a no-op, changed content is refused."""
    manifest = build_manifest(sources, resolutions_path)
    out_dir = Path(out_dir)
    path = out_dir / "manifest.json"
    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        old_body = {k: v for k, v in old.items() if k != "frozen_at"}
        if old_body != json.loads(_dump(manifest)):
            raise FrozenChanged(f"{path} is frozen; a change makes {BENCHMARK} -> a new version")
        return old
    manifest = {**manifest, "frozen_at": dt.date.today().isoformat()}
    out_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(_dump(manifest), encoding="utf-8")
    return manifest


def verify_captures(manifest: dict, sources: dict[str, Path], ids: set[str] | None = None) -> None:
    """Raise CaptureChanged if a capture's content differs from the frozen hash."""
    want = {c["id"]: c["sha256"] for c in manifest["captures"] if ids is None or c["id"] in ids}
    seen = set()
    for e in scan(sources):
        if e["id"] in want:
            seen.add(e["id"])
            if e["sha256"] != want[e["id"]]:
                raise CaptureChanged(f"{e['id']} differs from the frozen manifest")
    missing = sorted(set(want) - seen)
    if missing:
        raise CaptureChanged(f"captures missing from the data cache: {', '.join(missing[:5])}")
