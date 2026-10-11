"""`zoo catalog check`: run K1-K9, apply the rules and the state machine (FR-017, FR-018, FR-020).

Network checks (K4 landing page, K5 licence evidence, K6 opt-out signals, K7 access route) reuse
the signal checker of feature 006 and fetch only landing, licence and robots pages: never the
resource itself (FR-001, FR-024). Requests are throttled to one per second per host, at most eight
hosts run in parallel, and robots.txt, tdmrep.json and ai.txt are fetched once per host and run.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import threading
import time
from collections import defaultdict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from mobility_model_zoo.catalog import rules, states
from mobility_model_zoo.catalog.model import Catalog, compliance_list, licence_allowlist
from mobility_model_zoo.catalog.validate import Finding, k1, k2, k3, k9
from mobility_model_zoo.compliance import signals

MAX_HOSTS = 8
PER_HOST_SECONDS = 1.0
CACHED_PATHS = ("/robots.txt", "/.well-known/tdmrep.json", "/ai.txt")
SIGNAL_FIELDS = (
    "robots",
    "tdmrep",
    "x_robots",
    "meta_noai",
    "ai_txt",
    "content_signal",
    "content_usage",
)


class Throttle:
    """At most one request per `interval` seconds per host (injectable clock for tests)."""

    def __init__(self, interval: float = PER_HOST_SECONDS, clock=time.monotonic, sleep=time.sleep):
        self.interval, self.clock, self.sleep = interval, clock, sleep
        self.last: dict[str, float] = {}
        self.locks: dict[str, threading.Lock] = defaultdict(threading.Lock)
        self.guard = threading.Lock()

    def wait(self, host: str) -> None:
        with self.guard:
            lock = self.locks[host]
        with lock:
            now = self.clock()
            last = self.last.get(host)
            if last is not None and now - last < self.interval:
                self.sleep(self.interval - (now - last))
            self.last[host] = self.clock()


RETRIES_429 = 3
MAX_RETRY_AFTER = 60.0


def _retry_after(value: str | None) -> float:
    try:
        return min(max(float(value), 1.0), MAX_RETRY_AFTER) if value else 10.0
    except ValueError:
        return 10.0


class CachingTransport(httpx.BaseTransport):
    """Throttles every request per host, retries 429 answers after Retry-After (at most 3 times,
    60 s each) and caches robots.txt, tdmrep.json and ai.txt per run."""

    def __init__(self, inner: httpx.BaseTransport, throttle: Throttle):
        self.inner, self.throttle = inner, throttle
        self.cache: dict[str, tuple[int, dict[str, str], bytes]] = {}
        self.lock = threading.Lock()

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        key = f"{request.url.scheme}://{request.url.host}{request.url.path}"
        cacheable = request.method == "GET" and request.url.path in CACHED_PATHS
        if cacheable:
            with self.lock:
                hit = self.cache.get(key)
            if hit:
                return httpx.Response(hit[0], headers=hit[1], content=hit[2], request=request)
        self.throttle.wait(request.url.host)
        response = self.inner.handle_request(request)
        for _ in range(RETRIES_429):  # back off politely when a host says "too many requests"
            if response.status_code != 429:
                break
            response.close()
            self.throttle.sleep(_retry_after(response.headers.get("retry-after")))
            self.throttle.wait(request.url.host)
            response = self.inner.handle_request(request)
        if cacheable:
            body = response.read()  # decoded: drop the encoding headers so it is not decoded twice
            headers = {k: v for k, v in response.headers.items()
                       if k.lower() not in ("content-encoding", "content-length", "transfer-encoding")}
            response.close()
            with self.lock:
                self.cache[key] = (response.status_code, headers, body)
            return httpx.Response(response.status_code, headers=headers, content=body, request=request)
        return response


def make_client(
    transport: httpx.BaseTransport | None = None, throttle: Throttle | None = None
) -> httpx.Client:
    inner = transport or httpx.HTTPTransport(retries=1)
    return httpx.Client(
        transport=CachingTransport(inner, throttle or Throttle()),
        headers={"User-Agent": signals.USER_AGENT},
        follow_redirects=True,
        timeout=30,
    )


def _result(check: str, result: str, detail: str = "", previous: Any = None) -> dict[str, Any]:
    out = {"check": check, "result": result, "at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds")}
    if detail:
        out["detail"] = detail[:500]
    if previous is not None:
        out["previous"] = previous
    return out


def _from_findings(check: str, findings: list[Finding]) -> dict[str, Any]:
    mine = [f for f in findings if f.check == check]
    if any(f.severity == "fail" for f in mine):
        return _result(
            check, "fail", "; ".join(f"{f.field}: {f.message}" for f in mine if f.severity == "fail")
        )
    if mine:
        return _result(check, "warn", "; ".join(f"{f.field}: {f.message}" for f in mine))
    return _result(check, "pass")


def _old(entry: dict[str, Any], check: str) -> dict[str, Any]:
    return next((c for c in entry.get("checks") or [] if c.get("check") == check), {})


# ---- network checks ----------------------------------------------------------------------------


def _lists(zoo_root: Path | None) -> tuple[signals.Lists, Callable[[str], str] | None]:
    from mobility_model_zoo.compliance.hashing import url_hasher

    suppressed: set[str] = set()
    if zoo_root is not None and (zoo_root / "compliance" / "suppression.yaml").is_file():
        import yaml

        data = (
            yaml.safe_load((zoo_root / "compliance" / "suppression.yaml").read_text(encoding="utf-8"))
            or {}
        )
        suppressed = {e["hash"] for e in data.get("entries") or [] if e.get("kind") == "url"}
    lists = signals.Lists(
        ai_agents=(compliance_list("ai-user-agents", zoo_root) or {}).get("agents", []),
        denylist=(compliance_list("denylist", zoo_root) or {}).get("domains", []),
        piracy=(compliance_list("piracy-domains", zoo_root) or {}).get("domains", []),
        suppressed_url_hashes=suppressed,
        reservation_labels=signals.reservation_labels(compliance_list("ai-preferences", zoo_root)),
    )
    return lists, (url_hasher() if suppressed else None)


def network_checks(
    entry: dict[str, Any], client: httpx.Client, lists: signals.Lists, url_hash, today: str
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, bool]:
    """K4-K7 for one entry. Returns (results, new signals or None, host reachable)."""
    results = []
    terms = entry.get("platform_terms") or {}
    verdict, page = signals.check_url(
        entry["landing_url"], lists, client, tos_url=terms.get("url"), url_hash=url_hash
    )
    reasons = "; ".join(f"{c}: {r}" for c, r in verdict.reasons)
    reachable = True
    old4 = _old(entry, "K4")
    gone = list((old4.get("previous") or {}).get("gone_dates") or [])
    if page is None:
        robots_down = any(c == "C-F1" and "unreachable" in r for c, r in verdict.reasons)
        if robots_down or not verdict.reasons:
            reachable = False
            results.append(
                _result("K4", "fail", "landing page unreachable" + (f" ({reasons})" if reasons else ""))
            )
        else:  # blocked before the page was fetched (robots, lists): not a reachability failure
            results.append(_result("K4", "warn", f"page not fetched: {reasons}"))
    elif page.status_code in (404, 410):
        gone.append(today)
        results.append(
            _result("K4", "fail", f"HTTP {page.status_code}", {"gone_dates": sorted(set(gone))})
        )
    elif page.status_code >= 400:
        results.append(_result("K4", "fail", f"HTTP {page.status_code}"))
    else:
        results.append(_result("K4", "pass", f"HTTP {page.status_code}"))

    new_signals = None
    if page is not None or verdict.reasons:
        new_signals = {name: getattr(verdict, name) for name in SIGNAL_FIELDS}
        new_signals["checked_at"] = today
        hard = [r for c, r in verdict.reasons if c in ("C-F1", "C-F2", "C-F3", "C-F4", "C-F5")]
        if any("unreachable; retry later" in r for r in hard):
            results.append(_result("K6", "fail", reasons))
            new_signals = None
        elif verdict.reasons:
            results.append(_result("K6", "warn", reasons))
        else:
            results.append(_result("K6", "pass"))

    lic = entry.get("licence") or {}
    if lic.get("id") == "unknown" or not lic.get("evidence_url"):
        results.append(_result("K5", "pass", "skipped: licence unknown"))
    else:
        ev, ev_page = signals.check_url(lic["evidence_url"], lists, client)
        if ev_page is None or ev_page.status_code >= 400:
            status = ev_page.status_code if ev_page is not None else "-"
            results.append(_result("K5", "fail", f"licence evidence unreachable (HTTP {status})"))
        else:
            digest = hashlib.sha256(ev_page.content).hexdigest()
            previous = _old(entry, "K5").get("previous") or {}
            results.append(
                _result(
                    "K5",
                    "pass",
                    f"sha256={digest}",
                    {
                        "evidence_sha256": digest,
                        "licence_id": lic.get("id"),
                        "before": previous.get("evidence_sha256"),
                    },
                )
            )

    results.append(_route_check(entry, client))
    return results, new_signals, reachable


def _route_check(entry: dict[str, Any], client: httpx.Client) -> dict[str, Any]:
    route = states.clearable_route(entry)
    if route is None:
        return _result("K7", "pass", "skipped: no route usable for an automated download")
    url = route.get("download_url") or route["url"]
    try:
        if route.get("download_url"):
            resp = client.head(url)
            if resp.status_code in (405, 501):
                with client.stream("GET", url, headers={"Range": "bytes=0-0"}) as r:
                    resp = r
        else:
            with client.stream("GET", url) as r:
                resp = r
    except httpx.HTTPError as e:
        return _result("K7", "fail", f"{url}: {type(e).__name__}")
    ok = resp.status_code < 400 or (route.get("auth") == "api_key" and resp.status_code in (401, 403))
    return _result("K7", "pass" if ok else "fail", f"{url}: HTTP {resp.status_code}")


# ---- orchestration -----------------------------------------------------------------------------


def select(
    cat: Catalog, ids: list[str] | None, statuses: list[str] | None, stale_days: int, today: dt.date
) -> list[str]:
    if ids:
        return [i for i in ids if i in cat.entries]
    out = []
    for eid, e in cat.entries.items():
        value = (e.get("status") or {}).get("value")
        if statuses:
            if value in statuses:
                out.append(eid)
            continue
        if value in ("candidate", "verified"):
            out.append(eid)
        elif value == "cleared":
            last = (e.get("provenance") or {}).get("last_verified")
            if not last or (today - dt.date.fromisoformat(last)).days > stale_days:
                out.append(eid)
    return sorted(out)


def _changed(entry: dict[str, Any], before: dict[str, Any]) -> list[str]:
    out = []
    k5 = _old(entry, "K5").get("previous") or {}
    if k5.get("before") and k5.get("evidence_sha256") and k5["before"] != k5["evidence_sha256"]:
        out.append("evidence")
    if before.get("licence") != (entry.get("licence") or {}).get("id"):
        out.append("licence")
    old_deny = {k for k, v in (before.get("signals") or {}).items() if v == "deny"}
    new_deny = {k for k, v in (entry.get("signals") or {}).items() if v == "deny"}
    if new_deny - old_deny:
        out.append("signals")
    if before.get("use") != (entry.get("usage") or {}).get("permitted_use"):
        out.append("usage")
    return out


def run(
    cat: Catalog,
    *,
    ids=None,
    statuses=None,
    stale_days: int = 180,
    network: bool = True,
    zoo_root: Path | None = None,
    say: Callable[[str], None] = print,
    transport: httpx.BaseTransport | None = None,
    throttle: Throttle | None = None,
    today: dt.date | None = None,
) -> dict[str, int]:
    from mobility_model_zoo.release.errors import HubError

    day = today or dt.date.today()
    today_s = day.isoformat()
    selected = select(cat, ids, statuses, stale_days, day)
    allowlist = licence_allowlist(zoo_root)
    catalog_findings = k2(cat) + k3(cat)
    by_entry: dict[str, list[Finding]] = defaultdict(list)
    for f in catalog_findings:
        by_entry[f.entry_id].append(f)

    net: dict[str, tuple[list[dict[str, Any]], dict[str, Any] | None, bool]] = {}
    if network and selected:
        lists, url_hash = _lists(zoo_root)
        client = make_client(transport, throttle)
        hosts: dict[str, list[str]] = defaultdict(list)
        for eid in selected:
            hosts[urlparse(cat.entries[eid]["landing_url"]).hostname or ""].append(eid)

        def work(group: list[str]) -> list[tuple[str, Any]]:
            return [
                (eid, network_checks(cat.entries[eid], client, lists, url_hash, today_s))
                for eid in group
            ]

        with ThreadPoolExecutor(max_workers=MAX_HOSTS) as pool:
            for done in pool.map(work, hosts.values()):
                net.update(dict(done))
                say(f"network checks: {len(net)}/{len(selected)} entries")
        client.close()
        if not any(reachable for _, _, reachable in net.values()):
            raise HubError("no host was reachable; check the network and run again")

    summary: dict[str, int] = defaultdict(int)
    for eid in selected:
        e = cat.entries[eid]
        before = {
            "licence": _prev_licence(e),
            "signals": dict(e.get("signals") or {}),
            "use": (e.get("usage") or {}).get("permitted_use"),
        }
        offline = k1(e) + k9(e) + by_entry.get(eid, [])
        results = [_from_findings(c, offline) for c in ("K1", "K2", "K3", "K9")]
        for f in offline:
            if f.flag:
                states.set_flag(e, f.flag)
        if eid in net:
            net_results, new_signals, reachable = net[eid]
            results += net_results
            if new_signals is not None:
                e["signals"] = new_signals
            k4 = next(r for r in net_results if r["check"] == "K4")
            states.set_flag(
                e,
                "unreachable",
                k4["result"] == "fail"
                and k4.get("detail", "").startswith(("landing page unreachable", "HTTP 5")),
            )
            if k4["result"] == "pass":
                e.setdefault("provenance", {})["last_verified"] = today_s
        else:  # keep earlier network results
            results += [c for c in e.get("checks") or [] if c["check"] in ("K4", "K5", "K6", "K7")]
        usage, flags = rules.apply(e, allowlist, today_s)
        if e.get("signals") or (e.get("status") or {}).get("value") != "candidate":
            e["usage"] = usage
        states.set_flag(e, "owner_decision_needed", "owner_decision_needed" in flags)
        results.append(_result("K8", "pass", f"{usage['rule']}: {usage['permitted_use']}"))
        order = {c: i for i, c in enumerate(("K1", "K2", "K3", "K4", "K5", "K6", "K7", "K8", "K9"))}
        e["checks"] = sorted(results, key=lambda r: order[r["check"]])
        new = states.transition(e, today_s, _changed(e, before))
        cat.write_entry(e)
        summary[new] += 1
        summary["checked"] += 1
    return dict(summary)


def _prev_licence(entry: dict[str, Any]) -> str | None:
    prev = _old(entry, "K5").get("previous") or {}
    return prev.get("licence_id") or (entry.get("licence") or {}).get("id")
