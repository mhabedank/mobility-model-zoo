"""Regenerate the synthetic fixture catalogs tests/fixtures/catalog and tests/fixtures/catalog-invalid.

Run `uv run python tests/catalog/make_fixtures.py` after changing the entry schema or the rules;
the stored `usage` is computed with the current rules so that check K8 passes. All addresses use
example.org or .test domains; no entry describes a real resource.
"""

from __future__ import annotations

import copy
import shutil
from pathlib import Path

import yaml

from mobility_model_zoo.catalog import rules
from mobility_model_zoo.catalog.model import dump_yaml, entry_path, licence_allowlist, ordered

HERE = Path(__file__).resolve().parents[1] / "fixtures"
VALID = HERE / "catalog"
INVALID = HERE / "catalog-invalid"
DAY = "2026-10-11"
SIGNALS_OK = {
    "robots": "allow",
    "tdmrep": "absent",
    "x_robots": "absent",
    "meta_noai": "allow",
    "ai_txt": "absent",
    "content_signal": "absent",
    "content_usage": "absent",
    "checked_at": DAY,
}
PASSED = [
    {"check": c, "result": "pass", "at": DAY}
    for c in ("K1", "K2", "K3", "K4", "K5", "K6", "K7", "K8", "K9")
]


def base(
    eid,
    *,
    title,
    langs,
    area,
    publisher,
    kind,
    modality,
    genre,
    licence,
    subdomains,
    status="verified",
    access=None,
    level="collection",
    parent=None,
    **extra,
):
    lic_id = licence
    entry = {
        "id": eid,
        "schema_version": 1,
        "level": level,
        "parent": parent,
        "title": {"original": title[0], "en": title[1]},
        "description": extra.pop("description", f"Synthetic fixture: {title[1]}."),
        "languages": [{"code": c, "origin": o} for c, o in langs],
        "origin_area": area,
        "publisher": {"name": publisher, "kind": kind},
        "landing_url": f"https://example.org/{eid}",
        "resource_type": {"modality": modality, "genre": genre},
        "topics": extra.pop("topics", ["productdev"]),
        "subdomains": subdomains,
        "licence": {
            "id": lic_id,
            "url": None if lic_id in ("unknown", "mixed") else f"https://licences.test/{lic_id}",
            "evidence_url": None if lic_id == "unknown" else f"https://example.org/{eid}/licence",
            "attribution_required": "yes" if lic_id.startswith("CC-BY") else "unknown",
            "attribution_text": None,
            "commercial_use": "no"
            if "NC" in lic_id
            else ("yes" if lic_id.startswith(("CC-BY", "CC0")) else "unknown"),
            "share_alike": None,
            "derivatives": "yes"
            if lic_id.startswith(("CC-BY", "CC0")) and "ND" not in lic_id
            else "unknown",
        },
        "signals": dict(SIGNALS_OK),
        "personal_data": extra.pop("personal_data", {"expectation": "none", "categories": []}),
        "access": access
        or [
            {
                "method": "direct_download",
                "url": f"https://example.org/{eid}/data",
                "download_url": f"https://example.org/{eid}/data.zip",
                "auth": "none",
                "cost": "free",
                "formats": ["application/zip"],
                "size_bytes_est": 1000,
            }
        ],
        "quality": {
            "score": extra.pop("score", 3),
            "rationale": "Synthetic fixture with a fixed score.",
        },
        "provenance": {
            "added_by": "owner",
            "added_at": DAY,
            "method": "search",
            "evidence": [f"https://example.org/{eid}"],
            "last_verified": DAY,
        },
        "status": {"value": status, "since": DAY},
        "checks": copy.deepcopy(PASSED),
    }
    entry.update(extra)
    return entry


