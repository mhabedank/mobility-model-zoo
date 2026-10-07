"""Feature 004 adds roles and a backend but leaves the frozen LLM output schema unchanged (T014)."""

from mobility_model_zoo.productdev.jtbd.freeze import schema_sha256

# schema_sha256() before feature 004 (commit 7260dfa).
FROZEN = "e9a8a5fed9ed57a9b91f1d186a1062389497ca2d7e386d75dfab19633be8b67e"


def test_output_schema_hash_is_unchanged():
    assert schema_sha256() == FROZEN
