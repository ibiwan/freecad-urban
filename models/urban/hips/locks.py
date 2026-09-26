from hips.shared import plate_width
from shared import (
    board_thickness,
    hinge_box_height,
    hip_dowel_diameter,
    n_gon_wire,
    upper_leg_width,
)

from flatpack import t


def lock():
    t1 = t.forward(plate_width / 2 + upper_leg_width + board_thickness).nose_down(90)
    t1.circle(0, 0, 1).chip(punch="hip-dowel", no_punch="hip-pin")
    (n_gon_wire(t1.up(board_thickness), 6, 1, True)).chip(
        punch="hip-pin", no_punch="hip-dowel"
    )
    (n_gon_wire(t1.up(board_thickness * 2), 6, 0.75, True)).chip(
        punch="hip-pin", no_punch="hip-dowel"
    )
    (
        t1.up(board_thickness * 3)
        .circle(0, 0, 0.5)
        .chip(punch="hip-pin", no_punch="hip-dowel")
    )


def locks():
    t1 = t.down(
        hinge_box_height + hip_dowel_diameter / 2 + board_thickness * 2
    ).nose_right(90)
    t1.place(lock)
    t1.mirrored("y").place(lock)
