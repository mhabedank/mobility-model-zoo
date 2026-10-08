import json

from mobility_model_zoo.compliance import recipients


def _run(base, run_id, backend, model_id, role, raws, host="openrouter"):
    d = base / run_id
    (d / "raw").mkdir(parents=True)
    (d / "manifest.json").write_text(
        json.dumps(
            {"run_id": run_id, "backend": backend, "model_id": model_id, "role": role, "host": host}
        )
    )
    for i, raw in enumerate(raws):
        (d / "raw" / f"chunk-{i}.a1.json").write_text(
            json.dumps(
                {"chunk_id": f"chunk-{i}", "attempt": 1, "raw_body": {"text": "Erika Mustermann"}, **raw}
            )
        )


def test_collect_groups_by_provider_without_text(tmp_path):
    _run(
        tmp_path,
        "run-a",
        "openrouter",
        "teacher-x",
        "teacher",
        [
            {"request_ts": "2026-10-01T10:00:00Z", "backend_meta": {"provider": "DeepInfra"}},
            {"request_ts": "2026-10-02T10:00:00Z", "backend_meta": {"provider": "DeepInfra"}},
            {"request_ts": "2026-10-02T11:00:00Z", "error": "timeout"},
        ],
    )
    _run(
        tmp_path,
        "run-b",
        "ollama",
        "local-y",
        "baseline",
        [{"request_ts": "2026-10-03T10:00:00Z", "backend_meta": {"host": "spark"}}],
        host="spark",
    )
    recs = recipients.collect([tmp_path])
    by = {(r["model_id"], r["hosting_provider"]): r for r in recs}
    assert by[("teacher-x", "DeepInfra")]["calls_ok"] == 2
    assert by[("teacher-x", "unrecorded")]["calls_error"] == 1
    assert by[("local-y", "local:spark")]["roles"] == ["baseline"]
    dumped = json.dumps(recs)
    assert "chunk" not in dumped and "Mustermann" not in dumped


def test_assign_routes(tmp_path):
    recs = [
        {"model_id": "m", "backend": "openrouter", "hosting_provider": "DeepInfra"},
        {"model_id": "m", "backend": "openrouter", "hosting_provider": "Other"},
    ]
    recipients.assign_routes(recs, [{"id": "m-deepinfra", "log_matches": ["m|openrouter|DeepInfra"]}])
    assert [r["route_id"] for r in recs] == ["m-deepinfra", "unregistered"]
