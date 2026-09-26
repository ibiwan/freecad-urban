from hips.shared import (
    dowel_brace_size,
    nether_width,
    plate_width,
)
from shared import (
    board_thickness,
    hinge_box_height,
    hip_dowel_diameter,
    rect_around,
    rect_forward,
)

from flatpack import t


def cross_braces():
    rect_forward(
        t.down(hinge_box_height + 2 * board_thickness)
        .forward(hip_dowel_diameter / 2)
        .nose_down(90),
        nether_width,
        hip_dowel_diameter,
    ).chip()

    rect_forward(
        t.down(hinge_box_height + 2 * board_thickness)
        .back(hip_dowel_diameter / 2 + board_thickness)
        .nose_down(90),
        nether_width,
        hip_dowel_diameter,
    ).chip()

    rect_around(
        t.down(3 * board_thickness + hinge_box_height + hip_dowel_diameter),
        plate_width,
        dowel_brace_size,
    ).chip()

    rect_around(
        t.down(4 * board_thickness + hinge_box_height + hip_dowel_diameter),
        nether_width,
        dowel_brace_size,
    ).chip()
