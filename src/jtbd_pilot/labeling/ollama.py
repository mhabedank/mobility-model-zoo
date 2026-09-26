"""Local models through Ollama: teacher candidates and baselines on the Spark, perf runs on the VM.

Schema-constrained decoding (`format` = JSON Schema), temperature 0. The model digest is recorded,
so performance runs can prove they used the identical model file.
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

from jtbd_pilot.config import ModelEntry, Settings
from jtbd_pilot.errors import BackendFailure, UsageError
from jtbd_pilot.labeling.base import CallResult, parse_json_text

HOST_ENV = {"spark": "OLLAMA_HOST", "vm": "OLLAMA_HOST_VM"}


def resolve_host(host: str) -> str:
    if host.startswith("http"):
        return host.rstrip("/")
    env = HOST_ENV.get(host)
    value = os.environ.get(env) if env else None
    if not value:
        raise UsageError(f"no Ollama URL for host {host!r}; set {env or 'a URL'} in .env")
    return value.rstrip("/")


def model_digest(base_url: str, model: str) -> str:
    response = httpx.get(f"{base_url}/api/tags", timeout=30)
    response.raise_for_status()
    for entry in response.json().get("models", []):
        if entry.get("name") == model or entry.get("model") == model:
            return entry["digest"]
    raise UsageError(f"model {model} is not pulled on {base_url}")


def model_details(base_url: str, model: str) -> dict[str, Any]:
    response = httpx.post(f"{base_url}/api/show", json={"model": model}, timeout=30)
    response.raise_for_status()
    return response.json().get("details", {})


class OllamaBackend:
    name = "ollama"
    temperature = 0.0
    structured_output = "json_schema_grammar"

    def __init__(self, settings: Settings, entry: ModelEntry, host: str | None):
        if not entry.api_model:
            raise UsageError(f"set api_model for {entry.model_id} in configs/models.yaml")
        self.entry = entry
        self.host_name = host or entry.host
        self.base_url = resolve_host(self.host_name)
        self.num_ctx = int(entry.extra.get("num_ctx", 16384))
        self.digest = model_digest(self.base_url, entry.api_model)
        details = model_details(self.base_url, entry.api_model)
        self.quantization = details.get("quantization_level") or entry.quantization
        self.deviations: list[str] = []
        self.client = httpx.Client(timeout=1800)

    def call(self, system: str, user: str, schema: dict, chunk_id: str) -> CallResult:
        payload = {
            "model": self.entry.api_model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "format": schema,
            "stream": False,
            "options": {"temperature": 0, "num_ctx": self.num_ctx, "seed": 0},
        }
        if "think" in self.entry.extra:
            payload["think"] = bool(self.entry.extra["think"])
        start = time.monotonic()
        try:
            response = self.client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise BackendFailure(f"Ollama call failed on {chunk_id}: {exc}") from exc
        latency = (time.monotonic() - start) * 1000
        body = response.json()
        text = (body.get("message") or {}).get("content")
        return CallResult(
            raw_body=body,
            parsed_candidate=parse_json_text(text),
            model_version=self.digest,
            usage={"prompt_tokens": body.get("prompt_eval_count"),
                   "completion_tokens": body.get("eval_count"),
                   "eval_duration_ns": body.get("eval_duration"),
                   "total_duration_ns": body.get("total_duration")},
            meta={"host": self.host_name},
            cost_eur=0.0,
            latency_ms=latency,
        )