def valid_entries():
    def av_stream(eid):
        return [
            {
                "method": "streaming_platform",
                "url": f"https://video.test/{eid}",
                "auth": "none",
                "cost": "free",
            }
        ]

    return [
        base(
            "es-mitma-informes",
            title=("Informes de movilidad", "Mobility reports"),
            langs=[("es", "original"), ("en", "machine_translated")],
            area="ES",
            publisher="Ministerio de Ejemplo",
            kind="government",
            modality="text",
            genre="report",
            licence="CC-BY-4.0",
            subdomains=["policy_regulation", "public_transport"],
            status="cleared",
            content={"volume": {"items": 40}},
        ),
        base(
            "es-mitma-informe-2025",
            title=("Informe 2025", "Report 2025"),
            langs=[("es", "original")],
            area="ES",
            publisher="Ministerio de Ejemplo",
            kind="government",
            modality="text",
            genre="report",
            licence="CC-BY-4.0",
            subdomains=["policy_regulation"],
            status="cleared",
            level="item",
            parent="es-mitma-informes",
            content={"volume": {"items": 1}},
        ),
        base(
            "pl-stat-transport-tables",
            title=("Statystyka transportu", "Transport statistics"),
            langs=[("pl", "original")],
            area="PL",
            publisher="Urząd Przykładowy",
            kind="government",
            modality="structured_data",
            genre="table",
            licence="CC-BY-4.0",
            subdomains=["road", "rail"],
            status="cleared",
            content={"frequency": "ANNUAL", "volume": {"bytes": 5000000}},
        ),
        base(
            "jp-gtfs-feeds",
            title=("公共交通オープンデータ", "Public transport open data"),
            langs=[("zxx", "original")],
            area="JP",
            publisher="Example Transit Bureau",
            kind="government",
            modality="structured_data",
            genre="gtfs",
            licence="CC-BY-4.0",
            subdomains=["public_transport"],
            status="verified",
            content={"frequency": "WEEKLY"},
            access=[
                {
                    "method": "api",
                    "url": "https://api.example.org/gtfs",
                    "auth": "account",
                    "cost": "free",
                    "formats": ["application/zip"],
                    "provider_hint": "mobilitydatabase",
                }
            ],
        ),
        base(
            "es-parlamento-comision-transportes",
            title=("Comisión de Transportes", "Transport committee hearings"),
            langs=[("es", "original")],
            area="ES",
            publisher="Parlamento de Ejemplo",
            kind="parliament",
            modality="video",
            genre="hearing",
            licence="LicenseRef-proprietary",
            subdomains=["policy_regulation"],
            status="verified",
            access=av_stream("es-parl"),
            content={"transcripts": {"available": "yes", "languages": ["es"]}, "volume": {"hours": 120}},
            personal_data={"expectation": "present", "categories": ["voices", "faces", "names"]},
        ),
        base(
            "br-podcast-mobilidade",
            title=("Podcast Mobilidade", "Mobility podcast"),
            langs=[("pt", "original")],
            area="BR",
            publisher="Example Podcast Collective",
            kind="community",
            modality="audio",
            genre="podcast",
            licence="CC-BY-NC-4.0",
            subdomains=["cycling", "urban_planning"],
            status="cleared",
            content={"transcripts": {"available": "no"}, "volume": {"hours": 30}},
            access=[
                {
                    "method": "feed",
                    "url": "https://example.org/br-podcast/feed.xml",
                    "auth": "none",
                    "cost": "free",
                    "formats": ["application/rss+xml"],
                }
            ],
            personal_data={"expectation": "present", "categories": ["voices", "names"]},
        ),
        base(
            "pt-lecture-cycling",
            title=("Aulas sobre ciclismo urbano", "Lectures on urban cycling"),
            langs=[("pt", "original")],
            area="PT",
            publisher="Universidade de Exemplo",
            kind="research",
            modality="video",
            genre="lecture",
            licence="CC-BY-4.0",
            subdomains=["cycling"],
            status="cleared",
            content={
                "transcripts": {"available": "yes", "languages": ["pt", "en"]},
                "volume": {"hours": 12},
            },
            personal_data={"expectation": "present", "categories": ["voices", "faces"]},
        ),
        base(
            "fr-charts-mobilite",
            title=("Graphiques de mobilité", "Mobility charts"),
            langs=[("fr", "original")],
            area="FR",
            publisher="Observatoire Exemple",
            kind="government",
            modality="graphic",
            genre="chart",
            licence="etalab-2.0",
            subdomains=["road"],
            status="verified",
            content={"transcripts": {"available": "yes", "languages": ["fr"]}},
        ),
        base(
            "global-street-photos",
            title=("Street photos", "Street photos"),
            langs=[("zxx", "original")],
            area="001",
            publisher="Example Photo Commons",
            kind="community",
            modality="image",
            genre="photo",
            licence="CC0-1.0",
            subdomains=["walking", "urban_planning"],
            status="cleared",
            content={"transcripts": {"available": "no"}, "volume": {"items": 800}},
            personal_data={"expectation": "possible", "categories": ["faces"]},
        ),
        base(
            "eu-maps-mixed",
            title=("Transport maps", "Transport maps"),
            langs=[("und", "unknown")],
            area="EU",
            publisher="Example Union Agency",
            kind="international_org",
            modality="image",
            genre="map",
            licence="mixed",
            subdomains=["rail"],
            status="verified",
            content={"transcripts": {"available": "unknown"}},
        ),
        base(
            "jp-infographic-traffic",
            title=("交通安全インフォグラフィック", "Traffic safety infographic"),
            langs=[("ja", "original")],
            area="JP",
            publisher="Example News",
            kind="media",
            modality="graphic",
            genre="infographic",
            licence="unknown",
            subdomains=["safety"],
            status="candidate",
            content={"transcripts": {"available": "unknown"}},
            checks=[],
            signals=None,
        ),
        base(
            "pl-radio-transport",
            title=("Audycja o transporcie", "Radio programme on transport"),
            langs=[("pl", "original")],
            area="PL",
            publisher="Example Radio",
            kind="media",
            modality="audio",
            genre="radio_programme",
            licence="LicenseRef-proprietary",
            subdomains=["public_transport"],
            status="verified",
            content={"transcripts": {"available": "no"}},
            signals={**SIGNALS_OK, "robots": "deny"},
            personal_data={"expectation": "present", "categories": ["voices"]},
        ),
    ]


