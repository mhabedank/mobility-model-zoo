"""Encoders and the embedding cache (feature 009, T013). No model is downloaded."""

import numpy as np
import pytest
from cluster_helpers import FIXTURE

from mobility_model_zoo.productdev.jtbd.cluster.embed import (
    EmbeddingCache,
    HFEncoder,
    TableEncoder,
    make_encoder,
    variant_of,
)
from mobility_model_zoo.productdev.jtbd.errors import UsageError


class CountingEncoder(TableEncoder):
    def __init__(self):
        super().__init__({}, dim=8)
        self.calls: list[list[str]] = []

    def embed(self, quotes):
        self.calls.append(list(quotes))
        return super().embed(quotes)


def test_table_encoder_rows_are_normalised_and_seeded():
    enc = TableEncoder.from_file(FIXTURE / "vectors.json")
    v = enc.embed(["The bus is always late.", "a quote not in the table"])
    assert v.dtype == np.float32
    assert np.allclose(np.linalg.norm(v, axis=1), 1.0, atol=1e-6)
    assert np.array_equal(v, enc.embed(["The bus is always late.", "a quote not in the table"]))


def test_cache_embeds_only_new_quotes_and_reuses_bytes(tmp_path):
    enc = CountingEncoder()
    cache = EmbeddingCache(tmp_path, enc.model_id, enc.revision)
    first = cache.get(["A", "B", "A"], enc)
    assert enc.calls == [["A", "B"]]
    again = EmbeddingCache(tmp_path, enc.model_id, enc.revision)
    second = again.get(["B", "A", "C"], enc)
    assert enc.calls[-1] == ["C"]
    assert second[0].tobytes() == first[1].tobytes()
    assert second[1].tobytes() == first[0].tobytes()


def test_changed_revision_misses_the_cache(tmp_path):
    enc = CountingEncoder()
    EmbeddingCache(tmp_path, enc.model_id, "r1").get(["A"], enc)
    EmbeddingCache(tmp_path, enc.model_id, "r2").get(["A"], enc)
    assert enc.calls == [["A"], ["A"]]


def test_cache_key_uses_the_normalised_quote(tmp_path):
    enc = CountingEncoder()
    EmbeddingCache(None, enc.model_id, enc.revision).get(["The bus is late.", "the bus is late"], enc)
    assert enc.calls == [["The bus is late."]]


@pytest.mark.parametrize("missing", ["revision", "licence_basis"])
def test_real_encoder_needs_pinned_revision_and_licence(missing):
    settings = {"model_id": "intfloat/multilingual-e5-base", "revision": "abc",
                "licence_basis": "MIT"}
    settings[missing] = None
    with pytest.raises(UsageError, match=missing):
        HFEncoder(settings)
    with pytest.raises(UsageError, match=missing):
        make_encoder(settings)


def test_remote_code_needs_a_pinned_code_revision():
    settings = {"model_id": "Alibaba-NLP/gte-multilingual-base", "revision": "abc",
                "licence_basis": "Apache-2.0", "trust_remote_code": True}
    with pytest.raises(UsageError, match="code_revision"):
        HFEncoder(settings)


def test_cache_variant_separates_pooling_and_prefix(tmp_path):
    enc = CountingEncoder()
    EmbeddingCache(tmp_path, enc.model_id, "r1", variant_of({"pooling": "mean"})).get(["A"], enc)
    EmbeddingCache(tmp_path, enc.model_id, "r1", variant_of({"pooling": "cls"})).get(["A"], enc)
    EmbeddingCache(tmp_path, enc.model_id, "r1", variant_of({"pooling": "cls"})).get(["A"], enc)
    assert enc.calls == [["A"], ["A"]]
    assert variant_of({}) == ""


def test_table_backend_resolves_relative_to_settings():
    enc = make_encoder({"backend": "table", "table": "vectors.json"}, base=FIXTURE)
    assert isinstance(enc, TableEncoder) and enc.dim == 32
