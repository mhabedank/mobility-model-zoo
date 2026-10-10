"""Example outputs from the published card (research R4; check B3)."""

from __future__ import annotations

import hashlib

import pytest
from site_fixture import MODEL, VERSION

from mobility_model_zoo.release.card import parse_card_examples
from mobility_model_zoo.release.errors import GateFailed, UsageError
from mobility_model_zoo.site import examples
from mobility_model_zoo.site.schema_doc import output_format

CARD = """## Examples

### Example 1: `a.txt`

Input:

> Text

Output:

```json
{"x": 1}
```

### Example 2: `b.txt`

Output:

```json
{
  "y": 2
}
```
"""


def test_parse_card_examples():
    assert parse_card_examples(CARD) == {"a.txt": '{"x": 1}', "b.txt": '{\n  "y": 2\n}'}


def _schema(env):
    return output_format(env.reg, "jtbd-span-v1")["schema"]


def test_cached_outputs_load_and_validate(site_env):
    loaded = examples.load(site_env.reg, MODEL, VERSION, _schema(site_env), offline=True)
    assert [e["file"] for e in loaded] == [
        "01-night-shift.txt",
        "02-depot-charging.txt",
        "03-cargo-bike.txt",
    ]
    assert loaded[0]["lang"] == "de" and loaded[1]["lang"] == "en"
    assert all(e["span_format"] and e["segments"] for e in loaded)


def test_offline_without_cache_fails(site_env):
    (site_env.root / ".cache" / "site" / MODEL / f"{VERSION}.json").unlink()
    with pytest.raises(UsageError, match="not cached"):
        examples.card_outputs(site_env.reg, MODEL, VERSION, offline=True)


def test_cache_of_another_commit_is_not_used(site_env):
    site_env.edit_cache(lambda d: d.update(repo_commit="0" * 40))
    with pytest.raises(UsageError):
        examples.card_outputs(site_env.reg, MODEL, VERSION, offline=True)


def test_downloaded_card_must_match_card_sha256(site_env, monkeypatch):
    (site_env.root / ".cache" / "site" / MODEL / f"{VERSION}.json").unlink()
    monkeypatch.setattr(examples, "_download_card", lambda repo, rev: b"# another card\n")
    with pytest.raises(GateFailed, match="B3 .*card hash"):
        examples.card_outputs(site_env.reg, MODEL, VERSION)


def test_downloaded_card_with_matching_hash_is_cached(site_env, monkeypatch):
    card = CARD.replace("a.txt", "01-night-shift.txt").encode()
    sha = hashlib.sha256(card).hexdigest()
    site_env.edit_yaml(
        f"zoo/models/{MODEL}/releases/{VERSION}.yaml", lambda r: r["published"].update(card_sha256=sha)
    )
    monkeypatch.setattr(examples, "_download_card", lambda repo, rev: card)
    outputs = examples.card_outputs(site_env.reg, MODEL, VERSION, refresh=True)
    assert outputs["01-night-shift.txt"] == '{"x": 1}'
    assert examples.card_outputs(site_env.reg, MODEL, VERSION, offline=True) == outputs


def test_truncated_output_is_b3(site_env):
    site_env.edit_cache(lambda d: d["outputs"].update({"01-night-shift.txt": '{"items": ['}))
    with pytest.raises(GateFailed, match="B3 .*01-night-shift.txt.*not JSON"):
        examples.load(site_env.reg, MODEL, VERSION, _schema(site_env), offline=True)
