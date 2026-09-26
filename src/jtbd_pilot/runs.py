"""Reading label runs: manifests, parsed outputs and located items."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jtbd_pilot.config import Settings
from jtbd_pilot.corpus.store import chunk_map
from jtbd_pilot.errors import UsageError
from jtbd_pilot.jsonio import read_json
from jtbd_pilot.quotes import locate
from jtbd_pilot.schema import ExtractionOutput, LabelRunManifest


@dataclass
class LocatedItem:
    index: int
    kind: str
    quote: str
    actor: str
    actor_type: str
    statement: str
    evidence_type: str
    evidence_scope: str
    span: tuple[int, int] | None

    @property
    def valid(self) -> bool:
        return self.span is not None

    def attrs(self) -> dict[str, str]:
        return {
            "kind": self.kind,
            "actor_type": self.actor_type,
            "evidence_type": self.evidence_type,
            "evidence_scope": self.evidence_scope,
        }


@dataclass
class ChunkOutput:
    chunk_id: str
    relevant: bool | None  # None: no valid output (excluded chunk)
    items: list[LocatedItem] = field(default_factory=list)

    @property
    def valid_items(self) -> list[LocatedItem]:
        return [i for i in self.items if i.valid]


def run_dir(settings: Settings, run_id: str) -> Path:
    path = settings.runs_dir / run_id
    if not (path / "manifest.json").exists():
        raise UsageError(f"unknown run {run_id} (no {path / 'manifest.json'})")
    return path


def load_run_manifest(settings: Settings, run_id: str) -> LabelRunManifest:
    return LabelRunManifest.model_validate(read_json(run_dir(settings, run_id) / "manifest.json"))


def locate_items(output: ExtractionOutput, text: str) -> list[LocatedItem]:
    used: list[tuple[int, int]] = []
    items = []
    for n, item in enumerate(output.items):
        span = locate(item.quote, text, used)
        if span:
            used.append(span)
        items.append(LocatedItem(index=n, span=span, **item.model_dump()))
    return items


def load_outputs(settings: Settings, run_id: str) -> dict[str, ChunkOutput]:
    """All chunks of the run's split. Excluded chunks have relevant=None and no items."""
    manifest = load_run_manifest(settings, run_id)
    directory = run_dir(settings, run_id)
    chunks = chunk_map(settings, manifest.split)
    excluded = {e.chunk_id for e in manifest.excluded_chunks}
    outputs: dict[str, ChunkOutput] = {}
    for chunk_id, chunk in sorted(chunks.items()):
        parsed_path = directory / "parsed" / f"{chunk_id}.json"
        if chunk_id in excluded or not parsed_path.exists():
            if chunk_id in excluded:
                outputs[chunk_id] = ChunkOutput(chunk_id, None)
            continue
        output = ExtractionOutput.model_validate(read_json(parsed_path))
        outputs[chunk_id] = ChunkOutput(chunk_id, output.relevant,
                                        locate_items(output, chunk.text))
    return outputs


def output_summary(outputs: dict[str, ChunkOutput]) -> dict[str, Any]:
    items = [i for o in outputs.values() for i in o.items]
    return {
        "chunks": len(outputs),
        "excluded": sum(1 for o in outputs.values() if o.relevant is None),
        "items": len(items),
        "invalid_quotes": sum(1 for i in items if not i.valid),
    }
