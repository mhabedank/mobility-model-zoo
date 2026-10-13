"""OpenAlex harvester: open-access papers by language and mobility subdomain (research R6, T051).

One query per language × subdomain on https://api.openalex.org/works: open access, with a DOI,
in the language, with a transport-related topic (`TOPIC_SUBFIELDS`), and a title/abstract search
for any of the subdomain's terms (terms.yaml), paged with a cursor. Only metadata is requested
(`select`); the abstract is never requested and author names, ids and ORCIDs are never read: the
authorships are used for the institution country only.

Budget (checked 2026-10-11). OpenAlex bills usage beyond the free daily allowance; the owner's
account has no payment method, so the harvester stops at 80% of that allowance (R6):
- https://help.openalex.org/access/pricing : a free key gets "$1 of usage per day", reset at
  midnight UTC.
- https://help.openalex.org/access/example-costs : list + filter 1 credit ($0.0001), search
  10 credits ($0.001), singleton free, content download 100 credits.
- https://help.openalex.org/how-to-use-the-api/rate-limits-and-authentication : headers
  X-RateLimit-Limit (daily budget), X-RateLimit-Remaining, X-RateLimit-Credits-Used,
  X-RateLimit-Reset; 429 when the budget is used up; key as `api_key` or `Authorization: Bearer`.
- Live headers on 2026-10-11 for a /works query with `title_and_abstract.search`:
  x-ratelimit-limit 10000, x-ratelimit-limit-usd 1, x-ratelimit-credits-used 10,
  x-ratelimit-cost-usd 0.001; x-ratelimit-remaining is the balance after the request.
So the free allowance is 10,000 credits a day (one credit is $0.0001, not $0.00001), each page of
results costs 10 credits, and 80% allows 800 pages a day. The harvester counts its own spending
(`Budget`) and also stops when the account-wide remaining credits fall below 20% of the limit,
which covers other runs on the same day.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterator
from typing import Any

from mobility_model_zoo.catalog.harvest.base import (
    Budget,
    BudgetExhausted,
    Context,
    Scope,
    candidate,
    licence_block,
    search_terms,
    spdx,
    subdomains_for,
)
from mobility_model_zoo.catalog.model import vocab

API = "https://api.openalex.org/works"
DAILY_CREDITS = 10_000  # free key, $1 a day (see the module docstring)
SEARCH_CREDITS = 10  # one /works page with a title/abstract search
STOP_SHARE = 0.8
PER_PAGE = 50
FIELDS = "id,doi,display_name,language,publication_date,primary_location,best_oa_location,authorships"
# OpenAlex topic subfields a work must have among its topics (any position). Without this filter
# the term search also finds literature and art history ("Un tranvía llamado deseo"); with it the
# pilot queries returned transport papers only (checked live 2026-10-11, same cost per page).
# https://openalex.org/subfields/<id>: 3313 Transportation, 3322 Urban Studies, 3305 Geography,
# Planning and Development, 2203 Automotive, 2202 Aerospace, 2212 Ocean, 2205 Civil and Structural
# Engineering, 1803 Management Science and Operations Research.
TOPIC_SUBFIELDS = "3313|3322|3305|2203|2202|2212|2205|1803"
DOI = re.compile(r"^10\.[0-9]{4,9}/\S+$")
CJK = re.compile(r"[぀-ヿ㐀-鿿가-힯]")


# OpenAlex licence ids carry no version; like base.SPDX_ALIASES for `cc-by`, CC 4.0 is assumed.
# `other-oa`, `publisher-specific-oa`, `implied-oa` and `unspecified-oa` stay `unknown`.
def licence_id(value: str | None) -> str:
    """SPDX id of an OpenAlex `license` value (`cc-by-nc`, …); `unknown` when nothing matches."""
    if not value:
        return "unknown"
    key = str(value).strip().lower().removeprefix("https://openalex.org/licenses/")
    return spdx(key)  # versionless CC ids are in base.SPDX_ALIASES


def search_filter(terms: list[str]) -> str:
    """`a|"b c"|d` for `title_and_abstract.search`: OR over the terms, Latin phrases quoted."""
    parts = []
    for term in terms:
        text = " ".join(re.sub(r'[,|"]', " ", term).split())
        if text:
            parts.append(f'"{text}"' if " " in text and not CJK.search(text) else text)
    return "|".join(parts)


def _doi(value: str | None) -> str | None:
    if not value:
        return None
    doi = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", str(value).strip(), flags=re.IGNORECASE)
    return doi if DOI.match(doi) else None


def _http(value: Any) -> str | None:
    return value if isinstance(value, str) and value.startswith(("http://", "https://")) else None


def _area(work: dict[str, Any]) -> str:
    """Country of the first institution in the authorships (no author data is read), else World."""
    areas = vocab().areas
    for authorship in work.get("authorships") or []:
        for inst in (authorship or {}).get("institutions") or []:
            code = str((inst or {}).get("country_code") or "").upper()
            if code:
                return code if code in areas else "001"
    return "001"


class Meter:
    """Account-wide credits from the response headers; stops below (1 - stop_share) of the limit."""

    def __init__(self, stop_share: float):
        self.stop_share = stop_share
        self.limit: float | None = None
        self.remaining: float | None = None

    def update(self, headers: Any) -> None:
        try:
            self.limit = float(headers.get("x-ratelimit-limit") or self.limit or DAILY_CREDITS)
            if headers.get("x-ratelimit-remaining") is not None:
                self.remaining = float(headers["x-ratelimit-remaining"])
        except ValueError:
            pass

    def check(self) -> None:
        if self.remaining is None or self.limit is None:
            return
        if self.remaining < self.limit * (1 - self.stop_share):
            raise BudgetExhausted(
                f"OpenAlex reports {self.remaining:g} of {self.limit:g} daily credits left; "
                f"stopping at {self.stop_share:.0%} of the free allowance"
            )


class OpenAlex:
    name = "openalex"
    catalogue = "OpenAlex"
    env_keys = ("OPENALEX_API_KEY",)
    modalities = ("text",)
    method = (
        "OpenAlex /works: open-access works with a DOI per language and transport-related topic "
        "subfield, title/abstract search for the subdomain terms (terms.yaml), cursor paging; "
        "stops at 80% of the free daily credits"
    )

    def iterate(self, scope: Scope, ctx: Context) -> Iterator[dict[str, Any]]:
        budget = ctx.budget or Budget(allowance=DAILY_CREDITS, stop_share=STOP_SHARE)
        meter = Meter(budget.stop_share)
        cells = [(lang, sub) for lang in scope.languages for sub in subdomains_for(scope)]
        quota = max(1, math.ceil(ctx.limit / max(1, len(cells))))
        seen: dict[str, dict[str, Any]] = {}
        for lang, sub in cells:
            terms = search_filter(search_terms(sub, lang))
            if not terms:
                continue
            got = 0
            for work in self.works(ctx, budget, meter, lang, terms, min(PER_PAGE, quota)):
                key = str(work.get("id") or "")
                if key in seen:  # found again with another subdomain's terms
                    if sub not in seen[key]["subdomains"]:
                        seen[key]["subdomains"].append(sub)
                    continue
                cand = self.to_candidate(work, lang, sub)
                if cand is None:
                    continue
                seen[key] = cand
                got += 1
                yield cand
                if got >= quota:
                    break
            ctx.say(f"openalex: {lang} {sub}: {got} works")

    def works(
        self, ctx: Context, budget: Budget, meter: Meter, language: str, terms: str, per_page: int
    ) -> Iterator[dict[str, Any]]:
        cursor: str | None = "*"
        params = {
            "filter": f"language:{language},open_access.is_oa:true,has_doi:true,"
            f"topics.subfield.id:{TOPIC_SUBFIELDS},"
            f"title_and_abstract.search:{terms}",
            "select": FIELDS,
            "per_page": str(per_page),
        }
        headers = {"Authorization": f"Bearer {ctx.env['OPENALEX_API_KEY']}"}
        while cursor:
            meter.check()
            budget.spend(SEARCH_CREDITS)
            response = ctx.client.get(API, params={**params, "cursor": cursor}, headers=headers)
            meter.update(response.headers)
            if response.status_code == 429:
                raise BudgetExhausted("OpenAlex answered 429 (daily budget or rate limit reached)")
            response.raise_for_status()
            data = response.json()
            results = data.get("results") or []
            yield from results
            cursor = (data.get("meta") or {}).get("next_cursor") if results else None

    def to_candidate(self, work: dict[str, Any], language: str, subdomain: str) -> dict[str, Any] | None:
        title = str(work.get("display_name") or "").strip()
        best = work.get("best_oa_location") or {}
        primary = work.get("primary_location") or {}
        doi = _doi(work.get("doi"))
        doi_url = f"https://doi.org/{doi}" if doi else None
        page = _http(best.get("landing_page_url")) or _http(primary.get("landing_page_url"))
        landing = doi_url or page
        if not title or not landing:
            return None
        lid = licence_id(best.get("license") or primary.get("license"))
        source = primary.get("source") or best.get("source") or {}
        publisher = source.get("host_organization_name") or source.get("display_name") or ""
        pdf = _http(best.get("pdf_url"))
        route: dict[str, Any] = {
            "method": "direct_download" if pdf else "page_by_page",
            "url": page or landing,
            "auth": "none",
            "cost": "free",
            "provider_hint": "url",
        }
        if pdf:
            route |= {"download_url": pdf, "formats": ["application/pdf"]}
        identifiers: dict[str, Any] = {}
        if doi:
            identifiers["doi"] = doi
        work_id = str(work.get("id") or "").rsplit("/", 1)[-1]
        if work_id:
            identifiers["other"] = [f"openalex:{work_id}"]
        evidence = [u for u in (_http(work.get("id")), page or landing) if u]
        published = work.get("publication_date")
        cand = candidate(
            self,
            title=title,
            title_en=None,
            languages=[work.get("language") or language],
            area=_area(work),
            publisher=str(publisher),
            kind="research",
            landing_url=landing,
            modality="text",
            genre="paper",
            subdomains=[subdomain],
            licence=licence_block(lid, None, page or landing),
            access=[route],
            evidence=list(dict.fromkeys(evidence)),
            level="item",
            content={"published": str(published)} if published else None,
            identifiers=identifiers or None,
        )
        cand["parent"] = None
        return cand
