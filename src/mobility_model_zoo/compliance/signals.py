"""Opt-out signals at fetch time (research R4, checks C-F1 … C-F7). Fail closed.

Order: domain lists, robots.txt (project agent, `*`, AI crawler agents), access barriers, TDMRep
(well-known file, header, meta), X-Robots-Tag and meta robots (`noai`), ai.txt, terms of service.
Network errors and 5xx answers of robots.txt mean "do not fetch now"; RFC 9309 allows treating
4xx (except 401/403) as "no robots.txt".
"""

from __future__ import annotations

import datetime as dt
import hashlib
import re
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

PROJECT_AGENT = "mobility-model-zoo-crawler"
USER_AGENT = (
    f"{PROJECT_AGENT}/1.0 "
    "(+https://github.com/mhabedank/mobility-model-zoo/blob/main/COPYRIGHT_POLICY.md)"
)
LEGACY_AGENTS = ("jtbd-pilot",)
TOS_TERMS = re.compile(
    r"(?i)(text[- ]and[- ]data[- ]mining|data[- ]mining|text[- ]mining|scrap(e|ing)|crawl(er|ing)?|"
    r"machine[- ]learning|künstliche[n]? intelligenz|\bKI\b|automatisiert\w* (abruf|auslesen|zugriff)|"
    r"robots?|spider)"
)
NOAI = re.compile(r"(?i)\b(noai|noml|noimageai)\b")
LOGIN = re.compile(r'(?i)(<input[^>]+type=["\']?password|captcha|g-recaptcha|hcaptcha)')


@dataclass
class Verdict:
    url: str
    fetched_at: str
    user_agent: str = USER_AGENT
    http_status: int | None = None
    robots: str = "absent"  # allow | deny | absent
    tdmrep: str = "absent"
    x_robots: str = "absent"
    meta_noai: str = "absent"
    ai_txt: str = "absent"
    denylist: bool = False
    robots_sha256: str | None = None
    tos_url: str | None = None
    tos_sha256: str | None = None
    tos_flag: bool = False
    content_sha256: str | None = None
    decision: str = "skipped"  # fetched | skipped | allowed
    reasons: list[tuple[str, str]] = field(default_factory=list)  # (check id, reason)

    def block(self, check_id: str, reason: str) -> None:
        self.reasons.append((check_id, reason))

    @property
    def allowed(self) -> bool:
        return not self.reasons

    def manifest_entry(self) -> dict[str, Any]:
        d = asdict(self)
        d["reasons"] = [{"check": c, "reason": r} for c, r in self.reasons]
        d["canonical_url"] = canonical(self.url)
        return d


def canonical(url: str) -> str:
    p = urlparse(url)
    host = (p.hostname or "").lower().removeprefix("www.")
    return f"{p.scheme.lower()}://{host}{p.path.rstrip('/') or '/'}" + (f"?{p.query}" if p.query else "")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def host_matches(host: str, domains: Iterable[str]) -> bool:
    host = host.lower().removeprefix("www.")
    return any(
        host == d.lower().removeprefix("www.") or host.endswith("." + d.lower().removeprefix("www."))
        for d in domains
    )


# ---- robots.txt (RFC 9309) -------------------------------------------------------------------


def parse_robots(text: str) -> list[tuple[list[str], list[tuple[str, str]]]]:
    """Groups of (user agents, [(allow|disallow, path)])."""
    groups: list[tuple[list[str], list[tuple[str, str]]]] = []
    agents: list[str] = []
    rules: list[tuple[str, str]] = []
    last_was_agent = False
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, value = (x.strip() for x in line.split(":", 1))
        key = key.lower()
        if key == "user-agent":
            if not last_was_agent and (agents or rules):
                groups.append((agents, rules))
                agents, rules = [], []
            agents.append(value.lower())
            last_was_agent = True
        elif key in ("allow", "disallow"):
            rules.append((key, value))
            last_was_agent = False
        else:
            last_was_agent = False
    if agents or rules:
        groups.append((agents, rules))
    return groups


