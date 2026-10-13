"""The roadmap record and its checks RM1-RM8 (feature 015, contracts/checks.md), each with a
deliberate fault in a copy of the fixture registry."""

from __future__ import annotations

from datetime import date

import pytest

from mobility_model_zoo.release.errors import GateFailed
from mobility_model_zoo.site import roadmap

RECORD = "zoo/roadmap/roadmap.yaml"


def entry(record, entry_id):
    return next(e for e in record["entries"] if e["id"] == entry_id)


def findings(env, fn=None, day=None):
    """Apply `fn` to the fixture record, then return every RM finding."""
    if fn:
        env.edit_yaml(RECORD, fn)
    try:
        record = roadmap.load(env.reg)
    except GateFailed as e:
        return e.failures
    return roadmap.validate(env.reg, record, day)


def publish(env, model, version="0.1.0", when="2026-11-20T10:00:00Z"):
    """A published release record for `model` (enough for the roadmap's delivery rules)."""
    path = env.root / "zoo" / "models" / model / "releases" / f"{version}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"model: {model}\nversion: {version}\ndate: {when[:10]}\nstatus: experimental\n"
        f"published:\n  tag: v{version}\n  published_at: {when}\n",
        encoding="utf-8",
    )


def test_fixture_is_clean(site_env):
    assert findings(site_env) == []


# ---- RM1 --------------------------------------------------------------------------------------
def test_rm1_missing(site_env):
    (site_env.root / RECORD).unlink()
    assert findings(site_env) == [f"RM1 {RECORD} is missing"]


def test_rm1_unknown_key(site_env):
    out = findings(site_env, lambda r: entry(r, "hum-bearing").update(colour="mint"))
    assert any(f.startswith("RM1") and "colour" in f for f in out)


def test_rm1_duplicate_id(site_env):
    out = findings(site_env, lambda r: r["entries"].append(dict(entry(r, "hum-bearing"))))
    assert "RM1 entries: duplicate id hum-bearing" in out


# ---- delivery, timing, usage ------------------------------------------------------------------
def test_first_release_is_delivered_by_publishing(site_env):
    publish(site_env, "picket-forest", when="2026-11-20T10:00:00Z")
    record = roadmap.load(site_env.reg)
    e = entry(record, "picket-forest")
    assert roadmap.state(site_env.reg, e) == "delivered"
    assert roadmap.delivery_date(site_env.reg, e) == date(2026, 11, 20)
    assert roadmap.timing(e, date(2026, 11, 20)) == ("on time", None, None)


def test_update_needs_delivered_by(site_env):
    record = roadmap.load(site_env.reg)
    e = entry(record, "scout-large-reader-test")
    assert roadmap.state(site_env.reg, e) == "open"  # scout-large is published, the update is not


def test_timing():
    e = {"planned": "2027-Q1..Q2"}
    assert roadmap.timing(e, date(2026, 12, 1)) == ("early", None, None)
    assert roadmap.timing(e, date(2027, 6, 30)) == ("on time", None, None)
    assert roadmap.timing(e, date(2027, 7, 10)) == ("late", 10, 1)
    assert roadmap.timing(e, date(2027, 10, 2)) == ("late", 94, 2)


def test_dropped_wins(site_env):
    record = roadmap.load(site_env.reg)
    e = entry(record, "hum-bearing")
    e["dropped"] = {"date": "2026-11-01", "reason": "No usable data."}
    assert roadmap.state(site_env.reg, e) == "dropped"


def test_usage_label(site_env):
    site_env.edit_yaml(
        "zoo/models/picket-forest/model.yaml", lambda m: m.update(usage_class="commercial-share-alike")
    )
    record = roadmap.load(site_env.reg)
    assert roadmap.usage_label(site_env.reg, entry(record, "picket-forest")) == "share-alike"
    assert roadmap.usage_label(site_env.reg, entry(record, "hum-bearing")) is None


