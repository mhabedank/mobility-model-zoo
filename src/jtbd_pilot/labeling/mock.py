"""Replays fixture answers from <mock dir>/<model_id>/<chunk_id>.json (tests and dry runs only).

A fixture file may contain {"__raw__": "..."} to simulate a non-JSON answer.
"""

from __future__ import annotations

import json

from jtbd_pilot.config import ModelEntry, Settings
from jtbd_pilot.errors import BackendFailure, UsageError
from jtbd_pilot.labeling.base import CallResult, parse_json_text


class MockBackend:
    name = "mock"
    temperature = 0.0
    structured_output = "post_validation"

    def __init__(self, settings: Settings, entry: ModelEntry):
        if "mock" not in settings.paths:
            raise UsageError("mock backend needs paths.mock in the config")
        self.directory = settings.paths["mock"] / entry.model_id
        self.entry = entry
        self.deviations = ["mock backend: fixture replay, not a real model"]

    def call(self, system: str, user: str, schema: dict, chunk_id: str) -> CallResult:
        path = self.directory / f"{chunk_id}.json"
        if not path.exists():
            raise BackendFailure(f"no mock answer for {self.entry.model_id}/{chunk_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "__raw__" in data:
            text = data["__raw__"]
        else:
            text = json.dumps(data, ensure_ascii=False)
        return CallResult(
            raw_body={"content": text},
            parsed_candidate=parse_json_text(text),
            model_version=f"mock-{self.entry.model_id}",
            usage={"prompt_tokens": len(system + user) // 4, "completion_tokens": len(text) // 4},
            cost_eur=0.0,
            latency_ms=1.0,
        )
