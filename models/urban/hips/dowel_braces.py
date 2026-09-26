from hips.shared import (
    dowel_brace_size,
    nether_width,
    plate_width,
)
from shared import (
    board_thickness,
    rect_around,
)

from flatpack import t


def dowel_braces():
    outer_left = rect_around(
        t.down(plate_width / 2 + board_thickness),
        dowel_brace_size,
        dowel_brace_size,
    )
    outer_left.chip(punch="hip-dowel", no_punch="hip-pin")

    outer_right = rect_around(
        t.up(plate_width / 2),
        dowel_brace_size,
        dowel_brace_size,
    )
    outer_right.chip(punch="hip-dowel", no_punch="hip-pin")

    inner_left = rect_around(
        t.down(nether_width / 2),
        dowel_brace_size,
        dowel_brace_size,
    )
    inner_left.chip(punch="hip-dowel", no_punch="hip-pin")

    inner_right = rect_around(
        t.up(nether_width / 2 - board_thickness),
        dowel_brace_size,
        dowel_brace_size,
    )
    inner_right.chip(punch="hip-dowel", no_punch="hip-pin")

    return (inner_left, inner_right)
