"""Model names become C identifiers in the generated firmware sources (feature 005, T030)."""

import pytest

from mobility_model_zoo.edge.int8.codegen import _ident


@pytest.mark.parametrize(
    ("name", "ident"),
    [
        ("picket-mlp", "picket_mlp"),
        ("hum-fan", "hum_fan"),
        ("pace-cnn", "pace_cnn"),
        ("can_ids_mlp", "can_ids_mlp"),
        ("3axis", "m_3axis"),
        ("bär", "b_r"),
    ],
)
def test_model_names_are_c_identifiers(name, ident):
    assert _ident(name) == ident
    assert ident.isidentifier() and ident.isascii()