def _rule_matches(pattern: str, path: str) -> bool:
    if not pattern:
        return False
    regex = re.escape(pattern).replace(r"\*", ".*")
    if regex.endswith(r"\$"):
        regex = regex[:-2] + "$"
    return re.match(regex, path) is not None


def robots_allows(groups, agent: str, path: str) -> bool | None:
    """True/False for the group naming `agent`; None if no group names it (caller handles '*')."""
    agent = agent.lower()
    chosen = [rules for agents, rules in groups if any(a != "*" and agent.startswith(a) for a in agents)]
    if not chosen:
        return None
    rules = [r for g in chosen for r in g]
    best: tuple[int, str] | None = None
    for kind, pattern in rules:
        if _rule_matches(pattern, path) and (
            best is None or len(pattern) > best[0] or (len(pattern) == best[0] and kind == "allow")
        ):
            best = (len(pattern), kind)
    return best is None or best[1] == "allow"


def robots_star_allows(groups, path: str) -> bool:
    rules = [r for agents, g in groups if "*" in agents for r in g]
    best: tuple[int, str] | None = None
    for kind, pattern in rules:
        if _rule_matches(pattern, path) and (
            best is None or len(pattern) > best[0] or (len(pattern) == best[0] and kind == "allow")
        ):
            best = (len(pattern), kind)
    return best is None or best[1] == "allow"


def evaluate_robots(text: str, path: str, ai_agents: Iterable[str]) -> tuple[bool, list[str]]:
    """Allowed for the project agent and every AI agent? Returns (allowed, agents that are denied)."""
    groups = parse_robots(text)
    denied = []
    for agent in (PROJECT_AGENT, *LEGACY_AGENTS):
        verdict = robots_allows(groups, agent, path)
        if verdict is False or (verdict is None and not robots_star_allows(groups, path)):
            denied.append(agent)
    for agent in ai_agents:
        if robots_allows(groups, agent, path) is False:
            denied.append(agent)
    return (not denied, denied)


# ---- the full check -------------------------------------------------------------------------


@dataclass
class Lists:
    ai_agents: list[str] = field(default_factory=list)
    denylist: list[str] = field(default_factory=list)
    piracy: list[str] = field(default_factory=list)
    suppressed_url_hashes: set[str] = field(default_factory=set)


def _get(client: httpx.Client, url: str) -> httpx.Response | None:
    try:
        return client.get(url, headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=30)
    except httpx.HTTPError:
        return None


