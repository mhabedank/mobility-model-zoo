"""Scanner patterns: technical text from the imported edge material is not PII (feature 005)."""

import pytest

from mobility_model_zoo.compliance.scan import pii


@pytest.mark.parametrize(
    "text",
    [
        "accelerometer + gyroscope @50 Hz",
        "Person detect 73 ms @360 MHz",
        "#3 INFER can_ids_mlp 00112233…",
    ],
)
def test_technical_text_is_not_pii(text):
    assert pii(text) == []


@pytest.mark.parametrize("text", ["contact @jane_doe on the forum", "call 0049 30 1234 5678"])
def test_real_identifiers_still_found(text):
    assert pii(text)
