from dataclasses import dataclass

from jtbd_pilot.matching import iou, match_items


@dataclass
class It:
    span: tuple | None
    kind: str


def test_iou():
    assert iou((0, 10), (5, 15)) == 5 / 15
    assert iou((0, 10), (20, 30)) == 0.0


def test_one_to_one_hungarian():
    a = [It((0, 10), "pain"), It((20, 30), "job")]
    b = [It((0, 9), "pain"), It((21, 30), "job"), It((50, 60), "gain")]
    matches = match_items(a, b, 0.3)
    pairs = [(m.a, m.b) for m in matches if m.a and m.b]
    assert pairs == [(a[0], b[0]), (a[1], b[1])]
    assert [m.b for m in matches if m.a is None] == [b[2]]


def test_kind_breaks_exact_ties_only():
    a = [It((0, 10), "pain")]
    same_kind_lower = It((0, 9), "pain")  # IoU 0.9
    other_kind_higher = It((0, 10), "job")  # IoU 1.0
    m = match_items(a, [same_kind_lower, other_kind_higher], 0.3)
    assert [x.b for x in m if x.a] == [other_kind_higher]
    tie_same = It((0, 10), "pain")
    m = match_items(a, [other_kind_higher, tie_same], 0.3)
    assert [x.b for x in m if x.a] == [tie_same]


def test_below_min_iou_unmatched_and_invalid_excluded():
    a = [It((0, 10), "pain"), It(None, "job")]
    b = [It((8, 30), "pain")]  # IoU 2/30
    matches = match_items(a, b, 0.3)
    assert all(m.a is None or m.b is None for m in matches)
    assert len(matches) == 2  # invalid item is not part of matching
