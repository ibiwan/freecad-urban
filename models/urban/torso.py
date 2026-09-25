from head import head
from shared import board_thickness, n_gon, rect_forward, waist_hinge_diameter

from flatpack import t

bearing_plate_diameter = 2.125
hinge_straight_height = 0.125
hinge_rounded_radius = 0.25
hinge_full_height = hinge_straight_height + hinge_rounded_radius
hinge_half_width = waist_hinge_diameter / 2
waist_spar_height = 0.375
waist_width_1 = 2.5
waist_width_2 = 3.75


def _hinge_plate():
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


def _full_spar(w):
    rect_forward(
        t.nose_down(90).down(board_thickness / 2),
        w,
        waist_spar_height,
    ).chip()


def _half_spar(w):
    big_w = rect_forward(
        t.left(w / 4).nose_down(90).down(board_thickness / 2), w / 2, waist_spar_height
    )
    small_w = rect_forward(
        t.nose_down(90).down(board_thickness / 2), w / 4, waist_spar_height
    )
    (big_w - small_w).chip()


def torso():
    # bearing/hinge
    t.circle(0, 0, bearing_plate_diameter / 2).chip()
    t.place(_hinge_plate)
    t.nose_right(90).place(_hinge_plate)

    # waist tier 1
    tt = t.up(waist_spar_height + board_thickness)
    tt.place(_full_spar, waist_width_1)
    tt.nose_right(90).place(_full_spar, waist_width_1)

    for i in range(4):
        tt.nose_right(45 + 90 * i).place(_half_spar, waist_width_1)

    w = tt.wire().jump(0, 0, "v-1")
    for i in range(0, 9):
        lbl = f"v{i}"
        w = w.line(*n_gon(8, waist_width_1 / 2, i - 0.5, True), lbl)
    w.close().chip()

    # head
    t.up(4).place(head)