# ---- RM2 --------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("fault", "expected"),
    [
        (lambda r: r["entries"].remove(entry(r, "picket-forest")), "RM2 picket-forest: registered"),
        (lambda r: entry(r, "picket-forest").update(model="no-such-model"), "is not a registered model"),
        (lambda r: entry(r, "hum-bearing").update(topic="sandbox"), "is not a zoo topic"),
        (lambda r: entry(r, "picket-forest").update(topic="productdev"), "differs from the topic"),
        (lambda r: entry(r, "picket-forest").update(kind="update"), "has no published version"),
        (
            lambda r: entry(r, "picket-signal").update(model="picket-forest", working_name=True),
            "set working_name: false",
        ),
    ],
)
def test_rm2(site_env, fault, expected):
    assert any(f.startswith("RM2") and expected in f for f in findings(site_env, fault))


# ---- RM3 --------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("field", "text", "expected"),
    [
        ("text", " ".join(["word"] * 21), "has 21 words, limit 20"),
        ("text", "Runs 2 times faster than before.", "literal number '2'"),
        ("precondition", " ".join(["word"] * 9), "has 9 words, limit 8"),
        ("text", "Reaches {metric:quality.f1} on the benchmark.", "metric placeholder"),
        ("text", "Gets released after the reader test.", "release-status word 'released'"),
    ],
)
def test_rm3(site_env, field, text, expected):
    out = findings(site_env, lambda r: entry(r, "hum-bearing").update({field: text}))
    assert any(f.startswith(f"RM3 hum-bearing.{field}") and expected in f for f in out)


# ---- RM4 --------------------------------------------------------------------------------------
def _move(r):
    entry(r, "hum-bearing").update(
        horizon="2027-Q3..Q4",
        moves=[{"date": "2026-11-01", "to": "2027-Q1..Q2", "reason": "Waiting for data."}],
    )


def _seven(r):
    base = entry(r, "picket-signal")
    for i in range(7):
        r["entries"].append({**base, "id": f"extra-{i}", "name": f"extra-{i}"})


def _dropped_and_delivered(r):
    entry(r, "picket-forest")["dropped"] = {"date": "2026-11-01", "reason": "Stopped."}


@pytest.mark.parametrize(
    ("fault", "expected"),
    [
        (lambda r: r.update(horizons=["2026-Q4", "2027-Q1..Q2", "2027-Q4..2028-Q1"]), "does not follow"),
        (
            lambda r: r.update(horizons=["2026-Q4..2027-Q1", "2027-Q2..Q3", "2027-Q4..2028-Q1"]),
            "one quarter",
        ),
        (_move, "the last move goes to 2027-Q1..Q2"),
        (lambda r: entry(r, "hum-bearing").update(horizon="2027-Q3..Q4"), "no move is recorded"),
        (
            lambda r: entry(r, "hum-bearing").update(planned="2028-Q1..Q2", horizon="2028-Q1..Q2"),
            "is not one of",
        ),
        (_seven, "holds 8 open entries, limit 6"),
    ],
)
def test_rm4(site_env, fault, expected):
    assert any(f.startswith("RM4") and expected in f for f in findings(site_env, fault))


def test_rm4_two_horizons_is_rm1(site_env):
    out = findings(site_env, lambda r: r.update(horizons=["2026-Q4", "2027-Q1..Q2"]))
    assert any(f.startswith("RM1") and "horizons" in f for f in out)


def test_rm4_dropped_and_delivered(site_env):
    publish(site_env, "picket-forest")
    out = findings(site_env, _dropped_and_delivered)
    assert any("dropped and delivered at once" in f for f in out)


def test_rm4_correct_move_passes(site_env):
    def move(r):
        entry(r, "hum-bearing").update(
            horizon="2027-Q3..Q4",
            moves=[{"date": "2026-11-01", "to": "2027-Q3..Q4", "reason": "Waiting for data."}],
        )

    assert findings(site_env, move) == []


# ---- RM6 --------------------------------------------------------------------------------------
def test_rm6_ended_horizon(site_env):
    out = findings(site_env, day=date(2027, 1, 5))
    assert any(f.startswith("RM6 picket-forest: open entry in 2026-Q4") for f in out)


