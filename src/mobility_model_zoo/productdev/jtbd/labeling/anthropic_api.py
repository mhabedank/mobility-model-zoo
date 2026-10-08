"""Anthropic API backend (feature 006, decision D-claude-api): reference labels under the Commercial
Terms and the data processing addendum, instead of the consumer subscription.

The route `claude-api` in compliance/providers.yaml stays blocked (`allowed_for: []`) until the owner
records the DPA and the commercial terms check; the pre-send check refuses runs before that.

Refusals are recorded as backend failures. Server-side model fallbacks are deliberately not used:
a fallback would label with a different model than the run records.
"""

from __future__ import annotations

import time

from mobility_model_zoo.productdev.jtbd.config import ModelEntry, Settings
from mobility_model_zoo.productdev.jtbd.errors import BackendFailure, UsageError
from mobility_model_zoo.productdev.jtbd.labeling.base import CallResult, parse_json_text

DEFAULT_MODEL = "claude-opus-5-5"


class AnthropicApiBackend:
    name = "anthropic_api"
    structured_output = "output_config.format json_schema"

    def __init__(self, settings: Settings, entry: ModelEntry, client=None):
        try:
            import anthropic
        except ImportError as exc:  # optional dependency
            raise UsageError("install the labeling-api extra: uv sync --extra labeling-api") from exc
        self.entry = entry
        self.client = client or anthropic.Anthropic(timeout=float(entry.extra.get("timeout_s", 600)))
        self.model = entry.api_model or DEFAULT_MODEL
        self.effort = entry.extra.get("effort", "medium")
        self.max_tokens = int(entry.extra.get("max_output_tokens")
                              or settings.pilot.get("max_output_tokens", 16000))
        budget = settings.budget()
        self.usd_to_eur = float(budget.get("usd_to_eur", 1.0))
        self.price = (budget.get("prices") or {}).get(entry.model_id) or {}
        self.temperature = "not_settable"  # sampling parameters are not accepted on this model
        self.deviations: list[str] = []

    def _cost(self, usage) -> float:
        if not self.price or self.price.get("input") is None or usage is None:
            return 0.0
        return ((usage.input_tokens or 0) * self.price["input"]
                + (usage.output_tokens or 0) * self.price["output"]) / 1_000_000 * self.usd_to_eur

    def call(self, system: str, user: str, schema: dict, chunk_id: str) -> CallResult:
        import anthropic

        start = time.monotonic()
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_config={"effort": self.effort,
                               "format": {"type": "json_schema", "schema": schema}},
            )
        except anthropic.APIError as exc:
            raise BackendFailure(f"Anthropic API call failed on {chunk_id}: {exc}") from exc
        latency = (time.monotonic() - start) * 1000
        if response.stop_reason == "refusal":
            details = response.stop_details
            category = getattr(details, "category", None) if details else None
            raise BackendFailure(f"Anthropic API refused {chunk_id} (category {category})")
        text = next((b.text for b in response.content if b.type == "text"), None)
        usage = response.usage
        return CallResult(
            raw_body=response.to_dict(),
            parsed_candidate=parse_json_text(text),
            model_version=response.model,
            usage=usage.to_dict() if usage else {},
            meta={"request_id": response._request_id, "provider": "anthropic"},
            cost_eur=self._cost(usage),
            latency_ms=latency,
        )
