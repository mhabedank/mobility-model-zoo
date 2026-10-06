"""OpenRouter requests leave out parameters a model does not take (T058 smoke test, 2026-10-06)."""

from types import SimpleNamespace

from mobility_model_zoo.productdev.jtbd.config import ModelEntry, load_settings
from mobility_model_zoo.productdev.jtbd.labeling.openrouter import OpenRouterBackend


def backend(fixture_dir, monkeypatch, **extra):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test")
    settings = load_settings(fixture_dir / "pilot.yaml")
    entry = ModelEntry(model_id="gpt", family="openai-gpt", backend="openrouter", host="openai",
                       role="reference", api_model="openai/x", extra=extra)
    b = OpenRouterBackend(settings, entry)
    sent = {}

    def create(**kwargs):
        sent.update(kwargs)
        message = SimpleNamespace(content='{"items": []}')
        usage = SimpleNamespace(cost=0.0, prompt_tokens=1, completion_tokens=1,
                                model_dump=lambda: {})
        return SimpleNamespace(id="g", choices=[SimpleNamespace(message=message)],
                               model="openai/x", usage=usage, model_dump=lambda: {})

    b.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    return b, sent


def test_temperature_zero_by_default(fixture_dir, monkeypatch):
    b, sent = backend(fixture_dir, monkeypatch)
    b.call("s", "u", {}, "ch-001")
    assert sent["temperature"] == 0.0 and b.temperature == 0.0 and not b.deviations


def test_a_model_without_temperature_gets_none_and_a_deviation(fixture_dir, monkeypatch):
    b, sent = backend(fixture_dir, monkeypatch, temperature=None)
    b.call("s", "u", {}, "ch-001")
    assert "temperature" not in sent and b.temperature == "not_settable"
    assert any("no temperature" in d for d in b.deviations)
