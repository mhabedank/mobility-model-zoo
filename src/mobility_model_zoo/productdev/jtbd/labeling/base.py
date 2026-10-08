"""Backend interface shared by claude_cli, openrouter, ollama and mock."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from mobility_model_zoo.productdev.jtbd.config import ModelEntry, Settings


@dataclass
class CallResult:
    raw_body: Any
    parsed_candidate: Any | None  # JSON-decoded model output, or None if not JSON
    model_version: str
    usage: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)
    cost_eur: float = 0.0
    latency_ms: float = 0.0


class Backend(Protocol):
    name: str
    temperature: float | str
    structured_output: str
    deviations: list[str]

    def call(self, system: str, user: str, schema: dict, chunk_id: str) -> CallResult: ...


def parse_json_text(text: str | None) -> Any | None:
    """Decode a model's text answer as JSON, tolerating a surrounding code fence and a leading
    (usually empty) `<think>...</think>` block, which Qwen3 chat templates teach fine-tuned models."""
    if text is None:
        return None
    candidate = text.strip()
    if "</think>" in candidate:
        candidate = candidate.split("</think>", 1)[1].strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", candidate, re.DOTALL)
    if fence:
        candidate = fence.group(1)
    try:
        # strict=False: accept a raw line break inside a string (small fine-tuned models emit them
        # when quotes span PDF line breaks); the content is the same.
        return json.loads(candidate, strict=False)
    except json.JSONDecodeError:
        return None


def make_backend(settings: Settings, entry: ModelEntry, backend: str, host: str | None) -> Backend:
    if backend != entry.backend:
        from mobility_model_zoo.productdev.jtbd.errors import UsageError

        raise UsageError(f"model {entry.model_id} is configured for backend {entry.backend}, "
                         f"not {backend}")
    if backend == "claude_cli":
        from mobility_model_zoo.productdev.jtbd.labeling.claude_cli import ClaudeCliBackend

        return ClaudeCliBackend(settings, entry)
    if backend == "anthropic_api":
        from mobility_model_zoo.productdev.jtbd.labeling.anthropic_api import AnthropicApiBackend

        return AnthropicApiBackend(settings, entry)
    if backend == "openrouter":
        from mobility_model_zoo.productdev.jtbd.labeling.openrouter import OpenRouterBackend

        return OpenRouterBackend(settings, entry)
    if backend == "ollama":
        from mobility_model_zoo.productdev.jtbd.labeling.ollama import OllamaBackend

        return OllamaBackend(settings, entry, host)
    if backend == "openai_compat":
        from mobility_model_zoo.productdev.jtbd.labeling.openai_compat import OpenAICompatBackend

        return OpenAICompatBackend(settings, entry)
    if backend == "mock":
        from mobility_model_zoo.productdev.jtbd.labeling.mock import MockBackend

        return MockBackend(settings, entry)
    from mobility_model_zoo.productdev.jtbd.errors import UsageError

    if backend == "ensemble":
        raise UsageError(f"{entry.model_id} is derived from other runs: use `jtbd ensemble`")

    raise UsageError(f"unknown backend {backend}")
