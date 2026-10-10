"""Usage class, licence list and derivation (feature 011, T011). No network."""

from pathlib import Path

import pytest

from mobility_model_zoo.compliance.usage import (
    COMMERCIAL,
    NON_COMMERCIAL,
    Derivation,
    LicenceList,
    RestrictingInput,
    UsageClass,
    name_findings,
    release_findings,
    resolve_source_licence,
)

ROOT = Path(__file__).resolve().parents[2]
SA = UsageClass(commercial=True, share_alike=True)
NC_SA = UsageClass(commercial=False, share_alike=True)


def licences():
    return LicenceList.from_records([
        {"id": "Apache-2.0"},
        {"id": "CC-BY-4.0"},
        {"id": "CC-BY-SA-4.0", "share_alike": True, "release_licences": ["CC-BY-SA-4.0"]},
        {"id": "CC-BY-NC-4.0", "non_commercial": True},
        {"id": "CC-BY-NC-SA-4.0", "non_commercial": True, "share_alike": True,
         "release_licences": ["CC-BY-NC-SA-4.0"]},
        {"id": "LicenseRef-Open-Parliament-Licence"},
    ])


@pytest.mark.parametrize("value", ["commercial", "commercial-share-alike", "non-commercial",
                                   "non-commercial-share-alike"])
def test_parse_round_trip(value):
    assert str(UsageClass.parse(value)) == value


def test_parse_refuses_unknown_value():
    with pytest.raises(ValueError):
        UsageClass.parse("research-only")


def test_combine_is_most_restrictive():
    assert COMMERCIAL.combine(NON_COMMERCIAL) == NON_COMMERCIAL
    assert SA.combine(NON_COMMERCIAL) == NC_SA
    assert COMMERCIAL.combine(COMMERCIAL) == COMMERCIAL


@pytest.mark.parametrize("a,b,expected", [
    (NON_COMMERCIAL, COMMERCIAL, True),
    (COMMERCIAL, NON_COMMERCIAL, False),
    (NC_SA, SA, True),
    (NON_COMMERCIAL, SA, False),
    (SA, COMMERCIAL, True),
])
def test_covers(a, b, expected):
    assert a.covers(b) is expected


def test_licence_list_validation():
    bad = LicenceList.from_records([{"id": "X-SA", "share_alike": True},
                                    {"id": "Y-SA", "share_alike": True, "release_licences": ["Z"]}])
    assert len(bad.errors()) == 2
    assert LicenceList.load(ROOT).errors() == []


def test_real_licence_list_has_nc_entries():
    real = LicenceList.load(ROOT)
    assert real.get("CC-BY-NC-4.0").non_commercial
    assert real.get("CC-BY-NC-SA-4.0").release_licences == ("CC-BY-NC-SA-4.0",)
    assert real.get("CC-BY-NC-ND-4.0") is None  # no-derivatives is never listed


class Declared:
    def __init__(self, license):
        self.license = license


def test_resolution_order():
    lic = licences()
    source = {"origin": "https://example.org/a", "license": "Open Parliament Licence v3.0",
              "dataset": "ds"}
    # 1. dataset declaration wins
    assert resolve_source_licence(source, lic, {"ds": Declared("CC-BY-4.0")}, {}) == "CC-BY-4.0"
    # 2. compliance record of the same origin
    by_origin = {"https://example.org/a": {"licence": "CC-BY-SA-4.0"}}
    assert resolve_source_licence({**source, "dataset": None}, lic, {}, by_origin) == "CC-BY-SA-4.0"
    # 3./4. the string itself, then the free-text mapping
    assert resolve_source_licence({"license": "Apache-2.0"}, lic) == "Apache-2.0"
    assert resolve_source_licence({**source, "dataset": None}, lic) == \
        "LicenseRef-Open-Parliament-Licence"
    # unresolved: the best candidate comes back and is not on the list
    assert lic.get(resolve_source_licence({"license": "some licence"}, lic)) is None


def deriv(*inputs):
    d = Derivation()
    for i in inputs:
        d.add(i)
    return d


def test_nc_input_on_commercial_model_is_c_u2():
    d = deriv(RestrictingInput("dataset", "tue-can-v2", "CC-BY-NC-4.0", NON_COMMERCIAL))
    findings = release_findings(COMMERCIAL, "Apache-2.0", d, licences())
    assert [f.check_id for f in findings] == ["C-K2"]
    assert "tue-can-v2" in findings[0].reason and "CC-BY-NC-4.0" in findings[0].reason


def test_nc_model_with_nc_licence_passes():
    d = deriv(RestrictingInput("dataset", "tue-can-v2", "CC-BY-NC-4.0", NON_COMMERCIAL))
    assert release_findings(NON_COMMERCIAL, "CC-BY-NC-4.0", d, licences()) == []


def test_release_licence_must_mark_the_class():
    d = deriv(RestrictingInput("dataset", "x", "CC-BY-NC-4.0", NON_COMMERCIAL))
    assert [f.check_id for f in release_findings(NON_COMMERCIAL, "Apache-2.0", d, licences())] == \
        ["C-K3"]


def test_share_alike_nc_needs_nc_sa_licence():
    item = RestrictingInput("dataset", "dcase", "CC-BY-NC-SA-4.0", NC_SA, ("CC-BY-NC-SA-4.0",))
    assert release_findings(NC_SA, "CC-BY-NC-SA-4.0", deriv(item), licences()) == []
    checks = [f.check_id for f in release_findings(NON_COMMERCIAL, "CC-BY-NC-4.0", deriv(item),
                                                   licences())]
    assert "C-K2" in checks  # the share-alike term was dropped


def test_share_alike_conflict_names_both_inputs():
    a = RestrictingInput("dataset", "mimii", "CC-BY-SA-4.0", SA, ("CC-BY-SA-4.0",))
    b = RestrictingInput("dataset", "dcase", "CC-BY-NC-SA-4.0", NC_SA, ("CC-BY-NC-SA-4.0",))
    findings = release_findings(NC_SA, "CC-BY-NC-SA-4.0", deriv(a, b), licences())
    conflict = [f for f in findings if "no single release licence" in f.reason]
    assert conflict and "mimii" in conflict[0].reason and "dcase" in conflict[0].reason


def test_owner_may_choose_a_stricter_class():
    d = deriv(RestrictingInput("dataset", "road", "CC-BY-4.0", COMMERCIAL))
    assert release_findings(NON_COMMERCIAL, "CC-BY-NC-4.0", d, licences()) == []


@pytest.mark.parametrize("name,variant,cls,ok", [
    ("picket-forest", "forest", COMMERCIAL, True),
    ("picket-forest-nc", "forest", COMMERCIAL, False),
    ("picket-forest-nc", "forest", NON_COMMERCIAL, True),
    ("picket-forest", "forest", NON_COMMERCIAL, False),
])
def test_name_suffix(name, variant, cls, ok):
    assert (name_findings(name, variant, cls) == []) is ok
