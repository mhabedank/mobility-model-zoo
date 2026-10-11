"""Network checks K4-K7 and `zoo catalog check` against a mocked web (feature 009, T038)."""

from __future__ import annotations

import httpx
import pytest
from catalog_http import ROBOTS_OK, Web

from mobility_model_zoo.catalog import checks
from mobility_model_zoo.catalog.model import load

DAY = "2026-10-11"


def _run(cat, web, **kw):
    return checks.run(
        cat,
        transport=httpx.MockTransport(web),
        throttle=checks.Throttle(sleep=lambda s: None),
        say=lambda m: None,
        **kw,
    )


def _check(e, cid):
    return next(c for c in e["checks"] if c["check"] == cid)


def test_clean_web_verifies_and_clears(catalog_dir):
    cat = load(catalog_dir)
    summary = _run(cat, Web(), ids=["pl-stat-transport-tables", "jp-infographic-traffic"])
    assert summary["checked"] == 2
    e = load(catalog_dir).entries["pl-stat-transport-tables"]
    assert e["status"]["value"] == "cleared" and e["provenance"]["last_verified"]
    assert {c["check"]: c["result"] for c in e["checks"]} == {f"K{i}": "pass" for i in range(1, 10)}
    assert _check(e, "K5")["detail"].startswith("sha256=")
    cand = load(catalog_dir).entries["jp-infographic-traffic"]
    assert cand["status"]["value"] == "verified"  # licence unknown → undetermined, never cleared
    assert cand["usage"]["rule"] == "U2" and cand["signals"]["robots"] == "allow"


def test_404_fails_k4_and_records_the_date(catalog_dir):
    cat = load(catalog_dir)
    _run(cat, Web(status={"/pl-stat-transport-tables": 404}), ids=["pl-stat-transport-tables"])
    e = load(catalog_dir).entries["pl-stat-transport-tables"]
    k4 = _check(e, "K4")
    assert k4["result"] == "fail" and k4["previous"]["gone_dates"]
    assert e["status"]["value"] == "verified"


def test_robots_deny_for_an_ai_agent_blocks_usage(catalog_dir):
    cat = load(catalog_dir)
    _run(
        cat,
        Web(robots=ROBOTS_OK + "User-agent: ClaudeBot\nDisallow: /\n"),
        ids=["pl-stat-transport-tables"],
    )
    e = load(catalog_dir).entries["pl-stat-transport-tables"]
    assert e["signals"]["robots"] == "deny" and _check(e, "K6")["result"] == "warn"
    assert e["usage"]["rule"] == "U1" and e["status"]["value"] == "verified"


def test_head_405_falls_back_to_a_range_get(catalog_dir):
    cat = load(catalog_dir)
    web = Web(head_status=405)
    _run(cat, web, ids=["pl-stat-transport-tables"])
    e = load(catalog_dir).entries["pl-stat-transport-tables"]
    assert _check(e, "K7")["result"] == "pass" and "HTTP 206" in _check(e, "K7")["detail"]


def test_licence_page_change_revokes_clearing(catalog_dir):
    cat = load(catalog_dir)
    _run(cat, Web(licence_body="CC BY 4.0"), ids=["pl-stat-transport-tables"])
    cat = load(catalog_dir)
    _run(cat, Web(licence_body="All rights reserved now"), ids=["pl-stat-transport-tables"])
    e = load(catalog_dir).entries["pl-stat-transport-tables"]
    assert e["status"]["value"] == "verified" and "licence_changed" in e["status"]["flags"]
    assert _check(e, "K5")["previous"]["before"] != _check(e, "K5")["previous"]["evidence_sha256"]


def test_robots_is_fetched_once_per_host_and_run(catalog_dir):
    cat = load(catalog_dir)
    web = Web()
    _run(cat, web, ids=["pl-stat-transport-tables", "es-mitma-informes", "pt-lecture-cycling"])
    assert web.calls[("GET", "example.org", "/robots.txt")] == 1


def test_throttle_waits_per_host():
    now = [0.0]
    slept = []

    def sleep(s):
        slept.append(s)
        now[0] += s

    t = checks.Throttle(interval=1.0, clock=lambda: now[0], sleep=sleep)
    t.wait("a.test")
    t.wait("b.test")
    now[0] += 0.25
    t.wait("a.test")
    assert slept == [pytest.approx(0.75)]


def test_default_selection(catalog_dir):
    import datetime as dt

    cat = load(catalog_dir)
    sel = checks.select(cat, None, None, 180, dt.date(2026, 10, 11))
    assert "jp-infographic-traffic" in sel and "eu-maps-mixed" in sel  # candidate, verified
    assert "pl-stat-transport-tables" not in sel  # cleared and fresh
    later = checks.select(cat, None, None, 180, dt.date(2027, 6, 1))
    assert "pl-stat-transport-tables" in later


def test_unreachable_web_is_exit_6(catalog_dir):
    from mobility_model_zoo.release.errors import HubError

    def down(req):
        raise httpx.ConnectError("down", request=req)

    with pytest.raises(HubError):
        checks.run(
            load(catalog_dir),
            ids=["pl-stat-transport-tables"],
            transport=httpx.MockTransport(down),
            throttle=checks.Throttle(sleep=lambda s: None),
            say=lambda m: None,
        )


def test_offline_check_keeps_earlier_network_results(catalog_dir):
    cat = load(catalog_dir)
    checks.run(cat, ids=["pl-stat-transport-tables"], network=False, say=lambda m: None)
    e = load(catalog_dir).entries["pl-stat-transport-tables"]
    assert e["status"]["value"] == "cleared" and len(e["checks"]) == 9


def test_429_is_retried_after_retry_after():
    answers = [httpx.Response(429, headers={"retry-after": "2"}), httpx.Response(200, text="ok")]
    slept = []
    client = checks.make_client(
        httpx.MockTransport(lambda req: answers.pop(0)), checks.Throttle(sleep=slept.append)
    )
    assert client.get("https://api.example.org/x").status_code == 200
    assert 2.0 in slept


def test_cached_gzip_robots_is_decoded_once():
    import gzip

    body = gzip.compress(b"User-agent: *\nDisallow: /private\n")

    def handler(req):
        return httpx.Response(200, content=body, headers={"content-encoding": "gzip"})

    client = checks.make_client(httpx.MockTransport(handler), checks.Throttle(sleep=lambda s: None))
    assert client.get("https://gz.example.org/robots.txt").text.startswith("User-agent")
    assert client.get("https://gz.example.org/robots.txt").text.startswith("User-agent")  # from the cache
