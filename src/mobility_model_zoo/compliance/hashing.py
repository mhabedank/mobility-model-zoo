"""Keyed hashes (HMAC-SHA-256) of request identifiers and URLs (research R12).

The key comes from MMZ_SUPPRESSION_KEY in the environment or .env and never enters git, so the
hashes in compliance/requests.yaml and suppression.yaml cannot be reversed by guessing names.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import unicodedata
from collections.abc import Callable

ENV = "MMZ_SUPPRESSION_KEY"


def _key() -> bytes | None:
    value = os.environ.get(ENV)
    if not value:
        try:
            from dotenv import dotenv_values

            value = dotenv_values(".env").get(ENV)
        except ImportError:
            value = None
    return value.encode("utf-8") if value else None


def normalise(identifier: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", identifier).lower().split())


def keyed_hash(identifier: str, key: bytes | None = None) -> str:
    key = key or _key()
    if not key:
        raise RuntimeError(f"{ENV} is not set (see .env.example)")
    return hmac.new(key, normalise(identifier).encode("utf-8"), hashlib.sha256).hexdigest()


def url_hasher() -> Callable[[str], str] | None:
    key = _key()
    if not key:
        return None
    return lambda url: keyed_hash(url, key)
