"""Claude reference labeler through headless Claude Code on the subscription (research.md R9).

No `--bare`: bare mode reads only ANTHROPIC_API_KEY and never the subscription login. Isolation
instead: own system prompt, no tools, no setting sources, no MCP, no slash commands, empty
working directory. Temperature cannot be set on this path (documented deviation).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from jtbd_pilot.config import ModelEntry, Settings
from jtbd_pilot.errors import BackendFailure, UsageError
from jtbd_pilot.labeling.base import CallResult, parse_json_text

MIN_INTERVAL_S = 1.5


def result_event(events: object) -> dict:
    """`--output-format json` returns either one result object or a list of events."""
    if isinstance(events, dict):
        return events
    if isinstance(events, list):
        results = [e for e in events if isinstance(e, dict) and e.get("type") == "result"]
        if results:
            return results[-1]
    raise BackendFailure("claude CLI output contains no result event")


class ClaudeCliBackend:
    name = "claude_cli"
    temperature = "not_settable"
    structured_output = "json_schema_strict"

    def __init__(self, settings: Settings, entry: ModelEntry):
        if not shutil.which("claude"):
            raise UsageError("the `claude` CLI is not on PATH")
        if not entry.api_model:
            raise UsageError(f"set api_model for {entry.model_id} in configs/models.yaml")
        self.entry = entry
        self.deviations = [
            "temperature not settable on the Claude subscription CLI path",
            "user-level ~/.claude/CLAUDE.md may be loaded as context by the CLI",
        ]
        self._last = 0.0

    def call(self, system: str, user: str, schema: dict, chunk_id: str) -> CallResult:
        wait = MIN_INTERVAL_S - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        with tempfile.TemporaryDirectory(prefix="pilot-claude-") as tmp:
            prompt_file = Path(tmp) / "system.md"
            prompt_file.write_text(system, encoding="utf-8")
            workdir = Path(tmp) / "work"
            workdir.mkdir()
            cmd = [
                "claude", "-p",
                "--output-format", "json",
                "--json-schema", json.dumps(schema),
                "--system-prompt-file", str(prompt_file),
                "--tools", "",
                "--model", self.entry.api_model,
                "--setting-sources", "",
                "--strict-mcp-config",
                "--disable-slash-commands",
                "--no-session-persistence",
            ]
            start = time.monotonic()
            try:
                proc = subprocess.run(cmd, input=user, capture_output=True, text=True,
                                      cwd=workdir, timeout=900)
            except subprocess.TimeoutExpired as exc:
                raise BackendFailure(f"claude CLI timed out on {chunk_id}") from exc
            latency = (time.monotonic() - start) * 1000
            self._last = time.monotonic()
        if proc.returncode != 0:
            raise BackendFailure(f"claude CLI failed on {chunk_id}: {proc.stderr.strip()[:300]}")
        try:
            events = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise BackendFailure(f"claude CLI returned non-JSON on {chunk_id}") from exc
        body = result_event(events)
        if body.get("is_error"):
            raise BackendFailure(f"claude CLI reported an error on {chunk_id}: "
                                 f"{str(body.get('result'))[:200]}")
        candidate = body.get("structured_output")
        if candidate is None:
            candidate = parse_json_text(body.get("result"))
        model_usage = body.get("modelUsage") or {}
        if model_usage:
            # The CLI may call a small helper model too; the labeler is the one that wrote the answer.
            model_version = max(model_usage,
                                key=lambda m: (model_usage[m] or {}).get("outputTokens", 0))
            version_note = None
        else:
            model_version = self.entry.api_model
            version_note = "model version taken from the pinned --model value (not in CLI output)"
        if version_note and version_note not in self.deviations:
            self.deviations.append(version_note)
        return CallResult(
            raw_body=events,
            parsed_candidate=candidate,
            model_version=model_version,
            usage=body.get("usage") or {},
            meta={"session_id": body.get("session_id"),
                  "total_cost_usd_info_only": body.get("total_cost_usd")},
            cost_eur=0.0,
            latency_ms=latency,
        )
