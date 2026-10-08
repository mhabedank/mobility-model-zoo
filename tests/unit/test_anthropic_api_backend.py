"""Anthropic API backend with a fake client: structured output, usage, refusals (no paid calls)."""

from types import SimpleNamespace

import pytest

from mobility_model_zoo.productdev.jtbd.config import ModelEntry
from mobility_model_zoo.productdev.jtbd.errors import BackendFailure

pytest.importorskip("anthropic")


class FakeMessages:
    def __init__(self, response):
        self.response, self.calls = response, []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def _response(stop="end_turn", text='{"relevant": true, "items": []}'):
    usage = SimpleNamespace(input_tokens=100, output_tokens=20, to_dict=lambda: {"input_tokens": 100})
    return SimpleNamespace(
        stop_reason=stop, stop_details=SimpleNamespace(category="cyber") if stop == "refusal" else None,
        content=[SimpleNamespace(type="text", text=text)], usage=usage, model="claude-opus-5-5",
        _request_id="req_1", to_dict=lambda: {"id": "msg_1"})


def _backend(response):
    from mobility_model_zoo.productdev.jtbd.labeling.anthropic_api import AnthropicApiBackend

    settings = SimpleNamespace(pilot={}, budget=lambda: {"usd_to_eur": 1.0, "prices": {}})
    entry = ModelEntry(model_id="claude-api-reference", family="anthropic-claude",
                       backend="anthropic_api", host="api", role="reference")
    fake = SimpleNamespace(messages=FakeMessages(response))
    return AnthropicApiBackend(settings, entry, client=fake), fake.messages


def test_structured_output_request_and_result():
    backend, messages = _backend(_response())
    result = backend.call("system", "text", {"type": "object"}, "ch-1")
    call = messages.calls[0]
    assert call["model"] == "claude-opus-5-5"
    assert call["output_config"]["format"] == {"type": "json_schema", "schema": {"type": "object"}}
    assert result.parsed_candidate == {"relevant": True, "items": []}
    assert result.model_version == "claude-opus-5-5" and result.meta["provider"] == "anthropic"


def test_refusal_is_a_backend_failure():
    backend, _ = _backend(_response(stop="refusal"))
    with pytest.raises(BackendFailure, match="refused"):
        backend.call("system", "text", {}, "ch-1")
