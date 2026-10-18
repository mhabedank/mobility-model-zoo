"""Where runs are tracked, from the environment only (FR-010, research R4).

Live: `MLFLOW_TRACKING_URI` from the process environment, else from the `MLFLOW_*` and
`MMZ_TRACKING_*` keys of a `.env` in the working directory or at the repository root. Nothing else of
`.env` is loaded, so commands that do not load `.env` today keep behaving as before.

Offline: `MMZ_TRACKING_OFFLINE=1` without a URI (the Spark scripts set it in training containers);
runs then write an offline log next to their sidecar (research R17). A URI wins. With neither, the
tracking layer does nothing.
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit

URI = "MLFLOW_TRACKING_URI"
OFFLINE = "MMZ_TRACKING_OFFLINE"
# Client limits the layer sets only when the user has not (research R5): the defaults retry for
# about four minutes and would stall a training run when the server is gone.
CLIENT_DEFAULTS = {
    "MLFLOW_HTTP_REQUEST_MAX_RETRIES": "2",
    "MLFLOW_HTTP_REQUEST_TIMEOUT": "10",
    "MLFLOW_DISABLE_AGENT_HINT": "1",
    "MLFLOW_ENABLE_ARTIFACTS_PROGRESS_BAR": "false",
}


def _dotenv_keys() -> dict[str, str]:
    from mobility_model_zoo.edge.paths import repo_root

    for path in (Path.cwd() / ".env", repo_root() / ".env"):
        if path.is_file():
            try:
                from dotenv import dotenv_values
            except ImportError:
                return {}
            return {
                k: v
                for k, v in dotenv_values(path).items()
                if k.startswith(("MLFLOW_", "MMZ_TRACKING_")) and v
            }
    return {}


def tracking_uri() -> str | None:
    uri = os.environ.get(URI)
    if uri:
        return uri
    found = _dotenv_keys()
    for key, value in found.items():
        os.environ.setdefault(key, value)  # only MLFLOW_* and MMZ_TRACKING_* keys, nothing else
    return found.get(URI)


def client_installed() -> bool:
    apply_client_defaults()  # before the first `import mlflow`, which reads some of them
    try:
        import mlflow  # noqa: F401
    except ImportError:
        return False
    return True


def enabled() -> bool:
    return bool(tracking_uri()) and client_installed()


def offline() -> bool:
    """Offline run logs instead of a server: `MMZ_TRACKING_OFFLINE=1` and no tracking URI."""
    return not tracking_uri() and os.environ.get(OFFLINE, "").strip() == "1"


def apply_client_defaults() -> None:
    for key, value in CLIENT_DEFAULTS.items():
        os.environ.setdefault(key, value)


def uri_host(uri: str | None = None) -> str:
    """Host and port only, for sidecars and status lines (never credentials or paths)."""
    parts = urlsplit(uri or tracking_uri() or "")
    if parts.hostname is None:
        return parts.scheme or "-"
    return f"{parts.hostname}:{parts.port}" if parts.port else parts.hostname
