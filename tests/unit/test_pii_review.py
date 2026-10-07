"""Model-assisted personal-data review replaces manual review (FR-012, R7 amended 2026-10-06)."""

import yaml
from helpers import copy_fixture, pilot
from span_helpers import write_train_chunks

from mobility_model_zoo.productdev.jtbd.config import load_settings
from mobility_model_zoo.productdev.jtbd.corpus.pii import apply, pii_review, present_findings
from mobility_model_zoo.productdev.jtbd.corpus.store import load_chunks
from mobility_model_zoo.productdev.jtbd.jsonio import read_json

TEXT = ("Ich heiße Erika Muster und wohne in der Lindenstraße 12. Der Bus kommt nie. "
        "Minister Wissing sagte dazu nichts. Mein Nachbar Hans fährt Auto.")


def model_config(tmp_path):
    config = copy_fixture(tmp_path)
    raw = yaml.safe_load(config.read_text())
    raw["pilot"]["redaction_review"] = "model"
    config.write_text(yaml.safe_dump(raw, allow_unicode=True))
    models = config.parent / "models.yaml"
    m = yaml.safe_load(models.read_text())
    m["models"].append({"model_id": "local-reviewer", "family": "fam-l", "backend": "ollama",
                        "host": "http://localhost:1", "role": "baseline",
                        "api_model": "x", "quantization": "Q4"})
    models.write_text(yaml.safe_dump(m))
    return config


def fake(findings_by_pass):
    calls = iter(findings_by_pass)
    return lambda text: {"findings": next(calls, [])}


def test_apply_replaces_longest_first_and_skips_placeholders():
    findings = [{"text": "Erika", "category": "person_name"},
                {"text": "Erika Muster", "category": "person_name"},
                {"text": "[PERSON]", "category": "person_name"}]
    text, n = apply("Erika Muster sagt hallo.", findings)
    assert text == "[PERSON] sagt hallo." and n == 1


def test_only_whole_words_are_replaced():
    text, n = apply("Al sagt: Alle Busse fahren, auch in Altona. Al!",
                    [{"text": "Al", "category": "person_name"}])
    assert text == "[PERSON] sagt: Alle Busse fahren, auch in Altona. [PERSON]!" and n == 2


def test_a_reported_placeholder_or_a_word_fragment_is_not_present():
    findings = [{"text": "[PERSON]", "category": "person_name"},
                {"text": "Al", "category": "person_name"}]
    assert present_findings("[PERSON] sagt: Alle Busse fahren.", findings) == []


def test_review_redacts_until_clean_and_keeps_an_audit_trail(tmp_path):
    config = model_config(tmp_path)
    settings = load_settings(config)
    write_train_chunks(settings, [("snap-000000000001", "de", "forum_review")], text=TEXT)
    asker = fake([
        [{"text": "Erika Muster", "category": "person_name"},
         {"text": "Lindenstraße 12", "category": "address"},
         {"text": "Nicht im Text", "category": "person_name"}],
        [{"text": "Hans", "category": "person_name"}],
        [],
    ])
    out = pii_review(settings, "local-reviewer", asker=asker)
    # The fixture's other four chunks get an empty answer and pass unchanged.
    assert out == {"chunks": 5, "changed": 1, "replacements": 3, "unresolved": []}
    chunk = load_chunks(settings)[0]
    assert "Erika" not in chunk.text and "Hans" not in chunk.text
    assert "[ADDRESS]" in chunk.text and "Minister Wissing" in chunk.text
    assert chunk.redaction.model_review_model == "local-reviewer"
    audit = read_json(settings.analysis_dir / "pii-review" / "ch-001.json")
    assert [p["present"] for p in audit["passes"]] == [2, 1, 0] and audit["final_clean"]
    pilot(config, "corpus", "redact-check")


def test_unreviewed_or_unresolved_chunks_fail_redact_check(tmp_path):
    config = model_config(tmp_path)
    settings = load_settings(config)
    write_train_chunks(settings, [("snap-000000000001", "de", "paper")], text=TEXT)
    pilot(config, "corpus", "redact-check", expect=1)  # not reviewed yet
    out = pii_review(settings, "local-reviewer", asker=fake(
        [[{"text": "Hans", "category": "person_name"}],
         [{"text": "Erika", "category": "person_name"}],
         [{"text": "Muster", "category": "person_name"}]]))
    assert out["unresolved"] == ["ch-001"]  # still finding new names after the last pass
    pilot(config, "corpus", "redact-check", expect=1)
