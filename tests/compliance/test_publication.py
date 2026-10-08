"""Publication stage: corpus overlap, PII, example sources (C-U1 … C-U4)."""

import json

from compliance_helpers import load, write

from mobility_model_zoo.compliance import release_checks as rc
from mobility_model_zoo.compliance.checks import Context
from mobility_model_zoo.compliance.scan import CorpusIndex

CORPUS = (
    "Der Bus kommt am Abend viel zu selten und deshalb fahren die meisten Leute aus dem Dorf "
    "mit dem eigenen Auto in die Stadt zur Arbeit und zurück nach Hause obwohl sie lieber mit "
    "dem Bus fahren würden wenn er öfter käme und pünktlich wäre und bezahlbar bliebe für alle"
)
WORDS = CORPUS.split()


def _env(root, example_text="A fictional example about late buses.", sources=None):
    write(root, "zoo/models/m/model.yaml", {"topic": "t"})
    (root / "zoo/models/m/examples").mkdir(parents=True, exist_ok=True)
    (root / "zoo/models/m/examples/01.txt").write_text(example_text)
    write(
        root,
        "zoo/models/m/examples/SOURCES.yaml",
        {"examples": [{"file": "01.txt", "source": "synthetic", "note": "written for the card"}]}
        if sources is None
        else sources,
    )
    return root


def _scan(root, card):
    reg = load(root)
    ctx = Context(reg, model="m", version="0.1.0", extra={"card": card})
    full = CorpusIndex.build([CORPUS])
    report = rc.scan_publication(ctx, full, full)
    rc.report_path(root, "m", "0.1.0").parent.mkdir(parents=True, exist_ok=True)
    rc.report_path(root, "m", "0.1.0").write_text(json.dumps(report))
    return ctx


def ids(ctx):
    return {f.check_id for f in rc.stage_publication(ctx)}


def test_clean_passes(register_tree):
    ctx = _scan(_env(register_tree), "# Card\n\nA card without copied text.\n")
    assert ids(ctx) == set()


def test_31_corpus_words_fail_29_pass(register_tree):
    root = _env(register_tree)
    assert ids(_scan(root, " ".join(WORDS[:31]))) == {"C-U2"}
    assert ids(_scan(root, " ".join(WORDS[:29]))) == set()


def test_allowed_quote_source_passes(register_tree):
    root = _env(register_tree)
    reg = load(root)
    ctx = Context(reg, model="m", version="0.1.0", extra={"card": " ".join(WORDS[:40])})
    full = CorpusIndex.build([CORPUS])
    restricted = CorpusIndex.build([])  # the corpus text belongs to a quote_allowed source
    report = rc.scan_publication(ctx, full, restricted)
    rc.report_path(root, "m", "0.1.0").parent.mkdir(parents=True, exist_ok=True)
    rc.report_path(root, "m", "0.1.0").write_text(json.dumps(report))
    assert ids(ctx) == set()
    card_entry = next(f for f in report["files"] if f["path"].startswith("README"))
    assert card_entry["allowed_quote_words"] == 40


def test_pii_in_card(register_tree):
    ctx = _scan(_env(register_tree), "Contact lena.beispiel@posteo.de for details.")
    assert ids(ctx) == {"C-U3"}


def test_changed_file_after_scan(register_tree):
    root = _env(register_tree)
    _scan(root, "card text")
    ctx = Context(load(root), model="m", version="0.1.0", extra={"card": "card text, edited"})
    assert ids(ctx) == {"C-U1"}


def test_missing_report(register_tree):
    ctx = Context(load(_env(register_tree)), model="m", version="0.1.0", extra={"card": "x"})
    assert ids(ctx) == {"C-U1"}


def test_example_sources(register_tree):
    root = _env(register_tree, sources={"examples": []})
    assert ids(_scan(root, "card")) == {"C-U4"}
    root = _env(
        register_tree, sources={"examples": [{"file": "01.txt", "source": "paper-one", "note": "n"}]}
    )
    assert ids(_scan(root, "card")) == {"C-U4"}  # paper-one has redistribution: not_allowed
