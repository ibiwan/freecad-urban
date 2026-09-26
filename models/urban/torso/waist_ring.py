from shared import (
    board_thickness,
    n_gon_wire,
    rect_forward,
)
from torso.shared import waist_spar_height

from flatpack import t


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


def waist_ring(width):
    tt = t.up(waist_spar_height + board_thickness)
    tt.place(_full_spar, width)
    tt.nose_right(90).place(_full_spar, width)

    for i in range(4):
        tt.nose_right(45 + 90 * i).place(_half_spar, width)

    w = n_gon_wire(tt, 8, width / 2, inradius=True, offset=True)
    w.chip()

    for i in range(8):
        lbl_a = f"v{i}"
        lbl_b = f"v{i + 1}"
        d = w.distance(lbl_a, lbl_b)
        rect_forward(
            w.on_edge(lbl_a, lbl_b).forward(d / 2).nose_right(90).back(board_thickness),
            d,
            waist_spar_height + board_thickness,
        ).chip()
    return tt