def check_url(
    url: str,
    lists: Lists,
    client: httpx.Client | None = None,
    *,
    tos_url: str | None = None,
    fetch_content: bool = True,
    url_hash=None,
) -> tuple[Verdict, httpx.Response | None]:
    """Run every signal for `url`. With fetch_content the page itself is fetched (and returned)."""
    own = client is None
    client = client or httpx.Client()
    v = Verdict(url=url, fetched_at=dt.datetime.now(dt.UTC).isoformat(timespec="seconds"))
    try:
        parsed = urlparse(url)
        host, base = parsed.hostname or "", f"{parsed.scheme}://{parsed.netloc}"
        if host_matches(host, lists.denylist):
            v.denylist = True
            v.block("C-F5", "domain on the deny list")
        if host_matches(host, lists.piracy):
            v.denylist = True
            v.block("C-F5", "domain on the piracy list")
        if url_hash and url_hash(canonical(url)) in lists.suppressed_url_hashes:
            v.block("C-F5", "URL on the suppression list")
        if v.reasons:
            return v, None

        robots = _get(client, urljoin(base, "/robots.txt"))
        if robots is None or robots.status_code >= 500:
            v.block("C-F1", "robots.txt unreachable; retry later")
        elif robots.status_code in (401, 403):
            v.robots = "deny"
            v.block("C-F1", f"robots.txt answered {robots.status_code}")
        elif robots.status_code >= 400:
            v.robots = "absent"
        else:
            v.robots_sha256 = _sha(robots.content)
            path = parsed.path or "/"
            if parsed.query:
                path += "?" + parsed.query
            ok, denied = evaluate_robots(robots.text, path, lists.ai_agents)
            v.robots = "allow" if ok else "deny"
            if not ok:
                v.block("C-F1", f"robots.txt disallows {', '.join(denied)}")

        tdm = _get(client, urljoin(base, "/.well-known/tdmrep.json"))
        if tdm is not None and tdm.status_code == 200:
            try:
                rules = tdm.json()
            except ValueError:
                rules = []
            for rule in rules if isinstance(rules, list) else []:
                loc = str(rule.get("location", "/"))
                if (
                    _rule_matches(loc if loc.startswith("/") else "/" + loc, parsed.path or "/")
                    and str(rule.get("tdm-reservation")) == "1"
                ):
                    v.tdmrep = "deny"
                    v.block("C-F2", "TDMRep reservation (/.well-known/tdmrep.json)")
                    break
            else:
                v.tdmrep = v.tdmrep if v.tdmrep == "deny" else "allow"

        ai_txt = _get(client, urljoin(base, "/ai.txt"))
        if (
            ai_txt is not None
            and ai_txt.status_code == 200
            and "text" in ai_txt.headers.get("content-type", "text")
        ):
            groups = parse_robots(ai_txt.text)
            text_denied = any(
                _rule_matches(p, "/x.txt") or _rule_matches(p, "*.txt") or p in ("/", "*")
                for agents, rules in groups
                if "*" in agents
                for kind, p in rules
                if kind == "disallow"
            )
            v.ai_txt = "deny" if text_denied else "allow"
            if text_denied:
                v.block("C-F4", "ai.txt disallows text")

        if tos_url:
            v.tos_url = tos_url
            tos = _get(client, tos_url)
            if tos is None or tos.status_code >= 400:
                v.block("C-F6", "terms of service unreachable")
            else:
                v.tos_sha256 = _sha(tos.content)
                v.tos_flag = bool(TOS_TERMS.search(tos.text))

        page = None
        if fetch_content and v.allowed:
            page = _get(client, url)
            if page is None:
                v.block("C-F7", "page unreachable")
                return v, None
            v.http_status = page.status_code
            if page.status_code in (401, 402, 403, 407):
                v.block("C-F7", f"access barrier (HTTP {page.status_code})")
            reservation = page.headers.get("tdm-reservation")
            if reservation is not None and reservation.strip() == "1":
                v.tdmrep = "deny"
                v.block("C-F2", "TDM reservation header")
            if NOAI.search(page.headers.get("x-robots-tag", "")):
                v.x_robots = "deny"
                v.block("C-F3", "X-Robots-Tag noai")
            else:
                v.x_robots = "allow" if "x-robots-tag" in page.headers else "absent"
            if "html" in page.headers.get("content-type", ""):
                head = page.text[:200_000]
                for m in re.finditer(
                    r'(?is)<meta[^>]+name=["\'](robots|tdm-reservation)["\'][^>]*>', head
                ):
                    tag = m.group(0)
                    if m.group(1).lower() == "robots" and NOAI.search(tag):
                        v.meta_noai = "deny"
                        v.block("C-F3", "meta robots noai")
                    if m.group(1).lower() == "tdm-reservation" and re.search(r'content=["\']1', tag):
                        v.tdmrep = "deny"
                        v.block("C-F2", "meta tdm-reservation")
                if v.meta_noai == "absent":
                    v.meta_noai = "allow"
                if LOGIN.search(head):
                    v.block("C-F7", "login form or CAPTCHA")
            v.content_sha256 = _sha(page.content)
        v.decision = ("fetched" if fetch_content else "allowed") if v.allowed else "skipped"
        return v, page
    finally:
        if own:
            client.close()
