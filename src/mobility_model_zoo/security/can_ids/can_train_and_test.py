"""Parse the can-train-and-test dataset (Lampe & Meng).

Source:  https://bitbucket.org/brooke-lampe/can-train-and-test
DOI:     https://doi.org/10.11583/DTU.24805533 (DTU Data, CC BY 4.0)

Each CSV has the columns ``timestamp,arbitration_id,data_field,attack``. We convert every
file into a Parquet file with typed columns:

    ts (float64, s) | can_id (uint16) | dlc (uint8) | b0..b7 (uint8, zero-padded) | label (uint8)

Download with `uv run zoo data download can-train-and-test` (Bitbucket provider, files in
$MMZ_DATA/can-train-and-test/extracted/<set>/<split>/*.csv). Parsed captures are cached as Parquet
under $MMZ_DATA/derived/can-train-and-test/.
"""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pandas as pd

SETS = ("set_01", "set_02", "set_03", "set_04")
SPLITS = (
    "train_01",
    "test_01_known_vehicle_known_attack",
    "test_02_unknown_vehicle_known_attack",
    "test_03_known_vehicle_unknown_attack",
    "test_04_unknown_vehicle_unknown_attack",
)
# Known/unknown vehicle per set, from the dataset README.
VEHICLES = {
    "set_01": {"known": "chevrolet_impala", "unknown": "chevrolet_silverado"},
    "set_02": {"known": "chevrolet_traverse", "unknown": "subaru_forester"},
    "set_03": {"known": "chevrolet_silverado", "unknown": "subaru_forester"},
    "set_04": {"known": "subaru_forester", "unknown": "chevrolet_traverse"},
}


def vehicle_of(set_name: str, split: str) -> str:
    return VEHICLES[set_name]["unknown" if "unknown_vehicle" in split else "known"]



def parse_csv(raw: bytes) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(raw), dtype={"arbitration_id": str, "data_field": str})
    data = df["data_field"].fillna("").str.strip()
    dlc = (data.str.len() // 2).clip(upper=8).astype(np.uint8)
    padded = data.str.slice(0, 16).str.ljust(16, "0")
    hexbytes = np.frombuffer(bytes.fromhex("".join(padded.tolist())), dtype=np.uint8)
    out = pd.DataFrame(
        {
            "ts": df["timestamp"].astype(np.float64),
            "can_id": df["arbitration_id"].map(lambda x: int(x, 16)).astype(np.uint16),
            "dlc": dlc,
        }
    )
    payload = hexbytes.reshape(-1, 8)
    for i in range(8):
        out[f"b{i}"] = payload[:, i]
    out["label"] = df["attack"].astype(np.uint8)
    return out



def load(data_dir: Path, set_name: str, split: str) -> dict[str, pd.DataFrame]:
    """Return {capture_name: frames} for one split, e.g. ``{"DoS-1": df, ...}``.

    Reads the CSV files of a download (or Parquet files of an older conversion) and caches parsed
    captures as Parquet in $MMZ_DATA/derived/can-train-and-test/ when pyarrow is installed.
    """
    from mobility_model_zoo.edge.paths import derived_dir

    d = Path(data_dir) / set_name / split
    if parquet := sorted(d.glob("*.parquet")):
        return {p.stem: pd.read_parquet(p) for p in parquet}
    cache = derived_dir("can-train-and-test") / set_name / split
    out = {}
    for csv in sorted(d.glob("*.csv")):
        cached = cache / f"{csv.stem}.parquet"
        if cached.exists():
            out[csv.stem] = pd.read_parquet(cached)
            continue
        df = parse_csv(csv.read_bytes())
        try:
            cache.mkdir(parents=True, exist_ok=True)
            df.to_parquet(cached, index=False)
        except ImportError:  # no pyarrow: parse again next time
            pass
        out[csv.stem] = df
    return out