def test_rm6_age(site_env):
    assert not [f for f in findings(site_env, day=date(2026, 12, 31)) if f.startswith("RM6 as_of")]
    site_env.edit_yaml(RECORD, lambda r: r.update(as_of="2026-09-01"))
    record = roadmap.load(site_env.reg)
    assert not roadmap.check_stale(site_env.reg, record, date(2026, 12, 10))  # 100 days
    out = roadmap.check_stale(site_env.reg, record, date(2026, 12, 11))  # 101 days
    assert any("is 101 days old, limit 100" in f for f in out)


def test_rm6_future(site_env):
    out = findings(site_env, lambda r: r.update(as_of="2026-10-13"))
    assert any("is in the future" in f for f in out)


def test_rm6_warning(site_env):
    record = roadmap.load(site_env.reg)
    assert roadmap.validate(site_env.reg, record, date(2026, 12, 20)) == []
    assert roadmap.warnings(record, date(2026, 12, 20))[0].startswith("RM6 warning: Q4 2026 ends")
    assert roadmap.warnings(record, date(2026, 10, 12)) == []


# ---- RM8 --------------------------------------------------------------------------------------
def test_rm8(site_env):
    out = findings(
        site_env,
        lambda r: entry(r, "scout-large-reader-test").update(
            delivered_by={"model": "scout-large", "version": "9.9.9"}
        ),
    )
    assert "RM8 scout-large-reader-test: scout-large 9.9.9 is not published" in out


def test_rm8_delivered_update(site_env):
    def deliver(r):
        entry(r, "scout-large-reader-test")["delivered_by"] = {
            "model": "scout-large",
            "version": "0.1.2",
        }

    assert findings(site_env, deliver) == []
    record = roadmap.load(site_env.reg)
    assert roadmap.state(site_env.reg, entry(record, "scout-large-reader-test")) == "delivered"


# ---- RM7 --------------------------------------------------------------------------------------
ROLLED = {"horizons": ["2027-Q1", "2027-Q2..Q3", "2027-Q4..2028-Q1"]}


def _roll(r):
    r.update(ROLLED)
    for e in r["entries"]:
        if e["horizon"] == "2026-Q4":
            e["moves"] = [{"date": "2027-01-02", "to": "2027-Q1", "reason": "Not finished."}]
            e["horizon"] = "2027-Q1"
        elif e["horizon"] == "2027-Q1..Q2":
            e["moves"] = [{"date": "2027-01-02", "to": "2027-Q2..Q3", "reason": "Horizons rolled."}]
            e["horizon"] = "2027-Q2..Q3"
        elif e["horizon"] == "2027-Q3..Q4":
            e["moves"] = [{"date": "2027-01-02", "to": "2027-Q4..2028-Q1", "reason": "Horizons rolled."}]
            e["horizon"] = "2027-Q4..2028-Q1"


def test_rm7_review_required(site_env):
    out = findings(site_env, _roll, day=date(2027, 1, 5))
    assert any(f.startswith("RM7 zoo/roadmap/reviews/2026-Q4.md missing") for f in out)


def test_rm7_empty_replanning(site_env):
    review = site_env.root / "zoo" / "roadmap" / "reviews" / "2026-Q4.md"
    review.parent.mkdir(parents=True)
    review.write_text(f"# Pace review\n\n{roadmap.REPLANNING}\n\n{roadmap.REPLANNING_PLACEHOLDER}\n")
    out = findings(site_env, _roll, day=date(2027, 1, 5))
    assert any(f.startswith("RM7") and "is empty" in f for f in out)


def test_rm7_filled_review_passes(site_env):
    review = site_env.root / "zoo" / "roadmap" / "reviews" / "2026-Q4.md"
    review.parent.mkdir(parents=True)
    review.write_text(
        f"# Pace review\n\n{roadmap.REPLANNING}\n\nWe were slower; Q1 keeps two entries.\n"
    )
    site_env.edit_yaml(RECORD, lambda r: r.update(as_of="2027-01-02"))
    assert findings(site_env, _roll, day=date(2027, 1, 5)) == []
