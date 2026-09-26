from head import head
from shared import board_thickness, shoulder_dowel_diameter
from torso.hinge_bearing import hinge_bearing
from torso.sandwich import sandwich
from torso.shared import box_height, waist_height, waist_width_1, waist_width_2
from torso.waist_ring import waist_ring

from flatpack import t


def torso():
    t.up(waist_height * 2 + box_height / 2 + board_thickness * 2).nose_left(90).punch(
        shoulder_dowel_diameter / 2, "shoulder-dowel"
    )

    t.place(hinge_bearing)

    tt = t.place(waist_ring, waist_width_1)
    tt = tt.place(waist_ring, waist_width_2)
    tt = tt.place(sandwich)
    tt.up(board_thickness).circle(0, 0, 1).chip()

    # head
    t.up(4).place(head)
