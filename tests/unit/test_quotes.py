from mobility_model_zoo.productdev.jtbd.quotes import locate

TEXT = (
    "Er sagte: „Der Bus kommt\n  nie pünktlich.“ Danach fuhr er Rad. "
    "Der Bus kommt nie pünktlich."
)


def test_exact_match():
    assert locate("Danach fuhr er Rad.", TEXT) == (TEXT.index("Danach"), TEXT.index("Rad.") + 4)


def test_whitespace_and_typographic_quotes_normalized():
    span = locate('"Der Bus kommt nie pünktlich."', TEXT)
    assert span is not None
    assert TEXT[span[0]:span[1]].startswith("„Der Bus")


def test_paraphrase_and_translation_fail():
    assert locate("Der Bus ist nie pünktlich.", TEXT) is None
    assert locate("The bus is never on time.", TEXT) is None


def test_first_unused_occurrence_is_taken():
    first = locate("Der Bus kommt nie pünktlich.", TEXT)
    second = locate("Der Bus kommt nie pünktlich.", TEXT, used=[first])
    assert first != second
    assert second[0] > first[0]
