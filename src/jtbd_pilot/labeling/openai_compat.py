"""Any OpenAI-compatible server without cost, e.g. vLLM on the DGX Spark (spike 002).

Same prompt, JSON-schema response format and temperature 0 for every model served this way, so the
base and the fine-tuned model are compared on equal terms.
"""

from __future__ import annotations

import os
import time

from jtbd_pilot.config import ModelEntry, Settings
from jtbd_pilot.errors import BackendFailure, UsageError
from jtbd_pilot.labeling.base import CallResult, parse_json_text


class OpenAICompatBackend:
    name = "openai_compat"
    temperature = 0.0
    structured_output = "json_schema_grammar"

    def __init__(self, settings: Settings, entry: ModelEntry):
        from openai import OpenAI

        base_url = entry.extra.get("base_url") or os.environ.get(
            entry.extra.get("base_url_env", ""), "")
        if not base_url:
            raise UsageError(f"set base_url (or base_url_env) for {entry.model_id}")
        if not entry.api_model:
            raise UsageError(f"set api_model (served model name) for {entry.model_id}")
        self.entry = entry
        self.client = OpenAI(base_url=base_url, api_key=os.environ.get("OPENAI_COMPAT_KEY", "EMPTY"))
        self.max_tokens = int(settings.pilot.get("max_output_tokens", 4096))
        self.deviations: list[str] = []
        if entry.extra.get("schema_enforced") is False:
            # e.g. mlx_lm.server ignores response_format: the schema is only in the prompt and the
            # output is validated afterwards.
            self.structured_output = "post_validation"
            self.deviations.append(f"{entry.model_id}: server does not enforce the JSON schema; "
                                   "outputs validated after generation")

    def call(self, system: str, user: str, schema: dict, chunk_id: str) -> CallResult:
        start = time.monotonic()
        try:
            response = self.client.chat.completions.create(
                model=self.entry.api_model,
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}],
                temperature=0,
                max_tokens=self.max_tokens,
                response_format={"type": "json_schema",
                                 "json_schema": {"name": "extraction_output", "strict": True,
                                                 "schema": schema}},
                # Server-specific fields, e.g. {"adapters": path} for mlx_lm.server, whose
                # --adapter-path is ignored for "default_model" in 0.31.3.
                extra_body=self.entry.extra.get("extra_body"),
            )
        except Exception as exc:  # noqa: BLE001 - surface any client/server error as backend failure
            raise BackendFailure(f"{self.entry.model_id} call failed on {chunk_id}: {exc}") from exc
        latency = (time.monotonic() - start) * 1000
        text = response.choices[0].message.content if response.choices else None
        return CallResult(
            raw_body=response.model_dump(),
            parsed_candidate=parse_json_text(text),
            model_version=self.entry.extra.get("model_version") or response.model,
            usage=response.usage.model_dump() if response.usage else {},
            meta={"id": response.id},
            cost_eur=0.0,
            latency_ms=latency,
        )
