"""Model-assisted removal of personal data before labeling (FR-012, research R7 as amended).

The owner does not review chunks by hand (decision of 2026-10-06). Instead, after the pattern
redaction, a local model on the development hardware lists every piece of personal data about
private individuals in each chunk: names, usernames, e-mail addresses, phone numbers, street
addresses with house numbers, licence plates and other direct identifiers. Each listed string is
replaced by a placeholder, and the chunk is reviewed again until the model finds nothing (at most
`MAX_PASSES` passes). Every pass is stored under `<analysis>/pii-review/` for audit. The text never
leaves the local network.

Not personal data in this sense: public officials, members of parliament and invited experts
speaking or named in their public role in official records; authors of cited publications;
organisations, brands, places and roads without house numbers.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import httpx

from mobility_model_zoo.productdev.jtbd.config import Settings
from mobility_model_zoo.productdev.jtbd.corpus.store import load_chunks, save_chunk
from mobility_model_zoo.productdev.jtbd.errors import BackendFailure, UsageError
from mobility_model_zoo.productdev.jtbd.jsonio import write_json

MAX_PASSES = 3
PLACEHOLDERS = {
    "person_name": "[PERSON]",
    "username": "[USER]",
    "email": "[EMAIL]",
    "phone": "[PHONE]",
    "address": "[ADDRESS]",
    "licence_plate": "[PLATE]",
    "other_identifier": "[ID]",
}
SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "category": {"enum": sorted(PLACEHOLDERS)},
                },
                "required": ["text", "category"],
            },
        }
    },
    "required": ["findings"],
}
PROMPT = """You check a text for personal data before it is used in research.

List every piece of personal data about a PRIVATE individual that appears in the text, copied
exactly as it appears (same spelling, same characters):
- person_name: names of private persons (first names, surnames, nicknames used as names)
- username: forum or social media handles
- email, phone
- address: street address with house number, or another address of a private home
- licence_plate
- other_identifier: customer, contract, ticket or ID numbers that point to one person

Do NOT list:
- members of parliament, ministers, mayors, officials, invited experts or organisation
  representatives named or speaking in their public role in official records or hearings
- authors of cited studies, articles or laws
- companies, brands, products, institutions, parties, places, cities, roads without house number
- placeholders that are already in square brackets, such as [PERSON] or [EMAIL]

If there is no personal data, return an empty list. Answer only with JSON:
{"findings": [{"text": "...", "category": "..."}]}

Text:
"""


def ask(base_url: str, model: str, text: str, timeout: float = 600) -> dict[str, Any]:
    response = httpx.post(f"{base_url}/api/chat", timeout=timeout, json={
        "model": model, "stream": False, "think": False, "format": SCHEMA,
        "options": {"temperature": 0, "num_ctx": 16384},
        "messages": [{"role": "user", "content": PROMPT + text}],
    })
    if response.status_code >= 400:
        raise BackendFailure(f"Ollama answered {response.status_code}: {response.text[:200]}")
    content = response.json().get("message", {}).get("content", "")
    try:
        data = json.loads(content)
    except ValueError as exc:
        raise BackendFailure(f"model answer is not JSON: {content[:200]}") from exc
    return {"findings": [f for f in data.get("findings", [])
                         if isinstance(f, dict) and f.get("category") in PLACEHOLDERS
                         and isinstance(f.get("text"), str) and f["text"].strip()]}


def apply(text: str, findings: list[dict[str, str]]) -> tuple[str, int]:
    """Replace every exact occurrence of each finding (longest first). Returns (text, count)."""
    count = 0
    for finding in sorted(findings, key=lambda f: -len(f["text"])):
        needle = finding["text"].strip()
        if len(needle) < 2 or needle.startswith("[") and needle.endswith("]"):
            continue
        hits = text.count(needle)
        if hits:
            text = text.replace(needle, PLACEHOLDERS[finding["category"]])
            count += hits
    return text, count


def pii_review(settings: Settings, model_id: str, host: str | None = None,
               only_unreviewed: bool = True, asker=None) -> dict[str, Any]:
    """Review every chunk (or only the unreviewed ones) with the local model and redact."""
    from mobility_model_zoo.productdev.jtbd.labeling.ollama import resolve_host

    entry = settings.model(model_id)
    if entry.backend != "ollama":
        raise UsageError(f"{model_id} is not a local Ollama model; personal data stays local")
    base_url = resolve_host(host or entry.host)
    call = asker or (lambda text: ask(base_url, entry.api_model, text))
    out_dir = settings.analysis_dir / "pii-review"
    totals = {"chunks": 0, "changed": 0, "replacements": 0, "unresolved": []}
    for chunk in load_chunks(settings):
        if only_unreviewed and chunk.redaction.model_review_at is not None:
            continue
        passes = []
        text = chunk.text
        final_clean = False
        for _ in range(MAX_PASSES):
            answer = call(text)
            # Strings the model lists but that are not in the text are not personal data in it.
            present = [f for f in answer["findings"] if f["text"].strip() in text]
            new_text, count = apply(text, present)
            passes.append({"findings": answer["findings"], "present": len(present),
                           "replaced": count})
            text = new_text
            if not present:
                final_clean = True
                break
        write_json(out_dir / f"{chunk.chunk_id}.json", {
            "chunk_id": chunk.chunk_id, "model": entry.model_id, "api_model": entry.api_model,
            "reviewed_at": datetime.now(UTC).isoformat(), "passes": passes,
            "final_clean": final_clean})
        totals["chunks"] += 1
        replaced = sum(p["replaced"] for p in passes)
        if replaced:
            totals["changed"] += 1
            totals["replacements"] += replaced
            chunk.text = text
        if final_clean:
            chunk.redaction.model_review_at = datetime.now(UTC)
            chunk.redaction.model_review_model = entry.model_id
        else:
            chunk.redaction.model_review_at = None
            totals["unresolved"].append(chunk.chunk_id)
        chunk.redaction.check_passed = False
        save_chunk(settings, chunk)
    return totals
