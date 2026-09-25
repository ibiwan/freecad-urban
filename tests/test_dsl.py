"""Checks for the turtle DSL. Run: ./fp test  (or any Python with shapely + numpy)."""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flatpack import turtle as T  # noqa: E402
from flatpack.turtle import DSLError, Turtle  # noqa: E402
from shapely.geometry import Point, Polygon  # noqa: E402

O = Turtle()


def close(a, b, tol=1e-9):
    return np.allclose(np.asarray(a, float), np.asarray(b, float), atol=tol)


def raises(fn, text=""):
    try:
        fn()
    except DSLError as e:
        assert text in str(e), f"wrong message: {e}"
        return
    raise AssertionError("expected DSLError")


def build(part):
    b = T.begin("test")
    try:
        T.t.place(part)
    finally:
        T.end(b)
    return b.finish()


def world_pts(chip):
    """The chip outline's vertices in world space."""
    xy = np.array(chip.geom.exterior.coords)
    pts = np.c_[xy, np.zeros(len(xy)), np.ones(len(xy))]
    return (chip.matrix @ pts.T).T[:, :3]


# -- every verb is positive in its named direction --------------------------------

def test_moves():
    assert close(O.forward(1).pos, [0, 1, 0])
    assert close(O.right(1).pos, [1, 0, 0])
    assert close(O.up(1).pos, [0, 0, 1])
    assert close(O.back(1).pos, [0, -1, 0])
    assert close(O.left(1).pos, [-1, 0, 0])
    assert close(O.down(1).pos, [0, 0, -1])


def test_turns():
    assert close(O.nose_up(90).forward(1).pos, [0, 0, 1])       # nose up
    assert close(O.nose_right(90).forward(1).pos, [1, 0, 0])    # nose right
    assert close(O.roll_right(90).right(1).pos, [0, 0, -1])     # right side down
    assert close(O.nose_down(90).forward(1).pos, [0, 0, -1])
    assert close(O.nose_left(90).forward(1).pos, [-1, 0, 0])
    assert close(O.roll_left(90).right(1).pos, [0, 0, 1])


def test_moves_are_local():
    assert close(O.nose_right(90).right(1).pos, [0, -1, 0])
    assert close(O.nose_up(90).up(1).pos, [0, -1, 0])
    a = O.nose_right(37).nose_up(12).roll_right(-50)
    assert close(a.forward(2).back(2).pos, [0, 0, 0])


def test_immutable():
    a = O.forward(1)
    a.nose_up(30).right(5)
    assert close(a.pos, [0, 1, 0]) and close(a.rot, np.eye(3))
    assert close(O.pos, [0, 0, 0])


def test_no_drift():
    a = O
    for _ in range(3600):
        a = a.nose_right(0.1).nose_up(0.1).roll_right(0.1)
    assert close(a.rot.T @ a.rot, np.eye(3), 1e-12)


def test_aim():
    a = O.aim(1, 2, 1, 5)
    assert close(a.pos, [1, 2, 0]) and close(a.rot, np.eye(3))       # already facing forward
    a = O.aim(0, 0, 1, 1)
    assert close(a.rot[:, 1], [2 ** -0.5, 2 ** -0.5, 0])
    assert close(a.rot[:, 2], [0, 0, 1])                              # up unchanged
    raises(lambda: O.aim(1, 1, 1, 1), "two different points")
    # From any turtle, walking the edge's length lands on the far point.
    for base in (O, O.nose_right(37).nose_up(12).roll_right(-50).up(3),
                 O.mirrored("x").nose_up(20).right(2)):
        x0, y0, x1, y1 = 0.5, 2, 3, 3.25
        end = base.aim(x0, y0, x1, y1).forward(math.hypot(x1 - x0, y1 - y0))
        assert close(end.pos, base.right(x1).forward(y1).pos), base
        assert close(base.aim(x0, y0, x1, y1).rot[:, 2], base.rot[:, 2])


def taper(tt):
    return (tt.wire().jump(0, 0).line(0, 1, "A").line(3, 2.5, "B").line(3, 0, "C").close())


