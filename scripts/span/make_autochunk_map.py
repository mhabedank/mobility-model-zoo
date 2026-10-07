"""Write data/span-train-v1/autochunk-map.yaml for the training corpus (004 T023).

Lists every stored snapshot whose permitted use is `training_allowed` and that no pilot benchmark
chunk uses directly, as `use: train`. Snapshots that share a source with the benchmark in another
way (supersession, URL, content hash) are left to `jtbd corpus autochunk --exclude-benchmark`,
which refuses them; run this script with --drop to leave such snapshots out by name.

Metadata comes from the source plan where the snapshot is listed; otherwise the language is guessed
from stop words, the region from the URL's country domain, and the sub-area from topic words.

    uv run python scripts/span/make_autochunk_map.py [--drop snap-... ...]
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOTS = ROOT / "data/snapshots"
PLAN = ROOT / "data/sources/source-plan.yaml"
OUT = ROOT / "data/span-train-v1/autochunk-map.yaml"
SUB_AREA_WORDS = {
    "public_transport_rural": ["bus", "bahn", "rail", "train", "transit", "öpnv", "nahverkehr",
                               "rural", "ländlich", "ticket", "fahrplan", "timetable"],
    "logistics_delivery": ["logistik", "logistics", "freight", "delivery", "zustell", "paket",
                           "courier", "kurier", "truck", "lkw", "trucking", "spedition"],
    "emobility_charging": ["charging", "charger", "laden", "ladesäule", "ladepunkt", "elektro",
                           "electric vehicle", "e-auto", "battery", "batterie", "wallbox"],
    "car_ownership_use": ["car", "auto", "pkw", "parking", "parken", "driver", "fahrer",
                          "insurance", "versicherung", "fuel", "kraftstoff", "maut"],
    "sharing_platforms": ["sharing", "scooter", "uber", "lyft", "ride-hail", "rideshare",
                          "platform", "plattform", "gig", "carsharing", "bikesharing"],
}
REGION_BY_TLD = {"de": ("DACH", "DE"), "at": ("DACH", "AT"), "ch": ("DACH", "CH"),
                 "uk": ("non_EU", "GB"), "ie": ("EU_other", "IE"), "gov": ("non_EU", "US"),
                 "ca": ("non_EU", "CA"), "scot": ("non_EU", "GB"), "wales": ("non_EU", "GB"),
                 "eu": ("EU_other", "XX"), "nl": ("EU_other", "NL"), "fr": ("EU_other", "FR")}


def plan_meta() -> dict[str, dict]:
    plan = yaml.safe_load(PLAN.read_text())
    meta = {}
    for kind in ("papers", "transcripts", "forum_review"):
        for e in plan.get(kind, []) or []:
            if not isinstance(e, dict):
                continue
            single = e.get("snapshot")
            snaps = e.get("snapshots") or (single if isinstance(single, list)
                                            else [single] if single else [])
            for s in snaps:
                meta[s] = e
    return meta


def benchmark_snapshots() -> set[str]:
    return {json.loads(p.read_text())["snapshot_id"] for p in (ROOT / "data/chunks").glob("ch-*.json")}


def language(text: str) -> str:
    words = re.findall(r"[a-zäöüß]+", text[:20000].lower())
    de = sum(w in {"und", "der", "die", "das", "nicht", "ist", "mit", "auch"} for w in words)
    en = sum(w in {"and", "the", "of", "not", "is", "with", "also", "to"} for w in words)
    return "de" if de > en else "en"


def sub_area(text: str) -> str:
    low = text.lower()
    scores = Counter({area: sum(low.count(w) for w in words)
                      for area, words in SUB_AREA_WORDS.items()})
    return scores.most_common(1)[0][0]


def region(url: str) -> tuple[str, str]:
    host = re.sub(r"^https?://", "", url).split("/")[0]
    if "zenodo" in host or "doi.org" in host:
        return "EU_other", "XX"
    return REGION_BY_TLD.get(host.rsplit(".", 1)[-1], ("EU_other", "XX"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--drop", nargs="*", default=[])
    args = parser.parse_args()
    plan = plan_meta()
    used = benchmark_snapshots()
    out = {}
    for source in sorted(SNAPSHOTS.glob("snap-*/source.yaml")):
        s = yaml.safe_load(source.read_text())
        sid = s["snapshot_id"]
        if s.get("permitted_uses") != "training_allowed" or sid in used or sid in args.drop:
            continue
        text = (source.parent / "text.txt").read_text(encoding="utf-8")
        e = plan.get(sid, {})
        reg, country = (e.get("region"), e.get("country")) if e.get("region") else \
            region(s["origin_url"])
        area = e.get("sub_area") if isinstance(e.get("sub_area"), str) and \
            e.get("sub_area") in SUB_AREA_WORDS else sub_area(text)
        date = str(e.get("date") or s["retrieved_at"])[:10]
        out[sid] = {"plan_id": e.get("id", "reserved"), "use": "train", "sub_area": area,
                    "language": e.get("language") or language(text), "region": reg,
                    "country": country or "XX", "date": date}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(yaml.safe_dump({"snapshots": out}, sort_keys=True, allow_unicode=True))
    print(json.dumps({"snapshots": len(out),
                      "language": Counter(v["language"] for v in out.values()),
                      "region": Counter(v["region"] for v in out.values()),
                      "sub_area": Counter(v["sub_area"] for v in out.values())}, indent=1))


if __name__ == "__main__":
    main()
