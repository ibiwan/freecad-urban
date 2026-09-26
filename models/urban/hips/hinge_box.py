from hips.shared import plate_width
from shared import (
    board_thickness,
    hinge_box_height,
    rect_around,
    rect_forward,
    waist_hinge_diameter,
)

from flatpack import t


def hinge_box():

    w = rect_around(t.down(board_thickness), plate_width, plate_width)
    c = t.down(board_thickness).circle(0, 0, waist_hinge_diameter / 2)
    (w - c).chip()

    for i in range(4):
        t_outer = t.nose_right(90 * i)
        rect_forward(
            t_outer.down(board_thickness)
            .forward(plate_width / 2 - board_thickness)
            .nose_down(90),
            plate_width,
            hinge_box_height,
        ).chip()

        t_inner = t.nose_right(45 + 90 * i)
        rect_forward(
            t_inner.down(board_thickness)
            .forward(waist_hinge_diameter / 2)
            .nose_down(90),
            plate_width / 2,
            hinge_box_height,
        ).chip()

    rect_around(
        t.down(2 * board_thickness + hinge_box_height),
        plate_width + 2 * board_thickness,
        plate_width,
    ).chip()
