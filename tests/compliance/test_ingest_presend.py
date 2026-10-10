"""Ingest (C-I1 … C-I7) and pre-send / post-receive (C-P1 … C-P6) checks."""

from compliance_helpers import load, route, seed, source, write

from mobility_model_zoo.compliance.ingest import check_snapshots, window_allowed
from mobility_model_zoo.compliance.presend import check_answer, check_batch, route_allows

LEX = {"categories": {"health": ["rollstuhl", "krankheit"]}}


def snap(origin="https://example.org/paper-one", use="train", stype="paper"):
    return {"snapshot_id": "s1", "origin_url": origin, "source_type": stype, "use": use}


def ingest_ids(root, snaps):
    write(root, "compliance/lists/licence-allowlist.yaml", {"licences": [{"id": "CC-BY-4.0"}]})
    return {f.check_id for f in check_snapshots(load(root), snaps)}


def test_clean_ingest(register_tree):
    assert ingest_ids(register_tree, [snap()]) == set()


def test_missing_record(register_tree):
    assert ingest_ids(register_tree, [snap(origin="https://example.org/unknown")]) == {"C-I1"}


def test_nc_licence_for_training(register_tree):
    seed(
        register_tree,
        "topics/t/compliance/sources.yaml",
        lambda d: d["sources"][0].update(licence="CC-BY-NC-4.0", permitted_use="benchmark_only"),
    )
    assert ingest_ids(register_tree, [snap()]) == {"C-I2"}


def test_nc_licence_trains_non_commercial_models_only(register_tree):
    # constitution 2.1.0: NC data may train NC models (feature 011)
    seed(register_tree, "topics/t/compliance/sources.yaml",
         lambda d: d["sources"][0].update(licence="CC-BY-NC-4.0"))
    write(register_tree, "compliance/lists/licence-allowlist.yaml",
          {"licences": [{"id": "CC-BY-4.0"}, {"id": "CC-BY-NC-4.0", "non_commercial": True}]})
    reg = load(register_tree)
    assert {f.check_id for f in check_snapshots(reg, [snap()])} == {"C-I2"}
    assert check_snapshots(reg, [snap()], usage_class="non-commercial") == []


def test_human_subjects_without_consent(register_tree):
    seed(
        register_tree,
        "topics/t/compliance/sources.yaml",
        lambda d: d["sources"][0]["personal_data"].update(
            human_subjects=True, consent_or_ethics="unknown"
        ),
    )
    assert ingest_ids(register_tree, [snap()]) == {"C-I4"}


def test_reddit_without_platform_terms(register_tree):
    write(
        register_tree,
        "topics/t/compliance/sources.yaml",
        {"sources": [source(origin_url="https://www.reddit.com/comments/abc", id="reddit-abc")]},
    )
    assert "C-I7" in ingest_ids(register_tree, [snap(origin="https://www.reddit.com/comments/abc")])


def test_special_category_window_is_excluded(register_tree):
    write(register_tree, "compliance/lists/special-categories.yaml", LEX)
    reg = load(register_tree)
    assert not window_allowed(reg, "https://example.org/paper-one", "Ich sitze im Rollstuhl.")
    assert window_allowed(reg, "https://example.org/paper-one", "Der Bus kommt spät.")


def batch(root, items, backend="ollama", route_id="local-model", order=None, role="teacher"):
    return {
        f.check_id
        for f in check_batch(
            load(root),
            model_id="m",
            backend=backend,
            role=role,
            route_id=route_id,
            provider_order=order,
            items=items,
            current_patterns="redact-v2",
        )
    }


def test_presend_clean(register_tree):
    assert batch(register_tree, [("ch-1", "Der Bus kommt spät.", "redact-v1")]) == set()


def test_presend_unredacted_and_pii(register_tree):
    assert batch(register_tree, [("ch-1", "text", None)]) == {"C-P1"}
    assert batch(register_tree, [("ch-1", "Mail an lena.beispiel@posteo.de", "redact-v2")]) == {"C-P2"}


def test_presend_quarantined(register_tree):
    (register_tree / "data/compliance").mkdir(parents=True)
    (register_tree / "data/compliance/quarantine.jsonl").write_text('{"chunk_id": "ch-1"}\n')
    assert batch(register_tree, [("ch-1", "text", "redact-v2")]) == {"C-P3"}


def test_presend_routes(register_tree):
    write(
        register_tree,
        "compliance/providers.yaml",
        {
            "routes": [
                route(),
                route(id="cli", access_path="consumer_cli", allowed_for=[]),
                route(
                    id="or",
                    access_path="openrouter",
                    region="US",
                    dpf_listed=False,
                    dpa=True,
                    scc=True,
                    zero_data_retention=True,
                    training_on_inputs=False,
                    allowed_for=["teacher"],
                    signoff={"by": "o", "at": "2026-10-08"},
                    openrouter_provider="DeepInfra",
                ),
            ]
        },
    )
    item = [("ch-1", "text", "redact-v2")]
    assert batch(register_tree, item, route_id=None) == {"C-P4"}
    assert batch(register_tree, item, backend="claude_cli", route_id="cli") == {"C-P4"}
    assert batch(register_tree, item, backend="openrouter", route_id="or", order=None) == {"C-P5"}
    assert batch(register_tree, item, backend="openrouter", route_id="or", order=["deepinfra"]) == set()
    assert batch(register_tree, item, backend="mock", route_id=None) == set()


def test_route_allow_rule():
    hosted = route(
        id="h",
        access_path="api",
        region="US",
        dpf_listed=False,
        dpa=True,
        scc=False,
        zero_data_retention=True,
        training_on_inputs=False,
        allowed_for=["teacher"],
        signoff={"by": "o", "at": "2026-10-08"},
    )
    assert not route_allows(hosted, "teacher")[0]
    assert route_allows({**hosted, "scc": True}, "teacher")[0]
    assert not route_allows({**hosted, "scc": True, "zero_data_retention": False}, "teacher")[0]


def test_post_receive_provider_mismatch():
    r = {"id": "or", "openrouter_provider": "DeepInfra"}
    assert check_answer(r, "openrouter", {"provider": "DeepInfra"}) is None
    assert check_answer(r, "openrouter", {"provider": "Other"}).check_id == "C-P6"
