"""Shared helpers of the website tests: a temporary copy of the frozen fixture registry (scout-large
0.1.2 with its published example outputs in `.cache/site`, an unpublished model, a sandbox model),
so every test runs offline and can change files freely."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from mobility_model_zoo.release.registry import Registry, dump_yaml, load_yaml

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "registry"
MODEL, VERSION = "scout-large", "0.1.2"


@dataclass
class SiteEnv:
    root: Path
    reg: Registry
    out: Path

    def build(self, **kwargs):
        from mobility_model_zoo.site.build import build

        return build(self.reg, self.out, offline=True, say=lambda _: None, **kwargs)

    def html(self, rel: str) -> str:
        return (self.out / rel).read_text(encoding="utf-8")

    def edit_yaml(self, rel: str, fn) -> None:
        path = self.root / rel
        data = load_yaml(path)
        fn(data)
        path.write_text(dump_yaml(data), encoding="utf-8")

    def edit_cache(self, fn) -> None:
        path = self.root / ".cache" / "site" / MODEL / f"{VERSION}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        fn(data)
        path.write_text(json.dumps(data), encoding="utf-8")
