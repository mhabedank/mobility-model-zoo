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