def test_named_points():
    o = taper(O.up(2))
    assert o.point("B") == (3, 2.5)
    assert close(o.at("A").pos, [0, 1, 2])
    assert close(o.aim("A", "B").forward(math.hypot(3, 1.5)).pos, [3, 2.5, 2])
    raises(lambda: o.point("Z"), "no point named 'Z'")
    assert abs(o.distance("A", "B") - math.hypot(3, 1.5)) < 1e-12
    assert abs(o.distance("A", (0, 0)) - 1) < 1e-12
    w = O.wire().jump(0, 0, "P").line(3, 4, "Q")          # works mid-wire too
    assert w.distance("P", "Q") == 5
    raises(lambda: O.wire().jump(0, 0, "A").line(1, 0, "A"), "already used")
    # names survive subtraction, including ones from a hole drawn with another turtle
    hole = O.up(2).right(1).forward(1 / 2).wire().jump(0, 0, "H").line(1 / 4, 0).line(0, 1 / 4).close()
    cut = o - hole
    assert close(cut.point("H"), [1, 0.5]) and cut.point("A") == (0, 1)


def test_on_edge_finds_outside():
    o = taper(O)
    up = o.on_edge("A", "B").rot[:, 2]
    assert abs(up @ [3, 1.5, 0]) < 1e-9 and up[1] > 0 and abs(up[2]) < 1e-9   # out, not in
    up = o.on_edge("B", "A").rot[:, 2]                                         # either order
    assert up[1] > 0 and abs(up[2]) < 1e-9
    e = o.on_edge("A", "B")
    assert close(e.pos, [0, 1, 0]) and close(e.rot[:, 0], [0, 0, 1]) or close(e.rot[:, 0], [0, 0, -1])
    raises(lambda: o.on_edge("A", "C"), "isn't an edge")
    # mirrored and tilted turtles still point out
    for base in (O.mirrored("x").nose_up(30), O.roll_right(70).nose_right(20)):
        ob = taper(base)
        e = ob.on_edge("A", "B")
        probe = e.up(1e-3).pos                       # a hair outside the face
        local = np.linalg.inv(base.matrix) @ np.r_[probe, 1]
        assert not ob.geom.contains(Point(local[0], local[1]))


def test_frame():
    f = O.frame((0, 0, 0), (0, 1, 0), (0, 0, 1))
    assert close(f.rot, np.eye(3)) and close(f.pos, [0, 0, 0])
    # p2 only needs to be on the up side: its component along the aim is dropped
    f = O.frame((1, 1, 1), (4, 1, 1), (9, 1, 3))
    assert close(f.pos, [1, 1, 1]) and close(f.rot[:, 1], [1, 0, 0]) and close(f.rot[:, 2], [0, 0, 1])
    assert close(f.rot[:, 0], [0, -1, 0]) and np.linalg.det(f.rot) > 0      # right = forward x up
    # points are relative to the turtle it's called on
    base = O.nose_right(30).nose_up(15).up(2)
    f = base.frame((0, 0, 0), (0, 1, 0), (0, 0, 1))
    assert close(f.rot, base.rot) and close(f.pos, base.pos)
    raises(lambda: O.frame((0, 0, 0), (0, 0, 0), (1, 0, 0)), "different points")
    raises(lambda: O.frame((0, 0, 0), (1, 0, 0), (3, 0, 0)), "on the line")


def test_frame_from_outline_points():
    # Two stacked squares; a frame on one's edge, facing along it, up toward the other.
    sq = lambda tt: tt.wire().jump(0, 0, "a").line(0, 2, "b").line(2, 2).line(2, 0).close()
    o1, o2 = sq(O), sq(O.up(3))
    assert close(o2.world("b").pos, [0, 2, 3])
    f = O.frame(o1.world("a"), o1.world("b"), o2.world("a"))
    assert close(f.pos, [0, 0, 0]) and close(f.rot[:, 1], [0, 1, 0]) and close(f.rot[:, 2], [0, 0, 1])


def test_frame_mirrors():
    def panel():
        T.t.wire().jump(0, 0).line(2, 0).line(2, 1).line(0, 3).close().chip()

    def both():
        T.t.right(1).frame((0, 0, 0), (1, 2, 0), (0, 0, 1)).place(panel)
        T.t.mirrored("x").right(1).frame((0, 0, 0), (1, 2, 0), (0, 0, 1)).place(panel)

    m = build(both)
    pa = world_pts(m.chips["both/panel#1"]) * [-1, 1, 1]
    pb = world_pts(m.chips["both/panel#2"])
    for p in pa:
        assert np.min(np.linalg.norm(pb - p, axis=1)) < 1e-9


