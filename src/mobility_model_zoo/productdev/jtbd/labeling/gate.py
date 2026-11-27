"""Claude gate (constitution Principle XI, decision D-claude-ban).

No labeling, pilot, writer or evaluation run may use a Claude model. `jtbd label` checks the
registry entry and the requested backend before anything else, `make_backend` checks them again
before a backend is built and checks the model each answer reports afterwards; benchmark steps
check the stored run record with `require_pass`. The Claude reference labels of the frozen
benchmarks (pilot-v1, pilot-v2, cluster-v1, spike-v2) stay readable, but no new run may record Claude.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from mobility_model_zoo.productdev.jtbd.errors import ClaudeGateError

CLAUDE_FAMILIES = {"anthropic-claude"}
CLAUDE_BACKENDS = {"claude_cli", "anthropic_api"}
# Whole name parts only, so "corpus" or "opusculum" do not match.
CLAUDE_NAME = re.compile(r"(?<![a-z])(claude|anthropic|opus|sonnet|haiku|fable)(?![a-z])", re.I)


@dataclass(frozen=True)
class GateResult:
    status: Literal["pass", "fail"]
    reason: str = ""

    def as_record(self) -> dict[str, str]:
        return {"status": self.status, "reason": self.reason}


PASS = GateResult("pass")


def _name_hit(value: str | None) -> str | None:
    match = CLAUDE_NAME.search(value or "")
    return match.group(1).lower() if match else None


def check_names(*, model_id: str | None = None, family: str | None = None,
                backend: str | None = None, model: str | None = None) -> GateResult:
    if family in CLAUDE_FAMILIES:
        return GateResult("fail", f"family {family} is Claude")
    if backend in CLAUDE_BACKENDS:
        return GateResult("fail", f"backend {backend} serves Claude")
    for field, value in (("model id", model_id), ("model", model)):
        hit = _name_hit(value)
        if hit:
            return GateResult("fail", f"{field} {value!r} names Claude ({hit})")
    return PASS


def check_entry(entry: Any) -> GateResult:
    """Registry entry before any call: family, backend, registry id and requested model."""
    return check_names(model_id=entry.model_id, family=entry.family, backend=entry.backend,
                       model=entry.api_model)


def check_resolved(entry: Any, resolved_model: str | None) -> GateResult:
    """The model a backend reports after a call (OpenRouter model id, Ollama digest)."""
    return check_names(model=resolved_model)


def require(result: GateResult, what: str) -> None:
    if result.status != "pass":
        raise ClaudeGateError(f"Claude gate: {what}: {result.reason} (constitution XI)")


def require_pass(record: dict[str, Any]) -> None:
    """A stored run record must carry a passing gate result and name no Claude model."""
    run = record.get("run_id", "run")
    recorded = record.get("gate") or {}
    if recorded.get("status") != "pass":
        raise ClaudeGateError(
            f"Claude gate: {run} has no passing gate record ({recorded.get('reason') or 'missing'})")
    require(check_names(model_id=record.get("model_id"), family=record.get("family"),
                        backend=record.get("backend"), model=record.get("model_version")), run)
    for key in ("requested_model", "resolved_model"):
        require(check_names(model=record.get(key)), run)


def guard(backend: Any, entry: Any) -> Any:
    """Wrap `backend.call` so an answer from a Claude model is refused before it is used."""
    call = backend.call

    def gated_call(*args: Any, **kwargs: Any) -> Any:
        result = call(*args, **kwargs)
        require(check_resolved(entry, result.model_version), f"{entry.model_id} answered as")
        return result

    backend.call = gated_call
    return backend
