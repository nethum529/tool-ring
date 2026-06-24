import math
import tool_ring as cg


def test_parse_cursorpos():
    assert cg.parse_cursorpos("523, 582") == (523, 582)
    assert cg.parse_cursorpos(" 10 ,  20 \n") == (10, 20)


def test_hit_test_inside():
    assert cg.hit_test(100, 100, 100, 100, 24) is True
    assert cg.hit_test(120, 100, 100, 100, 24) is True


def test_hit_test_outside():
    assert cg.hit_test(200, 200, 100, 100, 24) is False
    assert cg.hit_test(125, 100, 100, 100, 24) is False


def test_resolve_monitor_single():
    mons = [{"x": 0, "y": 0, "width": 1920, "height": 1080}]
    idx, lx, ly = cg.resolve_monitor(500, 400, mons)
    assert (idx, lx, ly) == (0, 500, 400)


def test_resolve_monitor_picks_second_and_localizes():
    mons = [
        {"x": 0, "y": 0, "width": 1920, "height": 1080},
        {"x": 1920, "y": 0, "width": 2560, "height": 1440},
    ]
    idx, lx, ly = cg.resolve_monitor(2000, 300, mons)
    assert idx == 1
    assert lx == 2000 - 1920
    assert ly == 300


def test_resolve_monitor_fallback_when_outside_all():
    mons = [{"x": 0, "y": 0, "width": 1920, "height": 1080}]
    idx, lx, ly = cg.resolve_monitor(9999, 9999, mons)
    assert idx == 0


def test_ring_positions_count_and_top():
    pts = cg.ring_positions(100, 100, 70, 3)
    assert len(pts) == 3
    # first point is straight up (top): same x, y above center
    assert round(pts[0][0], 3) == 100
    assert pts[0][1] < 100


def test_place_ring_center_clamps():
    # near top-left corner -> pushed in by margin
    cx, cy = cg.place_ring_center(5, 5, 1920, 1080, 70, 24)
    assert cx == 70 + 24 + 4
    assert cy == 70 + 24 + 4


def test_place_ring_center_unclamped_middle():
    assert cg.place_ring_center(500, 400, 1920, 1080, 70, 24) == (500, 400)


def test_item_at_hits_and_misses():
    centers = [(100, 100), (300, 100)]
    assert cg.item_at(100, 100, centers, 24) == 0
    assert cg.item_at(300, 100, centers, 24) == 1
    assert cg.item_at(700, 700, centers, 24) == -1