# -- mirroring ------------------------------------------------------------------

def test_mirrored():
    m = O.mirrored("x")
    assert close(m.right(1).pos, [-1, 0, 0])
    assert close(m.nose_right(90).forward(1).pos, [-1, 0, 0])   # turns left in the world
    assert close(m.forward(1).pos, [0, 1, 0])
    assert close(O.mirrored("x").mirrored("x").rot, np.eye(3))
    assert close(O.pos, [0, 0, 0]) and close(O.rot, np.eye(3))  # original untouched


def test_mirrored_chip_is_reflection():
    def plate():
        T.t.wire().jump(0, 0).line(2, 0).line(2, 1).line(0, 3).close().chip()

    def both():
        T.t.right(1).nose_up(20).place(plate)
        T.t.mirrored("x").right(1).nose_up(20).place(plate)

    m = build(both)
    a, b = m.chips["both/plate#1"], m.chips["both/plate#2"]
    assert b.mirrored and not a.mirrored
    assert np.linalg.det(b.matrix[:3, :3]) > 0                  # stored as a proper rotation
    pa = world_pts(a) * [-1, 1, 1]                              # reflect a across x=0
    pb = world_pts(b)
    for p in pa:                                                # same vertex set
        assert np.min(np.linalg.norm(pb - p, axis=1)) < 1e-9


# -- wires ----------------------------------------------------------------------

