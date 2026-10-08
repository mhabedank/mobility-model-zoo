"""bootstrap-sources: records from snapshot metadata and mocked Zenodo/Crossref; nothing invented."""

import datetime as dt

import httpx
import yaml
from jsonschema import Draft202012Validator

from mobility_model_zoo.compliance import bootstrap, signals
from mobility_model_zoo.compliance.register import schema


def _snap(root, sid, url, licence, stype, permitted="training_allowed"):
    d = root / "data" / "snapshots" / sid
    d.mkdir(parents=True)
    (d / "source.yaml").write_text(
        yaml.safe_dump(
            {
                "snapshot_id": sid,
                "origin_url": url,
                "source_type": stype,
                "license": licence,
                "permitted_uses": permitted,
                "retention_until": "2028-10-01",
            }
        )
    )


def _meta():
    def handler(req):
        if "zenodo.org/api/records/42" in str(req.url):
            return httpx.Response(
                200,
                json={
                    "metadata": {
                        "title": "Mobility interviews",
                        "creators": [{"name": "Mustermann, Erika"}],
                        "license": {"id": "cc-by-4.0"},
                        "description": "<p>All participants gave informed consent. "
                        "Data are pseudonymised.</p>",
                    }
                },
            )
        if "zenodo.org/api/records/43" in str(req.url):
            return httpx.Response(
                200,
                json={
                    "metadata": {
                        "title": "Other interviews",
                        "creators": [],
                        "description": "Transcripts.",
                    }
                },
            )
        if "api.crossref.org" in str(req.url):
            return httpx.Response(
                200,
                json={
                    "message": {
                        "title": ["A paper"],
                        "publisher": "Example",
                        "author": [{"given": "Max", "family": "Muster"}],
                    }
                },
            )
        return httpx.Response(404)

    return bootstrap.Metadata(httpx.Client(transport=httpx.MockTransport(handler)))


def test_build_records(tmp_path):
    _snap(tmp_path, "snap-1", "https://zenodo.org/records/42", "CC-BY-4.0", "transcript")
    _snap(tmp_path, "snap-2", "https://zenodo.org/records/43", "CC-BY-4.0", "transcript")
    _snap(tmp_path, "snap-3", "https://doi.org/10.1000/xyz", "CC-BY-4.0", "paper")
    _snap(
        tmp_path,
        "snap-4",
        "https://dserver.bundestag.de/btp/20/1.pdf",
        "amtliches Werk § 5 UrhG",
        "transcript",
    )
    _snap(
        tmp_path,
        "snap-5",
        "https://www.motor-talk.de/forum/x.html",
        "none stated (forum posts, authors keep copyright)",
        "forum_review",
        "benchmark_only",
    )
    release = {
        "provenance": {
            "sources": [
                {"origin": u}
                for u in (
                    "https://zenodo.org/records/42",
                    "https://zenodo.org/records/43",
                    "https://doi.org/10.1000/xyz",
                    "https://dserver.bundestag.de/btp/20/1.pdf",
                )
            ]
        }
    }
    verdict = signals.Verdict(url="x", fetched_at="t", robots="allow")
    records, items = bootstrap.build(
        tmp_path,
        model="m",
        version="0.1.1",
        release_record=release,
        benchmark="pilot-v2",
        benchmark_ids={"snap-5"},
        meta=_meta(),
        check=lambda u: verdict,
        today=dt.date(2026, 10, 8),
        used_by_versions=["0.1.1", "0.1.2"],
    )
    errors = list(Draft202012Validator(schema("sources")).iter_errors({"sources": records}))
    assert not errors, errors[0].message
    by = {r["origin_url"]: r for r in records}
    z = by["https://zenodo.org/records/42"]
    assert z["class"] == "research-interviews" and z["creators"] == ["Mustermann, Erika"]
    assert "informed consent" in z["personal_data"]["consent_or_ethics"]
    assert "pseudonymised" in z["personal_data"]["anonymisation"]
    assert by["https://zenodo.org/records/43"]["personal_data"]["consent_or_ethics"] == "unknown"
    assert any("no consent" in i for i in items)
    assert by["https://doi.org/10.1000/xyz"]["creators"] == ["Max Muster"]
    parl = by["https://dserver.bundestag.de/btp/20/1.pdf"]
    assert parl["class"] == "parliamentary-records" and parl["creators"] == ["Deutscher Bundestag"]
    assert parl["licence"] == "LicenseRef-official-work-UrhG-5" and parl["quote_allowed"]
    forum = by["https://www.motor-talk.de/forum/x.html"]
    assert forum["permitted_use"] == "benchmark_only" and forum["used_by"] == ["benchmark:pilot-v2"]
    assert parl["used_by"] == ["m@0.1.1", "m@0.1.2"]


def test_signal_failure_is_an_item(tmp_path):
    _snap(tmp_path, "snap-1", "https://example.org/a", "CC-BY-4.0", "paper")
    release = {"provenance": {"sources": [{"origin": "https://example.org/a"}]}}
    bad = signals.Verdict(url="x", fetched_at="t", robots="deny")
    bad.block("C-F1", "robots.txt disallows GPTBot")
    _, items = bootstrap.build(
        tmp_path,
        model="m",
        version="0.1.1",
        release_record=release,
        benchmark=None,
        benchmark_ids=set(),
        meta=_meta(),
        check=lambda u: bad,
        today=dt.date(2026, 10, 8),
        used_by_versions=["0.1.1"],
    )
    assert any("opt-out signal" in i for i in items)
