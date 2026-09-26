from hips.armor import armor
from hips.cross_braces import cross_braces
from hips.dowel_braces import dowel_braces
from hips.hinge_box import hinge_box
from hips.locks import locks
from hips.shared import hip_leg_tops_delta
from leg.leg import leg
from shared import board_thickness, hinge_box_height, hip_dowel_diameter, pin_diameter

from flatpack import t


def hips():
    tc = t.down(
        hip_leg_tops_delta + hip_dowel_diameter / 2 + 2 * board_thickness
    ).nose_left(90)
    tc.punch(hip_dowel_diameter / 2, "hip-dowel")
    tc.punch(pin_diameter / 2, "hip-pin")

    t.place(hinge_box)

    inner_hip_braces = (
        t.down(hinge_box_height + hip_dowel_diameter / 2 + 2 * board_thickness)
        .nose_right(90)
        .nose_down(90)
        .place(dowel_braces)
    )

    t.place(cross_braces)

    left_brace, right_brace = inner_hip_braces
    t.place(armor, left_brace, right_brace)

    t.place(locks)

    t.left(2).down(hip_leg_tops_delta).place(leg)
    t.right(2).down(hip_leg_tops_delta).place(leg)
