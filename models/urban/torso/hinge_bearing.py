from shared import board_thickness
from torso.shared import (
    bearing_plate_diameter,
    hinge_full_height,
    hinge_half_width,
    hinge_rounded_radius,
    hinge_straight_height,
)

from flatpack import t


def hinge_plate():
    (
        t.nose_down(90)
        .down(board_thickness / 2)
        .wire()
        .jump(-hinge_half_width, 0)
        .line(-hinge_half_width, hinge_straight_height)
        .arc(-hinge_half_width + hinge_rounded_radius, hinge_straight_height, 90)
        .line(hinge_half_width - hinge_rounded_radius, hinge_full_height)
        .arc(hinge_half_width - hinge_rounded_radius, hinge_straight_height, 90)
        .line(hinge_half_width, 0)
        .close()
        .chip()
    )


def hinge_bearing():
    # bearing/hinge
    t.circle(0, 0, bearing_plate_diameter / 2).chip()
    t.place(hinge_plate)
    t.nose_right(90).place(hinge_plate)
