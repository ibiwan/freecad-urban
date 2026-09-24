from leg.lower import lower
from shared import board_thickness, hinge_radius, hip_dowel_diameter

from flatpack import t

skel_width = 1.5
skel_len = 3
taper_len = 1.75
straight_len = skel_len - taper_len
taper_depth = 0.75
skel_depth = 1.5


def _riser_wire(tt):
    return (
        tt.wire()
        .jump(-taper_depth / 2, 0, "A")
        .line(-skel_depth / 2, taper_len, "B")
        .line(-skel_depth / 2, skel_len)
        .line(skel_depth / 2, skel_len)
        .line(skel_depth / 2, taper_len, "C")
        .line(taper_depth / 2, 0, "D")
        .close()
    )


def _plate(width, depth):
    (
        t.wire()
        .jump(-width / 2, 0)
        .line(-width / 2, depth)
        .line(width / 2, depth)
        .line(width / 2, 0)
        .close()
        .chip()
    )


def upper():
    t_left = t.left(skel_width / 2).nose_right(90).nose_down(90)
    w_left = _riser_wire(t_left)
    (w_left + t_left.circle(0, skel_len, hinge_radius)).chip()

    t_right = t.right(skel_width / 2).nose_left(90).nose_down(90)
    w_right = _riser_wire(t_right)
    (w_right + t_right.circle(0, skel_len, hinge_radius)).chip()

    # top/bottom/mid
    t.down(board_thickness).back(taper_depth / 2).place(_plate, skel_width, taper_depth)
    t.down(taper_len).back(skel_depth / 2).place(_plate, skel_width, skel_depth)
    t.down(skel_len).back(skel_depth / 2).place(_plate, skel_width, skel_depth)

    # braces
    inner_w = skel_width - 2 * board_thickness
    t.down(board_thickness * 2).back(taper_depth / 2).place(
        _plate, inner_w, taper_depth
    )
    t.down(board_thickness * 2 + hip_dowel_diameter).back(taper_depth / 2).place(
        _plate, inner_w, taper_depth
    )

    # plates
    (
        w_right.on_edge("A", "B")
        .right(skel_width / 2)
        .place(_plate, skel_width, w_right.distance("A", "B")),
    )
    (
        w_right.on_edge("C", "D")
        .right(skel_width / 2)
        .place(_plate, skel_width, w_right.distance("C", "D")),
    )

    lower_plate_start = taper_len
    lower_plate_len = straight_len
    (
        t.down(lower_plate_start)
        .forward(skel_depth / 2)
        .nose_down(90)
        .place(_plate, skel_width, lower_plate_len)
    )
    (
        t.down(lower_plate_start)
        .back(skel_depth / 2)
        .nose_down(90)
        .roll_right(180)
        .place(_plate, skel_width, lower_plate_len)
    )

    t.down(skel_len + hinge_radius).place(lower)