def test_arc():
    w = O.wire().jump(0, 1).arc(0, 0, 90)                        # forward -> right: clockwise
    assert close(w.pts[-1], [1, 0])
    mid = w.pts[len(w.pts) // 2]
    assert mid[0] > 0 and mid[1] > 0 and abs(math.hypot(*mid) - 1) < 1e-12
    w = O.wire().jump(1, 0).arc(0, 0, -90)                       # right -> forward: counterclockwise
    assert close(w.pts[-1], [0, 1])
    w = O.wire().jump(1 / 2, 4).arc(0, 4, -180)                   # radius from the pen: 1/2
    assert close(w.pts[-1], [-1 / 2, 4]) and max(p[1] for p in w.pts) >= 4.5 - T.ARC_TOLERANCE
    w = O.wire().jump(3, 4).arc(0, 0, 360)                       # full turn ends where it began
    assert close(w.pts[-1], [3, 4])
    w = O.wire().jump(1, 0).arc(0, 0, 0, "here")                 # 0 is a no-op; still names the point
    assert w.pts == ((1.0, 0.0),) and w.point("here") == (1.0, 0.0)


def test_arc_errors():
    raises(lambda: O.wire().arc(0, 0, 90), "begin the wire with jump")
    raises(lambda: O.wire().jump(0, 0).arc(0, 0, 90), "needs a radius")
    raises(lambda: O.wire().jump(1, 0).arc(0, 0, 361), "between -360 and 360")
    raises(lambda: O.wire().jump(1, 0).arc(0, 0, -400), "between -360 and 360")


def test_circle():
    c = O.circle(1, 2, 0.5)
    assert abs(c.geom.area - math.pi * 0.25) < 0.01
    assert close(c.geom.centroid.coords[0], [1, 2], 1e-6)


def test_close_adds_last_segment():
    o = O.wire().jump(0, 0).line(2, 0).line(2, 2).close()
    assert abs(o.geom.area - 2) < 1e-12


def test_wire_errors():
    raises(lambda: O.wire().line(1, 1), "jump")
    raises(lambda: O.wire().jump(0, 0).jump(1, 1), "starts a wire")
    raises(lambda: O.wire().jump(0, 0).line(1, 0).close(), "at least 3")
    raises(lambda: O.wire().jump(0, 0).line(1, 1).line(1, 0).line(0, 1).close(), "crosses itself")


# -- outlines -------------------------------------------------------------------

def test_subtract_across_frames():
    outer = O.wire().jump(-1, -1).line(1, -1).line(1, 3).line(-1, 3).close()
    hole = O.forward(2).nose_right(45).circle(0, 0, 0.25)       # coplanar, different frame
    r = outer - hole
    assert len(r.geom.interiors) == 1
    assert close(r.geom.interiors[0].centroid.coords[0], [0, 2], 1e-6)


def test_subtract_needs_same_plane():
    outer = O.wire().jump(0, 0).line(1, 0).line(1, 1).close()
    raises(lambda: outer - O.up(0.1).circle(0, 0, 0.1), "same plane")
    raises(lambda: outer - O.nose_up(5).circle(0, 0, 0.1), "same plane")


def test_no_slivers_at_odd_angles():
    # Cutting flush with an edge from a turtle at an odd angle used to leave a
    # 1e-65 in² sliver that counted as a second piece.
    rect = lambda tt, w, h: tt.wire().jump(-w / 2, 0).line(-w / 2, h).line(w / 2, h).line(w / 2, 0).close()
    for angle in (45, 30, 17.3, 60):
        base = O.up(0.5).nose_right(angle)
        big = rect(base.left(0.625).nose_down(90).down(1 / 16), 1.25, 0.375)
        cut = rect(base.nose_down(90).down(1 / 16), 0.625, 0.375)
        r = big - cut
        assert isinstance(r.geom, Polygon), (angle, r.geom.geom_type)
        assert abs(r.geom.area - 0.9375 * 0.375) < 1e-9
    # a genuinely separate piece is still two pieces
    both = rect(O, 1, 1) + rect(O.right(3), 1, 1)
    assert both.geom.geom_type == "MultiPolygon"


def test_two_piece_chip():
    def p():
        a = T.t.wire().jump(0, 0).line(3, 0).line(3, 1).line(0, 1).close()
        cut = T.t.wire().jump(1, -1).line(2, -1).line(2, 2).line(1, 2).close()
        (a - cut).chip()
    raises(lambda: build(p), "2 separate pieces")


# -- parts and naming -------------------------------------------------------------

def square():
    T.t.wire().jump(0, 0).line(1, 0).line(1, 1).line(0, 1).close().chip()


def test_names():
    def two_chips():
        square()                       # a plain call stamps in the caller's part
        T.t.forward(2).place(square)

    def robot():
        T.t.place(two_chips)
        T.t.right(3).place(square)
        T.t.right(5).place(square)
        T.t.up(1).wire().jump(0, 0).line(1, 0).line(0, 1).close().chip("plate")

    names = set(build(robot).chips)
    assert names == {"robot/two_chips", "robot/two_chips/square",
                     "robot/square#1", "robot/square#2", "robot/plate"}, names


def test_place_hands_over_the_turtle():
    seen = []

    def probe():
        seen.append(T.t.pos.copy())
        T.t.forward(10)                # changes nothing

    def outer():
        T.t.right(1).place(probe)
        T.t.place(probe)

    build(outer)
    assert close(seen[0], [1, 0, 0]) and close(seen[1], [0, 0, 0])


def test_markers_at_every_part_entry():
    def inner():
        pass                           # no chips: abstract parts still get a marker

    def outer():
        T.t.forward(2).nose_right(90).place(inner)
        T.t.mirrored("x").right(1).place(inner)

    m = build(outer)
    marks = dict(m.markers)
    assert set(marks) == {"outer", "outer/inner#1", "outer/inner#2"}, set(marks)
    a = marks["outer/inner#1"]
    assert close(a[:3, 3], [0, 2, 0]) and close(a[:3, 1], [1, 0, 0])   # entry turtle, facing +x
    b = marks["outer/inner#2"]
    assert close(b[:3, 3], [-1, 0, 0]) and close(b[:3, 0], [-1, 0, 0])  # mirrored x shows as-is


def test_place_passes_arguments():
    def slat(width, tall=1):
        T.t.wire().jump(0, 0).line(0, tall).line(width, tall).line(width, 0).close().chip()

    def row():
        for i, w in enumerate((1, 2, 3)):
            T.t.right(4 * i).place(slat, w, tall=2)

    m = build(row)
    assert sorted(round(c.geom.area) for c in m.chips.values()) == [2, 4, 6]
    assert set(m.chips) == {"row/slat#1", "row/slat#2", "row/slat#3"}


def plate(tag=None, size=4):
    (T.t.wire().jump(-size / 2, -size / 2).line(size / 2, -size / 2)
     .line(size / 2, size / 2).line(-size / 2, size / 2).close()).chip(punch=tag)


def hole_centers_world(chip):
    """World positions of a chip's hole centers."""
    out = []
    for ring in chip.geom.interiors:
        c = np.array(ring.centroid.coords[0])
        out.append((chip.matrix @ np.r_[c, 0, 1])[:3])
    return out


def on_line(p, origin, axis):
    d = p - origin
    return np.linalg.norm(d - (d @ axis) * axis) < 1e-6


def test_punch_through_stacked_plates():
    def stack():
        T.t.right(1).forward(1 / 2).nose_up(90).punch(1 / 8, "dowel")  # vertical line at (1, .5)
        T.t.place(plate, "dowel")
        T.t.up(2).roll_right(180).place(plate, "dowel")                # flipped plate still works
        T.t.up(3).place(plate)                                         # untagged: no hole

    m = build(stack)
    a, b, c = (m.chips[n] for n in ("stack/plate#1", "stack/plate#2", "stack/plate#3"))
    assert len(c.geom.interiors) == 0
    for chip in (a, b):
        (h,) = hole_centers_world(chip)
        assert on_line(h, np.array([1, 0.5, 0]), np.array([0, 0, 1.0]))
        assert abs(chip.geom.area - (16 - math.pi / 64)) < 1e-3
    (rod,) = m.punches
    assert rod.used and rod.name == "stack/dowel"
    lo, hi = sorted((rod.p0[2], rod.p1[2]))
    assert abs(lo - (0 - T.PUNCH_OVERHANG)) < 1e-9 and abs(hi - (2 + T.PUNCH_OVERHANG)) < 1e-9, (lo, hi)


def test_punch_scoping():
    def leg():
        T.t.nose_up(90).punch(1 / 8, "knee")
        T.t.place(plate, "knee")                       # uses this leg's own knee

    def hips():
        T.t.right(3).nose_up(90).punch(1 / 4, "hip")
        T.t.place(leg)
        T.t.right(6).place(leg)
        T.t.right(3).up(1).place(plate, "hip")         # sees hips' punch

    m = build(hips)
    for n, x in (("hips/leg#1/plate", 0), ("hips/leg#2/plate", 6)):
        (h,) = hole_centers_world(m.chips[n])
        assert on_line(h, np.array([x, 0, 0]), np.array([0, 0, 1.0])), n
    assert {r.name for r in m.punches} == {"hips/hip", "hips/leg#1/knee", "hips/leg#2/knee"}

    def nearest():
        T.t.nose_up(90).punch(1 / 8, "p")
        def inner():
            T.t.right(1).nose_up(90).punch(1 / 8, "p")  # shadows the outer one
            T.t.place(plate, "p")
        T.t.place(inner)

    (h,) = hole_centers_world(build(nearest).chips["nearest/inner/plate"])
    assert on_line(h, np.array([1, 0, 0]), np.array([0, 0, 1.0]))


def test_punch_errors():
    def sibling():
        def a():
            T.t.nose_up(90).punch(1 / 8, "mine")
        def b():
            T.t.place(plate, "mine")
        T.t.place(a)
        T.t.place(b)
    raises(lambda: build(sibling), "no punch named 'mine' is visible")

    def slant():
        T.t.nose_up(80).punch(1 / 8, "p")
        T.t.place(plate, "p")
    raises(lambda: build(slant), "at a slant")

    def miss():
        T.t.right(10).nose_up(90).punch(1 / 8, "p")
        T.t.place(plate, "p")
    raises(lambda: build(miss), "misses this chip")

    def split():
        T.t.nose_up(90).punch(1, "p")
        (T.t.wire().jump(-2, -1 / 4).line(2, -1 / 4).line(2, 1 / 4).line(-2, 1 / 4).close()).chip(punch="p")
    raises(lambda: build(split), "into 2 pieces")

    def dup():
        T.t.nose_up(90).punch(1 / 8, "p")
        T.t.nose_up(90).punch(1 / 8, "p")
    raises(lambda: build(dup), "already defined")


def test_punch_mirrored_chip_and_unused():
    def side():
        T.t.right(1).nose_up(90).punch(1 / 8, "p")
        T.t.right(3).nose_up(90).punch(1 / 8, "spare")
        T.t.place(plate, "p")

    def both():
        T.t.place(side)
        T.t.mirrored("x").place(side)

    m = build(both)
    (h,) = hole_centers_world(m.chips["both/side#2/plate"])
    assert m.chips["both/side#2/plate"].mirrored
    assert on_line(h, np.array([-1, 0, 0]), np.array([0, 0, 1.0]))
    unused = sorted(r.name for r in m.punches if not r.used)
    assert unused == ["both/side#1/spare", "both/side#2/spare"]


def test_place_returns_what_the_part_returns():
    def thigh():
        shape = T.t.wire().jump(0, 0).line(0, 4, "knee").line(1, 4).line(1, 0).close()
        shape.chip()
        return shape.at("knee")

    def leg():
        knee = T.t.right(2).place(thigh)
        assert close(knee.pos, [2, 4, 0])      # a real world-space turtle, usable anywhere
        knee.nose_up(30).place(plate)
        assert T.t.place(lambda: None) is None

    m = build(leg)
    assert set(m.chips) == {"leg/thigh", "leg/plate"}


def test_untagged_punch_hits_are_flagged():
    def stack():
        T.t.nose_up(90).punch(1 / 8, "dowel")                 # vertical line through the origin
        T.t.place(plate, "dowel")
        T.t.up(2).place(plate, "dowel")                      # rod spans z = -1/4 .. 2 3/8
        T.t.up(1).place(plate)                               # in the middle, untagged: flagged
        T.t.up(1 / 2).right(3).place(plate, None, 1)         # beside the rod: fine
        T.t.up(6).place(plate)                               # on the line but past the rod: fine
        # a plate standing on edge, with the rod running through it lengthwise
        T.t.up(1 / 2).nose_up(90).place(plate, None, 1)

        # a rail along x at y = 3: plates lying along it may touch it but not sink into it
        rail = T.t.forward(3)
        rail.nose_right(90).punch(1 / 4, "rail")
        rail.roll_right(90).place(plate, "rail", 1)                  # end plates, tagged: the
        rail.right(2).roll_right(90).place(plate, "rail", 1)         # rod spans x = -1/4 .. 2 3/8
        rail.right(1).up(1 / 4).place(plate, None, 1)                # rests on top: touching
        rail.right(1).up(1 / 4 - 0.02).place(plate, None, 1)         # sunk 0.02": flagged

    m = build(stack)
    hit = sorted(ids[0] for _, ids in m.warnings)
    assert hit == ["chip:stack/plate#10", "chip:stack/plate#3", "chip:stack/plate#6"], hit
    text = m.warnings[0][0]
    assert "stack/dowel" in text and "isn't tagged" in text and "test_dsl.py" in text


def test_no_punch_exempts_a_chip():
    def capped(**kw):
        (T.t.wire().jump(-1, -1).line(1, -1).line(1, 1).line(-1, 1).close()).chip(**kw)

    def box(**cap):
        T.t.nose_up(90).punch(1 / 4, "dowel")
        T.t.place(plate, "dowel")
        T.t.up(2).place(plate, "dowel")
        T.t.up(2 + 1 / 8).place(capped, **cap)          # cap right on the dowel's end

    m = build(lambda: box())
    assert [ids[0] for _, ids in m.warnings] == ["chip:part/capped"]
    m = build(lambda: box(no_punch="dowel"))
    assert m.warnings == []
    assert len(m.chips["part/capped"].geom.interiors) == 0          # not cored
    raises(lambda: build(lambda: box(no_punch="dowl")), "no punch named 'dowl'")
    raises(lambda: build(lambda: box(punch="dowel", no_punch="dowel")), "in both punch= and no_punch=")


def test_thickness_chin_to_eyes():
    def p():
        T.setup(thickness=1/4)
        square()
    c = build(p).chips["p"]
    assert c.thickness == 0.25
    assert close(c.matrix, np.eye(4))  # chip z=0 is the turtle; solid grows to +z


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    failed = 0
    for n, f in tests:
        try:
            f()
            print(f"ok    {n}")
        except Exception as e:
            failed += 1
            print(f"FAIL  {n}: {type(e).__name__}: {e}")
    print(f"{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
