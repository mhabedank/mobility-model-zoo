"""Mobility Database harvester: GTFS and GTFS Realtime feeds per country (research R6).

The MobilityData catalogue API lists feeds with provider, status, locations and a licence URL. The
harvester exchanges the refresh token for an access token, lists the feeds of each `--area`
country and yields one collection per provider with its feeds as access routes. It never fetches
a feed (FR-001). Feeds listed for a country but located mostly in another one (cross-border
aggregates) are left to the harvest of that other country.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterator
from typing import Any

from mobility_model_zoo.catalog.harvest.base import Context, Scope, candidate, licence_block, spdx
from mobility_model_zoo.release.errors import CredentialError, UsageError

API = "https://api.mobilitydatabase.org/v1"
PAGE_URL = "https://mobilitydatabase.org/feeds/{data_type}/{id}"
ENDPOINTS = (("gtfs_feeds", "gtfs"), ("gtfs_rt_feeds", "gtfs_rt"))
PAGE = 100
MAX_PAGES = 25  # per endpoint and country: 2,500 feeds
MAX_ROUTES = 5
SKIP_STATUS = {"deprecated", "inactive"}
FORMATS = {"gtfs": ["application/zip"], "gtfs_rt": ["application/x-protobuf"]}
LABELS = {("gtfs",): "GTFS feeds", ("gtfs_rt",): "GTFS Realtime feeds",
          ("gtfs", "gtfs_rt"): "GTFS and GTFS Realtime feeds"}
SPDX_ID = re.compile(r"^([A-Za-z0-9.+-]+|LicenseRef-[A-Za-z0-9.-]+)$")
COUNTRY = re.compile(r"^[A-Z]{2}$")
# A public authority by its name (simple on purpose; the owner refines `publisher.kind` per entry).
GOVERNMENT = re.compile(
    r"\b(city|county|municipal\w*|bureau|ministry|ministerio|department|council|authority|government|"
    r"state of|transport for|région|region of|gobierno|ayuntamiento|consorci\w*|generalitat|junta|"
    r"diputaci\w+|cabildo|concello|ajuntament|àrea metropolitana|area metropolitana|urz[aą]d|gmina|"
    r"miasto|powiat|wojew\w+|zarz[aą]d)\b|[市町村県都府]$|[市町村]役所|交通局",
    re.IGNORECASE,
)


class MobilityDatabase:
    name = "mobility-database"
    catalogue = "Mobility Database"
    env_keys = ("MOBILITYDATABASE_REFRESH_TOKEN",)
    modalities = ("structured_data",)
    method = ("Mobility Database catalogue API (/v1/gtfs_feeds, /v1/gtfs_rt_feeds by country_code); "
              "one collection per provider; metadata only, no feed downloaded")

    def iterate(self, scope: Scope, ctx: Context) -> Iterator[dict[str, Any]]:
        if not scope.areas:
            raise UsageError("mobility-database needs --area: one or more ISO 3166-1 alpha-2 country "
                             "codes (for example --area ES PL JP)")
        regions = [a for a in scope.areas if not COUNTRY.match(a) or a == "EU"]
        if regions:
            raise UsageError(f"mobility-database lists feeds by country; {', '.join(regions)} is not a "
                             "country code")
        if "structured_data" not in scope.modalities:
            ctx.say(f"{self.name}: feeds are structured data; nothing in scope")
            return
        if scope.subdomains and not {"public_transport", "rail"} & set(scope.subdomains):
            ctx.say(f"{self.name}: feeds cover public transport and rail only; nothing in scope")
            return
        headers = {"Authorization": f"Bearer {self.access_token(ctx)}"}
        for area in scope.areas:
            providers: dict[str, list[dict[str, Any]]] = {}
            for feed in self.feeds(area, headers, ctx):
                if feed_in_scope(feed, area):
                    providers.setdefault(provider_of(feed), []).append(feed)
            ctx.say(f"{self.name}: {area}: {sum(map(len, providers.values()))} feeds, "
                    f"{len(providers)} providers")
            for provider, feeds in providers.items():
                cand = self.collection(area, provider, feeds)
                if cand:
                    yield cand

    # ---- API --------------------------------------------------------------------------------------

    def access_token(self, ctx: Context) -> str:
        refresh = ctx.env["MOBILITYDATABASE_REFRESH_TOKEN"]
        r = ctx.client.post(f"{API}/tokens", json={"refresh_token": refresh})
        if r.status_code in (400, 401, 403):
            raise CredentialError(f"MOBILITYDATABASE_REFRESH_TOKEN was refused (HTTP {r.status_code}); "
                                  "renew it at mobilitydatabase.org (see docs/credentials.md)")
        r.raise_for_status()
        token = (r.json() or {}).get("access_token")
        if not token:
            raise CredentialError("the Mobility Database token exchange returned no access_token")
        return token

    def feeds(self, area: str, headers: dict[str, str], ctx: Context) -> Iterator[dict[str, Any]]:
        for endpoint, data_type in ENDPOINTS:
            for page in range(MAX_PAGES):
                params = {"country_code": area, "limit": PAGE, "offset": page * PAGE}
                r = ctx.client.get(f"{API}/{endpoint}", params=params, headers=headers)
                r.raise_for_status()
                items = r.json() or []
                for feed in items:
                    feed.setdefault("data_type", data_type)
                    yield feed
                if len(items) < PAGE:
                    break

    # ---- mapping ----------------------------------------------------------------------------------

    def collection(self, area: str, provider: str, feeds: list[dict[str, Any]]) -> dict[str, Any] | None:
        feeds = sorted(feeds, key=lambda f: (f["data_type"] != "gtfs", str(f.get("id"))))
        routes = [r for r in (route(f) for f in feeds) if r][:MAX_ROUTES]
        if not routes:
            return None
        pages = [page_url(f) for f in feeds]
        types = tuple(sorted({f["data_type"] for f in feeds}))
        licence_id, licence_url, evidence = collection_licence(feeds, pages[0])
        return candidate(
            self,
            title=f"{provider}: {LABELS.get(types, 'GTFS feeds')}",
            title_en=None,
            languages=["zxx"],
            area=area,
            publisher=provider,
            kind="government" if GOVERNMENT.search(provider) else "company",
            landing_url=pages[0],
            modality="structured_data",
            genre="gtfs" if "gtfs" in types else "gtfs_rt",
            subdomains=["public_transport"],
            licence=licence_block(licence_id, licence_url, evidence),
            access=routes,
            evidence=pages[:MAX_ROUTES],
            identifiers={"other": [f"mobilitydatabase:{f['id']}" for f in feeds]},
        )


def provider_of(feed: dict[str, Any]) -> str:
    """The provider name; a long list of operators becomes `first and N others`."""
    name = " ".join(str(feed.get("provider") or "").split()) or "unknown publisher"
    parts = [p for p in name.split(", ") if p]
    if len(parts) > 3:
        return f"{parts[0]} and {len(parts) - 1} others"
    return name


def feed_in_scope(feed: dict[str, Any], area: str) -> bool:
    """Active (or development/future) feeds located mostly in `area`."""
    if str(feed.get("status") or "").lower() in SKIP_STATUS:
        return False
    counts = Counter(str(loc.get("country_code") or "") for loc in feed.get("locations") or []
                     if isinstance(loc, dict))
    return not counts or counts[area] == max(counts.values())


def page_url(feed: dict[str, Any]) -> str:
    return PAGE_URL.format(data_type=feed["data_type"], id=feed["id"])


def source(feed: dict[str, Any]) -> dict[str, Any]:
    info = feed.get("source_info")
    return info if isinstance(info, dict) else {}


def route(feed: dict[str, Any]) -> dict[str, Any] | None:
    info = source(feed)
    url = str(info.get("producer_url") or "").strip()
    if not url.startswith(("http://", "https://")):
        return None
    rt = feed["data_type"] == "gtfs_rt"
    keyed = info.get("authentication_type") not in (None, 0, "0")
    notes = f"{'GTFS Realtime' if rt else 'GTFS'} feed {feed['id']}"
    if rt and feed.get("entity_types"):
        notes += f" ({', '.join(map(str, feed['entity_types']))})"
    if keyed:
        notes += "; needs an API key"
        if str(info.get("authentication_info_url") or "").startswith("http"):
            notes += f": {info['authentication_info_url']}"
    return {
        "method": "feed",
        "url": url,
        "download_url": None if rt else url,
        "auth": "api_key" if keyed else "none",
        "cost": "free",
        "formats": list(FORMATS[feed["data_type"]]),
        "provider_hint": "mobilitydatabase",
        "notes": notes,
    }


def feed_licence(feed: dict[str, Any]) -> tuple[str, str | None]:
    """(SPDX id or `unknown`, licence URL) of one feed."""
    info = source(feed)
    url = str(info.get("license_url") or "").strip() or None
    lid = str(info.get("license_id") or "").strip()
    found = spdx(lid) if lid else "unknown"
    if found == "unknown" and lid and info.get("license_is_spdx") and SPDX_ID.match(lid):
        found = lid
    if found == "unknown":
        found = spdx(url)
    if url and not url.startswith(("http://", "https://")):
        url = None
    return found, url


def collection_licence(feeds: list[dict[str, Any]], landing: str) -> tuple[str, str | None, str | None]:
    """(id, url, evidence): one licence only if every feed states the same; `mixed` otherwise."""
    found = [feed_licence(f) for f in feeds]
    ids = {lid for lid, _ in found}
    if ids == {"unknown"}:
        return "unknown", next((u for _, u in found if u), None), None
    if len(ids) == 1:
        url = next((u for _, u in found if u), None)
        return found[0][0], url, url or landing
    return "mixed", None, landing
