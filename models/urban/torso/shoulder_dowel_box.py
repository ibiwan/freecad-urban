from shared import board_thickness, rect_forward
from torso.shared import box_depth, box_height, box_section_width, box_width

from flatpack import t


def shoulder_dowel_box():
    tt = t.nose_left(90).nose_up(90).down(board_thickness / 2)
    for i in range(-2, 3):
        rect_forward(tt.down(i * box_section_width), box_depth, box_height).chip(
            punch="shoulder-dowel"
        )

    tt = t.nose_up(90)
    rect_forward(tt.down(box_depth / 2), box_width - board_thickness, box_height).chip()
    rect_forward(
        tt.up(box_depth / 2 - board_thickness), box_width - board_thickness, box_height
    ).chip()

    return t.up(box_height)
