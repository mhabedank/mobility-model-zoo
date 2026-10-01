from jtbd_pilot.quotes import repair

TEXT = ("Wir fordern: Paket-\nboten wirksam schützen und die Qualität der Paketzustellung "
        "verbessern. Außerdem muss der ÖPNV im ländlichen Raum ausgebaut werden.")


def test_repair_bridges_pdf_hyphenation_and_returns_source_text():
    span = repair("Paketboten wirksam schützen und die Qualität der Paketzustellung verbessern", TEXT)
    assert span is not None
    assert TEXT[span[0]:span[1]].startswith("Paket-\nboten wirksam")
    assert TEXT[span[0]:span[1]].endswith("verbessern")


def test_repair_rejects_unrelated_or_short_quotes():
    assert repair("Die Bahn fährt pünktlich und ist immer sauber gewesen", TEXT) is None
    assert repair("ÖPNV", TEXT) is None


BUS = "Der Bus kommt am Abend nur noch alle zwei Stunden. Das ist ein Problem für Pendler."
# 13 inserted characters: the best source passage is 49 / 62 = 0.79 times the quote's length.
LONG_QUOTE = "Der Bus kommt am Abe" + "x" * 13 + "nd nur noch alle zwei Stunden"


def test_repair_length_ratio_is_a_parameter():
    assert repair(LONG_QUOTE, BUS, min_score=0) is None
    span = repair(LONG_QUOTE, BUS, min_score=0, min_length_ratio=0.75)
    assert span is not None
    assert BUS[span[0]:span[1]] == "Der Bus kommt am Abend nur noch alle zwei Stunden"
    assert repair(LONG_QUOTE, BUS, min_score=0, min_length_ratio=0.75, max_length_ratio=0.78) is None


def test_repair_min_score_is_a_parameter():
    quote = "Paketboten wirksam schützen und die Qualität der Paketzustellung verbessern"
    assert repair(quote, TEXT) is not None
    assert repair(quote, TEXT, min_score=100) is None


def test_repair_defaults_unchanged():
    from jtbd_pilot import quotes

    assert (quotes.REPAIR_MIN_SCORE, quotes.REPAIR_MIN_LENGTH_RATIO,
            quotes.REPAIR_MAX_LENGTH_RATIO) == (90.0, 0.8, 1.25)
