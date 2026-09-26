"""Prompt = guideline (with the domain definition) + worked examples + output schema.

The user message is the chunk text only: no persona (Principle I), no metadata (Principle VII).
"""

from __future__ import annotations

import json

import yaml

from jtbd_pilot.config import Settings
from jtbd_pilot.freeze import sha256_text
from jtbd_pilot.schema import ExtractionOutput, wire_schema

INSTRUCTIONS = (
    "Return exactly one JSON object that matches the schema below and nothing else. "
    "Quotes must be copied verbatim from the text, in the text's language. "
    "Statements are written in English. An empty items list is a correct answer when the text "
    "contains no job, pain or gain."
)


def build_system_prompt(settings: Settings) -> str:
    domain = settings.domain()
    guideline = settings.paths["guideline"].read_text(encoding="utf-8")
    guideline = guideline.replace("{{domain_definition}}", domain["definition"].strip())
    parts = [guideline.strip(), "", "## Worked examples"]
    for n, path in enumerate(sorted(settings.paths["examples"].glob("*.yaml")), start=1):
        example = yaml.safe_load(path.read_text(encoding="utf-8"))
        ExtractionOutput.model_validate(example["output"])
        parts += [
            f"### Example {n}" + (f": {example['title']}" if example.get("title") else ""),
            "Text:",
            example["text"].strip(),
            "Output:",
            json.dumps(example["output"], ensure_ascii=False, indent=2),
        ]
        if example.get("note"):
            parts.append(f"Why: {example['note'].strip()}")
    parts += ["", "## Output", INSTRUCTIONS, "", "Schema:",
              json.dumps(wire_schema(), ensure_ascii=False, indent=2)]
    return "\n".join(parts) + "\n"


def prompt_sha256(system_prompt: str) -> str:
    return sha256_text(system_prompt)


def approx_prompt_tokens(system_prompt: str) -> int:
    return max(1, round(len(system_prompt) / 4))
