"""Chunk storage: one JSON file per chunk under data/chunks/."""

from __future__ import annotations

from mobility_model_zoo.productdev.jtbd.config import Settings
from mobility_model_zoo.productdev.jtbd.jsonio import read_json, write_json
from mobility_model_zoo.productdev.jtbd.schema import ChunkRecord


def load_chunks(settings: Settings, split: str | None = None) -> list[ChunkRecord]:
    directory = settings.chunks_dir
    if not directory.exists():
        return []
    chunks = [ChunkRecord.model_validate(read_json(p)) for p in sorted(directory.glob("ch-*.json"))]
    if split:
        chunks = [c for c in chunks if c.split == split]
    return chunks


def chunk_map(settings: Settings, split: str | None = None) -> dict[str, ChunkRecord]:
    return {c.chunk_id: c for c in load_chunks(settings, split)}


def save_chunk(settings: Settings, chunk: ChunkRecord) -> None:
    write_json(settings.chunks_dir / f"{chunk.chunk_id}.json", chunk.model_dump(mode="json"))
