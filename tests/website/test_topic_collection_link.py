"""The website links a topic collection only once a model of the topic is published (feature 021, R12).

`zoo init-model` creates a new topic's collection private; a link to it before the first publication
answers 401 and fails the link check (L2).
"""

from pathlib import Path

from mobility_model_zoo.release.registry import Registry
from mobility_model_zoo.site.build import site_topic

REPO = Path(__file__).resolve().parents[2]


def test_unpublished_topic_has_no_collection_link():
    reg = Registry(REPO)
    topic = {"id": "no-such-topic", "title": "T", "hf_collection": "org/private-1"}
    assert site_topic(reg, topic)["hf_collection"] is None


def test_published_topic_keeps_its_collection_link():
    reg = Registry(REPO)
    published = next(reg.model_raw(n)["topic"] for n in reg.model_names() if reg.published_versions(n))
    topic = {"id": published, "title": "T", "hf_collection": "org/public-1"}
    assert site_topic(reg, topic)["hf_collection"] == "org/public-1"
