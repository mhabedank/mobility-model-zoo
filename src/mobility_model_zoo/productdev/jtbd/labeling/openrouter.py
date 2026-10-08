"""GPT reference labeler through OpenRouter (research.md R1, R8).

Fixed provider without fallbacks, strict JSON-schema output, temperature 0 (unless the model takes
no temperature, recorded as a deviation), no data collection.
"""

from __future__ import annotations

import os
import time

from mobility_model_zoo.productdev.jtbd.config import ModelEntry, Settings
from mobility_model_zoo.productdev.jtbd.errors import BackendFailure, UsageError
from mobility_model_zoo.productdev.jtbd.labeling.base import CallResult, parse_json_text

BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterBackend:
    name = "openrouter"
    temperature = 0.0
    structured_output = "json_schema_strict"

    def __init__(self, settings: Settings, entry: ModelEntry):
        from openai import OpenAI

        key_env = settings.budget().get("api_key_env", "OPENROUTER_API_KEY")
        key = os.environ.get(key_env)
        if not key:
            raise UsageError(f"{key_env} is not set (see .env.example)")
        if not entry.api_model:
            raise UsageError(f"set api_model (OpenRouter slug) for {entry.model_id} (T046)")
        self.entry = entry
        self.client = OpenAI(base_url=BASE_URL, api_key=key)
        budget = settings.budget()
        self.usd_to_eur = float(budget.get("usd_to_eur", 1.0))
        self.price = (budget.get("prices") or {}).get(entry.model_id) or {}
        self.max_tokens = int(entry.extra.get("max_output_tokens")
                              or settings.pilot.get("max_output_tokens", 4096))
        self.deviations: list[str] = []
        self.provider = {
            "allow_fallbacks": False,
            "require_parameters": True,
            "data_collection": "deny",
        }
        order = entry.extra.get("provider_order", ["openai"])
        if not order:
            # Compliance harness (C-P5, decision D-routing): texts only go to a pinned provider.
            raise UsageError(f"{entry.model_id}: provider_order is not pinned; OpenRouter would pick "
                             "a provider per request (not allowed since feature 006)")
        self.provider["order"] = order
        if entry.extra.get("quantizations"):
            self.provider["quantizations"] = entry.extra["quantizations"]
        if "temperature" in entry.extra and entry.extra["temperature"] is None:
            # Reasoning models such as the GPT-5 family take no temperature; with
            # require_parameters every endpoint would be filtered out.
            self.temperature = "not_settable"
            self.deviations.append(f"{entry.model_id}: no temperature parameter (not supported "
                                   "by the model); provider default sampling")

    def _cost_from_prices(self, usage) -> float:
        if not self.price or self.price.get("input") is None:
            return 0.0
        details = getattr(usage, "prompt_tokens_details", None)
        cached = (getattr(details, "cached_tokens", 0) or 0) if details else 0
        prompt = usage.prompt_tokens or 0
        cached_price = self.price.get("cached_input") or self.price["input"]
        return (
            (prompt - cached) * self.price["input"]
            + cached * cached_price
            + (usage.completion_tokens or 0) * self.price["output"]
        ) / 1_000_000

    def call(self, system: str, user: str, schema: dict, chunk_id: str) -> CallResult:
        extra_body = {"provider": self.provider, "usage": {"include": True}}
        effort = self.entry.extra.get("reasoning_effort")
        if effort:
            extra_body["reasoning"] = {"effort": effort}
        if self.entry.extra.get("reasoning") is not None:
            # e.g. {enabled: false}: teacher candidates answer without a thinking phase, like the
            # local teachers (think: false), so reasoning tokens cannot eat the output budget.
            extra_body["reasoning"] = self.entry.extra["reasoning"]
        sampling = {} if self.temperature == "not_settable" else {"temperature": self.temperature}
        start = time.monotonic()
        try:
            response = self.client.chat.completions.create(
                model=self.entry.api_model,
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}],
                **sampling,
                max_tokens=self.max_tokens,
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "extraction_output", "strict": True,
                                    "schema": schema},
                },
                extra_body=extra_body,
            )
        except Exception as exc:  # noqa: BLE001 - surface any client/API error as backend failure
            raise BackendFailure(f"OpenRouter call failed on {chunk_id}: {exc}") from exc
        latency = (time.monotonic() - start) * 1000
        text = response.choices[0].message.content if response.choices else None
        usage = response.usage
        reported_usd = getattr(usage, "cost", None) if usage else None
        cost_eur = (float(reported_usd) * self.usd_to_eur if reported_usd is not None
                    else self._cost_from_prices(usage) if usage else 0.0)
        return CallResult(
            raw_body=response.model_dump(),
            parsed_candidate=parse_json_text(text),
            model_version=response.model or self.entry.api_model,
            usage=usage.model_dump() if usage else {},
            meta={"generation_id": response.id, "provider": getattr(response, "provider", None)},
            cost_eur=cost_eur,
            latency_ms=latency,
        )
