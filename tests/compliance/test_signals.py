"""Opt-out signals at fetch time (C-F1 … C-F7), against mocked sites."""

import httpx
import pytest

from mobility_model_zoo.compliance import signals

LISTS = signals.Lists(
    ai_agents=["GPTBot", "CCBot"], denylist=["blocked.example"], piracy=["libgen.example"]
)
PAGE = "<html><head><title>t</title></head><body>Text about buses.</body></html>"


def site(
    robots=(200, "User-agent: *\nAllow: /\n"),
    page=(200, PAGE, {}),
    tdm=None,
    ai_txt=None,
    tos=None,
    robots_error=False,
):
    def handler(req):
        path = req.url.path
        if path == "/robots.txt":
            if robots_error:
                raise httpx.ConnectError("down")
            return httpx.Response(robots[0], text=robots[1])
        if path == "/.well-known/tdmrep.json":
            return httpx.Response(200, json=tdm) if tdm is not None else httpx.Response(404)
        if path == "/ai.txt":
            return (
                httpx.Response(200, text=ai_txt, headers={"content-type": "text/plain"})
                if ai_txt is not None
                else httpx.Response(404)
            )
        if path == "/terms":
            return httpx.Response(200, text=tos or "Use freely.")
        status, body, headers = page
        return httpx.Response(status, text=body, headers={"content-type": "text/html", **headers})

    return httpx.Client(transport=httpx.MockTransport(handler))


def check(client, url="https://news.example/a", **kw):
    v, _ = signals.check_url(url, LISTS, client, **kw)
    return {c for c, _ in v.reasons}, v


def test_clean_site_passes_and_records_verdicts():
    ids, v = check(site())
    assert ids == set() and v.decision == "fetched"
    entry = v.manifest_entry()
    for key in ("robots", "tdmrep", "x_robots", "meta_noai", "ai_txt", "content_sha256", "user_agent"):
        assert key in entry
    assert entry["robots"] == "allow"


@pytest.mark.parametrize(
    "robots",
    [
        "User-agent: GPTBot\nDisallow: /\n",
        "User-agent: *\nDisallow: /\n",
        "User-agent: mobility-model-zoo-crawler\nDisallow: /a\n",
    ],
)
def test_robots_disallow(robots):
    assert check(site(robots=(200, robots)))[0] == {"C-F1"}


def test_robots_unreachable_or_forbidden_blocks():
    assert check(site(robots_error=True))[0] == {"C-F1"}
    assert check(site(robots=(503, "")))[0] == {"C-F1"}
    assert check(site(robots=(403, "")))[0] == {"C-F1"}


def test_robots_404_means_allowed():
    assert check(site(robots=(404, "")))[0] == set()


def test_tdm_reservation_file_header_and_meta():
    assert check(site(tdm=[{"location": "/", "tdm-reservation": 1}]))[0] == {"C-F2"}
    assert check(site(page=(200, PAGE, {"tdm-reservation": "1"})))[0] == {"C-F2"}
    meta = PAGE.replace("<title>", '<meta name="tdm-reservation" content="1"><title>')
    assert check(site(page=(200, meta, {})))[0] == {"C-F2"}


def test_noai_header_and_meta():
    assert check(site(page=(200, PAGE, {"x-robots-tag": "noai"})))[0] == {"C-F3"}
    meta = PAGE.replace("<title>", '<meta name="robots" content="index, noai"><title>')
    assert check(site(page=(200, meta, {})))[0] == {"C-F3"}


def test_ai_txt_disallow():
    assert check(site(ai_txt="User-agent: *\nDisallow: /\n"))[0] == {"C-F4"}


def test_deny_and_piracy_lists():
    assert check(site(), url="https://blocked.example/x")[0] == {"C-F5"}
    assert check(site(), url="https://www.libgen.example/book")[0] == {"C-F5"}


def test_suppressed_url():
    lists = signals.Lists(suppressed_url_hashes={"h"})
    v, _ = signals.check_url("https://news.example/a", lists, site(), url_hash=lambda u: "h")
    assert {c for c, _ in v.reasons} == {"C-F5"}


def test_terms_are_flagged():
    _, v = check(
        site(tos="Automated scraping and text and data mining are prohibited."),
        tos_url="https://news.example/terms",
    )
    assert v.tos_flag and v.tos_sha256


def test_access_barriers():
    assert check(site(page=(402, "pay", {})))[0] == {"C-F7"}
    login = PAGE.replace("<body>", '<body><form><input type="password"></form>')
    assert check(site(page=(200, login, {})))[0] == {"C-F7"}
