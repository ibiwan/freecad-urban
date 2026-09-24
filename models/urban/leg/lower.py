from math import cos, pi, sin

from foot import foot
from shared import board_thickness, hinge_radius, rect_around, rect_forward

from flatpack import t

skel_width = 1.5
skel_len = 2.125
skel_depth = 1


def _n_gon(n, r, i):
    theta = 2 * pi / n * i
    return (r * cos(theta), r * sin(theta))


def _shin_slat(width, len, short=True):
    extra = 0 if short else 2 * board_thickness
    start = -extra
    use_len = len + 2 * extra
    rect_forward(
        t.forward(start),
        width,
        use_len,
    ).chip()


def _stab():
    (
        t.wire()
        .jump(skel_width / 2, -board_thickness)
        .line(skel_width / 2, board_thickness)
        .line(-skel_width / 2, board_thickness)
        .line(-skel_width / 2, -board_thickness)
        .close()
        .chip()
    )


def cross_riser():
    rect_forward(
        t.up(hinge_radius / 2 - board_thickness).nose_down(90),
        skel_width - 2 * board_thickness,
        skel_len + hinge_radius - board_thickness * 2,
    ).chip()


def lower():
    # left riser with hinge bosses
    t_left = t.right(skel_width / 2 - board_thickness).nose_down(90).roll_left(90)

    (
        rect_forward(t_left, skel_depth, skel_len)
        + t_left.circle(0, 0, hinge_radius)
        + t_left.circle(0, skel_len, hinge_radius)
    ).chip()

    # right riser with hinge bosses
    t_right = t.left(skel_width / 2 - board_thickness).nose_down(90).roll_right(90)

    (
        rect_forward(t_right, skel_depth, skel_len)
        + t_right.circle(0, 0, hinge_radius)
        + t_right.circle(0, skel_len, hinge_radius)
    ).chip()

    # cross risers
    t.back(2 * board_thickness).place(cross_riser)
    t.forward(board_thickness).place(cross_riser)

    # octagonal slat mounts
    r = 1

    w1 = t.down(2 * board_thickness).wire().jump(r, 0, "v0")
    w2 = t.down(skel_len - board_thickness).wire().jump(r, 0, "v0")
    for i in range(1, 9):
        lbl = f"v{i}"
        w1 = w1.line(*_n_gon(8, r, i), lbl)
        w2 = w2.line(*_n_gon(8, r, i), lbl)
    w1 = w1.close()
    w2 = w2.close()
    w1.chip()
    w2.chip()

    # slats
    for i in range(8):
        width = w1.distance(f"v{i}", f"v{i + 1}")
        (
            w1.on_edge(f"v{i}", f"v{i + 1}")
            .left(board_thickness)
            .forward(w1.distance(f"v{i}", f"v{i + 1}") / 2)
            .nose_right(90)
            .place(_shin_slat, width, skel_len - 2 * board_thickness, i in (0, 3, 4, 7))
        )

    # hinge stabilizers
    stab_d = 2 * board_thickness
    stab_offset = hinge_radius - board_thickness

    t_hi = t.down(board_thickness)
    rect_around(t_hi.forward(stab_offset), skel_width, stab_d).chip()
    rect_around(t_hi.back(stab_offset), skel_width, stab_d).chip()

    t_low = t.down(skel_len)
    rect_around(t_low.forward(stab_offset), skel_width, stab_d).chip()
    rect_around(t_low.back(stab_offset), skel_width, stab_d).chip()

    rect_forward(
        t.back(board_thickness / 2).up(hinge_radius).nose_down(90),
        skel_width - 2 * board_thickness,
        stab_d,
    ).chip()

    rect_forward(
        t.forward(board_thickness / 2).down(skel_len + hinge_radius).nose_up(90),
        skel_width - 2 * board_thickness,
        stab_d,
    ).chip()

    # foot
    t.down(skel_len + hinge_radius).place(foot)
