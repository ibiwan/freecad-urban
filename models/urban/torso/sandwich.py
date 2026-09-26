from shared import board_thickness, n_gon_wire
from torso.shared import box_height, sandwich_high_diameter, sandwich_low_diameter
from torso.shoulder_dowel_box import shoulder_dowel_box

from flatpack import t


def vent_mount(fudge_1, fudge_2):
    (
        t.nose_up(90)
        .wire()
        .jump(0, 0 - fudge_1)
        .line(-box_height, 0 - fudge_1)
        .line(-box_height, 1.25 - fudge_2)
        .line(0, 0.75 - fudge_2)
        .close()
        .chip()
    )


def vent_mounts(dist):
    t.forward(board_thickness).place(vent_mount, 0.5, 0.5)
    t.forward(dist).place(vent_mount, 0.75, 0.5)


def sandwich():
    tt = t.up(board_thickness)
    tt.circle(0, 0, sandwich_low_diameter / 2).chip()

    tt.up(board_thickness).place(shoulder_dowel_box)

    tt.up(box_height + board_thickness).circle(0, 0, sandwich_high_diameter / 2).chip()

    w14 = n_gon_wire(
        tt.up(board_thickness),
        14,
        # manually adjusted to get boarder faces fully outside box
        sandwich_low_diameter / 2 - 0.2,
    )
    w14.chip()

    # vents on edges 2-3 and 4-5
    w14.on_edge("v2", "v3").place(vent_mounts, w14.distance("v2", "v3"))
    w14.on_edge("v5", "v4").mirrored("x").place(vent_mounts, w14.distance("v5", "v4"))

    return tt.up(box_height + board_thickness)
