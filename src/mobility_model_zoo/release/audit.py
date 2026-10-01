"""`zoo audit`: published versions on the Hub still match their release records (FR-007), and every
staging and sandbox repo is private (FR-006a, FR-021)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from mobility_model_zoo.release.errors import GateFailed
from mobility_model_zoo.release.registry import Registry


def run(reg: Registry, only: str | None, hub: Any, say: Callable[[str], None]) -> None:
    failures: list[str] = []
    for name in [only] if only else reg.model_names():
        model = reg.model(name)
        public, staging = model["repos"]["public"], model["repos"]["staging"]
        if hub.visibility(staging) == "public":
            failures.append(f"{staging} is public; staging repos must be private")
        if model["topic"] == "sandbox" and hub.visibility(public) == "public":
            failures.append(f"{public} is public; sandbox models must stay private")
        published = reg.published_versions(name)
        if not published:
            continue
        tags = hub.refs(public)["tags"] if hub.visibility(public) else {}
        for version in published:
            pub = reg.record_raw(name, version)["published"]
            tag = pub["tag"]
            if tags.get(tag) != pub["repo_commit"]:
                failures.append(
                    f"{public} {tag} points to {tags.get(tag)}, recorded {pub['repo_commit']}"
                )
                continue
            info = hub.file_info(public, "README.md", pub["repo_commit"])
            if info is None or info[0] != pub["card_sha256"]:
                failures.append(f"{public} {tag}: the card differs from the recorded card")
            else:
                say(f"{name} {version}: OK")
    if failures:
        raise GateFailed(failures)
