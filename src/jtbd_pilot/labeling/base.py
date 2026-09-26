"""Backend interface shared by claude_cli, openrouter, ollama and mock."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from jtbd_pilot.config import ModelEntry, Settings


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
    """Decode a model's text answer as JSON, tolerating a surrounding code fence."""
    if text is None:
        return None
    candidate = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", candidate, re.DOTALL)
    if fence:
        candidate = fence.group(1)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def make_backend(settings: Settings, entry: ModelEntry, backend: str, host: str | None) -> Backend:
    if backend != entry.backend:
        from jtbd_pilot.errors import UsageError

        raise UsageError(f"model {entry.model_id} is configured for backend {entry.backend}, "
                         f"not {backend}")
    if backend == "claude_cli":
        from jtbd_pilot.labeling.claude_cli import ClaudeCliBackend

        return ClaudeCliBackend(settings, entry)
    if backend == "openrouter":
        from jtbd_pilot.labeling.openrouter import OpenRouterBackend

        return OpenRouterBackend(settings, entry)
    if backend == "ollama":
        from jtbd_pilot.labeling.ollama import OllamaBackend

        return OllamaBackend(settings, entry, host)
    if backend == "mock":
        from jtbd_pilot.labeling.mock import MockBackend

        return MockBackend(settings, entry)
    from jtbd_pilot.errors import UsageError

    raise UsageError(f"unknown backend {backend}")
