"""Shared helpers of the website tests: a temporary copy of the frozen fixture registry (scout-large
0.1.2 with its published example outputs in `.cache/site`, an unpublished model, a sandbox model),
so every test runs offline and can change files freely."""

from __future__ import annotations

import json
import shutil
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
        """Offline; without preview images unless `images=True` (those need Chromium)."""
        from mobility_model_zoo.site.build import build

        kwargs.setdefault("images", False)
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

    def clone_model(self, src: str, dst: str) -> None:
        """A second published model: `src` with its records and cached examples under a new name."""
        models = self.root / "zoo" / "models"
        shutil.copytree(models / src, models / dst)
        shutil.copytree(self.root / ".cache" / "site" / src, self.root / ".cache" / "site" / dst)

        def rename(model):
            model["name"] = dst
            model["repos"] = {k: v.replace(src, dst) for k, v in model["repos"].items()}

        self.edit_yaml(f"zoo/models/{dst}/model.yaml", rename)
        self.reg = type(self.reg)(self.root)