def finish(entry, allowlist):
    if entry.get("signals") is None:
        entry.pop("signals")
    if entry["status"]["value"] == "candidate":
        entry.pop("checks", None)
        return entry
    usage, flags = rules.apply(entry, allowlist, DAY)
    entry["usage"] = usage
    if flags:
        entry["status"]["flags"] = flags
    return entry


def invalid_entries(good):
    def variant(eid, change):
        e = copy.deepcopy(good)
        e["id"] = eid
        e["landing_url"] = f"https://example.org/{eid}"
        e["access"][0]["url"] = f"https://example.org/{eid}/data"
        e["access"][0]["download_url"] = f"https://example.org/{eid}/data.zip"
        e["title"] = {"original": f"Variant {eid}", "en": f"Variant {eid}"}
        change(e)
        return e

    return [
        variant("bad-no-licence", lambda e: e.pop("licence")),
        variant("bad-kind-blog", lambda e: e["publisher"].update(kind="blog")),
        variant(
            "bad-zxx-with-es",
            lambda e: e.update(
                languages=[{"code": "zxx", "origin": "original"}, {"code": "es", "origin": "original"}]
            ),
        ),
        variant("bad-missing-parent", lambda e: e.update(level="item", parent="no-such-collection")),
        variant("bad-evidence-null", lambda e: e["licence"].update(evidence_url=None)),
        variant("bad-no-subdomain", lambda e: e.update(subdomains=[])),
        variant(
            "bad-email-in-description",
            lambda e: e.update(
                description="Contact the editor at redaktion@verkehrsblatt-beispiel.de for access."
            ),
        ),
    ]


def write(root: Path, entries):
    if root.exists():
        shutil.rmtree(root)
    (root / "entries").mkdir(parents=True)
    (root / "catalog.yaml").write_text(
        dump_yaml(
            {
                "catalog_id": f"fixture-{root.name}",
                "schema_version": 1,
                "owner": "tests",
                "models": {
                    "scout-large": {
                        "training_data": "span-train-v1",
                        "language_shares": {"de": 0.28, "en": 0.72},
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    for e in entries:
        path = entry_path(root, e)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dump_yaml(ordered(e)), encoding="utf-8")


def main() -> None:
    allowlist = licence_allowlist()
    entries = [finish(e, allowlist) for e in valid_entries()]
    write(VALID, entries)
    good = next(e for e in entries if e["id"] == "pl-stat-transport-tables")
    write(INVALID, invalid_entries(good))
    print(
        yaml.safe_dump(
            {
                e["id"]: (e["status"]["value"], (e.get("usage") or {}).get("permitted_use"))
                for e in entries
            },
            sort_keys=False,
        )
    )


if __name__ == "__main__":
    main()
