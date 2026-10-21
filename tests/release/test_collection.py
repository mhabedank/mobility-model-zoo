"""Topic collection before the first card (feature 021, T051; research R12)."""

from mobility_model_zoo.release import publish as ops

MODEL = {"topic": "productdev", "repos": {"public": "mobility-model-zoo/x"}, "summary": "an x"}


def _quiet(*_):
    pass


def _slug(reg):
    return next(t for t in reg.topics() if t["id"] == "productdev")["hf_collection"]


def test_init_creates_a_private_collection_and_records_its_slug(zoo_env):
    slug = ops.ensure_topic_collection(zoo_env.reg, MODEL, zoo_env.hub, _quiet)
    assert _slug(zoo_env.reg) == slug
    assert zoo_env.hub.collections[slug]["private"] is True
    assert zoo_env.hub.collections[slug]["items"] == []


def test_an_existing_collection_changes_nothing(zoo_env):
    slug = ops.ensure_topic_collection(zoo_env.reg, MODEL, zoo_env.hub, _quiet)
    zoo_env.hub.writes.clear()
    before = (zoo_env.root / "zoo/topics.yaml").read_text()
    assert ops.ensure_topic_collection(zoo_env.reg, MODEL, zoo_env.hub, _quiet) == slug
    assert zoo_env.hub.writes == []
    assert (zoo_env.root / "zoo/topics.yaml").read_text() == before


def test_publish_makes_the_private_collection_public_with_its_first_model(zoo_env):
    slug = ops.ensure_topic_collection(zoo_env.reg, MODEL, zoo_env.hub, _quiet)
    ops.add_to_collection(zoo_env.reg, MODEL, zoo_env.hub, _quiet)
    assert zoo_env.hub.collections[slug]["private"] is False
    assert zoo_env.hub.collections[slug]["items"] == [("mobility-model-zoo/x", "an x")]
    zoo_env.hub.writes.clear()
    ops.add_to_collection(zoo_env.reg, {**MODEL, "repos": {"public": "o/y"}}, zoo_env.hub, _quiet)
    assert not [w for w in zoo_env.hub.writes if w.startswith("collection-public")]


def test_sandbox_models_get_no_collection(zoo_env):
    ops.init_model(zoo_env.reg, zoo_env.model, zoo_env.hub, _quiet)
    assert zoo_env.hub.collections == {}
