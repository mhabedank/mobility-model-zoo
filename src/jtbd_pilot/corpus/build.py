"""Cut chunks from existing snapshots (never fetches).

selection.yaml format:

    chunks:
      - chunk_id: ch-001
        snapshot_id: snap-0123456789ab
        ranges: [[0, 1800]]          # character offsets in the snapshot's text.txt
        sub_area: public_transport_rural
        region: DACH
        country: DE
        language: de
        date: 2025-03-01
        relevance_intent: relevant
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jtbd_pilot.config import Settings
from jtbd_pilot.corpus.store import save_chunk
from jtbd_pilot.errors import ValidationFailed
from jtbd_pilot.jsonio import read_yaml
from jtbd_pilot.schema import ChunkRecord
from jtbd_pilot.sources.snapshot import load_snapshot, snapshot_text

SEGMENT_SEPARATOR = "\n\n"


def approx_tokens(text: str) -> int:
    """Tokenizer-independent approximation: about 4 characters per token."""
    return max(1, round(len(text) / 4))


def build_from_selection(settings: Settings, selection_path: Path) -> dict[str, Any]:
    selection = read_yaml(selection_path) or {}
    built, errors = [], []
    for spec in selection.get("chunks", []):
        try:
            snapshot = load_snapshot(settings, spec["snapshot_id"])
            source_text = snapshot_text(settings, spec["snapshot_id"])
            segments = []
            for start, end in spec["ranges"]:
                if not (0 <= start < end <= len(source_text)):
                    raise ValidationFailed(f"range {start}-{end} outside snapshot text")
                segments.append(source_text[start:end].strip())
            text = SEGMENT_SEPARATOR.join(segments)
            chunk = ChunkRecord.model_validate(
                {
                    "chunk_id": spec["chunk_id"],
                    "snapshot_id": snapshot.snapshot_id,
                    "ranges": spec["ranges"],
                    "text": text,
                    "token_count": approx_tokens(text),
                    "split": spec.get("split", "main"),
                    "sub_area": spec["sub_area"],
                    "source_type": snapshot.source_type,
                    "region": spec["region"],
                    "country": spec["country"],
                    "language": spec["language"],
                    "date": spec["date"],
                    "license": snapshot.license,
                    "relevance_intent": spec["relevance_intent"],
                    "redaction": {
                        "patterns_version": settings.pilot.get("redaction_patterns_version",
                                                               "redact-v1"),
                        "manual_review_at": None,
                        "check_passed": False,
                    },
                }
            )
        except (KeyError, ValueError, ValidationFailed) as exc:
            errors.append({"chunk_id": spec.get("chunk_id"), "error": str(exc)})
            continue
        save_chunk(settings, chunk)
        built.append(chunk.chunk_id)
    if errors:
        raise ValidationFailed(f"{len(errors)} chunk(s) failed: {errors}")
    return {"built": len(built), "chunk_ids": built}
