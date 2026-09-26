"""`pilot doctor`: environment checks. Never calls a model and never writes a file."""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any

import httpx

from jtbd_pilot.config import Settings
from jtbd_pilot.errors import ValidationFailed
from jtbd_pilot.freeze import compute_hashes, load_manifest


def _claude() -> tuple[bool, str]:
    if not shutil.which("claude"):
        return False, "`claude` not on PATH"
    try:
        proc = subprocess.run(["claude", "auth", "status"], capture_output=True, text=True,
                              timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"`claude auth status` failed: {exc}"
    text = (proc.stdout + proc.stderr).strip().replace("\n", " ")[:200]
    return proc.returncode == 0, text or "claude CLI present"


def _ollama(env: str) -> tuple[bool, str]:
    url = os.environ.get(env)
    if not url:
        return False, f"{env} not set"
    try:
        response = httpx.get(f"{url.rstrip('/')}/api/tags", timeout=10)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        return False, f"{url} unreachable: {exc}"
    models = [m["name"] for m in response.json().get("models", [])]
    return True, f"{len(models)} models on {url}"


def doctor(settings: Settings) -> dict[str, Any]:
    checks: dict[str, dict[str, Any]] = {}

    def add(name: str, ok: bool, detail: str, required: bool = True) -> None:
        checks[name] = {"ok": ok, "detail": detail, "required": required}

    add("claude_cli", *_claude())
    add("openrouter_key", bool(os.environ.get("OPENROUTER_API_KEY")),
        "OPENROUTER_API_KEY set" if os.environ.get("OPENROUTER_API_KEY") else "not set")
    money = settings.budget()
    cap_ok = money.get("key_cap_eur") is not None and money["key_cap_eur"] <= money["budget_eur"]
    add("openrouter_cap", cap_ok and bool(money.get("key_cap_set_on")),
        f"key cap EUR {money.get('key_cap_eur')} of budget EUR {money.get('budget_eur')}, set on "
        f"{money.get('key_cap_set_on') or 'NOT RECORDED (T046)'}")
    add("ollama_spark", *_ollama("OLLAMA_HOST"))
    add("ollama_vm", *_ollama("OLLAMA_HOST_VM"), required=False)

    manifest = load_manifest(settings)
    if manifest:
        current = compute_hashes(settings)
        drift = [k for k in ("hashes", "chunks", "holdout_chunks", "train_chunks")
                 if manifest.get(k, {}) != current[k]]
        add("manifest", not drift,
            f"{manifest['version']} state {manifest['state']}, pilot {manifest['pilot_state']}"
            + (f", DRIFT in {drift}" if drift else ""))
    else:
        add("manifest", True, "not frozen yet", required=False)

    failed = [n for n, c in checks.items() if c["required"] and not c["ok"]]
    result = {"checks": checks, "failed": failed}
    if failed:
        raise ValidationFailed(f"doctor: {failed} failed: "
                               + "; ".join(f"{n}: {checks[n]['detail']}" for n in failed))
    return result
